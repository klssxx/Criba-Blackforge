"""Prefiltrado causal top-N antes de la interpretación del modelo.

Reemplaza al juez de BASURA (umbral 0.9 inalcanzable) con un filtro que
garantiza que las candidatas tengan tangibilidad causal real:

- Dh governor: 0.45 <= D_H <= 0.85 (zona sweet-spot Kauffman).
- SOTA taboo: rechaza clichés del estado del arte (99 patrones).
- novelty recortado a [0.65, 0.85]: banda de serendipia asociativa.

NO promete EXTRAORDINARIA: promete candidatos con tangibilidad causal.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from criba.core.adjacent_possible import (
    AdjacentPossibleGovernor,
    SOTA_TABOO_PATTERNS,
)


def _novelty_band(idea: dict[str, Any], lo: float = 0.65, hi: float = 0.85) -> bool:
    """Idea dentro de la banda de serendipia asociativa. Si no hay novelty, pasa (no filtra)."""
    n = idea.get("convergence", {}).get("novelty")
    if n is None:
        return True
    return lo <= float(n) <= hi


def dh_out_of_range(idea: dict[str, Any]) -> float | None:
    """Retorna D_H ajustado. None si cae fuera de [0.45, 0.85].

    Usa causal_axes_changed (los ejes que REALMENTE mutó el operador),
    no todos los causal_variables que difieren del base.
    """
    cv: Mapping[str, Any] = idea.get("causal_variables", {})
    # El engine registra los ejes realmente mutados en causal_axes_changed
    axes_moved = idea.get("causal_axes_changed", [])
    g = AdjacentPossibleGovernor()
    contract = g.evaluate_proposal(
        proposal_id=idea.get("id", "x"),
        target_axiom=idea.get("known_space_element", "problema"),
        intervention=idea["description"],
        causal_axes_moved=axes_moved,
        domain=idea.get("domain", "general"),
    )
    if g.min_dist <= contract.adjacent_distance <= g.max_dist:
        return contract.adjacent_distance
    return None


def sota_taboo_violations(idea: dict[str, Any]) -> list[str]:
    text = f"{idea.get('description', '')} {idea.get('mechanism_causal', '')}".lower()
    return [p for p in SOTA_TABOO_PATTERNS if p in text]


class PreFilter:
    """Filtra el conjunto de ideas producidas por activate() a top-N candidatas
    con tangibilidad causal. Deterministic (seed no afecta el orden de salida
    dentro de un mismo lote — preserva el orden del motor)."""

    def __init__(
        self,
        top_n: int = 12,
        dh_lo: float = 0.45,
        dh_hi: float = 0.85,
        novelty_lo: float = 0.65,
        novelty_hi: float = 0.85,
        strict: bool = True,
    ) -> None:
        self.top_n = top_n
        self.dh_lo = dh_lo
        self.dh_hi = dh_hi
        self.novelty_lo = novelty_lo
        self.novelty_hi = novelty_hi
        self.strict = strict
        # En modo no estricto (fallback local), la banda de novelty se relaja
        # para que el pipeline sea útil sin modelo cloud.
        if not strict:
            self.novelty_lo = 0.25
            self.novelty_hi = 0.95
        self.governor = AdjacentPossibleGovernor(min_dist=dh_lo, max_dist=dh_hi)

    def apply(self, ideas: Sequence[dict[str, Any]]) -> dict[str, Any]:
        """Retorna {candidates, dropped, stats} con top-N candidatas."""
        candidates: list[dict[str, Any]] = []
        dropped: list[dict[str, Any]] = []
        dh_rejected = tabu_rejected = novelty_rejected = 0

        for idea in ideas:
            # 1. SOTA taboo primero (rechaza clichés del estado del arte)
            v = sota_taboo_violations(idea)
            if v:
                tabu_rejected += 1
                dropped.append({"id": idea.get("id"), "reason": "sota_taboo",
                                "violations": v[:3]})
                continue
            # 2. Dh governor (rango causal [0.45, 0.85])
            dh = dh_out_of_range(idea)
            if dh is None:
                dh_rejected += 1
                dropped.append({"id": idea.get("id"), "reason": "dh_fuera_rango"})
                continue
            # 3. Novelty band (serendipia asociativa)
            if not _novelty_band(idea, self.novelty_lo, self.novelty_hi):
                novelty_rejected += 1
                dropped.append({"id": idea.get("id"), "reason": "novelty_fuera_banda"})
                continue
            idea = dict(idea)
            idea["prefilter"] = {"dh": dh, "novelty_band": [self.novelty_lo, self.novelty_hi]}
            candidates.append(idea)

        candidates.sort(
            key=lambda x: x.get("convergence", {}).get("value_score", 0.0),
            reverse=True,
        )
        top = candidates[: self.top_n]

        return {
            "candidates": top,
            "dropped": dropped,
            "stats": {
                "total_input": len(ideas),
                "kept": len(candidates),
                "selected": len(top),
                "dh_rejected": dh_rejected,
                "tabu_rejected": tabu_rejected,
                "novelty_rejected": novelty_rejected,
                "dh_range": [self.dh_lo, self.dh_hi],
                "novelty_band": [self.novelty_lo, self.novelty_hi],
            },
        }
