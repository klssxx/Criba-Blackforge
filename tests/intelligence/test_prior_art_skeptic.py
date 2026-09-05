"""P10-T08: deterministic skeptic contract for prior-art evidence."""
from __future__ import annotations

import json
from collections.abc import Mapping

import pytest

from criba.intelligence.contracts import (
    EvidenceDocument,
    InventionCandidate,
    ProvenanceRecord,
    QueryVariant,
    SourceQueryResult,
)
from criba.intelligence.prior_art import CrossDomainScout, PriorArtSkeptic
from criba.intelligence.sources.protocol import IntelligenceSource, SourceContext
from criba.intelligence.sources.transport import Response, Transport


def _candidate() -> InventionCandidate:
    return InventionCandidate(
        candidate_id="cand_thermal",
        title="Thermal management transfer",
        description="Apply a documented heat-transfer mechanism in a new context.",
        mechanism="transfer a verified heat-transfer mechanism",
    )


def _result(
    source_id: str,
    *,
    ok: bool = True,
    documents: list[EvidenceDocument] | None = None,
    error: str = "",
) -> SourceQueryResult:
    if documents is None:
        documents = [
            EvidenceDocument(
                doc_id=f"doc_{source_id}",
                source_id=source_id,
                title=f"{source_id} evidence",
                provenance=ProvenanceRecord(
                    source_id=source_id,
                    url=f"https://{source_id}.invalid/evidence",
                    method="api",
                ),
            )
        ]
    return SourceQueryResult(
        source_id=source_id,
        query_text="thermal management",
        ok=ok,
        documents=documents,
        error=error,
    )


class _Source(IntelligenceSource):
    RATE_LIMIT_S = 0.0

    def __init__(self, source_id: str, kind: str) -> None:
        super().__init__(
            SourceContext(
                transport=Transport(sender=lambda *args, **kwargs: Response(200, "{}"))
            )
        )
        self.SOURCE_ID = source_id
        self.KIND = kind

    def _search(self, query: str, limit: int = 10, **params: object) -> SourceQueryResult:
        return _result(self.SOURCE_ID)


def test_skeptic_returns_deterministic_json_safe_non_verdict_report() -> None:
    skeptic = PriorArtSkeptic()
    report = skeptic.review(
        _candidate(),
        {"science": _result("science"), "code": _result("code")},
    )
    reversed_report = skeptic.review(
        _candidate(),
        {"code": _result("code"), "science": _result("science")},
    )

    assert isinstance(report, Mapping)
    assert report.to_dict() == reversed_report.to_dict()
    payload = report.to_dict()
    assert payload["candidate_id"] == "cand_thermal"
    assert payload["verdict"] == "survives_with_conditions"
    assert payload["evidence_gaps"] == []
    assert payload["falsification_tests"]
    assert "PROVEN_NEW" not in json.dumps(payload)
    assert json.loads(json.dumps(payload))["verdict"] == "survives_with_conditions"


def test_skeptic_exposes_coverage_gaps_without_leaking_source_error_text() -> None:
    skeptic = PriorArtSkeptic()
    report = skeptic.review(
        _candidate(),
        {
            "code": _result("code", ok=False, error="SECRET_TOKEN must not leak"),
            "science": _result("science", documents=[]),
        },
    )

    payload = report.to_dict()
    assert payload["verdict"] == "requires_experiment"
    assert payload["evidence_gaps"] == ["empty_source:science", "source_failure:code"]
    assert "SECRET_TOKEN" not in json.dumps(payload)


def test_skeptic_rejects_empty_or_mismatched_source_results() -> None:
    skeptic = PriorArtSkeptic()

    with pytest.raises(ValueError, match="results must not be empty"):
        skeptic.review(_candidate(), {})
    with pytest.raises(ValueError, match="source_id"):
        skeptic.review(_candidate(), {"science": _result("other")})


def test_skeptic_exposes_missing_document_provenance_as_a_coverage_gap() -> None:
    skeptic = PriorArtSkeptic()
    unprovenanced = EvidenceDocument(
        doc_id="doc_science",
        source_id="science",
        title="Unprovenanced source result",
    )

    report = skeptic.review(
        _candidate(),
        {
            "science": _result("science", documents=[unprovenanced]),
            "code": _result("code"),
        },
    )

    payload = report.to_dict()
    assert payload["verdict"] == "requires_experiment"
    assert payload["evidence_gaps"] == ["missing_provenance:science:doc_science"]


def test_skeptic_rejects_malformed_evidence_document() -> None:
    skeptic = PriorArtSkeptic()

    with pytest.raises(TypeError, match="EvidenceDocument"):
        skeptic.review(_candidate(), {"science": _result("science", documents=[object()])})


def test_t07_cross_domain_results_handoff_to_real_skeptic_contract() -> None:
    scout = CrossDomainScout([
        _Source("science", "science"),
        _Source("code", "code"),
    ])
    results = scout.cross_search(QueryVariant("thermal management"))
    report = PriorArtSkeptic().review(_candidate(), results)

    scout.validate_downstream_handoff(
        results,
        skeptic=report,
        verdict="UNRESOLVED",
    )
    assert report.to_dict()["evidence_gaps"] == []
