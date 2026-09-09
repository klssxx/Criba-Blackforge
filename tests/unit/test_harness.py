"""Tests del harness benchmark v0 (megaprompt §45-§48)."""
from __future__ import annotations

import json

import pytest

from benchmarks.innovation.harness import CONDITIONS, exportar, run_condition, run_smoke


def test_conditions_reservadas() -> None:
    assert set(CONDITIONS) == {"A_DIRECT", "B_STRONG_PROMPT", "C_CRIBA"}


def test_sin_modelo_status_unavailable() -> None:
    rec = run_condition("A_DIRECT", {"id": "G01", "texto": "cola"}, seed=7)
    assert rec["status"] == "UNAVAILABLE"
    assert rec["metrics"] is None
    assert rec["candidates"] == []


def test_smoke_sin_llamadas_externas_exporta_json(tmp_path) -> None:
    """Smoke funcional con modelo stub inyectado: cero red, export JSON.

    C_CRIBA usa criba_fn real (loop CRIBA); las condiciones de modelo usan el
    stub. Hallazgo 6: sin criba_fn, C_CRIBA sería UNAVAILABLE honesto.
    """
    from benchmarks.innovation.criba_adapter import criba_fn

    def _model_stub(prompt: str) -> list[dict]:
        return [
            {"idea_id": f"c{i}", "score": 0.9 - i * 0.1, "family": f"f{i}",
             "methods": [f"T{i}"],
             "genome": {"mechanism": [f"m{i}"], "trust_model": ["t"],
                        "topology": ["x"], "actor": ["a"], "time_model": ["tt"]},
             "texto": f"respuesta {i}"}
            for i in range(3)
        ]
    report = run_smoke(model_fn=_model_stub, seed=7, criba_fn=criba_fn)
    assert report["n_problemas"] == 10
    assert len(report["runs"]) == 30  # 10 problemas × 3 condiciones
    assert all(r["status"] == "OK" for r in report["runs"])
    out = exportar(report, tmp_path / "bench_smoke.json")
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["n_problemas"] == 10
    assert "NO concluye superioridad" in data["advertencia"]


def test_seed_explicita_reproduce_bench_run_id() -> None:
    a = run_condition("C_CRIBA", {"id": "B01", "texto": "x"}, seed=9)
    b = run_condition("C_CRIBA", {"id": "B01", "texto": "x"}, seed=9)
    assert a["bench_run_id"] == b["bench_run_id"]
    assert a["run_id"] != b["run_id"]  # ejecuciones distintas, misma semilla
