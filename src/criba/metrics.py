"""Quality metrics and continuous feedback (HIPERMEGAPROMPT §13).

Collects and aggregates metrics from gates (P7), logs (P8), ensemble (P3),
latency (P9), and process outcomes. Provides explicit/implicit feedback,
drift detection, and promotion gates.
"""
from __future__ import annotations

import math
from collections.abc import Mapping
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

# ---------------------------------------------------------------------------
# Metric categories (§13.2–§13.7)
# ---------------------------------------------------------------------------

class InputMetrics(BaseModel):
    """§13.2 — Input quality indicators."""

    model_config = ConfigDict(extra="forbid")

    query_clarity: float = 0.0  # 0–1
    context_completeness: float = 0.0
    unknown_count: int = 0
    constraint_conflicts: int = 0
    authorization_state: str = "pending"
    evidence_quality: float = 0.0
    space_coverage: float = 0.0


class GenerationMetrics(BaseModel):
    """§13.3 — Generation quality indicators."""

    model_config = ConfigDict(extra="forbid")

    relevance: float = 0.0
    anchor_completeness: float = 0.0
    mechanism_specificity: float = 0.0
    semantic_diversity: float = 0.0
    structural_diversity: float = 0.0
    novelty_internal: float = 0.0
    duplication_rate: float = 0.0
    invalid_output_rate: float = 0.0
    regeneration_rate: float = 0.0


class EvaluationMetrics(BaseModel):
    """§13.4 — Evaluation quality indicators."""

    model_config = ConfigDict(extra="forbid")

    inter_evaluator_consistency: float = 0.0
    ranking_stability: float = 0.0
    justification_score: float = 0.0
    human_correlation: float = 0.0
    weight_sensitivity: float = 0.0
    arbitrary_score_rate: float = 0.0
    false_winner_rate: float = 0.0
    confidence_calibration: float = 0.0


class BlackforgeMetrics(BaseModel):
    """§13.5 — Blackforge-specific quality indicators."""

    model_config = ConfigDict(extra="forbid")

    authorization_completeness: float = 0.0
    asset_coverage: float = 0.0
    threat_coverage: float = 0.0
    attack_surface_coverage: float = 0.0
    trust_boundary_coverage: float = 0.0
    evidence_quality: float = 0.0
    bypass_depth: float = 0.0
    detection_quality: float = 0.0
    containment_quality: float = 0.0
    recovery_quality: float = 0.0
    residual_risk_visibility: float = 0.0
    safe_validation_quality: float = 0.0


class ProcessMetrics(BaseModel):
    """§13.6 — Process metrics."""

    model_config = ConfigDict(extra="forbid")

    latency_per_stage: dict[str, float] = Field(default_factory=dict)
    tokens_total: int = 0
    cost: float = 0.0
    cache_hit_rate: float = 0.0
    retries: int = 0
    cancellations: int = 0
    human_review_time_ms: float = 0.0
    return_to_previous_rate: float = 0.0
    context_length: int = 0
    summarization_loss: float = 0.0
    schema_failures: int = 0
    traceability_failures: int = 0


class ResultMetrics(BaseModel):
    """§13.7 — Outcome metrics."""

    model_config = ConfigDict(extra="forbid")

    ideas_implemented: int = 0
    ideas_validated: int = 0
    experiment_pass_rate: float = 0.0
    real_impact: float = 0.0
    savings: float = 0.0
    risk_reduction: float = 0.0
    human_acceptance: float = 0.0
    abandonment_rate: float = 0.0
    regressions: int = 0
    reuse_count: int = 0


# ---------------------------------------------------------------------------
# Feedback (§13.8–§13.9)
# ---------------------------------------------------------------------------

class ExplicitFeedback(BaseModel):
    """§13.8 — Explicit user feedback."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    useful: bool | None = None
    score: float | None = None  # 0–1
    reason: str = ""
    correction: str = ""
    preferred_idea: str = ""
    missed_risk: str = ""
    missing_context: str = ""
    actual_outcome: str = ""

    @field_validator("score")
    @classmethod
    def _score_in_range(cls, value: float | None) -> float | None:
        if value is not None and not 0.0 <= value <= 1.0:
            raise ValueError("score debe estar entre 0 y 1")
        return value


class ImplicitFeedback(BaseModel):
    """§13.9 — Implicit feedback (used with caution)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    idea_opened: str = ""
    idea_saved: str = ""
    idea_discarded: str = ""
    idea_implemented: str = ""
    stage_reviewed: int = 0
    edit_distance: int = 0
    abandoned_at_stage: int = 0


