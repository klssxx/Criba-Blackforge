"""Focused tests for sleeping-beauty detection (P08-T09)."""
from __future__ import annotations

from criba.intelligence.contracts import EvidenceDocument, EvidenceFragment, SleepingBeautyCandidate
from criba.intelligence.gaps import (
    SleepingBeautyAnalyzer,
    detect_sleeping_beauties,
    extract_sleeping_beauties,
)


def test_sleeping_beauty_contract_is_json_safe() -> None:
    candidate = SleepingBeautyCandidate(
        paper_id="paper-1",
        title="Delayed discovery",
        published="1990",
        awakening_year=2018,
        beauty_period_years=25,
        early_citations=1,
        peak_citations=42,
        later_citations=42,
        awakening_evidence="Citation series rises sharply in 2018.",
        evidence_doc_ids=("paper-1",),
        confidence=0.95,
    )
    payload = candidate.to_dict()
    assert payload["awakening_year"] == 2018
    assert payload["beauty_period_years"] == 25
    assert payload["evidence_doc_ids"] == ["paper-1"]


def test_detects_delayed_attention_from_citation_series() -> None:
    document = EvidenceDocument(
        doc_id="paper-series",
        kind="paper",
        title="Delayed discovery",
        published="2000",
        metadata={
            "citation_counts_by_year": {
                "2000": 0,
                "2001": 0,
                "2002": 1,
                "2003": 0,
                "2012": 12,
                "2013": 18,
                "2014": 15,
            }
        },
    )
    candidates = detect_sleeping_beauties([document])
    assert len(candidates) == 1
    item = candidates[0]
    assert item.awakening_year == 2012
    assert item.beauty_period_years == 8
    assert item.early_citations == 1
    assert item.peak_citations == 18
    assert item.later_citations == 18


def test_extracts_explicit_sleeping_beauty_text_signal() -> None:
    document = EvidenceDocument(
        doc_id="paper-text",
        kind="paper",
        title="Rediscovered method",
        fragments=[
            EvidenceFragment(
                text="A 1995 paper became a sleeping beauty and was rediscovered in 2020."
            )
        ],
    )
    candidates = extract_sleeping_beauties([document])
    assert len(candidates) == 1
    assert candidates[0].paper_id == "paper-text"
    assert candidates[0].published == "1995"
    assert candidates[0].awakening_year == 2020
    assert candidates[0].early_citations is None


def test_flat_citation_series_is_not_promoted() -> None:
    document = EvidenceDocument(
        doc_id="paper-flat",
        kind="paper",
        published="2000",
        metadata={
            "citation_counts_by_year": {
                "2000": 0,
                "2001": 0,
                "2002": 1,
                "2012": 2,
                "2013": 2,
            }
        },
    )
    analyzer = SleepingBeautyAnalyzer()
    assert analyzer.analyze([document]) == []
    assert detect_sleeping_beauties([], min_later_citations=10) == []
