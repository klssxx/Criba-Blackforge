"""Independent persona contracts for the CRIBA/Blackforge P2 layer.

The module deliberately separates four analytical architectures instead of
creating four stylistic variants of the same response.  It is usable without a
model: the deterministic fallback preserves the complete contract and labels
its epistemic status as inferred.  A later ensemble may consume these results,
but no persona receives another persona's output here.
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from enum import Enum
from typing import Any, Final, Literal, Protocol, TypeAlias

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)

from .constraints import FindingConfidence
from .engine import build_prompt as build_engine_prompt
from .llm_adapter import NoneBackend, build_llm_prompt

PERSONAS_SCHEMA_VERSION: Final[str] = "1.0.0"
PersonaId: TypeAlias = Literal["A", "B", "C", "D"]
AuthorizationStatus: TypeAlias = Literal["pending", "granted", "denied", "expired", "not_required"]
PERSONA_IDS: Final[tuple[PersonaId, PersonaId, PersonaId, PersonaId]] = ("A", "B", "C", "D")
_ISOLATION_EXCLUDED_PACKET_KEYS: Final[frozenset[str]] = frozenset({
    "persona_outputs",
    "prior_persona_outputs",
    "ensemble_outputs",
    "minority_report",
    "synthesis",
})


class PersonaContract(BaseModel):
    """Strict base for an approved persona output schema."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class PersonaA(PersonaContract):
    """System and product architecture contract (§1.3)."""

    current_structure: str
    structural_problem: str
    root_component: str
    proposed_change: str
    shared_or_specialized: str
    affected_modules: list[str]
    interfaces: list[str]
    state_changes: list[str]
    persistence_changes: list[str]
    migration: str
    failure_modes: list[str]
    simpler_alternative: str
    evidence_required: list[str]
    recommendation: str


class PersonaB(PersonaContract):
    """Innovation and known-space mapping contract (§1.4)."""

    known_space: list[str]
    dominant_paradigms: list[str]
    shared_assumptions: list[str]
    unresolved_gaps: list[str]
    operators_selected: list[str]
    structural_directions: list[str]
    mechanism_diversity: list[str]
    novelty_status: str
    technical_translation: str
    strongest_direction: str
    strongest_counterargument: str
    validation_needed: list[str]


class PersonaC(PersonaContract):
    """Evidence, quality, and reliability contract (§1.5)."""

    confirmed_facts: list[str]
    inferred_claims: list[str]
    unsupported_claims: list[str]
    evidence_quality: str
    conflicting_evidence: list[str]
    confidence: FindingConfidence
    falsification_tests: list[str]
    pass_fail_criteria: list[str]
    reproducibility: str
    traceability_gaps: list[str]
    risk_of_wrong_decision: str
    recommendation: str

    @model_validator(mode="after")
    def confirmed_requires_evidence(self) -> PersonaC:
        """Prevent an unsupported CONFIRMED claim from entering the pipeline."""
        if self.confidence == FindingConfidence.CONFIRMED and not self.confirmed_facts:
            raise ValueError("confidence=confirmed requires non-empty confirmed_facts")
        return self


class PersonaD(PersonaContract):
    """Adversarial, security, and operations contract (§1.6)."""

    assets: list[str]
    threat_actors: list[str]
    attack_surfaces: list[str]
    trust_boundaries: list[str]
    attack_hypotheses: list[str]
    existing_controls: list[str]
    likely_bypasses: list[str]
    detection: str
    containment: str
    recovery: str
    evidence_status: str
    authorization_status: AuthorizationStatus
    residual_risk: str
    recommendation: str


PersonaOutput: TypeAlias = PersonaA | PersonaB | PersonaC | PersonaD


class PersonaConfidence(str, Enum):
    """Confidence label for the provenance of a persona result."""

    INFERRED = "inferred"
    UNVERIFIED = "unverified"


class PersonaSource(str, Enum):
    """Origin of a persona output."""

    LLM = "llm"
    DETERMINISTIC_FALLBACK = "deterministic_fallback"


