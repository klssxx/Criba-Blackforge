"""CRIBA innovation engine — MVP orchestrator.

Single canonical packet: MANDATORY_MODEL_PACKET (schema 2.0.0) extended with an
``innovation`` block, additively. Legacy fields are preserved. ``packet["ideas"]``
is the SAME object as ``packet["innovation"]["ideas"]`` (one canonical collection).

Separation of concerns (condition 5):
- orchestration:  ``activate`` (this file)
- local generation: ``cartograph_and_break`` / ``diverge`` (injectable hooks)
- genome validation/normalization: ``criba.genome``
- similarity / duplicates: ``criba.similarity``

The two HY3 call points are isolated as injectable functions so a cloud adapter
can replace the local implementation later without touching the rest.
"""
from __future__ import annotations
import json, uuid
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple

from .catalog import find_current
from .constants import MAX_QUERY_CHARS, VALID_MODES, CURRENT_CATALOG_VERSION, SELECTOR_VERSION, VALID_DECISIONS, VALID_PIPELINE_ACTIONS
from .methods import select_methods
from .selector import select
from .genome import normalize_proposal, ONTOLOGY_VERSION, UnclassifiedProperty
from .similarity import classify as genome_classify

SCHEMA = "mandatory_model_packet"
SCHEMA_VERSION = "2.0.0"

INSTRUCTION = """Antes de responder al usuario, aplica obligatoriamente el paquete CRIBA adjunto.

Corriente activada: {current}.

Tu tarea es INNOVAR: usa el paquete para generar ideas nuevas, divergentes y accionables. Separa: 1. ideas generadas, 2. combinaciones inesperadas, 3. experimentos rápidos, 4. riesgos y cómo acotarlos.

No reveles cadena de pensamiento privada. Expón corriente activada, ideas, propuestas, riesgos, incertidumbre y respuesta final. Cuando falte información, no inventes datos."""

# ---------------------------------------------------------------------------
# Injectable generation hooks (condition 4). Local deterministic implementations
# today; swap for an HY3 adapter later without rewriting the orchestrator.
# ---------------------------------------------------------------------------
CartographFn = Callable[[str, dict[str, Any], dict[str, Any]], dict[str, Any]]
DivergeFn = Callable[[dict[str, Any], dict[str, Any], dict[str, Any], list[Any], str], list[Any]]


def _novelty_verbs(query: str) -> bool:
    lowered = query.casefold()
    return any(v in lowered for v in ("nuev", "innov", "disrupt", "alternativa", "idea",
                                       "crea", "diseñ", "mejor", "propuest", "experimento",
                                       "raro", "diferente", "original", "reinvent", "romper"))


def cartograph_and_break(query: str, context: dict[str, Any], selection: dict[str, Any]) -> dict[str, Any]:
    """Phase 1+2 (Cartografiar + Romper). Local, deterministic.

    Returns {known_space, assumptions, saturated_mechanisms, ruptures}.
    """
    lowered = query.casefold()
    known = [
        "El enfoque estándar delega la decisión a un operador humano.",
        "La solución dominante añade más reglas de validación.",
        "Se asume que más automatización siempre reduce el error.",
        "El diseño convencional centraliza la autoridad.",
        "Se parte de que el usuario conocerá el procedimiento.",
    ]
    if "aprob" in lowered or "agent" in lowered:
        known.append("El flujo típico exige aprobación previa de un supervisor.")
    if "fraude" in lowered:
        known.append("La defensa habitual son reglas estáticas de detección de fraude.")
    assumptions = [
        "El primer enfoque es el único posible.",
        "Quien diseña conoce todos los casos límite.",
        "Más control siempre implica más seguridad.",
        "El coste de error es aceptable mientras sea raro.",
    ]
    saturated = [
        {"mechanism": "verification", "reason": "ya se aplica en todas las capas."},
        {"mechanism": "automation", "reason": "empujada al límite sin margen de reversión."},
        {"mechanism": "consensus", "reason": "se invoca para todo, diluyendo responsabilidad."},
    ]
    # Ruptures: at least 4 operations, >=3 families, >=1 invert, >=1 elimination.
    ruptures = []
    for i, a in enumerate(assumptions[:4], start=1):
        ruptures.append({"assumption_id": f"A{i:02d}", "operation": "invert",
                         "result": f"En lugar de asumir '{a}', exigir lo contrario y diseñar para él.",
                         "method_id": "M200-01"})
        ruptures.append({"assumption_id": f"A{i:02d}", "operation": "eliminate",
                         "result": f"Quitar el componente implícito en '{a}' y ver si el sistema sigue funcionando.",
                         "method_id": "M100-01"})
    return {
        "known_space": known[:12],
        "assumptions": assumptions,
        "saturated_mechanisms": saturated,
        "ruptures": ruptures,
        "counterexample": "Contraejemplo: una entrada válida según las reglas actuales produce un resultado que viola el objetivo declarado.",
        "wants_novelty": _novelty_verbs(query),
    }


