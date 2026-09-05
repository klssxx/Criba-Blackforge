"""P10-T09: deterministic prior-art verdict engine contract."""
from __future__ import annotations

import pytest

from criba.intelligence import prior_art
from criba.intelligence.contracts import (
    EvidenceDocument,
    InventionCandidate,
    PriorArtAssessment,
    PriorArtMatch,
    ProvenanceRecord,
    QueryVariant,
    SourceQueryResult,
)
from criba.intelligence.enums import PriorArtVerdict
from criba.intelligence.prior_art import (
    CrossDomainScout,
    PriorArtSkeptic,
    PriorArtVerdictEngine,
)
from criba.intelligence.sources.protocol import IntelligenceSource, SourceContext
from criba.intelligence.sources.transport import Response, Transport


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
        return SourceQueryResult(
            source_id=self.SOURCE_ID,
            query_text=query,
            ok=True,
            documents=[
                EvidenceDocument(
                    doc_id=f"doc_{self.SOURCE_ID}",
                    source_id=self.SOURCE_ID,
                    title=f"{self.SOURCE_ID} evidence",
                    provenance=ProvenanceRecord(
                        source_id=self.SOURCE_ID,
                        url=f"https://{self.SOURCE_ID}.invalid/evidence",
                        method="api",
                    ),
                )
            ],
        )


def _candidate() -> InventionCandidate:
    return InventionCandidate(
        candidate_id="cand_thermal",
        title="Thermal management transfer",
        description="Apply a documented heat-transfer mechanism in a new context.",
        mechanism="transfer a verified heat-transfer mechanism",
    )


def test_verdict_engine_runs_the_real_t07_t08_handoff_without_claiming_novelty() -> None:
    scout = CrossDomainScout([
        _Source("science", "science"),
        _Source("code", "code"),
    ])
    candidate = _candidate()
    results = scout.cross_search(QueryVariant("thermal management"))
    skeptic = PriorArtSkeptic().review(candidate, results)

    assessment = PriorArtVerdictEngine().assess(candidate, results, skeptic, matches=[])

    assert isinstance(assessment, PriorArtAssessment)
    assert assessment.candidate_id == candidate.candidate_id
    assert assessment.verdict == PriorArtVerdict.SURVIVED_SEARCH.value
    assert assessment.matches == []
    assert assessment.coverage_limitations == ()
    assert assessment.queries_executed == ("thermal management",)
    scout.validate_downstream_handoff(
        results,
        skeptic=skeptic,
        verdict=assessment.verdict,
    )


def test_verdict_engine_fails_closed_when_the_skeptic_report_hides_empty_source_coverage() -> None:
    scout = CrossDomainScout([
        _Source("science", "science"),
        _Source("code", "code"),
    ])
    candidate = _candidate()
    results = scout.cross_search(QueryVariant("thermal management"))
    results["science"] = SourceQueryResult(
        source_id="science",
        query_text="thermal management",
        ok=True,
        documents=[],
    )
    observed = PriorArtSkeptic().review(candidate, results)
    hidden_gap_report = type(observed)(
        **{**observed.to_dict(), "evidence_gaps": (), "verdict": "survives_with_conditions"}
    )

    assessment = PriorArtVerdictEngine().assess(
        candidate,
        results,
        hidden_gap_report,
        matches=[],
    )

    assert assessment.verdict == PriorArtVerdict.UNRESOLVED.value
    assert assessment.coverage_limitations == ("empty_source:science",)


def test_verdict_engine_returns_partial_prior_art_for_a_normalized_match() -> None:
    scout = CrossDomainScout([
        _Source("science", "science"),
        _Source("code", "code"),
    ])
    candidate = _candidate()
    results = scout.cross_search(QueryVariant("thermal management"))
    skeptic = PriorArtSkeptic().review(candidate, results)
    match = PriorArtMatch(
        doc=results["science"].documents[0],
        similarity=0.01,
        match_kind="literal",
        scout="ScienceScout",
    )

    assessment = PriorArtVerdictEngine().assess(
        candidate,
        results,
        skeptic,
        matches=[match],
    )

    assert assessment.verdict == PriorArtVerdict.PARTIAL_PRIOR_ART.value
    assert assessment.matches == [match]


