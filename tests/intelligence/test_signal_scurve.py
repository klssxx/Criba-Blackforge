"""P07-T08 tests for deterministic S-curve approximation."""
from __future__ import annotations

from criba.intelligence import contracts as C
from criba.intelligence.signals.scurve import SCurveApproximator


def _observations(values: list[int]) -> list[C.TopicObservation]:
    return [
        C.TopicObservation(topic="topic", period=f"2026-{index + 1:02d}", frequency=value)
        for index, value in enumerate(values)
    ]


def test_scurve_fit_models_increasing_series_and_extrapolates_saturation():
    result = SCurveApproximator().fit(_observations([1, 2, 4, 7, 11, 14, 16, 17]))

    assert result is not None
    assert result.topic == "topic"
    assert result.carrying_capacity > 17
    assert result.growth_rate > 0
    assert result.predict(8) > result.predict(7)
    assert result.predict(80) < result.carrying_capacity
    assert result.to_dict()["topic"] == "topic"


def test_scurve_fit_rejects_short_or_non_increasing_series():
    approximator = SCurveApproximator()

    assert approximator.fit(_observations([1, 2, 3])) is None
    assert approximator.fit(_observations([4, 4, 4, 4])) is None