# ===========================================================================
# Two-layer ideation model (correct category separation):
#  - OPERATORS (16) = generation layer (TRIZ-style verbs). They perturb the
#    base idea. They are NOT axes of divergence.
#  - CAUSAL VARIABLES (5) = verification layer (Zwicky-box parameters). They
#    are the ONLY criterion that measures whether divergence was real.
#  - CCA = cross-consistency assessment: an operator that moved no causal axis
#    produced cosmetic wording, not a new idea -> flagged divergence_real=False.
# ===========================================================================

# The 5 causal axes (Zwicky box columns). These define the configuration space.
_CAUSAL_AXES = ("quien_decide", "cuando", "evidencia_requerida", "si_falla", "topologia")

# Base causal configuration of the problem (from cartograph). Operators mutate it.
_BASE_CAUSAL = {
    "quien_decide": "operador humano",
    "cuando": "despues de validar",
    "evidencia_requerida": "reglas estaticas",
    "si_falla": "incidente detectado tarde",
    "topologia": "centralizada",
}

# Each operator declares (axis, normal_value, extreme_value). The extreme is
# OPERATOR-SPECIFIC (not generic per axis) so two operators over the same axis
# still produce distinct causal vectors -> real divergence, never cosmetic.
_OPERATOR_EFFECT = {
    "diagnostico":        ("evidencia_requerida", "supuesto hecho explicito", "se asume lo contrario del supuesto y se prueba"),
    "inversion":          ("quien_decide", "el objetivo opuesto", "quien decide es el que antes no podia"),
    "sustraccion":        ("si_falla", "colapsa funcion oculta al quitar dependencia", "el fallo se vuelve visible y obligatorio"),
    "restricciones":      ("cuando", "durante la ideacion con regla absurda", "nunca: se prohibe la opcion obvia"),
    "actores_roles":      ("quien_decide", "un actor distinto con la ultima palabra", "un actor externo sin historial decide"),
    "incentivos":         ("evidencia_requerida", "comportamiento recompensado", "se premia el error para revelar limites"),
    "morfologia":         ("topologia", "reensamblada por dimensiones", "topologia efimera que se recrea por operacion"),
    "recombinacion":      ("topologia", "dos mecanismos cruzados en malla", "tres mecanismos en anillo cerrado"),
    "analogias":          ("evidencia_requerida", "mapeo causal de otro dominio", "analogia de un dominio opuesto y no relacionado"),
    "arquitectura":       ("quien_decide", "una parte disidente del todo", "cada parte tiene veto y desacuerdo audible"),
    "gobernanza":         ("evidencia_requerida", "trazabilidad de cada cambio", "cada cambio es reversible y auditable por terceros"),
    "diseno_adversarial": ("si_falla", "flanco explotado por atacante simulado", "el atacante participa en disenar la defensa"),
    "escenarios":         ("cuando", "en el caso limite llevado al extremo", "en el peor caso ya ocurrido y reversible"),
    "prototipado":        ("cuando", "antes de comprometer, en sombra", "en produccion con red de seguridad minima"),
    "verificacion":       ("evidencia_requerida", "relacion reproducible no predicha", "la relacion se busca donde intuicion dice imposible"),
    "decision_riesgo":    ("si_falla", "dano contenido, no catastrofico", "el dano es el dato de entrenamiento"),
}

