"""P10-T08: deterministic adversarial review of prior-art source evidence.

The skeptic assesses only evidence coverage and contract integrity.  It does not
compare mechanism semantics, compute similarity, or issue a PriorArtVerdict.
"""
from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass

from ..contracts import EvidenceDocument, InventionCandidate, SourceQueryResult


@dataclass(frozen=True)
class PriorArtSkepticReport(Mapping[str, object]):
    """JSON-safe adversarial report that is compatible with the T07 handoff."""

    candidate_id: str
    thesis_under_attack: str
    strongest_hidden_assumptions: tuple[str, ...]
    causal_challenges: tuple[str, ...]
    factual_challenges: tuple[str, ...]
    evidence_gaps: tuple[str, ...]
    alternative_explanations: tuple[str, ...]
    implementation_failures: tuple[str, ...]
    incentive_failures: tuple[str, ...]
    operational_failures: tuple[str, ...]
    simpler_alternatives: tuple[str, ...]
    worst_case: str
    falsification_tests: tuple[str, ...]
    kill_criteria: tuple[str, ...]
    survivable_parts: tuple[str, ...]
    verdict: str

    def to_dict(self) -> dict[str, object]:
        """Return the generic adversarial-pass schema without enum leakage."""
        return {
            "candidate_id": self.candidate_id,
            "thesis_under_attack": self.thesis_under_attack,
            "strongest_hidden_assumptions": list(self.strongest_hidden_assumptions),
            "causal_challenges": list(self.causal_challenges),
            "factual_challenges": list(self.factual_challenges),
            "evidence_gaps": list(self.evidence_gaps),
            "alternative_explanations": list(self.alternative_explanations),
            "implementation_failures": list(self.implementation_failures),
            "incentive_failures": list(self.incentive_failures),
            "operational_failures": list(self.operational_failures),
            "simpler_alternatives": list(self.simpler_alternatives),
            "worst_case": self.worst_case,
            "falsification_tests": list(self.falsification_tests),
            "kill_criteria": list(self.kill_criteria),
            "survivable_parts": list(self.survivable_parts),
            "verdict": self.verdict,
        }

    def __getitem__(self, key: str) -> object:
        return self.to_dict()[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self.to_dict())

    def __len__(self) -> int:
        return len(self.to_dict())


class PriorArtSkeptic:
    """Attack coverage assumptions before a later prior-art verdict stage."""

    def review(
        self,
        candidate: InventionCandidate,
        results: Mapping[str, SourceQueryResult],
    ) -> PriorArtSkepticReport:
        """Produce an evidence-only challenge report in stable source order."""
        thesis = self._validate_candidate(candidate)
        ordered_results = self._validate_results(results)

        evidence_gaps: list[str] = []
        factual_challenges: list[str] = []
        falsification_tests: list[str] = []
        for source_id, result in ordered_results:
            if not result.ok:
                evidence_gaps.append(f"source_failure:{source_id}")
                continue
            if not result.documents:
                evidence_gaps.append(f"empty_source:{source_id}")
                continue
            factual_challenges.append(
                f"{source_id} returned {len(result.documents)} normalized document(s)"
            )
            for document in sorted(result.documents, key=lambda item: item.doc_id):
                if document.provenance is None:
                    evidence_gaps.append(f"missing_provenance:{source_id}:{document.doc_id}")
                falsification_tests.append(
                    f"compare_candidate_mechanism:{source_id}:{document.doc_id}"
                )

        normalized_gaps = tuple(sorted(set(evidence_gaps)))
        has_gaps = bool(normalized_gaps)
        return PriorArtSkepticReport(
            candidate_id=candidate.candidate_id,
            thesis_under_attack=thesis,
            strongest_hidden_assumptions=(
                "normalized documents are materially relevant to the candidate mechanism",
                "completed source calls provide enough coverage for a later prior-art verdict",
            ),
            causal_challenges=(
                "lexical retrieval alone does not establish material mechanism overlap",
            ),
            factual_challenges=tuple(factual_challenges),
            evidence_gaps=normalized_gaps,
            alternative_explanations=(
                "shared terminology can describe different mechanisms",
            ),
            implementation_failures=tuple(
                gap for gap in normalized_gaps if gap.startswith("source_failure:")
            ),
            incentive_failures=(),
            operational_failures=(),
            simpler_alternatives=(
                "adopt documented prior art if a later comparison establishes material overlap",
            ),
            worst_case="existing prior art materially discloses the candidate mechanism",
            falsification_tests=tuple(falsification_tests) or (
                "collect normalized source evidence before comparison",
            ),
            kill_criteria=(
                "a later verdict establishes material mechanism overlap",
            ),
            survivable_parts=(
                "the candidate remains a hypothesis until the prior-art verdict stage",
            ),
            verdict="requires_experiment" if has_gaps else "survives_with_conditions",
        )

    @staticmethod
    def _validate_candidate(candidate: InventionCandidate) -> str:
        if not isinstance(candidate, InventionCandidate):
            raise TypeError("candidate must be an InventionCandidate")
        if (
            not isinstance(candidate.candidate_id, str)
            or not candidate.candidate_id
            or candidate.candidate_id != candidate.candidate_id.strip()
        ):
            raise ValueError("candidate_id must be a non-blank trimmed string")
        for value in (candidate.mechanism, candidate.description, candidate.title):
            if isinstance(value, str) and value.strip():
                return value
        raise ValueError("candidate must provide a non-blank thesis")

    @staticmethod
    def _validate_results(
        results: Mapping[str, SourceQueryResult],
    ) -> tuple[tuple[str, SourceQueryResult], ...]:
        if not isinstance(results, Mapping):
            raise TypeError("results must be a mapping")
        if not results:
            raise ValueError("results must not be empty")

        normalized: list[tuple[str, SourceQueryResult]] = []
        for source_id, result in results.items():
            if not isinstance(source_id, str) or not source_id or source_id != source_id.strip():
                raise ValueError("result source_id keys must be non-blank trimmed strings")
            if not isinstance(result, SourceQueryResult):
                raise TypeError("results values must be SourceQueryResult instances")
            if result.source_id != source_id:
                raise ValueError("result source_id must match its mapping key")
            if not isinstance(result.query_text, str) or not result.query_text.strip():
                raise ValueError("result query_text must be non-blank")
            if not isinstance(result.ok, bool):
                raise TypeError("result ok must be a bool")
            if not isinstance(result.documents, list):
                raise TypeError("result documents must be a list")
            if any(not isinstance(document, EvidenceDocument) for document in result.documents):
                raise TypeError("result documents must contain EvidenceDocument instances")
            normalized.append((source_id, result))
        return tuple(sorted(normalized, key=lambda item: item[0]))
