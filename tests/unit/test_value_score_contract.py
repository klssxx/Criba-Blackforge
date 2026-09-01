"""FASE 2 — contrato explícito de value_score.

value_score = evidence * novelty / cost (fórmula RATIFICADA, no se cambia).
Este módulo prueba el contrato de dominio: cost debe ser > 0, entradas finitas,
sin coerción silenciosa, sin infinito, sin NaN, sin ocultar el error.
"""
from __future__ import annotations

import math

import pytest

from criba.engine import ValueScoreError, value_score


def test_value_score_formula_matches_definition():
    assert value_score(0.8, 0.6, 0.5) == round((0.8 * 0.6) / 0.5, 4)


def test_value_score_rejects_zero_cost():
    with pytest.raises(ValueScoreError):
        value_score(0.8, 0.6, 0.0)


def test_value_score_rejects_negative_cost():
    with pytest.raises(ValueScoreError):
        value_score(0.8, 0.6, -0.3)


def test_value_score_evidence_zero_is_valid_zero():
    assert value_score(0.0, 0.6, 0.5) == 0.0


def test_value_score_novelty_zero_is_valid_zero():
    assert value_score(0.8, 0.0, 0.5) == 0.0


def test_value_score_rejects_nan_and_infinity():
    with pytest.raises(ValueScoreError):
        value_score(float("nan"), 0.6, 0.5)
    with pytest.raises(ValueScoreError):
        value_score(0.8, float("inf"), 0.5)
    with pytest.raises(ValueScoreError):
        value_score(0.8, 0.6, float("inf"))


def test_value_score_rejects_non_numeric_types():
    with pytest.raises(ValueScoreError):
        value_score("0.8", 0.6, 0.5)
    with pytest.raises(ValueScoreError):
        value_score(0.8, None, 0.5)
    # bool is explicitly rejected (avoid True==1 silent coercion)
    with pytest.raises(ValueScoreError):
        value_score(True, 0.6, 0.5)


def test_value_score_never_returns_infinite_or_nan():
    # small positive cost -> large but finite score
    result = value_score(1.0, 1.0, 0.0001)
    assert math.isfinite(result)
