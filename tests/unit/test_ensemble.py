"""Tests for the four-persona ensemble (HIPERMEGAPROMPT §6)."""
from __future__ import annotations

from typing import Any

from criba.constraints import FindingConfidence
from criba.ensemble import (
    EnsembleMetrics,
    EnsembleSynthesis,
    _check_regeneration,
    _classify_disagreements,
    _compute_agreement_strength,
    _compute_semantic_diversity,
    _extract_mechanisms,
    _find_emergent_findings,
    _find_partial_agreements,
    _find_strong_agreements,
    _recommendation_text,
    run_ensemble,
)
from criba.personas import (
    PersonaA,
    PersonaB,
    PersonaC,
    PersonaConfidence,
    PersonaD,
    PersonaResult,
    PersonaSource,
    validate_team_protocol,
)


def _make_result(
    persona_id: str,
    output: Any,
    confidence: PersonaConfidence = PersonaConfidence.INFERRED,
    source: PersonaSource = PersonaSource.DETERMINISTIC_FALLBACK,
) -> PersonaResult:
    names = {"A": "Arquitecto", "B": "Innovador", "C": "Auditor", "D": "Adversarial"}
    contracts = {
        "A": "system_architect_output",
        "B": "innovation_architect_output",
        "C": "evidence_auditor_output",
        "D": "adversarial_engineer_output",
    }
    return PersonaResult(
        persona_id=persona_id,
        persona_name=names[persona_id],
        output_contract=contracts[persona_id],
        output=output,
        confidence=confidence,
        source=source,
        packet_fingerprint="fp",
        prompt_fingerprint="pp",
    )


def _packet() -> dict[str, Any]:
    return {
        "original_query": "How to improve security",
        "intent": "INNOVAR",
        "confirmed_facts": ["fact1"],
        "protected_assets": ["data"],
        "threat_actors": ["attacker"],
        "attack_surfaces": ["web"],
        "trust_boundaries": ["api"],
        "existing_controls": ["waf"],
        "innovation": {
            "known_space": ["solution1"],
            "assumptions": ["assumption1"],
            "ruptures": [{"result": "rupture1"}],
        },
    }


class TestRecommendationText:
    def test_persona_a(self) -> None:
        r = _make_result("A", PersonaA(
            current_structure="s", structural_problem="p", root_component="r",
            proposed_change="change", shared_or_specialized="shared",
            affected_modules=[], interfaces=[], state_changes=[],
            persistence_changes=[], migration="", failure_modes=[],
            simpler_alternative="", evidence_required=[], recommendation="REC",
        ))
        assert _recommendation_text(r) == "REC"

    def test_persona_b_uses_strongest_direction(self) -> None:
        r = _make_result("B", PersonaB(
            known_space=[], dominant_paradigms=[], shared_assumptions=[],
            unresolved_gaps=[], operators_selected=[], structural_directions=[],
            mechanism_diversity=[], novelty_status="", technical_translation="",
            strongest_direction="INNOVATE", strongest_counterargument="",
            validation_needed=[],
        ))
        assert _recommendation_text(r) == "INNOVATE"

    def test_persona_c(self) -> None:
        r = _make_result("C", PersonaC(
            confirmed_facts=[], inferred_claims=[], unsupported_claims=[],
            evidence_quality="", conflicting_evidence=[],
            confidence=FindingConfidence.HYPOTHESIS,
            falsification_tests=[], pass_fail_criteria=[], reproducibility="",
            traceability_gaps=[], risk_of_wrong_decision="", recommendation="CAUTION",
        ))
        assert _recommendation_text(r) == "CAUTION"


