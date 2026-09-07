"""Evidence-bounded cross-domain transfer hypotheses (P09-T04 / T055)."""
from __future__ import annotations

from collections import defaultdict
from itertools import combinations

from ..contracts import EvidenceDocument, InventionCandidate


def _domain(document: EvidenceDocument) -> str:
    value = (document.metadata or {}).get("domain", "")
    return value.strip() if isinstance(value, str) else ""


def _concepts(document: EvidenceDocument) -> tuple[str, ...]:
    raw = (document.metadata or {}).get("concepts") or ()
    if not isinstance(raw, (list, tuple, set)):
        return ()
    return tuple(sorted({str(item).strip() for item in raw if str(item).strip()}))


def detect_cross_domain_analogies(
    documents: list[EvidenceDocument], *, limit: int = 20
) -> list[InventionCandidate]:
    """Propose transfer hypotheses for explicit concepts shared across domains."""

    if limit < 0:
        raise ValueError("limit must not be negative")
    concept_domains: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    for document in documents:
        domain = _domain(document)
        if not domain:
            continue
        for concept in _concepts(document):
            concept_domains[concept][domain].add(document.doc_id)

    candidates: list[InventionCandidate] = []
    for concept, domains in sorted(concept_domains.items()):
        for source, target in combinations(sorted(domains), 2):
            source_docs = ", ".join(sorted(domains[source]))
            target_docs = ", ".join(sorted(domains[target]))
            candidates.append(
                InventionCandidate(
                    title=f"Transfer {concept}: {source} → {target}",
                    description=(
                        f"Corpus-local T055 hypothesis: {concept} is explicitly present in "
                        f"{source} ({source_docs}) and {target} ({target_docs}). This is a "
                        "transfer prompt, not evidence that the mechanism is feasible."
                    ),
                    operators=("T055",),
                )
            )
    return candidates[:limit]
