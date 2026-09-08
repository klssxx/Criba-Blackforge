"""P06-T03 traversal tests: bounded directed graph walks."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from criba.intelligence import contracts as C
from criba.intelligence.graph import SQLiteKnowledgeGraphStore

try:
    from criba.intelligence.graph import GraphTraversal
except ImportError:
    GraphTraversal = None  # type: ignore[assignment,misc]


def _traversal(tmp_path):
    assert GraphTraversal is not None, "graph traversal is not implemented"
    store = SQLiteKnowledgeGraphStore(tmp_path / "intelligence.sqlite3")
    for entity_id in ("a", "b", "c", "d"):
        store.upsert_node(C.EntityNode(entity_id=entity_id, label=entity_id, node_type="Technology"))
    store.upsert_edge(C.RelationEdge(src="a", dst="b", relation="USES"))
    store.upsert_edge(C.RelationEdge(src="a", dst="c", relation="USES"))
    store.upsert_edge(C.RelationEdge(src="b", dst="d", relation="USES"))
    store.upsert_edge(C.RelationEdge(src="c", dst="d", relation="USES"))
    return GraphTraversal(store), store


def test_bfs_is_directed_ordered_and_depth_bounded(tmp_path):
    traversal, store = _traversal(tmp_path)
    try:
        assert traversal.bfs("a", max_depth=0) == ["a"]
        assert traversal.bfs("a", max_depth=1) == ["a", "b", "c"]
        assert traversal.bfs("a", max_depth=2) == ["a", "b", "c", "d"]
        assert traversal.bfs("d", max_depth=2) == ["d"]
    finally:
        store.close()


def test_shortest_path_preserves_directed_store_semantics(tmp_path):
    traversal, store = _traversal(tmp_path)
    try:
        assert traversal.shortest_path("a", "d") == ["a", "b", "d"]
        assert traversal.shortest_path("d", "a") is None
    finally:
        store.close()


def test_bfs_rejects_negative_depth(tmp_path):
    traversal, store = _traversal(tmp_path)
    try:
        with pytest.raises(ValueError, match="max_depth"):
            traversal.bfs("a", max_depth=-1)
    finally:
        store.close()
