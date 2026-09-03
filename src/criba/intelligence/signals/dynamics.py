"""Deterministic topic-observation time series for the IIE signal sector."""
from __future__ import annotations

from collections.abc import Iterable

from ..contracts import TopicObservation


class ObservationSeries:
    """Ordered collection of topic observations grouped by topic and period."""

    def __init__(self, observations: Iterable[TopicObservation] = ()) -> None:
        self._observations = tuple(
            sorted(observations, key=lambda observation: (observation.topic, observation.period))
        )

    def for_topic(self, topic: str) -> list[TopicObservation]:
        """Return observations for ``topic`` in ascending period order."""
        return [observation for observation in self._observations if observation.topic == topic]

    def topics(self) -> list[str]:
        """Return the distinct topics in deterministic lexical order."""
        return sorted({observation.topic for observation in self._observations})

    def all(self) -> list[TopicObservation]:
        """Return all observations in deterministic topic/period order."""
        return list(self._observations)


class TopicDynamics:
    """Calculate discrete frequency velocity and acceleration per topic."""

    def __init__(self, series: ObservationSeries | Iterable[TopicObservation]) -> None:
        self.series = series if isinstance(series, ObservationSeries) else ObservationSeries(series)

    def velocity(self, topic: str) -> list[float]:
        """Return period-aligned frequency deltas, using zero for the first point."""
        points = self.series.for_topic(topic)
        if not points:
            return []
        return [0.0] + [
            float(current.frequency - previous.frequency)
            for previous, current in zip(points, points[1:])
        ]

    def acceleration(self, topic: str) -> list[float]:
        """Return period-aligned changes in velocity for equally spaced buckets."""
        velocities = self.velocity(topic)
        if not velocities:
            return []
        if len(velocities) == 1:
            return [0.0]
        return [0.0, 0.0] + [
            velocities[index] - velocities[index - 1]
            for index in range(2, len(velocities))
        ]


__all__ = ["ObservationSeries", "TopicDynamics"]
