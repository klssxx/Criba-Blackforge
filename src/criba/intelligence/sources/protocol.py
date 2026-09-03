"""IIE source protocol (P03-T01, blueprint §33).

IntelligenceSource: capabilities() / search() / fetch() / health().
States: AVAILABLE, DEGRADED, UNCONFIGURED, RATE_LIMITED, UNAVAILABLE, DISABLED.

Adapters are THIN: they build requests and normalize responses into
EvidenceDocument dicts. Transport (retries/rate/budget/cache) is injected —
tests never touch the network (§101).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from ..contracts import EvidenceDocument, QueryPlan, SourceQueryResult

__all__ = ["IntelligenceSource", "SourceContext"]


@dataclass
class SourceContext:
    """Injected dependencies for a source adapter (no globals)."""
    transport: Any                       # Transport protocol: get(url, params) -> Response
    cache_get: Callable[[str], Any] | None = None
    cache_set: Callable[[str, Any, float], None] | None = None
    credentials: dict[str, str] = field(default_factory=dict)

    def has_credential(self, name: str) -> bool:
        return bool(self.credentials.get(name))


class IntelligenceSource:
    """Base class. Subclasses set SOURCE_ID/NAME/KIND and implement
    _search()/health(); they must NOT import httpx directly."""
    SOURCE_ID: str = "abstract"
    NAME: str = "abstract"
    KIND: str = "abstract"
    BASE_URL: str = ""
    REQUIRES_CREDENTIALS: tuple[str, ...] = ()
    RATE_LIMIT_S: float = 1.0            # min seconds between requests
    TIMEOUT_S: float = 20.0

    def __init__(self, context: SourceContext):
        self.context = context
        self._last_request_ts: float = 0.0

    # -- public API (§33) ----------------------------------------------------
    def capabilities(self) -> list[str]:
        return ["search"]

    def source_id(self) -> str:
        return self.SOURCE_ID

    def health(self) -> str:
        missing = [c for c in self.REQUIRES_CREDENTIALS
                   if not self.context.has_credential(c)]
        if missing:
            return "UNCONFIGURED"
        return "AVAILABLE"

    def search(self, query: str, limit: int = 10, **params: Any) -> SourceQueryResult:
        """Template method: cache-first (§34), rate-limit, budget, then _search."""
        import time as _t

        cache_key = f"src:{self.SOURCE_ID}:q:{query}:n:{limit}:{sorted(params.items())}"
        if self.context.cache_get is not None:
            cached = self.context.cache_get(cache_key)
            if cached is not None:
                res = SourceQueryResult(source_id=self.SOURCE_ID, query_text=query, ok=True)
                res.documents = [EvidenceDocument(**d) for d in cached]
                return res

        now = _t.monotonic()
        wait = self._last_request_ts + self.RATE_LIMIT_S - now
        if wait > 0:
            _t.sleep(min(wait, self.RATE_LIMIT_S))
        self._last_request_ts = _t.monotonic()

        started = _t.monotonic()
        result = self._search(query, limit=limit, **params)
        result.elapsed_s = _t.monotonic() - started
        result.query_text = query

        if result.ok and self.context.cache_set is not None:
            self.context.cache_set(cache_key, [d.to_dict() for d in result.documents])
        return result

    # -- subclass hook --------------------------------------------------------
    def _search(self, query: str, limit: int = 10, **params: Any) -> SourceQueryResult:
        raise NotImplementedError

    def fetch(self, doc_id: str) -> EvidenceDocument | None:
        return None
