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
