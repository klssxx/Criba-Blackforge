"""MCP-compatible JSON-RPC stdio transport, with no network exposure."""
from __future__ import annotations

import json
import sqlite3
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .catalog import currents
from .engine import activate, build_prompt
from .selector import select
from .storage import Storage

JsonObject = dict[str, Any]

TOOLS: list[JsonObject] = [
    {"name": "activate_current", "description": "Activate CRIBA before a final model response.", "inputSchema": {"type": "object", "properties": {"query": {"type": "string"}, "current": {"type": "string", "default": "auto"}, "mode": {"type": "string", "default": "balanced"}, "supporting_methods": {"type": "integer", "default": 4}, "context": {"type": "object"}, "safety_level": {"type": "string", "default": "strict"}}, "required": ["query"]}},
    {"name": "list_currents", "description": "List current modules.", "inputSchema": {"type": "object", "properties": {}}},
    {"name": "explain_selection", "description": "Explain deterministic selection.", "inputSchema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}},
    {"name": "run_criba", "description": "Run and persist the CRIBA flow.", "inputSchema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}},
    {"name": "build_model_prompt", "description": "Build an enriched model prompt.", "inputSchema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}},
    {"name": "record_decision", "description": "Persist evidence and decision.", "inputSchema": {"type": "object", "properties": {"session_id": {"type": "string"}, "status": {"type": "string"}, "evidence": {}}, "required": ["session_id", "status"]}},
    {"name": "compare_runs", "description": "Compare two stored activations.", "inputSchema": {"type": "object", "properties": {"session_a": {"type": "string"}, "session_b": {"type": "string"}}, "required": ["session_a", "session_b"]}},
]


def _string_arg(args: Mapping[str, Any], name: str, default: str | None = None) -> str:
    value = args.get(name, default)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"argumento MCP '{name}' debe ser un string no vacío")
    return value


def _int_arg(args: Mapping[str, Any], name: str, default: int) -> int:
    value = args.get(name, default)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"argumento MCP '{name}' debe ser un entero")
    return value


def call(name: str, args: Mapping[str, Any], store: Storage) -> Any:
    """Execute one named MCP tool against a validated argument mapping."""
    if name == "list_currents":
        return currents()
    if name == "explain_selection":
        return select(_string_arg(args, "query"), _string_arg(args, "current", "auto"))
    if name in {"activate_current", "run_criba", "build_model_prompt"}:
        context = args.get("context")
        if context is not None and not isinstance(context, dict):
            raise ValueError("argumento MCP 'context' debe ser un objeto")
        packet = activate(
            query=_string_arg(args, "query"),
            current=_string_arg(args, "current", "auto"),
            mode=_string_arg(args, "mode", "balanced"),
            supporting_methods=_int_arg(args, "supporting_methods", 4),
            context=context,
            safety_level=_string_arg(args, "safety_level", "strict"),
        )
        store.save(str(packet["original_query"]), packet, args)
        return build_prompt(packet) if name == "build_model_prompt" else packet
    if name == "record_decision":
        evidence = args.get("evidence", [])
        if not isinstance(evidence, (list, dict)):
            raise ValueError("argumento MCP 'evidence' debe ser una lista u objeto")
        return store.record_decision(
            _string_arg(args, "session_id"),
            _string_arg(args, "status"),
            evidence,
            _string_arg(args, "note", "") if args.get("note") else "",
        )
    if name == "compare_runs":
        return store.compare(_string_arg(args, "session_a"), _string_arg(args, "session_b"))
    raise ValueError(f"Herramienta MCP inexistente: {name}")


def run_stdio(database: Path | str | None = None) -> None:
    """Serve JSON-RPC requests from stdin and emit one response per input line."""
    store = Storage(database)
    for line in sys.stdin:
        request: JsonObject = {}
        try:
            raw_request = json.loads(line)
            if not isinstance(raw_request, dict):
                raise ValueError("Solicitud JSON-RPC debe ser un objeto")
            request = raw_request
            method = request.get("method")
            if not isinstance(method, str):
                raise ValueError("Campo JSON-RPC 'method' debe ser un string")
            ident = request.get("id")
            result: Any
            if method == "initialize":
                result = {"protocolVersion": "2024-11-05", "serverInfo": {"name": "criba", "version": "0.2.0"}, "capabilities": {"tools": {}}}
            elif method == "tools/list":
                result = {"tools": TOOLS}
            elif method == "tools/call":
                params = request.get("params")
                if not isinstance(params, Mapping):
                    raise ValueError("Campo JSON-RPC 'params' debe ser un objeto")
                tool_name = _string_arg(params, "name")
                arguments = params.get("arguments", {})
                if not isinstance(arguments, Mapping):
                    raise ValueError("Campo MCP 'arguments' debe ser un objeto")
                result = {"content": [{"type": "text", "text": json.dumps(call(tool_name, arguments, store), ensure_ascii=False)}]}
            else:
                raise ValueError(f"Método MCP inexistente: {method}")
            print(json.dumps({"jsonrpc": "2.0", "id": ident, "result": result}, ensure_ascii=False), flush=True)
        except (ValueError, KeyError, TypeError, sqlite3.Error) as exc:
            print(json.dumps({"jsonrpc": "2.0", "id": request.get("id"), "error": {"code": -32000, "message": str(exc)}}, ensure_ascii=False), flush=True)
