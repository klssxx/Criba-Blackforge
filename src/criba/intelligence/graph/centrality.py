"""Deterministic graph centrality metrics for the IIE graph sector (P06-T04)."""
from __future__ import annotations

from collections.abc import Iterable

from .store import KnowledgeGraphStore


class GraphCentrality:
    """Compute normalized, unweighted degree centrality."""

    def __init__(self, store: KnowledgeGraphStore) -> None:
        self.store = store

    def degree_centrality(self, entity_ids: Iterable[str] | None = None) -> dict[str, float]:
        """Return normalized unique-neighbor degree scores in sorted id order."""
        ids = (
            self.store.node_ids()
            if entity_ids is None
            else sorted(set(entity_ids))
        )
        allowed = set(ids)
        denominator = len(ids) - 1
        if denominator <= 0:
            return {entity_id: 0.0 for entity_id in ids}

        scores: dict[str, float] = {}
        for entity_id in ids:
            neighbors = {
                edge["dst"] if edge["src"] == entity_id else edge["src"]
                for edge in self.store.neighbors(entity_id)
                if edge["src"] in allowed and edge["dst"] in allowed
            }
            scores[entity_id] = len(neighbors) / denominator
        return scores


__all__ = ["GraphCentrality"]
