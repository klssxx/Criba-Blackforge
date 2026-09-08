"""Evidence-gated patent-expiration opportunity analysis (P08-T07)."""
from __future__ import annotations

import re
from typing import Any, Iterable

from ..contracts import EvidenceDocument, PatentExpirationOpportunity

__all__ = [
    "PatentExpirationAnalyzer",
    "PatentExpirationOpportunityExtractor",
    "PatentExpirationEngine",
    "analyze_patent_expirations",
    "analyze_patent_expiration",
    "extract_patent_expiration_opportunities",
    "find_patent_expiration_opportunities",
]

_EXPIRY_CUE = re.compile(
    r"\b(?:expires?|expiration|expiry|lapses?|lapsed|expired|ends?)\b",
    re.IGNORECASE,
)
_DATE = re.compile(r"\b(?:19|20)\d{2}(?:-\d{2}(?:-\d{2})?)?\b")
_PATENT_ID = re.compile(
    r"\b(?:US|EP|WO|CN|JP|KR|DE|FR|GB)[- ]?[A-Z]?\d[\w-]*\b", re.IGNORECASE
)
_CLAIM_SCOPE = re.compile(
    r"\b(?:claims?|claim\s+scope)\s+(?:cover|covers|protect|protects|is|:)?\s*"
    r"(?P<scope>[^.!?;]+)",
    re.IGNORECASE,
)
_VALID_DATE = re.compile(r"^(?:19|20)\d{2}(?:-\d{2}(?:-\d{2})?)?$")
_SENTENCE = re.compile(r"[^.!?\n]+(?:[.!?]|$)")


def _text(value: Any) -> str:
    if isinstance(value, (list, tuple)):
        return "; ".join(str(item).strip() for item in value if str(item).strip())
    return str(value).strip() if value is not None else ""


def _clean(value: str, limit: int = 500) -> str:
    return " ".join(value.split()).strip(" ,:;-\t")[:limit]


def _sentences(text: str) -> list[str]:
    return [
        _clean(match.group(0))
        for match in _SENTENCE.finditer(text)
        if _clean(match.group(0))
    ]


def _valid_date(value: str) -> bool:
    return bool(_VALID_DATE.fullmatch(value))


def _status(value: Any, *, cue: str = "") -> str:
    normalized = _text(value).upper()
    if normalized:
        return normalized
    lowered = cue.casefold()
    if "expired" in lowered:
        return "EXPIRED"
    if "lapsed" in lowered or "lapse" in lowered:
        return "LAPSED"
    if "expire" in lowered or "expiry" in lowered or "expiration" in lowered:
        return "EXPIRING"
    return "UNKNOWN"


def _statement(patent_id: str, expiration_date: str, jurisdiction: str) -> str:
    location = f" in {jurisdiction}" if jurisdiction else ""
    return (
        f"Potential opportunity around patent {patent_id} after the stated "
        f"expiration date {expiration_date}{location}; legal status, maintenance "
        "and claim scope require verification."
    )


def _from_metadata(document: EvidenceDocument) -> PatentExpirationOpportunity | None:
    metadata = document.metadata
    patent_id = _clean(_text(metadata.get("patent_id", "")), 200)
    expiration_date = _clean(
        _text(metadata.get("expiration_date", metadata.get("expires_on", ""))), 40
    )
    if not patent_id or not expiration_date or not _valid_date(expiration_date):
        return None
    jurisdiction = _clean(_text(metadata.get("jurisdiction", "")), 80)
    title = _clean(_text(metadata.get("title", document.title)))
    claim_scope = _clean(_text(metadata.get("claim_scope", "")))
    status = _status(metadata.get("expiration_status", metadata.get("status", "")))
    statement = _clean(_text(metadata.get("opportunity_statement", "")))
    if not statement:
        statement = _statement(patent_id, expiration_date, jurisdiction)
    return PatentExpirationOpportunity(
        patent_id=patent_id,
        title=title,
        expiration_date=expiration_date,
        jurisdiction=jurisdiction,
        claim_scope=claim_scope,
        expiration_status=status,
        opportunity_statement=statement,
        evidence_doc_ids=(document.doc_id,),
        confidence=0.75,
    )


