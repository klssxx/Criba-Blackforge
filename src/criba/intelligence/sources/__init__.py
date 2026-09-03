"""IIE source registry (P03): discovery of available sources (§114)."""
from __future__ import annotations

from .adapters import ArxivSource, CrossrefSource, EpoOpsSource, GitHubSource, OpenAlexSource
from .protocol import IntelligenceSource, SourceContext
from .transport import Transport, TransportBudget

_ALL = [OpenAlexSource, CrossrefSource, ArxivSource, GitHubSource, EpoOpsSource]


def build_sources(context: SourceContext) -> list[IntelligenceSource]:
    return [cls(context) for cls in _ALL]


def default_context(cache=None, credentials: dict | None = None,
                    budget: TransportBudget | None = None) -> SourceContext:
    """Wire cache + transport. cache = IntelligenceStore or None."""
    return SourceContext(
        transport=Transport(budget=budget),
        cache_get=cache.cache_get if cache else None,
        cache_set=cache.cache_set if cache else None,
        credentials=credentials or {},
    )
