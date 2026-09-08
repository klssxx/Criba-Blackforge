"""P07-T04 tests for deterministic change-point detection."""
from __future__ import annotations

from criba.intelligence import contracts as C
from criba.intelligence.signals.changepoints import ChangePointDetector


def test_change_point_detector_reports_level_shift_at_candidate_period():
    observations = [
        C.TopicObservation(topic="cooling", period="2026-01", frequency=2),
        C.TopicObservation(topic="cooling", period="2026-02", frequency=2),
        C.TopicObservation(topic="cooling", period="2026-03", frequency=8),
        C.TopicObservation(topic="cooling", period="2026-04", frequency=8),
    ]

    changes = ChangePointDetector(window=2, min_delta=2.0).detect(observations)

    assert [change.to_dict() for change in changes] == [
        {
            "topic": "cooling",
            "period": "2026-03",
            "before_mean": 2.0,
            "after_mean": 8.0,
            "delta": 6.0,
            "direction": "up",
            "strength": 1.0,
        }
    ]
