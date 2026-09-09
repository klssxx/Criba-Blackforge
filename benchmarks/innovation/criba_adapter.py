"""Adaptador real de la condición C_CRIBA al LOOP de CRIBA (hallazgo 6).

C_CRIBA no es un prompt distinto: ejecuta el pipeline real — lotería
estratificada + selector diversity-aware sobre el catálogo de métodos — con la
semilla propagada (reproducible). Es lo que el harness necesita para que la
comparación mida a CRIBA y no a un texto de prompt.

Sin LLM: produce candidatos ESTRUCTURADOS (cruce de métodos + genoma), no
prosa interpretada. La interpretación por modelo pertenece a las condiciones
A_DIRECT/B_STRONG_PROMPT vía model_fn; medir CRIBA es medir su selección
determinista y su diversidad de mecanismos, no su redacción.
"""
from __future__ import annotations

from typing import Any


def criba_fn(problema_texto: str, seed: int, n_candidatos: int) -> list[dict[str, Any]]:
    """Ejecuta el loop de selección de CRIBA sobre el problema, con semilla.

    Devuelve ``n_candidatos`` candidatos estructurados (cruce de métodos),
    reproducibles por semilla. Determinista y offline.
    """
    from criba.catalog import methods as catalog_methods
    from criba.diversity_selector import select_finalists
    from criba.lottery import LotteryEngine

    engine = LotteryEngine.from_methods(catalog_methods(), seed=seed)
    # una ronda estratificada produce el pool de cruces
    engine.run_round(mode="stratified", batch_size=max(8, n_candidatos * 2),
                     query=problema_texto)
    pool = engine.get_top_ideas(max(n_candidatos * 4, 8))
    finalists, _report = select_finalists(pool, n_candidatos)
    out: list[dict[str, Any]] = []
    for idx, idea in enumerate(finalists):
        out.append({
            "idea_id": str(idea.get("idea_id") or f"criba-{seed}-{idx:02d}"),
            "title": str(idea.get("title", "")),
            "description": str(idea.get("description", "")),
            "score": float(idea.get("score", 0.0)),
            "genome": idea.get("genome") or {},
            "methods": [idea.get("method1", ""), idea.get("method2", "")],
            "classes": [idea.get("class1", ""), idea.get("class2", "")],
        })
    return out
