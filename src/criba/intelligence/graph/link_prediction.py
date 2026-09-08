"""Deterministic link-prediction interface for the IIE graph sector (P06-T07)."""
from __future__ import annotations

from typing import Any

from .store import KnowledgeGraphStore


class LinkPredictionInterface:
    """Rank absent links with an explainable common-neighbor score."""

    def __init__(self, store: KnowledgeGraphStore) -> None:
        self.store = store

    def predict(self, source: str, limit: int = 10) -> list[dict[str, Any]]:
        """Return ranked absent links from ``source`` using Jaccard similarity."""
        if limit < 0:
            raise ValueError("limit must be non-negative")
        if limit == 0:
            return []

        source_neighbors = self._neighbors(source)
        predictions: list[dict[str, Any]] = []
        for candidate in self.store.node_ids():
            if candidate == source or candidate in source_neighbors:
                continue
            candidate_neighbors = self._neighbors(candidate)
            common = sorted(source_neighbors & candidate_neighbors)
            union = source_neighbors | candidate_neighbors
            if not common or not union:
                continue
            predictions.append(
                {
                    "src": source,
                    "dst": candidate,
                    "score": len(common) / len(union),
                    "common_neighbors": common,
                }
            )

        predictions.sort(key=lambda prediction: (-float(prediction["score"]), str(prediction["dst"])))
        return predictions[:limit]

    def _neighbors(self, entity_id: str) -> set[str]:
        return {
            edge["dst"] if edge["src"] == entity_id else edge["src"]
            for edge in self.store.neighbors(entity_id)
            if edge["src"] != edge["dst"]
        }


LinkPredictor = LinkPredictionInterface

__all__ = ["LinkPredictionInterface", "LinkPredictor"]
