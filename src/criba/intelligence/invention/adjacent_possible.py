"""Corpus-bounded adjacent-possible hypotheses (P09-T12 / T116)."""
from __future__ import annotations

from collections.abc import Sequence
from itertools import combinations

from ..contracts import InventionCandidate


def _normalized_capabilities(capabilities: Sequence[str]) -> tuple[str, ...]:
    if isinstance(capabilities, str) or not isinstance(capabilities, (list, tuple, set)):
        raise TypeError("capabilities must be a sequence of names")
    return tuple(sorted({str(capability).strip() for capability in capabilities if str(capability).strip()}))


def _normalized_known_pairs(known_combinations: Sequence[Sequence[str]]) -> set[tuple[str, str]]:
    if isinstance(known_combinations, str) or not isinstance(known_combinations, (list, tuple, set)):
        raise TypeError("known_combinations must be a sequence of capability pairs")
    pairs: set[tuple[str, str]] = set()
    for raw_pair in known_combinations:
        if isinstance(raw_pair, str) or not isinstance(raw_pair, (list, tuple, set)):
            continue
        values = tuple(sorted({str(value).strip() for value in raw_pair if str(value).strip()}))
        if len(values) == 2:
            pairs.add(values)
    return pairs


def generate_adjacent_possible_hypotheses(
    problem: str,
    capabilities: Sequence[str],
    *,
    known_combinations: Sequence[Sequence[str]] = (),
    limit: int = 20,
) -> list[InventionCandidate]:
    """Return capped T116 prompts for capability pairs absent from known input.

    Absence is measured only against ``known_combinations`` supplied by the
    caller. It is neither a global novelty claim nor evidence of feasibility.
    """

    normalized_problem = problem.strip()
    if not normalized_problem:
        raise ValueError("problem must not be empty")
    if limit < 0:
        raise ValueError("limit must not be negative")
    normalized_capabilities = _normalized_capabilities(capabilities)
    known_pairs = _normalized_known_pairs(known_combinations)
    if len(normalized_capabilities) < 2 or limit == 0:
        return []

    candidates: list[InventionCandidate] = []
    for left, right in combinations(normalized_capabilities, 2):
        if (left, right) in known_pairs:
            continue
        candidates.append(
            InventionCandidate(
                title=f"Adjacent possible: {left} + {right}",
                description=(
                    f"T116 adjacent-possible hypothesis for {normalized_problem}: "
                    f"the explicit capability pair {left} + {right} is absent from the "
                    "caller-supplied known combinations. This is not evidence of global "
                    "novelty, feasibility, compatibility, or value."
                ),
                operators=("T116",),
            )
        )
        if len(candidates) == limit:
            break
    return candidates
