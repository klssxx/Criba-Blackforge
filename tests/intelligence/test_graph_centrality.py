"""P06-T04 centrality tests: deterministic degree scores."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from criba.intelligence import contracts as C
from criba.intelligence.graph import SQLiteKnowledgeGraphStore

try:
    from criba.intelligence.graph import GraphCentrality
except ImportError:
    GraphCentrality = None  # type: ignore[assignment,misc]


def _centrality(tmp_path):
    assert GraphCentrality is not None, "graph centrality is not implemented"
    store = SQLiteKnowledgeGraphStore(tmp_path / "intelligence.sqlite3")
    for entity_id in ("a", "b", "c", "d"):
        store.upsert_node(C.EntityNode(entity_id=entity_id, label=entity_id, node_type="Technology"))
    store.upsert_edge(C.RelationEdge(src="a", dst="b", relation="USES"))
    store.upsert_edge(C.RelationEdge(src="a", dst="c", relation="USES"))
    store.upsert_edge(C.RelationEdge(src="c", dst="d", relation="USES"))
    return GraphCentrality(store), store


def test_degree_centrality_is_normalized_and_deterministic(tmp_path):
    centrality, store = _centrality(tmp_path)
    try:
        scores = centrality.degree_centrality()

        assert list(scores) == ["a", "b", "c", "d"]
        assert scores["a"] == pytest.approx(2 / 3)
        assert scores["b"] == pytest.approx(1 / 3)
        assert scores["c"] == pytest.approx(2 / 3)
        assert scores["d"] == pytest.approx(1 / 3)
    finally:
        store.close()


def test_degree_centrality_limits_neighbors_to_requested_subgraph(tmp_path):
    centrality, store = _centrality(tmp_path)
    try:
        assert centrality.degree_centrality(["d"]) == {"d": 0.0}
        scores = centrality.degree_centrality(["a", "b", "d"])
        assert scores == {
            "a": pytest.approx(0.5),
            "b": pytest.approx(0.5),
            "d": pytest.approx(0.0),
        }
    finally:
        store.close()
