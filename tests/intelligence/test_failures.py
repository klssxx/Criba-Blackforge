"""Focused tests for deterministic failure mining (P08-T04 / T070)."""
from __future__ import annotations

from criba.intelligence.contracts import EvidenceDocument, EvidenceFragment
from criba.intelligence.gaps import FailureCaseExtractor, extract_failures, mine_failures


def _documents() -> list[EvidenceDocument]:
    return [
        EvidenceDocument(
            doc_id="doc-a",
            kind="paper",
            fragments=[
                EvidenceFragment(
                    text="The system fails under high load. The baseline is stable."
                ),
                EvidenceFragment(text="The system fails under high load."),
            ],
        ),
        EvidenceDocument(
            doc_id="doc-b",
            kind="report",
            fragments=[
                EvidenceFragment(text="A failure mode is data leakage when logs are shared."),
                EvidenceFragment(text="The method cannot handle missing values."),
            ],
        ),
    ]


def test_mines_failure_cases_with_mode_and_provenance() -> None:
    failures = extract_failures(_documents())
    assert len(failures) == 3
    assert [item.evidence_doc_ids for item in failures] == [
        ("doc-a",),
        ("doc-b",),
        ("doc-b",),
    ]
    assert failures[0].kind == "failure"
    assert failures[0].failure_mode == "under high load"
    assert failures[1].failure_mode == "data leakage when logs are shared"
    assert failures[2].failure_mode == "missing values"


def test_mining_is_deterministic_and_deduplicated() -> None:
    miner = FailureCaseExtractor()
    first = [item.to_dict() for item in miner.extract(_documents())]
    second = [item.to_dict() for item in mine_failures(reversed(_documents()))]
    for payload in (first, second):
        for item in payload:
            item.pop("gap_id")
    assert first == second


def test_resolved_failure_language_is_not_promoted() -> None:
    document = EvidenceDocument(
        doc_id="doc-c",
        fragments=[
            EvidenceFragment(text="The patch prevents failure under high load."),
            EvidenceFragment(text="The service tolerates failures during retries."),
        ],
    )
    failures = extract_failures([document])
    assert failures == []


def test_unstructured_failure_is_retained_without_inventing_a_mode() -> None:
    document = EvidenceDocument(
        doc_id="doc-d",
        fragments=[EvidenceFragment(text="The experiment reports an unresolved failure.")],
    )
    failures = extract_failures([document])
    assert len(failures) == 1
    assert failures[0].failure_mode == "unresolved failure"


def test_empty_input_and_case_insensitive_topic_filter_are_safe() -> None:
    failures = extract_failures(_documents(), topic="MISSING VALUES")
    assert len(failures) == 1
    assert failures[0].evidence_doc_ids == ("doc-b",)
    assert extract_failures([]) == []
