"""Future-back hypotheses from caller-supplied future states and precursor steps (P09-T14 / T129)."""
from __future__ import annotations

from collections.abc import Mapping, Sequence

from ..contracts import InventionCandidate


def _normalized_future_steps(
    future_steps: Mapping[str, Sequence[str]],
) -> tuple[tuple[str, tuple[str, ...]], ...]:
    """Return explicit future-state/precursor pairs in stable order."""

    normalized: list[tuple[str, tuple[str, ...]]] = []
    for raw_state, raw_steps in future_steps.items():
        state = str(raw_state).strip()
        if not state:
            continue
        if isinstance(raw_steps, str) or not isinstance(raw_steps, (list, tuple, set)):
            return ()
        steps = tuple(sorted({str(step).strip() for step in raw_steps if str(step).strip()}))
        if not steps:
            return ()
        normalized.append((state, steps))
    return tuple(sorted(normalized))


def generate_future_back_hypotheses(
    problem: str,
    future_steps: Mapping[str, Sequence[str]],
    *,
    limit: int = 20,
) -> list[InventionCandidate]:
    """Produce capped T129 prompts by backcasting from supplied future states."""

    normalized_problem = problem.strip()
    if not normalized_problem:
        raise ValueError("problem must not be empty")
    if limit < 0:
        raise ValueError("limit must not be negative")
    if not isinstance(future_steps, Mapping):
        raise TypeError("future_steps must map future states to precursor-step sequences")

    normalized_future_steps = _normalized_future_steps(future_steps)
    if not normalized_future_steps or limit == 0:
        return []

    candidates: list[InventionCandidate] = []
    for future_state, steps in normalized_future_steps:
        for step in steps:
            candidates.append(
                InventionCandidate(
                    title=f"Future-back: {future_state} ← {step}",
                    description=(
                        f"T129 future-back hypothesis for {normalized_problem}: investigate "
                        f"whether {step} is a necessary precursor to the supplied future state "
                        f"{future_state}. This is not evidence and does not establish that the "
                        "future state will be reached, that the step is sufficient, or that the "
                        "path is feasible."
                    ),
                    operators=("T129",),
                )
            )
            if len(candidates) == limit:
                return candidates
    return candidates
