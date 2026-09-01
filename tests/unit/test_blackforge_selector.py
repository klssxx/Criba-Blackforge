"""FASE 2 — SELECTOR BLACKFORGE (gate reproducible).

Validates the deterministic quota-respecting selector (src/criba/blackforge_selector.py)
against HIPER_MEGAPROMPT FASE 2 contracts, and emits
verification/blackforge_selector_report.json.

Contracts:
- misma semilla -> mismos IDs y orden;
- semilla distinta -> puede variar conservando cuotas;
- 12 elementos por defecto;
- >=3 fuentes, >=5 categorías primarias, >=4 ejes causales;
- máximos por categoría/familia/eje desconocido;
- 0 S3 por defecto; S3 rechazado sin aprobación; máximo 1 con aprobación completa;
- research solo con modo explícito; archive nunca seleccionable;
- fallo estructurado (SelectionFailure) cuando las cuotas son imposibles.
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from criba import blackforge_selector as bs

ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
REPORT = os.path.join(ROOT, "verification", "blackforge_selector_report.json")


def _ids(rep):
    return rep.selected_ids


def test_default_12_elements_and_reproducible():
    a = bs.select_blackforge(seed=7)
    b = bs.select_blackforge(seed=7)
    assert a.status_ok()
    assert len(a.selected_ids) == 12
    assert _ids(a) == _ids(b)  # same seed -> same ids AND order


def test_different_seed_may_vary_but_keeps_quotas():
    a = bs.select_blackforge(seed=1)
    b = bs.select_blackforge(seed=99)
    assert a.status_ok() and b.status_ok()
    for rep in (a, b):
        assert len(rep.selected_ids) == 12
        assert rep.compliance["min_source_catalogs"]["ok"]
        assert rep.compliance["min_primary_categories"]["ok"]
        assert rep.compliance["min_causal_axes"]["ok"]
        assert rep.compliance["mandatory_stages"]["ok"]


def test_minimum_sources_categories_axes():
    rep = bs.select_blackforge(seed=3)
    assert rep.compliance["min_source_catalogs"]["ok"]  # >=3
    assert rep.compliance["min_primary_categories"]["ok"]  # >=5
    assert rep.compliance["min_causal_axes"]["ok"]  # >=4


def test_maxima_per_category_family_unknown_axis():
    rep = bs.select_blackforge(seed=5)
    c = rep.compliance
    assert c["max_per_primary_category"]["ok"]
    assert c["max_per_source_family"]["ok"]
    assert c["max_unknown_causal_axis"]["ok"]
    # Enforce concretely on the selected set.
    from collections import Counter

    from criba.blackforge_catalog import get
    pc = Counter(); fam = Counter(); unk = 0
    for bid in rep.selected_ids:
        r = get(bid)
        pc[r.get("functional_category_primary") or r.get("functional_category")] += 1
        if r.get("source_family"):
            fam[r["source_family"]] += 1
        if (r.get("causal_axis_primary") in (None, "", "unknown")):
            unk += 1
    assert max(pc.values()) <= 3
    assert max(fam.values()) <= 2
    assert unk <= 2


def test_s3_zero_by_default_and_rejected_without_approval():
    rep = bs.select_blackforge(seed=11)
    assert rep.s3_count == 0
    assert rep.s3_allowed is False
    # Even requesting S3 tier path without the approval triad: still 0.
    rep2 = bs.select_blackforge(seed=11, explicit_high_control_approval=True)
    assert rep2.s3_count == 0  # missing scope + sandbox


def test_s3_max_one_with_full_approval():
    rep = bs.select_blackforge(
        seed=11,
        explicit_high_control_approval=True,
        authorized_scope_confirmed=True,
        sandbox_available=True,
    )
    assert rep.s3_allowed is True
    assert rep.s3_count <= 1
    assert rep.compliance["s3_cap"]["ok"]


def test_research_only_with_explicit_mode():
    base = bs.select_blackforge(seed=2)
    assert "research" not in base.allowed_tiers
    res = bs.select_blackforge(seed=2, allow_research=True)
    assert "research" in res.allowed_tiers
    # all selected are within allowed tiers
    from criba.blackforge_catalog import get
    for bid in res.selected_ids:
        assert get(bid).get("activation_tier") in res.allowed_tiers


def test_archive_never_selectable():
    rep = bs.select_blackforge(seed=4, allowed_tiers=["essential", "core", "extended", "research", "archive"])
    from criba.blackforge_catalog import get
    for bid in rep.selected_ids:
        assert get(bid).get("activation_tier") != "archive"


def test_structured_failure_when_quota_impossible():
    # Force an impossible session size far beyond the eligible pool respecting
    # all other quotas -> honest SelectionFailure, NOT a fake selection.
    rep = bs.select_blackforge(seed=1, session_size=9999)
    assert rep.failure is not None
    assert rep.failure.failed_quota == "session_size"
    assert rep.selected_ids == []  # does NOT invent a fake selection
    assert rep.to_dict()["status"] == "FAILED"


def test_emits_report():
    """Write the FASE 2 machine-readable selector report."""
    samples = {}
    for seed in (1, 2, 3):
        samples[seed] = bs.select_blackforge(seed=seed).to_dict()
    # A deliberately failing configuration to capture the failure shape.
    failing = bs.select_blackforge(seed=1, session_size=9999).to_dict()
    os.makedirs(os.path.dirname(REPORT), exist_ok=True)
    report = {
        "phase": "FASE 2 — SELECTOR",
        "selector_module": "src/criba/blackforge_catalog.py + src/criba/blackforge_selector.py",
        "policy_source": "catalog selection_policy / safety_policy",
        "samples": samples,
        "failing_case": failing,
        "contracts_checked": [
            "same seed -> same ids+order",
            "different seed keeps quotas",
            "12 elements default",
            ">=3 sources / >=5 primary categories / >=4 causal axes",
            "max per primary category (3) / family (2) / unknown axis (2)",
            "0 S3 by default; rejected without approval; max 1 with full approval",
            "research only with explicit mode",
            "archive never selectable",
            "structured SelectionFailure when quota impossible",
        ],
    }
    with open(REPORT, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    assert os.path.exists(REPORT)
    with open(REPORT, encoding="utf-8") as f:
        back = json.load(f)
    assert back["samples"]["1"]["status"] == "OK"
    assert back["failing_case"]["status"] == "FAILED"
