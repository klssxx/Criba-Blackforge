"""P07-T09 synthetic time-series tests for the signal sector."""
from __future__ import annotations

from criba.intelligence import contracts as C
from criba.intelligence.signals import (
    AnomalyDetector,
    BurstDetector,
    ChangePointDetector,
    LeadLagAnalyzer,
    ObservationSeries,
    SCurveApproximator,
    TopicDynamics,
    WeakSignalAggregator,
)
from criba.intelligence.storage import IntelligenceStore

from .signal_fixtures import (
    COOLING_FREQUENCIES,
    PERIODS,
    QUANTUM_FREQUENCIES,
    SOLID_FREQUENCIES,
    quantum_observations,
    synthetic_series,
)


def test_fixture_periods_are_sorted_and_aligned() -> None:
    series = synthetic_series()
    assert PERIODS == tuple(sorted(PERIODS))
    assert len(set(PERIODS)) == len(PERIODS)
    for topic in ("quantum", "cooling", "robotics", "solid"):
        assert [point.period for point in series.for_topic(topic)] == list(PERIODS)
    assert [point.frequency for point in series.for_topic("quantum")] == list(
        QUANTUM_FREQUENCIES
    )


def test_fixture_roundtrips_through_store_in_order(tmp_path) -> None:
    store = IntelligenceStore(tmp_path / "intelligence.sqlite3")
    try:
        for observation in synthetic_series().all():
            store.save_observation(observation.to_dict())
        rows = store.list_observations()
        assert all(set(row) == {"obs_id", "topic", "period", "frequency", "source_diversity", "metadata"} for row in rows)
        restored = ObservationSeries(
            C.TopicObservation(
                topic=row["topic"], period=row["period"], frequency=row["frequency"],
                source_diversity=row["source_diversity"], metadata=row["metadata"],
            )
            for row in rows
        )
        assert restored.all() == synthetic_series().all()
    finally:
        store.close()


def test_synthetic_bursts_track_ramp_acceleration() -> None:
    bursts = BurstDetector(min_velocity=2.0).detect(synthetic_series(), topic="quantum")
    assert [burst.period for burst in bursts] == [
        "2026-03", "2026-04", "2026-05", "2026-06", "2026-07",
    ]
    assert all(burst.velocity >= 2.0 for burst in bursts)
    assert [burst.velocity for burst in bursts] == [2.0, 3.0, 4.0, 5.0, 6.0]


def test_synthetic_change_points_find_level_shift_in_ramp() -> None:
    changes = ChangePointDetector(window=2, min_delta=1.0).detect(
        synthetic_series(), topic="quantum"
    )
    assert changes
    assert all(change.direction == "up" for change in changes)
    assert [change.period for change in changes] == [
        "2026-02", "2026-03", "2026-04", "2026-05", "2026-06",
    ]


def test_synthetic_anomaly_isolates_only_the_spiking_period() -> None:
    anomalies = AnomalyDetector(threshold=3.0).detect(synthetic_series())
    assert [(event.topic, event.period) for event in anomalies] == [
        ("solid", "2026-07")
    ]
    assert anomalies[0].direction == "up"
    assert anomalies[0].frequency == SOLID_FREQUENCIES[-1]


def test_synthetic_lead_lag_recovers_one_period_offset() -> None:
    result = LeadLagAnalyzer(max_lag=3).analyze(
        synthetic_series(), leader_topic="quantum", follower_topic="cooling"
    )
    assert result is not None
    assert result.lag == 1
    assert result.correlation > 0.99


def test_synthetic_flat_topic_has_no_dynamics_or_signals() -> None:
    series = synthetic_series()
    dynamics = TopicDynamics(series)
    assert set(dynamics.velocity("robotics")) == {0}
    assert set(dynamics.acceleration("robotics")) == {0}
    assert BurstDetector().detect(series, topic="robotics") == []
    assert AnomalyDetector().detect(series, topic="robotics") == []
    assert ChangePointDetector().detect(series, topic="robotics") == []


def test_synthetic_scurve_fits_ramp_with_positive_growth() -> None:
    fit = SCurveApproximator(min_points=4).fit(
        quantum_observations()
    )
    assert fit is not None
    assert fit.topic == "quantum"
    assert fit.growth_rate > 0
    assert fit.carrying_capacity > max(QUANTUM_FREQUENCIES)
    assert fit.lower_bound == float(min(QUANTUM_FREQUENCIES))
    assert fit.r_squared > 0.8
    # Extrapolation stays strictly inside the fitted asymptote.
    assert fit.predict(len(QUANTUM_FREQUENCIES)) < fit.carrying_capacity
    assert fit.predict(len(QUANTUM_FREQUENCIES)) >= max(QUANTUM_FREQUENCIES)


def test_synthetic_declining_series_has_no_scurve_fit() -> None:
    declining = ObservationSeries(
        C.TopicObservation(topic="falling", period=period, frequency=frequency)
        for period, frequency in zip(PERIODS, reversed(QUANTUM_FREQUENCIES))
    )
    assert SCurveApproximator().fit(declining) is None


def test_synthetic_weak_signal_aggregation_deduplicates_ids() -> None:
    base = C.WeakSignal(
        kind="burst", topic="quantum", strength=0.4, direction="up",
        lead_lag_hint="cooling follows",
    )
    duplicate = C.WeakSignal(
        kind="burst", topic="quantum", strength=0.9, direction="up",
        lead_lag_hint="cooling follows",
    )
    duplicate.signal_id = base.signal_id
    corroborator = C.WeakSignal(
        kind="burst", topic="quantum", strength=0.5, direction="up",
        lead_lag_hint="cooling follows",
    )
    aggregated = WeakSignalAggregator().aggregate([base, duplicate, corroborator])
    assert len(aggregated) == 1
    # 1 - (1 - 0.4) * (1 - 0.5) == 0.7; the duplicate id was ignored.
    assert aggregated[0].strength == 0.7


def test_cooling_fixture_is_shifted_quantum_by_one_period() -> None:
    assert COOLING_FREQUENCIES == (0,) + QUANTUM_FREQUENCIES[:-1]
