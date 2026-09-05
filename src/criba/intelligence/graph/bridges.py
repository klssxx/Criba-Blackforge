"""Deterministic bridge-node analysis for the IIE graph sector (P06-T06)."""
from __future__ import annotations

from collections.abc import Iterable, Iterator

from .store import KnowledgeGraphStore


class BridgeNodeAnalyzer:
    """Find articulation points in the weakly connected graph."""

    def __init__(self, store: KnowledgeGraphStore) -> None:
        self.store = store

    def articulation_points(self, entity_ids: Iterable[str] | None = None) -> list[str]:
        """Return node ids whose removal increases their component count."""
        ids = self.store.node_ids() if entity_ids is None else sorted(set(entity_ids))
        allowed = set(ids)
        adjacency: dict[str, set[str]] = {entity_id: set() for entity_id in ids}
        for entity_id in ids:
            for edge in self.store.neighbors(entity_id):
                candidate = edge["dst"] if edge["src"] == entity_id else edge["src"]
                if candidate in allowed and candidate != entity_id:
                    adjacency[entity_id].add(candidate)
                    adjacency[candidate].add(entity_id)

        discovery: dict[str, int] = {}
        low: dict[str, int] = {}
        parent: dict[str, str | None] = {}
        child_count: dict[str, int] = {}
        articulation: set[str] = set()
        timestamp = 0

        for root in ids:
            if root in discovery:
                continue
            parent[root] = None
            child_count[root] = 0
            discovery[root] = low[root] = timestamp
            timestamp += 1
            stack: list[tuple[str, Iterator[str]]] = [(root, iter(sorted(adjacency[root])))]

            while stack:
                current, children = stack[-1]
                try:
                    candidate = next(children)
                except StopIteration:
                    stack.pop()
                    current_parent = parent[current]
                    if current_parent is None:
                        if child_count[current] > 1:
                            articulation.add(current)
                    else:
                        low[current_parent] = min(low[current_parent], low[current])
                        if (
                            parent[current_parent] is not None
                            and low[current] >= discovery[current_parent]
                        ):
                            articulation.add(current_parent)
                    continue

                if candidate not in discovery:
                    parent[candidate] = current
                    child_count[current] += 1
                    child_count[candidate] = 0
                    discovery[candidate] = low[candidate] = timestamp
                    timestamp += 1
                    stack.append((candidate, iter(sorted(adjacency[candidate]))))
                elif candidate != parent[current]:
                    low[current] = min(low[current], discovery[candidate])

        return sorted(articulation)


__all__ = ["BridgeNodeAnalyzer"]
