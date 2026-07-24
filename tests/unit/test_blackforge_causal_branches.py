"""FASE 1 — cobertura de ramas de rechazo/normalización del motor causal.

Complementa test_blackforge_causal.py ejercitando las ramas de validación que
producen ValidationIssue (contrato: rechazo explícito CAUSAL_PROPOSAL_REJECTED,
nunca reparación silenciosa) y los casos borde de normalización escalar.
"""
from __future__ import annotations

import math

import pytest

from criba.blackforge_causal import (
    CausalWeightProfile,
    GENERAL_PROFILE,
    ProposalValidationError,
    analyze_causal_pair,
    build_causal_signature,
    normalize_scalar,
    normalize_id,
    sensitivity_analysis,
    validate_against_frozen_model,
)


def _model():
    return {
        "model_id": "PROBLEM-BR",
        "schema_version": "1.0.0",
        "variables": [
            {"id": "CV-001", "axis": "decision_owner", "baseline_value": "central_authority",
             "allowed_values": ["central_authority", "distributed_quorum", "rule_engine"]},
            {"id": "CV-003", "axis": "failure_default", "baseline_value": "fail_closed",
             "allowed_values": ["fail_closed", "isolate", "rollback"]},
        ],
        "outcomes": [
            {"id": "OUT-001", "allowed_directions": ["increase", "decrease", "maintain"]},
        ],
    }


def _proposal(interventions, *, primary=None, outcomes=None, proposal_id="P-BR"):
    return {
        "proposal_id": proposal_id,
        "primary_intervention": primary or interventions[0],
        "interventions": interventions,
        "affected_outcomes": outcomes if outcomes is not None else [
            {"outcome_id": "OUT-001", "direction": "decrease"}],
    }


# --- normalize_scalar edge cases -----------------------------------------
def test_normalize_scalar_bool_and_none():
    assert normalize_scalar(True) == "true"
    assert normalize_scalar(False) == "false"
    assert normalize_scalar(None) is None
    assert normalize_scalar("   ") is None  # whitespace -> None


def test_normalize_scalar_numeric_equivalence():
    assert normalize_scalar(0) == normalize_scalar("0") == normalize_scalar("0.0")
    assert normalize_scalar(1.5) == normalize_scalar("1.5")


def test_normalize_scalar_non_finite_float_raises():
    with pytest.raises(ValueError):
        normalize_scalar(float("inf"))
    with pytest.raises(ValueError):
        normalize_scalar(float("nan"))


def test_normalize_scalar_unsupported_type_raises():
    with pytest.raises(TypeError):
        normalize_scalar(["list"])


def test_normalize_id_empty_raises():
    with pytest.raises(ValueError):
        normalize_id(None, "field")


# --- proposal-level rejection branches -----------------------------------
def test_non_mapping_proposal_rejected():
    with pytest.raises(ProposalValidationError):
        validate_against_frozen_model(["not", "a", "mapping"], _model())


def test_empty_interventions_rejected():
    bad = {
        "proposal_id": "P-BR",
        "primary_intervention": {"variable_id": "CV-001", "operation": "replace",
                                 "from": "central_authority", "to": "distributed_quorum"},
        "interventions": [],
        "affected_outcomes": [{"outcome_id": "OUT-001", "direction": "decrease"}],
    }
    with pytest.raises(ProposalValidationError) as exc:
        validate_against_frozen_model(bad, _model())
    assert any(i.code == "NO_VALID_INTERVENTIONS" for i in exc.value.issues)


def test_unknown_operation_rejected():
    bad = _proposal([{"variable_id": "CV-001", "operation": "teleport",
                      "from": "central_authority", "to": "rule_engine"}])
    with pytest.raises(ProposalValidationError) as exc:
        validate_against_frozen_model(bad, _model())
    assert any(i.code == "UNKNOWN_OPERATION" for i in exc.value.issues)


def test_missing_required_to_rejected():
    # 'add' requires 'to'; omit it
    bad = _proposal([{"variable_id": "CV-001", "operation": "add"}])
    with pytest.raises(ProposalValidationError) as exc:
        validate_against_frozen_model(bad, _model())
    assert any(i.code == "MISSING_TO_VALUE" for i in exc.value.issues)


def test_forbidden_from_rejected():
    # 'add' forbids 'from'
    bad = _proposal([{"variable_id": "CV-001", "operation": "add",
                      "from": "central_authority", "to": "rule_engine"}])
    with pytest.raises(ProposalValidationError) as exc:
        validate_against_frozen_model(bad, _model())
    assert any(i.code == "FORBIDDEN_FROM_VALUE" for i in exc.value.issues)