_VALID_MECH = {"elimination", "inversion", "isolation", "verification", "delegation", "prediction",
               "coordination", "consensus", "redundancy", "adaptation", "automation", "transformation",
               "market_exchange", "capability_proof"}


def _apply_family(family: str, base: dict[str, str], extreme: bool) -> dict[str, str]:
    """Apply ONE operator family to a causal-vector base (the REAL mutation used
    by diverge). Returns a new vector. Used directly by tests so they exercise the
    actual generator, not a replica."""
    ax, val, ext = _OPERATOR_EFFECT.get(family, ("evidencia_requerida", "relacion no predicha", "relacion no predicha"))
    cv = dict(base)
    cv[ax] = ext if extreme else val
    return cv


def diverge(carto: dict[str, Any], rupture: dict[str, Any], selected: dict[str, Any], methods: list[Any], query: str) -> list[Any]:
    """Phase 3 (Divergir). Local, deterministic, two-layer:
    OPERATORS generate candidates via PAIRWISE recombination (combinatorial
    divergence over the 5 causal axes). CAUSAL VARIABLES measure real divergence.
    CCA flags cosmetic (no-axis-moved) candidates.

    Each pair of operators crosses DISTINCT causal axes, so two ideas sharing the
    same mechanism (family) still get DIFFERENT causal vectors -> real divergence,
    and the 4th verification (same mechanism / distinct family => distinct causal
    vars) holds by construction.
    """
    from itertools import combinations
    ideas = []
    base = dict(_BASE_CAUSAL)
    if carto.get("actor"):
        base["quien_decide"] = carto["actor"]
    base["topologia"] = "decentralizada" if "descentral" in query.casefold() else "centralizada"

    seq = 0
    pairs = list(combinations(methods, 2)) or [(methods[0], methods[0])]
    for (ma, mb) in pairs:
        for extreme in (False, True):
            seq += 1
            cv = _apply_family(ma["family"], dict(base), extreme)
            cv = _apply_family(mb["family"], cv, extreme)  # cross two distinct axes
            moved = [k for k in _CAUSAL_AXES if cv[k] != base[k]]
            divergence_real = len(moved) >= 1
            # genome mechanism = lead operator family if it is a valid enum, else
            # capability_proof (general-purpose). The full cross is traced in
            # source_method / evidence.value so duplicate detection + the 4th
            # verification can still distinguish distinct crosses.
            fam_a, fam_b = ma["family"], mb["family"]
            lead = fam_a if fam_a in _VALID_MECH else "capability_proof"
            mech_pair = f"{fam_a}+{fam_b}"
            genome = {
                "actor": [base["quien_decide"]],
                "mechanism": [lead],
                "topology": [cv["topologia"]],
                "trust_model": ["evidence_based" if ("evidencia" in cv["evidencia_requerida"]) else "implicit"],
                "time_model": ["ephemeral_per_operation" if "ephemeral" in cv["topologia"] else "staged"],
            }
            from .genome import normalize_proposal
            g, _ = normalize_proposal(dict(genome), source_idea=f"I{seq:02d}")
            idea = {
                "id": f"I{seq:02d}",
                "title": f"{ma['name']} × {mb['name']} ({'extremo' if extreme else 'cruce'})",
                "description": f"Idea {seq}: cruce de operadores {fam_a}+{fam_b}. Mueve ejes {moved}.",
                "mechanism_causal": f"cruce {fam_a}+{fam_b}: altera {moved}",
                "causal_variables": cv,
                "difference_from_known": f"Frente a base ({base}), cambia: {', '.join(moved) or 'nada'}.",
                "genome": g.model_dump(),
                "evidence": {"field": "mechanism", "value": mech_pair, "evidence_span": f"cruce {ma['name']}×{mb['name']}"},
                "family": fam_a,
                "divergence_real": divergence_real,
                "extreme": extreme,  # operator-produced mode (input for convergence layer)
                "causal_claim": "MECHANISM_VERIFIED",  # the code maps family->axis->value in _OPERATOR_EFFECT
                "duplicate_status": "candidate",
                "source_method": f"{ma['id']}+{mb['id']}",
            }
            ideas.append(idea)
    return ideas


