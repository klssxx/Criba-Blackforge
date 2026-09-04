"""Frozen operator taxonomy for the IIE invention engine (P09-T01).

This module names the supported operator families without implementing their
heuristics.  Execution is intentionally deferred to the registry (P09-T02),
so callers can distinguish a blueprint-backed capability from an unimplemented
strategy.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from types import MappingProxyType


@dataclass(frozen=True)
class OperatorDefinition:
    """A stable, blueprint-backed description of an invention operator."""

    key: str
    label: str
    family: str
    technique_ids: tuple[str, ...]
    module: str
    description: str = ""
    input_requirements: tuple[str, ...] = ()
    output_contract: str = ""
    deterministic: bool = True
    model_optional: bool = True
    evidence_required: bool = False

    @property
    def id(self) -> str:
        """Stable architectural identifier; ``key`` remains the legacy name."""

        return self.key


_DECLARED_OPERATORS = (
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

_OPERATOR_METADATA: dict[str, tuple[str, tuple[str, ...], str, bool]] = {
    "rare_combinations": ("Find corpus-local low-frequency concept pairs.", ("EvidenceDocument metadata.concepts",), "list[InventionCandidate]", True),
    "technological_recombination": ("Recombine explicit technical attributes.", ("declared technical attributes",), "list[InventionCandidate]", False),
    "cross_domain_analogy": ("Transfer a shared concept across explicit domains.", ("EvidenceDocument metadata.domain and metadata.concepts",), "list[InventionCandidate]", True),
    "biomimicry": ("Generate prompts from declared biological analogies.", ("declared biological evidence",), "list[InventionCandidate]", True),
    "triz": ("Expose traceable TRIZ reasoning prompts.", ("problem or selected TRIZ principle",), "list[InventionCandidate]", False),
    "triz_contradiction_mining": ("Inspect declared engineering contradictions through TRIZ.", ("explicit contradiction evidence",), "list[InventionCandidate]", True),
    "morphological_analysis": ("Enumerate combinations across explicit dimensions.", ("problem", "declared dimensions"), "list[InventionCandidate]", False),
    "scamper": ("Apply seven bounded SCAMPER prompts to components.", ("problem", "declared components"), "list[InventionCandidate]", False),
    "attribute_substitution": ("Substitute declared attributes in a proposal.", ("declared attributes",), "list[InventionCandidate]", False),
    "functional_decomposition": ("Decompose explicit component functions.", ("problem", "component-to-function mapping"), "list[InventionCandidate]", False),
    "function_to_mechanism": ("Find explicit function-mechanism associations in retrieved evidence.", ("requested functions", "retrieved documents"), "list[InventionCandidate]", True),
    "first_principles": ("Relate explicit premises to explicit implications.", ("problem", "premise-to-implication mapping"), "list[InventionCandidate]", False),
    "constraint_inversion": ("Form counterfactuals from declared constraints.", ("problem", "constraint-to-inversion mapping"), "list[InventionCandidate]", False),
    "assumption_mining": ("Inspect assumptions supported by declared evidence.", ("declared assumptions", "evidence"), "list[InventionCandidate]", True),
    "contradiction_mining": ("Inspect contradictions preserved in declared evidence.", ("contradiction evidence",), "list[InventionCandidate]", True),
    "adjacent_possible": ("Enumerate capability pairs absent from a supplied local corpus.", ("problem", "capabilities", "known combinations"), "list[InventionCandidate]", False),
    "counterfactual": ("Inspect supplied alternate scenarios and outcomes.", ("problem", "scenario-to-outcome mapping"), "list[InventionCandidate]", False),
    "future_back": ("Backcast declared precursor steps from declared future states.", ("problem", "future-state-to-step mapping"), "list[InventionCandidate]", False),
    "bottleneck_mapping": ("Inspect supplied bottleneck and probe relationships.", ("problem", "bottleneck-to-probe mapping"), "list[InventionCandidate]", False),
    "nth_order": ("Inspect explicitly supplied multi-step effect chains.", ("problem", "intervention-to-effect-chain mapping"), "list[InventionCandidate]", False),
}

_OPERATORS = tuple(
    replace(
        operator,
        description=_OPERATOR_METADATA[operator.key][0],
        input_requirements=_OPERATOR_METADATA[operator.key][1],
        output_contract=_OPERATOR_METADATA[operator.key][2],
        evidence_required=_OPERATOR_METADATA[operator.key][3],
    )
    for operator in _DECLARED_OPERATORS
)

OPERATORS_BY_KEY = MappingProxyType({operator.key: operator for operator in _OPERATORS})


def operator_definitions() -> tuple[OperatorDefinition, ...]:
    """Return the canonical ordered taxonomy without exposing mutable state."""

    return _OPERATORS


def get_operator(key: str) -> OperatorDefinition | None:
    """Look up one declared operator; unknown keys remain intentionally absent."""

    return OPERATORS_BY_KEY.get(key)
