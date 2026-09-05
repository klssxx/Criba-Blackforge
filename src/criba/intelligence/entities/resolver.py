"""Deterministic entity resolution for the IIE entities sector (P05)."""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from ..contracts import EntityAlias, EntityNode


def normalize_label(label: str) -> str:
    """Stable lookup normalization; preserves source labels on EntityNode."""
    return re.sub(r"\s+", " ", label.strip().lower())


@dataclass
class EntityResolver:
    """Type-aware normalized-label and alias resolution."""

    _by_key: dict[tuple[str, str], str] = field(default_factory=dict)
    _nodes: dict[str, EntityNode] = field(default_factory=dict)

    def resolve(
        self, label: str, node_type: str = "Technology", source_doc_id: str = ""
    ) -> EntityNode:
        key = (node_type, normalize_label(label))
        if key in self._by_key:
            node = self._nodes[self._by_key[key]]
            if source_doc_id and source_doc_id not in node.source_doc_ids:
                node.source_doc_ids = (*node.source_doc_ids, source_doc_id)
            return node

        node = EntityNode(
            label=label,
            node_type=node_type,
            source_doc_ids=(source_doc_id,) if source_doc_id else (),
        )
        self._nodes[node.entity_id] = node
        self._by_key[key] = node.entity_id
        return node

    def add_alias(self, entity_id: str, alias: str, source_doc_id: str = "") -> None:
        node = self._nodes[entity_id]
        key = (node.node_type, normalize_label(alias))
        if key not in self._by_key:
            node.aliases.append(EntityAlias(alias=alias, source_doc_id=source_doc_id))
            self._by_key[key] = entity_id

    def merge(self, target_id: str, source_id: str) -> str:
        """Merge same-type source into target and repoint all source keys."""
        target, source = self._nodes[target_id], self._nodes[source_id]
        if target.node_type != source.node_type:
            raise ValueError("cannot merge entities with different node types")
        for alias in source.aliases:
            self.add_alias(target_id, alias.alias, alias.source_doc_id)
        self.add_alias(target_id, source.label)
        target.source_doc_ids = tuple(
            sorted(set(target.source_doc_ids) | set(source.source_doc_ids))
        )
        for key, entity_id in list(self._by_key.items()):
            if entity_id == source_id:
                self._by_key[key] = target_id
        del self._nodes[source_id]
        return target_id

    def all(self) -> list[EntityNode]:
        return list(self._nodes.values())

    def count(self) -> int:
        return len(self._nodes)
