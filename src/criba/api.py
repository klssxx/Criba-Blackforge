"""Loopback-only JSON API with optional FastAPI/OpenAPI support."""

import json
import sqlite3
from collections.abc import Mapping
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, cast
from urllib.parse import urlparse

from .catalog import currents, methods
from .constants import MAX_QUERY_CHARS
from .engine import activate, build_prompt
from .storage import Storage

JsonObject = dict[str, Any]
DatabasePath = Path | str | None


def _string(data: Mapping[str, Any], name: str, default: str | None = None, *, allow_empty: bool = False) -> str:
    value = data.get(name, default)
    if not isinstance(value, str) or (not allow_empty and not value.strip()):
        raise ValueError(f"campo '{name}' debe ser un string{' no vacío' if not allow_empty else ''}")
    return value


def _integer(data: Mapping[str, Any], name: str, default: int) -> int:
    value = data.get(name, default)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"campo '{name}' debe ser un entero")
    return value


def _context(data: Mapping[str, Any]) -> dict[str, Any]:
    value = data.get("context", {})
    if not isinstance(value, dict):
        raise ValueError("campo 'context' debe ser un objeto")
    return value


def _manual_methods(data: Mapping[str, Any]) -> list[str] | None:
    value = data.get("manual_methods")
    if value is None:
        return None
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError("campo 'manual_methods' debe ser una lista de strings")
    return value


def _evidence(data: Mapping[str, Any]) -> list[Any] | dict[str, Any]:
    value = data.get("evidence", [])
    if not isinstance(value, (list, dict)):
        raise ValueError("campo 'evidence' debe ser una lista u objeto")
    return value


class Handler(BaseHTTPRequestHandler):
    """Standard-library HTTP handler for CRIBA's loopback API."""

    server_version = "CRIBA/0.1"

    def _json(self, status: int, payload: Any) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _body(self) -> JsonObject:
        length = int(self.headers.get("Content-Length", "0"))
        if length < 0 or length > MAX_QUERY_CHARS * 2:
            raise ValueError("Cuerpo excede el límite permitido.")
        raw = self.rfile.read(length)
        try:
            data = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("JSON malformado.") from exc
        if not isinstance(data, dict):
            raise ValueError("El cuerpo debe ser un objeto JSON.")
        return data

    @property
    def store(self) -> Storage:
        server = cast(CribaHTTPServer, self.server)
        return Storage(server.database)

    def log_message(self, format: str, *args: Any) -> None:
        """Disable request logging so query content and secrets are never logged."""

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        try:
            if path == "/health":
                self._json(200, {"status": "ok", "bind": "loopback"})
                return
            if path == "/v1/currents":
                self._json(200, currents())
                return
            if path == "/v1/methods":
                self._json(200, methods())
                return
            if path.startswith("/v1/sessions/"):
                self._json(200, self.store.get(path.rsplit("/", 1)[1]))
                return
            if path == "/docs":
                self._json(200, {"openapi": "manual", "endpoints": ["POST /v1/activate", "POST /v1/run", "POST /v1/build-prompt", "POST /v1/compare", "POST /v1/decisions", "GET /v1/currents", "GET /v1/methods", "GET /v1/sessions/{id}", "GET /health"]})
                return
            self._json(404, {"error": "Endpoint inexistente."})
        except ValueError as exc:
            self._json(404, {"error": str(exc)})
        except sqlite3.Error:
            self._json(500, {"error": "Error interno de persistencia."})

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        try:
            data = self._body()
            if path in {"/v1/activate", "/v1/run", "/v1/build-prompt"}:
                packet = activate(
                    query=_string(data, "query"),
                    current=_string(data, "current", "auto"),
                    mode=_string(data, "mode", "balanced"),
                    supporting_methods=_integer(data, "supporting_methods", 4),
                    context=_context(data),
                    safety_level=_string(data, "safety_level", "strict"),
                    manual_methods=_manual_methods(data),
                )
                self.store.save(
                    str(packet["original_query"]),
                    packet,
                    {key: data.get(key) for key in ("current", "mode", "supporting_methods", "safety_level")},
                )
                payload = {"packet": packet, "prompt": build_prompt(packet)} if path == "/v1/build-prompt" else packet
                self._json(200, payload)
                return
            if path == "/v1/compare":
                self._json(200, self.store.compare(_string(data, "session_a"), _string(data, "session_b")))
                return
            if path == "/v1/decisions":
                self._json(200, self.store.record_decision(
                    _string(data, "session_id"),
                    _string(data, "status"),
                    _evidence(data),
                    _string(data, "note", "", allow_empty=True),
                ))
                return
            self._json(404, {"error": "Endpoint inexistente."})
        except (ValueError, TypeError, KeyError) as exc:
            self._json(400, {"error": str(exc)})
        except sqlite3.Error:
            self._json(500, {"error": "Error interno de persistencia."})


