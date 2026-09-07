"""Deterministic morphological hypotheses from explicit dimensions (P09-T07 / T059)."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from itertools import product

from ..contracts import InventionCandidate


def _normalized_dimensions(
    dimensions: Mapping[str, Sequence[str]],
) -> tuple[tuple[str, tuple[str, ...]], ...]:
    """Return an ordered product space without inferring missing dimensions."""

    normalized: list[tuple[str, tuple[str, ...]]] = []
    for raw_name, raw_values in dimensions.items():
        name = str(raw_name).strip()
        if not name:
            continue
        if isinstance(raw_values, str) or not isinstance(raw_values, (list, tuple, set)):
            return ()
        values = tuple(sorted({str(value).strip() for value in raw_values if str(value).strip()}))
        if not values:
            return ()
        normalized.append((name, values))
    return tuple(sorted(normalized))


def generate_morphological_hypotheses(
    problem: str,
    dimensions: Mapping[str, Sequence[str]],
    *,
    limit: int = 20,
) -> list[InventionCandidate]:
    """Enumerate capped, traceable T059 hypotheses from caller-supplied axes.

    This does not infer dimensions or establish feasibility, compatibility, or
    novelty. It only makes combinations in the explicitly supplied product
    space available for later evidence-based investigation.
    """

    normalized_problem = problem.strip()
    if not normalized_problem:
        raise ValueError("problem must not be empty")
    if limit < 0:
        raise ValueError("limit must not be negative")
    if not isinstance(dimensions, Mapping):
        raise TypeError("dimensions must be a mapping of names to value sequences")

    normalized_dimensions = _normalized_dimensions(dimensions)
    if not normalized_dimensions or limit == 0:
        return []

    names = tuple(name for name, _ in normalized_dimensions)
    value_spaces = tuple(values for _, values in normalized_dimensions)
    candidates: list[InventionCandidate] = []
    for values in product(*value_spaces):
        combination = "; ".join(
            f"{name}={value}" for name, value in zip(names, values, strict=True)
        )
        candidates.append(
            InventionCandidate(
                title=f"Morphology: {combination}",
                description=(
                    f"T059 morphological hypothesis for {normalized_problem}: {combination}. "
                    "This deterministic combination enumerates only supplied dimensions; "
                    "it is not evidence of feasibility, novelty, or compatibility."
                ),
                operators=("T059",),
            )
        )
        if len(candidates) == limit:
            break
    return candidates
