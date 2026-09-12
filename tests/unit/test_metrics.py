"""Tests for quality metrics and feedback (HIPERMEGAPROMPT §13)."""
from __future__ import annotations

from criba.metrics import (
    BlackforgeMetrics,
    EvaluationMetrics,
    ExplicitFeedback,
    GenerationMetrics,
    ImplicitFeedback,
    InputMetrics,
    MetricsCollector,
    ProcessMetrics,
    PromotionStatus,
    ResultMetrics,
)


class TestInputMetrics:
    def test_defaults(self) -> None:
        m = InputMetrics()
        assert m.query_clarity == 0.0
        assert m.evidence_quality == 0.0


class TestGenerationMetrics:
    def test_duplication_rate(self) -> None:
        m = GenerationMetrics(duplication_rate=0.3)
        assert m.duplication_rate == 0.3


class TestMetricsCollector:
    def test_composite_no_data(self) -> None:
        collector = MetricsCollector()
        assert collector.compute_composite() == 0.0

    def test_composite_with_generation(self) -> None:
        collector = MetricsCollector()
        collector.generation_metrics = GenerationMetrics(
            semantic_diversity=0.8,
            relevance=0.9,
        )
        composite = collector.compute_composite()
        assert 0.0 <= composite <= 1.0

    def test_composite_with_all(self) -> None:
        collector = MetricsCollector()
        collector.generation_metrics = GenerationMetrics(
            semantic_diversity=0.7,
            relevance=0.8,
        )
        collector.evaluation_metrics = EvaluationMetrics(
            confidence_calibration=0.9,
        )
        collector.process_metrics = ProcessMetrics(cache_hit_rate=0.6)
        collector.result_metrics = ResultMetrics(human_acceptance=0.85)
        composite = collector.compute_composite()
        assert 0.0 < composite <= 1.0

    def test_detect_drift(self) -> None:
        collector = MetricsCollector()
        collector.generation_metrics = GenerationMetrics(
            semantic_diversity=0.5,  # Below baseline
            relevance=0.9,
        )
        baseline = {"semantic_diversity": 0.8, "relevance": 0.8}
        alerts = collector.detect_drift(baseline)
        assert any("semantic_diversity" in a for a in alerts)

    def test_detect_no_drift(self) -> None:
        collector = MetricsCollector()
        collector.generation_metrics = GenerationMetrics(
            semantic_diversity=0.85,
            relevance=0.9,
        )
        baseline = {"semantic_diversity": 0.8, "relevance": 0.8}
        alerts = collector.detect_drift(baseline)
        assert alerts == []

    def test_promotion_approved(self) -> None:
        collector = MetricsCollector()
        collector.generation_metrics = GenerationMetrics(
            semantic_diversity=0.9,
            relevance=0.9,
        )
        collector.process_metrics = ProcessMetrics(schema_failures=0)
        baseline = {"semantic_diversity": 0.7, "relevance": 0.7}
        status, reasons = collector.evaluate_promotion(baseline)
        assert status == PromotionStatus.APPROVED

    def test_promotion_rejected_for_regressions(self) -> None:
        collector = MetricsCollector()
        collector.generation_metrics = GenerationMetrics(
            semantic_diversity=0.5,
            relevance=0.5,
        )
        collector.process_metrics = ProcessMetrics(schema_failures=0)
        baseline = {"semantic_diversity": 0.9, "relevance": 0.9}
        status, reasons = collector.evaluate_promotion(baseline)
        assert status == PromotionStatus.REJECTED

    def test_promotion_rejected_for_blackforge_regression(self) -> None:
        collector = MetricsCollector()
        collector.generation_metrics = GenerationMetrics(
            semantic_diversity=0.9,
            relevance=0.9,
        )
        collector.blackforge_metrics = BlackforgeMetrics(
            authorization_completeness=0.5,
        )
        collector.process_metrics = ProcessMetrics(schema_failures=0)
        baseline = {"semantic_diversity": 0.7}
        status, reasons = collector.evaluate_promotion(baseline)
        assert status == PromotionStatus.REJECTED
        assert "blackforge_authorization_incomplete" in reasons

    def test_promotion_rejected_for_schema_failures(self) -> None:
        collector = MetricsCollector()
        collector.generation_metrics = GenerationMetrics(
            semantic_diversity=0.9,
            relevance=0.9,
        )
        collector.process_metrics = ProcessMetrics(schema_failures=3)
        baseline = {"semantic_diversity": 0.7}
        status, reasons = collector.evaluate_promotion(baseline)
        assert status == PromotionStatus.REJECTED
        assert "schema_failures_present" in reasons

    def test_promotion_needs_more_data(self) -> None:
        collector = MetricsCollector()
        collector.generation_metrics = GenerationMetrics(
            semantic_diversity=0.7,
            relevance=0.7,
        )
        collector.process_metrics = ProcessMetrics(schema_failures=0)
        baseline = {"semantic_diversity": 0.7, "relevance": 0.7}
        status, reasons = collector.evaluate_promotion(baseline)
        assert status == PromotionStatus.NEEDS_MORE_DATA


