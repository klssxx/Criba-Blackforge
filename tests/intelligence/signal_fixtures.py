"""Reusable synthetic time-series observation fixtures for P07 signal tests.

The topology provides stable periods and deterministic frequencies so every
signal component can be exercised without production data.
"""
from __future__ import annotations

from criba.intelligence import contracts as C
from criba.intelligence.signals import ObservationSeries

PERIODS: tuple[str, ...] = (
    "2025-12", "2026-01", "2026-02", "2026-03", "2026-04",
    "2026-05", "2026-06", "2026-07",
)

# "quantum" ramps smoothly and monotonically (velocity/burst/S-curve shape).
QUANTUM_FREQUENCIES: tuple[int, ...] = (1, 2, 3, 5, 8, 12, 17, 23)
# "cooling" lags "quantum" by one period with identical shape (lead/lag).
COOLING_FREQUENCIES: tuple[int, ...] = (0, 1, 2, 3, 5, 8, 12, 17)
# "robotics" stays flat (baseline/anomaly-negative control).
ROBOTICS_FREQUENCIES: tuple[int, ...] = (10, 10, 10, 10, 10, 10, 10, 10)
# "solid" spikes only in the last period (anomaly control).
SOLID_FREQUENCIES: tuple[int, ...] = (4, 4, 4, 4, 4, 4, 4, 40)


def _observations(topic: str, frequencies: tuple[int, ...]) -> list[C.TopicObservation]:
    return [
        C.TopicObservation(topic=topic, period=period, frequency=frequency)
        for period, frequency in zip(PERIODS, frequencies)
    ]


def synthetic_series() -> ObservationSeries:
    """Return the shared multi-topic synthetic observation series."""
    return ObservationSeries(
        _observations("quantum", QUANTUM_FREQUENCIES)
        + _observations("cooling", COOLING_FREQUENCIES)
        + _observations("robotics", ROBOTICS_FREQUENCIES)
        + _observations("solid", SOLID_FREQUENCIES)
    )


def quantum_observations() -> list[C.TopicObservation]:
    return _observations("quantum", QUANTUM_FREQUENCIES)


__all__ = [
    "PERIODS",
    "QUANTUM_FREQUENCIES",
    "COOLING_FREQUENCIES",
    "ROBOTICS_FREQUENCIES",
    "SOLID_FREQUENCIES",
    "synthetic_series",
    "quantum_observations",
]
