"""Cableado del interprete-serendipia dentro del pipeline del engine.

Extrae de engine.activate() la capa P2 (bloque ``innovation.interprete``)
para que TODO lo relacionado con el interprete viva en este paquete:
prefilter, juez, adaptador, store, protocolo e IDs.

Contrato:
- Flag ``FEATURES["interprete_serendipia"]`` OFF -> ``{"applied": False}``
  sin tocar nada más (packet base intacto, golden master a salvo).
- ON -> interpreta el lote con IDs DETERMINISTAS derivados de
  (query, seed, modelo) — misma seed + misma query + mismo modelo
  producen los mismos run_id/activation_id y la dedup de InterpreteStore
  dispara en la segunda pasada (PR-0).
- Cualquier fallo del interprete NO rompe el pipeline: el bloque se
  degrada a ``{"applied": True, "error": "interprete_no_disponible"}``.
"""
from __future__ import annotations

from typing import Any

from criba.constants import DEFAULT_DB, FEATURES
from criba.interprete.ids import interprete_ids
from criba.interprete.juez import JuezInterprete
from criba.storage import Storage


def build_interprete_block(
    query: str,
    ideas: list[dict[str, Any]],
    context: dict[str, Any] | None,
) -> dict[str, Any]:
    """Construye el bloque ``innovation.interprete`` del packet.

    ``context`` es el context dict del engine (seed, database, zai_api_key...).
    """
    if not FEATURES.get("interprete_serendipia"):
        return {"applied": False}

    ctx = context if isinstance(context, dict) else {}
    try:
        api_key = ctx.get("zai_api_key")
        storage = Storage(ctx.get("database", DEFAULT_DB)) if "database" in ctx else None
        juez = JuezInterprete(api_key=api_key, storage=storage)
        seed = ctx.get("seed")
        # PR-0: IDs deterministas — misma (query, seed, modelo) -> mismos IDs.
        ids = interprete_ids(query=query, seed=seed, modelo=juez.adaptador.model)
        interp_result = juez.interpretar_lote(
            query=query,
            ideas=ideas,
            activation_id=ids.activation_id,
            run_id=ids.run_id,
            seed=seed,
        )
        return {
            "applied": True,
            "modelo": interp_result["modelo"],
            "fallback_usado": interp_result["fallback_usado"],
            "interpretados": [
                {
                    "idea_id": r["id"],
                    "labels": r.get("interprete_labels", []),
                    "score": r.get("interprete_score", 0.0),
                    "veredicto": r.get("interprete_verdict", "PENDIENTE"),
                    "dh": r.get("prefilter", {}).get("dh"),
                    "registro": r.get("_registro", {}).get("status"),
                }
                for r in interp_result["interpretados"]
            ],
            "prefiltrado_stats": interp_result["prefiltrado"]["stats"],
            "top_interprete": interp_result["interpretados"][0] if interp_result["interpretados"] else None,
        }
    except Exception:
        return {"applied": True, "error": "interprete_no_disponible"}
