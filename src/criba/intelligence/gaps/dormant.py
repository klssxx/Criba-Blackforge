"""Evidence-gated dormant-paper detection (P08-T08)."""
from __future__ import annotations

import re
from typing import Any, Iterable

from ..contracts import DormantPaperCandidate, EvidenceDocument

__all__ = [
    "DormantPaperAnalyzer",
    "DormantPaperDetector",
    "DormantPaperExtractor",
    "detect_dormant_papers",
    "analyze_dormant_papers",
    "extract_dormant_papers",
    "find_dormant_papers",
]

_DORMANCY_CUE = re.compile(
    r"\b(?:rarely\s+cited|little\s+attention|low\s+attention|"
    r"no\s+attention|under[- ]cited|forgotten|dormant|overlooked|"
    r"sleeping\s+beauty)\b",
    re.IGNORECASE,
)
_YEAR = re.compile(r"\b(?:19|20)\d{2}\b")
_SINCE = re.compile(r"\bsince\s+(?P<year>(?:19|20)\d{2})\b", re.IGNORECASE)
_SENTENCE = re.compile(r"[^.!?\n]+(?:[.!?]|$)")


def _text(value: Any) -> str:
    if isinstance(value, (list, tuple)):
        return "; ".join(str(item).strip() for item in value if str(item).strip())
    return str(value).strip() if value is not None else ""


def _clean(value: str, limit: int = 500) -> str:
    return " ".join(value.split()).strip(" ,:;-\t")[:limit]


def _int(value: Any) -> int | None:
    if isinstance(value, bool):
        return int(value)
    try:
        parsed = int(str(value).strip())
    except (TypeError, ValueError):
        return None
    return parsed if parsed >= 0 else None


def _year(value: Any) -> int | None:
    match = _YEAR.search(_text(value))
    return int(match.group(0)) if match else None


def _sentences(text: str) -> list[str]:
    return [_clean(match.group(0)) for match in _SENTENCE.finditer(text) if _clean(match.group(0))]


def _old_enough(published: str, as_of: str, min_age_years: int) -> bool:
    publication_year = _year(published)
    as_of_year = _year(as_of)
    return (
        publication_year is not None
        and as_of_year is not None
        and as_of_year - publication_year >= min_age_years
    )


def _metadata_metrics(metadata: dict[str, Any]) -> tuple[int | None, int | None, int | None, str]:
    citation_count = _int(metadata.get("citation_count"))
    recent_citations = _int(
        metadata.get("recent_citations", metadata.get("citations_last_year"))
    )
    recent_attention = _int(
        metadata.get(
            "recent_attention",
            metadata.get("mentions_last_year", metadata.get("altmetric_mentions")),
        )
    )
    last_cited = _clean(_text(metadata.get("last_cited", "")), 40)
    return citation_count, recent_citations, recent_attention, last_cited


def _has_low_attention(
    recent_citations: int | None,
    recent_attention: int | None,
    max_recent_citations: int,
    max_recent_attention: int,
) -> bool:
    observed = [value for value in (recent_citations, recent_attention) if value is not None]
    if not observed:
        return False
    return (
        recent_citations is None or recent_citations <= max_recent_citations
    ) and (recent_attention is None or recent_attention <= max_recent_attention)


def _candidate(
    *,
    document: EvidenceDocument,
    paper_id: str,
    title: str,
    published: str,
    dormant_since: str,
    citation_count: int | None,
    recent_citations: int | None,
    recent_attention: int | None,
    last_cited: str,
    reason: str,
    confidence: float,
) -> DormantPaperCandidate:
    return DormantPaperCandidate(
        paper_id=paper_id,
        title=title,
        published=published,
        dormant_since=dormant_since,
        citation_count=citation_count,
        recent_citations=recent_citations,
        recent_attention=recent_attention,
        last_cited=last_cited,
        dormancy_reason=reason,
        evidence_doc_ids=(document.doc_id,),
        confidence=confidence,
    )


def _from_metadata(
    document: EvidenceDocument,
    *,
    as_of: str,
    min_age_years: int,
    max_recent_citations: int,
    max_recent_attention: int,
) -> DormantPaperCandidate | None:
    metadata = document.metadata
    published = _clean(_text(metadata.get("published", document.published)), 40)
    citation_count, recent_citations, recent_attention, last_cited = _metadata_metrics(metadata)
    explicit = str(metadata.get("dormant", "")).casefold() in {"true", "1", "yes"}
    low_attention = _has_low_attention(
        recent_citations, recent_attention, max_recent_citations, max_recent_attention
    )
    if not low_attention:
        return None
    if as_of and not _old_enough(published, as_of, min_age_years) and not explicit:
        return None
    if not as_of and not explicit:
        return None
    paper_id = _clean(_text(metadata.get("paper_id", document.doc_id)), 200)
    title = _clean(_text(metadata.get("title", document.title)))
    dormant_since = _clean(
        _text(metadata.get("dormant_since", last_cited or published)), 40
    )
    reason = _clean(
        _text(metadata.get("dormancy_reason", "Low recent citation or attention signal."))
    )
    return _candidate(
        document=document,
        paper_id=paper_id,
        title=title,
        published=published,
        dormant_since=dormant_since,
        citation_count=citation_count,
        recent_citations=recent_citations,
        recent_attention=recent_attention,
        last_cited=last_cited,
        reason=reason,
        confidence=0.9 if as_of and _old_enough(published, as_of, min_age_years) else 0.75,
    )


