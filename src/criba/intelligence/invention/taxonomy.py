"""Frozen operator taxonomy for the IIE invention engine (P09-T01).

This module names the supported operator families without implementing their
heuristics.  Execution is intentionally deferred to the registry (P09-T02),
so callers can distinguish a blueprint-backed capability from an unimplemented
strategy.
"""
from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType


@dataclass(frozen=True)
class OperatorDefinition:
    """A stable, blueprint-backed description of an invention operator."""

    key: str
    label: str
    family: str
    technique_ids: tuple[str, ...]
    module: str


_OPERATORS = (
    OperatorDefinition("rare_combinations", "Rare-combination detection", "recombination", ("T053",), "invention.rare_combinations"),
    OperatorDefinition("technological_recombination", "Technological recombination", "recombination", ("T054",), "invention.recombination"),
    OperatorDefinition("cross_domain_analogy", "Cross-domain analogy", "analogy", ("T055",), "invention.cross_domain"),
    OperatorDefinition("biomimicry", "Biomimicry", "analogy", ("T056",), "invention.biomimicry"),
    OperatorDefinition("triz", "TRIZ", "systematic", ("T057",), "invention.triz"),
    OperatorDefinition("triz_contradiction_mining", "TRIZ contradiction mining", "systematic", ("T058",), "invention.triz"),
    OperatorDefinition("morphological_analysis", "Morphological analysis", "systematic", ("T059",), "invention.morphology"),
    OperatorDefinition("scamper", "SCAMPER", "systematic", ("T060",), "invention.scamper"),
    OperatorDefinition("attribute_substitution", "Attribute substitution", "recombination", ("T061",), "invention.recombination"),
    OperatorDefinition("functional_decomposition", "Functional decomposition", "decomposition", ("T062",), "invention.functions"),
    OperatorDefinition("function_to_mechanism", "Function-to-mechanism search", "decomposition", ("T063",), "invention.functions"),
    OperatorDefinition("first_principles", "First-principles decomposition", "decomposition", ("T064",), "invention.first_principles"),
    OperatorDefinition("constraint_inversion", "Constraint inversion", "constraint", ("T065",), "invention.inversion"),
    OperatorDefinition("assumption_mining", "Assumption mining", "constraint", ("T066",), "invention.assumptions"),
    OperatorDefinition("contradiction_mining", "Contradiction mining", "constraint", ("T067",), "gaps.contradictions"),
    OperatorDefinition("adjacent_possible", "Adjacent possible", "temporal", ("T116",), "invention.adjacent_possible"),
    OperatorDefinition("counterfactual", "Counterfactual", "temporal", ("T129",), "invention.counterfactual"),
    OperatorDefinition("future_back", "Future-back", "temporal", ("T129",), "invention.future_back"),
    OperatorDefinition("bottleneck_mapping", "Bottleneck mapping", "temporal", ("T129",), "invention.bottlenecks"),
    OperatorDefinition("nth_order", "Second/Nth-order reasoning", "temporal", ("T129",), "invention.nth_order"),
)

OPERATORS_BY_KEY = MappingProxyType({operator.key: operator for operator in _OPERATORS})


def operator_definitions() -> tuple[OperatorDefinition, ...]:
    """Return the canonical ordered taxonomy without exposing mutable state."""

    return _OPERATORS


def get_operator(key: str) -> OperatorDefinition | None:
    """Look up one declared operator; unknown keys remain intentionally absent."""

    return OPERATORS_BY_KEY.get(key)
