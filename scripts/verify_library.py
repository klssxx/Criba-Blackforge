#!/usr/bin/env python3
"""Validate the composed runtime method catalog."""

from __future__ import annotations

from collections import Counter

from criba.catalog import methods

catalog = methods()
ids = [str(item["id"]) for item in catalog]
checks = {
    "expected_runtime_count": len(catalog) == 7_201,
    "all_have_id": all(item.get("id") for item in catalog),
    "all_have_name": all(item.get("name") for item in catalog),
    "ids_are_unique": len(ids) == len(set(ids)),
    "master_extension_count": sum(
        item.get("source") == "escape_1030_master" for item in catalog
    )
    == 30,
    "foundational_count": sum(
        item.get("source") == "foundational_methods" for item in catalog
    )
    == 66,
}
for name, passed in checks.items():
    print(f"{name}: {'PASS' if passed else 'FAIL'}")
print(f"Runtime total: {len(catalog)}")
print(f"Sources: {len(Counter(str(item.get('source')) for item in catalog))}")
raise SystemExit(0 if all(checks.values()) else 1)
