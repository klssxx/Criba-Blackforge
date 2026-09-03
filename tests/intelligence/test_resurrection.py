"""Focused tests for technology resurrection candidates (P08-T05 / T071)."""
from __future__ import annotations

from criba.intelligence.contracts import EvidenceDocument, EvidenceFragment, ResurrectionCandidate
from criba.intelligence.gaps import (
    ResurrectionCandidateExtractor,
    extract_resurrection_candidates,
    find_resurrection_candidates,
)


def test_resurrection_contract_preserves_blueprint_fields() -> None:
    candidate = ResurrectionCandidate(
        historical_idea="analog accelerator",
        historical_failure_reason="components were too expensive",
        blocking_constraint="fabrication cost",
        current_evidence="new fabrication evidence reduces cost",
        constraint_change="open-source fabrication is available",
        new_feasibility="low-cost prototypes are feasible",
        resurrection_confidence=0.8,
    )
    payload = candidate.to_dict()
    assert payload["kind"] == "resurrection"
    assert payload["historical_idea"] == "analog accelerator"
    assert payload["blocking_constraint"] == "fabrication cost"
    assert payload["resurrection_confidence"] == 0.8


def test_extracts_structured_resurrection_with_provenance() -> None:
    document = EvidenceDocument(
        doc_id="doc-a",
        published="1998",
        metadata={
            "historical_idea": "analog accelerator",
            "historical_failure_reason": "components were too expensive",
            "blocking_constraint": "fabrication cost",
            "current_evidence": "new fabrication evidence reduces cost",
            "constraint_change": "open-source fabrication is available",
            "new_feasibility": "low-cost prototypes are feasible",
            "resurrection_confidence": 0.8,
        },
    )
    candidates = extract_resurrection_candidates([document])
    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.evidence_doc_ids == ("doc-a",)
    assert candidate.dormant_since == "1998"
    assert candidate.unlock_enabler == "open-source fabrication is available"
    assert candidate.resurrection_confidence == 0.8


def test_text_extraction_requires_current_evidence_of_constraint_change() -> None:
    documents = [
        EvidenceDocument(
            doc_id="doc-b",
            published="2001",
            fragments=[
                EvidenceFragment(
                    text=(
                        "The optical sensor was abandoned because it was too expensive. "
                        "Recent manufacturing advances reduced the cost and make prototypes feasible."
                    )
                )
            ],
        ),
        EvidenceDocument(
            doc_id="doc-c",
            fragments=[
                EvidenceFragment(
                    text=(
                        "The thermal design was shelved because cooling was difficult. "
                        "It may be feasible now, but no current evidence shows the constraint changed."
                    )
                )
            ],
        ),
    ]
    candidates = find_resurrection_candidates(documents)
    assert len(candidates) == 1
    assert candidates[0].evidence_doc_ids == ("doc-b",)
    assert candidates[0].historical_idea == "The optical sensor"
    assert "Recent manufacturing advances" in candidates[0].current_evidence
    assert candidates[0].blocking_constraint == "it was too expensive"
    assert candidates[0].new_feasibility.endswith("prototypes feasible")


def test_extraction_is_deterministic_deduplicated_and_topic_filtered() -> None:
    document = EvidenceDocument(
        doc_id="doc-d",
        metadata={
            "historical_idea": "photonic memory",
            "historical_failure_reason": "materials degraded",
            "blocking_constraint": "material stability",
            "current_evidence": "new materials remain stable",
            "constraint_change": "new materials are available",
            "new_feasibility": "photonic memory is feasible",
        },
    )
    extractor = ResurrectionCandidateExtractor()
    first = [item.to_dict() for item in extractor.extract([document], topic="PHOTONIC")]
    second = [item.to_dict() for item in extractor.extract(reversed([document]), topic="photonic")]
    for payload in (first, second):
        for item in payload:
            item.pop("gap_id")
    assert first == second
    assert len(first) == 1
    assert extractor.extract([document], topic="unrelated") == []
