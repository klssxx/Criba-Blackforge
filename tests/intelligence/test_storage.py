"""P02 storage tests: CRUD, migrations, FTS5, cache, failure isolation."""
from __future__ import annotations

import sqlite3
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest

from criba.intelligence import contracts as C
from criba.intelligence.storage import IntelligenceStore, DB_VERSION


@pytest.fixture()
def store(tmp_path):
    s = IntelligenceStore(tmp_path / "intelligence.sqlite3")
    yield s
    s.close()


def _doc(title="Cooling paper", abstract="Photonic cooling reduces datacenter energy"):
    return C.EvidenceDocument(
        source_id="openalex", title=title, kind="paper", published="2026",
        abstract=abstract,
        fragments=[C.EvidenceFragment(text="energy -42%")],
        provenance=C.ProvenanceRecord(source_id="openalex", url="https://x"),
    )


def test_schema_migrates_to_v1(store):
    v = store.migrate()
    assert v == DB_VERSION == 1
    # re-open: idempotent
    store2 = IntelligenceStore(store.path)
    assert store2.migrate() == 1
    store2.close()


def test_all_18_tables_exist(store):
    names = {r["name"] for r in store._conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    expected = {
        "intel_runs", "intel_queries", "intel_source_requests", "intel_documents",
        "intel_fragments", "intel_claims", "intel_entities", "intel_entity_aliases",
        "intel_relations", "intel_topic_observations", "intel_signals", "intel_gaps",
        "intel_hypotheses", "intel_prior_art_matches", "intel_scorecards",
        "intel_watches", "intel_cache", "intel_technique_runs",
    }
    assert expected <= names
    fts = {r["name"] for r in store._conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%fts%'")}
    assert "intel_documents_fts" in fts


def test_run_roundtrip(store):
    run = C.IntelligenceRun(goal="datacenter cooling", intent="discovery").to_dict()
    store.save_run(run)
    got = store.get_run(run["run_id"])
    assert got and got["goal"] == "datacenter cooling"
    assert got["status"] == "RUNNING"
    assert store.list_runs()[0]["run_id"] == run["run_id"]


def test_document_roundtrip_with_fragments(store):
    doc = _doc()
    store.save_document(doc.to_dict())
    got = store.get_document(doc.doc_id)
    assert got["title"] == "Cooling paper"
    assert got["fragments"][0]["text"] == "energy -42%"
    assert got["provenance"]["url"] == "https://x"


def test_fts5_search_finds_document(store):
    store.save_document(_doc().to_dict())
    store.save_document(_doc(title="Unrelated", abstract="Quantum dots synthesis").to_dict())
    hits = store.search_documents("photonic cooling")
    assert len(hits) == 1 and hits[0]["title"] == "Cooling paper"
    assert store.search_documents("   ") == []


def test_claims_signals_gaps_hypotheses_roundtrip(store):
    store.save_claim(C.Claim(text="X works", evidence_doc_ids=("d1",)).to_dict())
    store.save_signal(C.Signal(kind="burst", topic="cooling", strength=0.9).to_dict())
    gap = C.WhiteSpaceCandidate(statement="no A+B combo", space_type="research")
    store.save_gap(gap.to_dict())
    store.save_hypothesis(C.Hypothesis(statement="try A+B", gap_ids=(gap.gap_id,)).to_dict())
    assert store._conn.execute("SELECT COUNT(*) c FROM intel_claims").fetchone()["c"] == 1
    assert store._conn.execute("SELECT kind FROM intel_gaps").fetchone()["kind"] == "white_space"
    hyp = store._conn.execute("SELECT * FROM intel_hypotheses").fetchone()
    assert hyp["falsifiable"] == 1


def test_entities_relations_graph_queries(store):
    e1 = C.EntityNode(label="Photonics", node_type="Technology")
    e2 = C.EntityNode(label="Cooling", node_type="Problem")
    e1.aliases.append(C.EntityAlias(alias="optical refrigeration"))
    store.save_entity(e1.to_dict())
    store.save_entity(e2.to_dict())
    store.save_relation(C.RelationEdge(src=e1.entity_id, dst=e2.entity_id, relation="SOLVES").to_dict())
    nb = store.neighbors(e1.entity_id)
    assert len(nb) == 1 and nb[0]["relation"] == "SOLVES"
    alias = store._conn.execute("SELECT alias FROM intel_entity_aliases").fetchone()
    assert alias["alias"] == "optical refrigeration"


def test_cache_ttl_semantics(store):
    store.cache_set("k1", {"a": 1}, ttl_s=9999)
    assert store.cache_get("k1") == {"a": 1}
    store.cache_set("k2", {"b": 2}, ttl_s=0)
    time.sleep(0.01)
    assert store.cache_get("k2") is None  # expired


def test_technique_run_lifecycle(store):
    tr = store.start_technique("run_x", "T096")
    store.finish_technique(tr, "DONE", {"n": 3})
    hist = store.technique_history("T096")
    assert hist[0]["status"] == "DONE"


def test_isolated_from_legacy_db(store, tmp_path):
    """§29: IIE must NEVER write to criba.sqlite3."""
    files = [p.name for p in tmp_path.iterdir()]
    assert "criba.sqlite3" not in files
    assert any("intelligence" in f for f in files)


def test_corrupt_input_does_not_break_store(store):
    with pytest.raises((KeyError, sqlite3.Error)):
        store.save_document({"no_doc_id": True})
    # store still usable
    store.save_run(C.IntelligenceRun(goal="after failure").to_dict())
    assert store.get_run(store.list_runs(1)[0]["run_id"])["goal"] == "after failure"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
