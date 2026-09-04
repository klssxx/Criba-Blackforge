"""Explicit functional-decomposition hypotheses (P09-T08 / T062)."""
from __future__ import annotations

from collections.abc import Mapping, Sequence

from ..contracts import InventionCandidate


def _normalized_functions(
    component_functions: Mapping[str, Sequence[str]],
) -> tuple[tuple[str, tuple[str, ...]], ...]:
    """Return explicit component/function pairs without inferring missing ones."""

    normalized: list[tuple[str, tuple[str, ...]]] = []
    for raw_component, raw_functions in component_functions.items():
        component = str(raw_component).strip()
        if not component:
            continue
        if isinstance(raw_functions, str) or not isinstance(raw_functions, (list, tuple, set)):
            return ()
        functions = tuple(
            sorted({str(function).strip() for function in raw_functions if str(function).strip()})
        )
        if not functions:
            return ()
        normalized.append((component, functions))
    return tuple(sorted(normalized))


def decompose_functional_hypotheses(
    problem: str,
    component_functions: Mapping[str, Sequence[str]],
    *,
    limit: int = 20,
) -> list[InventionCandidate]:
    """Produce capped T062 prompts for functions explicitly assigned to components.

    A decomposition exposes caller-supplied function boundaries. It does not
    identify a mechanism, infer omitted functions, or establish that the
    supplied decomposition is complete or correct.
    """

    normalized_problem = problem.strip()
    if not normalized_problem:
        raise ValueError("problem must not be empty")
    if limit < 0:
        raise ValueError("limit must not be negative")
    if not isinstance(component_functions, Mapping):
        raise TypeError("component_functions must map components to function sequences")

    normalized_functions = _normalized_functions(component_functions)
    if not normalized_functions or limit == 0:
        return []

    candidates: list[InventionCandidate] = []
    for component, functions in normalized_functions:
        for function in functions:
            candidates.append(
                InventionCandidate(
                    title=f"Function: {component} → {function}",
                    description=(
                        f"T062 functional-decomposition hypothesis for {normalized_problem}: "
                        f"{component} is explicitly assigned {function}. This is not evidence "
                        "that the function is complete, correct, feasible, or novel."
                    ),
                    operators=("T062",),
                )
            )
            if len(candidates) == limit:
                return candidates
    return candidates
