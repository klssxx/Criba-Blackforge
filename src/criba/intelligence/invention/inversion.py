"""Constraint-inversion hypotheses that preserve the original constraint (P09-T11 / T065)."""
from __future__ import annotations

from collections.abc import Mapping, Sequence

from ..contracts import InventionCandidate


def _normalized_inversions(
    constraint_inversions: Mapping[str, Sequence[str]],
) -> tuple[tuple[str, tuple[str, ...]], ...]:
    """Return only caller-supplied counterfactuals in deterministic order."""

    normalized: list[tuple[str, tuple[str, ...]]] = []
    for raw_constraint, raw_inversions in constraint_inversions.items():
        constraint = str(raw_constraint).strip()
        if not constraint:
            continue
        if isinstance(raw_inversions, str) or not isinstance(raw_inversions, (list, tuple, set)):
            return ()
        inversions = tuple(
            sorted(
                {
                    str(inversion).strip()
                    for inversion in raw_inversions
                    if str(inversion).strip()
                }
            )
        )
        if not inversions:
            return ()
        normalized.append((constraint, inversions))
    return tuple(sorted(normalized))


def generate_constraint_inversion_hypotheses(
    problem: str,
    constraint_inversions: Mapping[str, Sequence[str]],
    *,
    limit: int = 20,
) -> list[InventionCandidate]:
    """Generate capped T065 counterfactual prompts from explicit inversions.

    An inversion is a question to investigate. The original constraint remains
    in force unless independent evidence shows otherwise.
    """

    normalized_problem = problem.strip()
    if not normalized_problem:
        raise ValueError("problem must not be empty")
    if limit < 0:
        raise ValueError("limit must not be negative")
    if not isinstance(constraint_inversions, Mapping):
        raise TypeError("constraint_inversions must map constraints to inversion sequences")

    normalized_inversions = _normalized_inversions(constraint_inversions)
    if not normalized_inversions or limit == 0:
        return []

    candidates: list[InventionCandidate] = []
    for constraint, inversions in normalized_inversions:
        for inversion in inversions:
            candidates.append(
                InventionCandidate(
                    title=f"Constraint inversion: {constraint} → {inversion}",
                    description=(
                        f"T065 constraint-inversion hypothesis for {normalized_problem}: "
                        f"investigate the counterfactual {inversion} against the current "
                        f"constraint {constraint}. This is not evidence and does not establish "
                        "that the constraint is removed, changed, feasible, or irrelevant."
                    ),
                    operators=("T065",),
                )
            )
            if len(candidates) == limit:
                return candidates
    return candidates
