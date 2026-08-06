"""FASE 6 — PIPELINE HEADLESS BLACKFORGE (gate reproducible).

Runs the deterministic headless pipeline (src/criba/blackforge_pipeline.py) and
validates HIPER_MEGAPROMPT FASE 6 contracts. Artifact persistence is exercised
in pytest's temporary directory so a test run never rewrites tracked evidence.

Contracts:
- same seed -> same normalized result (deterministic);
- selection respects policy (seed 1 -> 12 items, quotas OK);
- safety report present; DENY items excluded from ideas;
- frozen problem model referenced (causal signal present);
- 8-12 surviving ideas;
- measurement (metrics), CCA (real_divergent_count/cosmetic_rejected),
  convergence (value_score), top_ideas, mean_value_score all present.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from criba import blackforge_pipeline as bp  # noqa: E402

ROOT = os.path.join(os.path.dirname(__file__), "..", "..")


def test_deterministic_same_seed():
    a = bp.run_headless(seed=1)
    b = bp.run_headless(seed=1)
    sa, sb = bp._stable(a), bp._stable(b)
    assert sa == sb


def test_selection_respects_policy():
    p = bp.run_headless(seed=1)
    assert p["selection"]["selected_count"] == 12
    assert p["selection"]["compliance"]["min_source_catalogs"]["ok"]
    assert p["selection"]["compliance"]["min_primary_categories"]["ok"]
    assert p["selection"]["compliance"]["min_causal_axes"]["ok"]


def test_safety_report_present_and_deny_excluded():
    p = bp.run_headless(seed=1)
    assert p["safety_report"]
    denied = {r["item_id"] for r in p["safety_report"] if r["decision"] == "DENY"}
    idea_ids = {i["blackforge_id"] for i in p["ideas"]}
    assert not (denied & idea_ids), "DENY items must not appear as ideas"


def test_surviving_ideas_count():
    p = bp.run_headless(seed=1)
    assert 8 <= len(p["ideas"]) <= 12


def test_measurement_cca_convergence_present():
    p = bp.run_headless(seed=1)
    assert "metrics" in p and "mean_value_score" in p["metrics"]
    assert "real_divergent_count" in p and "cosmetic_rejected" in p
    assert p["top_ideas"]
    assert all("convergence" in i and "value_score" in i["convergence"] for i in p["ideas"])
    # causal signal present on survivors
    assert p["causal_axes_represented"]


def test_frozen_problem_model_referenced():
    p = bp.run_headless(seed=1)
    # selection + causal axes represented => frozen model contract exercised
    assert p["selection"]["allowed_tiers"]


def test_emits_artifacts_and_normalized_matches_rerun(tmp_path: Path):
    p = bp.run_headless(seed=1)
    paths = bp.save_artifacts(p, out_dir=str(tmp_path))
    assert os.path.exists(paths["raw"]) and os.path.exists(paths["normalized"])
    assert os.path.basename(paths["raw"]) == "blackforge_headless_output.json"
    assert os.path.basename(paths["normalized"]) == "blackforge_headless_output.normalized.json"
    # A second run with the same seed must reproduce the normalized artifact.
    p2 = bp.run_headless(seed=1)
    with open(paths["normalized"], encoding="utf-8") as f:
        saved = json.load(f)
    assert saved == bp._stable(p2)
