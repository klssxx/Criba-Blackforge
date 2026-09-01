"""Juez orquestador del interprete-serendipia.

Pipeline:
  activate() --[ideas]--> PreFilter (Dh 0.45-0.85 + SOTA taboo + novelty band) --> top-N
  --> CloudInterprete/LocalInterprete (preguntas de expansión) --> veredictos
  --> InterpreteStore (SQLite auditable, deduplicación por seed+comb_id)

Reemplaza la etiqueta estática BASURA/EXTRAORDINARIA del LotteryEngine
con labels epistemológicos + score interprete + veredicto cualitativo.

Mantiene AUSENCIA DE DAÑO: prefiltrado determinista (no consume créditos);
el modelo solo interpreta candidatas ya prevalidadas causalmente. En fallo de
plan (429) o red, la idea se marca PENDIENTE_PLAN y se reinterpreta en el
próximo ciclo sin bloquear el pipeline.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from criba.interprete.adaptador import CloudInterprete, LocalInterprete
from criba.interprete.prefilter import PreFilter
from criba.interprete.store import InterpreteStore

if TYPE_CHECKING:
    from criba.storage import Storage


class JuezInterprete:
    """Orquesta prefiltrado + interpretación + registro."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "glm-5.3-flash",
        storage: "Storage | None" = None,
    ) -> None:
        self.prefilter = PreFilter(top_n=12, strict=bool(api_key))
        self.adaptador = CloudInterprete(api_key, model) if api_key else LocalInterprete()
        self.storage = storage
        self.store: InterpreteStore | None = None
        if storage is not None:
            self.store = InterpreteStore(storage)

    def interpretar_lote(
        self,
        query: str,
        ideas: list[dict[str, Any]],
        activation_id: str,
        run_id: str,
        seed: int | None = None,
    ) -> dict[str, Any]:
        """Toma el lote de ideas, aplica prefiltrado, interpreta top-N, registra."""
        prefiltrado = self.prefilter.apply(ideas)
        candidates = prefiltrado["candidates"]
        resultados: list[dict[str, Any]] = []
        for idea in candidates:
            idea = dict(idea)
            interp = self.adaptador.interpretar(query, idea)
            idea["interprete_labels"] = interp["labels"]
            idea["interprete_score"] = interp["score"]
            idea["interprete_verdict"] = interp["veredicto"]
            idea["interprete_analisis"] = interp.get("analisis", "")
            idea["interprete_protocolo"] = interp.get("protocolo_aplicado", {})

            if self.store:
                modelo = self.adaptador.model
                reg = self.store.record_decision(
                    activation_id=activation_id, idea=idea,
                    modelo=modelo, run_id=run_id, seed=seed,
                )
                idea["_registro"] = reg
            else:
                idea["_registro"] = {"status": "unregistered", "reason": "no storage"}

            resultados.append(idea)

        resultados.sort(
            key=lambda x: (x.get("interprete_score", 0.0),
                           x.get("convergence", {}).get("value_score", 0.0)),
            reverse=True,
        )
        return {
            "query": query,
            "activation_id": activation_id,
            "total_ideas_entrada": len(ideas),
            "prefiltrado": prefiltrado,
            "interpretados": resultados,
            "modelo": self.adaptador.model,
            "fallback_usado": isinstance(self.adaptador, LocalInterprete),
        }