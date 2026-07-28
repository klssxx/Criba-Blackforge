#!/usr/bin/env python3
"""
Benchmark real de CRIBA BLACKFORGE: ejecuta consultas de dominios distintos
y mite métricas de calidad de innovación.
"""
import sys
import json
import hashlib
from collections import Counter
from pathlib import Path

sys.path.insert(0, "E:/PROYECTS/CRIBA/src")

from criba import engine

# Consultas de dominios distintos
QUERIES = [
    # Seguridad
    "¿Cómo proteger APIs de ataques de inyección SQL?",
    "¿Cómo detectar malware que usa ofuscación de código?",
    "¿Cómo prevenir ataques de ingeniería social en empresas?",
    # Innovación
    "¿Cómo generar ideas disruptivas para una app de salud mental?",
    "¿Cómo reinventar la experiencia de compra online?",
    "¿Cómo diseñar un sistema de educación personalizado?",
    # Negocio
    "¿Cómo reducir el churn en un SaaS B2B?",
    "¿Cómo escalar un marketplace de servicios locales?",
    "¿Cómo monetizar datos abiertos sin violar privacidad?",
    # Sistemas complejos
    "¿Cómo gobernar una DAO sin centralización?",
    "¿Cómo coordinar robots autónomos en almacén?",
    "¿Cómo gestionar crisis en red social masiva?",
    # Ética y sociedad
    "¿Cómo evitar sesgo algorítmico en decisiones de crédito?",
    "¿Cómo diseñar IA explicables para healthcare?",
    "¿Cómo proteger datos de niños en plataformas educativas?",
]

def measure_semantic_diversity(ideas):
    """Mide diversidad semántica: familias únicas (family + family2)."""
    all_families = set()
    for i in ideas:
        all_families.add(i.get("family", "unknown"))
        all_families.add(i.get("family2", "unknown"))
    all_families.discard("unknown")
    primary_families = [i.get("family", "unknown") for i in ideas]
    return {
        "unique_families": len(all_families),
        "unique_primary_families": len(set(primary_families)),
        "total_ideas": len(ideas),
        "diversity_ratio": round(len(all_families) / max(1, len(ideas)), 3),
        "primary_diversity_ratio": round(len(set(primary_families)) / max(1, len(ideas)), 3),
        "family_distribution": dict(Counter(primary_families)),
    }

def measure_structural_repetition(ideas):
    """Mide repetición estructural y diversidad estructural."""
    structures = []
    for i in ideas:
        cv = i.get("causal_variables", {})
        struct = tuple(sorted(cv.items()))
        structures.append(struct)
    unique_structures = len(set(structures))
    # Count unique axes changed
    all_axes = set()
    for i in ideas:
        axes = i.get("causal_axes_changed", [])
        all_axes.update(axes)
    return {
        "unique_structures": unique_structures,
        "total_ideas": len(structures),
        "structural_diversity_ratio": round(unique_structures / max(1, len(structures)), 3),
        "repetition_ratio": round(1 - (unique_structures / max(1, len(structures))), 3),
        "unique_axes_changed": len(all_axes),
        "axes_used": list(all_axes),
    }

def measure_catalog_dependency(ideas, methods_used):
    """Mide dependencia del catálogo: cuánto dependen las ideas de los métodos seleccionados."""
    method_names = [m.get("name", "") for m in methods_used]
    idea_methods = []
    for i in ideas:
        m1 = i.get("method1_name", "")
        m2 = i.get("method2_name", "")
        idea_methods.extend([m1, m2])
    # Cuántas veces aparece cada método
    method_counts = Counter(idea_methods)
    top_methods = method_counts.most_common(3)
    return {
        "methods_available": len(methods_used),
        "methods_used_in_ideas": len(set(idea_methods)),
        "top_methods": top_methods,
        "dependency_score": round(sum(c for _, c in top_methods) / max(1, len(idea_methods)), 3),
    }

def measure_variation_between_executions(query, n_runs=3):
    """Mide variación entre ejecuciones con la misma query."""
    results = []
    for _ in range(n_runs):
        packet = engine.activate(query, "auto", "balanced", 4)
        idea_ids = [i["id"] for i in packet["innovation"]["ideas"]]
        families = [i["family"] for i in packet["innovation"]["ideas"]]
        results.append({"ids": idea_ids, "families": families})
    # Todas las ejecuciones producen los mismos IDs? (determinismo)
    all_same_ids = all(r["ids"] == results[0]["ids"] for r in results)
    all_same_families = all(r["families"] == results[0]["families"] for r in results)
    return {
        "n_runs": n_runs,
        "deterministic_ids": all_same_ids,
        "deterministic_families": all_same_families,
    }

