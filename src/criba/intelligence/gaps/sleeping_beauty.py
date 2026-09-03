"""Deterministic sleeping-beauty detection from delayed-attention evidence (P08-T09)."""
from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any, Iterable

from ..contracts import EvidenceDocument, SleepingBeautyCandidate

__all__ = [
    "SleepingBeautyAnalyzer",
    "SleepingBeautyDetector",
    "SleepingBeautyExtractor",
    "detect_sleeping_beauties",
    "analyze_sleeping_beauties",
    "extract_sleeping_beauties",
    "find_sleeping_beauties",
]

_SLEEPING_CUE = re.compile(
    r"\b(?:sleeping\s+beaut(?:y|ies)|delayed\s+recognition|"
    r"late\s+recognition|rediscovered\s+after\s+years)\b",
    re.IGNORECASE,
)
_YEAR = re.compile(r"\b(?:19|20)\d{2}\b")
_REDISCOVERED = re.compile(
    r"\b(?:rediscovered|awakened|recognized|recognised)\b[^.!?\n]*"
    r"\b(?P<year>(?:19|20)\d{2})\b",
    re.IGNORECASE,
)
_SENTENCE = re.compile(r"[^.!?\n]+(?:[.!?]|$)")
_SERIES_KEYS = ("citation_counts_by_year", "citations_by_year", "annual_citations")


