"""IIE query expansion (P04, T033/T034/T036/T122-lite).

Deterministic synonym/ontology/multilingual expansion — no LLM required
(§27: models propose, never ground). Seeds kept minimal & curated.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..contracts import QueryVariant

_SYNONYMS: dict[str, list[str]] = {
    "cooling": ["thermal management", "heat dissipation", "refrigeration"],
    "datacenter": ["data center", "datacentre", "server farm"],
    "ai": ["artificial intelligence", "machine learning", "llm"],
    "energy": ["power", "electricity"],
    "cheap": ["low cost", "inexpensive", "affordable"],
    "fast": ["low latency", "high speed", "rapid"],
    "small": ["miniaturized", "compact", "miniature"],
    "efficient": ["high efficiency", "optimized"],
    "detect": ["sensing", "detection", "monitoring"],
    "patent": ["intellectual property", "ip rights"],
}

_ML: dict[str, dict[str, str]] = {
    "en": {"cooling": "enfriamiento", "energy": "energia", "datacenter": "centro de datos",
           "efficient": "eficiente", "cheap": "barato", "fast": "rapido"},
    "es": {"enfriamiento": "cooling", "energia": "energy", "centro de datos": "datacenter"},
}

_ONTOLOGY: dict[str, list[str]] = {
    "cooling": ["radiative cooling", "evaporative cooling", "thermoelectric cooling",
                "liquid cooling", "immersion cooling", "photonic cooling"],
    "energy": ["power density", "pue", "waste heat recovery"],
}


@dataclass
class ExpandedQuery:
    original: str
    variants: list[QueryVariant] = field(default_factory=list)

    def texts(self) -> list[str]:
        seen: set[str] = set()
        out = []
        for v in self.variants:
            if v.text and v.text not in seen:
                seen.add(v.text)
                out.append(v.text)
        return out


class QueryExpander:
    """T033 synonym + T034 ontology + T035 multilingual + T036 decomposition-lite."""

    def __init__(self, max_variants: int = 12):
        self.max_variants = max_variants

    def expand(self, query: str) -> ExpandedQuery:
        eq = ExpandedQuery(original=query)
        eq.variants.append(QueryVariant(text=query, origin="original"))
        words = query.lower().split()
        # T033 synonyms (single-word hits, keep original word too)
        for w in words:
            for syn in _SYNONYMS.get(w.strip(".,:;"), [])[:2]:
                eq.variants.append(QueryVariant(
                    text=query.replace(w, syn), origin="synonym", technique_ids=("T033",)))
        # T034 ontology (broader/narrower terms)
        for w in words:
            for term in _ONTOLOGY.get(w.strip(".,:;"), [])[:2]:
                eq.variants.append(QueryVariant(
                    text=f"{query} {term}", origin="ontology", technique_ids=("T034",)))
        # T035 multilingual (es both directions)
        for w in words:
            tr = _ML["en"].get(w.strip(".,:;"))
            if tr:
                eq.variants.append(QueryVariant(
                    text=query.replace(w, tr), language="es", origin="multilingual",
                    technique_ids=("T035",)))
        # T036 decomposition: key interrogatives split on ' and '/' or '
        if " and " in query.lower():
            parts = [p.strip() for p in query.replace(" and ", "|").replace(" AND ", "|").split("|") if len(p.strip()) > 3]
            for p in parts[:3]:
                eq.variants.append(QueryVariant(text=p, origin="decomposition", technique_ids=("T036",)))
        # dedupe by text+lang, cap
        seen: set[tuple[str, str]] = set()
        uniq: list[QueryVariant] = []
        for v in eq.variants:
            key = (v.text, v.language)
            if key not in seen:
                seen.add(key)
                uniq.append(v)
        eq.variants = uniq[:self.max_variants]
        return eq

    def mutate(self, query: str, prior_terms: list[str]) -> list[QueryVariant]:
        """T122-lite: drop failing terms, add synonym variants (used by prior-art
        rejection loop P10)."""
        out = []
        lowered = query.lower()
        for term in prior_terms[:3]:
            if term.lower() in lowered:
                for syn in _SYNONYMS.get(term.lower(), [])[:1]:
                    out.append(QueryVariant(
                        text=lowered.replace(term.lower(), syn), origin="mutation",
                        technique_ids=("T122",)))
        if not out and prior_terms:
            out.append(QueryVariant(
                text=f"{query} {prior_terms[0]} OR alternative", origin="mutation",
                technique_ids=("T122",)))
        return out[:3]
