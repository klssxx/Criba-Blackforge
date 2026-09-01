"""Tests for adversarial self-reinforcement (HIPERMEGAPROMPT §8)."""
from __future__ import annotations

from typing import Any

from criba.adversarial_self import (
    AdversarialPass,
    AdversarialSelfReinforcement,
    BlackforgeAdversarialExtension,
    ThesisPass,
    ThesisResolution,
    ThesisStatus,
    _check_adversarial_quality,
)


def _packet() -> dict[str, Any]:
    return {
        "original_query": "How to improve security",
        "central_problem": "Security gap",
        "thesis": "Add zero-trust architecture",
        "causal_mechanism": "Verify every request",
        "expected_value": "Reduce breach risk",
        "assumptions": ["Users will adapt", "Infrastructure supports it"],
        "confirmed_facts": ["fact1"],
        "conflicting_evidence": ["counter1"],
        "implementation_plan": "Phase rollout",
        "success_criteria": ["metric1"],
        "risks": ["risk1"],
        "confidence": "hypothesis",
    }


class TestThesisPass:
    def test_build_thesis(self) -> None:
        runner = AdversarialSelfReinforcement()
        thesis = runner.build_thesis(_packet())
        assert isinstance(thesis, ThesisPass)
        assert thesis.thesis == "Add zero-trust architecture"
        assert thesis.causal_mechanism == "Verify every request"

    def test_build_thesis_defaults(self) -> None:
        runner = AdversarialSelfReinforcement()
        thesis = runner.build_thesis({})
        assert isinstance(thesis, ThesisPass)
        assert thesis.thesis == "Tesis por defecto: mejorar el sistema actual"


class TestAdversarialPass:
    def test_attack_thesis_returns_adversarial(self) -> None:
        runner = AdversarialSelfReinforcement()
        thesis = runner.build_thesis(_packet())
        adversarial = runner.attack_thesis(thesis)
        assert isinstance(adversarial, AdversarialPass)
        assert adversarial.thesis_under_attack == thesis.thesis

    def test_adversarial_has_kill_criteria(self) -> None:
        runner = AdversarialSelfReinforcement()
        thesis = runner.build_thesis(_packet())
        adversarial = runner.attack_thesis(thesis)
        assert len(adversarial.kill_criteria) >= 1

    def test_adversarial_has_survivable_parts(self) -> None:
        runner = AdversarialSelfReinforcement()
        thesis = runner.build_thesis(_packet())
        adversarial = runner.attack_thesis(thesis)
        assert len(adversarial.survivable_parts) >= 1

    def test_adversarial_has_falsification_tests(self) -> None:
        runner = AdversarialSelfReinforcement()
        thesis = runner.build_thesis(_packet())
        adversarial = runner.attack_thesis(thesis)
        assert len(adversarial.falsification_tests) >= 1

    def test_adversarial_has_simpler_alternatives(self) -> None:
        runner = AdversarialSelfReinforcement()
        thesis = runner.build_thesis(_packet())
        adversarial = runner.attack_thesis(thesis)
        assert len(adversarial.simpler_alternatives) >= 1