def _from_sentence(sentence: str, document: EvidenceDocument) -> PatentExpirationOpportunity | None:
    cue_match = _EXPIRY_CUE.search(sentence)
    if not cue_match:
        return None
    date_match = _DATE.search(sentence, cue_match.end()) or _DATE.search(sentence)
    patent_match = _PATENT_ID.search(sentence)
    if not date_match or not patent_match:
        return None
    patent_id = patent_match.group(0)
    expiration_date = date_match.group(0)
    jurisdiction = ""
    prefix = re.match(r"[A-Za-z]+", patent_id)
    if prefix:
        jurisdiction = prefix.group(0).upper()
    scope_match = _CLAIM_SCOPE.search(sentence)
    claim_scope = _clean(scope_match.group("scope")) if scope_match else ""
    return PatentExpirationOpportunity(
        patent_id=patent_id,
        title=document.title,
        expiration_date=expiration_date,
        jurisdiction=jurisdiction,
        claim_scope=claim_scope,
        expiration_status=_status("", cue=cue_match.group(0)),
        opportunity_statement=_statement(patent_id, expiration_date, jurisdiction),
        evidence_doc_ids=(document.doc_id,),
        confidence=0.6,
    )


class PatentExpirationAnalyzer:
    """Extract stated expiration opportunities without making legal conclusions."""

    def analyze(
        self,
        documents: Iterable[EvidenceDocument],
        *,
        jurisdiction: str = "",
        patent_id: str = "",
    ) -> list[PatentExpirationOpportunity]:
        requested_jurisdiction = jurisdiction.casefold().strip()
        requested_patent = patent_id.casefold().strip()
        found: list[PatentExpirationOpportunity] = []
        seen: set[tuple[str, str, str]] = set()
        for document in documents:
            extracted = [candidate for candidate in [_from_metadata(document)] if candidate]
            extracted.extend(
                candidate
                for fragment in document.fragments
                for sentence in _sentences(fragment.text)
                for candidate in [_from_sentence(sentence, document)]
                if candidate
            )
            for candidate in extracted:
                if requested_jurisdiction and candidate.jurisdiction.casefold() != requested_jurisdiction:
                    continue
                if requested_patent and candidate.patent_id.casefold() != requested_patent:
                    continue
                key = (
                    document.doc_id,
                    candidate.patent_id.casefold(),
                    candidate.expiration_date,
                )
                if key in seen:
                    continue
                seen.add(key)
                found.append(candidate)
        found.sort(
            key=lambda item: (
                item.evidence_doc_ids,
                item.patent_id.casefold(),
                item.expiration_date,
            )
        )
        return found


PatentExpirationOpportunityExtractor = PatentExpirationAnalyzer
PatentExpirationEngine = PatentExpirationAnalyzer


def analyze_patent_expirations(
    documents: Iterable[EvidenceDocument], *, jurisdiction: str = "", patent_id: str = ""
) -> list[PatentExpirationOpportunity]:
    """Analyze documents for stated patent-expiration opportunities."""
    return PatentExpirationAnalyzer().analyze(
        documents, jurisdiction=jurisdiction, patent_id=patent_id
    )


def analyze_patent_expiration(
    documents: Iterable[EvidenceDocument], *, jurisdiction: str = "", patent_id: str = ""
) -> list[PatentExpirationOpportunity]:
    """Singular alias for callers treating the engine as one analysis."""
    return analyze_patent_expirations(documents, jurisdiction=jurisdiction, patent_id=patent_id)


def extract_patent_expiration_opportunities(
    documents: Iterable[EvidenceDocument], *, jurisdiction: str = "", patent_id: str = ""
) -> list[PatentExpirationOpportunity]:
    """Extraction-oriented alias."""
    return analyze_patent_expirations(documents, jurisdiction=jurisdiction, patent_id=patent_id)


def find_patent_expiration_opportunities(
    documents: Iterable[EvidenceDocument], *, jurisdiction: str = "", patent_id: str = ""
) -> list[PatentExpirationOpportunity]:
    """Discovery-oriented alias."""
    return analyze_patent_expirations(documents, jurisdiction=jurisdiction, patent_id=patent_id)
