from criba.intelligence.contracts import Claim
from criba.intelligence.gaps import ContradictionAnalyzer, analyze_contradictions


def test_detects_opposing_claims_and_unites_document_provenance() -> None:
    claims = [
        Claim(text="Graph improves retrieval", evidence_doc_ids=("doc-a",)),
        Claim(text="Graph worsens retrieval", evidence_doc_ids=("doc-b",)),
    ]
    contradictions = analyze_contradictions(claims)
    assert len(contradictions) == 1
    assert contradictions[0].kind == "contradiction"
    assert contradictions[0].evidence_doc_ids == ("doc-a", "doc-b")
    assert {contradictions[0].doc_a, contradictions[0].doc_b} == {"doc-a", "doc-b"}


def test_is_deterministic_and_ignores_unparseable_or_same_polarity_claims() -> None:
    claims = [
        Claim(text="Graph increases recall", evidence_doc_ids=("a",)),
        Claim(text="Graph increases recall", evidence_doc_ids=("b",)),
        Claim(text="free text", evidence_doc_ids=("c",)),
    ]
    analyzer = ContradictionAnalyzer()
    assert analyzer.analyze(claims) == []
    assert analyzer.analyze([]) == []


def test_reverse_polarity_order_produces_one_pair() -> None:
    claims = [
        Claim(text="Graph decreases latency", evidence_doc_ids=("doc-2",)),
        Claim(text="Graph increases latency", evidence_doc_ids=("doc-1",)),
    ]
    results = analyze_contradictions(claims)
    assert len(results) == 1
    assert results[0].evidence_doc_ids == ("doc-2", "doc-1")
