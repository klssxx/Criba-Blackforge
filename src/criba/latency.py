"""Latency optimization (HIPERMEGAPROMPT §9).

Adaptive budget, batch generation, controlled parallelism, semantic cache.

In deterministic mode (no LLM backend) most features are measured no-ops:
budget is tracked, cache keys are computed, metrics are recorded.
"""
from __future__ import annotations

import time
from collections.abc import Sequence
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

    tokens_spent: int = 0
    latency_ms_spent: float = 0.0
    ideas_generated: int = 0

    def spend(self, tokens: int = 0, latency_ms: float = 0.0) -> None:
        """Record spend; raises if budget is exceeded."""
        self.tokens_spent += tokens
        self.latency_ms_spent += latency_ms
        if self.tokens_spent > self.maximum_tokens:
            raise BudgetExceededError(
                f"Token budget exceeded: {self.tokens_spent}/{self.maximum_tokens}"
            )
        if self.latency_ms_spent > self.maximum_latency_ms:
            raise BudgetExceededError(
                f"Latency budget exceeded: {self.latency_ms_spent:.0f}ms/{self.maximum_latency_ms}ms"
            )

    def early_exit(self, diversity: float, quality: float) -> bool:
        """§9.9 — Exit early if diversity/quality targets are met."""
        return diversity >= self.diversity_target and quality >= self.quality_floor

    @property
    def exhausted(self) -> bool:
        return (
            self.tokens_spent >= self.maximum_tokens
            or self.latency_ms_spent >= self.maximum_latency_ms
        )


class BudgetExceededError(Exception):
    """Raised when the generation budget is exceeded (§9.15)."""

    def __init__(self, message: str) -> None:
        super().__init__(message)


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
    cost_per_accepted_idea: float = 0.0
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

    def plan_batches(self, operators: Sequence[str]) -> list[BatchPlan]:
        """§9.4 — Split operators into family batches."""
        if not operators:
            return [BatchPlan(family=BatchFamily.INCREMENTAL, operators=["default"])]
        batches: list[BatchPlan] = []
        chunk_size = 4
        families = list(BatchFamily)
        for i in range(0, len(operators), chunk_size):
            chunk = operators[i:i + chunk_size]
            family = families[i // chunk_size % len(families)]
            batches.append(BatchPlan(family=family, operators=chunk))
        return batches

    def should_early_exit(self, diversity: float, quality: float) -> bool:
        """§9.9 — Check early exit conditions."""
        return self.budget.early_exit(diversity, quality)

    def record_spend(self, tokens: int = 0) -> None:
        """§9.15 — Record spend and raise if budget exceeded."""
        elapsed = self._elapsed_ms()
        self.budget.spend(tokens=tokens, latency_ms=elapsed)

    def finalize_metrics(self) -> LatencyMetrics:
        """§9.14 — Compute final latency metrics."""
        elapsed = self._elapsed_ms()
        return LatencyMetrics(
            p50_ms=elapsed,
            p95_ms=elapsed,
            p99_ms=elapsed,
            time_to_decision_ms=elapsed,
            cache_hit_rate=self.cache_hit_rate,
            total_tokens=self.budget.tokens_spent,
        )
