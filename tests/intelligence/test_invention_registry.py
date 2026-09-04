"""P09-T17: registry state must match implemented invention operators."""
from __future__ import annotations

from pathlib import Path

from criba.intelligence.invention import get_operator
from criba.intelligence.registry import TechniqueRegistry

REGISTRY_PATH = Path(__file__).resolve().parents[2] / "data" / "intelligence" / "technique_registry.yaml"
IMPLEMENTED_OPERATOR_KEYS = (
    "rare_combinations",
    "cross_domain_analogy",
    "triz",
    "morphological_analysis",
    "scamper",
    "functional_decomposition",
    "function_to_mechanism",
    "first_principles",
    "constraint_inversion",
    "adjacent_possible",
    "counterfactual",
    "future_back",
    "bottleneck_mapping",
    "nth_order",
)
EXPECTED_TECHNIQUE_IDS = {
    "T053",
    "T055",
    "T057",
    "T059",
    "T060",
    "T062",
    "T063",
    "T064",
    "T065",
    "T116",
    "T129",
}


def test_implemented_invention_operators_match_registry_contracts():
    registry = TechniqueRegistry(REGISTRY_PATH)
    resolved_ids: set[str] = set()

    for key in IMPLEMENTED_OPERATOR_KEYS:
        definition = get_operator(key)
        assert definition is not None, key
        resolved_ids.update(definition.technique_ids)

    assert resolved_ids == EXPECTED_TECHNIQUE_IDS
    for technique_id in sorted(resolved_ids):
        technique = registry.get(technique_id)
        assert technique.status == "IMPLEMENTED"
        assert technique.implementation
        assert technique.input_contracts
        assert technique.output_contracts
        assert technique.tests
