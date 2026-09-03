"""Latency optimization (HIPERMEGAPROMPT §9).

Adaptive budget, batch generation, controlled parallelism, semantic cache.

In deterministic mode (no LLM backend) most features are measured no-ops:
budget is tracked, cache keys are computed, metrics are recorded.
"""
from __future__ import annotations

import math
import threading
import time
from collections.abc import Mapping, Sequence
from contextlib import contextmanager
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .blackforge_causal import canonical_hash

# ---------------------------------------------------------------------------
# Budget (§9.3)
# ---------------------------------------------------------------------------

class GenerationBudget(BaseModel):
    """§9.3 — Adaptive generation budget."""

    model_config = ConfigDict(extra="forbid")

    target_idea_count: int = 16
    minimum_family_count: int = 3
    maximum_tokens: int = 50_000
    maximum_latency_ms: int = 30_000
    early_stop_threshold: float = 0.8
    diversity_target: float = 0.7
    quality_floor: float = 0.5
    minimum_accepted: int = 0
    top_score_gap: float | None = None
    marginal_novelty_floor: float | None = None
    no_improvement_rounds: int = 0
    human_review_required: bool = False

    tokens_spent: int = 0
    latency_ms_spent: float = 0.0
    ideas_generated: int = 0
    accepted_ideas: int = 0
    best_score: float = 0.0
    last_marginal_novelty: float = 1.0
    observed_no_improvement_rounds: int = 0
    cost_spent: float = 0.0
    human_review_completed: bool = False

    def spend(self, tokens: int = 0, latency_ms: float = 0.0) -> None:
        """Record spend atomically; over-budget attempts leave state unchanged."""
        if tokens < 0 or latency_ms < 0:
            raise ValueError("El gasto no puede ser negativo")
        next_tokens = self.tokens_spent + tokens
        next_latency = self.latency_ms_spent + latency_ms
        if next_tokens > self.maximum_tokens:
            raise BudgetExceededError(
                f"Token budget exceeded: {next_tokens}/{self.maximum_tokens}"
            )
        if next_latency > self.maximum_latency_ms:
            raise BudgetExceededError(
                f"Latency budget exceeded: {next_latency:.0f}ms/{self.maximum_latency_ms}ms"
            )
        self.tokens_spent = next_tokens
        self.latency_ms_spent = next_latency

    def record_idea(
        self,
        *,
        accepted: bool,
        score: float = 0.0,
        marginal_novelty: float = 1.0,
    ) -> None:
        """Record one candidate and its quality signal without spending tokens."""
        if not 0.0 <= score <= 1.0 or not 0.0 <= marginal_novelty <= 1.0:
            raise ValueError("score y marginal_novelty deben estar entre 0 y 1")
        self.ideas_generated += 1
        if accepted:
            self.accepted_ideas += 1
        self.last_marginal_novelty = marginal_novelty
        if score > self.best_score:
            self.best_score = score
            self.observed_no_improvement_rounds = 0
        else:
            self.observed_no_improvement_rounds += 1

    def early_exit(
        self,
        diversity: float,
        quality: float,
        *,
        accepted_count: int | None = None,
        top_score_gap: float | None = None,
        marginal_novelty: float | None = None,
        no_improvement_rounds: int | None = None,
        dominant_score: float | None = None,
    ) -> bool:
        """§9.9 — Exit only when configured coverage and quality criteria hold."""
        accepted = self.accepted_ideas if accepted_count is None else accepted_count
        novelty = self.last_marginal_novelty if marginal_novelty is None else marginal_novelty
        stagnant = (
            self.observed_no_improvement_rounds
            if no_improvement_rounds is None
            else no_improvement_rounds
        )
        if accepted < self.minimum_accepted:
            return False
        if diversity < self.diversity_target or quality < self.quality_floor:
            return False
        if self.top_score_gap is not None and (
            top_score_gap is None or top_score_gap < self.top_score_gap
        ):
            return False
        if self.marginal_novelty_floor is not None and novelty < self.marginal_novelty_floor:
            return False
        if self.no_improvement_rounds and stagnant < self.no_improvement_rounds:
            return False
        if dominant_score is not None and dominant_score < self.early_stop_threshold:
            return False
        return True

    @property
    def target_reached(self) -> bool:
        """Whether the requested number of candidates has been generated."""
        return self.target_idea_count > 0 and self.ideas_generated >= self.target_idea_count

    @property
    def exhausted(self) -> bool:
        return (
            self.target_reached
            or self.tokens_spent >= self.maximum_tokens
            or self.latency_ms_spent >= self.maximum_latency_ms
        )

    @property
    def review_ready(self) -> bool:
        """Whether the mandatory human-review condition has been satisfied."""
        return not self.human_review_required or self.human_review_completed


