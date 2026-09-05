"""Verify catalog provenance: raw source integrity + structured class coverage.

Checks:
1. Every raw source in ``data/methods/raw/`` matches ``manifest.sha256``.
2. Every runtime method entry carries a valid ``thinking_class``.
3. Class coverage summary (draw classes + domain bank).
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
METHODS_DIR = PACKAGE_ROOT / "data" / "methods"
RAW_DIR = METHODS_DIR / "raw"

DRAW_CLASSES = ("perspectiva", "generacion", "ruptura", "escape")
DOMAIN_CLASS = "dominio"
VALID_CLASSES = frozenset((*DRAW_CLASSES, DOMAIN_CLASS))


def verify_raw_manifest() -> list[str]:
    problems: list[str] = []
    manifest = RAW_DIR / "manifest.sha256"
    if not manifest.is_file():
        return [f"missing manifest: {manifest}"]
    for line in manifest.read_text(encoding="ascii").splitlines():
        expected, _, name = line.partition("  ")
        path = RAW_DIR / name.strip()
        if not path.is_file():
            problems.append(f"missing raw file: {name}")
            continue
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            problems.append(f"checksum mismatch: {name}")
    return problems


def verify_class_coverage() -> tuple[list[str], dict[str, int]]:
    problems: list[str] = []
    counts: dict[str, int] = {}
    payloads: list[tuple[Path, list[dict]]] = []
    combined = METHODS_DIR / "library_combined.json"
    payloads.append((combined, json.loads(combined.read_text(encoding="utf-8"))))
    for path in sorted((METHODS_DIR / "sources").glob("*.json")):
        payloads.append((path, json.loads(path.read_text(encoding="utf-8"))))
    for path, entries in payloads:
        for item in entries:
            thinking_class = str(item.get("thinking_class") or "")
            if thinking_class not in VALID_CLASSES:
                problems.append(f"{path.name}: id={item.get('id')} has invalid class '{thinking_class}'")
                continue
            counts[thinking_class] = counts.get(thinking_class, 0) + 1
    return problems, counts


def main() -> int:
    problems = verify_raw_manifest()
    class_problems, counts = verify_class_coverage()
    problems.extend(class_problems)
    print("Class coverage:", json.dumps(dict(sorted(counts.items())), ensure_ascii=False))
    if problems:
        for problem in problems:
            print(f"FAIL: {problem}", file=sys.stderr)
        return 1
    print("Catalog provenance OK.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
