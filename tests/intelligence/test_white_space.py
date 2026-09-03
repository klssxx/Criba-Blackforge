"""Focused tests for deterministic white-space analysis (P08-T06 / T086)."""
from __future__ import annotations

from criba.intelligence.contracts import EvidenceDocument, EvidenceFragment
from criba.intelligence.gaps import (
    WhiteSpaceAnalyzer,
    analyze_white_spaces,
    extract_white_spaces,
)


def _documents() -> list[EvidenceDocument]:
    return [
        EvidenceDocument(
            doc_id="doc-a",
            kind="paper",
            fragments=[
                EvidenceFragment(
                    text="Few studies investigate photonic cooling for edge devices."
                ),
                EvidenceFragment(
                    text="Few studies investigate photonic cooling for edge devices."
                ),
            ],
        ),
        EvidenceDocument(
            doc_id="doc-b",
            kind="patent",
            fragments=[EvidenceFragment(text="No patent covers low-cost thermal storage.")],
        ),
        EvidenceDocument(
            doc_id="doc-c",
            kind="product",
            fragments=[EvidenceFragment(text="The market remains underserved for quiet cooling.")],
        ),
    ]


def test_analyzes_white_spaces_with_type_and_provenance() -> None:
    spaces = analyze_white_spaces(_documents())
    assert len(spaces) == 3
    assert [item.evidence_doc_ids for item in spaces] == [
        ("doc-a",),
        ("doc-b",),
        ("doc-c",),
    ]
    assert [item.space_type for item in spaces] == ["research", "patent", "market"]
    assert all(item.kind == "white_space" for item in spaces)


def test_analysis_is_deterministic_deduplicated_and_topic_filtered() -> None:
    analyzer = WhiteSpaceAnalyzer()
    first = [item.to_dict() for item in analyzer.analyze(_documents())]
    second = [item.to_dict() for item in extract_white_spaces(reversed(_documents()))]
    for payload in (first, second):
        for item in payload:
            item.pop("gap_id")
    assert first == second
    filtered = analyzer.analyze(_documents(), topic="THERMAL STORAGE")
    assert len(filtered) == 1
    assert filtered[0].space_type == "patent"


def test_resolved_gap_language_is_not_promoted() -> None:
    document = EvidenceDocument(
        doc_id="doc-d",
        kind="product",
        fragments=[
            EvidenceFragment(text="The new product fills the market gap."),
            EvidenceFragment(text="This study addresses the research gap directly."),
        ],
    )
    assert analyze_white_spaces([document]) == []


def test_structured_metadata_and_empty_input_are_supported() -> None:
    document = EvidenceDocument(
        doc_id="doc-e",
        metadata={
            "white_space": True,
            "space_type": "market",
            "statement": "No product serves rural clinics.",
        },
    )
    spaces = analyze_white_spaces([document], space_type="MARKET")
    assert len(spaces) == 1
    assert spaces[0].statement == "No product serves rural clinics."
    assert spaces[0].evidence_doc_ids == ("doc-e",)
    assert extract_white_spaces([], topic="anything") == []
