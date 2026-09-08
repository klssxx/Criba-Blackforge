"""P06-T05 community tests: deterministic weak components."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from criba.intelligence import contracts as C
from criba.intelligence.graph import SQLiteKnowledgeGraphStore

try:
    from criba.intelligence.graph import CommunityDetector
except ImportError:
    CommunityDetector = None  # type: ignore[assignment,misc]


def _detector(tmp_path):
    assert CommunityDetector is not None, "community detection is not implemented"
    store = SQLiteKnowledgeGraphStore(tmp_path / "intelligence.sqlite3")
    for entity_id in ("a", "b", "c", "d", "e", "f"):
        store.upsert_node(C.EntityNode(entity_id=entity_id, label=entity_id, node_type="Technology"))
    store.upsert_edge(C.RelationEdge(src="a", dst="b", relation="USES"))
    store.upsert_edge(C.RelationEdge(src="b", dst="c", relation="USES"))
    store.upsert_edge(C.RelationEdge(src="e", dst="d", relation="USES"))
    return CommunityDetector(store), store


def test_detect_returns_sorted_weak_communities(tmp_path):
    detector, store = _detector(tmp_path)
    try:
        assert detector.detect() == [["a", "b", "c"], ["d", "e"], ["f"]]
    finally:
        store.close()


def test_detect_restricts_communities_to_requested_subset(tmp_path):
    detector, store = _detector(tmp_path)
    try:
        assert detector.detect(["d", "b", "a"]) == [["a", "b"], ["d"]]
    finally:
        store.close()
