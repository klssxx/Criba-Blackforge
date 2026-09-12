"""Tests for latency optimization (HIPERMEGAPROMPT §9)."""
from __future__ import annotations

import pytest

from criba.latency import (
    BatchFamily,
    BatchPlan,
    BudgetExceededError,
    GenerationBudget,
    LatencyMetrics,
    LatencyScheduler,
    SemanticCacheKey,
)


class TestGenerationBudget:
    def test_spend_within_budget(self) -> None:
        budget = GenerationBudget(maximum_tokens=100, maximum_latency_ms=5000)
        budget.spend(tokens=50, latency_ms=1000)
        assert budget.tokens_spent == 50

    def test_spend_exceeds_token_budget(self) -> None:
        budget = GenerationBudget(maximum_tokens=100)
        budget.spend(tokens=50)
        with pytest.raises(BudgetExceededError, match="Token budget exceeded"):
            budget.spend(tokens=60)

    def test_spend_exceeds_latency_budget(self) -> None:
        budget = GenerationBudget(maximum_latency_ms=100)
        with pytest.raises(BudgetExceededError, match="Latency budget exceeded"):
            budget.spend(latency_ms=200)

    def test_early_exit_when_targets_met(self) -> None:
        budget = GenerationBudget(diversity_target=0.7, quality_floor=0.5)
        assert budget.early_exit(diversity=0.8, quality=0.6) is True

    def test_no_early_exit_when_targets_not_met(self) -> None:
        budget = GenerationBudget(diversity_target=0.7, quality_floor=0.5)
        assert budget.early_exit(diversity=0.6, quality=0.4) is False

    def test_exhausted_property(self) -> None:
        budget = GenerationBudget(maximum_tokens=100)
        budget.spend(tokens=100)
        assert budget.exhausted is True

    def test_overrun_is_atomic(self) -> None:
        budget = GenerationBudget(maximum_tokens=100, maximum_latency_ms=100)
        budget.spend(tokens=80, latency_ms=20)
        with pytest.raises(BudgetExceededError):
            budget.spend(tokens=21, latency_ms=81)
        assert budget.tokens_spent == 80
        assert budget.latency_ms_spent == 20

    def test_negative_spend_is_rejected(self) -> None:
        budget = GenerationBudget()
        with pytest.raises(ValueError, match="no puede ser negativo"):
            budget.spend(tokens=-1)


class TestBatchPlan:
    def test_default_batch(self) -> None:
        plan = BatchPlan()
        assert plan.family == BatchFamily.INCREMENTAL
        assert plan.min_candidates == 2
        assert plan.cancelled is False


class TestSemanticCacheKey:
    def test_hash_stable(self) -> None:
        key = SemanticCacheKey(context_hash="ctx1", task_hash="task1")
        assert key.to_hash() == key.to_hash()

    def test_hash_changes_with_data(self) -> None:
        k1 = SemanticCacheKey(context_hash="a")
        k2 = SemanticCacheKey(context_hash="b")
        assert k1.to_hash() != k2.to_hash()

    def test_includes_mode(self) -> None:
        k1 = SemanticCacheKey(mode="criba")
        k2 = SemanticCacheKey(mode="blackforge")
        assert k1.to_hash() != k2.to_hash()


class TestLatencyScheduler:
    def test_returns_metrics(self) -> None:
        scheduler = LatencyScheduler()
        metrics = scheduler.finalize_metrics()
        assert isinstance(metrics, LatencyMetrics)
        assert metrics.total_tokens == 0

    def test_cache_hit_rate_zero_when_empty(self) -> None:
        scheduler = LatencyScheduler()
        assert scheduler.cache_hit_rate == 0.0

    def test_cache_hit_rate_after_hits(self) -> None:
        scheduler = LatencyScheduler()
        key = SemanticCacheKey(context_hash="ctx")
        scheduler.put_in_cache(key, "result")
        scheduler.get_from_cache(key)
        assert scheduler.cache_hit_rate == 1.0

    def test_cache_miss(self) -> None:
        scheduler = LatencyScheduler()
        key = SemanticCacheKey(context_hash="ctx")
        assert scheduler.get_from_cache(key) is None

    def test_plan_batches_empty_operators(self) -> None:
        scheduler = LatencyScheduler()
        batches = scheduler.plan_batches([])
        assert len(batches) == 1

    def test_plan_batches_splits_operators(self) -> None:
        scheduler = LatencyScheduler()
        batches = scheduler.plan_batches(["op1", "op2", "op3", "op4"])
        assert len(batches) >= 1

    def test_early_exit_delegates_to_budget(self) -> None:
        scheduler = LatencyScheduler(
            budget=GenerationBudget(diversity_target=0.7, quality_floor=0.5)
        )
        assert scheduler.should_early_exit(0.8, 0.6) is True
        assert scheduler.should_early_exit(0.5, 0.4) is False

    def test_record_spend(self) -> None:
        scheduler = LatencyScheduler(budget=GenerationBudget(maximum_tokens=1000))
        scheduler.record_spend(tokens=500)
        assert scheduler.budget.tokens_spent == 500

    def test_record_spend_raises_when_exceeded(self) -> None:
        scheduler = LatencyScheduler(budget=GenerationBudget(maximum_tokens=100))
        with pytest.raises(BudgetExceededError):
            scheduler.record_spend(tokens=200)

    def test_percentiles_use_observed_samples(self) -> None:
        scheduler = LatencyScheduler()
        for sample in (10.0, 30.0, 20.0):
            scheduler.record_latency(sample)
        metrics = scheduler.finalize_metrics()
        assert metrics.p50_ms == 20.0
        assert metrics.p95_ms == 30.0
        assert metrics.p99_ms == 30.0


class TestBudgetExceededError:
    def test_error_message(self) -> None:
        err = BudgetExceededError("test message")
        assert str(err) == "test message"
