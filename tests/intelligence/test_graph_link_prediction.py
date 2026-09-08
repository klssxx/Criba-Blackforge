"""P06-T07 link prediction tests: deterministic common-neighbor candidates."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from criba.intelligence import contracts as C
from criba.intelligence.graph import SQLiteKnowledgeGraphStore

try:
    from criba.intelligence.graph import LinkPredictor
except ImportError:
    LinkPredictor = None  # type: ignore[assignment,misc]


def _predictor(tmp_path):
    assert LinkPredictor is not None, "link prediction is not implemented"
    store = SQLiteKnowledgeGraphStore(tmp_path / "intelligence.sqlite3")
    for entity_id in ("a", "b", "c", "d"):
        store.upsert_node(C.EntityNode(entity_id=entity_id, label=entity_id, node_type="Technology"))
    store.upsert_edge(C.RelationEdge(src="a", dst="b", relation="USES"))
    store.upsert_edge(C.RelationEdge(src="a", dst="c", relation="USES"))
    store.upsert_edge(C.RelationEdge(src="b", dst="d", relation="USES"))
    store.upsert_edge(C.RelationEdge(src="c", dst="d", relation="USES"))
    return LinkPredictor(store), store


def test_predict_returns_ranked_absent_links_by_common_neighbors(tmp_path):
    predictor, store = _predictor(tmp_path)
    try:
        assert predictor.predict("a", limit=1) == [
            {
                "src": "a",
                "dst": "d",
                "score": 1.0,
                "common_neighbors": ["b", "c"],
            }
        ]
    finally:
        store.close()


def test_predict_excludes_existing_links(tmp_path):
    predictor, store = _predictor(tmp_path)
    try:
        assert [item["dst"] for item in predictor.predict("a", limit=10)] == ["d"]
    finally:
        store.close()


def test_predict_rejects_negative_limit_and_accepts_zero(tmp_path):
    predictor, store = _predictor(tmp_path)
    try:
        with pytest.raises(ValueError, match="limit"):
            predictor.predict("a", limit=-1)
        assert predictor.predict("a", limit=0) == []
    finally:
        store.close()
