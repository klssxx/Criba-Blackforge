"""Deterministic gazetteer entity extraction for the IIE entities sector (P05)."""
from __future__ import annotations

from ..contracts import EntityNode
from .resolver import EntityResolver

# Extend through a data-backed ontology in P06+; keep P05 offline and deterministic.
_GAZETTEER: tuple[tuple[str, str], ...] = (
    ("machine learning", "Technology"),
    ("deep learning", "Technology"),
    ("radiative cooling", "Technology"),
    ("photonic cooling", "Technology"),
    ("liquid cooling", "Technology"),
    ("immersion cooling", "Technology"),
    ("data center", "Market"),
    ("datacenter", "Market"),
    ("heat pump", "Technology"),
    ("waste heat", "Problem"),
    ("power usage effectiveness", "Standard"),
)


def extract_entities(
    text: str, resolver: EntityResolver, source_doc_id: str = ""
) -> list[EntityNode]:
    """Extract known terms deterministically; novel entities require explicit input."""
    lowered = text.lower()
    return [
        resolver.resolve(term, node_type=node_type, source_doc_id=source_doc_id)
        for term, node_type in _GAZETTEER
        if term in lowered
    ]
