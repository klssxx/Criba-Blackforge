"""Idempotent catalog structuring: add `thinking_class` to every method entry.

Existing `family` / `source` fields are preserved untouched; `family` already
carries a real taxonomy (lente_avanzado, estrategia, seguridad, ...).

Mapping rationale (see docs/METHODS_INTEGRATION.md):
- Four thinking classes drawn with equal weight (25% each):
  perspectiva (lenses), generacion (idea generation), ruptura (frame-breaking),
  escape (jumping outside the known space).
- `dominio` is NOT a draw class: it is the domain bank (metodologias_2000,
  tecnicas_max, research taxonomies) used as an optional coupling die.
- Security families fold into `generacion` as the BLACKFORGE family.
"""
from __future__ import annotations

import json
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
METHODS_DIR = PACKAGE_ROOT / "data" / "methods"

CLASS_BY_SOURCE: dict[str, str] = {
    # library_combined.json sources
    "lentes_1_1700": "perspectiva",
    "metodos_disruptivos": "generacion",
    "ruptura_marco": "ruptura",
    "salto_espacio": "escape",
    "metodologias_2000": "dominio",
    "tecnicas_max": "dominio",
    # sources/*.json (unprefixed `source` values)
    "brainstorming_techniques": "generacion",
    "ideo_method_cards": "generacion",
    "gamestorming": "generacion",
    "liberating_structures": "generacion",
    "innovation_frameworks": "generacion",
    "decision_frameworks": "generacion",
    "pentest_methodologies": "generacion",
    "red_team_playbooks": "generacion",
    "incident_response": "generacion",
    "security_frameworks": "generacion",
    "research_taxonomies": "dominio",
    "escape_1030_master": "escape",
    # archive/library_expanded.json (no source field at rest)
    "foundational_methods": "generacion",
}


def _structure_payload(payload: list[dict], default_source: str) -> tuple[int, int]:
    changed = 0
    unmapped: set[str] = set()
    for item in payload:
        source = str(item.get("source", default_source))
        thinking_class = CLASS_BY_SOURCE.get(source)
        if thinking_class is None:
            unmapped.add(source)
            continue
        if item.get("thinking_class") != thinking_class:
            item["thinking_class"] = thinking_class
            changed += 1
    if unmapped:
        raise SystemExit(f"Unmapped sources (add them to CLASS_BY_SOURCE): {sorted(unmapped)}")
    return changed, len(payload)


def _write(path: Path, payload: list[dict]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    combined = METHODS_DIR / "library_combined.json"
    payload = json.loads(combined.read_text(encoding="utf-8"))
    changed, total = _structure_payload(payload, default_source="")
    _write(combined, payload)
    print(f"library_combined.json: {changed} updates over {total} entries")

    for path in sorted((METHODS_DIR / "sources").glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        changed, total = _structure_payload(payload, default_source=path.stem)
        _write(path, payload)
        print(f"{path.name}: {changed} updates over {total} entries")

    foundational = METHODS_DIR / "archive" / "library_expanded.json"
    payload = json.loads(foundational.read_text(encoding="utf-8"))
    changed, total = _structure_payload(payload, default_source="foundational_methods")
    _write(foundational, payload)
    print(f"archive/library_expanded.json: {changed} updates over {total} entries")


if __name__ == "__main__":
    main()
