"""P01-T04: contract serialization tests (GLM low role).

Every contract must round-trip to a JSON-safe dict (no enums, no dataclasses,
no tuples leaking) — they cross REST/MCP/STATE boundaries.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from criba.intelligence import contracts as C
from criba.intelligence import enums as E


def _full_packet() -> C.IntelligencePacket:
    doc = C.EvidenceDocument(
        source_id="openalex", title="A paper", kind="paper",
        fragments=[C.EvidenceFragment(text="claims X", locator="p.3")],
        provenance=C.ProvenanceRecord(source_id="openalex", url="https://example.org"),
    )
    gap = C.WhiteSpaceCandidate(statement="no one combined A+B", space_type="research")
    cand = C.InventionCandidate(title="A+B device", operators=("T053",))
    prior = C.PriorArtAssessment(
        candidate_id=cand.candidate_id, verdict=E.PriorArtVerdict.SURVIVED_SEARCH.value,
        matches=[C.PriorArtMatch(doc=doc, similarity=0.42, match_kind="semantic", scout="ScienceScout")],
    )
    score = C.ScoreCard(
        candidate_id=cand.candidate_id,
        novelty=C.NoveltyAssessment(global_novelty=0.8, rationale="sparse cluster"),
        evidence=C.EvidenceAssessment(grounded_claim_ratio=1.0),
        confidence=C.ConfidenceAssessment(confidence=0.6),
        feasibility=C.FeasibilityAssessment(feasibility=0.7),
        trl=C.TRLAssessment(trl=3),
        prototypeability=C.PrototypeabilityAssessment(prototypeability=0.9, cost_to_test=0.2),
        competition=C.CompetitionAssessment(saturation=0.1),
        patent_risk=C.PatentRiskAssessment(blocking_risk=0.3),
        opportunity=C.OpportunityAssessment(opportunity=0.75),
    )
    return C.IntelligencePacket(
        run=C.IntelligenceRun(goal="test", intent="prior_art"),
        documents=[doc],
        claims=[C.Claim(text="X enables Y", evidence_doc_ids=(doc.doc_id,))],
        entities=[C.EntityNode(label="X", node_type="Technology")],
        relations=[C.RelationEdge(src="e1", dst="e2", relation="ENABLES")],
        signals=[C.Signal(kind="burst", topic="X", strength=0.9)],
        gaps=[gap],
        hypotheses=[C.Hypothesis(statement="X+B reduces cooling", gap_ids=(gap.gap_id,))],
        candidates=[cand],
        prior_art=[prior],
        scorecards=[score],
        rankings=[C.RankingResult(ranking="MOST_NOVEL", items=[(cand.candidate_id, 0.81)])],
    )


def test_packet_roundtrip_json_safe():
    packet = _full_packet()
    d = packet.to_dict()
    # Must be strictly JSON-serializable (proves no enum/dataclass leaks)
    s = json.dumps(d)
    assert len(s) > 500
    back = json.loads(s)
    assert back["run"]["intent"] == "prior_art"
    assert back["candidates"][0]["title"] == "A+B device"
    assert back["prior_art"][0]["verdict"] == "SURVIVED_SEARCH"


def test_query_plan_budget_embedded():
    plan = C.QueryPlan(run_id="run_x", goal="g", variants=[C.QueryVariant(text="q", origin="synonym")])
    d = plan.to_dict()
    assert d["budget"]["paid_sources_allowed"] is False
    assert d["variants"][0]["origin"] == "synonym"


def test_provenance_timestamps_present():
    p = C.ProvenanceRecord(source_id="s")
    assert "T" in p.to_dict()["retrieved_at"]


def test_weak_signal_extends_signal():
    ws = C.WeakSignal(kind="weak", topic="photonic cooling", confidence=0.4)
    d = ws.to_dict()
    assert d["confidence"] == 0.4 and d["kind"] == "weak"


def test_gap_subclasses_keep_kind():
    assert C.Contradiction(statement="A vs B").kind == "contradiction"
    assert C.FailureCase(statement="f", failure_mode="leak").to_dict()["failure_mode"] == "leak"
    assert C.ResurrectionCandidate(statement="r", dormant_since="1998").kind == "resurrection"


def test_enums_values_blueprint_exact():
    assert [v.value for v in E.PriorArtVerdict] == [
        "KNOWN", "NEAR_PRIOR_ART", "PARTIAL_PRIOR_ART", "UNRESOLVED", "SURVIVED_SEARCH"]
    assert "PROVEN_NEW" not in [v.value for v in E.PriorArtVerdict]
    assert len(list(E.TechniqueStatus)) == 8
    assert len(list(E.ExecutionProfile)) == 7


def test_ids_have_prefixes():
    assert C.EvidenceDocument().doc_id.startswith("doc_")
    assert C.Claim(text="x").claim_id.startswith("clm_")
    assert C.IntelligenceRun().run_id.startswith("run_")


if __name__ == "__main__":
    raise SystemExit(__import__("pytest").main([__file__, "-q"]))
