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

from typing import Any

from .similarity import MIN_DUPLICATE_COVERAGE, classify, genome_distance

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


def _mechanism(candidate: dict[str, Any]) -> str:
    genome = candidate.get("genome") or {}
    values = genome.get("mechanism")
    if isinstance(values, list) and values and values[0] != "unknown":
        return str(values[0])
    return ""


def _structural_distance(a: dict[str, Any], b: dict[str, Any]) -> float:
    """Distancia estructural [0,1]. Con cobertura insuficiente (<0.60) el
    genoma no afirma ni igualdad ni diversidad: distancia neutra."""
    result = genome_distance(a.get("genome") or {}, b.get("genome") or {})
    if result["coverage"] < MIN_DUPLICATE_COVERAGE:
        return NEUTRAL_DISTANCE
    return float(result["distance"])


def _relation(a: dict[str, Any], b: dict[str, Any]) -> str:
    return classify(a.get("genome") or {}, b.get("genome") or {})["verdict"]


def select_finalists(
    pool: list[dict[str, Any]],
    n: int,
    *,
    quality_floor: float | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Selección finalista por utilidad marginal. Devuelve (finalistas, informe).

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
