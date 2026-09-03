"""Deterministic weak-community detection for the IIE graph sector (P06-T05)."""
from __future__ import annotations

from collections import deque
from collections.abc import Iterable

from .store import KnowledgeGraphStore


class CommunityDetector:
    """Group nodes into weakly connected communities."""

    def __init__(self, store: KnowledgeGraphStore) -> None:
        self.store = store

    def detect(self, entity_ids: Iterable[str] | None = None) -> list[list[str]]:
        """Return sorted weak components, optionally restricted to a node subset."""
        ids = (
            self.store.node_ids()
            if entity_ids is None
            else sorted(set(entity_ids))
        )
        allowed = set(ids)
        seen: set[str] = set()
        communities: list[list[str]] = []

        for start in ids:
            if start in seen:
                continue
            component: list[str] = []
            queue: deque[str] = deque([start])
            seen.add(start)
            while queue:
                current = queue.popleft()
                component.append(current)
                for edge in self.store.neighbors(current):
                    candidate = edge["dst"] if edge["src"] == current else edge["src"]
                    if candidate not in allowed or candidate in seen:
                        continue
                    seen.add(candidate)
                    queue.append(candidate)
            communities.append(sorted(component))

        communities.sort(key=lambda community: community[0])
        return communities


__all__ = ["CommunityDetector"]
