"""P06-T01 graph-store tests: SQLite-backed graph primitives."""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from criba.intelligence import contracts as C
import pytest

try:
    from criba.intelligence.graph import SQLiteKnowledgeGraphStore
except ImportError:
    SQLiteKnowledgeGraphStore = None  # type: ignore[assignment,misc]


def _store(tmp_path):
    assert SQLiteKnowledgeGraphStore is not None, "graph store is not implemented"
    return SQLiteKnowledgeGraphStore(tmp_path / "intelligence.sqlite3")


def test_upsert_node_roundtrip_and_stats(tmp_path):
    store = _store(tmp_path)
    try:
        node = C.EntityNode(
            label="Photonic cooling",
            node_type="Technology",
            properties={"domain": "energy"},
            source_doc_ids=("doc-1",),
        )
        store.upsert_node(node)

        assert store.get_node(node.entity_id) == {
            "entity_id": node.entity_id,
            "label": "Photonic cooling",
            "node_type": "Technology",
            "properties": {"domain": "energy"},
            "source_doc_ids": ["doc-1"],
            "aliases": [],
        }
        assert store.stats() == {"nodes": 1, "edges": 0}
    finally:
        store.close()


def test_upsert_edge_is_visible_from_both_endpoints(tmp_path):
    store = _store(tmp_path)
    try:
        source = C.EntityNode(label="Cooling", node_type="Technology")
        target = C.EntityNode(label="Waste heat", node_type="Problem")
        store.upsert_node(source)
        store.upsert_node(target)
        edge = C.RelationEdge(
            src=source.entity_id,
            dst=target.entity_id,
            relation="SOLVES",
            weight=0.8,
            source_doc_ids=("doc-1",),
        )

        store.upsert_edge(edge)

        expected = {
            "relation_id": 1,
            "src": source.entity_id,
            "dst": target.entity_id,
            "relation": "SOLVES",
            "weight": 0.8,
            "source_doc_ids": ["doc-1"],
        }
        assert store.neighbors(source.entity_id) == [expected]
        assert store.neighbors(target.entity_id) == [expected]
        assert store.stats() == {"nodes": 2, "edges": 1}
    finally:
        store.close()


def test_upsert_edge_updates_without_duplicate_edges(tmp_path):
    store = _store(tmp_path)
    try:
        source = C.EntityNode(label="A", node_type="Technology")
        target = C.EntityNode(label="B", node_type="Technology")
        store.upsert_node(source)
        store.upsert_node(target)
        edge = {"src": source.entity_id, "dst": target.entity_id, "relation": "ENABLES"}

        store.upsert_edge(edge | {"weight": 0.2, "source_doc_ids": ["doc-1"]})
        store.upsert_edge(edge | {"weight": 0.9, "source_doc_ids": ["doc-2"]})

        assert store.stats() == {"nodes": 2, "edges": 1}
        assert store.neighbors(source.entity_id)[0]["relation_id"] == 1
        assert store.neighbors(source.entity_id)[0]["weight"] == 0.9
        assert store.neighbors(source.entity_id)[0]["source_doc_ids"] == ["doc-2"]
    finally:
        store.close()


def test_shortest_path_is_directed_and_returns_minimal_route(tmp_path):
    store = _store(tmp_path)
    try:
        nodes = [C.EntityNode(label=label, node_type="Technology") for label in "ABC"]
        for node in nodes:
            store.upsert_node(node)
        store.upsert_edge(C.RelationEdge(nodes[0].entity_id, nodes[1].entity_id, "ENABLES"))
        store.upsert_edge(C.RelationEdge(nodes[1].entity_id, nodes[2].entity_id, "ENABLES"))

        assert store.shortest_path(nodes[0].entity_id, nodes[2].entity_id) == [
            nodes[0].entity_id,
            nodes[1].entity_id,
            nodes[2].entity_id,
        ]
        assert store.shortest_path(nodes[2].entity_id, nodes[0].entity_id) is None
        assert store.shortest_path(nodes[0].entity_id, nodes[0].entity_id) == [nodes[0].entity_id]
        assert store.shortest_path(nodes[0].entity_id, "missing") is None
    finally:
        store.close()


def test_subgraph_is_bounded_to_requested_nodes(tmp_path):
    store = _store(tmp_path)
    try:
        nodes = [C.EntityNode(label=label, node_type="Technology") for label in "ABC"]
        for node in nodes:
            store.upsert_node(node)
        store.upsert_edge(C.RelationEdge(nodes[0].entity_id, nodes[1].entity_id, "ENABLES"))
        store.upsert_edge(C.RelationEdge(nodes[1].entity_id, nodes[2].entity_id, "ENABLES"))

        result = store.subgraph([nodes[1].entity_id, nodes[0].entity_id, nodes[1].entity_id])

        assert [node["entity_id"] for node in result["nodes"]] == sorted(
            [nodes[0].entity_id, nodes[1].entity_id]
        )
        assert len(result["edges"]) == 1
        assert result["edges"][0]["src"] == nodes[0].entity_id
        assert result["edges"][0]["dst"] == nodes[1].entity_id
        assert store.subgraph([]) == {"nodes": [], "edges": []}
    finally:
        store.close()


def test_upsert_node_preserves_existing_edges(tmp_path):
    store = _store(tmp_path)
    try:
        source = C.EntityNode(label="Source", node_type="Technology")
        target = C.EntityNode(label="Target", node_type="Problem")
        store.upsert_node(source)
        store.upsert_node(target)
        store.upsert_edge(C.RelationEdge(source.entity_id, target.entity_id, "SOLVES"))

        store.upsert_node(
            C.EntityNode(
                entity_id=source.entity_id,
                label="Updated source",
                node_type="Technology",
                properties={"updated": True},
            )
        )

        assert store.get_node(source.entity_id)["label"] == "Updated source"
        assert len(store.neighbors(source.entity_id)) == 1
        assert store.stats() == {"nodes": 2, "edges": 1}
    finally:
        store.close()


def test_upsert_edge_rejects_missing_endpoints(tmp_path):
    store = _store(tmp_path)
    try:
        with pytest.raises(sqlite3.IntegrityError):
            store.upsert_edge(C.RelationEdge("missing-source", "missing-target", "USES"))
        assert store.stats() == {"nodes": 0, "edges": 0}
    finally:
        store.close()
