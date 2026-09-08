"""P06-T08 graph-fixture tests: reusable deterministic topology."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

try:
    from graph_fixtures import FIXTURE_NODE_IDS, build_fixture_graph
except ImportError:
    FIXTURE_NODE_IDS = None  # type: ignore[assignment]
    build_fixture_graph = None  # type: ignore[assignment]

from criba.intelligence.graph import BridgeNodeAnalyzer, CommunityDetector


def test_fixture_graph_has_stable_nodes_edges_and_isolate(tmp_path):
    assert build_fixture_graph is not None, "graph fixture is not implemented"
    assert FIXTURE_NODE_IDS is not None, "graph fixture ids are not implemented"
    store = build_fixture_graph(tmp_path / "fixture.sqlite3")
    try:
        assert store.node_ids() == list(FIXTURE_NODE_IDS)
        assert store.stats() == {"nodes": 7, "edges": 6}
        assert store.neighbors("isolated:one") == []
    finally:
        store.close()


def test_fixture_graph_exercises_community_and_bridge_algorithms(tmp_path):
    assert build_fixture_graph is not None, "graph fixture is not implemented"
    store = build_fixture_graph(tmp_path / "fixture.sqlite3")
    try:
        assert CommunityDetector(store).detect() == [
            [
                "company:alpha",
                "company:beta",
                "paper:one",
                "paper:two",
                "technology:cooling",
                "technology:ml",
            ],
            ["isolated:one"],
        ]
        assert BridgeNodeAnalyzer(store).articulation_points() == ["paper:one"]
    finally:
        store.close()