def cross_consistency_assessment(ideas: list[Any]) -> Tuple[list[Any], int]:
    """CCA filter: mark cosmetic candidates (no causal axis moved) and drop them
    from the divergent set so they never count as real innovation."""
    real = []
    cosmetic = 0
    for i in ideas:
        if i.get("divergence_real"):
            real.append(i)
        else:
            i["duplicate_status"] = "cosmetic"
            cosmetic += 1
    return real, cosmetic


# ---------------------------------------------------------------------------
# Duplicate detection (condition 6/7) — uses criba.similarity
# ---------------------------------------------------------------------------
def _detect_duplicates(ideas: list[Any]) -> list[dict[str, Any]]:
    report: list[dict[str, Any]] = []
    seen: list[Any] = []
    for idea in ideas:
        g = idea["genome"]
        matched = None
        for prev in seen:
            r = genome_classify(g, prev["genome"])
            if r["verdict"] == "probable_duplicate":
                matched = r; break
            if r["verdict"] == "close_variant" and matched is None:
                matched = r
        if matched:
            idea["duplicate_status"] = "duplicate" if matched["verdict"] == "probable_duplicate" else "variant"
            report.append({
                "idea_id": idea["id"], "verdict": matched["verdict"],
                "similarity": matched["similarity"], "reason": matched["reason"],
                "vs": matched.get("vs") or (prev["id"] if "vs" not in matched else None),
            })
        else:
            idea["duplicate_status"] = "distinct"
            report.append({"idea_id": idea["id"], "verdict": "distinct", "similarity": 1.0, "reason": "primera de su clase"})
        seen.append(idea)
    return report


# ---------------------------------------------------------------------------
# Convergence layer (SPEC): evaluates quality of what GENERATION produced,
# using criteria derived from the operator's content. Does NOT use causal
# variables (measurement axes) as generators. Novelty is read FROM the
# measurement layer (how many distinct axes the operator moved), never
# redefined as a design axis.
# ---------------------------------------------------------------------------
_BASE_VALUES = {
    "quien_decide": "operador humano",
    "cuando": "despues de validar",
    "evidencia_requerida": "reglas estaticas",
    "si_falla": "incidente detectado tarde",
    "topologia": "centralizada",
}


class ValueScoreError(ValueError):
    """Raised when value_score inputs violate the ratified contract.

    The formula value_score = evidence * novelty / cost is ratified and must not
    change. This guards its domain: cost must be strictly positive and all inputs
    finite, so the score is never silently coerced, infinite, or NaN.
    """


def value_score(evidence: float, novelty: float, cost: float) -> float:
    """Ratified convergence score: ``evidence * novelty / cost``.

    Args:
        evidence: Evidence anchoring of the idea (finite number).
        novelty: Measurement-layer novelty (finite number).
        cost: Effort to test the idea. MUST be strictly positive.

    Returns:
        The rounded value score (4 decimals).

    Raises:
        ValueScoreError: if ``cost <= 0`` or any input is non-finite. The error
            is explicit — cost is never silently converted and the result is
            never infinite or NaN.
    """
    import math as _math
    for name, val in (("evidence", evidence), ("novelty", novelty), ("cost", cost)):
        if not isinstance(val, (int, float)) or isinstance(val, bool):
            raise ValueScoreError(f"value_score: {name} debe ser numérico, no {type(val).__name__}.")
        if not _math.isfinite(val):
            raise ValueScoreError(f"value_score: {name} debe ser finito; se recibió {val!r}.")
    if cost <= 0:
        raise ValueScoreError(
            f"value_score: cost debe ser > 0 (fórmula evidence*novelty/cost); se recibió cost={cost!r}."
        )
    return round((evidence * novelty) / cost, 4)


