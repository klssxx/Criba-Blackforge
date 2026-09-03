"""Deterministic robust anomaly detection for topic frequencies (P07-T05)."""
from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass
from statistics import median

from ..contracts import TopicObservation
from .dynamics import ObservationSeries


@dataclass(frozen=True)
class AnomalyEvent:
    """A frequency observation whose robust deviation crosses the threshold."""

    topic: str
    period: str
    frequency: int
    baseline_median: float
    score: float
    direction: str
    strength: float

    def to_dict(self) -> dict[str, object]:
        return {
            "topic": self.topic,
            "period": self.period,
            "frequency": self.frequency,
            "baseline_median": self.baseline_median,
            "score": self.score,
            "direction": self.direction,
            "strength": self.strength,
        }


class AnomalyDetector:
    """Detect robust frequency outliers independently for each topic."""

    def __init__(self, threshold: float = 3.0) -> None:
        if not math.isfinite(threshold) or threshold <= 0:
            raise ValueError("threshold must be a finite positive number")
        self.threshold = float(threshold)

    def detect(
        self,
        series: ObservationSeries | Iterable[TopicObservation],
        topic: str | None = None,
    ) -> list[AnomalyEvent]:
        """Return outliers using median/MAD scores, sorted by topic and period."""
        observations = series if isinstance(series, ObservationSeries) else ObservationSeries(series)
        topics = [topic] if topic is not None else observations.topics()
        anomalies: list[AnomalyEvent] = []
        for current_topic in topics:
            points = observations.for_topic(current_topic)
            if not points:
                continue
            frequencies = [point.frequency for point in points]
            baseline_median = float(median(frequencies))
            deviations = [abs(frequency - baseline_median) for frequency in frequencies]
            mad = float(median(deviations))
            scale = 1.4826 * mad if mad > 0 else 1.0
            for point in points:
                score = abs(point.frequency - baseline_median) / scale
                if score < self.threshold:
                    continue
                anomalies.append(
                    AnomalyEvent(
                        topic=current_topic,
                        period=point.period,
                        frequency=point.frequency,
                        baseline_median=baseline_median,
                        score=score,
                        direction="up" if point.frequency > baseline_median else "down",
                        strength=min(1.0, score / self.threshold),
                    )
                )
        return sorted(anomalies, key=lambda anomaly: (anomaly.topic, anomaly.period))


__all__ = ["AnomalyDetector", "AnomalyEvent"]
