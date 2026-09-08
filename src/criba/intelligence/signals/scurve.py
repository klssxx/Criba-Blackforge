"""Deterministic logistic S-curve approximation for topic observations (P07-T08)."""
from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass
from statistics import fmean

from ..contracts import TopicObservation
from .dynamics import ObservationSeries


@dataclass(frozen=True)
class SCurveFit:
    """Fitted logistic parameters and diagnostics for one topic."""

    topic: str
    lower_bound: float
    carrying_capacity: float
    growth_rate: float
    midpoint: float
    rmse: float
    r_squared: float
    sample_count: int

    def predict(self, step: float) -> float:
        """Predict the frequency at a zero-based period index."""
        exponent = max(-700.0, min(700.0, -self.growth_rate * (step - self.midpoint)))
        prediction = self.lower_bound + (
            (self.carrying_capacity - self.lower_bound) / (1.0 + math.exp(exponent))
        )
        if prediction >= self.carrying_capacity:
            return math.nextafter(self.carrying_capacity, self.lower_bound)
        if prediction <= self.lower_bound:
            return math.nextafter(self.lower_bound, self.carrying_capacity)
        return prediction

    def to_dict(self) -> dict[str, object]:
        return {
            "topic": self.topic,
            "lower_bound": self.lower_bound,
            "carrying_capacity": self.carrying_capacity,
            "growth_rate": self.growth_rate,
            "midpoint": self.midpoint,
            "rmse": self.rmse,
            "r_squared": self.r_squared,
            "sample_count": self.sample_count,
        }


class SCurveApproximator:
    """Estimate a rising logistic curve without external numerical libraries."""

    def __init__(self, min_points: int = 4, capacity_margin: float = 0.1) -> None:
        if min_points < 3:
            raise ValueError("min_points must be at least 3")
        if capacity_margin <= 0:
            raise ValueError("capacity_margin must be positive")
        self.min_points = min_points
        self.capacity_margin = capacity_margin

    def fit(
        self,
        series: ObservationSeries | Iterable[TopicObservation],
        topic: str | None = None,
    ) -> SCurveFit | None:
        """Fit one topic; infer the topic only when the series has one topic."""
        observations = series if isinstance(series, ObservationSeries) else ObservationSeries(series)
        if topic is None:
            topics = observations.topics()
            if len(topics) != 1:
                return None
            topic = topics[0]
        points = observations.for_topic(topic)
        if len(points) < self.min_points:
            return None

        values = [float(point.frequency) for point in points]
        lower = min(values)
        upper = max(values)
        span = upper - lower
        if span <= 0 or any(current < previous for previous, current in zip(values, values[1:])):
            return None

        capacity = upper + max(1.0, span * self.capacity_margin)
        x_values = list(range(len(values)))
        logits = [
            math.log(
                max(1e-9, min(1.0 - 1e-9, (value - lower) / (capacity - lower)))
                / max(1e-9, 1.0 - max(1e-9, min(1.0 - 1e-9, (value - lower) / (capacity - lower))))
            )
            for value in values
        ]
        x_mean = fmean(x_values)
        logit_mean = fmean(logits)
        denominator = sum((x - x_mean) ** 2 for x in x_values)
        if denominator == 0:
            return None
        growth_rate = sum(
            (x - x_mean) * (logit - logit_mean)
            for x, logit in zip(x_values, logits)
        ) / denominator
        if growth_rate <= 0:
            return None
        intercept = logit_mean - growth_rate * x_mean
        midpoint = -intercept / growth_rate
        predictions = [
            lower + (capacity - lower) / (1.0 + math.exp(
                max(-700.0, min(700.0, -growth_rate * (x - midpoint)))
            ))
            for x in x_values
        ]
        residuals = [value - prediction for value, prediction in zip(values, predictions)]
        rmse = math.sqrt(fmean([residual * residual for residual in residuals]))
        mean_value = fmean(values)
        total_sum = sum((value - mean_value) ** 2 for value in values)
        residual_sum = sum(residual * residual for residual in residuals)
        r_squared = 1.0 - residual_sum / total_sum if total_sum else 0.0
        return SCurveFit(
            topic=topic,
            lower_bound=round(lower, 12),
            carrying_capacity=round(capacity, 12),
            growth_rate=round(growth_rate, 12),
            midpoint=round(midpoint, 12),
            rmse=round(rmse, 12),
            r_squared=round(r_squared, 12),
            sample_count=len(values),
        )


__all__ = ["SCurveApproximator", "SCurveFit"]
