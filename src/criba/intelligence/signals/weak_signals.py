"""Deterministic aggregation of corroborating weak signals (P07-T06)."""
from __future__ import annotations

from collections.abc import Iterable

from ..contracts import WeakSignal


def _bounded(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _combine(values: Iterable[float]) -> float:
    remaining = 1.0
    for value in values:
        remaining *= 1.0 - _bounded(value)
    return round(1.0 - remaining, 12)


class WeakSignalAggregator:
    """Merge corroborating weak signals without counting an ID twice."""

    def aggregate(self, signals: Iterable[WeakSignal]) -> list[WeakSignal]:
        """Return one combined signal per semantic topic/direction group."""
        groups: dict[tuple[str, str, str, str], list[WeakSignal]] = {}
        seen_ids: set[str] = set()
        for signal in signals:
            if signal.signal_id and signal.signal_id in seen_ids:
                continue
            if signal.signal_id:
                seen_ids.add(signal.signal_id)
            key = (signal.topic, signal.kind, signal.direction, signal.lead_lag_hint)
            groups.setdefault(key, []).append(signal)

        aggregated: list[WeakSignal] = []
        for (topic, kind, direction, lead_lag_hint), members in groups.items():
            evidence_doc_ids = sorted(
                {doc_id for member in members for doc_id in member.evidence_doc_ids}
            )
            technique_ids = sorted(
                {technique_id for member in members for technique_id in member.technique_ids}
            )
            aggregated.append(
                WeakSignal(
                    kind=kind,
                    topic=topic,
                    strength=_combine(member.strength for member in members),
                    direction=direction,
                    evidence_doc_ids=tuple(evidence_doc_ids),
                    technique_ids=tuple(technique_ids),
                    lead_lag_hint=lead_lag_hint,
                    confidence=_combine(member.confidence for member in members),
                )
            )
        return sorted(
            aggregated,
            key=lambda signal: (signal.topic, signal.kind, signal.direction, signal.lead_lag_hint),
        )


__all__ = ["WeakSignalAggregator"]
