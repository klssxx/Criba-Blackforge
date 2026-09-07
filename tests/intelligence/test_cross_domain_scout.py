"""P10-T07: CrossDomainScout contract across multiple sources."""
from __future__ import annotations

import json

import pytest

from criba.intelligence.contracts import QueryVariant, SourceQueryResult
from criba.intelligence.prior_art import CrossDomainScout
from criba.intelligence.sources.adapters import GitHubSource, OpenAlexSource
from criba.intelligence.sources.protocol import IntelligenceSource, SourceContext
from criba.intelligence.sources.transport import Response, Transport, TransportBudget

OPEN_ALEX_JSON = json.dumps({
    "results": [
        {"id": "https://openalex.org/W1", "title": "Thermal management paper",
         "publication_year": 2024, "abstract_inverted_index": {"thermal": [0]}}
    ]
})

GITHUB_JSON = json.dumps({
    "items": [
        {"full_name": "thermal-solutions/heat-sink", "description": "Thermal management",
         "html_url": "https://github.com/thermal-solutions/heat-sink",
         "url": "https://api.github.com/repos/thermal-solutions/heat-sink",
         "created_at": "2023-01-01T00:00:00Z", "language": "Python", "stargazers_count": 10}
    ]
})


def test_cross_domain_scout_searches_all_sources() -> None:
    sources = [
        OpenAlexSource(SourceContext(transport=Transport(
            sender=lambda *a, **k: Response(200, OPEN_ALEX_JSON)))),
        GitHubSource(SourceContext(transport=Transport(
            sender=lambda *a, **k: Response(200, GITHUB_JSON)))),
    ]
    scout = CrossDomainScout(sources)
    results = scout.cross_search(QueryVariant("thermal management"), limit_per_source=1)

    assert "openalex" in results
    assert "github" in results
    assert results["openalex"].ok is True
    assert results["github"].ok is True
    assert len(results["openalex"].documents) == 1
    assert len(results["github"].documents) == 1
    assert results["openalex"].documents[0].title == "Thermal management paper"
    assert results["github"].documents[0].title == "thermal-solutions/heat-sink"


def test_cross_domain_scout_retains_query_text() -> None:
    sources = [
        OpenAlexSource(SourceContext(transport=Transport(
            sender=lambda *a, **k: Response(200, OPEN_ALEX_JSON)))),
        GitHubSource(SourceContext(transport=Transport(
            sender=lambda *a, **k: Response(200, GITHUB_JSON)))),
    ]
    scout = CrossDomainScout(sources)
    results = scout.cross_search(QueryVariant("heat transfer"), limit_per_source=1)

    assert results["openalex"].query_text == "heat transfer"


def test_cross_domain_scout_propagates_failures() -> None:
    sources = [
        OpenAlexSource(SourceContext(transport=Transport(
            sender=lambda *a, **k: Response(503, "")))),
        GitHubSource(SourceContext(transport=Transport(
            sender=lambda *a, **k: Response(200, GITHUB_JSON)))),
    ]
    scout = CrossDomainScout(sources)
    results = scout.cross_search(QueryVariant("cooling"), limit_per_source=1)

    assert results["openalex"].ok is False
    assert "HTTP 503" in results["openalex"].error
    assert results["github"].ok is True


class _StubSource(IntelligenceSource):
    RATE_LIMIT_S = 0.0

    def __init__(self, source_id: str, kind: str, failure: Exception | None = None) -> None:
        super().__init__(SourceContext(transport=Transport(
            sender=lambda *a, **k: Response(200, "{}"))))
        self.SOURCE_ID = source_id
        self.KIND = kind
        self.failure = failure
        self.calls = 0

    def _search(self, query: str, limit: int = 10, **params: object) -> SourceQueryResult:
        self.calls += 1
        self.context.transport.get("https://stub.invalid")
        if self.failure is not None:
            raise self.failure
        return SourceQueryResult(
            source_id=self.SOURCE_ID,
            query_text=query,
            ok=True,
        )


def _skeptic_payload(**changes: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "thesis_under_attack": "cross-domain evidence",
        "evidence_gaps": [],
        "falsification_tests": ["compare mechanisms"],
        "verdict": "survives",
    }
    payload.update(changes)
    return payload


def test_cross_domain_scout_rejects_sources_from_one_domain() -> None:
    scout = CrossDomainScout([
        _StubSource("science-a", "science"),
        _StubSource("science-b", "science"),
    ])

    with pytest.raises(ValueError, match="distinct domains"):
        scout.cross_search(QueryVariant("thermal"))


def test_cross_domain_scout_rejects_duplicate_source_ids() -> None:
    with pytest.raises(ValueError, match="duplicate source_id"):
        CrossDomainScout([
            _StubSource("same", "science"),
            _StubSource("same", "code"),
        ])


def test_cross_domain_scout_rejects_invalid_limit() -> None:
    scout = CrossDomainScout([
        _StubSource("science", "science"),
        _StubSource("code", "code"),
    ])

    with pytest.raises(ValueError, match="limit_per_source"):
        scout.cross_search(QueryVariant("thermal"), limit_per_source=0)


