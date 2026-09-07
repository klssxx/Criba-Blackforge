"""Medidor de diversidad de finalistas (PRE/POST, determinista, local).

Métricas honestas sobre un conjunto de finalistas, reutilizando
criba.similarity (genome_distance/classify). Cada métrica declara dominio,
rango y dirección en la docstring; sin 1.0 cuando faltan datos.

Uso:
    python benchmarks/diversity_measure.py --selector score_top_n --out artifacts/diversity_baseline.json
    python benchmarks/diversity_measure.py --selector diversity_aware --out artifacts/diversity_post.json

El selector NO vive aquí: este script aplica la función de selección que se le
pase por nombre (`score_top_n` = comportamiento actual; `diversity_aware` =
nuevo, cuando exista) y mide el resultado sobre los MISMOS fixtures.
"""
from __future__ import annotations

import argparse
import itertools
import json
import sys
from pathlib import Path
from typing import Any, Callable

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from benchmarks.diversity_fixtures import ANTI_CONVERGENCE_POOL, PAIR_REUSE_POOL  # noqa: E402
from src.criba.similarity import classify  # noqa: E402

SELECTOR = "score_top_n"
TOP_N = 3


def select_score_top_n(pool: list[dict], n: int = TOP_N) -> list[dict]:
    """Comportamiento actual de get_top_ideas: top-N por score."""
    return sorted(pool, key=lambda c: c["score"], reverse=True)[:n]


def _pair_verdicts(finalists: list[dict]) -> list[tuple[str, str, str]]:
    out = []
    for a, b in itertools.combinations(finalists, 2):
        out.append((a["idea_id"], b["idea_id"], classify(a["genome"], b["genome"])["verdict"]))
    return out


def measure(finalists: list[dict], pool: list[dict]) -> dict[str, Any]:
    """Métricas del conjunto finalista. Rangos documentados en cada campo."""
    pair_verdicts = _pair_verdicts(finalists)
    pairs = [v for _, _, v in pair_verdicts]
    n_pairs = len(pairs)

    # duplication_rate: proporción de pares finalistas clasificados
    # probable_duplicate. Rango [0,1]; 0 = sin duplicados probables.
    duplication_rate = (pairs.count("probable_duplicate") / n_pairs) if n_pairs else 0.0

    # close_variant_rate: proporción de pares close_variant. [0,1].
    close_variant_rate = (pairs.count("close_variant") / n_pairs) if n_pairs else 0.0

    # structural_diversity: media de genome_distance entre pares finalistas.
    # [0,1]; mayor = más diversos. Con <2 finalistas: null (datos insuficientes).
    if len(finalists) >= 2:
        dists = [
            __import__("src.criba.similarity", fromlist=["genome_distance"])
            .genome_distance(a["genome"], b["genome"])["distance"]
            for a, b in itertools.combinations(finalists, 2)
        ]
        structural_diversity = round(sum(dists) / len(dists), 4)
    else:
        structural_diversity = None

    # unique_mechanisms: mecanismos principales distintos entre finalistas.
    mechanisms = {
        next(iter(g["genome"]["mechanism"]), "")
        for g in finalists if g["genome"].get("mechanism")
    }
    unique_mechanisms = len(mechanisms)

    # family_coverage: familias de finalistas / familias del pool. [0,1].
    pool_families = {c["family"] for c in pool}
    family_coverage = (
        len({c["family"] for c in finalists}) / len(pool_families) if pool_families else None
    )

    # pair_reuse_rate: proporción de finalistas que repiten el par de métodos
    # de otro finalista. [0,1]; 0 = todos los pares distintos.
    method_pairs = [tuple(sorted(c.get("methods", []))) for c in finalists]
    repeats = len(method_pairs) - len(set(method_pairs))
    pair_reuse_rate = repeats / len(method_pairs) if method_pairs else 0.0

    return {
        "duplication_rate": round(duplication_rate, 4),
        "close_variant_rate": round(close_variant_rate, 4),
        "structural_diversity": structural_diversity,
        "unique_mechanisms": unique_mechanisms,
        "family_coverage": round(family_coverage, 4) if family_coverage is not None else None,
        "pair_reuse_rate": round(pair_reuse_rate, 4),
        "finalists": [c["idea_id"] for c in finalists],
        "pair_verdicts": [list(p) for p in pair_verdicts],
    }


def run_measurement(selector: str) -> dict[str, Any]:
    selectors: dict[str, Callable[[list[dict]], list[dict]]] = {
        "score_top_n": select_score_top_n,
    }
    if selector not in selectors:
        raise SystemExit(f"selector desconocido: {selector}; disponibles: {list(selectors)}")
    select = selectors[selector]
    return {
        "selector": selector,
        "fixtures": {
            "anti_convergence": measure(select(ANTI_CONVERGENCE_POOL), ANTI_CONVERGENCE_POOL),
            "pair_reuse": measure(select(PAIR_REUSE_POOL), PAIR_REUSE_POOL),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--selector", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    report = run_measurement(args.selector)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
