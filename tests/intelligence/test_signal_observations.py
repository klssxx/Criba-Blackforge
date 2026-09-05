"""P07-T01 tests for deterministic topic time-series observations."""
from __future__ import annotations

from criba.intelligence import contracts as C
from criba.intelligence.signals import ObservationSeries, TopicDynamics
from criba.intelligence.storage import IntelligenceStore


def test_observation_series_orders_points_by_period():
    series = ObservationSeries(
        [
            C.TopicObservation(topic="cooling", period="2026-02", frequency=4),
            C.TopicObservation(topic="cooling", period="2026-01", frequency=2),
            C.TopicObservation(topic="robotics", period="2026-01", frequency=9),
        ]
    )

    assert [point.period for point in series.for_topic("cooling")] == ["2026-01", "2026-02"]
    assert series.topics() == ["cooling", "robotics"]
    assert series.for_topic("missing") == []


def test_store_roundtrips_observations_in_period_order(tmp_path):
    store = IntelligenceStore(tmp_path / "intelligence.sqlite3")
    try:
        store.save_observation(
            C.TopicObservation(
                topic="cooling", period="2026-02", frequency=4,
                source_diversity=2, metadata={"source": "papers"},
            ).to_dict()
        )
        store.save_observation(
            C.TopicObservation(topic="cooling", period="2026-01", frequency=2).to_dict()
        )

        observations = store.list_observations(topic="cooling")
        assert [item["period"] for item in observations] == ["2026-01", "2026-02"]
        assert observations[1]["frequency"] == 4
        assert observations[1]["metadata"] == {"source": "papers"}
    finally:
        store.close()


def test_store_filters_topics_and_bounds_result_count(tmp_path):
    store = IntelligenceStore(tmp_path / "intelligence.sqlite3")
    try:
        for topic, period in (
            ("cooling", "2026-01"),
            ("robotics", "2026-01"),
            ("cooling", "2026-02"),
        ):
            store.save_observation(C.TopicObservation(topic=topic, period=period).to_dict())

        assert [item["topic"] for item in store.list_observations()] == [
            "cooling", "cooling", "robotics"
        ]
        assert len(store.list_observations(limit=2)) == 2
        assert store.list_observations(topic="missing") == []
        assert store.list_observations(limit=-1) == []
    finally:
        store.close()


def test_topic_dynamics_aligns_velocity_and_acceleration_to_periods():
    series = ObservationSeries(
        [
            C.TopicObservation(topic="cooling", period="2026-01", frequency=2),
            C.TopicObservation(topic="cooling", period="2026-02", frequency=4),
            C.TopicObservation(topic="cooling", period="2026-03", frequency=7),
        ]
    )

    dynamics = TopicDynamics(series)

    assert dynamics.velocity("cooling") == [0.0, 2.0, 3.0]
    assert dynamics.acceleration("cooling") == [0.0, 0.0, 1.0]


def test_topic_dynamics_accepts_raw_observations_and_short_series():
    dynamics = TopicDynamics(
        [
            C.TopicObservation(topic="cooling", period="2026-02", frequency=4),
            C.TopicObservation(topic="cooling", period="2026-01", frequency=2),
        ]
    )

    assert dynamics.velocity("cooling") == [0.0, 2.0]
    assert dynamics.acceleration("cooling") == [0.0, 0.0]
    assert TopicDynamics([]).velocity("missing") == []
