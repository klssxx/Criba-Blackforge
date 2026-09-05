"""Canonical entity extraction and resolution public surface (P05)."""

from .extractor import extract_entities
from .resolver import EntityResolver, normalize_label

__all__ = ["EntityResolver", "extract_entities", "normalize_label"]
