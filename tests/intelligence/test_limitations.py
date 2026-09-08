"""Focused tests for deterministic limitation extraction."""
from __future__ import annotations

from criba.intelligence.contracts import EvidenceDocument, EvidenceFragment
from criba.intelligence.gaps import LimitationExtractor, extract_limitations


def _documents() -> list[EvidenceDocument]:
    return [
        EvidenceDocument(
            doc_id="doc-a",
            kind="paper",
            fragments=[
                EvidenceFragment(
                    text="A limitation of this study is the small sample size. The method is useful."
                ),
                EvidenceFragment(
                    text="A limitation of this study is the small sample size."
                ),
            ],
        ),
        EvidenceDocument(
            doc_id="doc-b",
            kind="dataset",
            fragments=[EvidenceFragment(text="Coverage is limited by missing validation data.")],
        ),
    ]


def test_extracts_limitations_with_stable_provenance_and_scope() -> None:
    limitations = extract_limitations(_documents())
    assert len(limitations) == 2
    assert [item.evidence_doc_ids for item in limitations] == [("doc-a",), ("doc-b",)]
    assert limitations[0].kind == "limitation"
    assert limitations[0].scope == "paper"


def test_extraction_is_deterministic_and_deduplicated() -> None:
    extractor = LimitationExtractor()
    first = extractor.extract(_documents())
    second = extractor.extract(reversed(_documents()))
    assert [(x.statement, x.evidence_doc_ids) for x in first] == [
        (x.statement, x.evidence_doc_ids) for x in second
    ]


def test_scope_filter_is_case_insensitive() -> None:
    limitations = extract_limitations(_documents(), scope="MISSING VALIDATION")
    assert len(limitations) == 1
    assert limitations[0].evidence_doc_ids == ("doc-b",)


def test_resolved_limitation_language_is_not_promoted() -> None:
    document = EvidenceDocument(
        doc_id="doc-c",
        fragments=[EvidenceFragment(text="The method addresses the limitation directly.")],
    )
    assert extract_limitations([document]) == []
