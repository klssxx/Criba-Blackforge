"""FASE 1 — cobertura de fronteras de decisión del engine CRIBA.

Ejercita el generador y las capas reales (no réplicas de la implementación):
- separación pipeline_action / recommended_status (alternativa C ratificada);
- validación de contratos de entrada (mode, safety_level, query);
- capa de medición (_apply_family mueve ejes causales reales);
- CCA (marca cosméticos);
- convergencia (value_score = evidence*novelty/cost, cost>0).
"""
import pytest

from criba.engine import (
    activate,
    diverge,
    cross_consistency_assessment,
    _apply_family,
    _evaluate_idea,
    _CAUSAL_AXES,
    _BASE_CAUSAL,
)
from criba.methods import select_methods
from criba.constants import VALID_DECISIONS, VALID_PIPELINE_ACTIONS

QUERY = (
    "¿Cómo podríamos diseñar un sistema de aprobación para agentes de "
    "programación que sea seguro sin depender de una autoridad central "
    "permanente?"
)


# --- Contratos de entrada -------------------------------------------------
def test_activate_rejects_invalid_mode():
    with pytest.raises(ValueError):
        activate(QUERY, mode="no-existe")


def test_activate_rejects_invalid_safety_level():
    with pytest.raises(ValueError):
        activate(QUERY, safety_level="paranoid")


def test_activate_rejects_whitespace_only_query():
    with pytest.raises(ValueError):
        activate("   \t\n  ")


def test_activate_accepts_standard_safety_level():
    packet = activate(QUERY, safety_level="standard")
    assert packet["security"]["safety_level"] == "standard"
    # feasibility recibe el bonus de standard (rama distinta a strict)
    assert packet["metrics"]["feasibility"] >= 60


# --- Alternativa C: separación de dimensiones -----------------------------
def test_pipeline_action_and_recommended_status_are_independent():
    packet = activate(QUERY)
    decision = packet["decision"]
    assert decision["pipeline_action"] in VALID_PIPELINE_ACTIONS
    assert decision["recommended_status"] in VALID_DECISIONS
    # regla conservadora: recommended_status NUNCA es ADOPTAR solo por familias
    assert decision["recommended_status"] != "ADOPTAR"
    # pipeline_action NO es una decisión de negocio (no pertenece a VALID_DECISIONS)
    assert decision["pipeline_action"] not in VALID_DECISIONS


def test_pipeline_action_prototipar_when_four_or_more_families():
    # el flujo por defecto produce >=4 familias -> PROTOTIPAR
    packet = activate(QUERY)
    families = packet["innovation"]["idea_families"]
    if len(families) >= 4:
        assert packet["decision"]["pipeline_action"] == "PROTOTIPAR"
    else:
        assert packet["decision"]["pipeline_action"] == "DIVERGIR"
    # en ambos casos el estado de negocio permanece conservador
    assert packet["decision"]["recommended_status"] == "AMPLIAR PRUEBA"


# --- Capa de medición: _apply_family mueve ejes reales --------------------
def test_apply_family_moves_a_causal_axis():
    base = dict(_BASE_CAUSAL)
    mutated = _apply_family("inversion", dict(base), extreme=False)
    moved = [k for k in _CAUSAL_AXES if mutated[k] != base[k]]
    assert moved, "un operador conocido debe mover al menos un eje causal"


def test_apply_family_extreme_differs_from_normal():
    base = dict(_BASE_CAUSAL)
    normal = _apply_family("inversion", dict(base), extreme=False)
    extreme = _apply_family("inversion", dict(base), extreme=True)
    assert normal != extreme


def test_apply_family_unknown_family_uses_fallback_axis():
    base = dict(_BASE_CAUSAL)
    mutated = _apply_family("familia_inexistente", dict(base), extreme=True)
    # fallback documentado: mueve evidencia_requerida
    assert mutated["evidencia_requerida"] != base["evidencia_requerida"]


# --- diverge real con carto.actor ----------------------------------------
def test_diverge_honours_carto_actor():
    methods = select_methods(4, "strict")
    ideas = diverge({"actor": "consejo distribuido"}, {}, {}, methods, QUERY)
    assert ideas
    # el actor propuesto por carto debe propagarse a quien_decide de la base
    assert any(i["causal_variables"]["quien_decide"] == "consejo distribuido"
               for i in ideas)


# --- CCA: marca cosméticos ------------------------------------------------
def test_cca_flags_cosmetic_and_keeps_real():
    real_idea = {"divergence_real": True, "duplicate_status": "candidate"}
    cosmetic_idea = {"divergence_real": False, "duplicate_status": "candidate"}
    real, cosmetic_count = cross_consistency_assessment([real_idea, cosmetic_idea])
    assert real == [real_idea]
    assert cosmetic_count == 1
    assert cosmetic_idea["duplicate_status"] == "cosmetic"


# --- Convergencia: value_score = evidence*novelty/cost --------------------
def test_evaluate_idea_value_score_formula():
    cv = {
        "quien_decide": "un actor externo sin historial decide",
        "cuando": "nunca: se prohibe la opcion obvia",
        "evidencia_requerida": "se asume lo contrario del supuesto y se prueba",
        "si_falla": "el fallo se vuelve visible y obligatorio",
        "topologia": "topologia efimera que se recrea por operacion",
    }
    idea = {"causal_variables": cv, "extreme": True}
    conv = _evaluate_idea(idea)
    assert conv["cost"] > 0
    expected = round((conv["evidence"] * conv["novelty"]) / conv["cost"], 4)
    assert conv["value_score"] == expected
    assert 0.0 <= conv["novelty"] <= 1.0


def test_evaluate_idea_no_axis_moved_gives_zero_novelty():
    # causal_variables iguales a la base => novelty 0 => value_score 0
    idea = {"causal_variables": dict(_BASE_CAUSAL), "extreme": False}
    conv = _evaluate_idea(idea)
    assert conv["novelty"] == 0.0
    assert conv["value_score"] == 0.0
