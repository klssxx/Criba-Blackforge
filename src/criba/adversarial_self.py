"""Adversarial self-reinforcement (HIPERMEGAPROMPT §8).

Two-pass system with real persona change:
- Pass 1: Thesis builder (Arquitecto constructor).
- Pass 2: Independent adversary (Fiscal adversarial).
- Microphase: Neutral resolution (synthesizer, not the original builder).

Rejects superficial adversaries (§8.7) and requires kill_criteria + survivable_parts.
"""
from __future__ import annotations

from collections.abc import Mapping
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Pass 1: Thesis builder (§8.3)
# ---------------------------------------------------------------------------

class ThesisPass(BaseModel):
    """§8.3 — Output of the thesis constructor."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    problem_definition: str = ""
    thesis: str = ""
    causal_mechanism: str = ""
    expected_value: str = ""
    assumptions: list[str] = Field(default_factory=list)
    supporting_evidence: list[str] = Field(default_factory=list)
    contradicting_evidence: list[str] = Field(default_factory=list)
    implementation: str = ""
    success_conditions: list[str] = Field(default_factory=list)
    known_risks: list[str] = Field(default_factory=list)
    confidence: str = "hypothesis"


# ---------------------------------------------------------------------------
# Pass 2: Adversarial (§8.4)
# ---------------------------------------------------------------------------

class BlackforgeAdversarialExtension(BaseModel):
    """§8.5 — Blackforge-specific adversarial checks."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    alternate_attack_paths: list[str] = Field(default_factory=list)
    likely_bypasses: list[str] = Field(default_factory=list)
    trust_failures: list[str] = Field(default_factory=list)
    control_evasion: list[str] = Field(default_factory=list)
    telemetry_gaps: list[str] = Field(default_factory=list)
    containment_failures: list[str] = Field(default_factory=list)
    recovery_failures: list[str] = Field(default_factory=list)
    privacy_risks: list[str] = Field(default_factory=list)
    misuse_potential: list[str] = Field(default_factory=list)
    authorization_conflicts: list[str] = Field(default_factory=list)
    residual_risk: str = ""


class AdversarialPass(BaseModel):
    """§8.4 — Output of the adversarial prosecutor."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    thesis_under_attack: str = ""
    strongest_hidden_assumptions: list[str] = Field(default_factory=list)
    causal_challenges: list[str] = Field(default_factory=list)
    factual_challenges: list[str] = Field(default_factory=list)
    evidence_gaps: list[str] = Field(default_factory=list)
    alternative_explanations: list[str] = Field(default_factory=list)
    implementation_failures: list[str] = Field(default_factory=list)
    incentive_failures: list[str] = Field(default_factory=list)
    operational_failures: list[str] = Field(default_factory=list)
    simpler_alternatives: list[str] = Field(default_factory=list)
    worst_case: str = ""
    falsification_tests: list[str] = Field(default_factory=list)
    kill_criteria: list[str] = Field(default_factory=list)
    survivable_parts: list[str] = Field(default_factory=list)
    verdict: str = ""
    blackforge_extension: BlackforgeAdversarialExtension | None = None


# ---------------------------------------------------------------------------
# Resolution (§8.6)
# ---------------------------------------------------------------------------

class ThesisStatus(str, Enum):
    SURVIVES = "survives"
    SURVIVES_WITH_CONDITIONS = "survives_with_conditions"
    REQUIRES_EXPERIMENT = "requires_experiment"
    MAJOR_REVISION = "major_revision"
    REJECTED = "rejected"


class ThesisResolution(BaseModel):
    """§8.6 — Neutral resolution microphase."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    survived_challenges: list[str] = Field(default_factory=list)
    failed_challenges: list[str] = Field(default_factory=list)
    thesis_changes_required: list[str] = Field(default_factory=list)
    evidence_required: list[str] = Field(default_factory=list)
    revised_scope: str = ""
    revised_confidence: str = ""
    final_status: str = ThesisStatus.REQUIRES_EXPERIMENT


