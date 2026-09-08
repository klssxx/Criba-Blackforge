"""Deterministic, evidence-gated technology resurrection (P08-T05 / T071)."""
from __future__ import annotations

import re
from typing import Any, Iterable

from ..contracts import EvidenceDocument, ResurrectionCandidate

__all__ = [
    "ResurrectionCandidateExtractor",
    "ResurrectionExtractor",
    "TechnologyResurrectionExtractor",
    "TechnologyResurrection",
    "extract_resurrection_candidates",
    "find_resurrection_candidates",
    "extract_resurrection",
]

_HISTORICAL_CUE = re.compile(
    r"\b(?:abandoned|shelved|discarded|discontinued|dropped|rejected|"
    r"obsolete|dormant|failed|infeasible|impractical|could not|unable to)\b",
    re.IGNORECASE,
)
_CURRENT_CUE = re.compile(
    r"\b(?:now|today|currently|recent|modern|new|advance|advances|"
    r"improved|available|demonstrates?|shows?|feasible|viable|practical|"
    r"workable|prototype)\b",
    re.IGNORECASE,
)
_CHANGE_CUE = re.compile(
    r"\b(?:overcame?|overcome|resolved|removed|reduced|increased|improved|"
    r"available|advances?|new|now|changed|下降|突破)\b",
    re.IGNORECASE,
)
_NO_EVIDENCE_CUE = re.compile(
    r"\b(?:no|without|lacks?|lack of|not)\s+(?:current\s+)?"
    r"(?:evidence|proof|data)\b",
    re.IGNORECASE,
)
_SENTENCE = re.compile(r"[^.!?\n]+(?:[.!?]|$)")
_IDEA_RE = re.compile(
    r"^(?P<idea>.+?)\s+(?:was|were|became|proved)\s+"
    r"(?:abandoned|shelved|discarded|discontinued|dropped|rejected|obsolete)\b",
    re.IGNORECASE,
)
_CAUSE_RE = re.compile(
    r"\b(?:because|due to|owing to|limited by|constrained by|"
    r"constraint\s*(?:was|:)?|could not|unable to)\s+"
    r"(?P<cause>[^.!?;\n]+)",
    re.IGNORECASE,
)
_FEASIBILITY_RE = re.compile(
    r"(?P<value>[^.!?\n]*\b(?:feasible|viable|practical|workable|"
    r"possible|can now|now works)\b[^.!?\n]*)",
    re.IGNORECASE,
)
_REQUIRED_FIELDS = (
    "historical_idea",
    "historical_failure_reason",
    "blocking_constraint",
    "current_evidence",
    "constraint_change",
    "new_feasibility",
)


def _sentences(text: str) -> list[str]:
    return [
        " ".join(match.group(0).split())
        for match in _SENTENCE.finditer(text)
        if " ".join(match.group(0).split())
    ]


def _text(value: Any) -> str:
    if isinstance(value, (list, tuple)):
        return "; ".join(str(item).strip() for item in value if str(item).strip())
    return str(value).strip() if value is not None else ""


def _clean(value: str) -> str:
    return " ".join(value.split()).strip(" ,:;-\t")[:500]


def _cause(sentence: str) -> str:
    match = _CAUSE_RE.search(sentence)
    return _clean(match.group("cause")) if match else ""


def _idea(sentence: str) -> str:
    match = _IDEA_RE.match(sentence)
    if match:
        return _clean(match.group("idea"))
    cause = _CAUSE_RE.search(sentence)
    if cause:
        return _clean(sentence[: cause.start()])
    return ""


def _feasibility(sentence: str) -> str:
    match = _FEASIBILITY_RE.search(sentence)
    return _clean(match.group("value")) if match else ""


def _confidence(values: dict[str, str]) -> float:
    supported = sum(bool(values[field]) for field in _REQUIRED_FIELDS)
    return round(supported / len(_REQUIRED_FIELDS), 3)


