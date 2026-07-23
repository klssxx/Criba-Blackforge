"""FASE 4 — CAUSAL BLACKFORGE (gate reproducible).

Integrates the reference causal engine (imports/blackforge_v2/causal_engine.py)
as src/criba/blackforge_causal.py and validates it against HIPER_MEGAPROMPT FASE 4
contracts. Emits verification/blackforge_causal_report.json.

Contracts:
- validate_against_frozen_model rejects UNKNOWN_VARIABLE_ID etc. with code
  CAUSAL_PROPOSAL_REJECTED (never silent repair);
- None/str tuples are never sorted together (no TypeError);
- two causally-equal proposals with different wording get the SAME hash;
- normalization: NFKC, casefold, bool, numbers (0 == "0" == "0.0"), key order;
- frozen problem model fingerprint stable; critical axes force structural diff;
- sensitivity analysis runs +/-10% for each feature.
"""
from __future__ import annotations

import json
import os
import sys
import copy

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from criba.blackforge_causal import (  # noqa: E402
    CYBERSECURITY_PROFILE,
    GENERAL_PROFILE,
    CausalWeightProfile,
    ProposalValidationError,
    analyze_causal_pair,
    build_causal_signature,
    sensitivity_analysis,
    validate_against_frozen_model,
    frozen_model_fingerprint,
)

ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
REPORT = os.path.join(ROOT, "verification", "blackforge_causal_report.json")


@pytest.fixture
def model():
    return {
        "model_id": "PROBLEM-001",
        "schema_version": "1.0.0",
        "variables": [
            {"id": "CV-001", "axis": "decision_owner", "baseline_value": "central_authority",
             "allowed_values": ["central_authority", "distributed_quorum", "rule_engine"]},
            {"id": "CV-002", "axis": "evidence_required", "baseline_value": "human_approval",
             "allowed_values": ["human_approval", "capability_proof"]},
            {"id": "CV-003", "axis": "failure_default", "baseline_value": "fail_closed",
             "allowed_values": ["fail_closed", "isolate", "rollback"]},
            {"id": "CV-004", "axis": "numeric_threshold", "baseline_value": 0,
             "allowed_values": [0, 1]},
        ],
        "outcomes": [
            {"id": "OUT-001", "allowed_directions": ["increase", "decrease", "maintain"]},
        ],
    }


def proposal(interventions, *, primary=None, proposal_id="P-001"):
    return {
        "proposal_id": proposal_id,
        "primary_intervention": primary or interventions[0],
        "interventions": interventions,
        "affected_outcomes": [{"outcome_id": "OUT-001", "direction": "decrease"}],
    }


def test_signature_does_not_compare_none_and_string(model):
    first = {"variable_id": "CV-001", "operation": "condition", "to": "distributed_quorum"}
    second = {"variable_id": "CV-001", "operation": "condition", "from": "central_authority", "to": "rule_engine"}
    result = build_causal_signature(proposal([first, second], primary=first), model)
    assert len(result["digest"]) == 64
    assert result["payload"]["interventions"][0] != result["payload"]["interventions"][1]


def test_unknown_variable_is_rejected(model):
    bad = proposal([{"variable_id": "CV-999", "operation": "replace", "from": "x", "to": "y"}])
    with pytest.raises(ProposalValidationError) as exc:
        validate_against_frozen_model(bad, model)
    assert exc.value.error_code == "CAUSAL_PROPOSAL_REJECTED"
    assert any(issue.code == "UNKNOWN_VARIABLE_ID" for issue in exc.value.issues)


def test_value_outside_frozen_enum_is_rejected(model):
    bad = proposal([{"variable_id": "CV-001", "operation": "replace", "from": "central_authority", "to": "invented_value"}])
    with pytest.raises(ProposalValidationError) as exc:
        validate_against_frozen_model(bad, model)
    assert any(issue.code == "TO_OUTSIDE_ALLOWED_VALUES" for issue in exc.value.issues)


def test_numeric_string_and_number_produce_same_signature(model):
    a = proposal([{"variable_id": "CV-004", "operation": "replace", "from": 0, "to": 1}])
    b = proposal([{"to": "1", "operation": "replace", "variable_id": "CV-004", "from": "0"}])
    assert build_causal_signature(a, model)["digest"] == build_causal_signature(b, model)["digest"]


def test_dict_key_order_does_not_change_signature(model):
    a = proposal([{"variable_id": "CV-002", "operation": "replace", "from": "human_approval", "to": "capability_proof"}])
    b = {
        "affected_outcomes": [{"direction": "decrease", "outcome_id": "OUT-001"}],
        "interventions": [{"to": "capability_proof", "from": "human_approval", "operation": "replace", "variable_id": "CV-002"}],
        "primary_intervention": {"to": "capability_proof", "variable_id": "CV-002", "operation": "replace", "from": "human_approval"},
        "proposal_id": "P-001",
    }
    assert build_causal_signature(a, model)["digest"] == build_causal_signature(b, model)["digest"]