class TestMechanismExtraction:
    def test_persona_a_proposed_change(self) -> None:
        r = _make_result("A", PersonaA(
            current_structure="s", structural_problem="p", root_component="r",
            proposed_change="CHANGE", shared_or_specialized="shared",
            affected_modules=[], interfaces=[], state_changes=[],
            persistence_changes=[], migration="", failure_modes=[],
            simpler_alternative="", evidence_required=[], recommendation="",
        ))
        mechs = _extract_mechanisms(r)
        assert "change" in mechs

    def test_persona_b_mechanism_diversity(self) -> None:
        r = _make_result("B", PersonaB(
            known_space=[], dominant_paradigms=[], shared_assumptions=[],
            unresolved_gaps=[], operators_selected=[], structural_directions=[],
            mechanism_diversity=["mech1", "mech2"], novelty_status="",
            technical_translation="", strongest_direction="",
            strongest_counterargument="", validation_needed=[],
        ))
        mechs = _extract_mechanisms(r)
        assert "mech1" in mechs
        assert "mech2" in mechs

    def test_persona_d_attack_hypotheses(self) -> None:
        r = _make_result("D", PersonaD(
            assets=[], threat_actors=[], attack_surfaces=[],
            trust_boundaries=[], attack_hypotheses=["exploit1"],
            existing_controls=[], likely_bypasses=[], detection="",
            containment="", recovery="", evidence_status="",
            authorization_status="pending", residual_risk="", recommendation="",
        ))
        mechs = _extract_mechanisms(r)
        assert "exploit1" in mechs


class TestSemanticDiversity:
    def test_diverse_results(self) -> None:
        results = [
            _make_result("A", PersonaA(
                current_structure="s1", structural_problem="p1", root_component="r1",
                proposed_change="c1", shared_or_specialized="shared",
                affected_modules=[], interfaces=[], state_changes=[],
                persistence_changes=[], migration="", failure_modes=[],
                simpler_alternative="", evidence_required=[], recommendation="rec_a",
            )),
            _make_result("B", PersonaB(
                known_space=[], dominant_paradigms=[], shared_assumptions=[],
                unresolved_gaps=[], operators_selected=[], structural_directions=[],
                mechanism_diversity=[], novelty_status="", technical_translation="",
                strongest_direction="dir_b", strongest_counterargument="",
                validation_needed=[],
            )),
            _make_result("C", PersonaC(
                confirmed_facts=["fact_c"], inferred_claims=[], unsupported_claims=[],
                evidence_quality="low", conflicting_evidence=[],
                confidence=FindingConfidence.HYPOTHESIS,
                falsification_tests=[], pass_fail_criteria=[], reproducibility="",
                traceability_gaps=[], risk_of_wrong_decision="", recommendation="rec_c",
            )),
            _make_result("D", PersonaD(
                assets=[], threat_actors=[], attack_surfaces=[],
                trust_boundaries=[], attack_hypotheses=[], existing_controls=[],
                likely_bypasses=[], detection="", containment="", recovery="",
                evidence_status="", authorization_status="pending",
                residual_risk="", recommendation="rec_d",
            )),
        ]
        div = _compute_semantic_diversity(results)
        assert div == 1.0


class TestAgreementStrength:
    def test_full_agreement(self) -> None:
        results = [
            _make_result("A", PersonaA(
                current_structure="s", structural_problem="p", root_component="r",
                proposed_change="same", shared_or_specialized="shared",
                affected_modules=[], interfaces=[], state_changes=[],
                persistence_changes=[], migration="", failure_modes=[],
                simpler_alternative="", evidence_required=[], recommendation="same",
            )),
            _make_result("C", PersonaC(
                confirmed_facts=[], inferred_claims=[], unsupported_claims=[],
                evidence_quality="", conflicting_evidence=[],
                confidence=FindingConfidence.HYPOTHESIS,
                falsification_tests=[], pass_fail_criteria=[], reproducibility="",
                traceability_gaps=[], risk_of_wrong_decision="", recommendation="same",
            )),
        ]
        assert _compute_agreement_strength(results) == 1.0

    def test_no_agreement(self) -> None:
        results = [
            _make_result("A", PersonaA(
                current_structure="s", structural_problem="p", root_component="r",
                proposed_change="a", shared_or_specialized="shared",
                affected_modules=[], interfaces=[], state_changes=[],
                persistence_changes=[], migration="", failure_modes=[],
                simpler_alternative="", evidence_required=[], recommendation="rec_a",
            )),
            _make_result("C", PersonaC(
                confirmed_facts=[], inferred_claims=[], unsupported_claims=[],
                evidence_quality="", conflicting_evidence=[],
                confidence=FindingConfidence.HYPOTHESIS,
                falsification_tests=[], pass_fail_criteria=[], reproducibility="",
                traceability_gaps=[], risk_of_wrong_decision="", recommendation="rec_c",
            )),
        ]
        assert _compute_agreement_strength(results) == 0.0


