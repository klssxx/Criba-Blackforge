"""P06-T02 graph-builder tests: documents into graph nodes and edges."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from criba.intelligence import contracts as C
from criba.intelligence.graph import SQLiteKnowledgeGraphStore

try:
    from criba.intelligence.graph import GraphBuilder
except ImportError:
    GraphBuilder = None  # type: ignore[assignment,misc]


def _builder(tmp_path):
    assert GraphBuilder is not None, "graph builder is not implemented"
    store = SQLiteKnowledgeGraphStore(tmp_path / "intelligence.sqlite3")
    return GraphBuilder(store), store


def test_build_document_persists_document_entities_and_edges(tmp_path):
    builder, store = _builder(tmp_path)
    try:
        document = C.EvidenceDocument(
            doc_id="doc-1",
            source_id="openalex",
            title="Photonic cooling for a data center",
            kind="paper",
            abstract="Photonic cooling reduces waste heat in a data center",
        )

        result = builder.add_document(document)

        assert {node.label for node in result.nodes} == {
            "Photonic cooling for a data center",
            "photonic cooling",
            "data center",
            "waste heat",
        }
        assert len(result.edges) == 3
        assert store.get_node("document:doc-1")["node_type"] == "Paper"
        assert store.stats() == {"nodes": 4, "edges": 3}
        assert all(edge["relation"] == "DERIVED_FROM" for edge in store.neighbors("document:doc-1"))
    finally:
        store.close()


def test_build_documents_reuses_entities_and_accumulates_sources(tmp_path):
    builder, store = _builder(tmp_path)
    try:
        first = C.EvidenceDocument(
            doc_id="doc-1",
            source_id="openalex",
            title="Photonic cooling study one",
            kind="paper",
        )
        second = C.EvidenceDocument(
            doc_id="doc-2",
            source_id="openalex",
            title="Photonic cooling study two",
            kind="paper",
        )

        first_result = builder.add_document(first)
        second_result = builder.add_document(second)

        first_entity = next(node for node in first_result.nodes if node.label == "photonic cooling")
        second_entity = next(node for node in second_result.nodes if node.label == "photonic cooling")
        assert first_entity.entity_id == second_entity.entity_id
        assert store.get_node(first_entity.entity_id)["source_doc_ids"] == ["doc-1", "doc-2"]
        assert store.stats() == {"nodes": 3, "edges": 2}
        assert len(store.neighbors(first_entity.entity_id)) == 2
    finally:
        store.close()
