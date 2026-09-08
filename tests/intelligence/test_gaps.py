"""Focused tests for deterministic research-gap extraction."""
from __future__ import annotations

from criba.intelligence.contracts import EvidenceDocument, EvidenceFragment
from criba.intelligence.gaps import ResearchGapExtractor, extract_research_gaps


def _documents() -> list[EvidenceDocument]:
    return [
        EvidenceDocument(
            doc_id="doc-a",
            title="A study",
            fragments=[
                EvidenceFragment(
                    fragment_id="frag-a1",
                    text="The method works well. Further research is needed to test it in noisy settings.",
                ),
                EvidenceFragment(
                    fragment_id="frag-a2",
                    text="Further research is needed to test it in noisy settings.",
                ),
            ],
        ),
        EvidenceDocument(
            doc_id="doc-b",
            title="A second study",
            fragments=[
                EvidenceFragment(
                    fragment_id="frag-b1",
                    text="The research gap remains unclear for multilingual data.",
                )
            ],
        ),
    ]


def test_extracts_only_cued_sentences_with_provenance() -> None:
    gaps = extract_research_gaps(_documents())
    assert len(gaps) == 2
    assert [gap.evidence_doc_ids for gap in gaps] == [("doc-a",), ("doc-b",)]
    assert gaps[0].kind == "research"
    assert "Further research" in gaps[0].statement
    assert gaps[0].epistemic_state.value == "HYPOTHESIS"


def test_extraction_is_deterministic_and_deduplicates_same_document() -> None:
    extractor = ResearchGapExtractor()
    first = [gap.to_dict() for gap in extractor.extract(_documents())]
    second = [gap.to_dict() for gap in extractor.extract(reversed(_documents()))]
    # IDs are intentionally opaque, so compare semantic payloads.
    for payload in (first, second):
        for item in payload:
            item.pop("gap_id")
    assert first == second


def test_topic_filter_is_case_insensitive_and_empty_input_is_safe() -> None:
    gaps = extract_research_gaps(_documents(), topic="MULTILINGUAL")
    assert len(gaps) == 1
    assert gaps[0].evidence_doc_ids == ("doc-b",)
    assert extract_research_gaps([]) == []


def test_non_gap_language_is_not_promoted_to_gap() -> None:
    document = EvidenceDocument(
        doc_id="doc-c",
        fragments=[EvidenceFragment(text="This work addresses the open question directly.")],
    )
    assert extract_research_gaps([document]) == []