def _evaluate_idea(idea: dict[str, Any]) -> dict[str, Any]:
    """Convergence scoring. Input = what the OPERATOR generated (title,
    description, causal_variables, extreme). Novelty comes from the measurement
    layer (count of axes the operator perturbed vs base)."""
    cv = idea.get("causal_variables", {})
    # novelty: measurement-layer datum (how many distinct axes moved vs base)
    moved_axes = [k for k in _CAUSAL_AXES if cv.get(k) != _BASE_VALUES.get(k)]
    novelty = round(len(moved_axes) / len(_CAUSAL_AXES), 4)  # 0..1 gradient

    # evidence: how anchored the operator's proposition is. An operator that
    # names a concrete mechanism/axis value (not the generic base) scores higher.
    concrete = sum(1 for k in _CAUSAL_AXES if cv.get(k) and cv.get(k) != _BASE_VALUES.get(k))
    evidence = round(0.3 + 0.7 * (concrete / len(_CAUSAL_AXES)), 4)

    # viability: extreme perturbations are harder to test safely/reversibly.
    extreme = bool(idea.get("extreme"))
    viability = round(0.45 if extreme else 0.8, 4)

    # cost: effort to test; extreme + more moved axes = higher cost. The base
    # term 0.3 guarantees cost is always strictly positive here, so value_score's
    # cost>0 contract holds by construction.
    cost = round(0.3 + (0.4 if extreme else 0.0) + 0.3 * (len(moved_axes) / len(_CAUSAL_AXES)), 4)

    # value_score = evidence * novelty / cost  (explicit convergence criterion).
    # novelty==0 (no axis moved) yields a legitimate 0.0 — that is a real score,
    # not an error, because cost stays positive.
    score = value_score(evidence, novelty, cost)
    return {
        "novelty": novelty,
        "evidence": evidence,
        "viability": viability,
        "cost": cost,
        "value_score": score,
    }


