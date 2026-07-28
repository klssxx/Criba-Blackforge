#!/usr/bin/env python3
"""Traza el pipeline completo de CRIBA con funciones y líneas exactas."""
import sys
sys.path.insert(0, "E:/PROYECTS/CRIBA/src")

from criba import engine, catalog, methods, selector

QUERY = "¿Cómo proteger APIs de ataques de inyección?"

print("=== PIPELINE CRIBA BLACKFORGE ===\n")

# Step 1: Validation
print("[1] VALIDACIÓN (engine.py:398-405)")
print(f"    Query: {QUERY[:60]}...")
print(f"    Length OK: {len(QUERY) < 20000}\n")

# Step 2: Current selection
print("[2] SELECCIÓN DE CORRIENTE (engine.py:408)")
print("    -> selector.select(query, current)")
selection = selector.select(QUERY, "auto")
print(f"    Selected current: {selection['selected_current']}")
print(f"    Score: {selection['score']}\n")

# Step 3: Find current
print("[3] FIND CURRENT (engine.py:409)")
print("    -> catalog.find_current(current_id)")
selected = catalog.find_current(selection["selected_current"])
print(f"    Current name: {selected['name']}\n")

# Step 4: Select methods
print("[4] SELECCIÓN DE MÉTODOS (engine.py:410)")
print("    -> methods.select_methods(count, mode, manual, query)")
print("    -> methods.py:79 (select_methods function)")
print("    -> catalog.py:23 (methods() loads library_combined.json)")
selected_methods = methods.select_methods(8, "balanced", query=QUERY)
print(f"    Methods selected: {len(selected_methods)}")
for m in selected_methods[:3]:
    print(f"      - {m['id']}: {m['name'][:40]} (family: {m['family']})")
print(f"    ... y {len(selected_methods)-3} más\n")

# Step 5: Cartograph and break
print("[5] CARTOGRAFÍA Y RUPTURA (engine.py:412)")
print("    -> engine.cartograph_and_break(query, context, selection) [engine.py:54]")
carto = engine.cartograph_and_break(QUERY, {}, selection)
print(f"    Known space: {len(carto['known_space'])} items")
print(f"    Assumptions: {len(carto['assumptions'])} items")
print(f"    Ruptures: {len(carto['ruptures'])} items\n")

# Step 6: Diverge
print("[6] DIVERGENCIA (engine.py:420)")
print("    -> engine.diverge(carto, rupture, selected, methods, query) [engine.py:160]")
print("    -> engine._apply_family(family, base, extreme) [engine.py:150]")
rupture = {
    "operations": carto["ruptures"],
    "broken_assumptions": [r["assumption_id"] for r in carto["ruptures"] if r["operation"] == "invert"],
    "inversions": [r["result"] for r in carto["ruptures"] if r["operation"] == "invert"],
    "eliminations": [r["result"] for r in carto["ruptures"] if r["operation"] == "eliminate"],
    "counterexample": carto["counterexample"],
}
ideas = engine.diverge(carto, rupture, selected, selected_methods, QUERY)
print(f"    Ideas generated: {len(ideas)}\n")

# Step 7: CCA
print("[7] CROSS-CONSISTENCY ASSESSMENT (engine.py:422)")
print("    -> engine.cross_consistency_assessment(ideas) [engine.py:228]")
real_ideas, cosmetic_count = engine.cross_consistency_assessment(ideas)
print(f"    Real ideas: {len(real_ideas)}")
print(f"    Cosmetic rejected: {cosmetic_count}\n")

# Step 8: Duplicate detection
print("[8] DETECCIÓN DE DUPLICADOS (engine.py:423)")
print("    -> engine._detect_duplicates(ideas) [engine.py:245]")
print("    -> criba.similarity.classify(genome1, genome2)")
dup_report = engine._detect_duplicates(real_ideas)
distinct = sum(1 for r in dup_report if r["verdict"] == "distinct")
print(f"    Distinct: {distinct}")
print(f"    Duplicates/variants: {len(dup_report) - distinct}\n")

# Step 9: Convergence
print("[9] CAPA DE CONVERGENCIA (engine.py:446-452)")
print("    -> engine._evaluate_idea(idea) [engine.py:330]")
print("    -> engine.value_score(evidence, novelty, cost) [engine.py:296]")
for i in real_ideas:
    i["convergence"] = engine._evaluate_idea(i)
ranked = sorted(real_ideas, key=lambda x: x["convergence"]["value_score"], reverse=True)
print("    Top 3 ideas by value_score:")
for idx, idea in enumerate(ranked[:3]):
    conv = idea["convergence"]
    print(f"      {idx+1}. {idea['description'][:50]}...")
    print(f"         value_score: {conv['value_score']}")
    print(f"         evidence: {conv['evidence']}, novelty: {conv['novelty']}, cost: {conv['cost']}")
print()

# Step 10: Decision
print("[10] DECISIÓN (engine.py:492-503)")
families = sorted({i["family"] for i in real_ideas})
pipeline_action = "PROTOTIPAR" if len(families) >= 4 else "DIVERGIR"
print(f"     Families: {len(families)}")
print(f"     Pipeline action: {pipeline_action}")
print(f"     Recommended status: AMPLIAR PRUEBA\n")

print("=== RESUMEN ===")
print(f"Total ideas: {len(real_ideas)}")
print(f"Top idea: {ranked[0]['description'][:60]}...")
print(f"Top value_score: {ranked[0]['convergence']['value_score']}")
print(f"Decision: {pipeline_action}")
