"""Registro auditable de veredictos del interprete-serendipia.

Extiende el Storage base (src/criba/storage.py) con una tabla
``interprete_decisions`` que vincula cada veredicto a:
- activation_id (sesión CRIBA origen)
- idea_id
- modelo que interpretó
- labels epistemológicos emitidos
- score epistemológico 0-1
- veredicto cualitativo
- respuesta completa (JSON)

Reproducibilidad: MISMA comb_id + MISMO seed + MISMO modelo → MISMO veredicto.
Dedup cross-session garantizada por combo_key + run_id + seed (PK).
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from criba.storage import Storage


_INTERPRETE_SCHEMA = """
CREATE TABLE IF NOT EXISTS interprete_decisions (
    combo_key TEXT NOT NULL,
    run_id TEXT NOT NULL,
    seed INTEGER,
    activation_id TEXT NOT NULL,
    idea_id TEXT NOT NULL,
    modelo TEXT NOT NULL,
    labels_json TEXT NOT NULL,
    epistemic_score REAL NOT NULL,
    veredicto TEXT NOT NULL,
    response_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (combo_key, run_id, seed)
)
"""


class InterpreteStore:
    """Wrap de Storage para decisiones del interprete. Reutiliza la conexión
    de Storage para consistencia transaccional."""

    def __init__(self, storage: Storage) -> None:
        self._storage = storage
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        con = self._storage.connect()
        try:
            with con:
                con.execute(_INTERPRETE_SCHEMA)
        finally:
            con.close()

    @staticmethod
    def _combo_key(idea_id: str, modelo: str) -> str:
        return f"{idea_id}::{modelo}"

    def record_decision(
        self,
        activation_id: str,
        idea: dict[str, Any],
        modelo: str,
        run_id: str,
        seed: int | None,
    ) -> dict[str, Any]:
        """Registra (UPSERT) un veredicto. Si ya existe con misma seed/run,
        devuelve el previo (deduplicación determinista)."""
        idea_id = idea["id"]
        combo_key = self._combo_key(idea_id, modelo)
        now = datetime.now(timezone.utc).isoformat()
        labels = idea.get("interprete_labels", [])
        score = float(idea.get("interprete_score", 0.0))
        verdict = idea.get("interprete_verdict", "PENDIENTE")
        response = {k: v for k, v in idea.items() if not k.startswith("interprete_")}

        con = self._storage.connect()
        try:
            existing = con.execute(
                "SELECT combo_key, run_id, seed, veredicto, epistemic_score, "
                "created_at FROM interprete_decisions WHERE combo_key=? AND run_id=? AND (seed=? OR seed IS NULL)",
                (combo_key, run_id, seed),
            ).fetchone()
            if existing:
                return {
                    "status": "deduplicated",
                    "combo_key": existing["combo_key"],
                    "modelo": modelo,
                    "veredicto_previo": existing["veredicto"],
                    "score_previo": existing["epistemic_score"],
                    "created_at": existing["created_at"],
                }

            with con:
                con.execute(
                    "INSERT INTO interprete_decisions "
                    "(combo_key, run_id, seed, activation_id, idea_id, modelo, "
                    " labels_json, epistemic_score, veredicto, response_json, created_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (combo_key, run_id, seed, activation_id, idea_id, modelo,
                     json.dumps(labels, ensure_ascii=False), score, verdict,
                     json.dumps(response, ensure_ascii=False), now),
                )
            return {
                "status": "recorded",
                "combo_key": combo_key,
                "modelo": modelo,
                "veredicto": verdict,
                "score": score,
                "created_at": now,
            }
        finally:
            con.close()

    def get_verdict(self, idea_id: str, modelo: str) -> dict[str, Any] | None:
        combo_key = self._combo_key(idea_id, modelo)
        con = self._storage.connect()
        try:
            row = con.execute(
                "SELECT combo_key, run_id, seed, activation_id, idea_id, modelo, "
                "labels_json, epistemic_score, veredicto, response_json, created_at "
                "FROM interprete_decisions WHERE combo_key=?",
                (combo_key,),
            ).fetchone()
            if not row:
                return None
            r = {k: row[k] for k in row.keys()}
            r["labels"] = json.loads(r.pop("labels_json"))
            r["response"] = json.loads(r.pop("response_json"))
            return r
        finally:
            con.close()