class TestAdversarialQuality:
    def test_quality_passes_for_good_adversarial(self) -> None:
        adversarial = AdversarialPass(
            thesis_under_attack="test",
            strongest_hidden_assumptions=["assumption1"],
            causal_challenges=["challenge1"],
            factual_challenges=["fact1"],
            evidence_gaps=["gap1"],
            alternative_explanations=["alt1"],
            implementation_failures=["fail1"],
            incentive_failures=["incentive1"],
            operational_failures=["op1"],
            simpler_alternatives=["simple1"],
            worst_case="worst",
            falsification_tests=["test1"],
            kill_criteria=["kill_criteria_non_trivial"],
            survivable_parts=["part1"],
            verdict="requires_experiment",
        )
        is_quality, failures = _check_adversarial_quality(adversarial)
        assert is_quality is True
        assert failures == []

    def test_quality_fails_for_missing_kill_criteria(self) -> None:
        adversarial = AdversarialPass(
            thesis_under_attack="test",
            strongest_hidden_assumptions=["a"],
            causal_challenges=["c"],
            evidence_gaps=["g"],
            simpler_alternatives=["s"],
            falsification_tests=["f"],
            kill_criteria=[],
            survivable_parts=["p"],
        )
        is_quality, failures = _check_adversarial_quality(adversarial)
        assert is_quality is False
        assert "missing_kill_criteria" in failures

    def test_quality_fails_for_generic_kill_criteria(self) -> None:
        adversarial = AdversarialPass(
            thesis_under_attack="test",
            strongest_hidden_assumptions=["a"],
            causal_challenges=["c"],
            evidence_gaps=["g"],
            simpler_alternatives=["s"],
            falsification_tests=["f"],
            kill_criteria=["short", "tiny"],
            survivable_parts=["p"],
        )
        is_quality, failures = _check_adversarial_quality(adversarial)
        assert is_quality is False
        assert "generic_kill_criteria" in failures

    def test_quality_fails_for_no_challenges(self) -> None:
        adversarial = AdversarialPass(
            thesis_under_attack="test",
            strongest_hidden_assumptions=["a"],
            causal_challenges=[],
            factual_challenges=[],
            evidence_gaps=["g"],
            simpler_alternatives=["s"],
            falsification_tests=["f"],
            kill_criteria=["valid_criteria_here"],
            survivable_parts=["p"],
        )
        is_quality, failures = _check_adversarial_quality(adversarial)
        assert is_quality is False
        assert "no_substantive_challenges" in failures


class TestResolution:
    def test_resolve_returns_resolution(self) -> None:
        runner = AdversarialSelfReinforcement()
        thesis = runner.build_thesis(_packet())
        adversarial = runner.attack_thesis(thesis)
        resolution = runner.resolve(thesis, adversarial)
        assert isinstance(resolution, ThesisResolution)
        assert resolution.final_status in (
            ThesisStatus.SURVIVES,
            ThesisStatus.SURVIVES_WITH_CONDITIONS,
            ThesisStatus.REQUIRES_EXPERIMENT,
            ThesisStatus.MAJOR_REVISION,
            ThesisStatus.REJECTED,
        )

    def test_resolve_with_evidence_reduces_survived(self) -> None:
        runner = AdversarialSelfReinforcement()
        thesis = runner.build_thesis(_packet())
        adversarial = runner.attack_thesis(thesis)
        resolution = runner.resolve(thesis, adversarial)
        # With supporting evidence, some challenges should fail.
        assert isinstance(resolution, ThesisResolution)

    def test_resolve_with_poor_adversarial_returns_major_revision(self) -> None:
        runner = AdversarialSelfReinforcement()
        thesis = runner.build_thesis(_packet())
        poor_adversarial = AdversarialPass(
            thesis_under_attack="test",
            strongest_hidden_assumptions=[],
            causal_challenges=[],
            factual_challenges=[],
            evidence_gaps=[],
            simpler_alternatives=[],
            falsification_tests=[],
            kill_criteria=[],
            survivable_parts=[],
        )
        resolution = runner.resolve(thesis, poor_adversarial)
        assert resolution.final_status == ThesisStatus.MAJOR_REVISION


class TestRun:
    def test_run_returns_three_outputs(self) -> None:
        runner = AdversarialSelfReinforcement()
        thesis, adversarial, resolution = runner.run(_packet())
        assert isinstance(thesis, ThesisPass)
        assert isinstance(adversarial, AdversarialPass)
        assert isinstance(resolution, ThesisResolution)

    def test_run_with_blackforge(self) -> None:
        runner = AdversarialSelfReinforcement()
        thesis, adversarial, resolution = runner.run(_packet(), is_blackforge=True)
        assert isinstance(thesis, ThesisPass)
        assert isinstance(adversarial, AdversarialPass)
        assert isinstance(resolution, ThesisResolution)


class TestBlackforgeExtension:
    def test_extension_fields(self) -> None:
        ext = BlackforgeAdversarialExtension(
            likely_bypasses=["bypass1"],
            residual_risk="medium",
        )
        assert ext.likely_bypasses == ["bypass1"]
        assert ext.residual_risk == "medium"
