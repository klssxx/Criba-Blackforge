"""IIE invention sector."""

from .taxonomy import OPERATORS_BY_KEY, OperatorDefinition, get_operator, operator_definitions
from .registry import OperatorContext, OperatorRegistry
from .rare_combinations import detect_rare_combinations

__all__ = [
    "OPERATORS_BY_KEY",
    "OperatorContext",
    "OperatorDefinition",
    "OperatorRegistry",
    "detect_rare_combinations",
    "get_operator",
    "operator_definitions",
]
