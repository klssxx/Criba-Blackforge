"""IIE invention sector."""

from .taxonomy import OPERATORS_BY_KEY, OperatorDefinition, get_operator, operator_definitions
from .registry import OperatorContext, OperatorRegistry
from .rare_combinations import detect_rare_combinations
from .cross_domain import detect_cross_domain_analogies
from .morphology import generate_morphological_hypotheses
from .scamper import generate_scamper_hypotheses

__all__ = [
    "OPERATORS_BY_KEY",
    "OperatorContext",
    "OperatorDefinition",
    "OperatorRegistry",
    "detect_rare_combinations",
    "detect_cross_domain_analogies",
    "generate_morphological_hypotheses",
    "generate_scamper_hypotheses",
    "get_operator",
    "operator_definitions",
]
