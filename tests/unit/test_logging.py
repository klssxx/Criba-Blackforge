"""Tests for the logging and traceability layer (HIPERMEGAPROMPT §11)."""
from __future__ import annotations

from pathlib import Path

import pytest

from criba.logging import (
    _SENSITIVE_KEYS,
    EventCategory,
    LogEmitter,
    LogProfile,
    LogReconstructor,
    _redact,
)
from criba.storage import Storage


@pytest.fixture
def tmp_storage(tmp_path: Path) -> Storage:
    return Storage(tmp_path / "test.sqlite3")


@pytest.fixture
def emitter(tmp_storage: Storage) -> LogEmitter:
    return LogEmitter(tmp_storage, profile=LogProfile.STANDARD)


class TestRedaction:
    def test_redacts_api_key(self) -> None:
        assert _redact({"api_key": "secret123"}) == {"api_key": "[REDACTED]"}

    def test_redacts_password(self) -> None:
        assert _redact({"password": "hunter2"}) == {"password": "[REDACTED]"}

    def test_redacts_token(self) -> None:
        assert _redact({"token": "abc"}) == {"token": "[REDACTED]"}

    def test_redacts_nested_secret(self) -> None:
        payload = {"config": {"api_key": "secret", "name": "ok"}}
        result = _redact(payload)
        assert result["config"]["api_key"] == "[REDACTED]"
        assert result["config"]["name"] == "ok"

    def test_redacts_list_of_dicts(self) -> None:
        payload = [{"api_key": "a"}, {"api_key": "b"}]
        result = _redact(payload)
        assert result == [{"api_key": "[REDACTED]"}, {"api_key": "[REDACTED]"}]

    def test_allows_safe_fields(self) -> None:
        payload = {"event_type": "Test", "count": 42}
        assert _redact(payload) == payload

    def test_all_sensitive_keys_covered(self) -> None:
        for key in _SENSITIVE_KEYS:
            result = _redact({key: "value"})
            assert result[key] == "[REDACTED]", f"Key {key} not redacted"


class TestEmit:
    def test_emit_returns_event_with_hash(self, emitter: LogEmitter) -> None:
        ev = emitter.emit(event_type="TestEvent", payload={"x": 1})
        assert ev["event_id"]
        assert ev["event_hash"]
        assert ev["sequence_number"] == 1
        assert ev["previous_event_hash"] == ""

    def test_emit_increments_sequence(self, emitter: LogEmitter) -> None:
        e1 = emitter.emit(event_type="E1")
        e2 = emitter.emit(event_type="E2")
        assert e2["sequence_number"] == e1["sequence_number"] + 1

    def test_hash_chain_links_events(self, emitter: LogEmitter) -> None:
        e1 = emitter.emit(event_type="E1")
        e2 = emitter.emit(event_type="E2")
        assert e2["previous_event_hash"] == e1["event_hash"]

    def test_emit_redacts_by_default(self, tmp_storage: Storage) -> None:
        emitter = LogEmitter(tmp_storage, redact=True)
        ev = emitter.emit(event_type="Test", payload={"api_key": "secret"})
        assert ev["payload"]["api_key"] == "[REDACTED]"

    def test_emit_no_redact_flag(self, tmp_storage: Storage) -> None:
        emitter = LogEmitter(tmp_storage, redact=False)
        ev = emitter.emit(event_type="Test", payload={"api_key": "secret"})
        assert ev["payload"]["api_key"] == "secret"

    def test_emit_with_all_fields(self, emitter: LogEmitter) -> None:
        ev = emitter.emit(
            event_type="PersonaRunCompleted",
            category=EventCategory.EVENT,
            payload={"result": "ok"},
            chain_id="chain-1",
            stage_id="stage-2",
            context_id="ctx-3",
            task_id="task-4",
            persona_id="A",
            severity="info",
            evidence_refs=["ev-1", "ev-2"],
        )
        assert ev["chain_id"] == "chain-1"
        assert ev["stage_id"] == "stage-2"
        assert ev["context_id"] == "ctx-3"
        assert ev["task_id"] == "task-4"
        assert ev["persona_id"] == "A"
        assert ev["evidence_refs"] == ["ev-1", "ev-2"]

    def test_emit_audit_category(self, emitter: LogEmitter) -> None:
        ev = emitter.emit(
            event_type="AuthorizationChecked",
            category=EventCategory.AUDIT,
            payload={"user": "moli", "action": "run"},
        )
        assert ev["category"] == "audit"

    def test_emit_security_category(self, emitter: LogEmitter) -> None:
        ev = emitter.emit(
            event_type="ToolBlocked",
            category=EventCategory.SECURITY,
            payload={"tool": "metasploit"},
        )
        assert ev["category"] == "security"

    def test_emit_model_interaction(self, emitter: LogEmitter) -> None:
        ev = emitter.emit(
            event_type="ModelCall",
            category=EventCategory.MODEL_INTERACTION,
            payload={"model": "gpt-4", "tokens": 150},
        )
        assert ev["category"] == "model_interaction"

    def test_correlation_marker(self, emitter: LogEmitter) -> None:
        ev = emitter.correlate(chain_id="c1", stage_id="s1")
        assert ev["event_type"] == "correlation_marker"
        assert ev["chain_id"] == "c1"
        assert ev["stage_id"] == "s1"


