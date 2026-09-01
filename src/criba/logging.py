"""Logging and traceability layer (HIPERMEGAPROMPT §11).

Append-only, hash-chained event log with:
- Five event types: event, audit, operational, security, model_interaction.
- Correlation via chain_id / stage_id / context_id / task_id.
- Integrity: SHA-256 hash chain (previous_event_hash + canonical event).
- Minimization: secrets redacted before persistence.
- Cold reconstruction: rebuild session state from the event stream.

Persistence reuses ``storage.Storage`` (SQLite) so logs survive restarts
and share the same durable store as sessions and decisions.
"""
from __future__ import annotations

import hashlib
import json
import uuid
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from .blackforge_causal import canonical_json
from .storage import Storage

SCHEMA_VERSION = "1.0.0"

# Fields that must NEVER appear in plaintext (§11.6).
_SENSITIVE_KEYS = frozenset({
    "api_key", "apikey", "password", "secret", "token", "cookie",
    "cookies", "authorization", "credential", "private_key",
    "passphrase", "client_secret", "access_token", "refresh_token",
})


class EventCategory(str, Enum):
    EVENT = "event"
    AUDIT = "audit"
    OPERATIONAL = "operational"
    SECURITY = "security"
    MODEL_INTERACTION = "model_interaction"


class LogProfile(str, Enum):
    MINIMAL = "minimal"
    STANDARD = "standard"
    FORENSIC = "forensic"
    REGULATED = "regulated"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _redact_value(key: str, value: Any) -> Any:
    """Mask a sensitive field; recurse into dicts/lists."""
    if isinstance(key, str) and key.lower() in _SENSITIVE_KEYS:
        return "[REDACTED]"
    if isinstance(value, dict):
        return {k: _redact_value(k, v) for k, v in value.items()}
    if isinstance(value, list):
        # Use positional index as key (won't match sensitive keys, recurses fine).
        return [_redact_value(str(i), v) for i, v in enumerate(value)]
    return value


def _redact(payload: Any) -> Any:
    """Redact sensitive fields from any payload (dict, list, scalar)."""
    return _redact_value("", payload)


