"""FASE 1 — cobertura de ramas del safety gate BLACKFORGE.

Complementa test_blackforge_safety.py con las ramas no ejercitadas:
- S1_DEFENSIVE cuando requiere sandbox/autorización (rama else, no local puro);
- external_target_prohibited con S0 conceptual NO deniega (excepción documentada);
- clase de seguridad desconocida -> DENY conservador;
- fallback de _iso cuando el clock no devuelve un timestamp numérico.
"""
from __future__ import annotations

from criba import blackforge_safety as sf
from criba.blackforge_catalog import get


def _ctx(**kw):
    base = {"explicit_authorization": False, "sandbox": False, "rollback": False,
            "logging": False, "stop_condition": False, "isolated_sandbox": False,
            "human_approval": False, "authorized_scope_confirmed": False,
            "full_logging": False}
    base.update(kw)
    return base


FIXED_CLOCK = lambda: 1753324800.0


def test_s1_defensive_else_branch_when_sandbox_required():
    item = dict(get("BF-CYB-S800-0670"))
    item["safety_class"] = "S1_DEFENSIVE"
    item["requires_sandbox"] = True
    item["requires_explicit_authorization"] = True
    d = sf.evaluate_blackforge_safety(item, _ctx(), clock=FIXED_CLOCK)
    # rama else: no es local no-destructivo puro -> ALLOW_DEFENSIVE_DESIGN
    assert d.decision == sf.ALLOW_DEFENSIVE_DESIGN
    assert d.allowed_scope == sf.SCOPE_DEFENSIVE


def test_external_target_with_s0_is_not_denied():
    item = dict(get("BF-CYB-S800-0670"))
    item["safety_class"] = "S0_CONCEPTUAL"
    item["external_target_prohibited"] = True
    d = sf.evaluate_blackforge_safety(item, _ctx(), clock=FIXED_CLOCK)
    # S0 puramente conceptual no ejecuta nada -> no hard_deny -> ALLOW_CONCEPTUAL
    assert d.decision == sf.ALLOW_CONCEPTUAL


def test_s3_denied_lists_scope_unmet_when_triad_present_but_no_scope():
    item = dict(get("BF-CYB-S800-0670"))
    item["safety_class"] = "S3_HIGH_CONTROL"
    d = sf.evaluate_blackforge_safety(item, _ctx(
        explicit_authorization=True, isolated_sandbox=True, human_approval=True,
        rollback=True, full_logging=True, stop_condition=True,
        authorized_scope_confirmed=False), clock=FIXED_CLOCK)
    assert d.decision == sf.DENY
    assert "authorized_scope_confirmed" in d.unmet_requirements


def test_unknown_safety_class_denies_conservatively():
    item = dict(get("BF-CYB-S800-0670"))
    item["safety_class"] = "S9_MADE_UP"
    d = sf.evaluate_blackforge_safety(item, _ctx(), clock=FIXED_CLOCK)
    assert d.decision == sf.DENY
    assert "valid_safety_class" in d.unmet_requirements


def test_iso_fallback_when_clock_not_numeric():
    item = dict(get("BF-CYB-S800-0670"))
    item["safety_class"] = "S0_CONCEPTUAL"
    d = sf.evaluate_blackforge_safety(item, _ctx(), clock=lambda: "NOT-A-TS")
    # _iso cae al except y devuelve str(clock()) sin romper
    assert d.timestamp == "NOT-A-TS"
