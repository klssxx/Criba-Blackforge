"""Bottleneck-mapping hypotheses from explicit observations (P09-T15 / T129)."""
from __future__ import annotations

from collections.abc import Mapping, Sequence

from ..contracts import InventionCandidate


def _normalized_bottleneck_probes(
    bottleneck_probes: Mapping[str, Sequence[str]],
) -> tuple[tuple[str, tuple[str, ...]], ...]:
    """Return only explicit bottleneck/probe pairs in stable order."""

    normalized: list[tuple[str, tuple[str, ...]]] = []
    for raw_bottleneck, raw_probes in bottleneck_probes.items():
        bottleneck = str(raw_bottleneck).strip()
        if not bottleneck:
            continue
        if isinstance(raw_probes, str) or not isinstance(raw_probes, (list, tuple, set)):
            return ()
        probes = tuple(sorted({str(probe).strip() for probe in raw_probes if str(probe).strip()}))
        if not probes:
            return ()
        normalized.append((bottleneck, probes))
    return tuple(sorted(normalized))


def generate_bottleneck_mapping_hypotheses(
    problem: str,
    bottleneck_probes: Mapping[str, Sequence[str]],
    *,
    limit: int = 20,
) -> list[InventionCandidate]:
    """Produce capped T129 prompts for inspecting supplied bottleneck hypotheses."""

    normalized_problem = problem.strip()
    if not normalized_problem:
        raise ValueError("problem must not be empty")
    if limit < 0:
        raise ValueError("limit must not be negative")
    if not isinstance(bottleneck_probes, Mapping):
        raise TypeError("bottleneck_probes must map bottlenecks to probe sequences")

    normalized_bottlenecks = _normalized_bottleneck_probes(bottleneck_probes)
    if not normalized_bottlenecks or limit == 0:
        return []

    candidates: list[InventionCandidate] = []
    for bottleneck, probes in normalized_bottlenecks:
        for probe in probes:
            candidates.append(
                InventionCandidate(
                    title=f"Bottleneck map: {bottleneck} → {probe}",
                    description=(
                        f"T129 bottleneck-mapping hypothesis for {normalized_problem}: inspect "
                        f"the supplied bottleneck {bottleneck} through {probe}. This is not "
                        "evidence and does not establish causality, that this is the limiting "
                        "factor, or that the probe improves the system."
                    ),
                    operators=("T129",),
                )
            )
            if len(candidates) == limit:
                return candidates
    return candidates
