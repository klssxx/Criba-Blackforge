"""First-principles hypothesis decomposition from explicit premises (P09-T10 / T064)."""
from __future__ import annotations

from collections.abc import Mapping, Sequence

from ..contracts import InventionCandidate


def _normalized_premises(
    premise_implications: Mapping[str, Sequence[str]],
) -> tuple[tuple[str, tuple[str, ...]], ...]:
    """Preserve only caller-supplied premises and implications in stable order."""

    normalized: list[tuple[str, tuple[str, ...]]] = []
    for raw_premise, raw_implications in premise_implications.items():
        premise = str(raw_premise).strip()
        if not premise:
            continue
        if isinstance(raw_implications, str) or not isinstance(raw_implications, (list, tuple, set)):
            return ()
        implications = tuple(
            sorted(
                {
                    str(implication).strip()
                    for implication in raw_implications
                    if str(implication).strip()
                }
            )
        )
        if not implications:
            return ()
        normalized.append((premise, implications))
    return tuple(sorted(normalized))


def decompose_first_principles_hypotheses(
    problem: str,
    premise_implications: Mapping[str, Sequence[str]],
    *,
    limit: int = 20,
) -> list[InventionCandidate]:
    """Produce capped T064 investigation prompts from supplied premises.

    The caller owns the validity and provenance of every premise. This function
    makes possible implications inspectable; it does not promote a premise to a
    fact or establish that an implication is feasible, novel, or sufficient.
    """

    normalized_problem = problem.strip()
    if not normalized_problem:
        raise ValueError("problem must not be empty")
    if limit < 0:
        raise ValueError("limit must not be negative")
    if not isinstance(premise_implications, Mapping):
        raise TypeError("premise_implications must map premises to implication sequences")

    normalized_premises = _normalized_premises(premise_implications)
    if not normalized_premises or limit == 0:
        return []

    candidates: list[InventionCandidate] = []
    for premise, implications in normalized_premises:
        for implication in implications:
            candidates.append(
                InventionCandidate(
                    title=f"First principle: {premise} → {implication}",
                    description=(
                        f"T064 first-principles hypothesis for {normalized_problem}: "
                        f"inspect whether the supplied premise {premise} supports {implication}. "
                        "This is not evidence that the premise is true or that the implication "
                        "is feasible, novel, or sufficient."
                    ),
                    operators=("T064",),
                )
            )
            if len(candidates) == limit:
                return candidates
    return candidates