def _metadata_candidate(document: EvidenceDocument) -> ResurrectionCandidate | None:
    metadata = document.metadata
    values = {field: _text(metadata.get(field, "")) for field in _REQUIRED_FIELDS}
    if not all(values.values()):
        return None
    evidence_text = f"{values['current_evidence']} {values['constraint_change']}"
    if _NO_EVIDENCE_CUE.search(evidence_text):
        return None
    confidence_text = _text(metadata.get("resurrection_confidence", ""))
    try:
        confidence = float(confidence_text) if confidence_text else _confidence(values)
    except ValueError:
        confidence = _confidence(values)
    confidence = min(1.0, max(0.0, confidence))
    statement = _text(metadata.get("statement", "")) or (
        f"{values['historical_idea']}: {values['historical_failure_reason']}; "
        f"current evidence: {values['current_evidence']}"
    )
    return ResurrectionCandidate(
        statement=_clean(statement),
        evidence_doc_ids=(document.doc_id,),
        dormant_since=_text(metadata.get("dormant_since", "")) or document.published,
        unlock_enabler=_text(metadata.get("unlock_enabler", "")) or values["constraint_change"],
        historical_idea=values["historical_idea"],
        historical_failure_reason=values["historical_failure_reason"],
        blocking_constraint=values["blocking_constraint"],
        current_evidence=values["current_evidence"],
        constraint_change=values["constraint_change"],
        new_feasibility=values["new_feasibility"],
        resurrection_confidence=confidence,
    )


def _text_candidate(document: EvidenceDocument) -> ResurrectionCandidate | None:
    sentences = sorted(
        (sentence for fragment in document.fragments for sentence in _sentences(fragment.text)),
        key=str.casefold,
    )
    historical = next((s for s in sentences if _HISTORICAL_CUE.search(s)), "")
    current = next(
        (
            s for s in sentences
            if _CURRENT_CUE.search(s)
            and _CHANGE_CUE.search(s)
            and not _NO_EVIDENCE_CUE.search(s)
        ),
        "",
    )
    if not historical or not current:
        return None
    failure_reason = _cause(historical)
    blocking_constraint = failure_reason
    idea = _idea(historical)
    feasibility = _feasibility(current)
    if not idea or not failure_reason or not blocking_constraint or not feasibility:
        return None
    values = {
        "historical_idea": idea,
        "historical_failure_reason": failure_reason,
        "blocking_constraint": blocking_constraint,
        "current_evidence": current,
        "constraint_change": current,
        "new_feasibility": feasibility,
    }
    statement = _clean(f"{historical} {current}")
    return ResurrectionCandidate(
        statement=statement,
        evidence_doc_ids=(document.doc_id,),
        dormant_since=document.published,
        unlock_enabler=current,
        historical_idea=idea,
        historical_failure_reason=failure_reason,
        blocking_constraint=blocking_constraint,
        current_evidence=current,
        constraint_change=current,
        new_feasibility=feasibility,
        resurrection_confidence=_confidence(values),
    )


class ResurrectionCandidateExtractor:
    """Extract resurrection candidates only when change evidence is present."""

    def extract(
        self, documents: Iterable[EvidenceDocument], *, topic: str = ""
    ) -> list[ResurrectionCandidate]:
        candidates: list[ResurrectionCandidate] = []
        seen: set[tuple[str, str]] = set()
        for document in documents:
            candidate = _metadata_candidate(document) or _text_candidate(document)
            if candidate is None:
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


ResurrectionExtractor = ResurrectionCandidateExtractor
TechnologyResurrectionExtractor = ResurrectionCandidateExtractor
TechnologyResurrection = ResurrectionCandidateExtractor


def extract_resurrection_candidates(
    documents: Iterable[EvidenceDocument], *, topic: str = ""
) -> list[ResurrectionCandidate]:
    """Convenience wrapper for evidence-backed resurrection candidates."""
    return ResurrectionCandidateExtractor().extract(documents, topic=topic)


def find_resurrection_candidates(
    documents: Iterable[EvidenceDocument], *, topic: str = ""
) -> list[ResurrectionCandidate]:
    """Alias for callers using discovery terminology."""
    return extract_resurrection_candidates(documents, topic=topic)


def extract_resurrection(
    documents: Iterable[EvidenceDocument], *, topic: str = ""
) -> list[ResurrectionCandidate]:
    """Short alias for the technology-resurrection extractor."""
    return extract_resurrection_candidates(documents, topic=topic)
