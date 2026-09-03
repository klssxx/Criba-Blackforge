"""FASE 3 — SAFETY GATE BLACKFORGE (gate reproducible).

Validates evaluate_blackforge_safety against HIPER_MEGAPROMPT FASE 3 contracts
and emits verification/blackforge_safety_report.json.

Contracts:
- S0_CONCEPTUAL -> ALLOW_CONCEPTUAL (analysis/ideation only, no auto-exec).
- S1_DEFENSIVE -> ALLOW_DEFENSIVE_DESIGN / ALLOW_LOCAL_NON_DESTRUCTIVE (no external).
- S2_SANDBOX -> REQUIRE_SANDBOX only with full S2 requirements; DENY otherwise.
- S3_HIGH_CONTROL -> REQUIRE_HUMAN_APPROVAL only with full triad + scope;
  never enabled by default; DENY otherwise.
- external_target_prohibited -> DENY (except pure S0 conceptual).
- every decision records decision/policy_version/item_id/reasons/
  unmet_requirements/allowed_scope/timestamp/session_id.
- prohibited automatic actions never produce an ALLOW.
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from criba import blackforge_safety as sf
from criba.blackforge_safety import AuthorizationState
from criba.blackforge_catalog import get

ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
REPORT = os.path.join(ROOT, "verification", "blackforge_safety_report.json")

FIXED_CLOCK = lambda: 1753324800.0  # 2025-07-24T00:00:00Z


def _ctx(**kw):
    base = {"explicit_authorization": False, "sandbox": False, "rollback": False,
            "logging": False, "stop_condition": False, "isolated_sandbox": False,
            "human_approval": False, "authorized_scope_confirmed": False,
            "full_logging": False}
    base.update(kw)
    return base


def test_s0_conceptual_allows_analysis_only():
    item = get("BF-CYB-S800-0670")  # known S1 in sample; force S0
    item = dict(item); item["safety_class"] = "S0_CONCEPTUAL"
    d = sf.evaluate_blackforge_safety(item, _ctx(), clock=FIXED_CLOCK, session_id="s1")
    assert d.decision == sf.ALLOW_CONCEPTUAL
    assert d.allowed_scope == "analysis_and_ideation"
    assert d.unmet_requirements == []
    assert d.policy_version == "BF-SAFE-2.0.0"
    assert d.item_id == item["blackforge_id"]


def test_s1_defensive_allows_local_non_destructive():
    item = get("BF-CYB-S800-0670")  # S1_DEFENSIVE in catalog
    assert item["safety_class"] == "S1_DEFENSIVE"
    d = sf.evaluate_blackforge_safety(item, _ctx(), clock=FIXED_CLOCK, session_id="s2")
    assert d.decision in (sf.ALLOW_DEFENSIVE_DESIGN, sf.ALLOW_LOCAL_NON_DESTRUCTIVE)


def test_s2_requires_sandbox_with_full_requirements():
    item = get("BF-CYB-S800-0670"); item = dict(item); item["safety_class"] = "S2_SANDBOX"
    # Without requirements -> DENY
    d0 = sf.evaluate_blackforge_safety(item, _ctx(), clock=FIXED_CLOCK)
    assert d0.decision == sf.DENY
    assert d0.unmet_requirements  # lists missing requirements
    # With full S2 requirements -> REQUIRE_SANDBOX
    d1 = sf.evaluate_blackforge_safety(item, _ctx(
        explicit_authorization=True, sandbox=True, rollback=True, logging=True, stop_condition=True),
        clock=FIXED_CLOCK)
    assert d1.decision == sf.REQUIRE_SANDBOX
    assert d1.unmet_requirements == []


def test_s3_requires_human_approval_full_triad():
    item = get("BF-CYB-S800-0670"); item = dict(item); item["safety_class"] = "S3_HIGH_CONTROL"
    # By default (no approvals) -> DENY, never silently allowed.
    d0 = sf.evaluate_blackforge_safety(item, _ctx(), clock=FIXED_CLOCK)
    assert d0.decision == sf.DENY
    # Full triad + scope -> REQUIRE_HUMAN_APPROVAL
    d1 = sf.evaluate_blackforge_safety(item, _ctx(
        explicit_authorization=True, isolated_sandbox=True, human_approval=True,
        rollback=True, full_logging=True, stop_condition=True, authorized_scope_confirmed=True),
        clock=FIXED_CLOCK)
    assert d1.decision == sf.REQUIRE_HUMAN_APPROVAL
    assert d1.unmet_requirements == []


def test_external_target_prohibited_denies():
    item = get("BF-CYB-S800-0670"); item = dict(item)
    item["external_target_prohibited"] = True
    item["safety_class"] = "S1_DEFENSIVE"
    d = sf.evaluate_blackforge_safety(item, _ctx(), clock=FIXED_CLOCK)
    assert d.decision == sf.DENY


def test_decision_record_has_all_fields():
    item = get("BF-CYB-S800-0670")
    d = sf.evaluate_blackforge_safety(item, _ctx(), clock=FIXED_CLOCK, session_id="rec")
    dct = d.to_dict()
    for f in ("decision", "policy_version", "item_id", "reasons",
              "unmet_requirements", "allowed_scope", "session_id", "timestamp"):
        assert f in dct and dct[f] is not None
    assert dct["timestamp"].startswith("2025-07-24")


def test_authorization_state_is_enum_and_serialized():
    item = dict(get("BF-CYB-S800-0670"))
    d = sf.evaluate_blackforge_safety(
        item,
        _ctx(authorization_state="granted"),
        clock=FIXED_CLOCK,
        session_id="enum-state",
    )
    assert d.authorization_state is AuthorizationState.GRANTED
    assert d.to_dict()["authorization_state"] == "granted"


def test_no_prohibited_action_yields_allow():
    # If an item demanded a prohibited action it must be DENY, never ALLOW.
    # Sanity across the whole catalog: external_target_prohibited items are DENY.
    from criba.blackforge_catalog import records
    bad = [r for r in records() if r.get("external_target_prohibited") is True]
    for r in bad[:5]:
        d = sf.evaluate_blackforge_safety(dict(r), _ctx(), clock=FIXED_CLOCK)
        assert d.decision == sf.DENY


def test_emits_report():
    """Write the FASE 3 machine-readable safety report."""
    from criba.blackforge_catalog import records
    decisions = {}
    for r in records()[:40]:
        d = sf.evaluate_blackforge_safety(dict(r), _ctx(), clock=FIXED_CLOCK, session_id="report")
        decisions[r["blackforge_id"]] = d.to_dict()
    # distribution of decisions over full catalog under default (no-approval) ctx
    dist = {}
    for r in records():
        d = sf.evaluate_blackforge_safety(dict(r), _ctx(), clock=FIXED_CLOCK)
        dist[d.decision] = dist.get(d.decision, 0) + 1
    os.makedirs(os.path.dirname(REPORT), exist_ok=True)
    report = {
        "phase": "FASE 3 — SAFETY",
        "policy_version": "BF-SAFE-2.0.0",
        "sample_decisions": decisions,
        "decision_distribution_default_context": dist,
        "contracts_checked": [
            "S0 -> ALLOW_CONCEPTUAL",
            "S1 -> ALLOW_DEFENSIVE_DESIGN / ALLOW_LOCAL_NON_DESTRUCTIVE",
            "S2 -> REQUIRE_SANDBOX solo con requisitos completos; DENY si falta",
            "S3 -> REQUIRE_HUMAN_APPROVAL con triada completa+scope; DENY por defecto",
            "external_target_prohibited -> DENY",
            "registro completo de campos por decision",
            "accion prohibida nunca produce ALLOW",
        ],
    }
    with open(REPORT, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    assert os.path.exists(REPORT)
    with open(REPORT, encoding="utf-8") as f:
        back = json.load(f)
    assert back["decision_distribution_default_context"]["DENY"] >= 0
