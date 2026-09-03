"""SQLite-backed knowledge graph store for the IIE graph sector (P06)."""
from __future__ import annotations

import json
import sqlite3
from collections import deque
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any, Protocol

from ..contracts import EntityNode, RelationEdge
from ..storage import IntelligenceStore


class KnowledgeGraphStore(Protocol):
    """Public graph boundary described by the master blueprint."""

    def upsert_node(self, node: EntityNode | Mapping[str, Any]) -> None: ...

    def upsert_edge(self, edge: RelationEdge | Mapping[str, Any]) -> None: ...

    def neighbors(self, entity_id: str) -> list[dict[str, Any]]: ...

    def shortest_path(self, source: str, target: str) -> list[str] | None: ...

    def subgraph(self, entity_ids: Iterable[str]) -> dict[str, list[dict[str, Any]]]: ...

    def stats(self) -> dict[str, int]: ...

    def close(self) -> None: ...


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _unjson(value: str, default: Any) -> Any:
    try:
        return json.loads(value) if value else default
    except (TypeError, json.JSONDecodeError):
        return default


def _as_dict(value: EntityNode | RelationEdge | Mapping[str, Any]) -> dict[str, Any]:
    if isinstance(value, (EntityNode, RelationEdge)):
        return value.to_dict()
    return dict(value)


