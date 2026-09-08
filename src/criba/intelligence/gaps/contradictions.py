"""Deterministic contradiction analysis over extracted claims (P08-T03)."""
from __future__ import annotations

import re
from collections import defaultdict
from typing import Iterable

from ..contracts import Claim, Contradiction, EvidenceDocument

__all__ = ["ContradictionAnalyzer", "analyze_contradictions"]

_OPPOSITES = {
    "increases": "decreases", "decreases": "increases",
    "improves": "worsens", "worsens": "improves",
    "enables": "prevents", "prevents": "enables",
    "supports": "disputes", "disputes": "supports",
}
_CLAIM_SHAPE = re.compile(
    r"^(?P<subject>.+?)\s+(?P<verb>increases|decreases|improves|worsens|"
    r"enables|prevents|supports|disputes)\s+(?P<object>.+)$", re.IGNORECASE
)


def _key(text: str) -> tuple[str, str, str] | None:
    match = _CLAIM_SHAPE.match(" ".join(text.split()))
    if not match:
        return None
    return tuple(match.group(part).casefold().strip() for part in ("subject", "verb", "object"))  # type: ignore[return-value]


class ContradictionAnalyzer:
    """Find opposing claims sharing normalized subject and object."""

    def analyze(
        self, claims: Iterable[Claim], documents: Iterable[EvidenceDocument] = ()
    ) -> list[Contradiction]:
        by_key: dict[tuple[str, str, str], list[Claim]] = defaultdict(list)
        for claim in claims:
            parsed = _key(claim.text)
            if parsed:
                by_key[parsed].append(claim)
        out: list[Contradiction] = []
        seen: set[tuple[str, str, str, str]] = set()
        for (subject, verb, obj), left_claims in sorted(by_key.items()):
            opposite = _OPPOSITES[verb]
            right_claims = by_key.get((subject, opposite, obj), [])
            for left in left_claims:
                for right in right_claims:
                    doc_a = left.evidence_doc_ids[0] if left.evidence_doc_ids else left.claim_id
                    doc_b = right.evidence_doc_ids[0] if right.evidence_doc_ids else right.claim_id
                    pair = (subject, obj, min(doc_a, doc_b), max(doc_a, doc_b))
                    if pair in seen:
                        continue
                    seen.add(pair)
                    out.append(Contradiction(
                        statement=f"{left.text} ↔ {right.text}",
                        evidence_doc_ids=tuple(dict.fromkeys(left.evidence_doc_ids + right.evidence_doc_ids)),
                        doc_a=doc_a,
                        doc_b=doc_b,
                    ))
        return out


def analyze_contradictions(
    claims: Iterable[Claim], documents: Iterable[EvidenceDocument] = ()
) -> list[Contradiction]:
    """Convenience wrapper for contradiction analysis."""
    return ContradictionAnalyzer().analyze(claims, documents)
