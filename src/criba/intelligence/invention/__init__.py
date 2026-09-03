"""IIE invention sector."""

from .taxonomy import OPERATORS_BY_KEY, OperatorDefinition, get_operator, operator_definitions
from .registry import OperatorContext, OperatorRegistry
from .rare_combinations import detect_rare_combinations
from .cross_domain import detect_cross_domain_analogies

__all__ = [
    "OPERATORS_BY_KEY",
    "OperatorContext",
    "OperatorDefinition",
    "OperatorRegistry",
    "detect_rare_combinations",
    "detect_cross_domain_analogies",
    "get_operator",
    "operator_definitions",
]
