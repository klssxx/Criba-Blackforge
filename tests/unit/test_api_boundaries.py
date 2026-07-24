"""Adversarial validation tests for the loopback HTTP API."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from criba.api import create_app, serve


QUERY = "Evaluar un cambio reversible y verificable"


def test_fastapi_rejects_malformed_activation_fields(tmp_path) -> None:
    client = TestClient(create_app(tmp_path / "validation.sqlite3"))

    assert client.post("/v1/activate", json={"query": QUERY, "supporting_methods": True}).status_code == 422
    assert client.post("/v1/activate", json={"query": QUERY, "context": []}).status_code == 422
    assert client.post("/v1/activate", json={"query": QUERY, "manual_methods": [1]}).status_code == 422


def test_fastapi_rejects_non_business_decision_status(tmp_path) -> None:
    client = TestClient(create_app(tmp_path / "decision.sqlite3"))
    activation = client.post("/v1/activate", json={"query": QUERY})
    assert activation.status_code == 200

    response = client.post("/v1/decisions", json={
        "session_id": activation.json()["activation_id"],
        "status": "PROTOTIPAR",
        "evidence": [],
    })

    assert response.status_code == 400
    assert "inválido" in response.json()["detail"]


def test_health_reports_loopback_binding(tmp_path) -> None:
    response = TestClient(create_app(tmp_path / "health.sqlite3")).get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "bind": "loopback"}


def test_serve_rejects_non_loopback_before_starting() -> None:
    with pytest.raises(ValueError, match="loopback"):
        serve("0.0.0.0", 8765)
