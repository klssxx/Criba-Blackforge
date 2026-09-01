"""Context Layer — InnovationContext & BlackforgeContext (HIPERMEGAPROMPT §2).

Pydantic models that capture the structured representation of a problem before
generation, evaluation, or adversarial analysis begins.  The context builder
bridges the existing engine output (cartograph_and_break, selector) with the
new layered architecture.
"""
from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, model_validator

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class OperatingMode(str, Enum):
    CRIBA = "criba"
    BLACKFORGE = "blackforge"


class ContextIntegrityStatus(str, Enum):
    COMPLETE = "complete"
    PARTIAL = "partial"
    INCOMPLETE = "incomplete"


# ---------------------------------------------------------------------------
# InnovationContext
# ---------------------------------------------------------------------------

class InnovationContext(BaseModel):
    """Structured representation of a problem (HIPERMEGAPROMPT §2.2).

    Every idea produced by the engine must retain a reference to its
    ``context_id`` for traceability.
    """

    context_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    mode: OperatingMode = OperatingMode.CRIBA

    # Original query
    original_query: str
    normalized_query: str = ""
    central_problem: str = ""
    desired_outcome: str = ""

    # Domain
    primary_domain: str = "general"
    secondary_domains: list[str] = Field(default_factory=list)
    detected_intent: str = ""

    # Actors & entities
    actors: list[str] = Field(default_factory=list)
    affected_entities: list[str] = Field(default_factory=list)
    available_resources: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    unknowns: list[str] = Field(default_factory=list)

    # Known space
    known_solutions: list[str] = Field(default_factory=list)
    known_failures: list[str] = Field(default_factory=list)
    dominant_paradigms: list[str] = Field(default_factory=list)
    unexplored_zones: list[str] = Field(default_factory=list)

    # Operator selection
    selected_operators: list[str] = Field(default_factory=list)
    operator_selection_reasons: dict[str, str] = Field(default_factory=dict)

    # Evaluation
    evaluation_criteria: dict[str, float] = Field(default_factory=dict)
    source_evidence: list[dict[str, Any]] = Field(default_factory=list)
    previous_ideas: list[dict[str, Any]] = Field(default_factory=list)

    # Safety & trace
    safety_boundaries: list[str] = Field(default_factory=list)
    trace_log: list[dict[str, Any]] = Field(default_factory=list)

    # Metadata
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    @model_validator(mode="after")
    def _auto_normalize(self) -> InnovationContext:
        """Auto-fill normalized_query from original_query if empty."""
        if not self.normalized_query and self.original_query:
            self.normalized_query = self.original_query.strip().lower()
        return self


# ---------------------------------------------------------------------------
# BlackforgeContext
# ---------------------------------------------------------------------------