class SQLiteKnowledgeGraphStore:
    """Graph operations backed by the isolated IntelligenceStore database."""

    def __init__(self, path: str | Path = "intelligence.sqlite3") -> None:
        self._storage = IntelligenceStore(path)
        self._conn = self._storage._conn

    def close(self) -> None:
        self._storage.close()

    def upsert_node(self, node: EntityNode | Mapping[str, Any]) -> None:
        payload = _as_dict(node)
        entity_id = payload["entity_id"]
        self._conn.execute(
            """
            INSERT INTO intel_entities
                (entity_id, label, node_type, properties, source_doc_ids)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(entity_id) DO UPDATE SET
                label=excluded.label,
                node_type=excluded.node_type,
                properties=excluded.properties,
                source_doc_ids=excluded.source_doc_ids
            """,
            (
                entity_id,
                payload.get("label", ""),
                payload.get("node_type", ""),
                _json(payload.get("properties") or {}),
                _json(payload.get("source_doc_ids") or []),
            ),
        )
        for alias in payload.get("aliases") or []:
            alias_data = dict(alias)
            self._conn.execute(
                """
                INSERT INTO intel_entity_aliases (entity_id, alias, language, source_doc_id)
                SELECT ?, ?, ?, ?
                WHERE NOT EXISTS (
                    SELECT 1 FROM intel_entity_aliases
                    WHERE entity_id=? AND alias=? AND language=? AND source_doc_id=?
                )
                """,
                (
                    entity_id,
                    alias_data.get("alias", ""),
                    alias_data.get("language", "en"),
                    alias_data.get("source_doc_id", ""),
                    entity_id,
                    alias_data.get("alias", ""),
                    alias_data.get("language", "en"),
                    alias_data.get("source_doc_id", ""),
                ),
            )
        self._conn.commit()

    def get_node(self, entity_id: str) -> dict[str, Any] | None:
        row = self._conn.execute(
            "SELECT entity_id, label, node_type, properties, source_doc_ids "
            "FROM intel_entities WHERE entity_id=?",
            (entity_id,),
        ).fetchone()
        if row is None:
            return None
        node = dict(row)
        node["properties"] = _unjson(node["properties"], {})
        node["source_doc_ids"] = _unjson(node["source_doc_ids"], [])
        node["aliases"] = [
            dict(alias)
            for alias in self._conn.execute(
                "SELECT alias, language, source_doc_id FROM intel_entity_aliases "
                "WHERE entity_id=? ORDER BY alias_id",
                (entity_id,),
            ).fetchall()
        ]
        return node

    def upsert_edge(self, edge: RelationEdge | Mapping[str, Any]) -> None:
        payload = _as_dict(edge)
        src = payload["src"]
        dst = payload["dst"]
        relation = payload["relation"]
        source_doc_ids = _json(payload.get("source_doc_ids") or [])
        existing = self._conn.execute(
            "SELECT relation_id FROM intel_relations "
            "WHERE src=? AND dst=? AND relation=? ORDER BY relation_id LIMIT 1",
            (src, dst, relation),
        ).fetchone()
        if existing is None:
            self._conn.execute(
                "INSERT INTO intel_relations (src, dst, relation, weight, source_doc_ids) "
                "VALUES (?, ?, ?, ?, ?)",
                (src, dst, relation, payload.get("weight", 1.0), source_doc_ids),
            )
        else:
            self._conn.execute(
                "UPDATE intel_relations SET weight=?, source_doc_ids=? WHERE relation_id=?",
                (payload.get("weight", 1.0), source_doc_ids, existing["relation_id"]),
            )
        self._conn.commit()

    def neighbors(self, entity_id: str) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT relation_id, src, dst, relation, weight, source_doc_ids "
            "FROM intel_relations WHERE src=? OR dst=? ORDER BY relation_id",
            (entity_id, entity_id),
        ).fetchall()
        return [
            {
                **dict(row),
                "source_doc_ids": _unjson(row["source_doc_ids"], []),
            }
            for row in rows
        ]

    def shortest_path(self, source: str, target: str) -> list[str] | None:
        if not self._node_exists(source) or not self._node_exists(target):
            return None
        if source == target:
            return [source]

        previous: dict[str, str | None] = {source: None}
        queue: deque[str] = deque([source])
        while queue:
            current = queue.popleft()
            rows = self._conn.execute(
                "SELECT dst FROM intel_relations WHERE src=? ORDER BY relation_id",
                (current,),
            ).fetchall()
            for row in rows:
                candidate = row["dst"]
                if candidate in previous:
                    continue
                previous[candidate] = current
                if candidate == target:
                    return self._reconstruct_path(previous, target)
                queue.append(candidate)
        return None

    def subgraph(self, entity_ids: Iterable[str]) -> dict[str, list[dict[str, Any]]]:
        ids = tuple(sorted(set(entity_ids)))
        if not ids:
            return {"nodes": [], "edges": []}
        placeholders = ",".join("?" for _ in ids)
        nodes = [
            self.get_node(row["entity_id"])
            for row in self._conn.execute(
                f"SELECT entity_id FROM intel_entities WHERE entity_id IN ({placeholders}) "
                "ORDER BY entity_id",
                ids,
            ).fetchall()
        ]
        node_rows = [node for node in nodes if node is not None]
        edges = [
            {
                **dict(row),
                "source_doc_ids": _unjson(row["source_doc_ids"], []),
            }
            for row in self._conn.execute(
                f"SELECT relation_id, src, dst, relation, weight, source_doc_ids "
                f"FROM intel_relations WHERE src IN ({placeholders}) AND dst IN ({placeholders}) "
                "ORDER BY relation_id",
                ids + ids,
            ).fetchall()
        ]
        return {"nodes": node_rows, "edges": edges}

    def stats(self) -> dict[str, int]:
        nodes = self._conn.execute("SELECT COUNT(*) FROM intel_entities").fetchone()[0]
        edges = self._conn.execute("SELECT COUNT(*) FROM intel_relations").fetchone()[0]
        return {"nodes": int(nodes), "edges": int(edges)}

    def _node_exists(self, entity_id: str) -> bool:
        return self._conn.execute(
            "SELECT 1 FROM intel_entities WHERE entity_id=? LIMIT 1", (entity_id,)
        ).fetchone() is not None

    @staticmethod
    def _reconstruct_path(previous: Mapping[str, str | None], target: str) -> list[str]:
        path: list[str] = []
        current: str | None = target
        while current is not None:
            path.append(current)
            current = previous[current]
        path.reverse()
        return path


__all__ = ["KnowledgeGraphStore", "SQLiteKnowledgeGraphStore"]