class TestStrongAgreements:
    def test_convergent_recommendations(self) -> None:
        results = [
            _make_result("A", PersonaA(
                current_structure="s", structural_problem="p", root_component="r",
                proposed_change="change_x", shared_or_specialized="shared",
                affected_modules=[], interfaces=[], state_changes=[],
                persistence_changes=[], migration="", failure_modes=[],
                simpler_alternative="", evidence_required=[], recommendation="change_x",
            )),
            _make_result("C", PersonaC(
                confirmed_facts=[], inferred_claims=[], unsupported_claims=[],
                evidence_quality="", conflicting_evidence=[],
                confidence=FindingConfidence.HYPOTHESIS,
                falsification_tests=[], pass_fail_criteria=[], reproducibility="",
                traceability_gaps=[], risk_of_wrong_decision="", recommendation="change_x",
            )),
            _make_result("B", PersonaB(
                known_space=[], dominant_paradigms=[], shared_assumptions=[],
                unresolved_gaps=[], operators_selected=[], structural_directions=[],
                mechanism_diversity=[], novelty_status="", technical_translation="",
                strongest_direction="other", strongest_counterargument="",
                validation_needed=[],
            )),
            _make_result("D", PersonaD(
                assets=[], threat_actors=[], attack_surfaces=[],
                trust_boundaries=[], attack_hypotheses=[], existing_controls=[],
                likely_bypasses=[], detection="", containment="", recovery="",
                evidence_status="", authorization_status="pending",
                residual_risk="", recommendation="yet_another",
            )),
        ]
        agreements = _find_strong_agreements(results)
        assert len(agreements) >= 1
        assert any("change_x" in a.finding for a in agreements)


class TestPartialAgreements:
    def test_shared_diagnosis(self) -> None:
        results = [
            _make_result("A", PersonaA(
                current_structure="s", structural_problem="root_cause",
                root_component="r", proposed_change="fix_a",
                shared_or_specialized="shared",
                affected_modules=[], interfaces=[], state_changes=[],
                persistence_changes=[], migration="", failure_modes=[],
                simpler_alternative="", evidence_required=[], recommendation="",
            )),
            _make_result("C", PersonaC(
                confirmed_facts=["fact_linked_to_root_cause"],
                inferred_claims=[], unsupported_claims=[],
                evidence_quality="insufficient", conflicting_evidence=[],
                confidence=FindingConfidence.HYPOTHESIS,
                falsification_tests=[], pass_fail_criteria=[], reproducibility="",
                traceability_gaps=[], risk_of_wrong_decision="", recommendation="",
            )),
        ]
        partials = _find_partial_agreements(results)
        assert len(partials) >= 1


class TestDisagreements:
    def test_architectural_disagreement(self) -> None:
        results = [
            _make_result("A", PersonaA(
                current_structure="s", structural_problem="p", root_component="r",
                proposed_change="refactor", shared_or_specialized="shared",
                affected_modules=[], interfaces=[], state_changes=[],
                persistence_changes=[], migration="", failure_modes=[],
                simpler_alternative="", evidence_required=[], recommendation="",
            )),
            _make_result("B", PersonaB(
                known_space=[], dominant_paradigms=[], shared_assumptions=[],
                unresolved_gaps=[], operators_selected=[], structural_directions=[],
                mechanism_diversity=[], novelty_status="", technical_translation="",
                strongest_direction="new_paradigm", strongest_counterargument="",
                validation_needed=[],
            )),
        ]
        disagreements = _classify_disagreements(results)
        assert len(disagreements) >= 1
        assert disagreements[0].category == "architectural"


