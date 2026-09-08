"""P07-T05 tests for deterministic anomaly detection."""
from __future__ import annotations

from criba.intelligence import contracts as C
from criba.intelligence.signals.anomaly import AnomalyDetector


def test_anomaly_detector_reports_robust_frequency_outlier():
    observations = [
        C.TopicObservation(topic="cooling", period="2026-01", frequency=2),
        C.TopicObservation(topic="cooling", period="2026-02", frequency=2),
        C.TopicObservation(topic="cooling", period="2026-03", frequency=2),
        C.TopicObservation(topic="cooling", period="2026-04", frequency=12),
        C.TopicObservation(topic="cooling", period="2026-05", frequency=2),
    ]

    anomalies = AnomalyDetector(threshold=3.0).detect(observations)

    assert [anomaly.to_dict() for anomaly in anomalies] == [
        {
            "topic": "cooling",
            "period": "2026-04",
            "frequency": 12,
            "baseline_median": 2.0,
            "score": 10.0,
            "direction": "up",
            "strength": 1.0,
        }
    ]
