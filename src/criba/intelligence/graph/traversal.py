"""Deterministic graph traversal primitives for the IIE graph sector (P06-T03)."""
from __future__ import annotations

from collections import deque

from .store import KnowledgeGraphStore


class GraphTraversal:
    """Perform bounded, directed traversals over a knowledge graph store."""

    def __init__(self, store: KnowledgeGraphStore) -> None:
        self.store = store

    def bfs(self, start: str, max_depth: int = 1) -> list[str]:
        """Return reachable node ids in deterministic breadth-first order."""
        if max_depth < 0:
            raise ValueError("max_depth must be non-negative")

        order: list[str] = []
        seen = {start}
        queue: deque[tuple[str, int]] = deque([(start, 0)])
        while queue:
            current, depth = queue.popleft()
            order.append(current)
            if depth >= max_depth:
                continue
            for edge in self.store.neighbors(current):
                if edge["src"] != current:
                    continue
                candidate = edge["dst"]
                if candidate in seen:
                    continue
                seen.add(candidate)
                queue.append((candidate, depth + 1))
        return order

    def shortest_path(self, start: str, target: str) -> list[str] | None:
        """Delegate shortest-path semantics to the canonical graph store."""
        return self.store.shortest_path(start, target)


__all__ = ["GraphTraversal"]
