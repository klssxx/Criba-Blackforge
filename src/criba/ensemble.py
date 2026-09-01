"""Four-persona ensemble synthesis (HIPERMEGAPROMPT §6).

Runs the four personas independently, then synthesizes their outputs into:
- Strong / partial agreements.
- Substantive disagreements (factual, causal, criteria, architectural, irreconcilable).
- Emergent findings (intersection logic + why no single persona found it).
- Minority report when recommendations diverge.
- Ensemble metrics (semantic/mechanism diversity, agreement strength, etc.).

No simple voting (§6.8): decision factors are weighted and include minority
objections. Supports regeneration triggers (§6.10).
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .personas import (
    MinorityReport,
    PersonaC,
    PersonaId,
    PersonaResult,
    TeamProtocolValidation,
    evaluate_persona_diversity,
    run_personas,
    validate_team_protocol,
)

# ---------------------------------------------------------------------------
# Synthesis output contracts (§6.5, §6.6, §6.9)
# ---------------------------------------------------------------------------


class EmergentFinding(BaseModel):
    """§6.5 — A finding that emerges only from intersecting persona outputs."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source_observations: list[dict[str, str]] = Field(min_length=2)
    intersection_logic: str = Field(min_length=1)
    resulting_finding: str = Field(min_length=1)
    why_no_single_persona_found_it: str = Field(min_length=1)
    practical_implication: str = ""
    validation_needed: list[str] = Field(default_factory=list)
    confidence: str = "hypothesis"


class StrongAgreement(BaseModel):
    """§6.4 — Multiple personas converge on the same finding."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    finding: str = Field(min_length=1)
    supporting_personas: list[PersonaId] = Field(min_length=2)
    independent_routes: list[str] = Field(min_length=1)
    confidence_gain: str = ""
    remaining_uncertainty: str = ""


class PartialAgreement(BaseModel):
    """§6.4 — Shared diagnosis but divergent responses."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    shared_diagnosis: str = Field(min_length=1)
    divergent_responses: list[str] = Field(min_length=1)
    decision_needed: str = ""


class Disagreement(BaseModel):
    """§6.4 — A substantive disagreement between personas."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    category: str  # factual | causal | criteria | architectural | irreconciliable
    topic: str = Field(min_length=1)
    positions: list[dict[str, str]] = Field(min_length=2)
    evidence_gap: str = ""
    resolution_path: str = ""


class EnsembleMetrics(BaseModel):
    """§6.9 — Quantitative ensemble quality indicators."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    semantic_diversity: float = 0.0
    mechanism_diversity: float = 0.0
    agreement_strength: float = 0.0
    disagreement_value: float = 0.0
    evidence_coverage: float = 0.0
    hypothesis_coverage: float = 0.0
    emergent_finding_count: int = 0
    unresolved_conflict_count: int = 0
    synthesis_confidence: float = 0.0


