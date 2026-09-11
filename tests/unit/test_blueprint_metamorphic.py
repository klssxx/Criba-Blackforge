"""Metamorphic checks required by CRIBA/BLACKFORGE spec §10.8."""
from __future__ import annotations

from copy import deepcopy

from criba.blackforge_pipeline import run_headless
from criba.gates import G07_scores_normalized, G09_no_duplicate_ids
from criba.output_format import format_blackforge_output, format_criba_output
from criba.personas import build_persona_prompt


def test_rewording_preserves_headline_selection() -> None:
    first = run_headless(query="Protect the API without adding friction", seed=1)
    second = run_headless(query="Keep the API safe while avoiding extra friction", seed=1)
    assert first["top_ideas"] == second["top_ideas"]


def test_adding_a_constraint_changes_the_persona_input() -> None:
    base = {"original_query": "Improve service reliability", "constraints": []}
    constrained = deepcopy(base)
    constrained["constraints"] = ["only use a reversible lab experiment"]
    base_prompt = build_persona_prompt("A", base)
    constrained_prompt = build_persona_prompt("A", constrained)
    assert base_prompt != constrained_prompt
    assert "only use a reversible lab experiment" in constrained_prompt


def test_removing_authorization_blocks_offensive_gate() -> None:
    from criba.gates import G04_authorization_valid

    authorized = {
        "context_id": "meta-bf",
        "mode": "blackforge",
        "authorization_state": "granted",
        "authorization_scope": "isolated-lab",
        "stop_conditions": ["stop on degradation"],
    }
    denied = dict(authorized)
    denied.pop("authorization_state")
    assert G04_authorization_valid(authorized).passed is True
    assert G04_authorization_valid(denied).passed is False


def test_duplicate_idea_ids_are_rejected_instead_of_counted_twice() -> None:
    packet = {
        "ideas": [{"id": "i1"}, {"id": "i1"}],
    }
    result = G09_no_duplicate_ids(packet)
    assert result.passed is False
    assert "i1" in result.reason


def test_weight_change_is_checked_as_a_normalized_change() -> None:
    valid = {
        "evaluation_criteria": {"value": 0.5, "novelty": 0.3, "feasibility": 0.2},
        "ranking": [],
    }
    changed = {
        "evaluation_criteria": {"value": 0.7, "novelty": 0.2, "feasibility": 0.1},
        "ranking": [],
    }
    assert G07_scores_normalized(valid).passed is True
    assert G07_scores_normalized(changed).passed is True
    invalid = dict(changed, evaluation_criteria={"value": 0.8, "novelty": 0.3})
    assert G07_scores_normalized(invalid).passed is False


def test_mode_switch_adds_security_fields() -> None:
    context = {"central_problem": "protect API", "protected_assets": ["API"]}
    criba = format_criba_output(context=context, ideas=[{"title": "idea"}])
    blackforge = format_blackforge_output(
        context=context,
        ideas=[{
            "title": "defensive idea",
            "mechanism": "sandbox and rollback",
            "bypass_probable": "telemetry gap",
            "residual_risk": "medium",
        }],
    )
    assert not hasattr(criba, "authorization")
    assert blackforge.authorization is not None
    assert blackforge.winner.likely_bypass == "telemetry gap"
    assert blackforge.winner.residual_risk == "medium"