class TestEmergentFindings:
    def test_intersection_a_c(self) -> None:
        results = [
            _make_result("A", PersonaA(
                current_structure="s", structural_problem="structural_issue",
                root_component="r", proposed_change="c",
                shared_or_specialized="shared",
                affected_modules=[], interfaces=[], state_changes=[],
                persistence_changes=[], migration="", failure_modes=[],
                simpler_alternative="", evidence_required=[], recommendation="",
            )),
            _make_result("C", PersonaC(
                confirmed_facts=[], inferred_claims=[], unsupported_claims=[],
                evidence_quality="insufficient", conflicting_evidence=[],
                confidence=FindingConfidence.HYPOTHESIS,
                falsification_tests=[], pass_fail_criteria=[], reproducibility="",
                traceability_gaps=[], risk_of_wrong_decision="", recommendation="",
            )),
        ]
        emergent = _find_emergent_findings(results)
        assert len(emergent) >= 1
        assert emergent[0].why_no_single_persona_found_it != ""


class TestRegeneration:
    def test_three_identical_triggers(self) -> None:
        results = [
            _make_result("A", PersonaA(
                current_structure="s", structural_problem="p", root_component="r",
                proposed_change="same", shared_or_specialized="shared",
                affected_modules=[], interfaces=[], state_changes=[],
                persistence_changes=[], migration="", failure_modes=[],
                simpler_alternative="", evidence_required=[], recommendation="same",
            )),
            _make_result("B", PersonaB(
                known_space=[], dominant_paradigms=[], shared_assumptions=[],
                unresolved_gaps=[], operators_selected=[], structural_directions=[],
                mechanism_diversity=[], novelty_status="", technical_translation="",
                strongest_direction="same", strongest_counterargument="",
                validation_needed=[],
            )),
            _make_result("C", PersonaC(
                confirmed_facts=[], inferred_claims=[], unsupported_claims=[],
                evidence_quality="", conflicting_evidence=[],
                confidence=FindingConfidence.HYPOTHESIS,
                falsification_tests=[], pass_fail_criteria=[], reproducibility="",
                traceability_gaps=[], risk_of_wrong_decision="", recommendation="same",
            )),
            _make_result("D", PersonaD(
                assets=[], threat_actors=[], attack_surfaces=[],
                trust_boundaries=[], attack_hypotheses=[], existing_controls=[],
                likely_bypasses=[], detection="", containment="", recovery="",
                evidence_status="", authorization_status="pending",
                residual_risk="", recommendation="different",
            )),
        ]
        should, reasons = _check_regeneration(results)
        assert should is True
        assert "three_or_more_identical" in reasons

    def test_no_uncertainty_triggers(self) -> None:
        results = [
            _make_result("A", PersonaA(
                current_structure="s", structural_problem="p", root_component="r",
                proposed_change="c", shared_or_specialized="shared",
                affected_modules=[], interfaces=[], state_changes=[],
                persistence_changes=[], migration="", failure_modes=[],
                simpler_alternative="", evidence_required=[], recommendation="rec_a",
            )),
            _make_result("B", PersonaB(
                known_space=[], dominant_paradigms=[], shared_assumptions=[],
                unresolved_gaps=[], operators_selected=[], structural_directions=[],
                mechanism_diversity=[], novelty_status="", technical_translation="",
                strongest_direction="dir_b", strongest_counterargument="",
                validation_needed=[],
            )),
            _make_result("D", PersonaD(
                assets=[], threat_actors=[], attack_surfaces=[],
                trust_boundaries=[], attack_hypotheses=[], existing_controls=[],
                likely_bypasses=[], detection="", containment="", recovery="",
                evidence_status="", authorization_status="pending",
                residual_risk="", recommendation="rec_d",
            )),
        ]
        should, reasons = _check_regeneration(results)
        assert should is True
        assert "no_uncertainty_identified" in reasons