# ---------------------------------------------------------------------------
# Promotion status (§13.13)
# ---------------------------------------------------------------------------

class PromotionStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_MORE_DATA = "needs_more_data"


class QualityBaseline(BaseModel):
    """Versioned numeric baseline used for drift and promotion decisions."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    version: str = "quality-baseline-v1"
    metrics: dict[str, float] = Field(default_factory=dict)
    sample_size: int = 0
    source_hash: str = ""


QUALITY_FORMULA_VERSION = "quality-score-v1"
QUALITY_WEIGHTS: dict[str, float] = {
    "relevance": 0.20,
    "mechanism": 0.15,
    "evidence": 0.20,
    "diversity": 0.15,
    "feasibility": 0.10,
    "risk": 0.10,
    "traceability": 0.10,
}


# ---------------------------------------------------------------------------
# MetricsCollector
# ---------------------------------------------------------------------------

class MetricsCollector:
    """§13 — Aggregates metrics from all layers."""

    def __init__(
        self,
        *,
        drift_threshold: float = 0.20,
        promotion_threshold: float = 0.05,
    ) -> None:
        if not 0.0 <= drift_threshold <= 1.0:
            raise ValueError("drift_threshold debe estar entre 0 y 1")
        if not 0.0 <= promotion_threshold <= 1.0:
            raise ValueError("promotion_threshold debe estar entre 0 y 1")
        self.drift_threshold = drift_threshold
        self.promotion_threshold = promotion_threshold
        self.input_metrics: InputMetrics | None = None
        self.generation_metrics: GenerationMetrics | None = None
        self.evaluation_metrics: EvaluationMetrics | None = None
        self.blackforge_metrics: BlackforgeMetrics | None = None
        self.process_metrics: ProcessMetrics | None = None
        self.result_metrics: ResultMetrics | None = None
        self.explicit_feedback: list[ExplicitFeedback] = []
        self.implicit_feedback: list[ImplicitFeedback] = []
        self._human_review_count = 0
        self._return_to_previous_count = 0

    def record_explicit_feedback(self, feedback: ExplicitFeedback) -> None:
        """§13.8 — Store user feedback as an immutable typed record."""
        self.explicit_feedback.append(feedback)

    def record_implicit_feedback(self, feedback: ImplicitFeedback) -> None:
        """§13.9 — Store behavior signals without treating clicks as quality."""
        self.implicit_feedback.append(feedback)

    def record_human_review(
        self,
        duration_ms: float,
        *,
        returned_to_previous: bool = False,
    ) -> ProcessMetrics:
        """Record HITL review time and phase returns as process evidence."""
        if duration_ms < 0:
            raise ValueError("duration_ms no puede ser negativo")
        self._human_review_count += 1
        if returned_to_previous:
            self._return_to_previous_count += 1
        current = self.process_metrics or ProcessMetrics()
        self.process_metrics = current.model_copy(update={
            "human_review_time_ms": current.human_review_time_ms + duration_ms,
            "return_to_previous_rate": (
                self._return_to_previous_count / self._human_review_count
            ),
        })
        return self.process_metrics

    @staticmethod
    def _baseline_metrics(
        baseline: Mapping[str, float] | QualityBaseline,
    ) -> Mapping[str, float]:
        """Accept either a raw golden mapping or a versioned baseline."""
        return baseline.metrics if isinstance(baseline, QualityBaseline) else baseline

    def capture_baseline(
        self,
        *,
        sample_size: int = 0,
        source_hash: str = "",
        version: str = "quality-baseline-v1",
    ) -> QualityBaseline:
        """Capture the current numeric metrics as an explicit golden baseline."""
        if sample_size < 0:
            raise ValueError("sample_size no puede ser negativo")
        return QualityBaseline(
            version=version,
            metrics=self._flatten(),
            sample_size=sample_size,
            source_hash=source_hash,
        )

    def feedback_signal(self) -> float:
        """Return only explicit feedback as a quality signal.

        Implicit interaction data remains available for analysis but cannot
        silently improve the quality score (§13.9).
        """
        values: list[float] = []
        for feedback in self.explicit_feedback:
            if feedback.score is not None:
                values.append(feedback.score)
            elif feedback.useful is not None:
                values.append(1.0 if feedback.useful else 0.0)
        return math.fsum(values) / len(values) if values else 0.0

    def ingest_gate_report(self, report: Any) -> None:
        """§13.10 — Import executed gate evidence into process metrics."""
        raw = report.to_dict() if hasattr(report, "to_dict") else dict(report)
        results = raw.get("results") or []
        schema_failures = sum(
            1 for item in results
            if not item.get("passed", False)
            and item.get("gate_id") in {"G01_schema_valid", "G12_output_contract_valid"}
        )
        traceability_failures = sum(
            1 for item in results
            if not item.get("passed", False)
            and item.get("gate_id") == "G10_trace_complete"
        )
        current = self.process_metrics or ProcessMetrics()
        self.process_metrics = current.model_copy(update={
            "schema_failures": current.schema_failures + schema_failures,
            "traceability_failures": current.traceability_failures + traceability_failures,
        })

    def ingest_log_summary(self, summary: Mapping[str, Any]) -> None:
        """§13.10 — Import retry and cold-reconstruction evidence."""
        current = self.process_metrics or ProcessMetrics()
        integrity = summary.get("integrity", summary)
        integrity_failures = 0 if integrity.get("chain_intact", True) else 1
        self.process_metrics = current.model_copy(update={
            "retries": current.retries + int(summary.get("retries", 0)),
            "cancellations": current.cancellations + int(summary.get("cancellations", 0)),
            "traceability_failures": current.traceability_failures + integrity_failures,
        })

    def quality_breakdown(self) -> dict[str, Any]:
        """§13.15 — Visible weighted quality formula; missing inputs are explicit."""
        components: dict[str, float] = {}
        if self.generation_metrics:
            components["relevance"] = self.generation_metrics.relevance
            components["mechanism"] = self.generation_metrics.mechanism_specificity
            components["diversity"] = math.fsum((
                self.generation_metrics.semantic_diversity,
                self.generation_metrics.structural_diversity,
            )) / 2.0
        if self.input_metrics:
            components["evidence"] = self.input_metrics.evidence_quality
        elif self.blackforge_metrics:
            components["evidence"] = self.blackforge_metrics.evidence_quality
        if self.blackforge_metrics:
            components["risk"] = self.blackforge_metrics.safe_validation_quality
        if self.process_metrics:
            components["traceability"] = 1.0 if (
                self.process_metrics.schema_failures == 0
                and self.process_metrics.traceability_failures == 0
            ) else 0.0
        weights = {key: QUALITY_WEIGHTS[key] for key in components}
        weight_total = math.fsum(weights.values())
        score = (
            math.fsum(components[key] * weights[key] for key in components) / weight_total
            if weight_total else 0.0
        )
        return {
            "formula_version": QUALITY_FORMULA_VERSION,
            "components": components,
            "weights": weights,
            "score": score,
            "missing_components": [key for key in QUALITY_WEIGHTS if key not in components],
        }

    def compute_composite(self) -> float:
        """§13.15 — Return the visible weighted quality score."""
        return float(self.quality_breakdown()["score"])

    def detect_drift(
        self,
        baseline: Mapping[str, float] | QualityBaseline,
        *,
        threshold: float | None = None,
        per_metric_thresholds: Mapping[str, float] | None = None,
        directions: Mapping[str, str] | None = None,
    ) -> list[str]:
        """§13.12 — Detect configurable quality drift against a golden baseline."""
        default_threshold = self.drift_threshold if threshold is None else threshold
        if not 0.0 <= default_threshold <= 1.0:
            raise ValueError("threshold debe estar entre 0 y 1")
        alerts: list[str] = []
        current = self._flatten()
        baseline_metrics = self._baseline_metrics(baseline)
        lower_is_better = {
            "duplication_rate",
            "invalid_output_rate",
            "arbitrary_score_rate",
            "false_winner_rate",
            "latency_per_stage",
            "retries",
            "cancellations",
            "summarization_loss",
            "abandonment_rate",
            "regressions",
        }
        for key, base_val in baseline_metrics.items():
            cur_val = current.get(key)
            if cur_val is None:
                continue
            limit = (
                per_metric_thresholds.get(key, default_threshold)
                if per_metric_thresholds
                else default_threshold
            )
            if not 0.0 <= limit <= 1.0:
                raise ValueError("cada threshold debe estar entre 0 y 1")
            direction = (directions or {}).get(
                key,
                "lower_is_better" if key in lower_is_better else "higher_is_better",
            )
            changed = (
                cur_val > base_val * (1.0 + limit)
                if direction == "lower_is_better"
                else cur_val < base_val * (1.0 - limit)
            )
            if changed:
                alerts.append(f"drift:{key}:{base_val:.2f}->{cur_val:.2f}")
        return alerts

    def _flatten(self) -> dict[str, float]:
        """Flatten all numeric metrics into a single dict."""
        flat: dict[str, float] = {}
        for metrics in (
            self.input_metrics,
            self.generation_metrics,
            self.evaluation_metrics,
            self.blackforge_metrics,
            self.process_metrics,
            self.result_metrics,
        ):
            if metrics:
                for k, v in metrics.model_dump().items():
                    if isinstance(v, (int, float)):
                        flat[k] = float(v)
        return dict(flat)

    def evaluate_promotion(
        self,
        baseline: Mapping[str, float] | QualityBaseline,
        *,
        threshold: float | None = None,
        min_human_acceptance: float = 0.5,
        require_human_review: bool = False,
        minimum_sample_size: int = 0,
    ) -> tuple[PromotionStatus, list[str]]:
        """§13.13 — Decide promotion with regression and HITL fail-closed gates."""
        if not 0.0 <= min_human_acceptance <= 1.0:
            raise ValueError("min_human_acceptance debe estar entre 0 y 1")
        if minimum_sample_size < 0:
            raise ValueError("minimum_sample_size no puede ser negativo")
        change_threshold = self.promotion_threshold if threshold is None else threshold
        if not 0.0 <= change_threshold <= 1.0:
            raise ValueError("threshold debe estar entre 0 y 1")
        reasons: list[str] = []
        current = self._flatten()
        baseline_metrics = self._baseline_metrics(baseline)

        # Blackforge must not degrade and requires an observed HITL review.
        if self.blackforge_metrics:
            if self.blackforge_metrics.authorization_completeness < 1.0:
                reasons.append("blackforge_authorization_incomplete")
            require_human_review = True

        # Must not break traceability.
        if self.process_metrics:
            if self.process_metrics.schema_failures > 0:
                reasons.append("schema_failures_present")
            if self.process_metrics.traceability_failures > 0:
                reasons.append("traceability_failures_present")

        if require_human_review and (
            self.process_metrics is None
            or self.process_metrics.human_review_time_ms <= 0
        ):
            reasons.append("human_review_required")

        if self.result_metrics:
            if self.result_metrics.human_acceptance < min_human_acceptance:
                reasons.append("human_acceptance_below_threshold")
            if self.result_metrics.regressions > 0:
                reasons.append("result_regressions_present")
            sample_size = max(
                self.result_metrics.ideas_validated,
                self.result_metrics.ideas_implemented,
            )
            if sample_size < minimum_sample_size:
                reasons.append("insufficient_sample_size")
        elif minimum_sample_size > 0:
            reasons.append("result_metrics_required")

        # Explicit user feedback is a promotion signal; clicks are not.
        if self.explicit_feedback and self.feedback_signal() < 0.5:
            reasons.append("negative_explicit_feedback")

        if reasons:
            return PromotionStatus.REJECTED, reasons

        # Count improvements and regressions using the configurable threshold.
        improvements = 0
        regressions = 0
        for key, base_val in baseline_metrics.items():
            cur_val = current.get(key)
            if cur_val is None:
                continue
            if cur_val > base_val * (1.0 + change_threshold):
                improvements += 1
            elif cur_val < base_val * (1.0 - change_threshold):
                regressions += 1

        if regressions > improvements:
            return PromotionStatus.REJECTED, ["more_regressions_than_improvements"]
        if improvements == 0:
            return PromotionStatus.NEEDS_MORE_DATA, []

        return PromotionStatus.APPROVED, []

    def summarize(self) -> dict[str, Any]:
        """Produce a compact summary."""
        return {
            "composite": self.compute_composite(),
            "quality_breakdown": self.quality_breakdown(),
            "feedback_signal": self.feedback_signal(),
            "has_input": self.input_metrics is not None,
            "has_generation": self.generation_metrics is not None,
            "has_evaluation": self.evaluation_metrics is not None,
            "has_blackforge": self.blackforge_metrics is not None,
            "has_process": self.process_metrics is not None,
            "has_result": self.result_metrics is not None,
            "explicit_feedback_count": len(self.explicit_feedback),
            "implicit_feedback_count": len(self.implicit_feedback),
        }