class BlackforgeContext(InnovationContext):
    """Extended context for security / BLACKFORGE pipeline (§2.4).

    Inherits all InnovationContext fields and adds security-specific
    dimensions: assets, threats, surfaces, boundaries, authorization,
    evidence, impact, and legal constraints.
    """

    mode: OperatingMode = OperatingMode.BLACKFORGE

    # Protected assets
    protected_assets: list[str] = Field(default_factory=list)
    crown_jewels: list[str] = Field(default_factory=list)
    architecture_components: list[str] = Field(default_factory=list)
    data_flows: list[str] = Field(default_factory=list)

    # Threat actors
    threat_actors: list[str] = Field(default_factory=list)
    attacker_goals: list[str] = Field(default_factory=list)
    attacker_capabilities: list[str] = Field(default_factory=list)
    assumed_access_level: str = ""

    # Attack surfaces
    attack_surfaces: list[str] = Field(default_factory=list)
    trust_boundaries: list[str] = Field(default_factory=list)
    entry_vectors: list[str] = Field(default_factory=list)
    attack_paths: list[str] = Field(default_factory=list)

    # Defender capabilities
    defender_capabilities: list[str] = Field(default_factory=list)
    existing_controls: list[str] = Field(default_factory=list)
    control_limitations: list[str] = Field(default_factory=list)
    detection_capabilities: list[str] = Field(default_factory=list)
    response_capabilities: list[str] = Field(default_factory=list)
    recovery_capabilities: list[str] = Field(default_factory=list)

    # Assessment
    assessment_type: str = ""
    testing_methodology: list[str] = Field(default_factory=list)
    authorization_scope: str = ""
    in_scope_targets: list[str] = Field(default_factory=list)
    out_of_scope_targets: list[str] = Field(default_factory=list)
    permitted_techniques: list[str] = Field(default_factory=list)
    prohibited_techniques: list[str] = Field(default_factory=list)
    rules_of_engagement: list[str] = Field(default_factory=list)
    stop_conditions: list[str] = Field(default_factory=list)

    # Vulnerabilities
    vulnerability_classes: list[str] = Field(default_factory=list)
    suspected_weaknesses: list[str] = Field(default_factory=list)
    validated_findings: list[str] = Field(default_factory=list)
    false_positive_risks: list[str] = Field(default_factory=list)
    exploitability_conditions: list[str] = Field(default_factory=list)
    impact_scenarios: list[str] = Field(default_factory=list)

    # Evidence
    evidence_available: list[str] = Field(default_factory=list)
    evidence_required: list[str] = Field(default_factory=list)
    reproducibility_requirements: list[str] = Field(default_factory=list)
    validation_requirements: list[str] = Field(default_factory=list)
    retest_requirements: list[str] = Field(default_factory=list)

    # Risk
    business_impact: list[str] = Field(default_factory=list)
    technical_impact: list[str] = Field(default_factory=list)
    residual_risks: list[str] = Field(default_factory=list)
    likelihood_factors: list[str] = Field(default_factory=list)
    severity_model: str = ""

    # Legal & privacy
    defensive_purpose: str = ""
    authorized_environment: bool = False
    legal_boundaries: list[str] = Field(default_factory=list)
    privacy_constraints: list[str] = Field(default_factory=list)
    misuse_risk: str = ""
    safe_execution_requirements: list[str] = Field(default_factory=list)

    # References
    security_references: list[str] = Field(default_factory=list)
    mapped_frameworks: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Context integrity
# ---------------------------------------------------------------------------

class ContextIntegrityReport(BaseModel):
    """Result of validating a context's completeness (§2.7)."""

    status: ContextIntegrityStatus
    confirmed_data: list[str] = Field(default_factory=list)
    provided_sources: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    unknowns: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    prohibited_inferences: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Domain detection (reused from engine.py cartograph_and_break)
# ---------------------------------------------------------------------------

_DOMAIN_KEYWORDS: dict[str, list[str]] = {
    "seguridad": ["seguridad", "ataque", "vulnerabilidad", "amenaza", "proteger", "defensa"],
    "tecnologia": ["api", " software", "sistema", "codigo", "algoritmo", "red"],
    "negocio": ["negocio", "mercado", "cliente", "empresa", "ventas", "churn"],
    "ia": ["ia", "inteligencia artificial", "machine learning", "modelo"],
    "gobernanza": ["gobernanza", "dao", "organizacion", "equipo", "coordinar"],
    "etica": ["etica", "sesgo", "justo", "equidad", "niños"],
    "salud": ["salud", "medico", "hospital", "paciente"],
    "educacion": ["educacion", "aprendizaje", "estudiante", "escuela"],
    "transporte": ["transporte", "movilidad", "vehiculo", "logistica"],
    "energia": ["energia", "consumo", "edificio", "sostenible"],
    "alimentos": ["alimento", "supermercado", "desperdicio", "cadena"],
    "recursos_humanos": ["trabajo", "descanso", "turno", "jornada"],
}


def _keyword_matches(query_lower: str, keyword: str) -> bool:
    """Check if keyword appears in query at word boundaries."""
    # Keywords starting with space (e.g. " software") are substring-matched directly
    # Short keywords (< 4 chars) use word-boundary regex to avoid false positives
    if len(keyword) < 4 and not keyword.startswith(" "):
        pattern = r"(?:^|[\s\.,;:!?¿¡\-])(?:" + re.escape(keyword) + r")(?:$|[\s\.,;:!?¿¡\-])"
        return bool(re.search(pattern, query_lower))
    return keyword in query_lower


