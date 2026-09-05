"""Reusable deterministic topology for graph-sector tests."""
from __future__ import annotations

from pathlib import Path

from criba.intelligence import contracts as C
from criba.intelligence.graph import SQLiteKnowledgeGraphStore

FIXTURE_NODE_IDS = (
    "company:alpha",
    "company:beta",
    "isolated:one",
    "paper:one",
    "paper:two",
    "technology:cooling",
    "technology:ml",
)

_FIXTURE_NODES = (
    ("company:alpha", "Alpha", "Company"),
    ("company:beta", "Beta", "Company"),
    ("isolated:one", "Isolated", "Technology"),
    ("paper:one", "Paper One", "Paper"),
    ("paper:two", "Paper Two", "Paper"),
    ("technology:cooling", "Cooling", "Technology"),
    ("technology:ml", "Machine learning", "Technology"),
)

_FIXTURE_EDGES = (
    ("company:alpha", "paper:one", "CITES"),
    ("company:beta", "paper:two", "CITES"),
    ("technology:cooling", "paper:one", "DERIVED_FROM"),
    ("technology:cooling", "paper:two", "DERIVED_FROM"),
    ("technology:ml", "paper:one", "DERIVED_FROM"),
    ("company:alpha", "company:beta", "COLLABORATES"),
)


def build_fixture_graph(path: str | Path) -> SQLiteKnowledgeGraphStore:
    """Create and populate a fresh graph fixture; caller owns closing it."""
    store = SQLiteKnowledgeGraphStore(path)
    for entity_id, label, node_type in _FIXTURE_NODES:
        store.upsert_node(C.EntityNode(entity_id=entity_id, label=label, node_type=node_type))
    for src, dst, relation in _FIXTURE_EDGES:
        store.upsert_edge(C.RelationEdge(src=src, dst=dst, relation=relation))
    return store
