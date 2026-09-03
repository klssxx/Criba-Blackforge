"""Deterministic limitation extraction from evidence fragments (P08-T02)."""
from __future__ import annotations

import re
from typing import Iterable

from ..contracts import EvidenceDocument, Limitation

__all__ = ["LimitationExtractor", "extract_limitations"]

_LIMITATION_CUES = re.compile(
    r"\b(?:limitation|limitations|limited by|limited to|cannot be generalized|"
    r"not generalizable|small sample|shortcoming|constraint|constrained by|"
    r"lack(?:s|ing)?\s+(?:of\s+)?(?:data|evidence|coverage|validation))\b",
    re.IGNORECASE,
)
_RESOLVED_CUE = re.compile(
    r"\b(?:overcomes?|addresses?|resolved?|mitigates?|removes?|"
    r"satisf(?:y|ies|ied)|meets?|eliminates?)\b[^.!?\n]*"
    r"\b(?:limitation|constraint|shortcoming)\b",
    re.IGNORECASE,
)
_NEGATED_RESOLVED_CUE = re.compile(
    r"\b(?:no|never)\s+(?:(?!and\b)[\w-]+\s+){0,3}"
    r"(?:addresses?|addressed|overcomes?|overcome|resolves?|resolved|"
    r"mitigates?|removes?)\b|"
    r"\b(?:does|did|do)\s+not\s+(?:address|overcome|resolve|mitigate|remove)\w*\b",
    re.IGNORECASE,
)
_SENTENCE = re.compile(r"[^.!?\n]+(?:[.!?]|$)")


def _is_resolved(sentence: str) -> bool:
    return bool(_RESOLVED_CUE.search(sentence)) and not _NEGATED_RESOLVED_CUE.search(sentence)


def _sentences(text: str) -> Iterable[str]:
    for match in _SENTENCE.finditer(text):
        sentence = " ".join(match.group(0).split())
        if sentence:
            yield sentence


class LimitationExtractor:
    """Extract limitations while preserving document provenance."""

    def extract(
        self, documents: Iterable[EvidenceDocument], *, scope: str = ""
    ) -> list[Limitation]:
        limitations: list[Limitation] = []
        seen: set[tuple[str, str]] = set()
        for document in documents:
            for fragment in document.fragments:
                for sentence in _sentences(fragment.text):
                    if not _LIMITATION_CUES.search(sentence) or _is_resolved(sentence):
                        continue
                    if scope and scope.casefold() not in sentence.casefold():
                        continue
                    statement = sentence[:500]
                    key = (document.doc_id, statement.casefold())
                    if key in seen:
                        continue
                    seen.add(key)
                    limitations.append(
                        Limitation(
                            statement=statement,
                            scope=scope or document.kind,
                            evidence_doc_ids=(document.doc_id,),
                        )
                    )
        limitations.sort(key=lambda item: (item.evidence_doc_ids, item.statement.casefold()))
        return limitations


def extract_limitations(
    documents: Iterable[EvidenceDocument], *, scope: str = ""
) -> list[Limitation]:
    """Convenience wrapper for deterministic limitation extraction."""
    return LimitationExtractor().extract(documents, scope=scope)