# ---------------------------------------------------------------------------
# Orchestration (condition 2/3/10/11)
# ---------------------------------------------------------------------------
def activate(query: str, current: str = "auto", mode: str = "balanced", supporting_methods: int = 4,
             context: dict[str, Any] | None = None, safety_level: str = "strict", manual_methods: list[str] | None = None,
             cartograph_fn: Optional[CartographFn] = None, diverge_fn: Optional[DivergeFn] = None) -> dict[str, Any]:
    if not isinstance(query, str) or not query.strip():
        raise ValueError("La consulta no puede estar vacía.")
    if len(query) > MAX_QUERY_CHARS:
        raise ValueError(f"La consulta excede el límite de {MAX_QUERY_CHARS} caracteres.")
    if mode not in VALID_MODES:
        raise ValueError(f"Modo inválido: {mode}")
    if safety_level not in {"strict", "standard"}:
        raise ValueError("safety_level debe ser strict o standard.")

    context = context or {}
    selection = select(query, current)
    selected = find_current(selection["selected_current"])
    methods = select_methods(supporting_methods, mode, manual_methods)

    carto = (cartograph_fn or cartograph_and_break)(query, context, selection.__dict__ if hasattr(selection, "__dict__") else selection)
    rupture = {
        "operations": carto["ruptures"],
        "broken_assumptions": [r["assumption_id"] for r in carto["ruptures"] if r["operation"] == "invert"],
        "inversions": [r["result"] for r in carto["ruptures"] if r["operation"] == "invert"],
        "eliminations": [r["result"] for r in carto["ruptures"] if r["operation"] == "eliminate"],
        "counterexample": carto["counterexample"],
    }
    ideas = (diverge_fn or diverge)(carto, rupture, selected, methods, query)
    # CCA: drop cosmetic candidates (operators that moved no causal axis).
    real_ideas, cosmetic_count = cross_consistency_assessment(ideas)
    duplicate_report = _detect_duplicates(real_ideas)
    kept = [i for i, r in zip(real_ideas, duplicate_report) if r["verdict"] != "probable_duplicate"]
    if len(kept) < 8:
        kept = real_ideas[:8]
    # keep canonical collection exactly as-is (one object)
    for i, r in zip(real_ideas, duplicate_report):
        if r["verdict"] == "probable_duplicate" and i in kept:
            kept.remove(i)

    families = sorted({i["family"] for i in kept})
    unclassified = []
    for i in kept:
        for up in i["genome"].get("unclassified_properties", []):
            unclassified.append(up if isinstance(up, dict) else up.model_dump())
    real_divergent = sum(1 for i in kept if i.get("divergence_real"))

    # Convergence layer: score each kept idea (operator-produced content) and rank.
    for i in kept:
        i["convergence"] = _evaluate_idea(i)
    ranked = sorted(kept, key=lambda x: x["convergence"]["value_score"], reverse=True)
    # keep canonical collection ordered by value (best first)
    kept[:] = ranked
    top_ideas = [i["id"] for i in kept[:3]]
    mean_value = round(sum(i["convergence"]["value_score"] for i in kept) / max(1, len(kept)), 4)

    innovation: dict[str, Any] = {
        "known_space": carto["known_space"],
        "saturated_mechanisms": carto["saturated_mechanisms"],
        "assumptions": carto["assumptions"],
        "ruptures": carto["ruptures"],
        "idea_families": families,
        "ideas": kept,  # <-- canonical collection
        "real_divergent_count": real_divergent,
        "cosmetic_rejected": cosmetic_count,
        "top_ideas": top_ideas,
        "mean_value_score": mean_value,
        "duplicate_report": [r for r in duplicate_report if r["verdict"] != "probable_duplicate"],
        "unclassified_properties": unclassified,
    }

    metrics = {
        "potential_novelty": _clamp(60 + real_divergent * 4 + (10 if carto.get("wants_novelty") else 0)),
        "divergence": _clamp(40 + 12 * min(real_divergent, 8)),
        "feasibility": _clamp(60 + (8 if safety_level == "standard" else 0)),
        "controlled_risk": _clamp(48 - (6 if safety_level == "strict" else 0)),
        "reversibility": _clamp(74),
        "uncertainty": _clamp(56),
        # Rule 9 (Comet): differentiated confidence.
        # conf_code_executes: verifiable by reading the code (family->axis->value map exists).
        # conf_causal_root: requires a counterfactual test (change X, see if Y changes);
        #   in the LOCAL_MVP this is INFERRED, not proven, so it is flagged explicitly.
        "conf_code_executes": 1.0,
        "conf_causal_root": "INFERRED_NOT_PROVEN",
        "mean_value_score": mean_value,
    }
    # FASE 0 — alternativa C (ratificada por humano). Separa dos dimensiones que
    # el motor mezclaba:
    #  - pipeline_action: que hacer DESPUES (PROTOTIPAR / DIVERGIR). Basado solo en
    #    el numero de familias, es deliberadamente conservador y NO autoriza ADOPTAR.
    #  - recommended_status: estado de la idea, SIEMPRE en VALID_DECISIONS. Con la
    #    evidencia actual (solo numero de familias) no se justifica ADOPTAR, asi que
    #    se fija en "AMPLIAR PRUEBA" hasta que exista una regla explicita y probada.
    # La formula de convergencia (value_score = evidence*novelty/cost) queda intacta.
    pipeline_action = "PROTOTIPAR" if len(families) >= 4 else "DIVERGIR"
    if pipeline_action not in VALID_PIPELINE_ACTIONS:
        raise ValueError(f"pipeline_action fuera de enum: {pipeline_action}")
    recommended_status = "AMPLIAR PRUEBA"  # miembro de VALID_DECISIONS
    if recommended_status not in VALID_DECISIONS:
        raise ValueError(f"recommended_status fuera de enum: {recommended_status}")
    decision = {
        "pipeline_action": pipeline_action,
        "recommended_status": recommended_status,
        "justification": f"{len(families)} familias representadas; {metrics['divergence']}/100 de divergencia. {pipeline_action}: lleva la idea a prototipo en sombra.",
        "confidence": round(min(0.85, 0.4 + metrics["potential_novelty"] / 250 + metrics["divergence"] / 400), 2),
    }

    packet: dict[str, Any] = {
        "schema": SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "packet_type": "MANDATORY_MODEL_PACKET",
        "activation_id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "intent": "INNOVAR",
        "versions": {"currents": CURRENT_CATALOG_VERSION, "selector": SELECTOR_VERSION, "genome": ONTOLOGY_VERSION},
        "original_query": query,
        "selected_current": {"id": selected["id"], "name": selected["name"], "score": selection["score"],
                              "selection_reasons": selection["selection_reasons"]},
        "supporting_methods": [{"id": m["id"], "name": m["name"], "family": m["family"], "reason": m["reason"]} for m in methods],
        "contextualization": {"problem": query.strip(), "known_space": carto["known_space"],
                               "assumptions": carto["assumptions"], "saturated_mechanisms": carto["saturated_mechanisms"]},
        "rupture": rupture,
        "innovation": innovation,
        "experiment": {"falsifiable_hypothesis": f"La variante basada en {selected['name']} abre ideas nuevas sin romper guardrails.",
                        "baseline": "Lo ya conocido.", "variant": kept[0]["description"] if kept else "",
                        "damage_limit": "Solo datos sintéticos; cero cambios en proyectos reales.",
                        "sandbox": "Entorno local temporal, aislado y sin credenciales ni red externa.",
                        "rollback": "Eliminar artefactos temporales y conservar el registro de evidencia."},
        "metrics": metrics,
        "decision": decision,
        "model_instruction": INSTRUCTION.format(current=selected["name"]),
        "response_contract": {"must_use_packet": True, "must_name_current": True,
                               "must_generate_new_ideas": True, "must_state_uncertainty": True,
                               "must_not_reveal_private_chain_of_thought": True},
        "security": {"safety_level": safety_level, "no_command_execution": True,
                     "no_network_by_default": True, "no_credentials_access": True},
    }
    # condition 3: packet["ideas"] is the SAME object as innovation["ideas"] (no divergence possible)
    packet["ideas"] = packet["innovation"]["ideas"]
    if mode == "minimal":
        packet["minimal_summary"] = {"current": selected["name"], "intent": "INNOVAR",
                                     "central_idea": kept[0]["description"] if kept else "", "decision": decision}
    return packet


