"""MCP JSON-RPC transport and dispatch regression tests."""
from __future__ import annotations

import io
import json

import pytest

from criba.mcp_server import call, run_stdio
from criba.storage import Storage

QUERY = "Evaluar de forma reversible un flujo de aprobación"


def test_call_activates_and_persists_packet(tmp_path) -> None:
    store = Storage(tmp_path / "mcp.sqlite3")
    packet = call("activate_current", {"query": QUERY}, store)

    assert packet["packet_type"] == "MANDATORY_MODEL_PACKET"
    assert store.get(packet["activation_id"])["packet"]["activation_id"] == packet["activation_id"]


@pytest.mark.parametrize("name,args,match", [
    ("activate_current", {"query": ""}, "query"),
    ("activate_current", {"query": QUERY, "supporting_methods": True}, "entero"),
    ("activate_current", {"query": QUERY, "context": []}, "context"),
    ("record_decision", {"session_id": "missing", "status": "ADOPTAR", "evidence": "bad"}, "evidence"),
    ("unknown", {}, "inexistente"),
])
def test_call_rejects_malformed_tool_arguments(tmp_path, name, args, match) -> None:
    with pytest.raises(ValueError, match=match):
        call(name, args, Storage(tmp_path / "invalid.sqlite3"))


def test_stdio_emits_error_then_continues(monkeypatch, capsys, tmp_path) -> None:
    requests = [
        [],
        {"jsonrpc": "2.0", "id": 2, "method": "initialize"},
    ]
    monkeypatch.setattr(
        "sys.stdin",
        io.StringIO("".join(json.dumps(item) + "\n" for item in requests)),
    )

    run_stdio(tmp_path / "stdio.sqlite3")

    responses = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert responses[0]["error"]["code"] == -32000
    assert responses[1]["id"] == 2
    assert responses[1]["result"]["protocolVersion"] == "2024-11-05"
