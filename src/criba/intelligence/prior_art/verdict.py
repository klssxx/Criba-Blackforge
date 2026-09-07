"""P10-T09: deterministic prior-art verdicts from bounded evidence."""
from __future__ import annotations

from collections.abc import Mapping, Sequence

from ..contracts import (
    InventionCandidate,
    PriorArtAssessment,
    PriorArtMatch,
    SourceQueryResult,
)
from ..enums import PriorArtVerdict
from .skeptic import PriorArtSkepticReport


class PriorArtVerdictEngine:
    """Classify bounded evidence without inferring novelty from its absence."""

    def assess(
        self,
        candidate: InventionCandidate,
        results: Mapping[str, SourceQueryResult],
        skeptic: PriorArtSkepticReport,
        *,
        matches: Sequence[PriorArtMatch],
    ) -> PriorArtAssessment:
        """Return a conservative, deterministic prior-art assessment."""
        if not isinstance(candidate, InventionCandidate):
            raise TypeError("candidate must be an InventionCandidate")
        if not isinstance(results, Mapping) or not results:
            raise ValueError("results must be a non-empty mapping")
        if not isinstance(skeptic, PriorArtSkepticReport):
            raise TypeError("skeptic must be a PriorArtSkepticReport")
        if skeptic.candidate_id != candidate.candidate_id:
            raise ValueError("skeptic candidate_id must match candidate")
        ordered_results = tuple(sorted(results.items(), key=lambda item: item[0]))
        for source_id, result in ordered_results:
            if not isinstance(source_id, str) or not isinstance(result, SourceQueryResult):
                raise TypeError("results must map source IDs to SourceQueryResult instances")
            if result.source_id != source_id:
                raise ValueError("result source_id must match its mapping key")

        structural_gaps = [
            f"source_failure:{source_id}"
            for source_id, result in ordered_results
            if not result.ok
        ]
        structural_gaps.extend(
            f"empty_source:{source_id}"
            for source_id, result in ordered_results
            if result.ok and not result.documents
        )
        structural_gaps.extend(
            f"missing_provenance:{source_id}:{document.doc_id}"
            for source_id, result in ordered_results
            for document in result.documents
            if result.ok and document.provenance is None
        )
        coverage_limitations = tuple(
            sorted({*skeptic.evidence_gaps, *structural_gaps})
        )
        if any(not isinstance(match, PriorArtMatch) for match in matches):
            raise TypeError("matches must contain PriorArtMatch instances")
        ordered_matches = sorted(
            matches,
            key=lambda match: (
                match.doc.source_id,
                match.doc.doc_id,
                match.match_kind,
                match.similarity,
            ),
        )
        if coverage_limitations:
            verdict = PriorArtVerdict.UNRESOLVED.value
        elif ordered_matches:
            verdict = PriorArtVerdict.PARTIAL_PRIOR_ART.value
        else:
            verdict = PriorArtVerdict.SURVIVED_SEARCH.value

        queries_executed = tuple(
            dict.fromkeys(result.query_text for _, result in ordered_results)
        )
        return PriorArtAssessment(
            candidate_id=candidate.candidate_id,
            verdict=verdict,
            matches=list(ordered_matches),
            coverage_limitations=coverage_limitations,
            queries_executed=queries_executed,
        )
