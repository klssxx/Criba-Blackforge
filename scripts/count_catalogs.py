#!/usr/bin/env python3
"""Cuenta todos los catálogos de métodos."""
import json
from pathlib import Path

methods_dir = Path("E:/PROYECTS/CRIBA/data/methods")
total_new = 0
for f in sorted(methods_dir.glob("source_*.json")):
    d = json.load(open(f, "r", encoding="utf-8"))
    total_new += len(d)
    print(f"  {f.name}: {len(d)} items")

existing = json.load(open(methods_dir / "library_combined.json", "r", encoding="utf-8"))
print(f"\n---")
print(f"New sources total: {total_new}")
print(f"Existing library: {len(existing)}")
print(f"Grand total: {total_new + len(existing)}")
