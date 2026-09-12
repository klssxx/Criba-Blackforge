"""Tests for the data-oriented TRIZ registry (P09-T05 / T057)."""
from __future__ import annotations

import dataclasses

import pytest

from criba.intelligence.invention.registry import OperatorContext, OperatorRegistry
from criba.intelligence.invention.triz import (
    CONTRADICTION_MATRIX_AVAILABLE,
    PRINCIPLES_COUNT,
    TRIZ_TECHNIQUE_ID,
    TrizPrinciple,
    generate_triz_hypotheses,
    get_principle,
    list_principles,
)


def triz_handler(context: OperatorContext):
    return generate_triz_hypotheses(context.problem)


def test_registry_contains_exactly_40_principles():
    principles = list_principles()
    assert len(principles) == PRINCIPLES_COUNT == 40


def test_numbers_unique_and_cover_1_to_40():
    numbers = [p.number for p in list_principles()]
    assert sorted(numbers) == list(range(1, 41))
    assert len(set(numbers)) == 40


def test_order_is_stable_across_calls():
    first = list_principles()
    second = list_principles()
    assert first is not None and second is not None
    assert [p.number for p in first] == [p.number for p in second] == list(range(1, 41))


def test_first_and_last_are_canonical_boundaries():
    assert get_principle(1).name == "Segmentation"
    assert get_principle(40).name == "Composite materials"


@pytest.mark.parametrize("number", [1, 7, 25, 40])
def test_lookup_valid_returns_matching_principle(number):
    principle = get_principle(number)
    assert isinstance(principle, TrizPrinciple)
    assert principle.number == number
    assert principle.name.strip()
    assert principle.description.strip()


@pytest.mark.parametrize("number", [-3, 0, 41, 99])
def test_lookup_invalid_raises_key_error(number):
    with pytest.raises(KeyError):
        get_principle(number)


def test_every_principle_traceable_to_t057():
    assert TRIZ_TECHNIQUE_ID == "T057"
    for principle in list_principles():
        assert principle.technique_id == "T057"
    assert get_principle(7).technique_id == "T057"


def test_principles_are_immutable():
    principle = get_principle(13)
    with pytest.raises(dataclasses.FrozenInstanceError):
        principle.name = "mutated"


def test_no_contradiction_matrix_is_claimed():
    # Honest limit: without a sourced, licensed dataset the module must not
    # pretend to offer the 39x39 matrix.
    assert CONTRADICTION_MATRIX_AVAILABLE is False


def test_principle_dataclass_rejects_invalid_numbers():
    with pytest.raises(ValueError):
        TrizPrinciple(number=0, name="bad", description="out of range")
    with pytest.raises(ValueError):
        TrizPrinciple(number=41, name="bad", description="out of range")


def test_principle_dataclass_rejects_untraceable_technique_id():
    with pytest.raises(ValueError, match="technique_id"):
        TrizPrinciple(number=1, name="Segmentation", description="valid", technique_id="T999")


# --- operator mapping (registry wiring) -------------------------------------

def test_triz_operator_registered_and_traceable_to_t057():
    registry = OperatorRegistry()
    definition = registry.definition("triz")
    assert definition.technique_ids == ("T057",)
    registry.register("triz", triz_handler)
    context = OperatorContext(problem="control autonomous agents without central authority")
    candidates = list(registry.execute("triz", context))
    assert len(candidates) == 40
    assert all(candidate.operators == ("T057",) for candidate in candidates)


def test_triz_operator_uses_context_problem_and_is_deterministic():
    registry = OperatorRegistry()
    registry.register("triz", triz_handler)
    first = list(registry.execute("triz", OperatorContext(problem="reduce heat")))
    second = list(registry.execute("triz", OperatorContext(problem="reduce heat")))
    assert [c.title for c in first] == [c.title for c in second]
    assert all("reduce heat" in c.description for c in first)
    assert first[0].title.startswith("TRIZ 01: Segmentation")


def test_triz_hypotheses_validate_inputs():
    with pytest.raises(ValueError, match="problem"):
        generate_triz_hypotheses("   ")
    with pytest.raises(ValueError, match="limit"):
        generate_triz_hypotheses("reduce heat", limit=-1)
    assert len(generate_triz_hypotheses("reduce heat", limit=3)) == 3
    assert len(generate_triz_hypotheses("reduce heat")) == 40


def test_package_exports_triz_operator_symbol():
    from criba.intelligence import invention

    assert invention.generate_triz_hypotheses is generate_triz_hypotheses
    assert "generate_triz_hypotheses" in invention.__all__


def test_triz_operator_prompts_disclaim_feasibility():
    for candidate in generate_triz_hypotheses("reduce heat", limit=5):
        assert "not evidence" in candidate.description
