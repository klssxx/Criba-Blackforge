"""Contract tests for the frozen P09 invention operator taxonomy."""
from __future__ import annotations

import pytest

from criba.intelligence.invention import OPERATORS_BY_KEY, get_operator, operator_definitions


def test_taxonomy_is_complete_for_blueprint_invention_techniques():
    technique_ids = {technique for operator in operator_definitions() for technique in operator.technique_ids}
    assert {f"T{number:03d}" for number in range(53, 68)} <= technique_ids
    assert "T129" in technique_ids
    assert len(OPERATORS_BY_KEY) == len(operator_definitions())


def test_taxonomy_lookup_is_stable_and_does_not_make_up_unknown_operators():
    operator = get_operator("function_to_mechanism")
    assert operator is not None
    assert operator.technique_ids == ("T063",)
    assert get_operator("unsupported_magic_operator") is None


def test_taxonomy_mapping_cannot_be_mutated_by_consumers():
    with pytest.raises(TypeError):
        OPERATORS_BY_KEY["invented"] = get_operator("triz")
