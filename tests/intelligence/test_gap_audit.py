"""Regression checks found by the P08 gap-engine audit."""
from __future__ import annotations

from criba.intelligence.contracts import EvidenceDocument, EvidenceFragment
from criba.intelligence.gaps import (
    analyze_white_spaces,
    detect_sleeping_beauties,
    extract_limitations,
    extract_research_gaps,
)


def _document(text: str, *, metadata: dict | None = None) -> EvidenceDocument:
    return EvidenceDocument(
        doc_id="audit-doc",
        kind="paper",
        title="Audit fixture",
        published="2024",
        metadata=metadata or {},
        fragments=(EvidenceFragment(fragment_id="audit-fragment", text=text),),
    )


def test_negated_resolution_is_still_evidence_of_a_gap_or_limitation() -> None:
    text = "No study addresses the research gap in photonics."
    assert len(extract_research_gaps([_document(text)])) == 1

    limitation_text = "No study addresses the limitation in photonics."
    assert len(extract_limitations([_document(limitation_text)])) == 1


def test_generic_few_is_not_a_white_space_signal() -> None:
    assert analyze_white_spaces([_document("Few issues remain in the deployment checklist.")]) == []


def test_numeric_boolean_metadata_flag_is_honored() -> None:
    document = _document(
        "",
        metadata={
            "white_space": 1,
            "statement": "Combination is explicitly marked as an uncovered space.",
            "space_type": "research",
        },
    )
    candidates = analyze_white_spaces([document])
    assert len(candidates) == 1
    assert candidates[0].space_type == "research"


def test_resolved_white_space_is_still_excluded() -> None:
    text = "The product closes the underserved market gap."
    assert analyze_white_spaces([_document(text)]) == []


def test_resolution_mention_is_not_misread_as_negated_when_conjoined() -> None:
    for conjunction in ("and", "but", "yet", "however"):
        text = f"The study reports no prior work {conjunction} addresses the research gap."
        assert extract_research_gaps([_document(text)]) == []


def test_unknown_metadata_space_type_falls_back_to_a_supported_type() -> None:
    document = _document(
        "",
        metadata={
            "white_space": True,
            "statement": "Explicitly marked uncovered combination.",
            "space_type": "unknown-type",
        },
    )
    candidates = analyze_white_spaces([document])
    assert len(candidates) == 1
    assert candidates[0].space_type == "research"


def test_duplicate_citation_years_are_order_independent() -> None:
    metadata = {
        "published": "2000",
        "citation_counts_by_year": [
            {"year": 2000, "citations": 0},
            {"year": 2000, "citations": 2},
            {"year": 2001, "citations": 0},
            {"year": 2002, "citations": 0},
            {"year": 2003, "citations": 0},
            {"year": 2012, "citations": 12},
        ],
    }
    document = _document("", metadata=metadata)
    candidate = detect_sleeping_beauties([document])[0]
    reversed_document = _document(
        "",
        metadata={**metadata, "citation_counts_by_year": list(reversed(metadata["citation_counts_by_year"]))},
    )
    reversed_candidate = detect_sleeping_beauties([reversed_document])[0]
    assert candidate.early_citations == reversed_candidate.early_citations == 2