class BudgetExceededError(Exception):
    """Raised when the generation budget is exceeded (§9.15)."""

    def __init__(self, message: str) -> None:
        super().__init__(message)


class BackpressureError(RuntimeError):
    """Raised when the configured generator queue/parallelism is saturated."""


# ---------------------------------------------------------------------------
# Batch plan (§9.4)
# ---------------------------------------------------------------------------

class BatchFamily(str, Enum):
    INCREMENTAL = "incremental"
    STRUCTURAL = "structural"
    DISRUPTIVE = "disruptive"
    EXTERNAL_ANALOGY = "external_analogy"
    LOW_COST = "low_cost"
    HIGH_IMPACT = "high_impact"
    BLACKFORGE_OFFENSIVE = "blackforge_offensive"
    BLACKFORGE_DEFENSIVE = "blackforge_defensive"
    DETECTION = "detection"
    RECOVERY = "recovery"


class BatchPlan(BaseModel):
    """§9.4 — One batch with its own operators and constraints."""

    model_config = ConfigDict(extra="forbid")

    family: str = BatchFamily.INCREMENTAL
    operators: list[str] = Field(default_factory=list)
    min_candidates: int = 2
    max_candidates: int = 8
    max_concurrency: int = 2
    timeout_ms: int = 10_000
    priority: int = 1
    cancelled: bool = False


class ProgressiveCandidate(BaseModel):
    """§9.7 — Cheap outline promoted to a deep architecture only when valid."""

    model_config = ConfigDict(extra="forbid")

    candidate_id: str
    one_line: str
    mechanism: str
    anchors: list[str] = Field(default_factory=list)
    primary_risk: str
    context_hash: str = ""
    full_architecture: dict[str, Any] | None = None