def _text(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _clean(value: str, limit: int = 500) -> str:
    return " ".join(value.split()).strip(" ,:;-\t")[:limit]


def _int(value: Any) -> int | None:
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


def _citation_series(metadata: dict[str, Any]) -> dict[int, int]:
    raw: Any = next((metadata.get(key) for key in _SERIES_KEYS if metadata.get(key) is not None), None)
    series: dict[int, int] = {}
    if isinstance(raw, Mapping):
        entries = list(raw.items())
    elif isinstance(raw, (list, tuple)):
        entries = [
            (item.get("year"), item.get("citations", item.get("count")))
            for item in raw
            if isinstance(item, Mapping)
        ]
    else:
        return series
    for raw_year, raw_count in entries:
        parsed_year = _year(raw_year)
        parsed_count = _int(raw_count)
        if parsed_year is not None and parsed_count is not None:
            series[parsed_year] = parsed_count
    return series


def _evidence(series: dict[int, int], awakening_year: int, peak: int) -> str:
    observed = [f"{year}={count}" for year, count in sorted(series.items()) if year >= awakening_year]
    suffix = "; ".join(observed[:4])
    return f"Citation series shows delayed attention: peak={peak} after awakening in {awakening_year} ({suffix})."


def _candidate(
    *,
    document: EvidenceDocument,
    published: str,
    awakening_year: int,
    beauty_period_years: int,
    early_citations: int | None,
    peak_citations: int | None,
    later_citations: int | None,
    awakening_evidence: str,
    confidence: float,
) -> SleepingBeautyCandidate:
    return SleepingBeautyCandidate(
        paper_id=document.doc_id,
        title=document.title,
        published=published,
        awakening_year=awakening_year,
        beauty_period_years=beauty_period_years,
        early_citations=early_citations,
        peak_citations=peak_citations,
        later_citations=later_citations,
        awakening_evidence=awakening_evidence,
        evidence_doc_ids=(document.doc_id,),
        confidence=confidence,
    )


def _from_series(
    document: EvidenceDocument,
    *,
    early_window_years: int,
    min_later_citations: int,
    awakening_ratio: float,
) -> SleepingBeautyCandidate | None:
    metadata = document.metadata
    published = _clean(_text(metadata.get("published", document.published)), 40)
    publication_year = _year(published)
    series = _citation_series(metadata)
    if publication_year is None or not series:
        return None
    early_values = [
        count
        for year, count in series.items()
        if publication_year <= year < publication_year + early_window_years
    ]
    if not early_values:
        return None
    early_citations = sum(early_values)
    early_peak = max(early_values)
    threshold = max(min_later_citations, int(early_peak * awakening_ratio) + 1)
    later = sorted(
        (year, count)
        for year, count in series.items()
        if year >= publication_year + early_window_years and count >= threshold
    )
    if not later:
        return None
    awakening_year, _ = later[0]
    peak_citations = max(
        count for year, count in series.items() if year >= publication_year + early_window_years
    )
    return _candidate(
        document=document,
        published=published,
        awakening_year=awakening_year,
        beauty_period_years=max(0, awakening_year - publication_year - early_window_years),
        early_citations=early_citations,
        peak_citations=peak_citations,
        later_citations=peak_citations,
        awakening_evidence=_evidence(series, awakening_year, peak_citations),
        confidence=0.95,
    )


def _from_metadata(
    document: EvidenceDocument,
    *,
    early_window_years: int,
    min_later_citations: int,
    awakening_ratio: float,
) -> SleepingBeautyCandidate | None:
    metadata = document.metadata
    series_candidate = _from_series(
        document,
        early_window_years=early_window_years,
        min_later_citations=min_later_citations,
        awakening_ratio=awakening_ratio,
    )
    if series_candidate:
        return series_candidate
    if str(metadata.get("sleeping_beauty", "")).casefold() not in {"true", "1", "yes"}:
        return None
    published = _clean(_text(metadata.get("published", document.published)), 40)
    publication_year = _year(published)
    awakening_year = _int(metadata.get("awakening_year"))
    early = _int(metadata.get("early_citations"))
    later = _int(metadata.get("later_citations"))
    peak = _int(metadata.get("peak_citations", later))
    if publication_year is None or awakening_year is None or awakening_year <= publication_year:
        return None
    if early is None or later is None or later < min_later_citations:
        return None
    if peak is None or peak <= int(early * awakening_ratio):
        return None
    evidence = _clean(_text(metadata.get("awakening_evidence", "")))
    if not evidence:
        evidence = f"Structured citation evidence marks delayed attention in {awakening_year}."
    return _candidate(
        document=document,
        published=published,
        awakening_year=awakening_year,
        beauty_period_years=max(0, awakening_year - publication_year - early_window_years),
        early_citations=early,
        peak_citations=peak,
        later_citations=later,
        awakening_evidence=evidence,
        confidence=0.85,
    )


def _from_text(document: EvidenceDocument, *, early_window_years: int) -> list[SleepingBeautyCandidate]:
    found: list[SleepingBeautyCandidate] = []
    for fragment in document.fragments:
        for sentence in _sentences(fragment.text):
            if not _SLEEPING_CUE.search(sentence):
                continue
            years = [_year(value) for value in _YEAR.findall(sentence)]
            years = [value for value in years if value is not None]
            publication_year = _year(document.published) or (years[0] if years else None)
            awakening_match = _REDISCOVERED.search(sentence)
            awakening_year = (
                int(awakening_match.group("year"))
                if awakening_match
                else (years[-1] if len(years) > 1 else None)
            )
            if publication_year is None or awakening_year is None or awakening_year <= publication_year:
                continue
            found.append(
                _candidate(
                    document=document,
                    published=str(publication_year),
                    awakening_year=awakening_year,
                    beauty_period_years=max(0, awakening_year - publication_year - early_window_years),
                    early_citations=None,
                    peak_citations=None,
                    later_citations=None,
                    awakening_evidence=sentence,
                    confidence=0.65,
                )
            )
    return found


class SleepingBeautyAnalyzer:
    """Detect low-initial-attention papers followed by later recognition."""

    def analyze(
        self,
        documents: Iterable[EvidenceDocument],
        *,
        early_window_years: int = 4,
        min_later_citations: int = 5,
        awakening_ratio: float = 3.0,
    ) -> list[SleepingBeautyCandidate]:
        if early_window_years <= 0 or min_later_citations < 0 or awakening_ratio <= 0:
            return []
        found: list[SleepingBeautyCandidate] = []
        seen: set[tuple[str, int | None]] = set()
        for document in documents:
            extracted = [
                candidate
                for candidate in [
                    _from_metadata(
                        document,
                        early_window_years=early_window_years,
                        min_later_citations=min_later_citations,
                        awakening_ratio=awakening_ratio,
                    )
                ]
                if candidate
            ]
            extracted.extend(_from_text(document, early_window_years=early_window_years))
            for candidate in extracted:
                key = (candidate.paper_id, candidate.awakening_year)
                if key in seen:
                    continue
                seen.add(key)
                found.append(candidate)
        found.sort(key=lambda item: (item.paper_id.casefold(), item.awakening_year or 0))
        return found


SleepingBeautyDetector = SleepingBeautyAnalyzer
SleepingBeautyExtractor = SleepingBeautyAnalyzer


def detect_sleeping_beauties(
    documents: Iterable[EvidenceDocument], **kwargs: Any
) -> list[SleepingBeautyCandidate]:
    """Detect delayed-attention papers from citation series or explicit evidence."""
    return SleepingBeautyAnalyzer().analyze(documents, **kwargs)


def analyze_sleeping_beauties(
    documents: Iterable[EvidenceDocument], **kwargs: Any
) -> list[SleepingBeautyCandidate]:
    """Analysis-oriented alias."""
    return detect_sleeping_beauties(documents, **kwargs)


def extract_sleeping_beauties(
    documents: Iterable[EvidenceDocument], **kwargs: Any
) -> list[SleepingBeautyCandidate]:
    """Extraction-oriented alias."""
    return detect_sleeping_beauties(documents, **kwargs)


def find_sleeping_beauties(
    documents: Iterable[EvidenceDocument], **kwargs: Any
) -> list[SleepingBeautyCandidate]:
    """Discovery-oriented alias."""
    return detect_sleeping_beauties(documents, **kwargs)
