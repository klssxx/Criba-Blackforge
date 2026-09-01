from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .constants import (
    DEFAULT_DB,
    VALID_DECISIONS,
)


class Storage:
    def __init__(self, path: Path | str | None = DEFAULT_DB) -> None:
        self.path = Path(path or DEFAULT_DB)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.path, timeout=3)
        con.row_factory = sqlite3.Row
        return con

    def initialize(self) -> None:
        con = self.connect()
        try:
            with con:
                con.execute('''CREATE TABLE IF NOT EXISTS sessions (
                  id TEXT PRIMARY KEY, created_at TEXT NOT NULL, query_hash TEXT NOT NULL,
                  query TEXT NOT NULL, current_id TEXT NOT NULL, status TEXT NOT NULL,
                  config_json TEXT NOT NULL, packet_json TEXT NOT NULL, evidence_json TEXT NOT NULL DEFAULT '[]')''')
                con.execute('''CREATE TABLE IF NOT EXISTS decisions (
                  id TEXT PRIMARY KEY, session_id TEXT NOT NULL, created_at TEXT NOT NULL,
                  status TEXT NOT NULL, evidence_json TEXT NOT NULL, note TEXT NOT NULL,
                  FOREIGN KEY(session_id) REFERENCES sessions(id))''')
                con.execute('''CREATE TABLE IF NOT EXISTS chain_sessions (
                  chain_id TEXT PRIMARY KEY, created_at TEXT NOT NULL, original_objective TEXT NOT NULL,
                  current_stage INTEGER NOT NULL, status TEXT NOT NULL)''')
                con.execute('''CREATE TABLE IF NOT EXISTS chain_memory (
                  id INTEGER PRIMARY KEY AUTOINCREMENT, chain_id TEXT NOT NULL, stage INTEGER NOT NULL,
                  field_name TEXT NOT NULL, field_value TEXT NOT NULL,
                  FOREIGN KEY(chain_id) REFERENCES chain_sessions(chain_id))''')
                con.execute('''CREATE TABLE IF NOT EXISTS lottery_used_combinations (
                  catalog_fingerprint TEXT NOT NULL,
                  combo_key TEXT NOT NULL,
                  first_seen_at TEXT NOT NULL,
                  run_id TEXT NOT NULL,
                  mode TEXT NOT NULL,
                  seed INTEGER,
                  PRIMARY KEY (catalog_fingerprint, combo_key))''')
        finally:
            con.close()

    def save(self, query: str, packet: Mapping[str, Any], config: Mapping[str, Any]) -> str:
        ident = str(packet["activation_id"])
        now = str(packet["timestamp"])
        digest = hashlib.sha256(query.encode("utf-8")).hexdigest()
        con = self.connect()
        try:
            with con:
                con.execute("INSERT INTO sessions VALUES(?,?,?,?,?,?,?,?,?)", (ident, now, digest, query, packet["selected_current"]["id"], "ACTIVATED", json.dumps(config, ensure_ascii=False), json.dumps(packet, ensure_ascii=False), "[]"))
            return ident
        finally:
            con.close()

    def get(self, ident: str) -> dict[str, Any]:
        con = self.connect()
        try:
            row = con.execute("SELECT * FROM sessions WHERE id=?", (ident,)).fetchone()
            if not row:
                raise ValueError(f"Sesión inexistente: {ident}")
            result: dict[str, Any] = {str(key): row[key] for key in row.keys()}
            for key in ("config_json", "packet_json", "evidence_json"):
                result[key[:-5]] = json.loads(result.pop(key))
            return result
        finally:
            con.close()

    def list_sessions(self, limit: int = 100) -> list[dict[str, Any]]:
        con = self.connect()
        try:
            rows = con.execute("SELECT id,created_at,query,current_id,status FROM sessions ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
            return [{str(key): row[key] for key in row.keys()} for row in rows]
        finally:
            con.close()

    def record_decision(self, session_id: str, status: str, evidence: list[Any] | dict[str, Any], note: str = "") -> dict[str, Any]:
        if status not in VALID_DECISIONS:
            raise ValueError("Estado de decisión inválido.")
        entry: dict[str, Any] = {"id": str(uuid.uuid4()), "session_id": session_id, "timestamp": datetime.now(timezone.utc).isoformat(), "status": status, "evidence": evidence, "note": note}
        con = self.connect()
        try:
            with con:
                if not con.execute("SELECT 1 FROM sessions WHERE id=?", (session_id,)).fetchone():
                    raise ValueError(f"Sesión inexistente: {session_id}")
                con.execute("INSERT INTO decisions VALUES(?,?,?,?,?,?)", (entry["id"], session_id, entry["timestamp"], status, json.dumps(evidence, ensure_ascii=False), note))
                con.execute("UPDATE sessions SET status=?, evidence_json=? WHERE id=?", (status, json.dumps([entry], ensure_ascii=False), session_id))
            return entry
        finally:
            con.close()

    def compare(self, a: str, b: str) -> dict[str, Any]:
        left, right = self.get(a), self.get(b)
        lp, rp = left["packet"], right["packet"]
        return {"session_a": a, "session_b": b, "same_query_hash": left["query_hash"] == right["query_hash"], "currents": {"a": lp["selected_current"]["id"], "b": rp["selected_current"]["id"]}, "methods": {"a": [x["id"] for x in lp["supporting_methods"]], "b": [x["id"] for x in rp["supporting_methods"]]}, "decisions": {"a": lp["decision"], "b": rp["decision"]}}

    def save_chain_session(self, chain_id: str, original_objective: str, current_stage: int, status: str) -> None:
        now = str(datetime.now(timezone.utc).isoformat())
        con = self.connect()
        try:
            with con:
                con.execute(
                    "INSERT OR REPLACE INTO chain_sessions VALUES(?,?,?,?,?)",
                    (chain_id, now, original_objective, current_stage, status),
                )
        finally:
            con.close()

    def save_chain_memory(self, chain_id: str, stage: int, memory: Mapping[str, Any]) -> None:
        con = self.connect()
        try:
            with con:
                for field_name, value in memory.items():
                    if isinstance(value, (list, dict)):
                        field_value = json.dumps(value, ensure_ascii=False)
                    else:
                        field_value = str(value)
                    con.execute(
                        "INSERT INTO chain_memory(chain_id, stage, field_name, field_value) VALUES(?,?,?,?)",
                        (chain_id, stage, field_name, field_value),
                    )
        finally:
            con.close()

    def load_chain_session(self, chain_id: str) -> dict[str, Any]:
        con = self.connect()
        try:
            row = con.execute("SELECT * FROM chain_sessions WHERE chain_id=?", (chain_id,)).fetchone()
            if not row:
                raise ValueError(f"Chain inexistente: {chain_id}")
            return {k: row[k] for k in row.keys()}
        finally:
            con.close()

    def load_chain_memory(self, chain_id: str) -> list[dict[str, Any]]:
        con = self.connect()
        try:
            rows = con.execute(
                "SELECT id, chain_id, stage, field_name, field_value FROM chain_memory WHERE chain_id=? ORDER BY stage, id",
                (chain_id,),
            ).fetchall()
            return [{k: row[k] for k in row.keys()} for row in rows]
        finally:
            con.close()

    def save_lottery_combinations(
        self,
        catalog_fingerprint: str,
        combinations_list: Sequence[tuple[str, str]],
        run_id: str = "lottery-run",
        mode: str = "alternating",
        seed: int | None = None,
    ) -> int:
        """Persist used method pairs to SQLite for cross-session deduplication."""
        now = datetime.now(timezone.utc).isoformat()
        saved = 0
        con = self.connect()
        try:
            with con:
                for left, right in combinations_list:
                    combo_key = f"{min(str(left), str(right))}::{max(str(left), str(right))}"
                    try:
                        con.execute(
                            "INSERT OR IGNORE INTO lottery_used_combinations VALUES(?,?,?,?,?,?)",
                            (catalog_fingerprint, combo_key, now, run_id, mode, seed),
                        )
                        saved += 1
                    except sqlite3.IntegrityError:
                        pass
            return saved
        finally:
            con.close()

    def load_used_lottery_combinations(self, catalog_fingerprint: str) -> set[tuple[str, str]]:
        """Load all historically used method pairs for this catalog fingerprint."""
        con = self.connect()
        try:
            rows = con.execute(
                "SELECT combo_key FROM lottery_used_combinations WHERE catalog_fingerprint=?",
                (catalog_fingerprint,),
            ).fetchall()
            combos: set[tuple[str, str]] = set()
            for r in rows:
                parts = str(r[0]).split("::")
                if len(parts) == 2:
                    combos.add((parts[0], parts[1]))
            return combos
        finally:
            con.close()
