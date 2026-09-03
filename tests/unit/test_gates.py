"""Tests for deterministic gates (HIPERMEGAPROMPT §10).

Evidence requirement (user addendum #1): VERIFIED is NEVER granted without
executed-test evidence, even if all 12 structural gates pass.
"""
from __future__ import annotations

from criba.gates import (
    G01_schema_valid,
    G04_authorization_valid,
    G05_state_transition_valid,
    G07_scores_normalized,
    G09_no_duplicate_ids,
    G11_human_review_present,
    G12_output_contract_valid,
    RetryClassification,
    RetryPolicy,
    Verdict,
    evaluate_gates,
)
from criba.output_format import CribaOutput

# ---------------------------------------------------------------------------
# Fixtures: a minimal valid CRIBA context/packet/output
# ---------------------------------------------------------------------------

def _criba_context() -> dict:
    return {
        "context_id": "ctx_abc123",
        "mode": "criba",
        "normalized_query": "mejorar retention de usuarios",
        "central_problem": "la retention cae tras el primer mes",
    }


def _criba_packet(ctx: dict) -> dict:
    return {
        "context": ctx,
        "task_id": "task_001",
        "ideas": [
            {"id": "idea_1", "title": "x", "problem_anchor": "retention",
             "mechanism": "onboarding adaptativo"},
        ],
        "ranking": [{"idea_id": "idea_1", "value": 0.8, "novelty": 0.5,
                     "feasibility": 0.7, "risk": 0.2, "final": 0.7}],
        "evaluation_criteria": {"value": 0.5, "novelty": 0.3, "feasibility": 0.2},
        "findings": [],
    }


def _criba_output() -> CribaOutput:
    return CribaOutput()


# ---------------------------------------------------------------------------
# Structural gates
# ---------------------------------------------------------------------------

def test_G01_schema_valid_accepts_contract():
    assert G01_schema_valid(CribaOutput()).passed is True


def test_G01_schema_valid_rejects_plain_dict():
    assert G01_schema_valid({"foo": "bar"}).passed is False


def test_G05_invalid_transition_rejected():
    res = G05_state_transition_valid("pending", "approved")
    assert res.passed is False


def test_G05_valid_transition_accepted():
    # Per §10.5 / §7.1 state machine, pending -> running is valid.
    assert G05_state_transition_valid("pending", "running").passed is True


def test_G07_scores_out_of_range_fails():
    pkt = _criba_packet(_criba_context())
    pkt["ranking"][0]["final"] = 1.7
    assert G07_scores_normalized(pkt).passed is False


def test_G09_duplicate_ids_fails():
    pkt = _criba_packet(_criba_context())
    pkt["ideas"].append({"id": "idea_1", "title": "dup", "problem_anchor": "a", "mechanism": "b"})
    assert G09_no_duplicate_ids(pkt).passed is False


def test_G11_no_review_fails():
    assert G11_human_review_present([]).passed is False
    assert G11_human_review_present([{"review_id": "r1"}]).passed is True


def test_G12_output_limits_valid():
    assert G12_output_contract_valid(CribaOutput()).passed is True


# ---------------------------------------------------------------------------
# Verdict logic
# ---------------------------------------------------------------------------

def test_verdict_verified_requires_test_evidence():
    """Addendum #1: all gates pass but no test evidence -> PARTIAL, not VERIFIED."""
    ctx = _criba_context()
    pkt = _criba_packet(ctx)
    report = evaluate_gates(context=ctx, packet=pkt, output=_criba_output(),
                             reviews=[{"review_id": "r1"}], test_evidence_present=False)
    assert report.verdict == Verdict.PARTIAL
    assert all(r.passed for r in report.results)


def test_verdict_verified_with_test_evidence():
    ctx = _criba_context()
    pkt = _criba_packet(ctx)
    report = evaluate_gates(context=ctx, packet=pkt, output=_criba_output(),
                             reviews=[{"review_id": "r1"}], test_evidence_present=True)
    assert report.verdict == Verdict.VERIFIED


def test_verdict_blocked_without_human_review():
    ctx = _criba_context()
    pkt = _criba_packet(ctx)
    report = evaluate_gates(context=ctx, packet=pkt, output=_criba_output(),
                             reviews=[], test_evidence_present=True)
    assert report.verdict in (Verdict.BLOCKED, Verdict.FAILED)