def test_cross_domain_scout_rejects_nonpositive_global_budget() -> None:
    with pytest.raises(ValueError, match="max_requests"):
        CrossDomainScout([
            _StubSource("science", "science"),
            _StubSource("code", "code"),
        ], budget=TransportBudget(max_requests=0))


def test_cross_domain_scout_rejects_wrong_budget_type() -> None:
    with pytest.raises(TypeError, match="TransportBudget"):
        CrossDomainScout([
            _StubSource("science", "science"),
            _StubSource("code", "code"),
        ], budget="not-a-budget")  # type: ignore[arg-type]


def test_cross_domain_scout_rejects_spent_budget_state() -> None:
    budget = TransportBudget(max_requests=1)
    budget.requests_made = 2

    with pytest.raises(ValueError, match="requests_made"):
        CrossDomainScout([
            _StubSource("science", "science"),
            _StubSource("code", "code"),
        ], budget=budget)


def test_cross_domain_scout_stops_at_shared_global_budget() -> None:
    first = _StubSource("alpha", "science")
    second = _StubSource("beta", "code")
    budget = TransportBudget(max_requests=1)
    scout = CrossDomainScout([second, first], budget=budget)

    results = scout.cross_search(QueryVariant("thermal"))

    assert budget.requests_made == 1
    assert first.calls == 1
    assert second.calls == 0
    assert results["alpha"].ok is True
    assert results["beta"].ok is False
    assert results["beta"].error == "GLOBAL_BUDGET_EXHAUSTED"


def test_cross_domain_scout_orders_results_by_source_id() -> None:
    forward = CrossDomainScout([
        _StubSource("zeta", "code"),
        _StubSource("alpha", "science"),
    ]).cross_search(QueryVariant("thermal"))
    reverse = CrossDomainScout([
        _StubSource("alpha", "science"),
        _StubSource("zeta", "code"),
    ]).cross_search(QueryVariant("thermal"))

    assert list(forward) == ["alpha", "zeta"]
    assert list(reverse) == ["alpha", "zeta"]


def test_cross_domain_scout_contains_source_exception_as_partial_failure() -> None:
    broken = _StubSource("broken", "science", RuntimeError("secret-like detail"))
    good = _StubSource("good", "code")

    results = CrossDomainScout([broken, good]).cross_search(QueryVariant("thermal"))

    assert results["broken"].ok is False
    assert results["broken"].error == "SOURCE_EXCEPTION:RuntimeError"
    assert "secret-like detail" not in results["broken"].error
    assert results["good"].ok is True


def test_cross_domain_scout_handoff_rejects_missing_skeptic() -> None:
    scout = CrossDomainScout([
        _StubSource("science", "science"),
        _StubSource("code", "code"),
    ])
    results = scout.cross_search(QueryVariant("thermal"))

    with pytest.raises(ValueError, match="SKEPTIC_REQUIRED"):
        scout.validate_downstream_handoff(results, skeptic=None, verdict="UNRESOLVED")


def test_cross_domain_scout_handoff_rejects_missing_verdict() -> None:
    scout = CrossDomainScout([
        _StubSource("science", "science"),
        _StubSource("code", "code"),
    ])
    results = scout.cross_search(QueryVariant("thermal"))

    with pytest.raises(ValueError, match="VERDICT_REQUIRED"):
        scout.validate_downstream_handoff(results, skeptic=_skeptic_payload(), verdict=None)


def test_cross_domain_scout_handoff_rejects_contradictory_survival() -> None:
    scout = CrossDomainScout([
        _StubSource("science", "science"),
        _StubSource("code", "code"),
    ])
    results = scout.cross_search(QueryVariant("thermal"))

    with pytest.raises(ValueError, match="DOWNSTREAM_CONTRADICTION"):
        scout.validate_downstream_handoff(
            results,
            skeptic=_skeptic_payload(evidence_gaps=["missing mechanism evidence"]),
            verdict="SURVIVED_SEARCH",
        )


def test_cross_domain_scout_handoff_rejects_skeptic_rejection() -> None:
    scout = CrossDomainScout([
        _StubSource("science", "science"),
        _StubSource("code", "code"),
    ])
    results = scout.cross_search(QueryVariant("thermal"))

    with pytest.raises(ValueError, match="SKEPTIC_REJECTED"):
        scout.validate_downstream_handoff(
            results,
            skeptic=_skeptic_payload(verdict="rejected"),
            verdict="UNRESOLVED",
        )


def test_cross_domain_scout_handoff_rejects_forbidden_verdict() -> None:
    scout = CrossDomainScout([
        _StubSource("science", "science"),
        _StubSource("code", "code"),
    ])
    results = scout.cross_search(QueryVariant("thermal"))

    with pytest.raises(ValueError, match="VERDICT_REJECTED"):
        scout.validate_downstream_handoff(
            results,
            skeptic=_skeptic_payload(),
            verdict="PROVEN_NEW",
        )
