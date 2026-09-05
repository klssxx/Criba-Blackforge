"""Second- and nth-order effect hypotheses from explicit chains (P09-T16 / T129)."""
from __future__ import annotations

from collections.abc import Mapping, Sequence

from ..contracts import InventionCandidate


def _normalized_effect_chains(
    intervention_chains: Mapping[str, Sequence[Sequence[str]]],
) -> tuple[tuple[str, tuple[tuple[str, ...], ...]], ...]:
    """Return explicit intervention/effect-chain pairs in deterministic order."""

    normalized: list[tuple[str, tuple[tuple[str, ...], ...]]] = []
    for raw_intervention, raw_chains in intervention_chains.items():
        intervention = str(raw_intervention).strip()
        if not intervention:
            continue
        if isinstance(raw_chains, str) or not isinstance(raw_chains, (list, tuple)):
            return ()
        chains: set[tuple[str, ...]] = set()
        for raw_chain in raw_chains:
            if isinstance(raw_chain, str) or not isinstance(raw_chain, (list, tuple)):
                continue
            chain = tuple(str(effect).strip() for effect in raw_chain if str(effect).strip())
            if len(chain) >= 2:
                chains.add(chain)
        if not chains:
            return ()
        normalized.append((intervention, tuple(sorted(chains))))
    return tuple(sorted(normalized))


def generate_nth_order_effect_hypotheses(
    problem: str,
    intervention_chains: Mapping[str, Sequence[Sequence[str]]],
    *,
    limit: int = 20,
) -> list[InventionCandidate]:
    """Produce capped T129 prompts for supplied second- and nth-order chains."""

    normalized_problem = problem.strip()
    if not normalized_problem:
        raise ValueError("problem must not be empty")
    if limit < 0:
        raise ValueError("limit must not be negative")
    if not isinstance(intervention_chains, Mapping):
        raise TypeError("intervention_chains must map interventions to effect-chain sequences")

    normalized_chains = _normalized_effect_chains(intervention_chains)
    if not normalized_chains or limit == 0:
        return []

    candidates: list[InventionCandidate] = []
    for intervention, chains in normalized_chains:
        for chain in chains:
            chain_text = " → ".join(chain)
            candidates.append(
                InventionCandidate(
                    title=f"Nth-order: {intervention} → {chain_text}",
                    description=(
                        f"T129 nth-order-effect hypothesis for {normalized_problem}: inspect "
                        f"the supplied chain {intervention} → {chain_text}. This is not evidence "
                        "and does not establish that the effect chain will occur, that each link "
                        "is causal, or that the intervention is feasible."
                    ),
                    operators=("T129",),
                )
            )
            if len(candidates) == limit:
                return candidates
    return candidates
