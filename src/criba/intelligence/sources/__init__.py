"""IIE source registry: the default active pair is free and key-less (0€).

Wikipedia (encyclopedic/product evidence) + Google Patents (patent evidence)
run by default. Optional sources (GitHub, OpenAlex, Crossref, arXiv, EPO,
ClinicalTrials, NSF) activate behind ``CRIBA_IIE_EXTRA_SOURCES=1`` or
``build_sources(context, extra=True)``.
"""
from __future__ import annotations

import os
from typing import Any

from .adapters import (
    ArxivSource,
    ClinicalTrialsSource,
    CrossrefSource,
    EpoOpsSource,
    GitHubSource,
    NsfAwardsSource,
    OpenAlexSource,
)
from .google_patents import GooglePatentsSource
from .protocol import IntelligenceSource, SourceContext
from .transport import Transport, TransportBudget
from .wikipedia import WikipediaSource

_DEFAULT_ACTIVE = (WikipediaSource, GooglePatentsSource)
_OPTIONAL = (
    GitHubSource,
    OpenAlexSource,
    CrossrefSource,
    ArxivSource,
    EpoOpsSource,
    ClinicalTrialsSource,
    NsfAwardsSource,
)


def build_sources(context: SourceContext, *, extra: bool = False) -> list[IntelligenceSource]:
    """Build the active sources: the free pair by default, extras opt-in."""
    classes = list(_DEFAULT_ACTIVE)
    if extra or os.environ.get("CRIBA_IIE_EXTRA_SOURCES", "") == "1":
        classes.extend(_OPTIONAL)
    return [cls(context) for cls in classes]


def default_context(cache: Any = None, credentials: dict[str, str] | None = None,
                    budget: TransportBudget | None = None) -> SourceContext:
    """Wire cache + transport. cache = IntelligenceStore or None."""
    return SourceContext(
        transport=Transport(budget=budget),
        cache_get=cache.cache_get if cache else None,
        cache_set=cache.cache_set if cache else None,
        credentials=credentials or {},
    )