class PersonaResult(BaseModel):
    """Versioned, attributable result of one isolated persona analysis."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0.0"] = "1.0.0"
    persona_id: PersonaId
    persona_name: str
    output_contract: str
    output: PersonaOutput
    confidence: PersonaConfidence
    source: PersonaSource
    packet_fingerprint: str
    prompt_fingerprint: str
    fallback_reason: str | None = None

    @model_validator(mode="after")
    def output_must_match_persona(self) -> PersonaResult:
        """Make a contract mismatch impossible even though outputs form a union."""
        expected: dict[PersonaId, type[PersonaOutput]] = {
            "A": PersonaA,
            "B": PersonaB,
            "C": PersonaC,
            "D": PersonaD,
        }
        if not isinstance(self.output, expected[self.persona_id]):
            raise ValueError(f"persona {self.persona_id} received the wrong output contract")
        return self


class CompositePersonaDimensions(BaseModel):
    """The simultaneous dimensions of the composite persona (§1.2)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    value_and_incentives: str = "Valor, coste de oportunidad e incentivos"
    human_and_organizational_behavior: str = "Comportamiento humano y organizativo"
    evidence_probability_and_risk: str = "Evidencia, probabilidad y riesgo residual"


class TeamProtocol(BaseModel):
    """Non-negotiable coordination contract for a four-persona pass (§1.8)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    independent_first_pass: Literal[True] = True
    shared_context: Literal[True] = True
    shared_task: Literal[True] = True
    shared_constraints: Literal[True] = True
    separate_analysis: Literal[True] = True
    normalized_output: Literal[True] = True
    synthesis_after_completion: Literal[True] = True
    minority_report_required: Literal[True] = True


DEFAULT_TEAM_PROTOCOL: Final[TeamProtocol] = TeamProtocol()
DEFAULT_COMPOSITE_DIMENSIONS: Final[CompositePersonaDimensions] = CompositePersonaDimensions()


class MinorityReport(BaseModel):
    """A preserved dissenting view required whenever recommendations differ."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    dissenting_persona_ids: list[PersonaId] = Field(min_length=1)
    disagreement: str = Field(min_length=1)
    evidence_needed: list[str] = Field(min_length=1)
    impact_on_recommendation: str = Field(min_length=1)

    @field_validator("dissenting_persona_ids")
    @classmethod
    def dissenters_are_unique(cls, value: list[PersonaId]) -> list[PersonaId]:
        """Keep minority attribution deterministic and unambiguous."""
        if len(set(value)) != len(value):
            raise ValueError("dissenting_persona_ids must not contain duplicates")
        return value


class PersonaDiversityReport(BaseModel):
    """Result of the P2 anti-voice-repetition check."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    is_diverse: bool
    reason: Literal["distinct_persona_contributions", "identical_semantic_contributions", "insufficient_personas"]
    semantic_fingerprints: dict[PersonaId, str] = Field(default_factory=dict)


class TeamProtocolValidation(BaseModel):
    """Whether the coordination contract preserves required dissent."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    is_valid: bool
    requires_minority_report: bool
    reason: str


