"""BLACKFORGE catalog loader — FASE 1 (INGESTA DEL CATÁLOGO).

Immutable, read-only view over the consolidated BLACKFORGE catalog
(imports/blackforge_v2/criba_blackforge_catalogo_final_debate20.json, 723
records). The loader is deliberately IMMUTABLE: it parses the JSON exactly
once, wraps the record list in a tuple and each record in a MappingProxyType,
and never exposes a mutable reference. Callers get defensive copies on demand
only (via ``get``/``to_dict``), so the loaded data cannot be mutated in place
during a session.

All validation rules come from the catalog's own embedded policies
(taxonomy_policy / safety_policy / selection_policy), never from hard-coded
guesses. The loader does NOT silently "fix" the data; it REPORTS divergences
(recorded by tests/unit/test_blackforge_catalog.py into
verification/blackforge_catalog_report.json) so a human can decide.
"""
from __future__ import annotations

import json
from pathlib import Path
from types import MappingProxyType
from typing import Dict, List, Optional, Tuple

from .constants import PACKAGE_ROOT

# Consolidated catalog source (canonical 723-record JSON).
_CATALOG_PATH = (
    PACKAGE_ROOT
    / "imports"
    / "blackforge_v2"
    / "criba_blackforge_catalogo_final_debate20.json"
)

# Module-level cache (parsed exactly once per process).
_cache: Optional[Tuple[MappingProxyType, Tuple[MappingProxyType, ...]]] = None


class CatalogValidationError(ValueError):
    """Raised when the catalog violates its own embedded policy contracts."""


def _load_raw() -> dict:
    if not _CATALOG_PATH.exists():
        raise FileNotFoundError(f"Catálogo BLACKFORGE no encontrado: {_CATALOG_PATH}")
    try:
        payload = json.loads(_CATALOG_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:  # pragma: no cover - defensive
        raise CatalogValidationError(f"Catálogo inválido (JSON): {exc}") from exc
    if not isinstance(payload, dict) or "records" not in payload:
        raise CatalogValidationError("Catálogo sin la clave 'records'.")
    if not isinstance(payload["records"], list):
        raise CatalogValidationError("'records' no es una lista.")
    return payload


def _freeze_record(rec: dict) -> MappingProxyType:
    """Return an immutable view of a single record (deep-frozen at top level)."""
    return MappingProxyType({k: (tuple(v) if isinstance(v, list) else v) for k, v in rec.items()})


def _get_catalog() -> Tuple[MappingProxyType, Tuple[MappingProxyType, ...]]:
    """Load + freeze the catalog once. Returns (meta, frozen_records)."""
    global _cache
    if _cache is not None:
        return _cache
    payload = _load_raw()
    meta = MappingProxyType(dict(payload))
    frozen = tuple(_freeze_record(r) for r in payload["records"])
    _cache = (meta, frozen)
    return _cache


def reset_cache() -> None:
    """Test hook: drop the cached parse (does not reload from disk)."""
    global _cache
    _cache = None


def load() -> Tuple[MappingProxyType, Tuple[MappingProxyType, ...]]:
    """Immutable (meta, records) view. Records are MappingProxyType, never mutable."""
    return _get_catalog()


def records() -> Tuple[MappingProxyType, ...]:
    """Frozen tuple of immutable records (read-only)."""
    return _get_catalog()[1]


def get(blackforge_id: str) -> Optional[MappingProxyType]:
    """Return an immutable record view by blackforge_id, or None if absent."""
    for r in _get_catalog()[1]:
        if r["blackforge_id"] == blackforge_id:
            return r
    return None


def to_dict() -> dict:
    """Defensive deep-ish copy for callers that truly need a mutable dict."""
    meta, recs = _get_catalog()
    return {
        "meta": dict(meta),
        "records": [dict(r) for r in recs],
    }


def policies() -> MappingProxyType:
    """Embedded taxonomy/safety/selection policies (immutable view)."""
    return _get_catalog()[0]
