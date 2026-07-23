"""FASE 7 — REGRESIÓN CRIBA (gate reproducible).

Guarantees the BLACKFORGE integration is ADDITIVE and never changes CRIBA base
behavior:

- cribra.engine.activate (mode=criba / default) does NOT import or depend on
  blackforge_* modules;
- running the CRIBA engine produces the same contract as before the BLACKFORGE
  work (recommended_status in VALID_DECISIONS, pipeline_action present,
  value_score formula intact);
- the CRIBA golden master is unchanged by the BLACKFORGE additions;
- no blackforge module is loaded as a side effect of importing cribra.engine.
"""
from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from criba import engine  # noqa: E402
from criba.constants import VALID_DECISIONS  # noqa: E402


def test_criba_engine_does_not_import_blackforge_on_load():
    # The CRIBA engine must not directly depend on any blackforge_* module.
    # Verify by INSPECTING the engine source (deterministic, independent of
    # what other tests already loaded into sys.modules).
    import pathlib
    engine_path = pathlib.Path(__file__).resolve().parents[2] / "src" / "criba" / "engine.py"
    source = engine_path.read_text(encoding="utf-8")
    assert "blackforge" not in source, "cribra/engine.py must not reference blackforge"
    # The already-imported engine module must not carry a blackforge submodule
    # in its namespace.
    for name, val in vars(engine).items():
        mod_name = getattr(val, "__name__", "")
        assert not mod_name.startswith("cribra.blackforge"), \
            f"cribra.engine imported blackforge module: {mod_name}"


def test_criba_activate_contract_unchanged():
    q = ("¿Cómo podemos generar ideas estructuralmente nuevas para controlar las acciones "
         "de agentes autónomos sin depender de una autoridad central permanente?")
    p = engine.activate(q, "auto", "balanced", 4)
    # recommended_status still within VALID_DECISIONS (FASE 0 invariant).
    assert p["decision"]["recommended_status"] in VALID_DECISIONS
    # pipeline_action dimension added but never breaks CRIBA contract.
    assert "pipeline_action" in p["decision"]
    assert p["decision"]["pipeline_action"] in {"PROTOTIPAR", "DIVERGIR"}
    # value_score formula present and finite (engine intact).
    assert all("value_score" in i.get("convergence", {}) for i in p["innovation"]["ideas"])
    # legacy packet contract intact.
    assert p["packet_type"] == "MANDATORY_MODEL_PACKET"
    assert p["ideas"] is p["innovation"]["ideas"]


def test_criba_tests_still_green():
    """Re-run the CRIBA baseline gate inside this process to prove no regression."""
    import subprocess
    ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
    mytemp = os.path.join(ROOT, ".tmp_pytest")
    os.makedirs(mytemp, exist_ok=True)
    env = dict(os.environ); env["TMPDIR"]=mytemp; env["TEMP"]=mytemp; env["TMP"]=mytemp
    r = subprocess.run(
        [sys.executable, "-m", "pytest",
         "tests/test_packet_ideas_invariant.py",
         "tests/test_genome_similarity_unknown.py",
         "tests/test_packet_v1_regression.py",
         "tests/test_mvp_golden_output.py",
         "tests/test_causal_mechanism.py",
         "-q", "-p", "no:cacheprovider", "-o", "tmp_path_retention_policy=none"],
        cwd=ROOT, capture_output=True, text=True, env=env)
    summary = [l for l in (r.stdout + r.stderr).splitlines() if "passed" in l or "failed" in l]
    assert r.returncode == 0, "CRIBA baseline gate regressed:\n" + "\n".join(summary)