class PersonaDefinition(BaseModel):
    """Static analytical architecture used to construct each persona prompt."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    persona_id: PersonaId
    name: str
    output_contract: str
    specialty: str
    mandatory_questions: tuple[str, ...]
    avoid: tuple[str, ...]


_PERSONA_DEFINITIONS: Final[dict[PersonaId, PersonaDefinition]] = {
    "A": PersonaDefinition(
        persona_id="A",
        name="Arquitecto sistémico y de producto",
        output_contract="system_architect_output",
        specialty="arquitectura, contratos, estados, persistencia, migración y rollback",
        mandatory_questions=(
            "¿Qué estructura produce el comportamiento actual?",
            "¿Qué componente causa realmente el fallo?",
            "¿La mejora pertenece al núcleo, extensión u orquestación?",
            "¿Qué evidencia demostraría que funciona?",
        ),
        avoid=(
            "rediseños totales innecesarios",
            "abstracciones sin necesidad",
            "cambios sin migración ni pruebas",
        ),
    ),
    "B": PersonaDefinition(
        persona_id="B",
        name="Arquitecto de innovación y cartógrafo del espacio",
        output_contract="innovation_architect_output",
        specialty="espacio conocido, supuestos, operadores y diversidad de mecanismos",
        mandatory_questions=(
            "¿Qué soluciones conocidas delimitan el espacio?",
            "¿Qué supuesto comparten?",
            "¿Qué mecanismo externo puede importarse?",
            "¿Qué evidencia distingue innovación real de novedad aparente?",
        ),
        avoid=(
            "ideas tipo usar IA",
            "metáforas no traducidas",
            "diversidad cosmética",
        ),
    ),
    "C": PersonaDefinition(
        persona_id="C",
        name="Auditor de evidencia, calidad y confiabilidad",
        output_contract="evidence_auditor_output",
        specialty="evidencia, falsación, reproducibilidad, trazabilidad y riesgo de decisión",
        mandatory_questions=(
            "¿Qué sabemos realmente?",
            "¿Qué parte se ha inferido?",
            "¿Qué observación demostraría que estamos equivocados?",
            "¿La prueba mide el mecanismo?",
        ),
        avoid=(
            "datos inventados",
            "confianza artificial",
            "pass basado solo en ausencia de error",
        ),
    ),
    "D": PersonaDefinition(
        persona_id="D",
        name="Ingeniero adversarial, seguridad y operaciones",
        output_contract="adversarial_engineer_output",
        specialty="abuso, rutas de bypass, detección, contención, recuperación y autorización",
        mandatory_questions=(
            "¿Cómo se abusaría?",
            "¿Qué ruta evita la defensa?",
            "¿Cómo se detecta, limita y recupera el fallo?",
            "¿Existe autorización y qué riesgo residual queda?",
        ),
        avoid=(
            "asumir autorización",
            "pruebas destructivas",
            "declarar vulnerabilidades sin evidencia",
        ),
    ),
}


class PersonaBackend(Protocol):
    """Minimal protocol used by persona execution without coupling to a provider."""

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        """Generate a single response for the prompt."""

    def is_available(self) -> bool:
        """Report whether the backend can currently be used."""


def build_persona_prompt(persona_id: PersonaId, packet: Mapping[str, Any]) -> str:
    """Build an isolated, contract-bound prompt for one persona.

    The common CRIBA packet is reused through ``engine.build_prompt`` and the
    LLM context section through ``llm_adapter.build_llm_prompt``.  Prior
    persona outputs are deliberately removed before either builder sees the
    packet, preserving independent first-pass analysis.
    """
    definition = _definition_for(persona_id)
    prepared_packet = _prepare_packet(packet)
    query = _packet_text(prepared_packet, "original_query", "Consulta no especificada")
    engine_prompt = build_engine_prompt(prepared_packet)
    llm_prompt = build_llm_prompt(prepared_packet, _prepared_methods(prepared_packet), query)
    schema = _output_schema_for(persona_id)
    questions = "\n".join(f"- {question}" for question in definition.mandatory_questions)
    avoid = "\n".join(f"- {item}" for item in definition.avoid)

    return "\n\n".join((
        f"# PERSONA {persona_id} — {definition.name}",
        f"Arquitectura analítica: {definition.specialty}.",
        "## Dimensiones compuestas simultáneas\n"
        f"- {DEFAULT_COMPOSITE_DIMENSIONS.value_and_incentives}\n"
        f"- {DEFAULT_COMPOSITE_DIMENSIONS.human_and_organizational_behavior}\n"
        f"- {DEFAULT_COMPOSITE_DIMENSIONS.evidence_probability_and_risk}",
        "## Preguntas obligatorias\n" + questions,
        "## Debe evitar\n" + avoid,
        "## Aislamiento\nAnaliza solamente el paquete común. No recibes ni debes inferir "
        "salidas de otras personas.",
        f"## Contrato de salida\nDevuelve solo un objeto JSON válido para "
        f"`{definition.output_contract}` que cumpla este schema:\n"
        + json.dumps(schema, ensure_ascii=False, sort_keys=True),
        "## Paquete CRIBA normalizado\n" + engine_prompt,
        "## Contexto para generación LLM\n" + llm_prompt,
    ))


def run_persona(
    persona_id: PersonaId,
    packet: Mapping[str, Any],
    *,
    backend: PersonaBackend | None = None,
) -> PersonaResult:
    """Run one isolated persona or return its explicitly inferred fallback.

    A missing, disabled, unavailable, malformed, or contract-invalid model
    response never becomes a fact.  The fallback is deterministic and its
    provenance is represented in the returned ``PersonaResult``.
    """
    definition = _definition_for(persona_id)
    prepared_packet = _prepare_packet(packet)
    prompt = build_persona_prompt(persona_id, prepared_packet)
    packet_fingerprint = _fingerprint(prepared_packet)
    prompt_fingerprint = _fingerprint(prompt)

    if backend is None or isinstance(backend, NoneBackend):
        return _fallback_result(
            persona_id, definition, prepared_packet, packet_fingerprint, prompt_fingerprint, None
        )
    if not backend.is_available():
        return _fallback_result(
            persona_id, definition, prepared_packet, packet_fingerprint, prompt_fingerprint, "backend_unavailable"
        )

    try:
        response = backend.generate(prompt, system_prompt=_system_instruction(definition))
        output = _parse_persona_output(persona_id, _json_object(response))
    except (TypeError, ValueError, ValidationError, json.JSONDecodeError):
        return _fallback_result(
            persona_id, definition, prepared_packet, packet_fingerprint, prompt_fingerprint, "invalid_backend_output"
        )

    return PersonaResult(
        persona_id=persona_id,
        persona_name=definition.name,
        output_contract=definition.output_contract,
        output=output,
        confidence=PersonaConfidence.UNVERIFIED,
        source=PersonaSource.LLM,
        packet_fingerprint=packet_fingerprint,
        prompt_fingerprint=prompt_fingerprint,
    )


def run_personas(
    packet: Mapping[str, Any],
    *,
    backend: PersonaBackend | None = None,
) -> list[PersonaResult]:
    """Run the four first-pass personas without sharing their outputs."""
    return [run_persona(persona_id, packet, backend=backend) for persona_id in PERSONA_IDS]


def evaluate_persona_diversity(results: list[PersonaResult]) -> PersonaDiversityReport:
    """Reject a four-persona response if its semantic contributions collapse.

    Contract names and provenance labels are excluded from the comparison: they
    are necessarily different and must not mask identical analytic content.
    """
    if len(results) != len(PERSONA_IDS) or {result.persona_id for result in results} != set(PERSONA_IDS):
        return PersonaDiversityReport(
            is_diverse=False,
            reason="insufficient_personas",
        )

    fingerprints = {
        result.persona_id: _fingerprint(_semantic_values(result.output.model_dump()))
        for result in results
    }
    if len(set(fingerprints.values())) == 1:
        return PersonaDiversityReport(
            is_diverse=False,
            reason="identical_semantic_contributions",
            semantic_fingerprints=fingerprints,
        )
    return PersonaDiversityReport(
        is_diverse=True,
        reason="distinct_persona_contributions",
        semantic_fingerprints=fingerprints,
    )


def validate_team_protocol(
    results: list[PersonaResult],
    *,
    minority_report: MinorityReport | None = None,
    protocol: TeamProtocol = DEFAULT_TEAM_PROTOCOL,
) -> TeamProtocolValidation:
    """Require preserved dissent when the isolated recommendations diverge."""
    del protocol  # Its Literal[True] fields make the agreed protocol non-weakenable.
    recommendations = {_recommendation_for(result.output) for result in results}
    recommendations.discard("")
    requires_report = len(recommendations) > 1
    if requires_report and minority_report is None:
        return TeamProtocolValidation(
            is_valid=False,
            requires_minority_report=True,
            reason="minority_report_required_for_disagreement",
        )
    return TeamProtocolValidation(
        is_valid=True,
        requires_minority_report=requires_report,
        reason="minority_report_present" if requires_report else "no_recommendation_disagreement",
    )


def _definition_for(persona_id: PersonaId) -> PersonaDefinition:
    """Look up a static persona definition with an explicit failure mode."""
    try:
        return _PERSONA_DEFINITIONS[persona_id]
    except KeyError as exc:
        raise ValueError(f"Unknown persona_id: {persona_id!r}") from exc


def _output_schema_for(persona_id: PersonaId) -> dict[str, Any]:
    """Return the public JSON schema for one strict output contract."""
    if persona_id == "A":
        return PersonaA.model_json_schema()
    if persona_id == "B":
        return PersonaB.model_json_schema()
    if persona_id == "C":
        return PersonaC.model_json_schema()
    return PersonaD.model_json_schema()


def _parse_persona_output(persona_id: PersonaId, payload: Mapping[str, Any]) -> PersonaOutput:
    """Validate a model response against its persona-specific Pydantic contract."""
    if persona_id == "A":
        return PersonaA.model_validate(payload)
    if persona_id == "B":
        return PersonaB.model_validate(payload)
    if persona_id == "C":
        return PersonaC.model_validate(payload)
    return PersonaD.model_validate(payload)


def _fallback_result(
    persona_id: PersonaId,
    definition: PersonaDefinition,
    packet: Mapping[str, Any],
    packet_fingerprint: str,
    prompt_fingerprint: str,
    fallback_reason: str | None,
) -> PersonaResult:
    """Build a complete deterministic output without overstating evidence."""
    return PersonaResult(
        persona_id=persona_id,
        persona_name=definition.name,
        output_contract=definition.output_contract,
        output=_fallback_output(persona_id, packet),
        confidence=PersonaConfidence.INFERRED,
        source=PersonaSource.DETERMINISTIC_FALLBACK,
        packet_fingerprint=packet_fingerprint,
        prompt_fingerprint=prompt_fingerprint,
        fallback_reason=fallback_reason,
    )


def _fallback_output(persona_id: PersonaId, packet: Mapping[str, Any]) -> PersonaOutput:
    """Derive differentiated, non-factual defaults from only the common packet."""
    query = _packet_text(packet, "original_query", "Consulta no especificada")
    innovation = _mapping(packet.get("innovation"))
    known_space = _string_list(innovation.get("known_space"))
    assumptions = _string_list(innovation.get("assumptions"))
    ruptures = _string_list(innovation.get("ruptures"))
    if not ruptures:
        ruptures = [
            _packet_text(item, "result", "")
            for item in _mapping_list(innovation.get("ruptures"))
            if _packet_text(item, "result", "")
        ]

    if persona_id == "A":
        return PersonaA(
            current_structure=f"Estructura a evaluar para: {query}",
            structural_problem="La estructura causal no está confirmada en el paquete común.",
            root_component="Pendiente de localizar mediante evidencia de ejecución.",
            proposed_change="Aislar el componente causal antes de cambiar interfaces compartidas.",
            shared_or_specialized="No decidido: requiere comparar impacto CRIBA y Blackforge.",
            affected_modules=[],
            interfaces=[],
            state_changes=[],
            persistence_changes=[],
            migration="No proponer migración hasta identificar el estado afectado.",
            failure_modes=["Cambio sin evidencia del componente causal", "Estado no reconstruible"],
            simpler_alternative="Instrumentar y validar el flujo actual antes de añadir una abstracción.",
            evidence_required=["Traza reproducible", "Prueba que mida el mecanismo"],
            recommendation="Priorizar un cambio mínimo, reversible y verificable.",
        )
    if persona_id == "B":
        return PersonaB(
            known_space=known_space,
            dominant_paradigms=[],
            shared_assumptions=assumptions,
            unresolved_gaps=["No hay evidencia suficiente para declarar el espacio agotado."],
            operators_selected=ruptures,
            structural_directions=[f"Modificar la causa identificada en: {query}"],
            mechanism_diversity=["Comparar mecanismos, no variaciones de redacción."],
            novelty_status="unverified_novelty",
            technical_translation="Traducir cada dirección a componentes, estados, entradas y salidas.",
            strongest_direction="La dirección con mecanismo causal y validación falsable.",
            strongest_counterargument="La novedad no se ha verificado frente al espacio conocido.",
            validation_needed=["Comparación con soluciones conocidas", "Experimento que mida la causa"],
        )
    if persona_id == "C":
        return PersonaC(
            confirmed_facts=_string_list(packet.get("confirmed_facts")),
            inferred_claims=[f"La consulta delimita un problema a evaluar: {query}"],
            unsupported_claims=["No declarar efectividad, novedad o severidad sin evidencia persistida."],
            evidence_quality="insufficient",
            conflicting_evidence=[],
            confidence=FindingConfidence.HYPOTHESIS,
            falsification_tests=["Definir una observación que invalide el mecanismo propuesto."],
            pass_fail_criteria=["PASS solo si la prueba mide el mecanismo y deja una traza reproducible."],
            reproducibility="Pendiente: no hay ejecución ni artefacto de evidencia en el paquete común.",
            traceability_gaps=["Falta enlace entre afirmación, fuente y resultado de prueba."],
            risk_of_wrong_decision="Adoptar una hipótesis como hecho puede dirigir inversión a un mecanismo incorrecto.",
            recommendation="Mantener la conclusión como hipótesis hasta registrar evidencia reproducible.",
        )
    return PersonaD(
        assets=_string_list(packet.get("protected_assets")),
        threat_actors=_string_list(packet.get("threat_actors")),
        attack_surfaces=_string_list(packet.get("attack_surfaces")),
        trust_boundaries=_string_list(packet.get("trust_boundaries")),
        attack_hypotheses=["No realizar ni detallar una prueba ofensiva sin autorización explícita y entorno seguro."],
        existing_controls=_string_list(packet.get("existing_controls")),
        likely_bypasses=["Pendiente de análisis autorizado; no asumir que un control elimina todas las rutas."],
        detection="Definir telemetría y criterio de detección antes de validar el control.",
        containment="Usar entorno aislado, condiciones de parada y reversión verificable.",
        recovery="Conservar trazas y restaurar el estado probado tras una validación segura.",
        evidence_status="insufficient_evidence",
        authorization_status=_authorization_status(packet),
        residual_risk="Existe riesgo residual hasta verificar controles y rutas alternativas en alcance autorizado.",
        recommendation="No avanzar con acciones ofensivas; priorizar modelado de amenaza y validación segura autorizada.",
    )


def _prepare_packet(packet: Mapping[str, Any]) -> dict[str, Any]:
    """Copy, sanitize, and normalize packet shape for both prompt builders."""
    prepared = {
        str(key): value
        for key, value in packet.items()
        if str(key) not in _ISOLATION_EXCLUDED_PACKET_KEYS
    }
    query = _packet_text(prepared, "original_query", "Consulta no especificada")
    prepared["original_query"] = query
    prepared["intent"] = _packet_text(prepared, "intent", "INNOVAR")
    prepared["model_instruction"] = _packet_text(
        prepared,
        "model_instruction",
        "Analiza el paquete sin inventar hechos y conserva incertidumbre explícita.",
    )
    innovation = dict(_mapping(prepared.get("innovation")))
    innovation["known_space"] = _string_list(innovation.get("known_space"))
    innovation["assumptions"] = _string_list(innovation.get("assumptions"))
    innovation["ruptures"] = _mapping_list(innovation.get("ruptures"))
    prepared["innovation"] = innovation
    return prepared


def _prepared_methods(packet: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Adapt engine method rows to the LLM prompt contract without mutation."""
    methods: list[dict[str, Any]] = []
    for item in _mapping_list(packet.get("supporting_methods")):
        methods.append({
            "name": _packet_text(item, "name", _packet_text(item, "id", "Método no identificado")),
            "selection_reason": _packet_text(item, "reason", _packet_text(item, "selection_reason", "")),
        })
    return methods


