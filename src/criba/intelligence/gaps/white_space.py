"""Deterministic white-space analysis over evidence documents (P08-T06 / T086)."""
from __future__ import annotations

import re
from typing import Any, Iterable

from ..contracts import EvidenceDocument, WhiteSpaceCandidate

__all__ = [
    "WhiteSpaceAnalyzer",
    "WhiteSpaceExtractor",
    "WhiteSpaceEngine",
    "analyze_white_spaces",
    "analyze_white_space",
    "extract_white_spaces",
    "find_white_spaces",
]

_SPACE_CUES = re.compile(
    r"\b(?:white[- ]space|whitespace|"
    r"(?:few|little|scarce)\s+(?:stud(?:y|ies)|research|evidence|data|"
    r"patents?|products?|coverage|options?|solutions?)|"
    r"underexplored|unexplored|unaddressed|overlooked|underserved|"
    r"no\s+(?:research|stud(?:y|ies)|patent|product|coverage)|"
    r"lack(?:s|ing)?\s+of|not\s+(?:covered|addressed|served))\b",
    re.IGNORECASE,
)
_RESOLVED_CUE = re.compile(
    r"\b(?:fills?|closes?|addresses?|solves?|covers?|serves?|"
    r"eliminates?|resolves?)\b[^.!?\n]*\b(?:gap|white[- ]space|"
    r"underserved|unserved|unexplored)\b",
    re.IGNORECASE,
)
_NEGATED_RESOLVED_CUE = re.compile(
    r"\b(?:no|never)\s+(?:(?!(?:and|but|yet|however)\b)[\w-]+\s+){0,3}"
    r"(?:addresses?|addressed|fills?|closes?|solves?|covers?|serves?|"
    r"resolves?)\b|"
    r"\b(?:does|did|do)\s+not\s+(?:address|fill|close|solve|cover|serve|resolve)\w*\b",
    re.IGNORECASE,
)
_SENTENCE = re.compile(r"[^.!?\n]+(?:[.!?]|$)")


def _is_resolved(sentence: str) -> bool:
    return bool(_RESOLVED_CUE.search(sentence)) and not _NEGATED_RESOLVED_CUE.search(sentence)


def _sentences(text: str) -> list[str]:
    sentences: list[str] = []
    for match in _SENTENCE.finditer(text):
        sentence = " ".join(match.group(0).split())
        if sentence:
            sentences.append(sentence)
    return sentences


def _text(value: Any) -> str:
    if isinstance(value, (list, tuple)):
        return "; ".join(str(item).strip() for item in value if str(item).strip())
    return str(value).strip() if value is not None else ""


def _clean(value: str) -> str:
    return " ".join(value.split()).strip(" ,:;-\t")[:500]


def _space_type(text: str, document: EvidenceDocument, requested: str = "") -> str:
    requested_type = requested.casefold().strip()
    if requested_type in {"patent", "research", "market"}:
        return requested_type
    lowered = text.casefold()
    if re.search(r"\b(?:patent|patents|intellectual property|\bip\b)\b", lowered):
        return "patent"
    if re.search(
        r"\b(?:market|product|customer|consumer|commercial|industry|user|served|service)\b",
        lowered,
    ):
        return "market"
    if document.kind.casefold() in {"patent", "ip"}:
        return "patent"
    if document.kind.casefold() in {"product", "market", "commercial"}:
        return "market"
    return "research"


def _metadata_candidate(document: EvidenceDocument) -> WhiteSpaceCandidate | None:
    metadata = document.metadata
    statement = _clean(_text(metadata.get("statement", "")))
    if not statement:
        statement = _clean(_text(metadata.get("white_space_statement", "")))
    if not statement:
        return None
    explicit = metadata.get("white_space")
    explicit_enabled = str(explicit).casefold() in {"true", "1", "yes"}
    if explicit is not None and not explicit_enabled:
        return None
    if not explicit_enabled and not _SPACE_CUES.search(statement):
        return None
    requested = _text(metadata.get("space_type", ""))
    return WhiteSpaceCandidate(
        statement=statement,
        evidence_doc_ids=(document.doc_id,),
        space_type=_space_type(statement, document, requested),
    )


class WhiteSpaceAnalyzer:
    """Find explicit evidence of under-covered research, patent or market areas."""

    def analyze(
        self,
        documents: Iterable[EvidenceDocument],
        *,
        space_type: str = "",
        topic: str = "",
    ) -> list[WhiteSpaceCandidate]:
        requested_type = space_type.casefold().strip()
        if requested_type and requested_type not in {"patent", "research", "market"}:
            return []
        candidates: list[WhiteSpaceCandidate] = []
        seen: set[tuple[str, str]] = set()
        for document in documents:
            metadata_candidate = _metadata_candidate(document)
            extracted = [metadata_candidate] if metadata_candidate else []
            extracted.extend(
                WhiteSpaceCandidate(
                    statement=sentence,
                    evidence_doc_ids=(document.doc_id,),
                    space_type=_space_type(sentence, document),
                )
                for fragment in document.fragments
                for sentence in _sentences(fragment.text)
                if _SPACE_CUES.search(sentence) and not _is_resolved(sentence)
            )
            for candidate in extracted:
                if requested_type and candidate.space_type != requested_type:
                    continue
                if topic and topic.casefold() not in candidate.statement.casefold():
                    continue
                key = (document.doc_id, candidate.statement.casefold())
                if key in seen:
                    continue
                seen.add(key)
                candidates.append(candidate)
        candidates.sort(key=lambda item: (item.evidence_doc_ids, item.statement.casefold()))
        return candidates


WhiteSpaceExtractor = WhiteSpaceAnalyzer
WhiteSpaceEngine = WhiteSpaceAnalyzer


def analyze_white_spaces(
    documents: Iterable[EvidenceDocument], *, space_type: str = "", topic: str = ""
) -> list[WhiteSpaceCandidate]:
    """Convenience wrapper for deterministic white-space analysis."""
    return WhiteSpaceAnalyzer().analyze(documents, space_type=space_type, topic=topic)


def analyze_white_space(
    documents: Iterable[EvidenceDocument], *, space_type: str = "", topic: str = ""
) -> list[WhiteSpaceCandidate]:
    """Singular alias for callers treating the engine as one analysis."""
    return analyze_white_spaces(documents, space_type=space_type, topic=topic)


def extract_white_spaces(
    documents: Iterable[EvidenceDocument], *, space_type: str = "", topic: str = ""
) -> list[WhiteSpaceCandidate]:
    """Alias for extraction-oriented callers."""
    return analyze_white_spaces(documents, space_type=space_type, topic=topic)


def find_white_spaces(
    documents: Iterable[EvidenceDocument], *, space_type: str = "", topic: str = ""
) -> list[WhiteSpaceCandidate]:
    """Alias for discovery-oriented callers."""
    return analyze_white_spaces(documents, space_type=space_type, topic=topic)