class TestReconstructor:
    def test_read_stream_order(self, emitter: LogEmitter) -> None:
        emitter.emit(event_type="E1")
        emitter.emit(event_type="E2")
        emitter.emit(event_type="E3")
        recon = LogReconstructor(emitter._storage)
        events = recon.read_stream(emitter.session_id)
        assert len(events) == 3
        assert [e["event_type"] for e in events] == ["E1", "E2", "E3"]

    def test_verify_chain_intact(self, emitter: LogEmitter) -> None:
        for i in range(5):
            emitter.emit(event_type=f"E{i}")
        recon = LogReconstructor(emitter._storage)
        report = recon.verify_chain(emitter.session_id)
        assert report["chain_intact"] is True
        assert report["event_count"] == 5
        assert report["broken_at_sequences"] == []

    def test_verify_chain_empty_stream(self, tmp_storage: Storage) -> None:
        recon = LogReconstructor(tmp_storage)
        # No events emitted — create a session manually
        emitter = LogEmitter(tmp_storage, session_id="empty-session")
        report = recon.verify_chain("empty-session")
        assert report["chain_intact"] is True
        assert report["event_count"] == 0

    def test_reconstruct_extracts_metadata(self, emitter: LogEmitter) -> None:
        emitter.emit(
            event_type="ContextCreated",
            context_id="ctx-1",
            task_id="task-1",
            chain_id="chain-1",
            stage_id="stage-1",
        )
        emitter.emit(
            event_type="PersonaRunCompleted",
            persona_id="A",
            payload={"result": "ok"},
        )
        emitter.emit(
            event_type="DecisionFrozen",
            payload={"decision": "ADOPTAR"},
        )
        recon = LogReconstructor(emitter.session_id)
        # Use the reconstructor bound to the same storage
        recon = LogReconstructor(emitter._storage)
        summary = recon.reconstruct(emitter.session_id)
        assert summary["session_id"] == emitter.session_id
        assert summary["event_count"] == 3
        assert "ctx-1" in summary["context_ids"]
        assert "task-1" in summary["task_ids"]
        assert "chain-1" in summary["chain_ids"]
        assert "stage-1" in summary["stages"]
        assert "A" in summary["personas"]
        assert len(summary["decisions"]) == 1

    def test_export_canonical(self, emitter: LogEmitter) -> None:
        emitter.emit(event_type="TestEvent", payload={"k": "v"})
        recon = LogReconstructor(emitter._storage)
        export = recon.export_canonical(emitter.session_id)
        assert export["schema_version"] == "1.0.0"
        assert export["session_id"] == emitter.session_id
        assert export["event_count"] == 1
        assert export["integrity"]["chain_intact"] is True
        assert export["redactions_applied"] is True
        assert "exported_at" in export


class TestPersistence:
    def test_survives_restart(self, tmp_path: Path) -> None:
        db_path = tmp_path / "persist.sqlite3"
        storage = Storage(db_path)
        emitter = LogEmitter(storage, session_id="persist-test")
        emitter.emit(event_type="E1", payload={"x": 1})
        emitter.emit(event_id="E2", payload={"x": 2}) if False else emitter.emit(event_type="E2", payload={"x": 2})

        # Reopen same DB
        storage2 = Storage(db_path)
        recon = LogReconstructor(storage2)
        events = recon.read_stream("persist-test")
        assert len(events) == 2
        assert events[0]["event_type"] == "E1"
        assert events[1]["event_type"] == "E2"

    def test_multiple_streams_isolated(self, tmp_storage: Storage) -> None:
        e1 = LogEmitter(tmp_storage, session_id="s1")
        e2 = LogEmitter(tmp_storage, session_id="s2")
        e1.emit(event_type="E1")
        e2.emit(event_type="E2")
        recon = LogReconstructor(tmp_storage)
        assert len(recon.read_stream("s1")) == 1
        assert len(recon.read_stream("s2")) == 1
        assert recon.read_stream("s1")[0]["event_type"] == "E1"
        assert recon.read_stream("s2")[0]["event_type"] == "E2"


class TestStreamMetadata:
    def test_event_count_updated(self, emitter: LogEmitter) -> None:
        emitter.emit(event_type="E1")
        emitter.emit(event_type="E2")
        with emitter._storage.connect() as con:
            row = con.execute(
                "SELECT event_count, head_hash FROM log_streams WHERE session_id = ?",
                (emitter.session_id,),
            ).fetchone()
        assert row["event_count"] == 2
        assert row["head_hash"] == emitter._last_hash

    def test_head_hash_matches_last_event(self, emitter: LogEmitter) -> None:
        for _ in range(3):
            emitter.emit(event_type="E")
        with emitter._storage.connect() as con:
            row = con.execute(
                "SELECT head_hash FROM log_streams WHERE session_id = ?",
                (emitter.session_id,),
            ).fetchone()
        assert row["head_hash"] == emitter._last_hash
