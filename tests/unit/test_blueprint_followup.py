"""Follow-up regressions for the gaps found by the independent audit."""
from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

import criba.ensemble as ensemble_module
from criba.adversarial_self import AdversarialPass, AdversarialSelfReinforcement, ThesisPass
from criba.chain import ChainMemory, ChainRunner, Stage5Output
from criba.latency import (
    BackpressureError,
    BatchFamily,
    GenerationBudget,
    LatencyScheduler,
    ParallelismConfig,
    ProgressiveCandidate,
    SemanticCacheKey,
    promote_candidate,
    validate_candidate_cheap,
)
from criba.metrics import (
    BlackforgeMetrics,
    GenerationMetrics,
    MetricsCollector,
    ProcessMetrics,
    PromotionStatus,
    QualityBaseline,
    ResultMetrics,
)
from criba.personas import TeamProtocol


def test_team_protocol_cannot_be_weakened() -> None:
    with pytest.raises(ValidationError):
        TeamProtocol(minority_report_required=False)


def test_ensemble_regeneration_changes_generation_context(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict[str, Any]] = []

    def fake_run_personas(packet: dict[str, Any], *, backend: Any = None) -> list[Any]:
        calls.append(dict(packet))
        return []

    monkeypatch.setattr(ensemble_module, "run_personas", fake_run_personas)
    monkeypatch.setattr(ensemble_module, "_check_regeneration", lambda results: (True, ["test"]))
    ensemble_module.run_ensemble({"original_query": "q"}, max_regenerations=1)
    assert len(calls) == 2
    assert "_regeneration_attempt" not in calls[0]
    assert calls[1]["_regeneration_attempt"] == 1
    assert calls[1]["_regeneration_instruction"]


def test_adversarial_resolution_evaluates_all_challenges() -> None:
    thesis = ThesisPass(
        problem_definition="p",
        thesis="t",
        supporting_evidence=["e"],
        implementation="implementation",
    )
    adversarial = AdversarialPass(
        thesis_under_attack="t",
        strongest_hidden_assumptions=["assumption"],
        causal_challenges=["causal-1", "causal-2"],
        factual_challenges=["factual-1"],
        evidence_gaps=["gap"],
        simpler_alternatives=["simple alternative"],
        implementation_failures=["implementation-1", "implementation-2"],
        falsification_tests=["falsify mechanism"],
        kill_criteria=["The controlled experiment falsifies the causal mechanism"],
        survivable_parts=["problem definition"],
    )
    resolution = AdversarialSelfReinforcement().resolve(thesis, adversarial)
    assert resolution.failed_challenges == [
        "causal-1",
        "causal-2",
        "implementation-1",
        "implementation-2",
    ]


def test_chain_stage_five_contains_adversarial_reinforcement() -> None:
    output, _ = ChainRunner().run_stage(
        5,
        ChainMemory(current_problem_definition="security gap"),
        {
            "mode": "blackforge",
            "central_problem": "security gap",
            "authorization_state": "pending",
        },
    )
    assert isinstance(output, Stage5Output)
    assert output.kill_criteria
    assert output.survivable_parts
    assert output.residual_risk
    assert output.adversarial_reinforcement["adversarial"]["blackforge_extension"]


def test_early_exit_requires_configured_acceptance_and_quality() -> None:
    budget = GenerationBudget(
        minimum_accepted=3,
        diversity_target=0.7,
        quality_floor=0.5,
        top_score_gap=0.2,
        marginal_novelty_floor=0.1,
        no_improvement_rounds=2,
    )
    assert budget.early_exit(
        0.8,
        0.7,
        accepted_count=2,
        top_score_gap=0.4,
        marginal_novelty=0.2,
        no_improvement_rounds=2,
    ) is False
    assert budget.early_exit(
        0.8,
        0.7,
        accepted_count=3,
        top_score_gap=0.4,
        marginal_novelty=0.2,
        no_improvement_rounds=2,
    ) is True


def test_budget_tracks_target_and_scheduler_tracks_observed_metrics() -> None:
    budget = GenerationBudget(target_idea_count=2, maximum_tokens=1000)
    scheduler = LatencyScheduler(budget=budget)
    scheduler.record_candidate(accepted=True, score=0.8, marginal_novelty=0.9, latency_ms=10, stage="expand")
    scheduler.record_candidate(accepted=False, score=0.7, marginal_novelty=0.2, latency_ms=30, stage="expand")
    scheduler.record_spend(tokens=100, cost=0.4, stage="validate")
    scheduler.record_retry()
    scheduler.record_cancellation()
    metrics = scheduler.finalize_metrics()
    assert budget.target_reached is True
    assert budget.exhausted is True
    assert metrics.p50_stage_latency["expand"] == 10.0
    assert metrics.p95_stage_latency["expand"] == 30.0
    assert metrics.tokens_per_accepted_idea == 100.0
    assert metrics.cost_per_accepted_idea == 0.4
    assert metrics.cancellation_rate > 0.0
    assert metrics.retry_rate == 0.5