def _system_instruction(definition: PersonaDefinition) -> str:
    """Return the stable system instruction shared by supported LLM backends."""
    return (
        f"Eres la PERSONA {definition.persona_id}: {definition.name}. "
        "Devuelve solo JSON que cumpla exactamente el contrato pedido; "
        "no inventes evidencia y etiqueta la incertidumbre."
    )


def _json_object(response: str) -> dict[str, Any]:
    """Parse a JSON object, tolerating a Markdown fence but not prose payloads."""
    text = response.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else ""
        if text.endswith("```"):
            text = text[:-3].strip()
    parsed: Any = json.loads(text)
    if not isinstance(parsed, dict):
        raise ValueError("persona response must be a JSON object")
    return {str(key): value for key, value in parsed.items()}


def _mapping(value: object) -> Mapping[str, Any]:
    """Return a mapping only when the packet contains one."""
    if isinstance(value, Mapping):
        return {str(key): item for key, item in value.items()}
    return {}


def _mapping_list(value: object) -> list[Mapping[str, Any]]:
    """Return only mapping rows from a packet sequence."""
    if not isinstance(value, list):
        return []
    return [_mapping(item) for item in value if isinstance(item, Mapping)]


def _string_list(value: object) -> list[str]:
    """Normalize user-provided lists without promoting non-string values."""
    if not isinstance(value, list):
        return []
    return [item.strip() for item in value if isinstance(item, str) and item.strip()]


