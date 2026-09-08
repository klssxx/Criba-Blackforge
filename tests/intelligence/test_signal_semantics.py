"""P07-T10 signal semantics audit tests.

Adversarial cross-component invariants for the signal sector: determinism,
input-order independence, cross-topic isolation, lead/lag antisymmetry and
aggregation provenance.
"""
from __future__ import annotations

import random

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

from .signal_fixtures import synthetic_series


def test_signal_results_are_deterministic_across_repeated_runs() -> None:
    series = synthetic_series()
    for _ in range(5):
        assert [b.to_dict() for b in BurstDetector().detect(series)] == [
            b.to_dict() for b in BurstDetector().detect(series)
        ]
        assert [a.to_dict() for a in AnomalyDetector().detect(series)] == [
            a.to_dict() for a in AnomalyDetector().detect(series)
        ]
        assert [c.to_dict() for c in ChangePointDetector().detect(series)] == [
            c.to_dict() for c in ChangePointDetector().detect(series)
        ]


def test_signal_results_are_independent_of_input_order() -> None:
    ordered = synthetic_series()
    points = list(ordered.all())
    shuffled = points[:]
    random.Random(20260903).shuffle(shuffled)
    reordered = ObservationSeries(shuffled)

    assert reordered.all() == ordered.all()
    assert BurstDetector().detect(reordered) == BurstDetector().detect(ordered)
    assert AnomalyDetector().detect(reordered) == AnomalyDetector().detect(ordered)
    assert ChangePointDetector().detect(reordered) == ChangePointDetector().detect(ordered)
    assert SCurveApproximator().fit(reordered.for_topic("quantum")) == SCurveApproximator().fit(
        ordered.for_topic("quantum")
    )


def test_unrelated_topics_do_not_contaminate_each_other() -> None:
    full = synthetic_series()
    quantum_only = ObservationSeries(full.for_topic("quantum"))

    assert TopicDynamics(full).velocity("quantum") == TopicDynamics(quantum_only).velocity(
        "quantum"
    )
    assert AnomalyDetector().detect(full, topic="quantum") == AnomalyDetector().detect(
        quantum_only, topic="quantum"
    )
    # "solid"'s spike must never leak into "quantum" anomaly output.
    spiked = {event.topic for event in AnomalyDetector().detect(full)}
    assert spiked == {"solid"}


def test_lead_lag_is_antisymmetric_under_topic_swap() -> None:
    series = synthetic_series()
    analyzer = LeadLagAnalyzer(max_lag=3)
    forward = analyzer.analyze(series, leader_topic="quantum", follower_topic="cooling")
    backward = analyzer.analyze(series, leader_topic="cooling", follower_topic="quantum")
    assert forward is not None and backward is not None
    assert forward.lag == -backward.lag
    assert forward.correlation == backward.correlation


def test_lead_lag_rejects_mismatched_series_lengths() -> None:
    series = synthetic_series()
    shorter = ObservationSeries(
        series.for_topic("cooling")[:-1] + series.for_topic("robotics")
    )
    assert LeadLagAnalyzer().analyze(shorter, "quantum", "cooling") is None


def test_velocity_documents_missing_periods_as_absent_not_zero() -> None:
    # Two observations with a period gap: velocity is computed across the
    # gap, so periods are labels, not a continuous time axis.
    gapped = ObservationSeries(
        [
            C.TopicObservation(topic="gaps", period="2026-01", frequency=2),
            C.TopicObservation(topic="gaps", period="2026-05", frequency=6),
        ]
    )
    dynamics = TopicDynamics(gapped)
    assert dynamics.velocity("gaps") == [0.0, 4.0]
    assert dynamics.acceleration("gaps") == [0.0, 0.0]


def test_burst_requires_strictly_positive_threshold_and_velocity() -> None:
    series = synthetic_series()
    bursts = BurstDetector(min_velocity=100.0).detect(series)
    assert bursts == []


def test_changepoint_windows_require_enough_points() -> None:
    tiny = ObservationSeries(
        [
            C.TopicObservation(topic="tiny", period="2026-01", frequency=1),
            C.TopicObservation(topic="tiny", period="2026-02", frequency=9),
            C.TopicObservation(topic="tiny", period="2026-03", frequency=1),
        ]
    )
    assert ChangePointDetector(window=2).detect(tiny) == []
    assert len(ChangePointDetector(window=1, min_delta=1.0).detect(tiny)) == 2


def test_aggregation_preserves_provenance_union() -> None:
    first = C.WeakSignal(
        kind="burst", topic="quantum", strength=0.5, direction="up",
        evidence_doc_ids=("doc-1", "doc-2"), technique_ids=("T097",),
        lead_lag_hint="cooling follows",
    )
    second = C.WeakSignal(
        kind="burst", topic="quantum", strength=0.5, direction="up",
        evidence_doc_ids=("doc-2", "doc-3"), technique_ids=("T099",),
        lead_lag_hint="cooling follows",
    )
    aggregated = WeakSignalAggregator().aggregate([first, second])
    assert len(aggregated) == 1
    assert aggregated[0].evidence_doc_ids == ("doc-1", "doc-2", "doc-3")
    assert aggregated[0].technique_ids == ("T097", "T099")


def test_scurve_rejects_declining_and_constant_series() -> None:
    declining = ObservationSeries(
        C.TopicObservation(topic="d", period=p, frequency=f)
        for p, f in zip(
            ("2026-01", "2026-02", "2026-03", "2026-04"), (9, 7, 5, 3)
        )
    )
    constant = ObservationSeries(
        C.TopicObservation(topic="c", period=p, frequency=5)
        for p in ("2026-01", "2026-02", "2026-03", "2026-04")
    )
    assert SCurveApproximator().fit(declining) is None
    assert SCurveApproximator().fit(constant) is None


def test_signal_sector_sources_do_not_import_external_numeric_libraries() -> None:
    import ast
    import pathlib

    forbidden = {"numpy", "scipy", "pandas", "statsmodels", "sklearn", "networkx", "neo4j"}
    signals_dir = pathlib.Path(__file__).resolve().parents[2] / "src/criba/intelligence/signals"
    offenders: list[str] = []
    for source_file in sorted(signals_dir.glob("*.py")):
        tree = ast.parse(source_file.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name.split(".")[0] for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module.split(".")[0]]
            else:
                continue
            offenders.extend(
                f"{source_file.name}: {name}" for name in names if name in forbidden
            )
    assert offenders == [], f"forbidden numeric imports found: {offenders}"