def test_cache_key_separates_authorization_and_security_inputs() -> None:
    scheduler = LatencyScheduler()
    granted = SemanticCacheKey(
        context_hash="ctx",
        task_hash="task",
        authorization_state="granted",
        restrictions_hash="r1",
        asset_hash="asset-1",
        threat_hash="threat-1",
        evidence_hash="e1",
        evaluation_criteria_hash="c1",
    )
    revoked = granted.model_copy(update={"authorization_state": "denied"})
    scheduler.put_in_cache(granted, "safe-result")
    assert scheduler.get_from_cache(revoked) is None
    assert scheduler.get_from_cache(granted) == "safe-result"


def test_scheduler_enforces_family_quota_and_generator_slots() -> None:
    scheduler = LatencyScheduler(
        budget=GenerationBudget(minimum_family_count=3),
        parallelism=ParallelismConfig(max_concurrent_generators=1, queue_depth=2),
    )
    batches = scheduler.plan_batches(["a", "b", "c", "d", "e"])
    assert len({batch.family for batch in batches}) >= 3
    assert scheduler.can_queue(2) is True
    assert scheduler.can_queue(3) is False
    with scheduler.generator_slot():
        with pytest.raises(BackpressureError):
            with scheduler.generator_slot():
                pass
    review_scheduler = LatencyScheduler(
        budget=GenerationBudget(human_review_required=True),
    )
    assert review_scheduler.budget.review_ready is False
    with pytest.raises(RuntimeError, match="human_review_required"):
        review_scheduler.assert_review_ready()
    review_scheduler.mark_human_review_completed()
    review_scheduler.assert_review_ready()


def test_cheap_validation_rejects_unsafe_or_incomplete_outline() -> None:
    valid = validate_candidate_cheap(
        {
            "id": "idea-1",
            "description": "Detect anomalous requests before authorization.",
            "causal_mechanism": "Compare request provenance against a signed policy.",
            "evidence": ["auth-log"],
            "risk": "false positives",
            "context_hash": "ctx",
        },
        expected_context_hash="ctx",
    )
    assert valid.valid is True
    candidate = ProgressiveCandidate(
        candidate_id="idea-1",
        one_line="Detect anomalous requests.",
        mechanism="Compare provenance against policy.",
        anchors=["auth-log"],
        primary_risk="false positives",
        context_hash="ctx",
    )
    assert candidate.full_architecture is None
    promoted = promote_candidate(
        candidate,
        valid,
        {"stages": ["outline", "full"], "experiment": "controlled"},
    )
    assert promoted.full_architecture["experiment"] == "controlled"
    invalid = validate_candidate_cheap(
        {
            "id": "idea-1",
            "description": "Detect anomalous requests.",
            "causal_mechanism": "use AI",
            "evidence": [],
            "risk": "",
            "violation": True,
            "context_hash": "other",
        },
        seen_ids={"idea-1"},
        expected_context_hash="ctx",
    )
    assert invalid.valid is False
    assert {
        "anchors_missing",
        "schema_or_empty",
        "duplicate_id",
        "violation",
        "generic_mechanism",
        "context_mismatch",
    } <= set(invalid.failures)
    with pytest.raises(ValueError, match="candidate_failed_cheap_validation"):
        promote_candidate(candidate, invalid, {})


def test_metrics_use_weighted_breakdown_and_configurable_drift() -> None:
    collector = MetricsCollector()
    collector.generation_metrics = GenerationMetrics(
        relevance=1.0,
        mechanism_specificity=1.0,
        semantic_diversity=1.0,
        structural_diversity=1.0,
    )
    assert collector.compute_composite() == collector.quality_breakdown()["score"]
    collector.generation_metrics = GenerationMetrics(semantic_diversity=0.75)
    baseline = QualityBaseline(metrics={"semantic_diversity": 0.8}, sample_size=10)
    assert collector.detect_drift(baseline, threshold=0.2) == []
    assert collector.detect_drift(baseline, threshold=0.05)


def test_metrics_record_human_review_and_promotion_fails_closed() -> None:
    collector = MetricsCollector()
    collector.blackforge_metrics = BlackforgeMetrics(authorization_completeness=1.0)
    collector.process_metrics = ProcessMetrics(schema_failures=0)
    collector.result_metrics = ResultMetrics(
        ideas_validated=10,
        human_acceptance=0.3,
    )
    status, reasons = collector.evaluate_promotion({"semantic_diversity": 0.2})
    assert status == PromotionStatus.REJECTED
    assert "human_review_required" in reasons
    assert "human_acceptance_below_threshold" in reasons
    process = collector.record_human_review(125.0, returned_to_previous=True)
    assert process.human_review_time_ms == 125.0
    assert process.return_to_previous_rate == 1.0
    status, reasons = collector.evaluate_promotion({"semantic_diversity": 0.2})
    assert status == PromotionStatus.REJECTED
    assert "human_acceptance_below_threshold" in reasons
    assert "human_review_required" not in reasons


def test_metrics_capture_versioned_baseline() -> None:
    collector = MetricsCollector()
    collector.generation_metrics = GenerationMetrics(relevance=0.9)
    baseline = collector.capture_baseline(sample_size=12, source_hash="tree-hash")
    assert isinstance(baseline, QualityBaseline)
    assert baseline.version == "quality-baseline-v1"
    assert baseline.sample_size == 12
    assert baseline.metrics["relevance"] == 0.9
    assert baseline.source_hash == "tree-hash"
