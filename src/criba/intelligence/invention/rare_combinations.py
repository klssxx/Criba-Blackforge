"""Corpus-local rare-combination hypotheses (P09-T03 / T053)."""
from __future__ import annotations

from collections import Counter, defaultdict
from itertools import combinations

from ..contracts import EvidenceDocument, InventionCandidate


def _concepts(document: EvidenceDocument) -> tuple[str, ...]:
    """Read explicit source concepts only; no terms are inferred from prose."""

    raw = (document.metadata or {}).get("concepts") or ()
    if not isinstance(raw, (list, tuple, set)):
        return ()
    return tuple(sorted({str(item).strip() for item in raw if str(item).strip()}))


def detect_rare_combinations(
    documents: list[EvidenceDocument], *, max_frequency: int = 1, limit: int = 20
) -> list[InventionCandidate]:
    """Return deterministic, corpus-local hypotheses for infrequent concept pairs.

    ``max_frequency`` is a count of source documents, not a novelty score.  A
    result explicitly remains a hypothesis because the supplied corpus can be
    incomplete.
    """

    if max_frequency < 1:
        raise ValueError("max_frequency must be at least one")
    if limit < 0:
        raise ValueError("limit must not be negative")

    pair_documents: dict[tuple[str, str], set[str]] = defaultdict(set)
    for document in documents:
        for pair in combinations(_concepts(document), 2):
            pair_documents[pair].add(document.doc_id)

    candidates: list[InventionCandidate] = []
    for pair, doc_ids in sorted(pair_documents.items()):
        frequency = len(doc_ids)
        if frequency > max_frequency:
            continue
        left, right = pair
        sources = ", ".join(sorted(doc_ids))
        candidates.append(
            InventionCandidate(
                title=f"Explore {left} + {right}",
                description=(
                    f"Corpus-local T053 hypothesis: this explicit concept pair occurs in "
                    f"{frequency} supplied source document(s) ({sources}). It is not a "
                    "global novelty or patentability finding."
                ),
                operators=("T053",),
            )
        )
    return candidates[:limit]