def detect_domain(query: str) -> str:
    """Classify query into one of 12 domains (mirrors engine.py logic)."""
    q = query.casefold()
    for domain, keywords in _DOMAIN_KEYWORDS.items():
        if any(_keyword_matches(q, w) for w in keywords):
            return domain
    return "general"


# ---------------------------------------------------------------------------
# Context builder
# ---------------------------------------------------------------------------

def _extract_actors(query: str) -> list[str]:
    """Extract likely actors from query text."""
    q = query.casefold()
    actors: list[str] = []
    actor_signals = {
        "usuarios/destinatarios finales": ("usuario", "cliente", "persona", "gente", "equipo"),
        "organizacion/implementadores": ("empresa", "organizacion", "equipo"),
        "adversario/amenaza externa": ("atacante", "adversario", "amenaza"),
        "regulador/autoridad": ("regulador", "normativa", "ley"),
    }
    for label, keywords in actor_signals.items():
        if any(w in q for w in keywords):
            actors.append(label)
    return actors or ["stakeholders no identificados"]


def _extract_assumptions(domain: str, key_concept: str) -> list[str]:
    """Extract domain-specific dominant assumptions."""
    assumptions_map: dict[str, list[str]] = {
        "seguridad": [
            f"La defensa típica contra '{key_concept}' usa reglas estáticas.",
            "Se asume que el atacante sigue patrones conocidos.",
            "Más capas de defensa siempre reducen el riesgo.",
        ],
        "negocio": [
            f"La solución dominante para '{key_concept}' es incremental.",
            "Se asume que más features = más valor para el cliente.",
            "El modelo de negocio actual es el único viable.",
        ],
        "tecnologia": [
            f"La arquitectura actual de '{key_concept}' es la correcta.",
            "Se asume que más automatización siempre reduce el error.",
            "La escalabilidad se logra añadiendo más recursos.",
        ],
        "ia": [
            f"El modelo actual de '{key_concept}' captura la realidad.",
            "Se asume que más datos = mejor rendimiento.",
            "La explicabilidad es compatible con la complejidad.",
        ],
    }
    return assumptions_map.get(domain, [
        f"La solución estándar para '{key_concept}' es suficiente.",
        "Se asume que el enfoque actual es el correcto.",
    ])