class TestExplicitFeedback:
    def test_useful(self) -> None:
        fb = ExplicitFeedback(useful=True, score=0.9, reason="Great idea")
        assert fb.useful is True
        assert fb.score == 0.9


class TestImplicitFeedback:
    def test_opened(self) -> None:
        fb = ImplicitFeedback(idea_opened="idea_1", stage_reviewed=3)
        assert fb.idea_opened == "idea_1"
        assert fb.stage_reviewed == 3


class TestSummarize:
    def test_summary(self) -> None:
        collector = MetricsCollector()
        collector.explicit_feedback = [ExplicitFeedback(useful=True)]
        collector.implicit_feedback = [ImplicitFeedback(idea_opened="idea_1")]
        summary = collector.summarize()
        assert summary["explicit_feedback_count"] == 1
        assert summary["implicit_feedback_count"] == 1
        assert summary["composite"] == 0.0

    def test_explicit_feedback_is_validated_and_recorded(self) -> None:
        collector = MetricsCollector()
        collector.record_explicit_feedback(ExplicitFeedback(useful=True, score=0.8))
        collector.record_implicit_feedback(ImplicitFeedback(idea_opened="idea_1"))
        assert collector.feedback_signal() == 0.8
        assert collector.summarize()["feedback_signal"] == 0.8

    def test_invalid_explicit_score_is_rejected(self) -> None:
        import pytest
        with pytest.raises(ValueError, match="entre 0 y 1"):
            ExplicitFeedback(score=1.1)

    def test_implicit_feedback_does_not_improve_quality_signal(self) -> None:
        collector = MetricsCollector()
        collector.record_implicit_feedback(ImplicitFeedback(idea_saved="idea_1"))
        assert collector.feedback_signal() == 0.0

    def test_gate_and_log_evidence_are_ingested(self) -> None:
        collector = MetricsCollector()
        collector.ingest_gate_report({
            "results": [
                {"gate_id": "G01_schema_valid", "passed": False},
                {"gate_id": "G10_trace_complete", "passed": False},
            ]
        })
        collector.ingest_log_summary({"integrity": {"chain_intact": False}, "retries": 2})
        assert collector.process_metrics is not None
        assert collector.process_metrics.schema_failures == 1
        assert collector.process_metrics.traceability_failures == 2
        assert collector.process_metrics.retries == 2

    def test_quality_breakdown_exposes_formula_and_missing_inputs(self) -> None:
        collector = MetricsCollector()
        collector.generation_metrics = GenerationMetrics(
            relevance=0.8, mechanism_specificity=0.6,
            semantic_diversity=0.7, structural_diversity=0.5,
        )
        breakdown = collector.quality_breakdown()
        assert breakdown["formula_version"] == "quality-score-v1"
        assert breakdown["components"]["diversity"] == 0.6
        assert "feasibility" in breakdown["missing_components"]
        assert 0.0 <= breakdown["score"] <= 1.0

    def test_negative_explicit_feedback_blocks_promotion(self) -> None:
        collector = MetricsCollector()
        collector.generation_metrics = GenerationMetrics(semantic_diversity=0.9, relevance=0.9)
        collector.process_metrics = ProcessMetrics(schema_failures=0)
        collector.record_explicit_feedback(ExplicitFeedback(useful=False, score=0.1))
        status, reasons = collector.evaluate_promotion({"semantic_diversity": 0.7})
        assert status == PromotionStatus.REJECTED
        assert "negative_explicit_feedback" in reasons