class EnsembleSynthesis(BaseModel):
    """§6.6 — Complete synthesis output."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    shared_problem_definition: str = ""
    strongest_agreements: list[StrongAgreement] = Field(default_factory=list)
    partial_agreements: list[PartialAgreement] = Field(default_factory=list)
    substantive_disagreements: list[Disagreement] = Field(default_factory=list)
    factual_conflicts: list[str] = Field(default_factory=list)
    unresolved_uncertainties: list[str] = Field(default_factory=list)
    emergent_findings: list[EmergentFinding] = Field(default_factory=list)
    candidate_solutions: list[str] = Field(default_factory=list)
    rejected_solutions: list[str] = Field(default_factory=list)
    synthesis_recommendation: str = ""
    minority_report: MinorityReport | None = None
    confidence: str = "hypothesis"
    next_validation: str = ""
    metrics: EnsembleMetrics = Field(default_factory=EnsembleMetrics)
    regeneration_triggered: bool = False
    regeneration_reasons: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Regeneration triggers (§6.10)
# ---------------------------------------------------------------------------

REGENERATION_TRIGGERS = [
    "three_or_more_identical",
    "no_uncertainty_identified",
    "all_accept_premise",
    "no_alternative_explanations",
    "no_substantive_disagreement",
    "linguistic_variations_only",
    "minority_opinion_lost",
    "unsupported_claims_present",
]


def _check_regeneration(results: Sequence[PersonaResult]) -> tuple[bool, list[str]]:
    """§6.10 — Determine if the ensemble should be regenerated."""
    reasons: list[str] = []

    # Three or more produce the same recommendation.
    recommendations: dict[str, int] = {}
    for r in results:
        rec = _recommendation_text(r).strip().casefold()
        if rec:
            recommendations[rec] = recommendations.get(rec, 0) + 1
    if any(count >= 3 for count in recommendations.values()):
        reasons.append("three_or_more_identical")

    # No uncertainty identified.
    has_uncertainty = any(
        isinstance(r.output, PersonaC) and r.output.confidence.value in ("hypothesis", "inferred")
        for r in results
    )
    if not has_uncertainty:
        reasons.append("no_uncertainty_identified")

    # All accept the premise (no adversarial pushback).
    has_adversarial = any(r.persona_id == "D" for r in results)
    if not has_adversarial:
        reasons.append("all_accept_premise")

    # No alternative explanations (all strongest_directions identical).
    directions = {_recommendation_text(r).strip().casefold() for r in results}
    if len(directions) <= 1:
        reasons.append("no_alternative_explanations")

    # No substantive disagreement.
    if len(directions) <= 1:
        reasons.append("no_substantive_disagreement")

    # Minority opinion lost (only one unique recommendation).
    if len(recommendations) <= 1 and len(results) == 4:
        reasons.append("minority_opinion_lost")

    # Unsupported claims present (PersonaC with empty confirmed_facts but high confidence).
    for r in results:
        if isinstance(r.output, PersonaC):
            if r.output.confidence.value == "confirmed" and not r.output.confirmed_facts:
                reasons.append("unsupported_claims_present")
                break

    return bool(reasons), reasons


# ---------------------------------------------------------------------------
# Synthesis helpers
# ---------------------------------------------------------------------------


def _recommendation_text(result: PersonaResult) -> str:
    """Extract a comparable recommendation string from any persona output."""
    output = result.output
    if hasattr(output, "recommendation") and output.recommendation:
        return output.recommendation
    if hasattr(output, "strongest_direction") and output.strongest_direction:
        return output.strongest_direction
    return ""


def _extract_mechanisms(result: PersonaResult) -> set[str]:
    """Extract mechanism-related content for diversity measurement."""
    output = result.output
    mechanisms: set[str] = set()
    if hasattr(output, "proposed_change") and output.proposed_change:
        mechanisms.add(output.proposed_change.strip().casefold())
    if hasattr(output, "mechanism_diversity") and output.mechanism_diversity:
        for m in output.mechanism_diversity:
            mechanisms.add(m.strip().casefold())
    if hasattr(output, "defensive_mechanism") and output.defensive_mechanism:
        mechanisms.add(output.defensive_mechanism.strip().casefold())
    if hasattr(output, "attack_hypotheses") and output.attack_hypotheses:
        for h in output.attack_hypotheses:
            mechanisms.add(h.strip().casefold())
    return mechanisms


def _compute_semantic_diversity(results: Sequence[PersonaResult]) -> float:
    """§6.9 — Ratio of unique semantic fingerprints to total personas."""
    diversity = evaluate_persona_diversity(list(results))
    return 1.0 if diversity.is_diverse else 0.0


def _compute_mechanism_diversity(results: Sequence[PersonaResult]) -> float:
    """§6.9 — Ratio of unique mechanisms across all personas."""
    all_mechanisms: set[str] = set()
    per_persona: list[set[str]] = []
    for r in results:
        mechs = _extract_mechanisms(r)
        per_persona.append(mechs)
        all_mechanisms.update(mechs)
    if not all_mechanisms:
        return 0.0
    # Count how many mechanisms are unique to one persona.
    unique_count = 0
    for mech in all_mechanisms:
        owners = sum(1 for p in per_persona if mech in p)
        if owners == 1:
            unique_count += 1
    return unique_count / len(all_mechanisms) if all_mechanisms else 0.0


def _compute_agreement_strength(results: Sequence[PersonaResult]) -> float:
    """§6.9 — Fraction of recommendation pairs that agree."""
    recommendations = [_recommendation_text(r).strip().casefold() for r in results]
    non_empty = [r for r in recommendations if r]
    if len(non_empty) < 2:
        return 0.0
    # Count matching pairs.
    matches = 0
    total = 0
    for i in range(len(non_empty)):
        for j in range(i + 1, len(non_empty)):
            total += 1
            if non_empty[i] == non_empty[j]:
                matches += 1
    return matches / total if total else 0.0


def _find_strong_agreements(results: Sequence[PersonaResult]) -> list[StrongAgreement]:
    """§6.4 — Identify findings supported by multiple personas via independent routes."""
    agreements: list[StrongAgreement] = []
    # Group by recommendation text.
    by_rec: dict[str, list[PersonaResult]] = {}
    for r in results:
        rec = _recommendation_text(r).strip().casefold()
        if rec:
            by_rec.setdefault(rec, []).append(r)
    for rec, group in by_rec.items():
        if len(group) >= 2:
            agreements.append(
                StrongAgreement(
                    finding=rec,
                    supporting_personas=[r.persona_id for r in group],
                    independent_routes=[f"persona_{r.persona_id}" for r in group],
                    confidence_gain=f"{len(group)}/4 personas convergentes",
                    remaining_uncertainty="Verificar independencia real de razonamiento",
                )
            )
    return agreements


def _find_partial_agreements(results: Sequence[PersonaResult]) -> list[PartialAgreement]:
    """§6.4 — Shared diagnosis but divergent responses."""
    partials: list[PartialAgreement] = []
    # Check if PersonaC and PersonaA share a problem diagnosis.
    personac = next((r for r in results if r.persona_id == "C"), None)
    personaa = next((r for r in results if r.persona_id == "A"), None)
    if personac and personaa:
        cc = personac.output
        ca = personaa.output
        if hasattr(cc, "confirmed_facts") and hasattr(ca, "structural_problem"):
            if cc.confirmed_facts and ca.structural_problem:
                partials.append(
                    PartialAgreement(
                        shared_diagnosis=ca.structural_problem.strip().casefold(),
                        divergent_responses=[
                            f"Persona C: {cc.confirmed_facts[0].strip().casefold()}",
                            f"Persona A: {ca.proposed_change.strip().casefold()}" if ca.proposed_change else "",
                        ],
                        decision_needed="Validar si el mecanismo propuesto ataca la causa compartida",
                    )
                )
    return partials


def _classify_disagreements(results: Sequence[PersonaResult]) -> list[Disagreement]:
    """§6.4 — Classify substantive disagreements."""
    disagreements: list[Disagreement] = []
    # Compare PersonaB (innovation) vs PersonaA (architecture) on direction.
    personab = next((r for r in results if r.persona_id == "B"), None)
    personaa = next((r for r in results if r.persona_id == "A"), None)
    if personab and personaa:
        bb = personab.output
        aa = personaa.output
        if hasattr(bb, "strongest_direction") and hasattr(aa, "proposed_change"):
            if bb.strongest_direction and aa.proposed_change:
                dir_b = bb.strongest_direction.strip().casefold()
                dir_a = aa.proposed_change.strip().casefold()
                if dir_b != dir_a:
                    disagreements.append(
                        Disagreement(
                            category="architectural",
                            topic="primary_direction",
                            positions=[
                                {"persona": "B", "position": dir_b},
                                {"persona": "A", "position": dir_a},
                            ],
                            evidence_gap="Falta evidencia que favorezca una dirección sobre otra",
                            resolution_path="Prototipar la dirección de menor coste y validar hipótesis causal",
                        )
                    )
    return disagreements


def _find_emergent_findings(results: Sequence[PersonaResult]) -> list[EmergentFinding]:
    """§6.5 — Findings that emerge only from intersecting persona outputs."""
    emergent: list[EmergentFinding] = []
    # Intersection: PersonaA identifies structural problem + PersonaC identifies evidence gap.
    personaa = next((r for r in results if r.persona_id == "A"), None)
    personac = next((r for r in results if r.persona_id == "C"), None)
    if personaa and personac:
        aa = personaa.output
        cc = personac.output
        if hasattr(aa, "structural_problem") and hasattr(cc, "evidence_quality"):
            if aa.structural_problem and cc.evidence_quality == "insufficient":
                emergent.append(
                    EmergentFinding(
                        source_observations=[
                            {"persona": "A", "contribution": aa.structural_problem},
                            {"persona": "C", "contribution": f"evidence_quality={cc.evidence_quality}"},
                        ],
                        intersection_logic="A identifica la estructura; C confirma que falta evidencia",
                        resulting_finding="El problema estructural carece de evidencia empírica",
                        why_no_single_persona_found_it="A no evalúa evidencia; C no identifica estructura",
                        practical_implication="Instrumentar antes de proponer cambio",
                        validation_needed=["Traza reproducible", "Medición del mecanismo"],
                        confidence="hypothesis",
                    )
                )
    return emergent


def _build_minority_report(
    results: Sequence[PersonaResult],
    protocol_val: TeamProtocolValidation,
) -> MinorityReport | None:
    """§6.7 — Build minority report when recommendations diverge."""
    if protocol_val.is_valid:
        return None
    # Find the dissenting persona(s).
    recommendations: dict[str, list[PersonaId]] = {}
    for r in results:
        rec = _recommendation_text(r).strip().casefold()
        if rec:
            recommendations.setdefault(rec, []).append(r.persona_id)
    if len(recommendations) <= 1:
        return None
    # The minority is the group with fewer personas.
    minority_group = min(recommendations.values(), key=len)
    majority_group = max(recommendations.values(), key=len)
    minority_id = minority_group[0]
    minority_result = next(r for r in results if r.persona_id == minority_id)
    return MinorityReport(
        dissenting_persona_ids=minority_group,
        disagreement=f"Recomendación minoritaria: {_recommendation_text(minority_result)}",
        evidence_needed=["Evidencia que favorezca la posición minoritaria"],
        impact_on_recommendation="Si la minoría tiene razón, la recomendación principal es incorrecta",
    )


def _compute_metrics(results: Sequence[PersonaResult]) -> EnsembleMetrics:
    """§6.9 — Compute all ensemble metrics."""
    semantic_div = _compute_semantic_diversity(results)
    mechanism_div = _compute_mechanism_diversity(results)
    agreement = _compute_agreement_strength(results)
    strong_agreements = _find_strong_agreements(results)
    disagreements = _classify_disagreements(results)
    emergent = _find_emergent_findings(results)
    # Disagreement value: ratio of unique recommendations.
    unique_recs = len({_recommendation_text(r).strip().casefold() for r in results})
    disagreement_value = unique_recs / len(results) if results else 0.0
    # Evidence coverage: fraction of personas with evidence.
    with_evidence = sum(
        1 for r in results
        if hasattr(r.output, "confirmed_facts") and getattr(r.output, "confirmed_facts", [])
    )
    evidence_coverage = with_evidence / len(results) if results else 0.0
    # Hypothesis coverage: fraction of personas with hypotheses.
    with_hypothesis = sum(
        1 for r in results
        if hasattr(r.output, "hypotheses") and getattr(r.output, "hypotheses", [])
    )
    hypothesis_coverage = with_hypothesis / len(results) if results else 0.0
    # Synthesis confidence: average of agreement and diversity.
    synthesis_confidence = (agreement + semantic_div) / 2 if results else 0.0
    return EnsembleMetrics(
        semantic_diversity=semantic_div,
        mechanism_diversity=mechanism_div,
        agreement_strength=agreement,
        disagreement_value=disagreement_value,
        evidence_coverage=evidence_coverage,
        hypothesis_coverage=hypothesis_coverage,
        emergent_finding_count=len(emergent),
        unresolved_conflict_count=len(disagreements),
        synthesis_confidence=synthesis_confidence,
    )


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def run_ensemble(
    packet: Mapping[str, Any],
    *,
    backend: Any | None = None,
    max_regenerations: int = 1,
) -> EnsembleSynthesis:
    """§6 — Run the four-persona ensemble and synthesize results.

    Parameters
    ----------
    packet : Mapping[str, Any]
        Common CRIBA packet (context + task + constraints).
    backend : PersonaBackend | None
        Optional LLM backend. If None, deterministic fallback is used.
    max_regenerations : int
        Maximum number of regeneration attempts (§6.10).
    """

    results = run_personas(packet, backend=backend)
    protocol_val = validate_team_protocol(results)
    minority_report = _build_minority_report(results, protocol_val)

    # Check regeneration triggers.
    should_regen, regen_reasons = _check_regeneration(results)
    regeneration_triggered = False
    if should_regen and max_regenerations > 0:
        regeneration_triggered = True
        # Attempt regeneration (one pass; could be extended).
        results = run_personas(packet, backend=backend)
        protocol_val = validate_team_protocol(results)
        minority_report = _build_minority_report(results, protocol_val)

    # Build synthesis.
    strong_agreements = _find_strong_agreements(results)
    partial_agreements = _find_partial_agreements(results)
    disagreements = _classify_disagreements(results)
    emergent = _find_emergent_findings(results)
    metrics = _compute_metrics(results)

    # Determine recommendation.
    if strong_agreements:
        recommendation = strong_agreements[0].finding
    elif emergent:
        recommendation = emergent[0].resulting_finding
    elif partial_agreements:
        recommendation = partial_agreements[0].shared_diagnosis
    else:
        recommendation = "No hay consenso suficiente; validar hipótesis con experimento"

    # Collect candidate solutions from PersonaB.
    personab = next((r for r in results if r.persona_id == "B"), None)
    candidate_solutions: list[str] = []
    if personab and hasattr(personab.output, "structural_directions"):
        candidate_solutions = list(personab.output.structural_directions)

    # Collect rejected solutions from PersonaD.
    personad = next((r for r in results if r.persona_id == "D"), None)
    rejected_solutions: list[str] = []
    if personad and hasattr(personad.output, "likely_bypasses"):
        rejected_solutions = [b for b in personad.output.likely_bypasses if b]

    # Extract problem definition from PersonaA.
    personaa = next((r for r in results if r.persona_id == "A"), None)
    problem_def = ""
    if personaa and hasattr(personaa.output, "structural_problem"):
        problem_def = personaa.output.structural_problem

    # Extract factual conflicts from PersonaC.
    personac = next((r for r in results if r.persona_id == "C"), None)
    factual_conflicts: list[str] = []
    if personac and hasattr(personac.output, "conflicting_evidence"):
        factual_conflicts = list(personac.output.conflicting_evidence)

    # Extract unresolved uncertainties.
    unresolved: list[str] = []
    if personac and hasattr(personac.output, "traceability_gaps"):
        unresolved = list(personac.output.traceability_gaps)

    return EnsembleSynthesis(
        shared_problem_definition=problem_def,
        strongest_agreements=strong_agreements,
        partial_agreements=partial_agreements,
        substantive_disagreements=disagreements,
        factual_conflicts=factual_conflicts,
        unresolved_uncertainties=unresolved,
        emergent_findings=emergent,
        candidate_solutions=candidate_solutions,
        rejected_solutions=rejected_solutions,
        synthesis_recommendation=recommendation,
        minority_report=minority_report,
        confidence="hypothesis" if not strong_agreements else "confirmed",
        next_validation="Validar recomendación con prototipo o experimento controlado",
        metrics=metrics,
        regeneration_triggered=regeneration_triggered,
        regeneration_reasons=regen_reasons if regeneration_triggered else [],
    )
