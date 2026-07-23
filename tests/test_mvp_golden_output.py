"""Condition 16 — headless golden master.

Engine run without PySide6, with a fixed query, deterministic output saved to
verification/mvp_output_sample.json and a normalized golden master. This test
checks the canonical contract, schema, innovation presence, legacy fields,
idea-view equality, valid genomes, duplicate report, determinism, stable output.
The golden master is NOT auto-updated on failure.
"""
from __future__ import annotations
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from criba import engine

QUERY = ("¿Cómo podemos generar ideas estructuralmente nuevas para controlar las acciones "
         "de agentes autónomos sin depender de una autoridad central permanente?")
GOLDEN = os.path.join(os.path.dirname(__file__), "..", "verification", "mvp_output_sample.normalized.json")


def _stable(packet: dict) -> dict:
    p = {k: v for k, v in packet.items() if k not in ("activation_id", "timestamp")}
    return json.loads(json.dumps(p, ensure_ascii=False, sort_keys=True))


def test_contract_and_schema():
    p = engine.activate(QUERY, "auto", "balanced", 4)
    assert p["schema"] == "mandatory_model_packet"
    assert isinstance(p["schema_version"], str) and p["schema_version"] == "2.0.0"
    assert "innovation" in p


def test_legacy_fields_present():
    p = engine.activate(QUERY, "auto", "balanced", 4)
    for f in ("selected_current", "supporting_methods", "contextualization", "rupture",
              "experiment", "decision", "model_instruction", "response_contract"):
        assert f in p


def test_idea_views_equal():
    p = engine.activate(QUERY, "auto", "balanced", 4)
    assert p["ideas"] is p["innovation"]["ideas"]
    assert [i["id"] for i in p["ideas"]] == [i["id"] for i in p["innovation"]["ideas"]]


def test_genomes_valid_and_duplicate_report():
    p = engine.activate(QUERY, "auto", "balanced", 4)
    for i in p["innovation"]["ideas"]:
        g = i["genome"]
        for f in ("actor", "mechanism", "topology", "trust_model", "time_model"):
            assert isinstance(g[f], list) and len(g[f]) >= 1
    assert isinstance(p["innovation"]["duplicate_report"], list)


def test_determinism():
    a = engine.activate(QUERY, "auto", "balanced", 4)
    b = engine.activate(QUERY, "auto", "balanced", 4)
    assert _stable(a) == _stable(b)


def test_golden_master_exists_and_matches():
    p = engine.activate(QUERY, "auto", "balanced", 4)
    stable = _stable(p)
    assert os.path.exists(GOLDEN), f"golden master no existe: {GOLDEN} (generarlo con scripts/verify-mvp.ps1)"
    with open(GOLDEN, encoding="utf-8") as f:
        golden = json.load(f)
    assert golden == stable, "GOLDEN MASTER DIVERGE — revisión manual requerida antes de actualizar"
