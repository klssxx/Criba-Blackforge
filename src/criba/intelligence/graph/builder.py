"""Deterministic document-to-knowledge-graph builder (P06-T02)."""
from __future__ import annotations

from dataclasses import dataclass, field

from ..contracts import EntityNode, EvidenceDocument, RelationEdge
from ..entities import EntityResolver, extract_entities
from .store import KnowledgeGraphStore

_DOCUMENT_NODE_TYPES = {
    "paper": "Paper",
    "patent": "Patent",
    "repo": "Repository",
    "repository": "Repository",
    "product": "Product",
    "dataset": "Dataset",
    "model": "Model",
}


@dataclass
class GraphBuildResult:
    """Artifacts produced by one deterministic document build."""

    nodes: list[EntityNode] = field(default_factory=list)
    edges: list[RelationEdge] = field(default_factory=list)


class GraphBuilder:
    """Build and persist document/entity provenance edges."""

    def __init__(
        self,
        store: KnowledgeGraphStore,
        resolver: EntityResolver | None = None,
    ) -> None:
        self.store = store
        self.resolver = resolver or EntityResolver()

    def add_document(self, document: EvidenceDocument) -> GraphBuildResult:
        document_node = EntityNode(
            entity_id=f"document:{document.doc_id}",
            label=document.title or document.doc_id,
            node_type=_DOCUMENT_NODE_TYPES.get(document.kind.lower(), "Document"),
            properties={
                "source_id": document.source_id,
                "url": document.url,
                "published": document.published,
                "language": document.language,
                "kind": document.kind,
                "metadata": document.metadata,
            },
            source_doc_ids=(document.doc_id,),
        )
        entities = extract_entities(self._document_text(document), self.resolver, document.doc_id)
        nodes = [document_node, *entities]
        edges = [
            RelationEdge(
                src=entity.entity_id,
                dst=document_node.entity_id,
                relation="DERIVED_FROM",
                source_doc_ids=(document.doc_id,),
            )
            for entity in entities
        ]

        for node in nodes:
            self.store.upsert_node(node)
        for edge in edges:
            self.store.upsert_edge(edge)
        return GraphBuildResult(nodes=nodes, edges=edges)

    @staticmethod
    def _document_text(document: EvidenceDocument) -> str:
        return "\n".join(
            [document.title, document.abstract, *(fragment.text for fragment in document.fragments)]
        )


__all__ = ["GraphBuildResult", "GraphBuilder"]