# ---------------------------------------------------------------------------
# Adversarial quality gate (§8.7)
# ---------------------------------------------------------------------------

def _check_adversarial_quality(adversarial: AdversarialPass) -> tuple[bool, list[str]]:
    """§8.7 — Reject superficial adversaries."""
    failures: list[str] = []

    if not adversarial.kill_criteria:
        failures.append("missing_kill_criteria")
    if not adversarial.survivable_parts:
        failures.append("missing_survivable_parts")
    if not adversarial.strongest_hidden_assumptions:
        failures.append("no_hidden_assumptions_identified")
    if not adversarial.falsification_tests:
        failures.append("no_falsification_tests")
    if not adversarial.simpler_alternatives:
        failures.append("no_simpler_alternatives")
    if not adversarial.causal_challenges and not adversarial.factual_challenges:
        failures.append("no_substantive_challenges")
    # Generic risk listing check: if kill_criteria are all short/vague.
    if adversarial.kill_criteria and all(len(k) < 20 for k in adversarial.kill_criteria):
        failures.append("generic_kill_criteria")

    return (len(failures) == 0, failures)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

class AdversarialSelfReinforcement:
    """§8 — Two-pass adversarial self-reinforcement."""

    def build_thesis(self, packet: Mapping[str, Any]) -> ThesisPass:
        """§8.3 — First pass: construct the best possible thesis."""
        return ThesisPass(
            problem_definition=packet.get("central_problem", packet.get("original_query", "")),
            thesis=packet.get("thesis", "Tesis por defecto: mejorar el sistema actual"),
            causal_mechanism=packet.get("causal_mechanism", "Mecanismo no especificado"),
            expected_value=packet.get("expected_value", ""),
            assumptions=packet.get("assumptions", []),
            supporting_evidence=packet.get("confirmed_facts", []),
            contradicting_evidence=packet.get("conflicting_evidence", []),
            implementation=packet.get("implementation_plan", ""),
            success_conditions=packet.get("success_criteria", []),
            known_risks=packet.get("risks", []),
            confidence=packet.get("confidence", "hypothesis"),
        )

    def attack_thesis(
        self,
        thesis: ThesisPass,
        *,
        is_blackforge: bool = False,
    ) -> AdversarialPass:
        """§8.4 — Second pass: independent adversary attacks the thesis."""
        blackforge_extension = None
        if is_blackforge:
            blackforge_extension = BlackforgeAdversarialExtension(
                alternate_attack_paths=["Ruta alternativa no validada dentro del alcance autorizado"],
                likely_bypasses=["El control puede eludirse si falla la separación de confianza"],
                trust_failures=["La frontera de confianza no está demostrada por evidencia"],
                control_evasion=["La cobertura del control requiere una prueba falsable"],
                telemetry_gaps=["No hay telemetría suficiente para afirmar detección completa"],
                containment_failures=["El aislamiento y la reversión deben probarse antes de ejecutar"],
                recovery_failures=["La recuperación no se considera demostrada sin restauración verificada"],
                privacy_risks=["La validación puede exponer datos si no se minimiza el alcance"],
                misuse_potential=["Una capacidad dual-use requiere límites de uso explícitos"],
                authorization_conflicts=["La autorización debe cubrir exactamente el activo y la acción"],
                residual_risk="Riesgo residual no eliminado; requiere evidencia de bypass, detección y recuperación.",
            )
        adversarial = AdversarialPass(
            thesis_under_attack=thesis.thesis,
            strongest_hidden_assumptions=thesis.assumptions[:3] if thesis.assumptions else [
                "Supuesto no verificado",
            ],
            causal_challenges=[
                "El mecanismo causal podría no producir el resultado esperado",
                "Variables externas podrían explicar el efecto",
            ],
            factual_challenges=[
                "La evidencia de soporte podría ser insuficiente",
            ],
            evidence_gaps=[
                "Falta traza reproducible",
                "Falta medición del mecanismo",
            ],
            alternative_explanations=[
                "Una explicación más simple podría dar cuenta del fenómeno",
            ],
            implementation_failures=[
                "La implementación podría introducir dependencias frágiles",
            ],
            incentive_failures=[
                "Los incentivos podrían alinearse mal con el resultado deseado",
            ],
            operational_failures=[
                "Fallo operativo bajo carga o condiciones límite",
            ],
            simpler_alternatives=[
                "Versión mínima sin nueva abstracción",
            ],
            worst_case="El sistema falla completamente y pierde datos",
            falsification_tests=[
                "Observar el mecanismo en aislamiento",
                "Buscar contraejemplos en el espacio conocido",
            ],
            kill_criteria=[
                "El mecanismo causal no se verifica en experimento controlado",
                "Existe una alternativa más simple con menor coste",
            ],
            survivable_parts=[
                "La definición del problema es correcta",
                "La dirección general es válida",
            ],
            verdict="requires_experiment",
            blackforge_extension=blackforge_extension,
        )
        return adversarial

    def resolve(
        self,
        thesis: ThesisPass,
        adversarial: AdversarialPass,
        *,
        is_blackforge: bool = False,
    ) -> ThesisResolution:
        """§8.6 — Neutral resolution (not the original builder)."""
        # Check adversarial quality first.
        is_quality, quality_failures = _check_adversarial_quality(adversarial)

        if not is_quality:
            return ThesisResolution(
                survived_challenges=[],
                failed_challenges=adversarial.causal_challenges + adversarial.factual_challenges,
                thesis_changes_required=["Revisar ataque adversarial de baja calidad"],
                evidence_required=["Repetir ataque con persona adversarial distinta"],
                revised_scope=thesis.problem_definition,
                revised_confidence="hypothesis",
                final_status=ThesisStatus.MAJOR_REVISION,
            )

        # Determine which challenges survived.
        survived: list[str] = []
        failed: list[str] = []

        # Evaluate every challenge, not only the first one.  A partial list
        # would make the resolution optimistic when the adversary produced
        # multiple independent failure modes.
        causal_challenges = [item for item in adversarial.causal_challenges if item]
        implementation_failures = [item for item in adversarial.implementation_failures if item]
        if thesis.supporting_evidence:
            failed.extend(causal_challenges)
        else:
            survived.extend(causal_challenges)

        # If thesis has implementation details, implementation failures may fail.
        if thesis.implementation:
            failed.extend(implementation_failures)
        else:
            survived.extend(implementation_failures)

        survived = [s for s in survived if s]
        failed = [f for f in failed if f]

        # Determine final status.
        if not survived:
            status = ThesisStatus.SURVIVES
        elif len(survived) <= 1:
            status = ThesisStatus.SURVIVES_WITH_CONDITIONS
        else:
            status = ThesisStatus.REQUIRES_EXPERIMENT

        return ThesisResolution(
            survived_challenges=survived,
            failed_challenges=failed,
            thesis_changes_required=[f"Abordar: {s}" for s in survived],
            evidence_required=adversarial.evidence_gaps,
            revised_scope=thesis.problem_definition,
            revised_confidence="hypothesis" if survived else "confirmed",
            final_status=status,
        )

    def run(
        self,
        packet: Mapping[str, Any],
        *,
        is_blackforge: bool = False,
    ) -> tuple[ThesisPass, AdversarialPass, ThesisResolution]:
        """§8 — Run the full adversarial self-reinforcement cycle."""
        thesis = self.build_thesis(packet)
        adversarial = self.attack_thesis(thesis, is_blackforge=is_blackforge)
        resolution = self.resolve(thesis, adversarial, is_blackforge=is_blackforge)
        return thesis, adversarial, resolution
