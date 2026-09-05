"""Deterministic cross-topic lead/lag correlation analysis (P07-T07)."""
from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass
from statistics import fmean

from ..contracts import TopicObservation
from .dynamics import ObservationSeries


@dataclass(frozen=True)
class LeadLagResult:
    """Best tested lag between a leader and follower topic."""

    leader_topic: str
    follower_topic: str
    lag: int
    correlation: float
    strength: float
    overlap: int

    def to_dict(self) -> dict[str, object]:
        return {
            "leader_topic": self.leader_topic,
            "follower_topic": self.follower_topic,
            "lag": self.lag,
            "correlation": self.correlation,
            "strength": self.strength,
            "overlap": self.overlap,
        }


def _correlation(left: list[int], right: list[int]) -> float:
    if len(left) < 2 or len(left) != len(right):
        return 0.0
    left_mean = fmean(left)
    right_mean = fmean(right)
    numerator = sum((x - left_mean) * (y - right_mean) for x, y in zip(left, right))
    left_norm = sum((x - left_mean) ** 2 for x in left)
    right_norm = sum((y - right_mean) ** 2 for y in right)
    denominator = math.sqrt(left_norm * right_norm)
    if denominator == 0:
        return 0.0
    return round(numerator / denominator, 12)


class LeadLagAnalyzer:
    """Find the strongest Pearson correlation over a bounded integer lag."""

    def __init__(self, max_lag: int = 3) -> None:
        if max_lag < 0:
            raise ValueError("max_lag must be non-negative")
        self.max_lag = max_lag

    def analyze(
        self,
        series: ObservationSeries | Iterable[TopicObservation],
        leader_topic: str,
        follower_topic: str,
    ) -> LeadLagResult | None:
        """Return the best lag; positive means follower follows later."""
        observations = series if isinstance(series, ObservationSeries) else ObservationSeries(series)
        leader = [point.frequency for point in observations.for_topic(leader_topic)]
        follower = [point.frequency for point in observations.for_topic(follower_topic)]
        if len(leader) != len(follower) or len(leader) < 2:
            return None

        candidates: list[LeadLagResult] = []
        for lag in range(-self.max_lag, self.max_lag + 1):
            if lag >= 0:
                left = leader[: len(leader) - lag] if lag else leader
                right = follower[lag:] if lag else follower
            else:
                left = leader[-lag:]
                right = follower[: len(follower) + lag]
            if len(left) < 2:
                continue
            correlation = _correlation(left, right)
            candidates.append(
                LeadLagResult(
                    leader_topic=leader_topic,
                    follower_topic=follower_topic,
                    lag=lag,
                    correlation=correlation,
                    strength=abs(correlation),
                    overlap=len(left),
                )
            )
        if not candidates:
            return None
        return min(
            candidates,
            key=lambda result: (
                -result.strength,
                abs(result.lag),
                0 if result.lag >= 0 else 1,
                result.lag,
            ),
        )


__all__ = ["LeadLagAnalyzer", "LeadLagResult"]