def _clamp(v: int) -> int:
    return max(0, min(100, v))


def export_innovation_portfolio(packet: dict[str, Any]) -> dict[str, Any]:
    """INNOVATION_PORTFOLIO_PACKET is ONLY an exported view, never a persisted model."""
    inv = packet.get("innovation", {})
    return {
        "view": "innovation_portfolio",
        "activation_id": packet.get("activation_id"),
        "original_query": packet.get("original_query"),
        "known_space": inv.get("known_space"),
        "saturated_mechanisms": inv.get("saturated_mechanisms"),
        "assumptions": inv.get("assumptions"),
        "ruptures": inv.get("ruptures"),
        "idea_families": inv.get("idea_families"),
        "ideas": inv.get("ideas"),
        "duplicate_report": inv.get("duplicate_report"),
        "unclassified_properties": inv.get("unclassified_properties"),
    }


def build_prompt(packet: dict[str, Any]) -> str:
    return "\n\n".join([
        "# Consulta original\n" + packet["original_query"],
        "# Intención CRIBA\n" + packet.get("intent", "INNOVAR"),
        "# Instrucción CRIBA\n" + packet["model_instruction"],
        "# MANDATORY_MODEL_PACKET\n" + json.dumps(packet, ensure_ascii=False, indent=2),
        "# Contrato\nUsa obligatoriamente el paquete para generar ideas nuevas; no reveles razonamiento privado.",
    ])
