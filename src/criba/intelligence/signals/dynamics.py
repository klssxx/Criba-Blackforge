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


__all__ = ["ObservationSeries"]
