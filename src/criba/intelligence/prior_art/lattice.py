"""Deterministic prior-art query lattice (P10-T02)."""
from __future__ import annotations

from collections.abc import Sequence

from ..contracts import QueryVariant
from ..retrieval.expansion import QueryExpander


def build_query_lattice(
    query: str,
    *,
    classifications: Sequence[str] = (),
    max_variants: int = 20,
) -> list[QueryVariant]:
    """Build traceable query variants without performing any external search.

    The existing P04 ``QueryExpander`` owns literal, synonym, ontology,
    multilingual and decomposition variants.  This P10 layer adds explicit
    CPC/IPC-style classification queries and imposes a stable total cap.
    """

    normalized_query = query.strip()
    if not normalized_query:
        raise ValueError("query must not be blank")
    if max_variants < 1:
        raise ValueError("max_variants must be at least 1")

    expanded = QueryExpander(max_variants=max_variants).expand(normalized_query).variants
    normalized_classifications = tuple(
        sorted({str(classification).strip() for classification in classifications if str(classification).strip()})
    )
    classification_variants = [
        QueryVariant(
            text=f"{classification} {normalized_query}",
            origin="classification",
            technique_ids=("T003",),
        )
        for classification in normalized_classifications
    ]

    seen: set[tuple[str, str]] = set()
    lattice: list[QueryVariant] = []
    for variant in [*expanded, *classification_variants]:
        key = (variant.text, variant.language)
        if key not in seen:
            seen.add(key)
            lattice.append(variant)
        if len(lattice) == max_variants:
            break
    return lattice
