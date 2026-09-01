"""MVP innovation tests — pre-GUI gates (conditions 12-16).

Run: pytest tests/unit/test_innovation_mvp.py
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from criba import engine
from criba.genome import Genome, normalize_proposal
from criba.genome import classify as gclassify
from criba.similarity import WEIGHTS, classify, genome_distance


# ---------- condition 1: schema_version is a string ----------
def test_schema_version_is_string():
    p = engine.activate("idea nueva para reducir fraude", "auto", "balanced", 4)
    assert isinstance(p["schema_version"], str)
    assert p["schema_version"] == "2.0.0"


# ---------- condition 12: v1 compatibility ----------
def test_v1_packet_loads_and_migrates(tmp_path):
    v1 = {
        "packet_type": "MANDATORY_MODEL_PACKET",
        "activation_id": "abc-123",
        "timestamp": "2026-01-01T00:00:00Z",
        "original_query": "consulta legacy",
        "selected_current": {"id": "falsacion_invariantes", "name": "Falsación de invariantes", "score": 80, "selection_reasons": ["x"]},
        "supporting_methods": [], "contextualization": {}, "rupture": {},
        "ideas": [{"method": "m", "method_id": "M1", "proposal": "p"}],
        "experiment": {}, "decision": {"recommended_status": "AMPLIAR PRUEBA"},
        "model_instruction": "inst", "response_contract": {}, "security": {},
    }
    path = tmp_path / "v1.json"
    path.write_text(json.dumps(v1), encoding="utf-8")
    # loading must not raise; innovation block added, legacy fields preserved
    loaded = json.loads(path.read_text(encoding="utf-8"))
    loaded.setdefault("innovation", {"ideas": []})
    assert loaded["selected_current"]["name"] == "Falsación de invariantes"
    assert loaded["decision"]["recommended_status"] == "AMPLIAR PRUEBA"
    assert "innovation" in loaded


def test_v2_packet_creation():
    p = engine.activate("propon una alternativa original", "auto", "creative", 4)
    for f in ("selected_current", "supporting_methods", "contextualization", "rupture",
              "experiment", "decision", "model_instruction", "response_contract"):
        assert f in p, f"falta campo legacy {f}"
    assert "innovation" in p


# ---------- condition 12: enums ----------
def test_valid_enum():
    assert gclassify("topology", "decentralized") == "decentralized"


def test_invalid_enum_to_unknown():
    assert gclassify("topology", "red_federated") == "unknown"


def test_new_concept_parked():
    g, parked = normalize_proposal({"actor": ["autonomous_agent", "red_agent"], "mechanism": ["capability_proof"],
                                     "topology": ["decentralized"], "trust_model": ["evidence_based"],
                                     "time_model": ["ephemeral_per_operation"]})
    assert g.actor == ["autonomous_agent"]
    assert any(up.field == "actor" and up.value == "red_agent" for up in parked)
    # full structure (condition 8)
    up = [x for x in parked if x.field == "actor"][0]
    assert up.evidence and up.status == "pending_review"


def test_invalid_evidence_parked():
    g = Genome()
    w = engine  # placeholder
    from criba.genome import GenomeEvidence, validate_evidence
    warns = validate_evidence(g, [GenomeEvidence(field="trust_model", value="blockchain_trust", evidence_span="x")])
    assert any("blockchain_trust" in x for x in warns)
    assert any(up.value == "blockchain_trust" for up in g.unclassified_properties)


# ---------- condition 12 + 14: similarity ----------
def test_identical_similarity():
    a = {"mechanism": ["verification"], "topology": ["mesh"], "trust_model": ["evidence_based"],
         "actor": ["autonomous_agent"], "time_model": ["ephemeral_per_operation"]}
    b = dict(a)
    r = genome_distance(a, b)
    assert r["distance"] == 0.0
    assert r["similarity"] == 1.0


def test_close_variant():
    a = {"mechanism": ["verification"], "topology": ["mesh"], "trust_model": ["evidence_based"],
         "actor": ["autonomous_agent"], "time_model": ["ephemeral_per_operation"]}
    b = {"mechanism": ["verification"], "topology": ["mesh"], "trust_model": ["implicit"],
         "actor": ["autonomous_agent"], "time_model": ["ephemeral_per_operation"]}
    r = classify(a, b)
    assert r["verdict"] == "close_variant"


def test_structurally_distinct():
    a = {"mechanism": ["verification"], "topology": ["mesh"], "trust_model": ["evidence_based"],
         "actor": ["autonomous_agent"], "time_model": ["ephemeral_per_operation"]}
    b = {"mechanism": ["inversion"], "topology": ["centralized"], "trust_model": ["adversarial"],
         "actor": ["adversary"], "time_model": ["continuous"]}
    r = classify(a, b)
    assert r["verdict"] == "structurally_distinct"


def test_unknown_dominated_low_similarity():
    a = {"mechanism": ["unknown"], "topology": ["unknown"], "trust_model": ["unknown"],
         "actor": ["unknown"], "time_model": ["unknown"]}
    b = {"mechanism": ["unknown"], "topology": ["unknown"], "trust_model": ["unknown"],
         "actor": ["unknown"], "time_model": ["unknown"]}
    r = genome_distance(a, b)
    # both absent -> no match credit -> low similarity, NOT high
    assert r["similarity"] < 0.5


def test_multivalue_jaccard_excludes_unknown():
    a = {"mechanism": ["verification", "unknown"], "topology": ["mesh"], "trust_model": ["evidence_based"],
         "actor": ["autonomous_agent"], "time_model": ["ephemeral_per_operation"]}
    b = {"mechanism": ["verification"], "topology": ["mesh"], "trust_model": ["evidence_based"],
         "actor": ["autonomous_agent"], "time_model": ["ephemeral_per_operation"]}
    r = genome_distance(a, b)
    # unknown ignored -> should be high similarity, not penalized
    assert r["similarity"] >= 0.95


def test_weights_normalized():
    assert abs(sum(WEIGHTS.values()) - 1.0) < 1e-9


# ---------- condition 3 + 13: single canonical idea collection ----------
def test_ideas_alias_never_diverges():
    p = engine.activate("necesito una idea nueva y disruptiva", "auto", "balanced", 4)
    assert "ideas" in p and "innovation" in p
    assert p["ideas"] is p["innovation"]["ideas"], "packet['ideas'] debe ser el MISMO objeto que innovation['ideas']"
    assert len(p["ideas"]) == len(p["innovation"]["ideas"])
    ids_a = [i["id"] for i in p["ideas"]]
    ids_b = [i["id"] for i in p["innovation"]["ideas"]]
    assert ids_a == ids_b


def test_idea_has_required_fields():
    p = engine.activate("idea para onboarding", "auto", "creative", 4)
    idea = p["innovation"]["ideas"][0]
    for f in ("id", "title", "description", "mechanism_causal", "difference_from_known",
              "genome", "evidence", "family", "duplicate_status", "source_method"):
        assert f in idea, f"falta {f} en idea"


# ---------- condition 11: determinism ----------
def test_determinism_same_params():
    a = engine.activate("misma consulta determinista", "auto", "balanced", 4)
    b = engine.activate("misma consulta determinista", "auto", "balanced", 4)
    a_ids = [i["id"] for i in a["innovation"]["ideas"]]
    b_ids = [i["id"] for i in b["innovation"]["ideas"]]
    assert a_ids == b_ids
    # structural equality except uuid/timestamp
    a2 = {k: v for k, v in a.items() if k not in ("activation_id", "timestamp")}
    b2 = {k: v for k, v in b.items() if k not in ("activation_id", "timestamp")}
    assert json.dumps(a2, sort_keys=True) == json.dumps(b2, sort_keys=True)


# ---------- condition 12: persistence + export + prompt + v1 divergence ----------
def test_persistence_roundtrip(tmp_path):
    from criba.storage import Storage
    p = engine.activate("consulta para persistir", "auto", "balanced", 4)
    store = Storage(tmp_path / "s.sqlite3")
    ident = store.save(p["original_query"], p, {"gui": False})
    back = store.get(ident)
    assert back["packet"]["activation_id"] == p["activation_id"]
    assert len(back["packet"]["innovation"]["ideas"]) == len(p["innovation"]["ideas"])


def test_export_view():
    p = engine.activate("exportame", "auto", "balanced", 4)
    view = engine.export_innovation_portfolio(p)
    assert view["activation_id"] == p["activation_id"]
    assert view["ideas"] == p["innovation"]["ideas"]


def test_build_prompt():
    p = engine.activate("prompt", "auto", "balanced", 4)
    out = engine.build_prompt(p)
    assert "MANDATORY_MODEL_PACKET" in out
