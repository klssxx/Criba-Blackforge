"""SCAMPER question prompts that remain hypotheses (P09-T06 / T060)."""
from __future__ import annotations

from ..contracts import InventionCandidate


_SCAMPER_QUESTIONS: tuple[tuple[str, str], ...] = (
    ("Substitute", "What part of {component} could be substituted while preserving {problem}?"),
    ("Combine", "What could {component} be combined with to improve {problem}?"),
    ("Adapt", "What adjacent practice could adapt {component} for {problem}?"),
    ("Modify", "Which attribute of {component} could be modified for {problem}?"),
    ("Put to another use", "What alternative use of {component} could address {problem}?"),
    ("Eliminate", "What can be removed from {component} without losing {problem}?"),
    ("Reverse", "What ordering or direction in {component} could be reversed for {problem}?"),
)


def generate_scamper_hypotheses(
    problem: str, components: list[str] | tuple[str, ...], *, limit: int = 21
) -> list[InventionCandidate]:
    """Produce deterministic SCAMPER investigation prompts, never asserted solutions."""

    normalized_problem = problem.strip()
    if not normalized_problem:
        raise ValueError("problem must not be empty")
    if limit < 0:
        raise ValueError("limit must not be negative")
    normalized_components = tuple(dict.fromkeys(
        component.strip() for component in components if component and component.strip()
    ))
    candidates: list[InventionCandidate] = []
    for component in normalized_components:
        for action, template in _SCAMPER_QUESTIONS:
            question = template.format(component=component, problem=normalized_problem)
            candidates.append(
                InventionCandidate(
                    title=f"{action}: {component}",
                    description=(
                        f"T060 SCAMPER hypothesis prompt: {question} This is a question "
                        "for investigation, not evidence of feasibility or novelty."
                    ),
                    operators=("T060",),
                )
            )
    return candidates[:limit]
