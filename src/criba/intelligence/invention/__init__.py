"""IIE invention sector."""

from .adjacent_possible import generate_adjacent_possible_hypotheses
from .bottlenecks import generate_bottleneck_mapping_hypotheses
from .counterfactual import generate_counterfactual_hypotheses
from .cross_domain import detect_cross_domain_analogies
from .first_principles import decompose_first_principles_hypotheses
from .functions import (
    decompose_functional_hypotheses,
    search_function_to_mechanism_hypotheses,
)
from .future_back import generate_future_back_hypotheses
from .inversion import generate_constraint_inversion_hypotheses
from .morphology import generate_morphological_hypotheses
from .nth_order import generate_nth_order_effect_hypotheses
from .rare_combinations import detect_rare_combinations
from .registry import OperatorContext, OperatorRegistry
from .scamper import generate_scamper_hypotheses
from .taxonomy import (
    OPERATORS_BY_KEY,
    OperatorDefinition,
    get_operator,
    operator_definitions,
)

__all__ = [
    "OPERATORS_BY_KEY",
    "OperatorContext",
    "OperatorDefinition",
    "OperatorRegistry",
    "decompose_first_principles_hypotheses",
    "decompose_functional_hypotheses",
    "detect_cross_domain_analogies",
    "detect_rare_combinations",
    "generate_adjacent_possible_hypotheses",
    "generate_bottleneck_mapping_hypotheses",
    "generate_constraint_inversion_hypotheses",
    "generate_counterfactual_hypotheses",
    "generate_future_back_hypotheses",
    "generate_morphological_hypotheses",
    "generate_nth_order_effect_hypotheses",
    "generate_scamper_hypotheses",
    "get_operator",
    "operator_definitions",
    "search_function_to_mechanism_hypotheses",
]
