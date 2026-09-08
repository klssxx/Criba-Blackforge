"""Explainable burst detection over topic observation dynamics (P07-T03)."""
from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass

from ..contracts import TopicObservation
from .dynamics import ObservationSeries, TopicDynamics


@dataclass(frozen=True)
class BurstEvent:
    """One upward frequency spike identified in an observation period."""

    topic: str
    period: str
    velocity: float
    strength: float

    def to_dict(self) -> dict[str, object]:
        return {
            "topic": self.topic,
            "period": self.period,
            "velocity": self.velocity,
            "strength": self.strength,
        }


class BurstDetector:
    """Detect upward frequency jumps above a configurable threshold."""

    def __init__(self, min_velocity: float = 2.0) -> None:
        if not math.isfinite(min_velocity) or min_velocity <= 0:
            raise ValueError("min_velocity must be a finite positive number")
        self.min_velocity = float(min_velocity)

    def detect(
        self,
        series: ObservationSeries | Iterable[TopicObservation],
        topic: str | None = None,
    ) -> list[BurstEvent]:
        """Return bursts sorted by topic and period, optionally for one topic."""
        observations = series if isinstance(series, ObservationSeries) else ObservationSeries(series)
        topics = [topic] if topic is not None else observations.topics()
        dynamics = TopicDynamics(observations)
        bursts: list[BurstEvent] = []
        for current_topic in topics:
            points = observations.for_topic(current_topic)
            for point, point_velocity in zip(points, dynamics.velocity(current_topic)):
                if point_velocity < self.min_velocity:
                    continue
                bursts.append(
                    BurstEvent(
                        topic=point.topic,
                        period=point.period,
                        velocity=point_velocity,
                        strength=min(1.0, point_velocity / self.min_velocity),
                    )
                )
        return sorted(bursts, key=lambda burst: (burst.topic, burst.period))


__all__ = ["BurstDetector", "BurstEvent"]