def measure_rupture_degree(ideas):
    """Mide grado de ruptura: cuántas ideas mueven ejes causales."""
    real_divergent = sum(1 for i in ideas if i.get("divergence_real"))
    extreme_count = sum(1 for i in ideas if i.get("extreme"))
    total = len(ideas)
    return {
        "real_divergent": real_divergent,
        "extreme": extreme_count,
        "rupture_ratio": round(real_divergent / max(1, total), 3),
        "extreme_ratio": round(extreme_count / max(1, total), 3),
    }

def measure_specificity(ideas, query):
    """Mide especificidad respecto al problema: cuántas ideas mencionan palabras de la query."""
    query_words = set(query.lower().split())
    specific_count = 0
    for i in ideas:
        desc = i.get("description", "").lower()
        if any(w in desc for w in query_words if len(w) > 4):
            specific_count += 1
    return {
        "specific_ideas": specific_count,
        "total_ideas": len(ideas),
        "specificity_ratio": round(specific_count / max(1, len(ideas)), 3),
    }

def run_benchmark():
    """Ejecuta benchmark completo."""
    print("=" * 70)
    print("BENCHMARK REAL CRIBA BLACKFORGE")
    print("=" * 70)
    print(f"Consultas: {len(QUERIES)}")
    print(f"Dominios: seguridad, innovación, negocio, sistemas, ética")
    print()

    all_results = []
    summary = {
        "total_queries": len(QUERIES),
        "total_ideas": 0,
        "avg_diversity_ratio": 0,
        "avg_rupture_ratio": 0,
        "avg_specificity_ratio": 0,
        "deterministic": True,
    }

    for idx, query in enumerate(QUERIES):
        print(f"\n{'='*70}")
        print(f"[{idx+1}/{len(QUERIES)}] {query[:60]}...")
        print(f"{'='*70}")

        # Ejecutar pipeline
        packet = engine.activate(query, "auto", "balanced", 12)
        ideas = packet["innovation"]["ideas"]
        methods_used = packet["supporting_methods"]

        # Medir métricas
        diversity = measure_semantic_diversity(ideas)
        repetition = measure_structural_repetition(ideas)
        dependency = measure_catalog_dependency(ideas, methods_used)
        variation = measure_variation_between_executions(query, n_runs=2)
        rupture = measure_rupture_degree(ideas)
        specificity = measure_specificity(ideas, query)

        # Resultado
        result = {
            "query": query,
            "n_ideas": len(ideas),
            "diversity": diversity,
            "repetition": repetition,
            "dependency": dependency,
            "variation": variation,
            "rupture": rupture,
            "specificity": specificity,
            "decision": packet["decision"]["pipeline_action"],
            "families": len(set(i["family"] for i in ideas)),
        }
        all_results.append(result)

        # Imprimir resumen
        print(f"  Ideas: {len(ideas)}")
        print(f"  Familias: {result['families']}")
        print(f"  Diversidad: {diversity['diversity_ratio']} ({diversity['unique_families']} únicas)")
        print(f"  Ruptura: {rupture['rupture_ratio']} ({rupture['real_divergent']} reales)")
        print(f"  Repetición estructural: {repetition['repetition_ratio']}")
        print(f"  Especificidad: {specificity['specificity_ratio']}")
        print(f"  Determinista: {variation['deterministic_ids']}")
        print(f"  Decisión: {result['decision']}")

        summary["total_ideas"] += len(ideas)
        summary["avg_diversity_ratio"] += diversity["diversity_ratio"]
        summary["avg_rupture_ratio"] += rupture["rupture_ratio"]
        summary["avg_specificity_ratio"] += specificity["specificity_ratio"]
        if not variation["deterministic_ids"]:
            summary["deterministic"] = False

    # Resumen final
    n = len(QUERIES)
    summary["avg_diversity_ratio"] = round(summary["avg_diversity_ratio"] / n, 3)
    summary["avg_rupture_ratio"] = round(summary["avg_rupture_ratio"] / n, 3)
    summary["avg_specificity_ratio"] = round(summary["avg_specificity_ratio"] / n, 3)

    print("\n" + "=" * 70)
    print("RESUMEN GLOBAL")
    print("=" * 70)
    print(f"Consultas ejecutadas: {summary['total_queries']}")
    print(f"Total ideas generadas: {summary['total_ideas']}")
    print(f"Ideas promedio por query: {round(summary['total_ideas'] / n, 1)}")
    print(f"Diversidad promedio: {summary['avg_diversity_ratio']}")
    print(f"Ruptura promedio: {summary['avg_rupture_ratio']}")
    print(f"Especificidad promedio: {summary['avg_specificity_ratio']}")
    print(f"Determinista: {summary['deterministic']}")

    # Guardar resultados
    output = Path("E:/PROYECTS/CRIBA/verification/benchmark_real_results.json")
    with open(output, "w", encoding="utf-8") as f:
        json.dump({"summary": summary, "results": all_results}, f, ensure_ascii=False, indent=2)
    print(f"\nResultados guardados en: {output}")

if __name__ == "__main__":
    run_benchmark()