class CribaHTTPServer(ThreadingHTTPServer):
    """HTTP server carrying the configured persistence path as typed state."""

    def __init__(self, host: str, port: int, database: DatabasePath) -> None:
        self.database = database
        super().__init__((host, port), Handler)


def serve(host: str = "127.0.0.1", port: int = 8765, database: DatabasePath = None) -> None:
    """Serve CRIBA on a loopback address only.

    Uses FastAPI/uvicorn when available and falls back to the standard-library
    server otherwise.
    """
    if host not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("Por seguridad la API solo escucha en loopback.")
    try:
        import uvicorn
    except ImportError:
        server = CribaHTTPServer(host, port, database)
        print(f"CRIBA API listening on http://{host}:{port} (docs: /docs)")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.server_close()
    else:
        uvicorn.run(create_app(database), host=host, port=port, log_level="warning")


def create_app(database: DatabasePath = None) -> Any:
    """Create the optional FastAPI adapter with OpenAPI and Swagger UI."""
    try:
        from fastapi import FastAPI, HTTPException
        from pydantic import BaseModel, Field
    except ImportError as exc:
        raise RuntimeError(
            "FastAPI no está instalado; ejecute 'uv sync --extra api --locked'."
        ) from exc

    class Activation(BaseModel):
        query: str = Field(min_length=1, max_length=MAX_QUERY_CHARS)
        current: str = "auto"
        mode: str = "balanced"
        supporting_methods: int = Field(default=4, ge=1, le=8, strict=True)
        context: dict[str, Any] = Field(default_factory=dict)
        safety_level: str = "strict"
        manual_methods: list[str] | None = None

    class Compare(BaseModel):
        session_a: str
        session_b: str

    class Decision(BaseModel):
        session_id: str
        status: str
        evidence: list[Any] | dict[str, Any] = Field(default_factory=list)
        note: str = ""

    app = FastAPI(
        title="CRIBA Current Engine",
        version="0.1.0",
        description="Local loopback CRIBA API. No external provider or keys.",
    )

    def packet(data: Activation) -> JsonObject:
        try:
            result = activate(
                data.query,
                data.current,
                data.mode,
                data.supporting_methods,
                data.context,
                data.safety_level,
                data.manual_methods,
            )
            Storage(database).save(str(result["original_query"]), result, data.model_dump())
            return result
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc

    @app.get("/health")
    def health() -> JsonObject:
        return {"status": "ok", "bind": "loopback"}

    @app.get("/v1/currents")
    def get_currents() -> list[JsonObject]:
        return currents()

    @app.get("/v1/methods")
    def get_methods() -> list[JsonObject]:
        return methods()

    @app.get("/v1/sessions/{session_id}")
    def session(session_id: str) -> JsonObject:
        try:
            return Storage(database).get(session_id)
        except ValueError as exc:
            raise HTTPException(404, str(exc)) from exc

    @app.post("/v1/activate")
    def activate_endpoint(data: Activation) -> JsonObject:
        return packet(data)

    @app.post("/v1/run")
    def run_endpoint(data: Activation) -> JsonObject:
        return packet(data)

    @app.post("/v1/build-prompt")
    def prompt_endpoint(data: Activation) -> JsonObject:
        result = packet(data)
        return {"packet": result, "prompt": build_prompt(result)}

    @app.post("/v1/compare")
    def compare_endpoint(data: Compare) -> JsonObject:
        try:
            return Storage(database).compare(data.session_a, data.session_b)
        except ValueError as exc:
            raise HTTPException(404, str(exc)) from exc

    @app.post("/v1/decisions")
    def decision_endpoint(data: Decision) -> JsonObject:
        try:
            return Storage(database).record_decision(data.session_id, data.status, data.evidence, data.note)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc

    return app
