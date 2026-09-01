"""Tests for the hybrid orchestrator (end-to-end pipeline)."""
from __future__ import annotations

from typing import Any

from criba.hybrid import HybridOrchestrator, HybridResult, run_hybrid


def _packet() -> dict[str, Any]:
    return {
        "original_query": "How to improve security",
        "mode": "criba",
        "central_problem": "Security gap in API",
        "desired_outcome": "Reduce breach risk",
        "scope": "api",
        "actors": ["dev", "sec"],
        "constraints": ["no downtime"],
        "confirmed_facts": ["fact1"],
        "assumptions": ["assumption1"],
        "unknowns": ["unknown1"],
        "success_criteria": ["metric1"],
        "protected_assets": ["data"],
        "threat_actors": ["attacker"],
        "authorization_state": "pending",
        "innovation": {
            "known_space": ["solution1"],
            "dominant_paradigms": ["paradigm1"],
            "known_failures": ["failure1"],
            "unresolved_gaps": ["gap1"],
            "assumptions": ["assumption1"],
            "opportunity_zones": ["zone1"],
            "ruptures": [{"result": "rupture1"}, {"result": "rupture2"}],
            "assumptions_to_break": ["assumption1"],
            "solution_families": ["family1"],
            "structural_differences": ["diff1"],
            "most_promising": ["promising1"],
            "most_disruptive": ["disruptive1"],
        },
    }


class TestHybridResult:
    def test_defaults(self) -> None:
        result = HybridResult()
        assert result.run_id != ""
        assert result.error is None


class TestRunHybrid:
    def test_returns_hybrid_result(self) -> None:
        result = run_hybrid(_packet())
        assert isinstance(result, HybridResult)

    def test_completes_all_stages(self) -> None:
        result = run_hybrid(_packet())
        assert "ensemble" in result.pipeline_stages_completed
        assert "chain" in result.pipeline_stages_completed
        assert "adversarial" in result.pipeline_stages_completed

    def test_has_ensemble_output(self) -> None:
        result = run_hybrid(_packet())
        assert result.ensemble is not None
        assert result.ensemble.shared_problem_definition != ""

    def test_has_chain_outputs(self) -> None:
        result = run_hybrid(_packet())
        assert len(result.chain_outputs) == 6

    def test_has_chain_memory(self) -> None:
        result = run_hybrid(_packet())
        assert result.chain_memory is not None
        assert result.chain_memory.chain_id != ""

    def test_has_adversarial_output(self) -> None:
        result = run_hybrid(_packet())
        assert result.thesis is not None
        assert result.adversarial is not None
        assert result.resolution is not None

    def test_has_final_recommendation(self) -> None:
        result = run_hybrid(_packet())
        assert result.final_recommendation != ""

    def test_has_confidence(self) -> None:
        result = run_hybrid(_packet())
        assert result.final_confidence in ("confirmed", "hypothesis", "rejected")

    def test_duration_recorded(self) -> None:
        result = run_hybrid(_packet())
        assert result.total_duration_ms >= 0.0

    def test_no_error(self) -> None:
        result = run_hybrid(_packet())
        assert result.error is None

    def test_session_id_present(self) -> None:
        result = run_hybrid(_packet())
        assert result.session_id != ""


class TestHybridOrchestrator:
    def test_with_logging_disabled(self) -> None:
        orchestrator = HybridOrchestrator(enable_logging=False)
        result = orchestrator.run(_packet())
        assert result.error is None
        assert len(result.pipeline_stages_completed) == 3

    def test_with_metrics_disabled(self) -> None:
        orchestrator = HybridOrchestrator(enable_metrics=False)
        result = orchestrator.run(_packet())
        assert result.error is None

    def test_chain_memory_seeded_from_ensemble(self) -> None:
        orchestrator = HybridOrchestrator(enable_logging=False)
        result = orchestrator.run(_packet())
        memory = result.chain_memory
        assert memory is not None
        # Memory should have findings from ensemble.
        assert len(memory.key_findings) >= 1
        assert len(memory.candidate_directions) >= 1

    def test_adversarial_packet_built_from_chain(self) -> None:
        orchestrator = HybridOrchestrator(enable_logging=False)
        result = orchestrator.run(_packet())
        assert result.thesis is not None
        assert result.thesis.thesis != ""

    def test_blackforge_mode(self) -> None:
        packet = _packet()
        packet["mode"] = "blackforge"
        result = run_hybrid(packet)
        assert result.error is None
        assert "adversarial" in result.pipeline_stages_completed


class TestPipelineStages:
    def test_ensemble_produces_agreements(self) -> None:
        result = run_hybrid(_packet())
        assert result.ensemble is not None
        # Ensemble should produce at least one agreement or emergent finding.
        assert (
            len(result.ensemble.strongest_agreements) >= 1
            or len(result.ensemble.emergent_findings) >= 1
        )

    def test_chain_produces_final_decision(self) -> None:
        result = run_hybrid(_packet())
        stage6 = result.chain_outputs.get(6)
        assert stage6 is not None
        assert hasattr(stage6, "final_decision")

    def test_adversarial_produces_verdict(self) -> None:
        result = run_hybrid(_packet())
        assert result.resolution is not None
        assert result.resolution.final_status in (
            "survives",
            "survives_with_conditions",
            "requires_experiment",
            "major_revision",
            "rejected",
        )
