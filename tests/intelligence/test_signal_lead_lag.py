"""P07-T07 tests for deterministic lead/lag analysis."""
from __future__ import annotations

from criba.intelligence import contracts as C
from criba.intelligence.signals.lead_lag import LeadLagAnalyzer


def test_lead_lag_analyzer_identifies_delayed_follower():
    leader_values = [0, 1, 0, 2, 0, 3]
    follower_values = [9, 0, 1, 0, 2, 0]
    observations = [
        C.TopicObservation(topic=topic, period=f"2026-{index + 1:02d}", frequency=value)
        for topic, values in (("leader", leader_values), ("follower", follower_values))
        for index, value in enumerate(values)
    ]

    result = LeadLagAnalyzer(max_lag=2).analyze(observations, "leader", "follower")

    assert result is not None
    assert result.to_dict() == {
        "leader_topic": "leader",
        "follower_topic": "follower",
        "lag": 1,
        "correlation": 1.0,
        "strength": 1.0,
        "overlap": 5,
    }
