"""P10-T10: mutation/re-search loop contract over PriorArtAssessment."""
from __future__ import annotations

from typing import Any

import pytest

from criba.intelligence.contracts import (
    EvidenceDocument,
    InventionCandidate,
    PriorArtMatch,
    SourceQueryResult,
)
from criba.intelligence.enums import PriorArtVerdict
from criba.intelligence.prior_art import (
    AdversarialSearchProtocol,
    CrossDomainScout,
    PriorArtSkeptic,
    PriorArtVerdictEngine,
    run_prior_art_mutation_loop,
)
from criba.intelligence.sources.protocol import IntelligenceSource, SourceContext
from criba.intelligence.sources.transport import Response, Transport, TransportBudget


class _DummyTransport(Transport):
    def __init__(self) -> None:
        super().__init__(sender=self._send, budget=TransportBudget(max_requests=100))

    def _send(self, url: str, params: dict[str, Any] | None = None,
              timeout: float = 20.0, headers: dict[str, Any] | None = None) -> Response:
        return Response(status=200, text="{}", headers={})


class _DummySource(IntelligenceSource):
    SOURCE_ID = "dummy"
    NAME = "Dummy Source"
    KIND = "test"

    def __init__(self, context: SourceContext):
        super().__init__(context)

    def _search(self, query: str, limit: int = 10, **params: Any) -> SourceQueryResult:
        return SourceQueryResult(
            source_id=self.SOURCE_ID,
            query_text=query,
            ok=True,
            documents=[],
        )


class _SecondDummySource(IntelligenceSource):
    SOURCE_ID = "dummy2"
    NAME = "Second Dummy Source"
    KIND = "science"

    def __init__(self, context: SourceContext):
        super().__init__(context)

    def _search(self, query: str, limit: int = 10, **params: Any) -> SourceQueryResult:
        return SourceQueryResult(
            source_id=self.SOURCE_ID,
            query_text=query,
            ok=True,
            documents=[],
        )


class _CrossDomainScoutForLoop(CrossDomainScout):
    def __init__(self) -> None:
        transport = _DummyTransport()
        context = SourceContext(transport=transport)
        source1 = _DummySource(context)
        source2 = _SecondDummySource(context)
        super().__init__([source1, source2], budget=transport.budget)


class _CandidateFactory:
    @staticmethod
    def candidate() -> InventionCandidate:
        return InventionCandidate(
            candidate_id="cand_t10_001",
            title="Thermal management via phase change",
            description="A cooling system using phase change material",
            mechanism="Phase change material absorbs heat during melting",
            operators=("T063",),
        )


def _results_with_docs() -> dict[str, SourceQueryResult]:
    """Results where ALL sources have at least one document with provenance."""
    return {
        "dummy": SourceQueryResult(
            source_id="dummy",
            query_text="thermal management",
            ok=True,
            documents=[
                EvidenceDocument(
                    doc_id="doc_1",
                    source_id="dummy",
                    title="Phase change cooling",
                    provenance={"url": "https://example.com/patent/1"},
                )
            ],
        ),
        "dummy2": SourceQueryResult(
            source_id="dummy2",
            query_text="thermal management",
            ok=True,
            documents=[
                EvidenceDocument(
                    doc_id="doc_2",
                    source_id="dummy2",
                    title="Thermal management survey",
                    provenance={"url": "https://example.com/paper/1"},
                )
            ],
        ),
    }


def _empty_results() -> dict[str, SourceQueryResult]:
    return {
        "dummy": SourceQueryResult(
            source_id="dummy",
            query_text="thermal management",
            ok=True,
            documents=[],
        ),
        "dummy2": SourceQueryResult(
            source_id="dummy2",
            query_text="thermal management",
            ok=True,
            documents=[],
        ),
    }


def test_mutation_loop_fails_closed_when_assessment_is_unresolved() -> None:
    """A mutation loop must not start from an UNRESOLVED assessment."""
    candidate = _CandidateFactory.candidate()
    scout = _CrossDomainScoutForLoop()
    results = _empty_results()
    skeptic = PriorArtSkeptic().review(candidate, results)
    assessment = PriorArtVerdictEngine().assess(candidate, results, skeptic, matches=[])

    assert assessment.verdict == PriorArtVerdict.UNRESOLVED.value

    protocol = AdversarialSearchProtocol(
        candidate_id=candidate.candidate_id,
        max_prior_art_rounds=2,
        max_mutations_per_candidate=1,
    )

    # The loop should reject an UNRESOLVED input
    with pytest.raises(ValueError, match="UNRESOLVED"):
        run_prior_art_mutation_loop(
            candidate=candidate,
            initial_assessment=assessment,
            protocol=protocol,
            scout=scout,
        )


