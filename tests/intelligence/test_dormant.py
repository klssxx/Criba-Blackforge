"""Focused tests for dormant-paper detection (P08-T08)."""
from __future__ import annotations

from criba.intelligence.contracts import EvidenceDocument, EvidenceFragment, DormantPaperCandidate
from criba.intelligence.gaps import (
    DormantPaperAnalyzer,
    detect_dormant_papers,
    extract_dormant_papers,
)


def test_dormant_paper_contract_is_json_safe() -> None:
    candidate = DormantPaperCandidate(
        paper_id="paper-1",
        title="Old thermal method",
        published="2001",
        dormant_since="2014",
        citation_count=12,
        recent_citations=0,
        recent_attention=0,
        dormancy_reason="No citations or attention in the recent window.",
        evidence_doc_ids=("paper-1",),
        confidence=0.9,
    )
    payload = candidate.to_dict()
    assert payload["paper_id"] == "paper-1"
    assert payload["recent_citations"] == 0
    assert payload["evidence_doc_ids"] == ["paper-1"]
    assert payload["confidence"] == 0.9


def test_detects_old_paper_with_explicit_low_attention_evidence() -> None:
    document = EvidenceDocument(
        doc_id="paper-old",
        kind="paper",
        title="Old thermal method",
        published="2001",
        metadata={
            "citation_count": 12,
            "recent_citations": 0,
            "recent_attention": 0,
            "last_cited": "2014",
        },
    )
    candidates = detect_dormant_papers([document], as_of="2026-01-01")
    assert len(candidates) == 1
    item = candidates[0]
    assert item.paper_id == "paper-old"
    assert item.dormant_since == "2014"
    assert item.citation_count == 12
    assert "recent" in item.dormancy_reason.casefold()


def test_extracts_text_signal_and_excludes_unproven_old_paper() -> None:
    documents = [
        EvidenceDocument(
            doc_id="paper-text",
            kind="paper",
            title="Forgotten method",
            fragments=[
                EvidenceFragment(
                    text="A 1995 paper has been rarely cited and received no attention since 2010."
                )
            ],
        ),
        EvidenceDocument(
            doc_id="paper-unknown",
            kind="paper",
            title="Old but unmeasured",
            published="1990",
            fragments=[EvidenceFragment(text="This paper introduced a thermal method.")],
        ),
    ]
    candidates = extract_dormant_papers(documents, as_of="2026-01-01")
    assert len(candidates) == 1
    assert candidates[0].paper_id == "paper-text"
    assert candidates[0].dormant_since == "2010"


def test_age_filter_and_order_are_deterministic() -> None:
    documents = [
        EvidenceDocument(
            doc_id="paper-new",
            kind="paper",
            published="2024",
            metadata={"recent_citations": 0, "recent_attention": 0},
        ),
        EvidenceDocument(
            doc_id="paper-old-b",
            kind="paper",
            published="2000",
            metadata={"recent_citations": 0, "recent_attention": 0},
        ),
        EvidenceDocument(
            doc_id="paper-old-a",
            kind="paper",
            published="1999",
            metadata={"recent_citations": 0, "recent_attention": 0},
        ),
    ]
    analyzer = DormantPaperAnalyzer()
    first = analyzer.analyze(documents, as_of="2026-01-01")
    second = analyzer.analyze(reversed(documents), as_of="2026-01-01")
    assert [item.paper_id for item in first] == ["paper-old-a", "paper-old-b"]
    assert [item.paper_id for item in second] == ["paper-old-a", "paper-old-b"]
    assert extract_dormant_papers([], as_of="2026-01-01") == []