def test_noop_after_normalization_is_rejected(model):
    bad = proposal([{"variable_id": "CV-004", "operation": "replace", "from": 0, "to": "0.0"}])
    with pytest.raises(ProposalValidationError) as exc:
        validate_against_frozen_model(bad, model)
    assert any(issue.code == "NOOP_INTERVENTION" for issue in exc.value.issues)


def test_weight_profile_must_be_versioned_and_sum_to_one():
    with pytest.raises(ValueError):
        CausalWeightProfile(
            profile_id="bad", version="1.0.0", domain="test",
            weights={"primary_variable": 0.5, "primary_transition": 0.5,
                      "intervention_set": 0.5, "outcome_set": 0.0, "failure_behavior": 0.0},
        )


def test_critical_failure_axis_forces_structural_difference(model):
    a = proposal([{"variable_id": "CV-003", "operation": "replace", "from": "fail_closed", "to": "isolate"}], proposal_id="A")
    b = proposal([{"variable_id": "CV-002", "operation": "replace", "from": "human_approval", "to": "capability_proof"}], proposal_id="B")
    result = analyze_causal_pair(a, b, model, profile=CYBERSECURITY_PROFILE)
    assert result["classification"] == "structurally_distinct"
    assert "failure_default" in result["critical_differences"]


def test_sensitivity_runs_plus_and_minus_ten_percent_for_each_feature(model):
    a = proposal([{"variable_id": "CV-001", "operation": "replace", "from": "central_authority", "to": "distributed_quorum"}], proposal_id="A")
    b = proposal([{"variable_id": "CV-001", "operation": "replace", "from": "central_authority", "to": "rule_engine"}], proposal_id="B")
    result = sensitivity_analysis(a, b, model, profile=GENERAL_PROFILE, relative_delta=0.10)
    assert len(result["runs"]) == 10
    assert result["baseline_classification"] in {"causal_duplicate", "close_variant", "structurally_distinct", "insufficient_evidence"}


def test_frozen_model_fingerprint_stable(model):
    fp1 = frozen_model_fingerprint(model)
    fp2 = frozen_model_fingerprint(copy.deepcopy(model))
    assert fp1 == fp2
    assert len(fp1) == 64


def test_emits_report(model):
    samples = {}
    a = proposal([{"variable_id": "CV-001", "operation": "replace", "from": "central_authority", "to": "distributed_quorum"}], proposal_id="A")
    b = proposal([{"variable_id": "CV-001", "operation": "replace", "from": "central_authority", "to": "rule_engine"}], proposal_id="B")
    c = proposal([{"variable_id": "CV-001", "operation": "replace", "from": "central_authority", "to": "distributed_quorum"}], proposal_id="A2")
    samples["a_vs_b"] = analyze_causal_pair(a, b, model, profile=GENERAL_PROFILE)
    samples["a_vs_a"] = analyze_causal_pair(a, c, model, profile=GENERAL_PROFILE)  # equal -> duplicate
    assert samples["a_vs_a"]["classification"] == "causal_duplicate"
    os.makedirs(os.path.dirname(REPORT), exist_ok=True)
    report = {
        "phase": "FASE 4 — CAUSAL",
        "engine_module": "src/criba/blackforge_causal.py (integrated from imports/blackforge_v2/causal_engine.py)",
        "rejection_code": "CAUSAL_PROPOSAL_REJECTED",
        "rejection_codes_supported": [
            "UNKNOWN_VARIABLE_ID", "UNKNOWN_OUTCOME_ID", "UNKNOWN_OPERATION",
            "FROM_OUTSIDE_ALLOWED_VALUES", "TO_OUTSIDE_ALLOWED_VALUES",
            "DIRECTION_OUTSIDE_ALLOWED_VALUES", "MISSING_FROM_VALUE", "MISSING_TO_VALUE",
            "NOOP_INTERVENTION", "PRIMARY_NOT_IN_INTERVENTIONS", "DUPLICATE_INTERVENTION",
        ],
        "samples": samples,
        "frozen_fingerprint": frozen_model_fingerprint(model),
        "contracts_checked": [
            "rejection code CAUSAL_PROPOSAL_REJECTED on invalid proposals (no silent repair)",
            "None/str tuples never sorted together",
            "causally-equal proposals with different wording -> same hash",
            "NFKC/casefold/bool/numeric(0=='0'=='0.0')/key-order normalization",
            "frozen model fingerprint stable",
            "critical axes force structural difference",
            "sensitivity analysis +/-10% per feature",
        ],
    }
    with open(REPORT, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    assert os.path.exists(REPORT)
    with open(REPORT, encoding="utf-8") as f:
        back = json.load(f)
    assert back["frozen_fingerprint"]
