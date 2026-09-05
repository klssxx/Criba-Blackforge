"""P06-T09 graph semantics audit tests."""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from criba.intelligence import contracts as C
from criba.intelligence.graph import (
    BridgeNodeAnalyzer,
    CommunityDetector,
    GraphCentrality,
    LinkPredictor,
    SQLiteKnowledgeGraphStore,
)


def test_repeated_upserts_accumulate_source_document_ids(tmp_path):
    store = SQLiteKnowledgeGraphStore(tmp_path / "intelligence.sqlite3")
    try:
        store.upsert_node(
            C.EntityNode(entity_id="a", label="A", node_type="Technology", source_doc_ids=("doc-1",))
        )
        store.upsert_node(
            C.EntityNode(entity_id="a", label="A", node_type="Technology", source_doc_ids=("doc-2",))
        )
        store.upsert_node(C.EntityNode(entity_id="b", label="B", node_type="Technology"))
        store.upsert_edge(C.RelationEdge("a", "b", "USES", source_doc_ids=("doc-1",)))
        store.upsert_edge(C.RelationEdge("a", "b", "USES", source_doc_ids=("doc-2",)))

        assert store.get_node("a")["source_doc_ids"] == ["doc-1", "doc-2"]
        assert store.neighbors("a")[0]["source_doc_ids"] == ["doc-1", "doc-2"]
    finally:
        store.close()


def test_graph_direction_semantics_are_consistent_across_algorithms(tmp_path):
    store = SQLiteKnowledgeGraphStore(tmp_path / "intelligence.sqlite3")
    try:
        for entity_id in ("a", "b", "c"):
            store.upsert_node(C.EntityNode(entity_id=entity_id, label=entity_id, node_type="Technology"))
        store.upsert_edge(C.RelationEdge("a", "b", "USES"))
        store.upsert_edge(C.RelationEdge("b", "c", "USES"))
        store.upsert_edge(C.RelationEdge("c", "a", "USES"))

        assert store.shortest_path("a", "c") == ["a", "b", "c"]
        assert CommunityDetector(store).detect() == [["a", "b", "c"]]
        assert BridgeNodeAnalyzer(store).articulation_points() == []
    finally:
        store.close()


def test_self_loops_do_not_inflate_undirected_degree_centrality(tmp_path):
    store = SQLiteKnowledgeGraphStore(tmp_path / "intelligence.sqlite3")
    try:
        for entity_id in ("a", "b"):
            store.upsert_node(C.EntityNode(entity_id=entity_id, label=entity_id, node_type="Technology"))
        store.upsert_edge(C.RelationEdge("a", "a", "REFERS_TO"))
        store.upsert_edge(C.RelationEdge("a", "b", "REFERS_TO"))

        assert GraphCentrality(store).degree_centrality() == {"a": 1.0, "b": 1.0}
    finally:
        store.close()


def test_self_loops_do_not_contaminate_link_prediction_neighbors(tmp_path):
    store = SQLiteKnowledgeGraphStore(tmp_path / "intelligence.sqlite3")
    try:
        for entity_id in ("a", "b", "c"):
            store.upsert_node(C.EntityNode(entity_id=entity_id, label=entity_id, node_type="Technology"))
        store.upsert_edge(C.RelationEdge("a", "a", "REFERS_TO"))
        store.upsert_edge(C.RelationEdge("a", "b", "REFERS_TO"))
        store.upsert_edge(C.RelationEdge("b", "c", "REFERS_TO"))

        assert LinkPredictor(store).predict("a") == [
            {"src": "a", "dst": "c", "score": 1.0, "common_neighbors": ["b"]}
        ]
    finally:
        store.close()


def test_graph_store_isolated_database_uses_only_intelligence_tables(tmp_path):
    db_path = tmp_path / "intelligence.sqlite3"
    legacy_path = tmp_path / "criba.sqlite3"
    store = SQLiteKnowledgeGraphStore(db_path)
    store.close()

    with sqlite3.connect(db_path) as connection:
        table_names = {
            row[0]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }

    assert "intel_entities" in table_names
    assert "intel_relations" in table_names
    assert "entities" not in table_names
    assert "relations" not in table_names
    assert not legacy_path.exists()
