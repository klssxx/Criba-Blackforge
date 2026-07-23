"""File-backed catalogs. JSON only by design: portable and dependency free."""
from __future__ import annotations
import json
from pathlib import Path
from .constants import DATA_ROOT

def _load_dir(name: str) -> list[dict]:
    result = []
    directory = DATA_ROOT / name
    for path in sorted(directory.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"Catálogo inválido: {path.name}: {exc}") from exc
        entries = payload if isinstance(payload, list) else [payload]
        if not all(isinstance(item, dict) and item.get("id") for item in entries):
            raise ValueError(f"Catálogo inválido: {path.name}")
        result.extend(entries)
    return result

def currents() -> list[dict]: return _load_dir("currents")
def methods() -> list[dict]: return _load_dir("methods")
def find_current(current_id: str) -> dict:
    for item in currents():
        if item["id"] == current_id: return item
    raise ValueError(f"Corriente inexistente: {current_id}")
