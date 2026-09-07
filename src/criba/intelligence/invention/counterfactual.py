"""Counterfactual hypotheses from caller-supplied scenarios (P09-T13 / T129)."""
from __future__ import annotations

from collections.abc import Mapping, Sequence

from ..contracts import InventionCandidate


def _normalized_counterfactuals(
    scenario_outcomes: Mapping[str, Sequence[str]],
) -> tuple[tuple[str, tuple[str, ...]], ...]:
    """Keep only explicit scenario/outcome pairs in deterministic order."""

    normalized: list[tuple[str, tuple[str, ...]]] = []
    for raw_scenario, raw_outcomes in scenario_outcomes.items():
        scenario = str(raw_scenario).strip()
        if not scenario:
            continue
        if isinstance(raw_outcomes, str) or not isinstance(raw_outcomes, (list, tuple, set)):
            return ()
        outcomes = tuple(
            sorted({str(outcome).strip() for outcome in raw_outcomes if str(outcome).strip()})
        )
        if not outcomes:
            return ()
        normalized.append((scenario, outcomes))
    return tuple(sorted(normalized))


def generate_counterfactual_hypotheses(
    problem: str,
    scenario_outcomes: Mapping[str, Sequence[str]],
    *,
    limit: int = 20,
) -> list[InventionCandidate]:
    """Produce capped T129 prompts for supplied alternate scenarios and outcomes."""

    normalized_problem = problem.strip()
    if not normalized_problem:
        raise ValueError("problem must not be empty")
    if limit < 0:
        raise ValueError("limit must not be negative")
    if not isinstance(scenario_outcomes, Mapping):
        raise TypeError("scenario_outcomes must map scenarios to outcome sequences")

    normalized_counterfactuals = _normalized_counterfactuals(scenario_outcomes)
    if not normalized_counterfactuals or limit == 0:
        return []

    candidates: list[InventionCandidate] = []
    for scenario, outcomes in normalized_counterfactuals:
        for outcome in outcomes:
            candidates.append(
                InventionCandidate(
                    title=f"Counterfactual: {scenario} → {outcome}",
                    description=(
                        f"T129 counterfactual hypothesis for {normalized_problem}: examine "
                        f"whether {outcome} would follow under the supplied scenario {scenario}. "
                        "This is not evidence and does not predict the outcome, establish "
                        "causality, feasibility, or novelty."
                    ),
                    operators=("T129",),
                )
            )
            if len(candidates) == limit:
                return candidates
    return candidates