def _compute_event_hash(event: Mapping[str, Any], previous_hash: str) -> str:
    """SHA-256 of canonical event + previous hash (§11.5)."""
    canonical = canonical_json(event) + previous_hash
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class LogEmitter:
    """Append-only event emitter backed by ``storage.Storage``.

    Each emitter owns one ``session_id`` (the log stream). All events written
    through a single emitter form a hash chain that can be verified later.
    """

    def __init__(
        self,
        storage: Storage,
        *,
        session_id: str | None = None,
        profile: LogProfile = LogProfile.STANDARD,
        redact: bool = True,
    ) -> None:
        self._storage = storage
        self.session_id = session_id or str(uuid.uuid4())
        self.profile = profile
        self._redact = redact
        self._sequence = 0
        self._last_hash = ""
        self._initialize_stream()

    def _initialize_stream(self) -> None:
        """Create the log stream record if it does not exist."""
        with self._storage.connect() as con:
            con.execute(
                """CREATE TABLE IF NOT EXISTS log_streams (
                  session_id TEXT PRIMARY KEY,
                  created_at TEXT NOT NULL,
                  profile TEXT NOT NULL,
                  event_count INTEGER NOT NULL DEFAULT 0,
                  head_hash TEXT NOT NULL DEFAULT ''
                )"""
            )
            con.execute(
                """CREATE TABLE IF NOT EXISTS log_events (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  session_id TEXT NOT NULL,
                  sequence_number INTEGER NOT NULL,
                  event_id TEXT NOT NULL UNIQUE,
                  event_type TEXT NOT NULL,
                  category TEXT NOT NULL,
                  timestamp_utc TEXT NOT NULL,
                  correlation_id TEXT,
                  causation_id TEXT,
                  chain_id TEXT,
                  stage_id TEXT,
                  context_id TEXT,
                  task_id TEXT,
                  persona_id TEXT,
                  user_id_pseudonymous TEXT,
                  authorization_id TEXT,
                  severity TEXT,
                  payload TEXT NOT NULL,
                  evidence_refs TEXT NOT NULL DEFAULT '[]',
                  previous_event_hash TEXT NOT NULL,
                  event_hash TEXT NOT NULL,
                  schema_version TEXT NOT NULL,
                  FOREIGN KEY(session_id) REFERENCES log_streams(session_id)
                )"""
            )
            existing = con.execute(
                "SELECT 1 FROM log_streams WHERE session_id = ?", (self.session_id,)
            ).fetchone()
            if not existing:
                con.execute(
                    "INSERT INTO log_streams VALUES (?, ?, ?, 0, '')",
                    (self.session_id, _now_iso(), self.profile.value),
                )

    def _persist(self, event: dict[str, Any], event_hash: str) -> dict[str, Any]:
        with self._storage.connect() as con:
            con.execute(
                """INSERT INTO log_events (
                  session_id, sequence_number, event_id, event_type, category,
                  timestamp_utc, correlation_id, causation_id, chain_id, stage_id,
                  context_id, task_id, persona_id, user_id_pseudonymous,
                  authorization_id, severity, payload, evidence_refs,
                  previous_event_hash, event_hash, schema_version
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    self.session_id,
                    event["sequence_number"],
                    event["event_id"],
                    event["event_type"],
                    event["category"],
                    event["timestamp_utc"],
                    event.get("correlation_id"),
                    event.get("causation_id"),
                    event.get("chain_id"),
                    event.get("stage_id"),
                    event.get("context_id"),
                    event.get("task_id"),
                    event.get("persona_id"),
                    event.get("user_id_pseudonymous"),
                    event.get("authorization_id"),
                    event.get("severity"),
                    json.dumps(event["payload"], ensure_ascii=False),
                    json.dumps(event.get("evidence_refs", []), ensure_ascii=False),
                    event["previous_event_hash"],
                    event_hash,
                    SCHEMA_VERSION,
                ),
            )
            con.execute(
                """UPDATE log_streams SET event_count = ?, head_hash = ?
                  WHERE session_id = ?""",
                (self._sequence, event_hash, self.session_id),
            )
        return event

    def emit(
        self,
        *,
        event_type: str,
        category: EventCategory = EventCategory.EVENT,
        payload: Mapping[str, Any] | None = None,
        correlation_id: str | None = None,
        causation_id: str | None = None,
        chain_id: str | None = None,
        stage_id: str | None = None,
        context_id: str | None = None,
        task_id: str | None = None,
        persona_id: str | None = None,
        user_id_pseudonymous: str | None = None,
        authorization_id: str | None = None,
        severity: str = "info",
        evidence_refs: Sequence[str] | None = None,
    ) -> dict[str, Any]:
        """Append one event to the stream and return the stored record."""
        self._sequence += 1
        payload_clean = dict(payload or {})
        if self._redact:
            payload_clean = _redact(payload_clean)

        event: dict[str, Any] = {
            "event_id": str(uuid.uuid4()),
            "event_type": event_type,
            "category": category.value,
            "schema_version": SCHEMA_VERSION,
            "timestamp_utc": _utc_timestamp(),
            "sequence_number": self._sequence,
            "correlation_id": correlation_id or self.session_id,
            "causation_id": causation_id,
            "chain_id": chain_id,
            "stage_id": stage_id,
            "context_id": context_id,
            "task_id": task_id,
            "persona_id": persona_id,
            "user_id_pseudonymous": user_id_pseudonymous,
            "authorization_id": authorization_id,
            "severity": severity,
            "payload": payload_clean,
            "evidence_refs": list(evidence_refs or []),
            "previous_event_hash": self._last_hash,
            "event_hash": "",
        }
        event_hash = _compute_event_hash(event, self._last_hash)
        event["event_hash"] = event_hash
        self._last_hash = event_hash
        return self._persist(event, event_hash)

    def correlate(self, chain_id: str, stage_id: str) -> dict[str, Any]:
        """Emit a correlation marker (§11.4)."""
        return self.emit(
            event_type="correlation_marker",
            category=EventCategory.EVENT,
            payload={"chain_id": chain_id, "stage_id": stage_id},
            chain_id=chain_id,
            stage_id=stage_id,
        )


class LogReconstructor:
    """Cold-reconstruct a session from its event stream (§11.11)."""

    def __init__(self, storage: Storage) -> None:
        self._storage = storage

    def read_stream(self, session_id: str) -> list[dict[str, Any]]:
        """Return events in sequence order with payloads parsed."""
        with self._storage.connect() as con:
            rows = con.execute(
                """SELECT session_id, sequence_number, event_id, event_type,
                  category, timestamp_utc, correlation_id, causation_id,
                  chain_id, stage_id, context_id, task_id, persona_id,
                  user_id_pseudonymous, authorization_id, severity, payload,
                  evidence_refs, previous_event_hash, event_hash, schema_version
                FROM log_events WHERE session_id = ?
                ORDER BY sequence_number ASC""",
                (session_id,),
            ).fetchall()
        events = []
        for row in rows:
            d = {k: row[k] for k in row.keys()}
            d["payload"] = json.loads(d["payload"])
            d["evidence_refs"] = json.loads(d["evidence_refs"])
            events.append(d)
        return events

    def verify_chain(self, session_id: str) -> dict[str, Any]:
        """Verify hash integrity of the whole stream (§11.5)."""
        events = self.read_stream(session_id)
        previous_hash = ""
        broken_at: list[int] = []
        for ev in events:
            expected = _compute_event_hash(
                {
                    "event_id": ev["event_id"],
                    "event_type": ev["event_type"],
                    "category": ev["category"],
                    "schema_version": ev["schema_version"],
                    "timestamp_utc": ev["timestamp_utc"],
                    "sequence_number": ev["sequence_number"],
                    "correlation_id": ev["correlation_id"],
                    "causation_id": ev["causation_id"],
                    "chain_id": ev["chain_id"],
                    "stage_id": ev["stage_id"],
                    "context_id": ev["context_id"],
                    "task_id": ev["task_id"],
                    "persona_id": ev["persona_id"],
                    "user_id_pseudonymous": ev["user_id_pseudonymous"],
                    "authorization_id": ev["authorization_id"],
                    "severity": ev["severity"],
                    "payload": ev["payload"],
                    "evidence_refs": ev["evidence_refs"],
                    "previous_event_hash": previous_hash,
                    "event_hash": "",
                },
                previous_hash,
            )
            if expected != ev["event_hash"]:
                broken_at.append(ev["sequence_number"])
            previous_hash = ev["event_hash"]
        return {
            "session_id": session_id,
            "event_count": len(events),
            "chain_intact": not broken_at,
            "broken_at_sequences": broken_at,
        }

    def reconstruct(self, session_id: str) -> dict[str, Any]:
        """Build a session summary from events (§11.11)."""
        events = self.read_stream(session_id)
        context_ids: list[str] = []
        task_ids: list[str] = []
        chain_ids: list[str] = []
        stages: list[str] = []
        personas: list[str] = []
        decisions: list[dict[str, Any]] = []
        findings: list[dict[str, Any]] = []
        for ev in events:
            payload = ev.get("payload", {})
            if ev.get("context_id") and ev["context_id"] not in context_ids:
                context_ids.append(ev["context_id"])
            if ev.get("task_id") and ev["task_id"] not in task_ids:
                task_ids.append(ev["task_id"])
            if ev.get("chain_id") and ev["chain_id"] not in chain_ids:
                chain_ids.append(ev["chain_id"])
            if ev.get("stage_id") and ev["stage_id"] not in stages:
                stages.append(ev["stage_id"])
            if ev.get("persona_id") and ev["persona_id"] not in personas:
                personas.append(ev["persona_id"])
            if ev["event_type"] in ("DecisionFrozen", "StageApproved"):
                decisions.append(payload)
            if ev["event_type"] == "FindingCreated":
                findings.append(payload)
        return {
            "session_id": session_id,
            "event_count": len(events),
            "context_ids": context_ids,
            "task_ids": task_ids,
            "chain_ids": chain_ids,
            "stages": stages,
            "personas": personas,
            "decisions": decisions,
            "findings": findings,
        }

    def export_canonical(self, session_id: str) -> dict[str, Any]:
        """Export a canonical JSON report (§11.12)."""
        events = self.read_stream(session_id)
        integrity = self.verify_chain(session_id)
        return {
            "schema_version": SCHEMA_VERSION,
            "session_id": session_id,
            "event_count": len(events),
            "integrity": integrity,
            "events": events,
            "exported_at": _utc_timestamp(),
            "redactions_applied": True,
        }
