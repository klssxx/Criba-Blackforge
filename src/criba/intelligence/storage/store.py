"""IntelligenceStore (P02-T01/T02/T03): SQLite storage for the IIE.

18 tables (blueprint §29) + FTS5 full-text index over documents (§30).
Design rules:
- separate DB file (intelligence.sqlite3); NEVER criba.sqlite3
- additive, versioned migrations (PRAGMA user_version)
- JSON-safe dict in/out (contracts.to_dict shapes)
- WAL journal for concurrent reads; check_same_thread=False for API use
"""
from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any

DB_VERSION = 1

_SCHEMA = """
CREATE TABLE IF NOT EXISTS intel_runs (
    run_id TEXT PRIMARY KEY,
    goal TEXT NOT NULL DEFAULT '',
    intent TEXT NOT NULL DEFAULT 'discovery',
    preset TEXT NOT NULL DEFAULT 'BALANCED',
    started_at TEXT NOT NULL,
    finished_at TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'RUNNING',
    techniques_used TEXT NOT NULL DEFAULT '[]',
    request_count INTEGER NOT NULL DEFAULT 0,
    payload TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS intel_queries (
    query_id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL REFERENCES intel_runs(run_id) ON DELETE CASCADE,
    text TEXT NOT NULL,
    language TEXT NOT NULL DEFAULT 'en',
    origin TEXT NOT NULL DEFAULT 'original',
    technique_ids TEXT NOT NULL DEFAULT '[]'
);
CREATE TABLE IF NOT EXISTS intel_source_requests (
    request_id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL REFERENCES intel_runs(run_id) ON DELETE CASCADE,
    source_id TEXT NOT NULL,
    query_text TEXT NOT NULL DEFAULT '',
    ok INTEGER NOT NULL DEFAULT 0,
    error TEXT NOT NULL DEFAULT '',
    elapsed_s REAL NOT NULL DEFAULT 0.0,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS intel_documents (
    doc_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL DEFAULT '',
    source_id TEXT NOT NULL DEFAULT '',
    title TEXT NOT NULL DEFAULT '',
    kind TEXT NOT NULL DEFAULT 'document',
    published TEXT NOT NULL DEFAULT '',
    url TEXT NOT NULL DEFAULT '',
    language TEXT NOT NULL DEFAULT 'en',
    abstract TEXT NOT NULL DEFAULT '',
    provenance TEXT NOT NULL DEFAULT '{}',
    metadata TEXT NOT NULL DEFAULT '{}',
    content_hash TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS intel_fragments (
    fragment_id TEXT PRIMARY KEY,
    doc_id TEXT NOT NULL REFERENCES intel_documents(doc_id) ON DELETE CASCADE,
    text TEXT NOT NULL,
    locator TEXT NOT NULL DEFAULT '',
    language TEXT NOT NULL DEFAULT 'en',
    epistemic_state TEXT NOT NULL DEFAULT 'INFERENCE'
);
CREATE TABLE IF NOT EXISTS intel_claims (
    claim_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL DEFAULT '',
    text TEXT NOT NULL,
    epistemic_state TEXT NOT NULL DEFAULT 'INFERENCE',
    evidence_doc_ids TEXT NOT NULL DEFAULT '[]',
    fragment_ids TEXT NOT NULL DEFAULT '[]',
    technique_ids TEXT NOT NULL DEFAULT '[]',
    created_by TEXT NOT NULL DEFAULT 'rule'
);
CREATE TABLE IF NOT EXISTS intel_entities (
    entity_id TEXT PRIMARY KEY,
    label TEXT NOT NULL,
    node_type TEXT NOT NULL DEFAULT 'Technology',
    properties TEXT NOT NULL DEFAULT '{}',
    source_doc_ids TEXT NOT NULL DEFAULT '[]'
);
CREATE TABLE IF NOT EXISTS intel_entity_aliases (
    alias_id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_id TEXT NOT NULL REFERENCES intel_entities(entity_id) ON DELETE CASCADE,
    alias TEXT NOT NULL,
    language TEXT NOT NULL DEFAULT 'en',
    source_doc_id TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS intel_relations (
    relation_id INTEGER PRIMARY KEY AUTOINCREMENT,
    src TEXT NOT NULL REFERENCES intel_entities(entity_id) ON DELETE CASCADE,
    dst TEXT NOT NULL REFERENCES intel_entities(entity_id) ON DELETE CASCADE,
    relation TEXT NOT NULL,
    weight REAL NOT NULL DEFAULT 1.0,
    source_doc_ids TEXT NOT NULL DEFAULT '[]'
);
CREATE TABLE IF NOT EXISTS intel_topic_observations (
    obs_id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic TEXT NOT NULL,
    period TEXT NOT NULL,
    frequency INTEGER NOT NULL DEFAULT 0,
    source_diversity INTEGER NOT NULL DEFAULT 0,
    metadata TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS intel_signals (
    signal_id TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    topic TEXT NOT NULL DEFAULT '',
    strength REAL NOT NULL DEFAULT 0.0,
    direction TEXT NOT NULL DEFAULT 'up',
    evidence_doc_ids TEXT NOT NULL DEFAULT '[]',
    technique_ids TEXT NOT NULL DEFAULT '[]',
    extra TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS intel_gaps (
    gap_id TEXT PRIMARY KEY,
    kind TEXT NOT NULL DEFAULT 'research',
    statement TEXT NOT NULL DEFAULT '',
    evidence_doc_ids TEXT NOT NULL DEFAULT '[]',
    technique_ids TEXT NOT NULL DEFAULT '[]',
    epistemic_state TEXT NOT NULL DEFAULT 'HYPOTHESIS',
    extra TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS intel_hypotheses (
    hypothesis_id TEXT PRIMARY KEY,
    statement TEXT NOT NULL DEFAULT '',
    rationale TEXT NOT NULL DEFAULT '',
    epistemic_state TEXT NOT NULL DEFAULT 'HYPOTHESIS',
    gap_ids TEXT NOT NULL DEFAULT '[]',
    evidence_doc_ids TEXT NOT NULL DEFAULT '[]',
    technique_ids TEXT NOT NULL DEFAULT '[]',
    falsifiable INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS intel_prior_art_matches (
    match_id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL DEFAULT '',
    candidate_id TEXT NOT NULL DEFAULT '',
    doc_id TEXT NOT NULL DEFAULT '',
    similarity REAL NOT NULL DEFAULT 0.0,
    match_kind TEXT NOT NULL DEFAULT 'literal',
    overlapping_terms TEXT NOT NULL DEFAULT '[]',
    scout TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS intel_scorecards (
    candidate_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL DEFAULT '',
    payload TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS intel_watches (
    watch_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    definition TEXT NOT NULL DEFAULT '{}',
    last_run TEXT NOT NULL DEFAULT '',
    last_status TEXT NOT NULL DEFAULT 'NEW',
    enabled INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS intel_cache (
    cache_key TEXT PRIMARY KEY,
    payload TEXT NOT NULL,
    created_at REAL NOT NULL,
    ttl_s REAL NOT NULL DEFAULT 86400.0
);
CREATE TABLE IF NOT EXISTS intel_technique_runs (
    technique_run_id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL DEFAULT '',
    technique_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'RUNNING',
    started_at TEXT NOT NULL DEFAULT (datetime('now')),
    finished_at TEXT NOT NULL DEFAULT '',
    detail TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_documents_run ON intel_documents(run_id);
CREATE INDEX IF NOT EXISTS idx_documents_kind ON intel_documents(kind);
CREATE INDEX IF NOT EXISTS idx_claims_run ON intel_claims(run_id);
CREATE INDEX IF NOT EXISTS idx_signals_kind ON intel_signals(kind);
CREATE INDEX IF NOT EXISTS idx_gaps_kind ON intel_gaps(kind);
CREATE INDEX IF NOT EXISTS idx_relations_entities ON intel_relations(src, dst);
CREATE VIRTUAL TABLE IF NOT EXISTS intel_documents_fts USING fts5(
    doc_id UNINDEXED, title, abstract, content='intel_documents', content_rowid='rowid'
);
"""