def build_context(
    query: str,
    engine_output: dict[str, Any] | None = None,
    mode: str = "criba",
    *,
    selection: dict[str, Any] | None = None,
) -> InnovationContext:
    """Build an InnovationContext from a raw query and optional engine output.

    Parameters
    ----------
    query : str
        The user's original query.
    engine_output : dict, optional
        Output from ``cartograph_and_break()`` if available.
    mode : str
        ``"criba"`` or ``"blackforge"``.
    selection : dict, optional
        Output from ``selector.select()`` if available.

    Returns
    -------
    InnovationContext
        Fully populated context ready for persona/ensemble analysis.
    """
    domain = detect_domain(query)
    q_lower = query.strip().lower()
    key_concept = q_lower.split()[0] if q_lower.split() else "el problema"

    carto = engine_output or {}
    known_space = carto.get("known_space", [])
    ruptures = carto.get("ruptures", [])
    actors = carto.get("actors") or _extract_actors(query)
    assets = carto.get("assets", [])
    constraints_raw = carto.get("constraints", [])
    assumptions = carto.get("assumptions") or _extract_assumptions(domain, key_concept)

    # Determine desired_outcome from query intent
    desired = ""
    intent_q = q_lower
    if any(w in intent_q for w in ("mejor", "optimiz", "mejorar")):
        desired = "Mejora del estado actual"
    elif any(w in intent_q for w in ("innov", "nuev", "disrupt", "alternativa")):
        desired = "Generación de alternativas innovadoras"
    elif any(w in intent_q for w in ("analiz", "evalu", "compar")):
        desired = "Análisis comparativo fundamentado"
    elif any(w in intent_q for w in ("resolv", "solucion", "arregl")):
        desired = "Resolución del problema planteado"
    else:
        desired = "Exploración y orientación estratégica"

    # Operator selection from selection output or empty
    operators: list[str] = []
    op_reasons: dict[str, str] = {}
    if selection:
        sel_current = selection.get("selected_current", "")
        if sel_current:
            operators.append(sel_current)
            op_reasons[sel_current] = selection.get("selection_reasons", [""])[0] if selection.get("selection_reasons") else ""

    return InnovationContext(
        mode=OperatingMode(mode) if mode in ("criba", "blackforge") else OperatingMode.CRIBA,
        original_query=query,
        normalized_query=query.strip().lower(),
        central_problem=f"Problema detectado en dominio '{domain}': {key_concept}",
        desired_outcome=desired,
        primary_domain=domain,
        actors=actors if isinstance(actors, list) else [str(actors)],
        affected_entities=assets if isinstance(assets, list) else [],
        constraints=constraints_raw if isinstance(constraints_raw, list) else [],
        assumptions=assumptions,
        unknowns=carto.get("unknowns", []),
        known_solutions=known_space if isinstance(known_space, list) else [],
        known_failures=[r.get("result", "") for r in ruptures if isinstance(r, dict)] if isinstance(ruptures, list) else [],
        dominant_paradigms=[a for a in assumptions[:3]] if assumptions else [],
        selected_operators=operators,
        operator_selection_reasons=op_reasons,
        safety_boundaries=["No inventar datos", "No confundir hechos con hipótesis"],
    )


def extend_for_blackforge(ctx: InnovationContext) -> BlackforgeContext:
    """Extend an InnovationContext into a BlackforgeContext (§2.4).

    Copies all base fields and adds empty Blackforge-specific dimensions
    that must be populated by the user or a Blackforge pipeline step.
    """
    data = ctx.model_dump()
    data["mode"] = OperatingMode.BLACKFORGE
    return BlackforgeContext(**data)


def validate_context_integrity(ctx: InnovationContext) -> ContextIntegrityReport:
    """Validate completeness of a context (§2.7).

    Returns a report indicating which fields are confirmed, assumed,
    unknown, or missing.
    """
    confirmed: list[str] = []
    assumptions: list[str] = []
    unknowns: list[str] = []
    missing: list[str] = []

    # Core fields
    if ctx.original_query:
        confirmed.append("original_query")
    else:
        missing.append("original_query")

    if ctx.central_problem:
        confirmed.append("central_problem")
    else:
        missing.append("central_problem")

    if ctx.primary_domain and ctx.primary_domain != "general":
        confirmed.append("primary_domain")
    else:
        unknowns.append("primary_domain (general fallback)")

    if ctx.actors and ctx.actors != ["stakeholders no identificados"]:
        confirmed.append("actors")
    else:
        unknowns.append("actors (generic fallback)")

    if ctx.assumptions:
        assumptions.extend(ctx.assumptions)

    if ctx.unknowns:
        unknowns.extend(ctx.unknowns)

    if ctx.known_solutions:
        confirmed.append("known_solutions")
    else:
        missing.append("known_solutions (no cartography available)")

    # Determine overall status
    missing_count = len(missing)
    if missing_count == 0:
        status = ContextIntegrityStatus.COMPLETE
    elif missing_count <= 2:
        status = ContextIntegrityStatus.PARTIAL
    else:
        status = ContextIntegrityStatus.INCOMPLETE

    return ContextIntegrityReport(
        status=status,
        confirmed_data=confirmed,
        assumptions=assumptions,
        unknowns=unknowns,
        missing_information=missing,
        prohibited_inferences=[
            "No inventar fuentes",
            "No confundir inferencia con hecho",
            "No declarar novedad sin verificación",
        ],
    )
