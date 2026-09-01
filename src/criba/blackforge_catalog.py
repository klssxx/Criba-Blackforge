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
from collections.abc import Mapping
from types import MappingProxyType
from typing import Any

# Immutable view types over the frozen BLACKFORGE catalog.
_FrozenRecord = MappingProxyType[str, Any]
_FrozenCatalog = tuple[_FrozenRecord, tuple[_FrozenRecord, ...]]
_FrozenIndex = MappingProxyType[str, _FrozenRecord]

from .constants import PACKAGE_ROOT

# Consolidated catalog source (canonical 723-record JSON).
_CATALOG_PATH = (
    PACKAGE_ROOT
    / "imports"
    / "blackforge_v2"
    / "criba_blackforge_catalogo_final_debate20.json"
)

# Module-level cache (parsed exactly once per process).
_cache: _FrozenCatalog | None = None
_id_index: _FrozenIndex | None = None


class CatalogValidationError(ValueError):
    """Raised when the catalog violates its own embedded policy contracts."""


def _load_raw() -> dict[str, Any]:
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


def _freeze_value(value: Any) -> Any:
    """Recursively freeze JSON containers without copying immutable scalars."""
    if isinstance(value, dict):
        return MappingProxyType({str(key): _freeze_value(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze_value(item) for item in value)
    return value


def _freeze_record(rec: Mapping[str, Any]) -> _FrozenRecord:
    """Return a recursively immutable view of a catalog record."""
    return MappingProxyType({str(key): _freeze_value(value) for key, value in rec.items()})


def _build_id_index(records: tuple[_FrozenRecord, ...]) -> _FrozenIndex:
    """Build the immutable O(1) ID index and reject duplicate/malformed IDs."""
    index: dict[str, _FrozenRecord] = {}
    for record in records:
        raw_id = record.get("blackforge_id")
        if not isinstance(raw_id, str) or not raw_id:
            raise CatalogValidationError("Registro sin blackforge_id válido.")
        if raw_id in index:
            raise CatalogValidationError(f"blackforge_id duplicado: {raw_id}")
        index[raw_id] = record
    return MappingProxyType(index)


def _get_catalog() -> _FrozenCatalog:
    """Load + freeze the catalog once. Returns (meta, frozen_records)."""
    global _cache, _id_index
    if _cache is not None:
        return _cache
    payload = _load_raw()
    meta = _freeze_record({key: value for key, value in payload.items() if key != "records"})
    frozen = tuple(_freeze_record(r) for r in payload["records"])
    _id_index = _build_id_index(frozen)
    _cache = (meta, frozen)
    return _cache


def _get_id_index() -> _FrozenIndex:
    """Return the immutable index, initializing the catalog exactly once."""
    if _id_index is None:
        _get_catalog()
    assert _id_index is not None
    return _id_index


def reset_cache() -> None:
    """Test hook: drop the cached parse (does not reload from disk)."""
    global _cache, _id_index
    _cache = None
    _id_index = None


def load() -> _FrozenCatalog:
    """Immutable (meta, records) view. Records are MappingProxyType, never mutable."""
    return _get_catalog()


def records() -> tuple[_FrozenRecord, ...]:
    """Frozen tuple of immutable records (read-only)."""
    return _get_catalog()[1]


def get(blackforge_id: str) -> _FrozenRecord | None:
    """Return an immutable record view by blackforge_id, or None if absent."""
    return _get_id_index().get(blackforge_id)


def _thaw(value: Any) -> Any:
    """Recursively copy frozen JSON containers back to mutable dicts/lists."""
    if isinstance(value, Mapping):
        return {str(key): _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    return value


def to_dict() -> dict[str, Any]:
    """Defensive deep copy for callers that truly need a mutable JSON shape."""
    meta, recs = _get_catalog()
    return {
        "meta": _thaw(meta),
        "records": [_thaw(record) for record in recs],
    }


def policies() -> _FrozenRecord:
    """Embedded taxonomy/safety/selection policies (immutable view)."""
    return _get_catalog()[0]
