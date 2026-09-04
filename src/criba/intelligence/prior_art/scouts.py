"""Prior-art scout wrappers (P10).

Thin wrappers that run a query variant through an injected source adapter
while retaining its query text. PatentScout handles patents; ScienceScout
handles scientific sources (OpenAlex, Crossref, arXiv).
"""
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


class ScienceScout:
    """Run a scientific query variant through an injected source adapter.

    Supported adapters: OpenAlex, Crossref, arXiv (free, no-key).
    """

    def __init__(self, source: IntelligenceSource):
        self.source = source

    def search(self, variant: QueryVariant, *, limit: int = 10) -> SourceQueryResult:
        """Search one lattice variant while retaining its query text."""
        return self.source.search(variant.text, limit=limit)
