"""Prior-art scout wrappers (P10)."""
from __future__ import annotations

from ..contracts import QueryVariant, SourceQueryResult
from ..sources.protocol import IntelligenceSource


class PatentScout:
    """Run a patent query variant through an injected source adapter."""

    def __init__(self, source: IntelligenceSource):
        self.source = source

    def search(self, variant: QueryVariant, *, limit: int = 10) -> SourceQueryResult:
        """Search one lattice variant while retaining its query text."""
        return self.source.search(variant.text, limit=limit)
