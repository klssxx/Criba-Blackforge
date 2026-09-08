"""P07-T06 tests for deterministic weak-signal aggregation."""
from __future__ import annotations

from criba.intelligence import contracts as C
from criba.intelligence.signals.weak_signals import WeakSignalAggregator


def test_weak_signal_aggregator_merges_support_without_double_counting_ids():
    signals = [
        C.WeakSignal(
            signal_id="s1",
            kind="trend",
            topic="cooling",
            strength=0.2,
            direction="up",
            evidence_doc_ids=("d2", "d1"),
            technique_ids=("T002",),
            lead_lag_hint="leading",
            confidence=0.4,
        ),
        C.WeakSignal(
            signal_id="s2",
            kind="trend",
            topic="cooling",
            strength=0.3,
            direction="up",
            evidence_doc_ids=("d2", "d3"),
            technique_ids=("T001", "T002"),
            lead_lag_hint="leading",
            confidence=0.5,
        ),
    ]

    aggregated = WeakSignalAggregator().aggregate([signals[0], signals[1], signals[0]])

    assert len(aggregated) == 1
    result = aggregated[0]
    assert result.kind == "trend"
    assert result.topic == "cooling"
    assert result.strength == 0.44
    assert result.evidence_doc_ids == ("d1", "d2", "d3")
    assert result.technique_ids == ("T001", "T002")
    assert result.lead_lag_hint == "leading"
    assert result.confidence == 0.7
