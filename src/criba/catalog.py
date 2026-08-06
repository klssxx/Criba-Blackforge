"""File-backed catalogs. JSON only by design: portable and dependency free."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any
from .constants import DATA_ROOT

def _load_file(path: Path) -> list[dict[str, Any]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Catálogo inválido: {path.name}: {exc}") from exc
    entries = payload if isinstance(payload, list) else [payload]
    if not all(isinstance(item, dict) and item.get("id") for item in entries):
        raise ValueError(f"Catálogo inválido: {path.name}")
    return entries

def _load_dir(name: str) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    directory = DATA_ROOT / name
    for path in sorted(directory.glob("*.json")):
        result.extend(_load_file(path))
    return result

def currents() -> list[dict[str, Any]]: return _load_dir("currents")

def methods() -> list[dict[str, Any]]:
    """Load the approved runtime catalog and reject cross-source ID collisions."""
    methods_dir = DATA_ROOT / "methods"
    result = _load_file(methods_dir / "library_combined.json")
    for path in sorted((methods_dir / "sources").glob("*.json")):
        result.extend(_load_file(path))

    foundational = _load_file(methods_dir / "archive" / "library_expanded.json")
    for item in foundational:
        normalized = dict(item)
        normalized.setdefault("source", "foundational_methods")
        normalized.setdefault("granularity", "method")
        normalized.setdefault("origin", "internal")
        result.append(normalized)

    seen: set[str] = set()
    duplicate_ids: set[str] = set()
    for item in result:
        method_id = str(item["id"])
        if method_id in seen:
            duplicate_ids.add(method_id)
        seen.add(method_id)
    if duplicate_ids:
        sample = ", ".join(sorted(duplicate_ids)[:5])
        raise ValueError(f"Catálogo de métodos con ID duplicado: {sample}")
    return result

def methods_by_granularity(granularity: str) -> list[dict[str, Any]]:
    """Retorna solo métodos con la granularidad especificada."""
    return [m for m in methods() if m.get("granularity") == granularity]

def frameworks() -> list[dict[str, Any]]:
    """Retorna solo frameworks (granularity == 'framework')."""
    return methods_by_granularity("framework")

def facilitation_patterns() -> list[dict[str, Any]]:
    """Retorna solo patrones de facilitación (granularity == 'facilitation_pattern')."""
    return methods_by_granularity("facilitation_pattern")

def group_games() -> list[dict[str, Any]]:
    """Retorna solo juegos de grupo (granularity == 'group_game')."""
    return methods_by_granularity("group_game")

def methods_by_source(source: str) -> list[dict[str, Any]]:
    """Retorna solo métodos de una fuente específica."""
    return [m for m in methods() if m.get("source") == source]

def find_current(current_id: str) -> dict[str, Any]:
    for item in currents():
        if item["id"] == current_id: return item
    raise ValueError(f"Corriente inexistente: {current_id}")
