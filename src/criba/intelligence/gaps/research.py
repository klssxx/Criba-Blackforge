"""Deterministic research-gap extraction from evidence fragments (P08-T01)."""
from __future__ import annotations

import re
from typing import Iterable

from ..contracts import EvidenceDocument, Gap

__all__ = ["ResearchGapExtractor", "extract_research_gaps"]

_GAP_CUES = re.compile(
    r"\b(?:future work|further research|remains? unclear|remains? unknown|"
    r"not (?:yet )?(?:addressed|understood|resolved|studied)|open question|"
    r"research gap|lack(?:s|ing)?\s+(?:of\s+)?(?:data|evidence|understanding|coverage)|"
    r"little is known)\b",
    re.IGNORECASE,
)
_SENTENCE = re.compile(r"[^.!?\n]+(?:[.!?]|$)")
_RESOLVED_CUE = re.compile(
    r"\b(?:addresses?|addressed|resolves?|resolved|answers?|answered)\b.*"
    r"\b(?:open question|research gap|gap)\b",
    re.IGNORECASE,
)


def _sentences(text: str) -> Iterable[str]:
    for match in _SENTENCE.finditer(text):
        sentence = " ".join(match.group(0).split())
        if sentence:
            yield sentence


class ResearchGapExtractor:
    """Extract auditable research gaps from documents without external calls."""

    def extract(
        self, documents: Iterable[EvidenceDocument], *, topic: str = ""
    ) -> list[Gap]:
        gaps: list[Gap] = []
        seen: set[tuple[str, str]] = set()
        for document in documents:
            for fragment in document.fragments:
                for sentence in _sentences(fragment.text):
                    if not _GAP_CUES.search(sentence) or _RESOLVED_CUE.search(sentence):
                        continue
                    statement = sentence[:500]
                    if topic and topic.casefold() not in statement.casefold():
                        continue
                    key = (document.doc_id, statement.casefold())
                    if key in seen:
                        continue
                    seen.add(key)
                    gaps.append(
                        Gap(
                            kind="research",
                            statement=statement,
                            evidence_doc_ids=(document.doc_id,),
                        )
                    )
        gaps.sort(key=lambda gap: (gap.evidence_doc_ids, gap.statement.casefold()))
        return gaps


def extract_research_gaps(
    documents: Iterable[EvidenceDocument], *, topic: str = ""
) -> list[Gap]:
    """Convenience wrapper for deterministic research-gap extraction."""
    return ResearchGapExtractor().extract(documents, topic=topic)
