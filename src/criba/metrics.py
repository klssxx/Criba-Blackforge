"""Quality metrics and continuous feedback (HIPERMEGAPROMPT §13).

Collects and aggregates metrics from gates (P7), logs (P8), ensemble (P3),
latency (P9), and process outcomes. Provides explicit/implicit feedback,
drift detection, and promotion gates.
"""
from __future__ import annotations

from collections.abc import Mapping
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

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


# ---------------------------------------------------------------------------
# MetricsCollector
# ---------------------------------------------------------------------------

class MetricsCollector:
    """§13 — Aggregates metrics from all layers."""

    def __init__(self) -> None:
        self.input_metrics: InputMetrics | None = None
        self.generation_metrics: GenerationMetrics | None = None
        self.evaluation_metrics: EvaluationMetrics | None = None
        self.blackforge_metrics: BlackforgeMetrics | None = None
        self.process_metrics: ProcessMetrics | None = None
        self.result_metrics: ResultMetrics | None = None
        self.explicit_feedback: list[ExplicitFeedback] = []
        self.implicit_feedback: list[ImplicitFeedback] = []

    def compute_composite(self) -> float:
        """§13.15 — Single composite quality score."""
        scores: list[float] = []
        if self.generation_metrics:
            scores.append(self.generation_metrics.semantic_diversity)
            scores.append(self.generation_metrics.relevance)
        if self.evaluation_metrics:
            scores.append(self.evaluation_metrics.confidence_calibration)
        if self.process_metrics:
            scores.append(self.process_metrics.cache_hit_rate)
        if self.result_metrics:
            scores.append(self.result_metrics.human_acceptance)
        return sum(scores) / len(scores) if scores else 0.0

    def detect_drift(self, baseline: Mapping[str, float]) -> list[str]:
        """§13.12 — Detect quality drift against baseline."""
        alerts: list[str] = []
        current = self._flatten()
        for key, base_val in baseline.items():
            cur_val = current.get(key)
            if cur_val is None:
                continue
            if cur_val < base_val * 0.8:
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

    def evaluate_promotion(self, baseline: Mapping[str, float]) -> tuple[PromotionStatus, list[str]]:
        """§13.13 — Decide if a change should be promoted."""
        reasons: list[str] = []
        current = self._flatten()

        # Blackforge must not degrade.
        if self.blackforge_metrics:
            if self.blackforge_metrics.authorization_completeness < 1.0:
                reasons.append("blackforge_authorization_incomplete")

        # Must not break traceability.
        if self.process_metrics and self.process_metrics.schema_failures > 0:
            reasons.append("schema_failures_present")

        # Hard blockers reject immediately.
        if reasons:
            return PromotionStatus.REJECTED, reasons

        # Count improvements and regressions.
        improvements = 0
        regressions = 0
        for key, base_val in baseline.items():
            cur_val = current.get(key)
            if cur_val is None:
                continue
            if cur_val > base_val * 1.05:
                improvements += 1
            elif cur_val < base_val * 0.95:
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
            "has_input": self.input_metrics is not None,
            "has_generation": self.generation_metrics is not None,
            "has_evaluation": self.evaluation_metrics is not None,
            "has_blackforge": self.blackforge_metrics is not None,
            "has_process": self.process_metrics is not None,
            "has_result": self.result_metrics is not None,
            "explicit_feedback_count": len(self.explicit_feedback),
            "implicit_feedback_count": len(self.implicit_feedback),
        }
