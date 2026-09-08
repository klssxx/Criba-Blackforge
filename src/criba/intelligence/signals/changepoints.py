"""Deterministic two-window change-point detection (P07-T04)."""
from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass
from statistics import fmean

from ..contracts import TopicObservation
from .dynamics import ObservationSeries


@dataclass(frozen=True)
class ChangePointEvent:
    """A measurable level shift between adjacent observation windows."""

    topic: str
    period: str
    before_mean: float
    after_mean: float
    delta: float
    direction: str
    strength: float

    def to_dict(self) -> dict[str, object]:
        return {
            "topic": self.topic,
            "period": self.period,
            "before_mean": self.before_mean,
            "after_mean": self.after_mean,
            "delta": self.delta,
            "direction": self.direction,
            "strength": self.strength,
        }


class ChangePointDetector:
    """Find level shifts using adjacent fixed-size windows per topic."""

    def __init__(self, window: int = 2, min_delta: float = 1.0) -> None:
        if window < 1:
            raise ValueError("window must be a positive integer")
        if not math.isfinite(min_delta) or min_delta <= 0:
            raise ValueError("min_delta must be a finite positive number")
        self.window = window
        self.min_delta = float(min_delta)

    def detect(
        self,
        series: ObservationSeries | Iterable[TopicObservation],
        topic: str | None = None,
    ) -> list[ChangePointEvent]:
        """Return significant shifts sorted by topic and candidate period."""
        observations = series if isinstance(series, ObservationSeries) else ObservationSeries(series)
        topics = [topic] if topic is not None else observations.topics()
        changes: list[ChangePointEvent] = []
        for current_topic in topics:
            points = observations.for_topic(current_topic)
            for index in range(self.window, len(points) - self.window + 1):
                before_mean = fmean(
                    point.frequency for point in points[index - self.window : index]
                )
                after_mean = fmean(
                    point.frequency for point in points[index : index + self.window]
                )
                delta = after_mean - before_mean
                if abs(delta) < self.min_delta:
                    continue
                changes.append(
                    ChangePointEvent(
                        topic=current_topic,
                        period=points[index].period,
                        before_mean=before_mean,
                        after_mean=after_mean,
                        delta=delta,
                        direction="up" if delta > 0 else "down",
                        strength=min(1.0, abs(delta) / self.min_delta),
                    )
                )
        return sorted(changes, key=lambda change: (change.topic, change.period))


__all__ = ["ChangePointDetector", "ChangePointEvent"]