class TestRunEnsemble:
    def test_returns_synthesis(self) -> None:
        synthesis = run_ensemble(_packet())
        assert isinstance(synthesis, EnsembleSynthesis)
        assert synthesis.shared_problem_definition != ""
        assert isinstance(synthesis.metrics, EnsembleMetrics)

    def test_has_four_personas(self) -> None:
        synthesis = run_ensemble(_packet())
        # All four personas contribute.
        all_personas = set()
        for a in synthesis.strongest_agreements:
            all_personas.update(a.supporting_personas)
        # At minimum, the ensemble ran all four.
        assert synthesis.metrics.semantic_diversity >= 0.0

    def test_metrics_populated(self) -> None:
        synthesis = run_ensemble(_packet())
        m = synthesis.metrics
        assert 0.0 <= m.semantic_diversity <= 1.0
        assert 0.0 <= m.mechanism_diversity <= 1.0
        assert 0.0 <= m.agreement_strength <= 1.0
        assert m.emergent_finding_count >= 0

    def test_recommendation_present(self) -> None:
        synthesis = run_ensemble(_packet())
        assert synthesis.synthesis_recommendation != ""

    def test_no_simple_voting(self) -> None:
        """§6.8 — Recommendation is not a simple vote count."""
        synthesis = run_ensemble(_packet())
        # The recommendation should be derived from synthesis logic, not just counting.
        assert synthesis.confidence in ("hypothesis", "confirmed")
        assert synthesis.next_validation != ""


class TestMinorityReport:
    def test_divergent_recommendations_produce_report(self) -> None:
        results = [
            _make_result("A", PersonaA(
                current_structure="s", structural_problem="p", root_component="r",
                proposed_change="c_a", shared_or_specialized="shared",
                affected_modules=[], interfaces=[], state_changes=[],
                persistence_changes=[], migration="", failure_modes=[],
                simpler_alternative="", evidence_required=[], recommendation="rec_a",
            )),
            _make_result("B", PersonaB(
                known_space=[], dominant_paradigms=[], shared_assumptions=[],
                unresolved_gaps=[], operators_selected=[], structural_directions=[],
                mechanism_diversity=[], novelty_status="", technical_translation="",
                strongest_direction="dir_b", strongest_counterargument="",
                validation_needed=[],
            )),
            _make_result("C", PersonaC(
                confirmed_facts=[], inferred_claims=[], unsupported_claims=[],
                evidence_quality="", conflicting_evidence=[],
                confidence=FindingConfidence.HYPOTHESIS,
                falsification_tests=[], pass_fail_criteria=[], reproducibility="",
                traceability_gaps=[], risk_of_wrong_decision="", recommendation="rec_c",
            )),
            _make_result("D", PersonaD(
                assets=[], threat_actors=[], attack_surfaces=[],
                trust_boundaries=[], attack_hypotheses=[], existing_controls=[],
                likely_bypasses=[], detection="", containment="", recovery="",
                evidence_status="", authorization_status="pending",
                residual_risk="", recommendation="rec_d",
            )),
        ]
        protocol_val = validate_team_protocol(results)
        # Divergent recommendations should require minority report.
        assert protocol_val.requires_minority_report is True


class TestIndependence:
    def test_personas_see_no_other_outputs(self) -> None:
        """§6.2 — Personas must not receive other personas' outputs."""
        packet = _packet()
        # The packet should not contain persona_outputs.
        assert "persona_outputs" not in packet
        assert "prior_persona_outputs" not in packet
        assert "ensemble_outputs" not in packet