def test_verdict_engine_orders_matches_deterministically() -> None:
    scout = CrossDomainScout([
        _Source("science", "science"),
        _Source("code", "code"),
    ])
    candidate = _candidate()
    results = scout.cross_search(QueryVariant("thermal management"))
    skeptic = PriorArtSkeptic().review(candidate, results)
    science_match = PriorArtMatch(doc=results["science"].documents[0], scout="ScienceScout")
    code_match = PriorArtMatch(doc=results["code"].documents[0], scout="CodeScout")

    forward = PriorArtVerdictEngine().assess(
        candidate,
        results,
        skeptic,
        matches=[science_match, code_match],
    )
    reverse = PriorArtVerdictEngine().assess(
        candidate,
        results,
        skeptic,
        matches=[code_match, science_match],
    )

    assert [match.doc.doc_id for match in forward.matches] == ["doc_code", "doc_science"]
    assert forward.matches == reverse.matches


def test_verdict_engine_rejects_a_malformed_match() -> None:
    scout = CrossDomainScout([
        _Source("science", "science"),
        _Source("code", "code"),
    ])
    candidate = _candidate()
    results = scout.cross_search(QueryVariant("thermal management"))
    skeptic = PriorArtSkeptic().review(candidate, results)

    with pytest.raises(TypeError, match="PriorArtMatch"):
        PriorArtVerdictEngine().assess(candidate, results, skeptic, matches=[object()])


def test_verdict_engine_is_part_of_the_public_prior_art_contract() -> None:
    assert prior_art.PriorArtVerdictEngine is PriorArtVerdictEngine
    assert "PriorArtVerdictEngine" in prior_art.__all__


def test_verdict_engine_does_not_let_a_match_override_a_coverage_gap() -> None:
    scout = CrossDomainScout([
        _Source("science", "science"),
        _Source("code", "code"),
    ])
    candidate = _candidate()
    results = scout.cross_search(QueryVariant("thermal management"))
    results["science"] = SourceQueryResult(
        source_id="science",
        query_text="thermal management",
        ok=True,
        documents=[],
    )
    skeptic = PriorArtSkeptic().review(candidate, results)
    match = PriorArtMatch(doc=results["code"].documents[0], scout="CodeScout")

    assessment = PriorArtVerdictEngine().assess(
        candidate,
        results,
        skeptic,
        matches=[match],
    )

    assert assessment.verdict == PriorArtVerdict.UNRESOLVED.value
    assert assessment.coverage_limitations == ("empty_source:science",)


def test_verdict_engine_fails_closed_when_the_skeptic_report_hides_missing_provenance() -> None:
    scout = CrossDomainScout([
        _Source("science", "science"),
        _Source("code", "code"),
    ])
    candidate = _candidate()
    results = scout.cross_search(QueryVariant("thermal management"))
    results["science"] = SourceQueryResult(
        source_id="science",
        query_text="thermal management",
        ok=True,
        documents=[
            EvidenceDocument(
                doc_id="doc_science",
                source_id="science",
                title="Evidence without provenance",
            )
        ],
    )
    observed = PriorArtSkeptic().review(candidate, results)
    hidden_gap_report = type(observed)(
        **{**observed.to_dict(), "evidence_gaps": (), "verdict": "survives_with_conditions"}
    )

    assessment = PriorArtVerdictEngine().assess(
        candidate,
        results,
        hidden_gap_report,
        matches=[],
    )

    assert assessment.verdict == PriorArtVerdict.UNRESOLVED.value
    assert assessment.coverage_limitations == ("missing_provenance:science:doc_science",)