def _from_sentence(
    sentence: str,
    document: EvidenceDocument,
    *,
    as_of: str,
    min_age_years: int,
) -> DormantPaperCandidate | None:
    if not _DORMANCY_CUE.search(sentence):
        return None
    years = _YEAR.findall(sentence)
    published = document.published or (years[0] if years else "")
    if not published:
        return None
    if as_of and not _old_enough(published, as_of, min_age_years):
        return None
    since_match = _SINCE.search(sentence)
    dormant_since = since_match.group("year") if since_match else published
    lowered = sentence.casefold()
    recent_citations = 0 if re.search(r"rarely\s+cited|under[- ]cited|no\s+citation", lowered) else None
    recent_attention = 0 if re.search(r"no\s+attention|little\s+attention|low\s+attention", lowered) else None
    return _candidate(
        document=document,
        paper_id=document.doc_id,
        title=document.title,
        published=_clean(published, 40),
        dormant_since=dormant_since,
        citation_count=None,
        recent_citations=recent_citations,
        recent_attention=recent_attention,
        last_cited="",
        reason=sentence,
        confidence=0.7,
    )


class DormantPaperAnalyzer:
    """Detect sustained low-attention papers without fabricating citation data."""

    def analyze(
        self,
        documents: Iterable[EvidenceDocument],
        *,
        as_of: str = "",
        min_age_years: int = 5,
        max_recent_citations: int = 1,
        max_recent_attention: int = 1,
    ) -> list[DormantPaperCandidate]:
        if min_age_years < 0 or max_recent_citations < 0 or max_recent_attention < 0:
            return []
        found: list[DormantPaperCandidate] = []
        seen: set[tuple[str, str, str]] = set()
        for document in documents:
            extracted = [
                candidate
                for candidate in [
                    _from_metadata(
                        document,
                        as_of=as_of,
                        min_age_years=min_age_years,
                        max_recent_citations=max_recent_citations,
                        max_recent_attention=max_recent_attention,
                    )
                ]
                if candidate
            ]
            extracted.extend(
                candidate
                for fragment in document.fragments
                for sentence in _sentences(fragment.text)
                for candidate in [
                    _from_sentence(
                        sentence,
                        document,
                        as_of=as_of,
                        min_age_years=min_age_years,
                    )
                ]
                if candidate
            )
            for candidate in extracted:
                key = (document.doc_id, candidate.paper_id, candidate.published)
                if key in seen:
                    continue
                seen.add(key)
                found.append(candidate)
        found.sort(key=lambda item: (item.paper_id.casefold(), item.published, item.dormant_since))
        return found


DormantPaperDetector = DormantPaperAnalyzer
DormantPaperExtractor = DormantPaperAnalyzer


def detect_dormant_papers(
    documents: Iterable[EvidenceDocument],
    *,
    as_of: str = "",
    min_age_years: int = 5,
    max_recent_citations: int = 1,
    max_recent_attention: int = 1,
) -> list[DormantPaperCandidate]:
    """Detect dormant papers using explicit age and low-attention evidence."""
    return DormantPaperAnalyzer().analyze(
        documents,
        as_of=as_of,
        min_age_years=min_age_years,
        max_recent_citations=max_recent_citations,
        max_recent_attention=max_recent_attention,
    )


def analyze_dormant_papers(
    documents: Iterable[EvidenceDocument], **kwargs: Any
) -> list[DormantPaperCandidate]:
    """Analysis-oriented alias."""
    return detect_dormant_papers(documents, **kwargs)


def extract_dormant_papers(
    documents: Iterable[EvidenceDocument], **kwargs: Any
) -> list[DormantPaperCandidate]:
    """Extraction-oriented alias."""
    return detect_dormant_papers(documents, **kwargs)


def find_dormant_papers(
    documents: Iterable[EvidenceDocument], **kwargs: Any
) -> list[DormantPaperCandidate]:
    """Discovery-oriented alias."""
    return detect_dormant_papers(documents, **kwargs)