def test_from_outside_allowed_rejected():
    bad = _proposal([{"variable_id": "CV-001", "operation": "replace",
                      "from": "not_allowed", "to": "rule_engine"}])
    with pytest.raises(ProposalValidationError) as exc:
        validate_against_frozen_model(bad, _model())
    assert any(i.code == "FROM_OUTSIDE_ALLOWED_VALUES" for i in exc.value.issues)


def test_unknown_outcome_rejected():
    bad = _proposal(
        [{"variable_id": "CV-001", "operation": "replace",
          "from": "central_authority", "to": "rule_engine"}],
        outcomes=[{"outcome_id": "OUT-999", "direction": "increase"}])
    with pytest.raises(ProposalValidationError) as exc:
        validate_against_frozen_model(bad, _model())
    assert any(i.code == "UNKNOWN_OUTCOME_ID" for i in exc.value.issues)


def test_direction_outside_allowed_rejected():
    bad = _proposal(
        [{"variable_id": "CV-001", "operation": "replace",
          "from": "central_authority", "to": "rule_engine"}],
        outcomes=[{"outcome_id": "OUT-001", "direction": "explode"}])
    with pytest.raises(ProposalValidationError) as exc:
        validate_against_frozen_model(bad, _model())
    assert any(i.code == "DIRECTION_OUTSIDE_ALLOWED_VALUES" for i in exc.value.issues)


def test_primary_not_in_interventions_rejected():
    iv = [{"variable_id": "CV-001", "operation": "replace",
           "from": "central_authority", "to": "rule_engine"}]
    primary = {"variable_id": "CV-001", "operation": "replace",
               "from": "central_authority", "to": "distributed_quorum"}
    bad = _proposal(iv, primary=primary)
    with pytest.raises(ProposalValidationError) as exc:
        validate_against_frozen_model(bad, _model())
    assert any(i.code == "PRIMARY_NOT_IN_INTERVENTIONS" for i in exc.value.issues)


def test_duplicate_intervention_rejected():
    iv = {"variable_id": "CV-001", "operation": "replace",
          "from": "central_authority", "to": "rule_engine"}
    bad = _proposal([dict(iv), dict(iv)])
    with pytest.raises(ProposalValidationError) as exc:
        validate_against_frozen_model(bad, _model())
    assert any(i.code == "DUPLICATE_INTERVENTION" for i in exc.value.issues)


# --- model-level rejection branches --------------------------------------
def test_duplicate_variable_in_model_rejected():
    m = _model()
    m["variables"].append(dict(m["variables"][0]))  # duplicate CV-001
    good = _proposal([{"variable_id": "CV-001", "operation": "replace",
                       "from": "central_authority", "to": "rule_engine"}])
    with pytest.raises(ProposalValidationError) as exc:
        validate_against_frozen_model(good, m)
    assert any(i.code == "DUPLICATE_MODEL_VARIABLE" for i in exc.value.issues)


def test_baseline_outside_allowed_in_model_rejected():
    m = _model()
    m["variables"][0]["baseline_value"] = "not_in_allowed"
    good = _proposal([{"variable_id": "CV-001", "operation": "replace",
                       "from": "central_authority", "to": "rule_engine"}])
    with pytest.raises(ProposalValidationError) as exc:
        validate_against_frozen_model(good, m)
    assert any(i.code == "BASELINE_OUTSIDE_ALLOWED_VALUES" for i in exc.value.issues)


# --- analyze / sensitivity edge cases ------------------------------------
def test_exact_signature_pair_is_duplicate():
    m = _model()
    iv = [{"variable_id": "CV-001", "operation": "replace",
           "from": "central_authority", "to": "rule_engine"}]
    a = _proposal(iv, proposal_id="A")
    b = _proposal([dict(iv[0])], proposal_id="B")
    res = analyze_causal_pair(a, b, m, profile=GENERAL_PROFILE)
    assert res["exact_signature_match"] is True
    assert res["classification"] == "causal_duplicate"


def test_sensitivity_rejects_non_positive_delta():
    m = _model()
    a = _proposal([{"variable_id": "CV-001", "operation": "replace",
                    "from": "central_authority", "to": "distributed_quorum"}], proposal_id="A")
    b = _proposal([{"variable_id": "CV-001", "operation": "replace",
                    "from": "central_authority", "to": "rule_engine"}], proposal_id="B")
    with pytest.raises(ValueError):
        sensitivity_analysis(a, b, m, profile=GENERAL_PROFILE, relative_delta=0)


def test_weight_profile_rejects_negative_weight():
    with pytest.raises(ValueError):
        CausalWeightProfile(
            profile_id="neg", version="1.0.0", domain="t",
            weights={"primary_variable": 1.2, "primary_transition": -0.2,
                     "intervention_set": 0.0, "outcome_set": 0.0, "failure_behavior": 0.0})
