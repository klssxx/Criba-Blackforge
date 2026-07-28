#!/usr/bin/env python3
"""Verifica el estado final de la librería combinada."""
import json

d = json.load(open("E:/PROYECTS/CRIBA/data/methods/library_combined.json", "r", encoding="utf-8"))

print(f"Total items: {len(d)}")
print(f"All have id: {all('id' in i for i in d)}")
print(f"All have name: {all('name' in i for i in d)}")
print(f"All have source: {all('source' in i for i in d)}")
print(f"All have normalized_mechanism: {all('normalized_mechanism' in i for i in d)}")
print(f"Items with related_internal_ids: {sum(1 for i in d if i.get('related_internal_ids'))}")
print(f"Items with relationship_type: {sum(1 for i in d if i.get('relationship_type'))}")

# Granularities
grans = {}
for i in d:
    g = i.get("granularity", "micro_technique")
    grans[g] = grans.get(g, 0) + 1
print(f"Granularities: {grans}")

# Sources
sources = {}
for i in d:
    s = i.get("source", "NONE")
    sources[s] = sources.get(s, 0) + 1
print(f"Sources ({len(sources)}):")
for s, c in sorted(sources.items(), key=lambda x: -x[1]):
    print(f"  {s}: {c}")