def _js(v: Any) -> str:
    return json.dumps(v, ensure_ascii=False, sort_keys=True)


def _unjs(s: str, default: Any = None) -> Any:
    try:
        return json.loads(s) if s else default
    except (json.JSONDecodeError, TypeError):
        return default


class IntelligenceStore:
    """SQLite store for IIE artifacts. One file, isolated from legacy."""

    def __init__(self, path: str | Path = "intelligence.sqlite3"):
        self.path = Path(path)
        self._conn = sqlite3.connect(str(self.path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self.migrate()

    # -- schema / migrations (P02-T02) --------------------------------------
    def migrate(self) -> int:
        current = self._conn.execute("PRAGMA user_version").fetchone()[0]
        if current < 1:
            self._conn.executescript(_SCHEMA)
            self._conn.execute(f"PRAGMA user_version={DB_VERSION}")
            self._conn.commit()
        return self._conn.execute("PRAGMA user_version").fetchone()[0]

    def close(self) -> None:
        self._conn.close()

    # -- runs ---------------------------------------------------------------
    def save_run(self, run: dict[str, Any]) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO intel_runs "
            "(run_id, goal, intent, preset, started_at, finished_at, status, techniques_used, request_count, payload) "
            "VALUES (?,?,?,?,?,?,?,?,?,?)",
            (run["run_id"], run.get("goal", ""), run.get("intent", "discovery"),
             run.get("preset", "BALANCED"), run.get("started_at", ""),
             run.get("finished_at", ""), run.get("status", "RUNNING"),
             _js(run.get("techniques_used", [])), run.get("request_count", 0),
             _js(run.get("payload", {}))))
        self._conn.commit()

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        row = self._conn.execute("SELECT * FROM intel_runs WHERE run_id=?", (run_id,)).fetchone()
        if not row:
            return None
        d = dict(row)
        d["techniques_used"] = _unjs(d["techniques_used"], [])
        d["payload"] = _unjs(d["payload"], {})
        return d

    def list_runs(self, limit: int = 50) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT run_id, goal, intent, status, started_at FROM intel_runs "
            "ORDER BY started_at DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]

    # -- documents (P02-T03: FTS5) ------------------------------------------
    def save_document(self, doc: dict[str, Any], run_id: str = "") -> None:
        content_hash = ""  # filled by dedup layer later; keep storage dumb
        self._conn.execute(
            "INSERT OR REPLACE INTO intel_documents "
            "(doc_id, run_id, source_id, title, kind, published, url, language, abstract, provenance, metadata, content_hash) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (doc["doc_id"], run_id, doc.get("source_id", ""), doc.get("title", ""),
             doc.get("kind", "document"), doc.get("published", ""), doc.get("url", ""),
             doc.get("language", "en"), doc.get("abstract", ""),
             _js(doc.get("provenance") or {}), _js(doc.get("metadata") or {}), content_hash))
        # rebuild FTS row (delete+insert keeps external-content table in sync)
        self._conn.execute(
            "INSERT INTO intel_documents_fts(intel_documents_fts, doc_id, title, abstract) "
            "VALUES('delete', (SELECT rowid FROM intel_documents WHERE doc_id=?), ?, ?)",
            (doc["doc_id"], doc.get("title", ""), doc.get("abstract", "")))
        self._conn.execute(
            "INSERT INTO intel_documents_fts(doc_id, title, abstract) VALUES (?,?,?)",
            (doc["doc_id"], doc.get("title", ""), doc.get("abstract", "")))
        for frag in doc.get("fragments", []):
            self._conn.execute(
                "INSERT OR REPLACE INTO intel_fragments (fragment_id, doc_id, text, locator, language, epistemic_state) "
                "VALUES (?,?,?,?,?,?)",
                (frag["fragment_id"], doc["doc_id"], frag.get("text", ""),
                 frag.get("locator", ""), frag.get("language", "en"),
                 frag.get("epistemic_state", "INFERENCE")))
        self._conn.commit()

    def get_document(self, doc_id: str) -> dict[str, Any] | None:
        row = self._conn.execute("SELECT * FROM intel_documents WHERE doc_id=?", (doc_id,)).fetchone()
        if not row:
            return None
        d = dict(row)
        d["provenance"] = _unjs(d["provenance"], {})
        d["metadata"] = _unjs(d["metadata"], {})
        d["fragments"] = [dict(f) for f in self._conn.execute(
            "SELECT fragment_id, text, locator, language, epistemic_state "
            "FROM intel_fragments WHERE doc_id=?", (doc_id,)).fetchall()]
        return d

    def search_documents(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        """FTS5 MATCH search over title+abstract (T031 lexical base)."""
        if not query.strip():
            return []
        try:
            rows = self._conn.execute(
                "SELECT d.* FROM intel_documents_fts f JOIN intel_documents d ON d.rowid=f.rowid "
                "WHERE intel_documents_fts MATCH ? ORDER BY rank LIMIT ?",
                (query, limit)).fetchall()
        except sqlite3.OperationalError:
            return []
        out = []
        for r in rows:
            d = dict(r)
            d["provenance"] = _unjs(d["provenance"], {})
            d["metadata"] = _unjs(d["metadata"], {})
            out.append(d)
        return out

    # -- claims / signals / gaps / hypotheses -------------------------------
    def _upsert_simple(self, table: str, key: str, obj: dict[str, Any],
                       json_cols: tuple[str, ...]) -> None:
        cols = list(obj.keys())
        vals = [_js(obj[c]) if c in json_cols else obj.get(c, "") for c in cols]
        placeholders = ",".join("?" * len(cols))
        self._conn.execute(
            f"INSERT OR REPLACE INTO {table} ({','.join(cols)}) VALUES ({placeholders})", vals)
        self._conn.commit()

    def save_claim(self, claim: dict[str, Any]) -> None:
        self._upsert_simple("intel_claims", "claim_id", claim,
                            ("evidence_doc_ids", "fragment_ids", "technique_ids"))

    def save_signal(self, signal: dict[str, Any]) -> None:
        self._upsert_simple("intel_signals", "signal_id", signal,
                            ("evidence_doc_ids", "technique_ids"))

    def save_gap(self, gap: dict[str, Any]) -> None:
        g = {k: v for k, v in gap.items() if k in
             ("gap_id", "kind", "statement", "evidence_doc_ids", "technique_ids", "epistemic_state")}
        g["extra"] = _js({k: v for k, v in gap.items() if k not in g})
        self._upsert_simple("intel_gaps", "gap_id", g,
                            ("evidence_doc_ids", "technique_ids"))

    def save_hypothesis(self, hyp: dict[str, Any]) -> None:
        h = dict(hyp)
        h["falsifiable"] = 1 if h.get("falsifiable", True) else 0
        self._upsert_simple("intel_hypotheses", "hypothesis_id", h,
                            ("gap_ids", "evidence_doc_ids", "technique_ids"))

    # -- entities / relations ------------------------------------------------
    def save_entity(self, entity: dict[str, Any]) -> None:
        e = {k: v for k, v in entity.items() if k in
             ("entity_id", "label", "node_type", "properties", "source_doc_ids")}
        self._upsert_simple("intel_entities", "entity_id", e,
                            ("properties", "source_doc_ids"))
        for a in entity.get("aliases", []):
            self._conn.execute(
                "INSERT INTO intel_entity_aliases (entity_id, alias, language, source_doc_id) "
                "VALUES (?,?,?,?)",
                (entity["entity_id"], a.get("alias", ""), a.get("language", "en"),
                 a.get("source_doc_id", "")))
        self._conn.commit()

    def save_relation(self, rel: dict[str, Any]) -> None:
        self._conn.execute(
            "INSERT INTO intel_relations (src, dst, relation, weight, source_doc_ids) "
            "VALUES (?,?,?,?,?)",
            (rel["src"], rel["dst"], rel["relation"], rel.get("weight", 1.0),
             _js(rel.get("source_doc_ids", []))))
        self._conn.commit()

    def neighbors(self, entity_id: str) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT src, dst, relation, weight FROM intel_relations "
            "WHERE src=? OR dst=?", (entity_id, entity_id)).fetchall()
        return [dict(r) for r in rows]

    # -- cache (§34 free-first: cache before network) ------------------------
    def cache_get(self, key: str) -> Any | None:
        row = self._conn.execute(
            "SELECT payload, created_at, ttl_s FROM intel_cache WHERE cache_key=?",
            (key,)).fetchone()
        if not row:
            return None
        if time.time() - row["created_at"] > row["ttl_s"]:
            return None  # expired: caller may re-fetch and re-set
        return _unjs(row["payload"])

    def cache_set(self, key: str, payload: Any, ttl_s: float = 86400.0) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO intel_cache (cache_key, payload, created_at, ttl_s) "
            "VALUES (?,?,?,?)", (key, _js(payload), time.time(), ttl_s))
        self._conn.commit()

    # -- technique run tracking (§127) ---------------------------------------
    def start_technique(self, run_id: str, technique_id: str) -> int:
        cur = self._conn.execute(
            "INSERT INTO intel_technique_runs (run_id, technique_id, status) VALUES (?,?, 'RUNNING')",
            (run_id, technique_id))
        self._conn.commit()
        return cur.lastrowid

    def finish_technique(self, technique_run_id: int, status: str, detail: dict | None = None) -> None:
        self._conn.execute(
            "UPDATE intel_technique_runs SET status=?, finished_at=datetime('now'), detail=? "
            "WHERE technique_run_id=?", (status, _js(detail or {}), technique_run_id))
        self._conn.commit()

    def technique_history(self, technique_id: str, limit: int = 20) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT * FROM intel_technique_runs WHERE technique_id=? "
            "ORDER BY technique_run_id DESC LIMIT ?", (technique_id, limit)).fetchall()
        return [dict(r) for r in rows]
