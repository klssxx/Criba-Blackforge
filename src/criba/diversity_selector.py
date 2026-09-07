"""Selector finalista diversity-aware (megaprompt §24-§28, Fase M2).

Sustituye el embudo "top-N por score" del flujo de invención por una
selección de utilidad marginal determinista y local (estilo MMR):

    utilidad(c) = score
                + w_diversidad · distancia_estructural_mínima_a_elegidos
                − penalización_close_variant
                − penalización_duplicado_probable
                − penalización_familia_repetida
                − penalización_mecanismo_repetido

Contratos:
- Suelo de calidad PREVIO: la rareza sin relevancia no gana (§26).
- probable_duplicate se excluye del conjunto final cuando existen
  alternativas válidas (§28).
- Si el pool no alcanza N finalistas con diversidad: estado honesto
  DIVERSITY_CONSTRAINED (§28), nunca variedad fabricada.
- Pesos centralizados aquí, documentados y testeados por comportamiento
  (no por valor, salvo contrato público).
- Reutiliza criba.similarity (genome_distance/classify); sin dependencias
  nuevas, sin BD vectorial.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from .similarity import MIN_DUPLICATE_COVERAGE, WEIGHTS, _effective, classify, genome_distance

# Diversidad semántica de mecanismos interpretados (megaprompt §27.3): fallback
# local, determinista y gratuito — misma idea expresada con otras palabras.
# Jaccard sobre tokens normalizados (>=4 caracteres). Umbral 0.6: detecta
# paráfrasis de sinonimo único (~0.67 sobre 6 tokens) sin confundir mecanismos
# distintos que comparten vocabulario genérico (~0.2). Límite documentado: una
# paráfrasis que cambie MÁS de la mitad del vocabulario no se detecta aquí.
MECHANISM_DUPLICATE_JACCARD = 0.6

# Marcadores de negación: presentes en un lado y no en el otro, invierten el
# mecanismo aunque el vocabulario coincida (prueba negativa de negación).
_NEGATION_RE = re.compile(
    r"\b(no|sin|nunca|jamás|jamais|impide|impedir|prohíbe|prohibir|prohibido|"
    r"evita|evitar|cancela|cancelar|revoca|revocar)\b")


def _content_tokens(text: str) -> list[str]:
    return [t for t in re.split(r"[^a-z0-9áéíóúñü]+", (text or "").casefold()) if len(t) >= 4]


def compare_mechanisms(a: str, b: str) -> str:
    """Clasificación honesta entre dos mecanismos interpretados.

    Devuelve: ``DUPLICATE`` (misma idea, paráfrasis), ``DISTINCT`` (mecanismos
    distintos, incluidos negación e inversión de dirección) o ``UNKNOWN``
    (texto insuficiente o zona gris — NO se auto-descarta por similitud baja).
    """
    ta, tb = set(_content_tokens(a)), set(_content_tokens(b))
    if len(ta) < 3 or len(tb) < 3:
        return "UNKNOWN"
    # Negación asimétrica ANTES de comparar vocabulario: "no concede" vs
    # "concede" comparte todos los tokens pero el mecanismo es opuesto.
    neg_a = bool(_NEGATION_RE.search((a or "").casefold()))
    neg_b = bool(_NEGATION_RE.search((b or "").casefold()))
    if neg_a != neg_b:
        return "DISTINCT"
    ra, rb = _content_tokens(a), _content_tokens(b)
    if ta == tb:
        # Mismo vocabulario: el reorden de cláusulas es ambiguo desde léxico
        # (¿inversión de dirección o solo estilo?) → UNKNOWN, no DISTINCT ni
        # DUPLICATE (auditoría qa-win: la heurística de orden confunde estilo
        # con causalidad).
        return "DUPLICATE" if tuple(ra[:3]) == tuple(rb[:3]) else "UNKNOWN"
    inter, union = len(ta & tb), len(ta | tb)
    jac = inter / union if union else 0.0
    if jac >= MECHANISM_DUPLICATE_JACCARD:
        return "DUPLICATE"
    if jac >= 0.45:
        return "UNKNOWN"  # zona gris: no descartar automáticamente
    return "DISTINCT"


def same_idea_mechanism(a: str, b: str) -> bool:
    """Compatibilidad: True solo si son DUPLICATE (misma idea reescrita)."""
    return compare_mechanisms(a, b) == "DUPLICATE"

# Pesos centralizados (megaprompt §25/§44). Documentación por término:
W_QUALITY = 1.0            # score del candidato (heurística local etiquetada)
W_DIVERSITY = 0.6          # distancia estructural mínima a los ya elegidos
PENALTY_CLOSE_VARIANT = 0.35    # por cada close_variant ya elegido
PENALTY_PROBABLE_DUPLICATE = 2.0  # excluye en la práctica si hay alternativas
PENALTY_FAMILY_REPEAT = 0.15    # por cada finalista previo de la misma familia
PENALTY_MECHANISM_REPEAT = 0.25  # por cada finalista previo con el mismo mecanismo
NEUTRAL_DISTANCE = 0.5     # genoma insuficiente (cobertura < 0.60): ni igual ni diverso

# Suelo de calidad relativo: un candidato entra al pool si score >= mejor_score
# del pool − RELATIVE_QUALITY_FLOOR. Centralizado para poder ablacionar.
RELATIVE_QUALITY_FLOOR = 0.15

# Fatiga histórica (megaprompt §36): cooldown por decaimiento, NO ban
# permanente. first_seen reciente → penalización máxima; tras COOLDOWN_DAYS
# la combinación vuelve a estar neutra y puede reaparecer si es relevante.
PENALTY_OVERUSE_MAX = 0.30
COOLDOWN_DAYS = 30.0


def _pair_key(candidate: dict[str, Any]) -> tuple[str, str]:
    methods = sorted(str(m) for m in candidate.get("methods", []) if m)
    return (methods[0], methods[1]) if len(methods) >= 2 else ("", "")


def _historical_penalty(
    candidate: dict[str, Any],
    first_seen: dict[tuple[str, str], str] | None,
) -> float:
    """[0, PENALTY_OVERUSE_MAX] según antigüedad del primer uso del par.

    Sin historial o par nuevo: 0 (neutro). El decaimiento hace que una
    combinación excelente pueda reaparecer cuando su relevancia lo justifica.
    """
    if not first_seen:
        return 0.0
    seen_iso = first_seen.get(_pair_key(candidate))
    if not seen_iso:
        return 0.0
    try:
        seen = datetime.fromisoformat(str(seen_iso).replace("Z", "+00:00"))
        age_days = (datetime.now(timezone.utc) - seen).total_seconds() / 86400.0
    except ValueError:
        return 0.0
    remaining = max(0.0, 1.0 - age_days / COOLDOWN_DAYS)
    return PENALTY_OVERUSE_MAX * remaining


def _mechanism(candidate: dict[str, Any]) -> str:
    genome = candidate.get("genome") or {}
    values = genome.get("mechanism")
    if isinstance(values, list) and values and values[0] != "unknown":
        return str(values[0])
    return ""


def _structural_distance(a: dict[str, Any], b: dict[str, Any]) -> float:
    """Distancia estructural [0,1]. Un campo solo compara si AMBOS lados
    llevan información: lo desconocido NO otorga diversidad ni igualdad —
    contribuye neutro (mandato §2: mecanismo incompleto queda UNKNOWN).
    Sin ningún campo comparable en ambos lados: distancia neutra."""
    ga, gb = a.get("genome") or {}, b.get("genome") or {}
    if not ga and not gb:
        return NEUTRAL_DISTANCE
    total = 0.0
    comparable = False
    for field, w in WEIGHTS.items():
        ea = _effective(ga.get(field, ["unknown"]))
        eb = _effective(gb.get(field, ["unknown"]))
        if ea and eb:
            union = len(ea | eb)
            sim = (len(ea & eb) / union) if union else 0.0
            total += w * (1 - sim)
            comparable = True
        else:
            total += w * (1 - NEUTRAL_DISTANCE)
    return round(total, 4) if comparable else NEUTRAL_DISTANCE


def _relation(a: dict[str, Any], b: dict[str, Any]) -> str:
    return str(classify(a.get("genome") or {}, b.get("genome") or {})["verdict"])


def select_finalists(
    pool: list[dict[str, Any]],
    n: int,
    *,
    quality_floor: float | None = None,
    historical_first_seen: dict[tuple[str, str], str] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Selección finalista por utilidad marginal. Devuelve (finalistas, informe).

    ``historical_first_seen``: primer uso registrado por par de métodos
    (formato combo_key de Storage). Aplica cooldown por decaimiento; nunca
    prohibición permanente.

    El informe incluye el estado de diversidad (OK/DIVERSITY_CONSTRAINED) y
    la explicación de cada elección/descarte (trazabilidad §22).
    """
    if n <= 0 or not pool:
        return [], {"status": "EMPTY_POOL", "finalists": [], "picks": []}

    best_score = max(float(c.get("score", 0.0)) for c in pool)
    floor = best_score - RELATIVE_QUALITY_FLOOR if quality_floor is None else quality_floor
    valid = [c for c in pool if float(c.get("score", 0.0)) >= floor]

    report: dict[str, Any] = {
        "status": "OK",
        "quality_floor": round(floor, 4),
        "pool_size": len(pool),
        "valid_size": len(valid),
        "picks": [],
    }

    if not valid:
        report["status"] = "DIVERSITY_CONSTRAINED"
        report["reason"] = "ningún candidato supera el suelo de calidad"
        return [], report

    ordered = sorted(valid, key=lambda c: (-float(c.get("score", 0.0)), str(c.get("idea_id", ""))))
    selected: list[dict[str, Any]] = [ordered[0]]
    remaining = ordered[1:]
    report["picks"].append({
        "idea_id": ordered[0].get("idea_id"),
        "why": f"mejor score sobre el suelo ({ordered[0].get('score')})",
    })

    while remaining and len(selected) < n:
        best: dict[str, Any] | None = None
        best_utility = float("-inf")
        best_explain = ""
        for candidate in remaining:
            utility = W_QUALITY * float(candidate.get("score", 0.0))
            explain: list[str] = []
            min_distance = min(
                (_structural_distance(candidate, s) for s in selected),
                default=NEUTRAL_DISTANCE,
            )
            utility += W_DIVERSITY * min_distance
            explain.append(f"distancia mínima a elegidos={min_distance:.2f}")

            verdicts = [_relation(candidate, s) for s in selected]
            dup_count = verdicts.count("probable_duplicate")
            close_count = verdicts.count("close_variant")
            if dup_count:
                utility -= PENALTY_PROBABLE_DUPLICATE * dup_count
                explain.append(f"duplicado probable x{dup_count}")
            if close_count:
                utility -= PENALTY_CLOSE_VARIANT * close_count
                explain.append(f"variante cercana x{close_count}")

            same_family = sum(1 for s in selected if s.get("family") == candidate.get("family"))
            if same_family:
                utility -= PENALTY_FAMILY_REPEAT * same_family
                explain.append(f"familia repetida x{same_family}")

            mechanism = _mechanism(candidate)
            if mechanism:
                same_mechanism = sum(1 for s in selected if _mechanism(s) == mechanism)
                if same_mechanism:
                    utility -= PENALTY_MECHANISM_REPEAT * same_mechanism
                    explain.append(f"mecanismo repetido x{same_mechanism}")

            overuse = _historical_penalty(candidate, historical_first_seen)
            if overuse:
                utility -= overuse
                explain.append(f"fatiga histórica −{overuse:.2f}")

            if utility > best_utility:
                best, best_utility, best_explain = candidate, utility, "; ".join(explain) or "sin vecinos"

        if best is None:
            break
        selected.append(best)
        remaining.remove(best)
        report["picks"].append({
            "idea_id": best.get("idea_id"),
            "why": f"utilidad marginal {round(best_utility, 4)} ({best_explain})",
        })

    # Honestidad: ¿se alcanzó N sin fabricar variedad?
    if len(selected) < n:
        report["status"] = "DIVERSITY_CONSTRAINED"
        report["reason"] = (
            f"pool con {len(valid)} válidos no alcanza {n} finalistas con diversidad mínima"
        )

    report["finalists"] = [c.get("idea_id") for c in selected]
    report["discarded_by_floor"] = sorted(
        str(c.get("idea_id") or c.get("title") or "")
        for c in pool if float(c.get("score", 0.0)) < floor
    )
    return selected, report