def test_mutation_loop_accepts_partial_prior_art_and_schedules_mutation() -> None:
    """A PARTIAL_PRIOR_ART assessment should allow a bounded mutation round."""
    candidate = _CandidateFactory.candidate()
    scout = _CrossDomainScoutForLoop()
    results = _results_with_docs()
    skeptic = PriorArtSkeptic().review(candidate, results)
    # Create a match to trigger PARTIAL_PRIOR_ART
    match = PriorArtMatch(
        doc=results["dummy"].documents[0],
        similarity=0.7,
        match_kind="literal",
        overlapping_terms=("thermal", "management"),
        scout="PatentScout",
    )
    assessment = PriorArtVerdictEngine().assess(candidate, results, skeptic, matches=[match])

    assert assessment.verdict == PriorArtVerdict.PARTIAL_PRIOR_ART.value

    protocol = AdversarialSearchProtocol(
        candidate_id=candidate.candidate_id,
        max_prior_art_rounds=2,
        max_mutations_per_candidate=1,
    )

    final = run_prior_art_mutation_loop(
        candidate=candidate,
        initial_assessment=assessment,
        protocol=protocol,
        scout=scout,
    )

    assert final.verdict in (
        PriorArtVerdict.UNRESOLVED.value,
        PriorArtVerdict.PARTIAL_PRIOR_ART.value,
        PriorArtVerdict.SURVIVED_SEARCH.value,
    )
    assert "PROVEN_NEW" not in final.verdict


def test_mutation_loop_accepts_survived_search_and_may_mutate() -> None:
    """A SURVIVED_SEARCH assessment should allow mutation within budget."""
    candidate = _CandidateFactory.candidate()
    scout = _CrossDomainScoutForLoop()
    results = _results_with_docs()
    skeptic = PriorArtSkeptic().review(candidate, results)
    # No matches → SURVIVED_SEARCH
    assessment = PriorArtVerdictEngine().assess(candidate, results, skeptic, matches=[])

    assert assessment.verdict == PriorArtVerdict.SURVIVED_SEARCH.value

    protocol = AdversarialSearchProtocol(
        candidate_id=candidate.candidate_id,
        max_prior_art_rounds=2,
        max_mutations_per_candidate=1,
    )

    final = run_prior_art_mutation_loop(
        candidate=candidate,
        initial_assessment=assessment,
        protocol=protocol,
        scout=scout,
    )

    assert final.verdict in (
        PriorArtVerdict.UNRESOLVED.value,
        PriorArtVerdict.PARTIAL_PRIOR_ART.value,
        PriorArtVerdict.SURVIVED_SEARCH.value,
    )
    assert "PROVEN_NEW" not in final.verdict


def test_mutation_loop_respects_max_rounds() -> None:
    """The loop must not exceed max_prior_art_rounds."""
    protocol = AdversarialSearchProtocol(
        candidate_id="cand_test",
        max_prior_art_rounds=1,
        max_mutations_per_candidate=0,
    )

    assert protocol.can_execute(rounds_completed=0, mutations_completed=0)
    assert not protocol.can_execute(rounds_completed=1, mutations_completed=0)

    candidate = _CandidateFactory.candidate()
    scout = _CrossDomainScoutForLoop()
    results = _results_with_docs()
    skeptic = PriorArtSkeptic().review(candidate, results)
    assessment = PriorArtVerdictEngine().assess(candidate, results, skeptic, matches=[])

    final = run_prior_art_mutation_loop(
        candidate=candidate,
        initial_assessment=assessment,
        protocol=protocol,
        scout=scout,
    )

    # With max_rounds=1, only one execution allowed
    assert final.rounds_completed <= 1


def test_mutation_loop_respects_mutation_budget() -> None:
    """The loop must not exceed max_mutations_per_candidate."""
    protocol = AdversarialSearchProtocol(
        candidate_id="cand_test",
        max_prior_art_rounds=3,
        max_mutations_per_candidate=1,
    )

    assert protocol.can_mutate(mutations_completed=0)
    assert not protocol.can_mutate(mutations_completed=1)

    candidate = _CandidateFactory.candidate()
    scout = _CrossDomainScoutForLoop()
    results = _results_with_docs()
    skeptic = PriorArtSkeptic().review(candidate, results)
    assessment = PriorArtVerdictEngine().assess(candidate, results, skeptic, matches=[])

    final = run_prior_art_mutation_loop(
        candidate=candidate,
        initial_assessment=assessment,
        protocol=protocol,
        scout=scout,
    )

    assert final.mutations_completed <= 1


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
