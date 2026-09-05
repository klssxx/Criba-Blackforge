"""Prior-art scout wrappers (P10).

Thin wrappers that run a query variant through an injected source adapter
while retaining its query text. PatentScout handles patents; ScienceScout
handles scientific sources (OpenAlex, Crossref, arXiv); CodeScout handles
code repositories (GitHub); ProductScout handles product/company search
(Wikipedia); CrossDomainScout collects evidence across multiple domains
without inferring analogies.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from math import isfinite

from ..contracts import QueryVariant, SourceQueryResult
from ..enums import PriorArtVerdict
from ..sources.protocol import IntelligenceSource
from ..sources.transport import BudgetExceeded, TransportBudget


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


class CodeScout:
    """Run a code query variant through an injected source adapter.

    Supported adapters: GitHub (free unauthenticated: 10 req/min).
    """

    def __init__(self, source: IntelligenceSource):
        self.source = source

    def search(self, variant: QueryVariant, *, limit: int = 10) -> SourceQueryResult:
        """Search one lattice variant while retaining its query text."""
        return self.source.search(variant.text, limit=limit)


class ProductScout:
    """Run a product query variant through an injected source adapter.

    Supported adapters: Wikipedia (free, no-key).
    """

    def __init__(self, source: IntelligenceSource):
        self.source = source

    def search(self, variant: QueryVariant, *, limit: int = 10) -> SourceQueryResult:
        """Search one lattice variant while retaining its query text."""
        return self.source.search(variant.text, limit=limit)


class CrossDomainScout:
    """Collect evidence from at least two explicitly different domains.

    This class is deliberately an evidence collector, not an analogy or
    verdict engine. It validates the cross-domain boundary, shares one
    transport budget across sources, and preserves partial failures.
    """

    def __init__(
        self,
        sources: Sequence[IntelligenceSource],
        *,
        budget: TransportBudget | None = None,
    ) -> None:
        self.sources = tuple(sources)
        if not self.sources:
            raise ValueError("sources must not be empty")
        self.budget = budget if budget is not None else TransportBudget()
        self._validate_budget(self.budget)
        self._source_ids = self._validate_sources(self.sources)

    @staticmethod
    def _validate_budget(budget: TransportBudget) -> None:
        if not isinstance(budget, TransportBudget):
            raise TypeError("budget must be a TransportBudget")
        if not isinstance(budget.max_requests, int) or isinstance(budget.max_requests, bool):
            raise TypeError("budget.max_requests must be an integer")
        if budget.max_requests < 1:
            raise ValueError("budget.max_requests must be at least 1")
        if not isinstance(budget.requests_made, int) or isinstance(budget.requests_made, bool):
            raise TypeError("budget.requests_made must be an integer")
        if not 0 <= budget.requests_made <= budget.max_requests:
            raise ValueError("budget.requests_made must be within max_requests")
        if (
            isinstance(budget.max_runtime_s, bool)
            or not isinstance(budget.max_runtime_s, (int, float))
            or not isfinite(budget.max_runtime_s)
            or budget.max_runtime_s <= 0
        ):
            raise ValueError("budget.max_runtime_s must be a finite positive number")

    @staticmethod
    def _validate_sources(sources: Sequence[IntelligenceSource]) -> tuple[str, ...]:
        source_ids: list[str] = []
        seen: set[str] = set()
        for source in sources:
            source_id_method = getattr(source, "source_id", None)
            if not callable(source_id_method):
                raise TypeError("source must expose source_id()")
            source_id = source_id_method()
            if not isinstance(source_id, str) or not source_id or source_id != source_id.strip():
                raise ValueError("source_id must be a non-blank trimmed string")
            if source_id in seen:
                raise ValueError(f"duplicate source_id: {source_id}")
            seen.add(source_id)
            source_ids.append(source_id)

            kind = getattr(source, "KIND", "")
            if not isinstance(kind, str) or not kind or kind != kind.strip():
                raise ValueError(f"source {source_id} must declare a non-blank KIND")
            transport = getattr(getattr(source, "context", None), "transport", None)
            if not callable(getattr(transport, "get", None)) or not hasattr(transport, "budget"):
                raise ValueError(
                    f"source {source_id} transport must expose get() and budget"
                )
        return tuple(source_ids)

    @staticmethod
    def _domain(source: IntelligenceSource) -> str:
        return str(source.KIND).strip().casefold()

    @staticmethod
    def _failure(source_id: str, query_text: str, error: str) -> SourceQueryResult:
        return SourceQueryResult(
            source_id=source_id,
            query_text=query_text,
            ok=False,
            error=error,
        )

    def cross_search(
        self,
        variant: QueryVariant,
        *,
        limit_per_source: int = 5,
    ) -> dict[str, SourceQueryResult]:
        """Search one query across distinct source domains.

        The returned dictionary is ordered by source ID. Every configured source
        receives one result, including sources skipped after a global budget
        exhaustion or sources whose adapter raises an exception.
        """
        if not isinstance(variant, QueryVariant):
            raise TypeError("variant must be a QueryVariant")
        if not isinstance(variant.text, str) or not variant.text.strip():
            raise ValueError("variant.text must not be blank")
        if not isinstance(limit_per_source, int) or isinstance(limit_per_source, bool):
            raise TypeError("limit_per_source must be an integer")
        if limit_per_source < 1:
            raise ValueError("limit_per_source must be at least 1")
        domains = {self._domain(source) for source in self.sources}
        if len(domains) < 2:
            raise ValueError("cross-domain search requires at least two distinct domains")

        results: dict[str, SourceQueryResult] = {}
        sources_by_id = sorted(self.sources, key=lambda source: source.source_id())
        for source in sources_by_id:
            source_id = source.source_id()
            if self.budget.exhausted:
                results[source_id] = self._failure(
                    source_id, variant.text, "GLOBAL_BUDGET_EXHAUSTED"
                )
                continue

            transport = source.context.transport
            previous_budget = transport.budget
            transport.budget = self.budget
            try:
                result = source.search(variant.text, limit=limit_per_source)
            except BudgetExceeded:
                result = self._failure(
                    source_id, variant.text, "GLOBAL_BUDGET_EXHAUSTED"
                )
            except Exception as exc:  # noqa: BLE001 - isolate each adapter
                result = self._failure(
                    source_id,
                    variant.text,
                    f"SOURCE_EXCEPTION:{type(exc).__name__}",
                )
            finally:
                transport.budget = previous_budget

            if (
                not isinstance(result, SourceQueryResult)
                or result.source_id != source_id
                or result.query_text != variant.text
            ):
                result = self._failure(
                    source_id, variant.text, "SOURCE_CONTRACT_ERROR"
                )
            results[source_id] = result
        return results

    def validate_downstream_handoff(
        self,
        results: Mapping[str, SourceQueryResult],
        *,
        skeptic: Mapping[str, object] | None,
        verdict: str | None,
    ) -> None:
        """Fail closed before evidence reaches the later skeptic/verdict stages.

        This is a boundary validator only. It does not implement either later
        stage and therefore cannot establish end-to-end integration by itself.
        """
        if not isinstance(results, Mapping) or set(results) != set(self._source_ids):
            raise ValueError("HANDOFF_RESULTS_MISMATCH")
        for source_id, result in results.items():
            if not isinstance(result, SourceQueryResult) or result.source_id != source_id:
                raise ValueError("HANDOFF_RESULTS_MISMATCH")
        if skeptic is None:
            raise ValueError("SKEPTIC_REQUIRED")
        if not isinstance(skeptic, Mapping):
            raise TypeError("SKEPTIC_CONTRACT_ERROR")
        if verdict is None or not isinstance(verdict, str) or not verdict.strip():
            raise ValueError("VERDICT_REQUIRED")
        allowed_verdicts = {item.value for item in PriorArtVerdict}
        if verdict not in allowed_verdicts:
            raise ValueError("VERDICT_REJECTED")

        skeptic_verdict = skeptic.get("verdict")
        if not isinstance(skeptic_verdict, str) or not skeptic_verdict.strip():
            raise ValueError("SKEPTIC_REQUIRED")
        if skeptic_verdict.strip().casefold() in {"reject", "rejected"}:
            raise ValueError("SKEPTIC_REJECTED")

        evidence_gaps = skeptic.get("evidence_gaps", ())
        if evidence_gaps is None:
            evidence_gaps = ()
        if not isinstance(evidence_gaps, (list, tuple, set)):
            raise TypeError("SKEPTIC_CONTRACT_ERROR")
        if verdict == PriorArtVerdict.SURVIVED_SEARCH.value and (
            evidence_gaps or any(not result.ok for result in results.values())
        ):
            raise ValueError("DOWNSTREAM_CONTRADICTION")