# ---------------------------------------------------------------------------
# G04 authorization — Blackforge
# ---------------------------------------------------------------------------

def test_G04_blackforge_without_authorization_fails():
    ctx = {
        "context_id": "ctx_bf001",
        "mode": "blackforge",
        "normalized_query": "pentest autorizado de api interna",
        "central_problem": "posible idor en endpoint /account",
        "authorized_environment": False,       # no authorization
        "authorization_scope": "",
        "stop_conditions": [],
    }
    res = G04_authorization_valid(ctx)
    assert res.passed is False


def test_G04_blackforge_with_authorization_passes():
    ctx = {
        "context_id": "ctx_bf002",
        "mode": "blackforge",
        "normalized_query": "pentest autorizado de api interna",
        "central_problem": "posible idor en endpoint /account",
        "authorized_environment": True,
        "authorization_scope": "lab-interno-api",
        "stop_conditions": ["detener si se degrada producción"],
    }
    res = G04_authorization_valid(ctx)
    assert res.passed is True


def test_G04_explicit_denied_state_fails_closed():
    ctx = {
        "context_id": "ctx_bf002-denied", "mode": "blackforge",
        "authorization_state": "denied",
        "authorized_environment": True,
        "authorization_scope": "lab-interno-api",
        "stop_conditions": ["stop"],
    }
    res = G04_authorization_valid(ctx)
    assert res.passed is False


def test_G04_granted_state_still_requires_scope():
    ctx = {
        "context_id": "ctx_bf002-granted", "mode": "blackforge",
        "authorization_state": "granted",
        "authorized_environment": False,
        "authorization_scope": "",
        "stop_conditions": [],
    }
    res = G04_authorization_valid(ctx)
    assert res.passed is False


def test_metamorphic_remove_authorization_blocks():
    """Metamorphic test (§10.8): removing authorization must block offensive action."""
    base = {
        "context_id": "ctx_bf003", "mode": "blackforge",
        "authorized_environment": True, "authorization_scope": "lab",
        "stop_conditions": ["stop"],
    }
    assert G04_authorization_valid(base).passed is True
    no_auth = dict(base, authorized_environment=False, authorization_scope="")
    assert G04_authorization_valid(no_auth).passed is False


def test_blackforge_blocked_yields_blocked_verdict():
    ctx = {
        "context_id": "ctx_bf004", "mode": "blackforge",
        "authorized_environment": False, "authorization_scope": "",
        "stop_conditions": [],
    }
    pkt = _criba_packet(ctx)
    report = evaluate_gates(context=ctx, packet=pkt, output=_criba_output(),
                             reviews=[{"review_id": "r1"}], test_evidence_present=True)
    assert report.verdict == Verdict.BLOCKED


def test_failed_when_schema_invalid():
    """§10.11: an unusable (non-contract) output yields FAILED."""
    ctx = _criba_context()
    pkt = _criba_packet(ctx)
    report = evaluate_gates(context=ctx, packet=pkt, output={"not": "a contract"},
                             reviews=[{"review_id": "r1"}], test_evidence_present=True)
    assert report.verdict == Verdict.FAILED


# ---------------------------------------------------------------------------
# RetryPolicy (§10.6) — append-only
# ---------------------------------------------------------------------------

def test_retry_policy_append_only():
    policy = RetryPolicy()
    ledger: list[dict] = []
    policy.record_attempt(ledger, 1, RetryClassification.TIMEOUT.value,
                          {"error": "connection reset"})
    policy.record_attempt(ledger, 2, RetryClassification.TRANSIENT.value,
                          {"error": "retry succeeded"})
    # Neither call may erase the other.
    assert len(ledger) == 2
    assert ledger[0]["attempt"] == 1
    assert ledger[1]["attempt"] == 2
    assert ledger[0]["classification"] == RetryClassification.TIMEOUT.value
    # Evidence hash present (append-only proof of prior attempt).
    assert "evidence_hash" in ledger[0]


def test_retry_policy_classification():
    policy = RetryPolicy()
    assert policy.is_retryable(RetryClassification.TIMEOUT.value) is True
    assert policy.is_retryable(RetryClassification.PERMANENT.value) is False
    assert policy.is_retryable(RetryClassification.INVALID_OUTPUT.value) is False