class CheapValidation(BaseModel):
    """§9.8 — Deterministic pre-filter result."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    valid: bool
    checks: tuple[str, ...] = ()
    failures: tuple[str, ...] = ()


def validate_candidate_cheap(
    candidate: Mapping[str, Any],
    *,
    seen_ids: set[str] | None = None,
    expected_context_hash: str = "",
) -> CheapValidation:
    """Run schema, anchor, length, duplicate, violation, and context filters."""
    checks = (
        "schema",
        "anchors",
        "length",
        "duplicate",
        "violation",
        "mechanism",
        "context",
    )
    failures: list[str] = []
    candidate_id = candidate.get("candidate_id", candidate.get("id", ""))
    one_line = candidate.get("one_line", candidate.get("description", ""))
    mechanism = candidate.get("mechanism", candidate.get("causal_mechanism", ""))
    anchors = candidate.get("anchors", candidate.get("evidence", []))
    primary_risk = candidate.get("primary_risk", candidate.get("risk", ""))
    if not all(isinstance(value, str) and value.strip() for value in (
        candidate_id,
        one_line,
        mechanism,
        primary_risk,
    )):
        failures.append("schema_or_empty")
    if not isinstance(anchors, list) or not anchors:
        failures.append("anchors_missing")
    text_length = sum(len(value) for value in (one_line, mechanism) if isinstance(value, str))
    if text_length > 10_000:
        failures.append("length_limit")
    if seen_ids is not None and str(candidate_id) in seen_ids:
        failures.append("duplicate_id")
    if candidate.get("violation") or candidate.get("safety_violation"):
        failures.append("violation")
    if isinstance(mechanism, str) and mechanism.strip().casefold() in {
        "use ai",
        "usar ia",
        "use machine learning",
        "usar machine learning",
    }:
        failures.append("generic_mechanism")
    candidate_context = candidate.get("context_hash", "")
    if expected_context_hash and candidate_context != expected_context_hash:
        failures.append("context_mismatch")
    return CheapValidation(
        valid=not failures,
        checks=checks,
        failures=tuple(failures),
    )


# ---------------------------------------------------------------------------
# Parallelism config (§9.5)
# ---------------------------------------------------------------------------

class ParallelismConfig(BaseModel):
    """§9.5 — Controlled concurrency limits."""

    model_config = ConfigDict(extra="forbid")

    max_concurrent_generators: int = 2
    max_concurrent_validators: int = 4
    max_concurrent_embeddings: int = 4
    queue_depth: int = 10
    per_model_concurrency: int = 1
    global_rate_limit: float = 10.0  # requests per second


# ---------------------------------------------------------------------------
# Semantic cache key (§9.6)
# ---------------------------------------------------------------------------

class SemanticCacheKey(BaseModel):
    """§9.6 — Deterministic cache key for generation results."""

    model_config = ConfigDict(extra="forbid")

    context_hash: str = ""
    task_hash: str = ""
    persona_version: str = "1.0.0"
    prompt_version: str = "1.0.0"
    operator_id: str = ""
    model_id: str = ""
    generation_profile: str = "balanced"
    mode: str = "criba"
    authorization_state: str = "pending"
    restrictions_hash: str = ""
    asset_hash: str = ""
    threat_hash: str = ""
    evidence_hash: str = ""
    evaluation_criteria_hash: str = ""

    def to_hash(self) -> str:
        return canonical_hash(self.model_dump(mode="json"))


# ---------------------------------------------------------------------------
# Metrics (§9.14)
# ---------------------------------------------------------------------------

class LatencyMetrics(BaseModel):
    """§9.14 — Observed latency metrics."""

    model_config = ConfigDict(extra="forbid")

    p50_ms: float = 0.0
    p95_ms: float = 0.0
    p99_ms: float = 0.0
    time_to_first_useful_ms: float = 0.0
    time_to_diverse_set_ms: float = 0.0
    time_to_decision_ms: float = 0.0
    time_to_first_candidate_ms: float = 0.0
    time_to_first_accepted_ms: float = 0.0
    time_to_final_ranking_ms: float = 0.0
    p50_stage_latency: dict[str, float] = Field(default_factory=dict)
    p95_stage_latency: dict[str, float] = Field(default_factory=dict)
    p99_stage_latency: dict[str, float] = Field(default_factory=dict)
    tokens_per_accepted_idea: float = 0.0
    cost_per_accepted_idea: float = 0.0
    cancellation_rate: float = 0.0
    retry_rate: float = 0.0
    regeneration_rate: float = 0.0

    cache_hit_rate: float = 0.0
    total_tokens: int = 0


# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------

class LatencyScheduler:
    """§9 — Schedules generation batches with budget and cache."""

    def __init__(
        self,
        budget: GenerationBudget | None = None,
        parallelism: ParallelismConfig | None = None,
    ) -> None:
        self.budget = budget or GenerationBudget()
        self.parallelism = parallelism or ParallelismConfig()
        self._cache: dict[str, Any] = {}
        self._cache_hits = 0
        self._cache_misses = 0
        self._start_time = time.monotonic()
        self._last_spend_time = self._start_time
        self._latency_samples_ms: list[float] = []
        self._stage_latency_samples_ms: dict[str, list[float]] = {}
        self._candidate_count = 0
        self._accepted_count = 0
        self._first_candidate_ms: float | None = None
        self._first_accepted_ms: float | None = None
        self._cancellations = 0
        self._retry_count = 0
        self._generator_slots = threading.BoundedSemaphore(
            self.parallelism.max_concurrent_generators
        )

    def _elapsed_ms(self) -> float:
        return (time.monotonic() - self._start_time) * 1000

    def get_from_cache(self, key: SemanticCacheKey) -> Any | None:
        """§9.6 — Lookup by semantic cache key."""
        h = key.to_hash()
        if h in self._cache:
            self._cache_hits += 1
            return self._cache[h]
        self._cache_misses += 1
        return None

    def put_in_cache(self, key: SemanticCacheKey, value: Any) -> None:
        """§9.6 — Store result under semantic cache key."""
        h = key.to_hash()
        self._cache[h] = value

    @property
    def cache_hit_rate(self) -> float:
        total = self._cache_hits + self._cache_misses
        return self._cache_hits / total if total else 0.0

    def can_queue(self, queued: int) -> bool:
        """Apply the configured queue-depth backpressure rule."""
        return 0 <= queued <= self.parallelism.queue_depth

    @contextmanager
    def generator_slot(self, timeout_ms: int = 0):
        """Acquire/release a bounded generator slot cooperatively."""
        if timeout_ms < 0:
            raise ValueError("timeout_ms no puede ser negativo")
        acquired = self._generator_slots.acquire(
            timeout=timeout_ms / 1000 if timeout_ms else 0
        )
        if not acquired:
            raise BackpressureError("max_concurrent_generators alcanzado")
        try:
            yield
        finally:
            self._generator_slots.release()

    def plan_batches(self, operators: Sequence[str]) -> list[BatchPlan]:
        """§9.4 — Split operators into family batches."""
        if not operators:
            return [BatchPlan(family=BatchFamily.INCREMENTAL, operators=["default"])]
        batches: list[BatchPlan] = []
        families = list(BatchFamily)
        family_quota = max(1, min(self.budget.minimum_family_count, len(families)))
        batch_count = max(family_quota, math.ceil(len(operators) / 4))
        chunk_size = max(1, math.ceil(len(operators) / batch_count))
        for i in range(batch_count):
            chunk = operators[i * chunk_size:(i + 1) * chunk_size]
            batches.append(
                BatchPlan(
                    family=families[i % len(families)],
                    operators=list(chunk),
                    min_candidates=min(2, len(chunk)) if chunk else 0,
                )
            )
        return batches

    def should_early_exit(
        self,
        diversity: float,
        quality: float,
        *,
        accepted_count: int | None = None,
        top_score_gap: float | None = None,
        marginal_novelty: float | None = None,
        no_improvement_rounds: int | None = None,
        dominant_score: float | None = None,
    ) -> bool:
        """§9.9 — Check all configured early-exit conditions."""
        return self.budget.early_exit(
            diversity,
            quality,
            accepted_count=accepted_count,
            top_score_gap=top_score_gap,
            marginal_novelty=marginal_novelty,
            no_improvement_rounds=no_improvement_rounds,
            dominant_score=dominant_score,
        )

    def record_latency(self, latency_ms: float, *, stage: str = "generation") -> None:
        """Record one completed batch latency for global and stage metrics."""
        if latency_ms < 0:
            raise ValueError("La latencia no puede ser negativa")
        value = float(latency_ms)
        self._latency_samples_ms.append(value)
        self._stage_latency_samples_ms.setdefault(stage, []).append(value)

    def record_candidate(
        self,
        *,
        accepted: bool,
        score: float = 0.0,
        marginal_novelty: float = 1.0,
        latency_ms: float | None = None,
        stage: str = "generation",
    ) -> None:
        """Record a candidate and its observed generation outcome."""
        self.budget.record_idea(
            accepted=accepted,
            score=score,
            marginal_novelty=marginal_novelty,
        )
        self._candidate_count += 1
        if accepted:
            self._accepted_count += 1
        elapsed = self._elapsed_ms() if latency_ms is None else float(latency_ms)
        if self._first_candidate_ms is None:
            self._first_candidate_ms = elapsed
        if accepted and self._first_accepted_ms is None:
            self._first_accepted_ms = elapsed
        self.record_latency(elapsed, stage=stage)

    def record_cancellation(self, count: int = 1) -> None:
        """Record cooperative cancellations separately from generation failures."""
        if count < 0:
            raise ValueError("count no puede ser negativo")
        self._cancellations += count

    def record_retry(self, count: int = 1) -> None:
        """Record retries for the retry-rate metric."""
        if count < 0:
            raise ValueError("count no puede ser negativo")
        self._retry_count += count

    def cancel_batch(self, batch: BatchPlan) -> BatchPlan:
        """Cancel a batch cooperatively and account for it as cancellation."""
        if not batch.cancelled:
            batch.cancelled = True
            self.record_cancellation()
        return batch

    def cancel_redundant(self, batches: Sequence[BatchPlan], keep: int) -> int:
        """Cancel remaining batches after coverage makes them redundant."""
        if keep < 0:
            raise ValueError("keep no puede ser negativo")
        cancelled = 0
        for batch in list(batches)[keep:]:
            if not batch.cancelled:
                self.cancel_batch(batch)
                cancelled += 1
        return cancelled

    def mark_human_review_completed(self) -> None:
        """Close the mandatory review gate for a budgeted generation run."""
        self.budget.human_review_completed = True

    def assert_review_ready(self) -> None:
        """Fail closed when §9.15 requires review that has not happened."""
        if not self.budget.review_ready:
            raise RuntimeError("human_review_required")


    @staticmethod
    def _percentile(samples: list[float], percentile: float) -> float:
        if not samples:
            return 0.0
        ordered = sorted(samples)
        index = min(len(ordered) - 1, max(0, math.ceil(len(ordered) * percentile) - 1))
        return ordered[index]

    def record_spend(
        self,
        tokens: int = 0,
        *,
        cost: float = 0.0,
        stage: str = "generation",
    ) -> None:
        """§9.15 — Record spend and the elapsed interval since prior spend."""
        if cost < 0:
            raise ValueError("El coste no puede ser negativo")
        now = time.monotonic()
        interval_ms = max(0.0, (now - self._last_spend_time) * 1000)
        self.budget.spend(tokens=tokens, latency_ms=interval_ms)
        self.budget.cost_spent += cost
        self.record_latency(interval_ms, stage=stage)
        self._last_spend_time = now

    def finalize_metrics(self) -> LatencyMetrics:
        """§9.14 — Compute observed global and per-stage metrics."""
        elapsed = self._elapsed_ms()
        samples = self._latency_samples_ms or [elapsed]
        stage_metrics = {
            name: (
                self._percentile(values, 0.50),
                self._percentile(values, 0.95),
                self._percentile(values, 0.99),
            )
            for name, values in self._stage_latency_samples_ms.items()
        }
        accepted = self._accepted_count
        total_outcomes = self._candidate_count + self._cancellations
        return LatencyMetrics(
            p50_ms=self._percentile(samples, 0.50),
            p95_ms=self._percentile(samples, 0.95),
            p99_ms=self._percentile(samples, 0.99),
            time_to_first_candidate_ms=self._first_candidate_ms or 0.0,
            time_to_first_accepted_ms=self._first_accepted_ms or 0.0,
            time_to_final_ranking_ms=elapsed,
            time_to_decision_ms=elapsed,
            p50_stage_latency={name: values[0] for name, values in stage_metrics.items()},
            p95_stage_latency={name: values[1] for name, values in stage_metrics.items()},
            p99_stage_latency={name: values[2] for name, values in stage_metrics.items()},
            tokens_per_accepted_idea=(
                self.budget.tokens_spent / accepted if accepted else 0.0
            ),
            cost_per_accepted_idea=(
                self.budget.cost_spent / accepted if accepted else 0.0
            ),
            cancellation_rate=(
                self._cancellations / total_outcomes if total_outcomes else 0.0
            ),
            retry_rate=(
                self._retry_count / self._candidate_count if self._candidate_count else 0.0
            ),
            regeneration_rate=(
                self._retry_count / self._candidate_count if self._candidate_count else 0.0
            ),
            cache_hit_rate=self.cache_hit_rate,
            total_tokens=self.budget.tokens_spent,
        )
