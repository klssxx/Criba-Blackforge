"""P06-T06 bridge-node tests: articulation points in the weak graph."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from criba.intelligence import contracts as C
from criba.intelligence.graph import SQLiteKnowledgeGraphStore

try:
    from criba.intelligence.graph import BridgeNodeAnalyzer
except ImportError:
    BridgeNodeAnalyzer = None  # type: ignore[assignment,misc]


def _analyzer(tmp_path):
    assert BridgeNodeAnalyzer is not None, "bridge node analysis is not implemented"
    store = SQLiteKnowledgeGraphStore(tmp_path / "intelligence.sqlite3")
    for entity_id in ("a", "b", "c", "d", "e", "f"):
        store.upsert_node(C.EntityNode(entity_id=entity_id, label=entity_id, node_type="Technology"))
    store.upsert_edge(C.RelationEdge(src="a", dst="b", relation="USES"))
    store.upsert_edge(C.RelationEdge(src="b", dst="c", relation="USES"))
    store.upsert_edge(C.RelationEdge(src="c", dst="d", relation="USES"))
    store.upsert_edge(C.RelationEdge(src="c", dst="e", relation="USES"))
    return BridgeNodeAnalyzer(store), store


def test_articulation_points_are_sorted_and_exclude_leaves(tmp_path):
    analyzer, store = _analyzer(tmp_path)
    try:
        assert analyzer.articulation_points() == ["b", "c"]
    finally:
        store.close()


def test_articulation_points_respect_requested_subset(tmp_path):
    analyzer, store = _analyzer(tmp_path)
    try:
        assert analyzer.articulation_points(["c", "b", "a"]) == ["b"]
        assert analyzer.articulation_points(["d", "e", "f"]) == []
    finally:
        store.close()
