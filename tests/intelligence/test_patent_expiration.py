"""Focused tests for patent-expiration opportunity contracts (P08-T07)."""
from __future__ import annotations

from criba.intelligence.contracts import EvidenceDocument, EvidenceFragment, PatentExpirationOpportunity
from criba.intelligence.gaps import (
    PatentExpirationAnalyzer,
    analyze_patent_expirations,
    extract_patent_expiration_opportunities,
)


def test_patent_expiration_opportunity_is_json_safe() -> None:
    opportunity = PatentExpirationOpportunity(
        patent_id="US-123",
        title="Thermal storage",
        expiration_date="2030-05-01",
        jurisdiction="US",
        claim_scope="phase-change storage",
        expiration_status="EXPIRING",
        opportunity_statement="Potential opportunity; legal status requires verification.",
        evidence_doc_ids=("patent-record-1",),
        confidence=0.8,
    )
    payload = opportunity.to_dict()
    assert payload["patent_id"] == "US-123"
    assert payload["expiration_date"] == "2030-05-01"
    assert payload["expiration_status"] == "EXPIRING"
    assert payload["evidence_doc_ids"] == ["patent-record-1"]
    assert payload["confidence"] == 0.8


def test_analyzes_structured_opportunity_without_declaring_freedom_to_operate() -> None:
    document = EvidenceDocument(
        doc_id="doc-structured",
        kind="patent",
        metadata={
            "patent_id": "EP-456",
            "title": "Quiet cooling",
            "expiration_date": "2029",
            "jurisdiction": "EP",
            "claim_scope": "low-noise thermal control",
            "expiration_status": "EXPIRING",
        },
    )
    opportunities = analyze_patent_expirations([document])
    assert len(opportunities) == 1
    assert opportunities[0].patent_id == "EP-456"
    assert "legal" in opportunities[0].opportunity_statement.casefold()
    assert "freedom to operate" not in opportunities[0].opportunity_statement.casefold()


def test_extracts_expiration_date_and_claim_scope_from_text() -> None:
    document = EvidenceDocument(
        doc_id="doc-text",
        kind="patent",
        fragments=[
            EvidenceFragment(
                text=(
                    "Patent US789 expires on 2031-06-30 in the US; claims cover "
                    "immersion cooling for data centers."
                )
            )
        ],
    )
    opportunities = extract_patent_expiration_opportunities([document])
    assert len(opportunities) == 1
    item = opportunities[0]
    assert item.patent_id == "US789"
    assert item.expiration_date == "2031-06-30"
    assert item.jurisdiction == "US"
    assert item.claim_scope == "immersion cooling for data centers"


def test_missing_expiration_evidence_is_not_promoted() -> None:
    documents = [
        EvidenceDocument(
            doc_id="doc-missing-date",
            kind="patent",
            metadata={"patent_id": "US000", "jurisdiction": "US"},
        ),
        EvidenceDocument(
            doc_id="doc-no-date",
            kind="patent",
            fragments=[EvidenceFragment(text="Patent US001 may create an opportunity someday.")],
        ),
    ]
    analyzer = PatentExpirationAnalyzer()
    assert analyzer.analyze(documents) == []
    assert analyze_patent_expirations([], jurisdiction="US") == []
