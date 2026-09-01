"""Tests for the six-stage chain (HIPERMEGAPROMPT §7)."""
from __future__ import annotations

from typing import Any

import pytest

from criba.chain import (
    STAGE_TRANSITIONS,
    ChainMemory,
    ChainRunner,
    HumanDecisionRecord,
    RehydrationRequest,
    Stage1Output,
    Stage2Output,
    Stage3Output,
    Stage4Output,
    Stage5Output,
    Stage6Output,
    StageStatus,
)


def _packet() -> dict[str, Any]:
    return {
        "original_query": "How to improve security",
        "mode": "criba",
        "central_problem": "Security gap",
        "desired_outcome": "Reduce risk",
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


class TestStageStatus:
    def test_valid_transitions(self) -> None:
        assert StageStatus.RUNNING in STAGE_TRANSITIONS[StageStatus.PENDING]
        assert StageStatus.AWAITING_HUMAN_REVIEW in STAGE_TRANSITIONS[StageStatus.RUNNING]
        assert StageStatus.APPROVED in STAGE_TRANSITIONS[StageStatus.AWAITING_HUMAN_REVIEW]
        assert StageStatus.COMPLETED in STAGE_TRANSITIONS[StageStatus.APPROVED]

    def test_invalid_transition(self) -> None:
        assert StageStatus.COMPLETED not in STAGE_TRANSITIONS[StageStatus.PENDING]
        assert StageStatus.RUNNING not in STAGE_TRANSITIONS[StageStatus.COMPLETED]


class TestChainMemory:
    def test_fingerprint_stable(self) -> None:
        m = ChainMemory(original_objective="test")
        fp1 = m.fingerprint()
        fp2 = m.fingerprint()
        assert fp1 == fp2

    def test_fingerprint_changes_with_data(self) -> None:
        m1 = ChainMemory(original_objective="test")
        m2 = ChainMemory(original_objective="different")
        assert m1.fingerprint() != m2.fingerprint()


class TestStage1:
    def test_returns_stage1_output(self) -> None:
        runner = ChainRunner()
        memory = ChainMemory()
        output, mem = runner.run_stage(1, memory, _packet())
        assert isinstance(output, Stage1Output)
        assert output.normalized_query == "How to improve security"
        assert output.central_problem == "Security gap"

    def test_memory_condenses_facts(self) -> None:
        runner = ChainRunner()
        memory = ChainMemory()
        _, mem = runner.run_stage(1, memory, _packet())
        assert "fact1" in mem.confirmed_facts
        assert "assumption1" in mem.accepted_assumptions


class TestStage2:
    def test_returns_stage2_output(self) -> None:
        runner = ChainRunner()
        memory = ChainMemory()
        output, _ = runner.run_stage(2, memory, _packet())
        assert isinstance(output, Stage2Output)
        assert "solution1" in output.known_solutions

    def test_memory_condenses_gaps(self) -> None:
        runner = ChainRunner()
        memory = ChainMemory()
        _, mem = runner.run_stage(2, memory, _packet())
        assert "gap1" in mem.evidence_gaps


class TestStage3:
    def test_returns_stage3_output(self) -> None:
        runner = ChainRunner()
        memory = ChainMemory()
        output, _ = runner.run_stage(3, memory, _packet())
        assert isinstance(output, Stage3Output)
        assert len(output.selected_operators) >= 1

    def test_memory_condenses_directions(self) -> None:
        runner = ChainRunner()
        memory = ChainMemory()
        _, mem = runner.run_stage(3, memory, _packet())
        assert len(mem.candidate_directions) >= 1


class TestStage4:
    def test_returns_stage4_output(self) -> None:
        runner = ChainRunner()
        memory = ChainMemory()
        output, _ = runner.run_stage(4, memory, _packet())
        assert isinstance(output, Stage4Output)
        assert len(output.architectures) >= 1

    def test_architecture_has_blackforge_extension(self) -> None:
        runner = ChainRunner()
        memory = ChainMemory()
        output, _ = runner.run_stage(4, memory, _packet())
        arch = output.architectures[0]
        assert "blackforge_extension" in arch
        assert "likely_bypass" in arch["blackforge_extension"]


class TestStage5:
    def test_returns_stage5_output(self) -> None:
        runner = ChainRunner()
        memory = ChainMemory()
        output, _ = runner.run_stage(5, memory, _packet())
        assert isinstance(output, Stage5Output)
        assert len(output.adversarial_reviews) >= 1
        assert len(output.falsification_tests) >= 1

    def test_memory_condenses_surviving(self) -> None:
        runner = ChainRunner()
        memory = ChainMemory()
        # Stage 3 must run first to populate directions.
        _, memory = runner.run_stage(3, memory, _packet())
        _, mem = runner.run_stage(5, memory, _packet())
        assert len(mem.decisions_made) >= 1


class TestStage6:
    def test_returns_stage6_output(self) -> None:
        runner = ChainRunner()
        memory = ChainMemory()
        output, _ = runner.run_stage(6, memory, _packet())
        assert isinstance(output, Stage6Output)
        assert output.executive_summary != ""
        assert output.winning_proposal != ""
        assert output.final_decision != ""

    def test_memory_condenses_final_decision(self) -> None:
        runner = ChainRunner()
        memory = ChainMemory()
        _, memory = runner.run_stage(3, memory, _packet())
        _, memory = runner.run_stage(5, memory, _packet())
        _, mem = runner.run_stage(6, memory, _packet())
        assert len(mem.decisions_made) >= 1


class TestRunChain:
    def test_runs_all_six_stages(self) -> None:
        runner = ChainRunner()
        outputs, memory = runner.run_chain(_packet())
        assert len(outputs) == 6
        assert isinstance(outputs[1], Stage1Output)
        assert isinstance(outputs[6], Stage6Output)

    def test_memory_persists_across_stages(self) -> None:
        runner = ChainRunner()
        outputs, memory = runner.run_chain(_packet())
        assert memory.current_stage == 6
        assert len(memory.confirmed_facts) >= 1
        assert len(memory.decisions_made) >= 1

    def test_chain_id_stable(self) -> None:
        runner = ChainRunner()
        _, memory = runner.run_chain(_packet())
        assert memory.chain_id != ""
        # Same runner, same packet — chain_id is generated per chain.
        _, memory2 = runner.run_chain(_packet())
        # Different chains have different IDs.
        assert memory.chain_id != memory2.chain_id


class TestHumanReview:
    def test_review_reject_stops_chain(self) -> None:
        runner = ChainRunner()
        reviews = {
            2: HumanDecisionRecord(
                chain_id="test",
                stage=2,
                decision="reject",
                rationale="Bad output",
            ),
        }
        outputs, memory = runner.run_chain(_packet(), human_reviews=reviews)
        # Chain stops after stage 2 (reject), so stage 3 is not executed.
        assert 1 in outputs
        assert 2 in outputs  # Stage 2 was executed before review
        assert 3 not in outputs  # Chain stopped, stage 3 not executed

    def test_review_approve_continues_chain(self) -> None:
        runner = ChainRunner()
        reviews = {
            1: HumanDecisionRecord(
                chain_id="test",
                stage=1,
                decision="approve_stage",
                rationale="Looks good",
            ),
        }
        outputs, memory = runner.run_chain(_packet(), human_reviews=reviews)
        assert len(outputs) == 6


class TestRehydration:
    def test_request_rehydration(self) -> None:
        runner = ChainRunner()
        memory = ChainMemory()
        req = runner.request_rehydration(
            memory,
            source_stage=2,
            finding_id="gap1",
            required_detail="More detail on evidence",
            reason="Insufficient for stage 3",
        )
        assert isinstance(req, RehydrationRequest)
        assert req.chain_id == memory.chain_id
        assert req.source_stage == 2
        assert req.finding_id == "gap1"


class TestInvalidStage:
    def test_invalid_stage_raises(self) -> None:
        runner = ChainRunner()
        memory = ChainMemory()
        with pytest.raises(ValueError, match="Fase inválida"):
            runner.run_stage(0, memory, _packet())
        with pytest.raises(ValueError, match="Fase inválida"):
            runner.run_stage(7, memory, _packet())


class TestStageTransitionValidation:
    def test_runner_rejects_invalid_transition(self) -> None:
        runner = ChainRunner()
        with pytest.raises(ValueError, match="Transición inválida"):
            runner._validate_transition(StageStatus.PENDING, StageStatus.COMPLETED)

    def test_runner_accepts_valid_transition(self) -> None:
        runner = ChainRunner()
        # Should not raise.
        runner._validate_transition(StageStatus.PENDING, StageStatus.RUNNING)
