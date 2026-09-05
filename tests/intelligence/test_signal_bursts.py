"""P07-T03 tests for deterministic burst detection."""
from __future__ import annotations

from criba.intelligence import contracts as C
from criba.intelligence.signals.bursts import BurstDetector


def test_burst_detector_returns_velocity_spikes_with_period_and_strength():
    observations = [
        C.TopicObservation(topic="cooling", period="2026-01", frequency=2),
        C.TopicObservation(topic="cooling", period="2026-02", frequency=3),
        C.TopicObservation(topic="cooling", period="2026-03", frequency=8),
        C.TopicObservation(topic="cooling", period="2026-04", frequency=9),
    ]

    bursts = BurstDetector(min_velocity=2.0).detect(observations)

    assert [burst.to_dict() for burst in bursts] == [
        {
            "topic": "cooling",
            "period": "2026-03",
            "velocity": 5.0,
            "strength": 1.0,
        }
    ]
