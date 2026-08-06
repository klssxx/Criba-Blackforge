#!/usr/bin/env python3
"""Extract the MASTER-only escape techniques into a traceable JSON source."""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
from pathlib import Path
from typing import Any

ENTRY_PATTERN = re.compile(r"^(\d+)\.\s+(.+?)(?=^\d+\.\s|\Z)", re.MULTILINE | re.DOTALL)
MASTER_FILENAME = "1030_tecnicas_salto_fuera_espacio_conocido_MASTER.txt"


def _normalized_name(name: str) -> str:
    folded = unicodedata.normalize("NFKD", name.casefold())
    ascii_name = "".join(char for char in folded if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]", "", ascii_name)


def _parse(path: Path) -> list[dict[str, Any]]:
    raw = path.read_text(encoding="utf-8", errors="replace")
    entries: list[dict[str, Any]] = []
    for match in ENTRY_PATTERN.finditer(raw):
        number = int(match.group(1))
        text = re.sub(r"\s+", " ", match.group(2).strip().replace("\n", " "))
        text = re.split(r"\s*=+\s*FIN DEL CAT[ÁA]LOGO", text, maxsplit=1)[0].strip()
        if " — " in text:
            name, description = text.split(" — ", 1)
        elif ": " in text[:100]:
            name, description = text.split(": ", 1)
        else:
            name, description = text[:80], text
        entries.append(
            {
                "source_number": number,
                "name": name.strip(),
                "description": description.strip(),
                "normalized_name": _normalized_name(name),
            }
        )
    return entries


def build_extension(master_path: Path, expanded_path: Path) -> list[dict[str, Any]]:
    """Return entries present by mechanism in MASTER but absent from expanded."""
    master = _parse(master_path)
    expanded_names = {entry["normalized_name"] for entry in _parse(expanded_path)}
    unique = [
        entry for entry in master if entry["normalized_name"] not in expanded_names
    ]
    records = []
    for entry in unique:
        number = int(entry["source_number"])
        name = str(entry["name"])
        description = str(entry["description"])
        records.append(
            {
                "id": f"escape_master_{number:04d}",
                "name": name,
                "family": "salto_espacio",
                "selection_reason": (
                    "Mecanismo exclusivo del MASTER de 1.030 técnicas, ausente "
                    "del catálogo ampliado por comparación normalizada de nombre."
                ),
                "template": description,
                "source": "escape_1030_master",
                "source_number": number,
                "source_ref": f"{MASTER_FILENAME}#{number}",
                "granularity": "micro_technique",
                "origin": "internal",
                "axis": "escape",
                "categories": ["innovacion", "tecnicas_de_salto"],
                "tags": ["exploracion", "espacio_desconocido"],
                "normalized_mechanism": _normalized_name(name),
                "relationship_type": "complementa",
                "external_refs": [],
                "related_internal_ids": [],
                "sector": "",
            }
        )
    return records


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--master", type=Path, required=True)
    parser.add_argument("--expanded", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expected-count", type=int, default=30)
    args = parser.parse_args()

    records = build_extension(args.master, args.expanded)
    if len(records) != args.expected_count:
        raise ValueError(
            f"Se esperaban {args.expected_count} entradas exclusivas y se obtuvieron "
            f"{len(records)}."
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"{len(records)} entradas escritas en {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
