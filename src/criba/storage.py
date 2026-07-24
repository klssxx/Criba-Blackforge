from __future__ import annotations
import hashlib, json, sqlite3, uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping
from .constants import DEFAULT_DB, CURRENT_CATALOG_VERSION, SELECTOR_VERSION
from .constants import VALID_DECISIONS

class Storage:
    def __init__(self, path: Path | str | None = DEFAULT_DB) -> None:
        self.path=Path(path or DEFAULT_DB); self.path.parent.mkdir(parents=True, exist_ok=True); self.initialize()
    def connect(self) -> sqlite3.Connection:
        con=sqlite3.connect(self.path, timeout=3); con.row_factory=sqlite3.Row; return con
    def initialize(self) -> None:
        with self.connect() as con:
            con.execute('''CREATE TABLE IF NOT EXISTS sessions (
              id TEXT PRIMARY KEY, created_at TEXT NOT NULL, query_hash TEXT NOT NULL,
              query TEXT NOT NULL, current_id TEXT NOT NULL, status TEXT NOT NULL,
              config_json TEXT NOT NULL, packet_json TEXT NOT NULL, evidence_json TEXT NOT NULL DEFAULT '[]')''')
            con.execute('''CREATE TABLE IF NOT EXISTS decisions (
              id TEXT PRIMARY KEY, session_id TEXT NOT NULL, created_at TEXT NOT NULL,
              status TEXT NOT NULL, evidence_json TEXT NOT NULL, note TEXT NOT NULL,
              FOREIGN KEY(session_id) REFERENCES sessions(id))''')
    def save(self, query: str, packet: Mapping[str, Any], config: Mapping[str, Any]) -> str:
        ident=str(packet["activation_id"]); now=str(packet["timestamp"])
        digest=hashlib.sha256(query.encode("utf-8")).hexdigest()
        with self.connect() as con:
            con.execute("INSERT INTO sessions VALUES(?,?,?,?,?,?,?,?,?)",(ident,now,digest,query,packet["selected_current"]["id"],"ACTIVATED",json.dumps(config,ensure_ascii=False),json.dumps(packet,ensure_ascii=False),"[]"))
        return ident
    def get(self, ident: str) -> dict[str, Any]:
        with self.connect() as con: row=con.execute("SELECT * FROM sessions WHERE id=?",(ident,)).fetchone()
        if not row: raise ValueError(f"Sesión inexistente: {ident}")
        result: dict[str, Any] = {str(key): row[key] for key in row.keys()}
        for key in ("config_json","packet_json","evidence_json"): result[key[:-5]]=json.loads(result.pop(key))
        return result
    def list_sessions(self, limit: int=100) -> list[dict[str, Any]]:
        with self.connect() as con: rows=con.execute("SELECT id,created_at,query,current_id,status FROM sessions ORDER BY created_at DESC LIMIT ?",(limit,)).fetchall()
        return [{str(key): row[key] for key in row.keys()} for row in rows]
    def record_decision(self, session_id: str, status: str, evidence: list[Any] | dict[str, Any], note: str = "") -> dict[str, Any]:
        if status not in VALID_DECISIONS: raise ValueError("Estado de decisión inválido.")
        entry: dict[str, Any] = {"id":str(uuid.uuid4()),"session_id":session_id,"timestamp":datetime.now(timezone.utc).isoformat(),"status":status,"evidence":evidence,"note":note}
        with self.connect() as con:
            if not con.execute("SELECT 1 FROM sessions WHERE id=?",(session_id,)).fetchone(): raise ValueError(f"Sesión inexistente: {session_id}")
            con.execute("INSERT INTO decisions VALUES(?,?,?,?,?,?)",(entry["id"],session_id,entry["timestamp"],status,json.dumps(evidence,ensure_ascii=False),note))
            con.execute("UPDATE sessions SET status=?, evidence_json=? WHERE id=?",(status,json.dumps([entry],ensure_ascii=False),session_id))
        return entry
    def compare(self, a: str, b: str) -> dict[str, Any]:
        left,right=self.get(a),self.get(b); lp,rp=left["packet"],right["packet"]
        return {"session_a":a,"session_b":b,"same_query_hash":left["query_hash"]==right["query_hash"],"currents":{"a":lp["selected_current"]["id"],"b":rp["selected_current"]["id"]},"methods":{"a":[x["id"] for x in lp["supporting_methods"]],"b":[x["id"] for x in rp["supporting_methods"]]},"decisions":{"a":lp["decision"],"b":rp["decision"]}}
