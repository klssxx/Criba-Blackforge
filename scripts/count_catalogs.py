#!/usr/bin/env python3
"""Count the approved runtime method catalog by source and granularity."""

from __future__ import annotations

from collections import Counter

from criba.catalog import methods

catalog = methods()
print(f"Runtime total: {len(catalog)}")
print("\nBy source:")
for source, count in Counter(
    str(item.get("source", "unspecified")) for item in catalog
).most_common():
    print(f"  {source}: {count}")
print("\nBy granularity:")
for granularity, count in sorted(
    Counter(str(item.get("granularity", "micro_technique")) for item in catalog).items()
):
    print(f"  {granularity}: {count}")
