"""IIE invention sector."""

from .cross_domain import detect_cross_domain_analogies
from .first_principles import decompose_first_principles_hypotheses
from .functions import (
    decompose_functional_hypotheses,
    search_function_to_mechanism_hypotheses,
)
from .morphology import generate_morphological_hypotheses
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
    "generate_morphological_hypotheses",
    "generate_scamper_hypotheses",
    "get_operator",
    "operator_definitions",
    "search_function_to_mechanism_hypotheses",
]