def _packet_text(packet: Mapping[str, Any], key: str, fallback: str) -> str:
    """Read a non-empty text field from a packet without coercing arbitrary data."""
    value = packet.get(key)
    if isinstance(value, str) and value.strip():
        return value.strip()
    return fallback


def _authorization_status(packet: Mapping[str, Any]) -> AuthorizationStatus:
    """Normalize authorization conservatively; missing proof remains pending."""
    raw = _packet_text(packet, "authorization_state", "pending").lower()
    aliases: dict[str, AuthorizationStatus] = {
        "authorized": "granted",
        "unauthorized": "denied",
        "pending": "pending",
        "granted": "granted",
        "denied": "denied",
        "expired": "expired",
        "not_required": "not_required",
    }
    return aliases.get(raw, "pending")


def _semantic_values(payload: Mapping[str, Any]) -> list[str]:
    """Flatten contribution content while ignoring metadata-only enum fields."""
    ignored = {"confidence", "authorization_status"}
    values: list[str] = []
    for key, value in payload.items():
        if key in ignored:
            continue
        if isinstance(value, str):
            values.append(value.strip().casefold())
        elif isinstance(value, list):
            values.extend(item.strip().casefold() for item in value if isinstance(item, str) and item.strip())
    # Field cardinality belongs to the contract, not to the contribution.  A
    # repeated answer can occupy a different number of required fields in each
    # persona, so retain only its unique semantic statements for comparison.
    return sorted(set(values))


def _recommendation_for(output: PersonaOutput) -> str:
    """Extract a comparable recommendation without collapsing contracts."""
    if isinstance(output, PersonaB):
        return output.strongest_direction.strip().casefold()
    return output.recommendation.strip().casefold()


def _fingerprint(value: object) -> str:
    """Return a deterministic SHA-256 hash for tracing and anti-copy checks."""
    canonical = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
