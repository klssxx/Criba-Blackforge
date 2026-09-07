"""Servicio «Actualizar fuentes»: adquisición real → deduplicación → informe.

Mandato §6: el botón adquiere información, la normaliza, deduplica, guarda y
muestra resultados REALES (nuevos/modificados/duplicados/errores por fuente).
Sin porcentajes sintéticos ni éxito sin adquisición. Reutilizable desde GUI,
CLI, API y MCP. El modo offline se resuelve en el transporte: aquí solo se
declara y el informe muestra el bloqueo, nunca «0 errores».
"""
from __future__ import annotations

import hashlib
import time
from typing import Any

from .contracts import EvidenceDocument
from .storage.store import IntelligenceStore
from .sources import build_sources, default_context
from .sources.security_feeds import CisaKevSource, MitreAttackSource

# Perfiles de actualización (mandato §6)
PROFILE_GENERAL = ("crossref", "github", "wikipedia", "google_patents")
PROFILE_BLACKFORGE = ("cisa_kev", "mitre_attack")
PROFILE_EXTRA = ("openalex", "arxiv", "epo", "clinicaltrials", "nsf_awards")


def _doc_fingerprint(doc: EvidenceDocument) -> str:
    """Huella de contenido estable: URL (o título como fallback) + fuente."""
    key = f"{doc.source_id}|{doc.url or doc.title}|{doc.title}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def _build_profile(profile: str, *, offline: bool, extra: bool = False,
                   credentials: dict[str, str] | None = None,
                   cache: IntelligenceStore | None = None) -> list[Any]:
    context = default_context(cache=cache, credentials=credentials, offline=offline)
    if profile == "blackforge":
        return [CisaKevSource(context), MitreAttackSource(context)]
    sources = build_sources(context, extra=extra)
    if profile == "general":
        # Orden del mandato: Crossref + GitHub primero (sin desactivar el par gratuito).
        order = {"crossref": 0, "github": 1}
        return sorted(sources, key=lambda s: order.get(s.SOURCE_ID, 9))
    return sources


def refresh_sources(
    queries: list[str],
    *,
    profile: str = "general",
    store: IntelligenceStore | None = None,
    offline: bool = False,
    extra: bool = False,
    credentials: dict[str, str] | None = None,
    per_query_limit: int = 5,
    sources: list[Any] | None = None,
) -> dict[str, Any]:
    """Ejecuta la actualización y devuelve un informe con cantidades reales.

    Cada documento se deduplica por URL/contenido contra el almacén:
    ``nuevo`` / ``modificado`` / ``duplicado``. Los fallos de fuente se
    muestran como errores; un error NO equivale a «sin resultados».
    """
    if not queries or all(not q.strip() for q in queries):
        raise ValueError("se necesita al menos una consulta no vacía")
    clean_queries = [q.strip() for q in queries if q.strip()]
    run_store = store  # None → adquisición sin persistencia (informe puro)

    active_sources = sources or _build_profile(
        profile, offline=offline, extra=extra, credentials=credentials, cache=run_store)

    started = time.monotonic()
    per_source: list[dict[str, Any]] = []
    seen_urls: dict[str, str] = {}
    totals = {"consultas": 0, "documentos": 0, "nuevos": 0,
              "modificados": 0, "duplicados": 0, "errores": 0}

    for source in active_sources:
        sid = source.source_id()
        summary: dict[str, Any] = {
            "source_id": sid, "ok": 0, "documents": 0,
            "nuevos": 0, "modificados": 0, "duplicados": 0,
            "errores": 0, "errors": [], "offline_blocked": False,
        }
        for query in clean_queries:
            totals["consultas"] += 1
            try:
                result = source.search(query, limit=per_query_limit)
            except Exception as exc:  # noqa: BLE001 - un fallo no aborta el resto
                summary["errores"] += 1
                summary["errors"].append(f"{query}: {exc}")
                continue
            if not result.ok:
                summary["errores"] += 1
                blocked = "OFFLINE" in (result.error or "").upper()
                summary["offline_blocked"] = summary["offline_blocked"] or blocked
                summary["errors"].append(f"{query}: {result.error or 'sin respuesta'}")
                continue
            summary["ok"] += 1
            summary["documents"] += len(result.documents)
            for doc in result.documents:
                fp = _doc_fingerprint(doc)
                existing = seen_urls.get(doc.url or doc.title)
                if existing == fp:
                    summary["duplicados"] += 1
                    continue
                seen_urls[doc.url or doc.title] = fp
                if run_store is not None:
                    status = _persist(run_store, doc, fp)
                    summary[status] += 1
                    totals[status] += 1
            totals["documentos"] += len(result.documents)
        if summary["documents"] == 0 and summary["errores"] > 0:
            totals["errores"] += summary["errores"]
        elif summary["errores"]:
            totals["errores"] += summary["errores"]
        per_source.append(summary)

    report = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()) + "Z",
        "profile": profile,
        "offline": offline,
        "queries": clean_queries,
        "elapsed_s": round(time.monotonic() - started, 2),
        "per_source": per_source,
        "totals": totals,
    }
    if run_store is not None:
        run_store.save_refresh_report(report)
    return report


def _persist(store: IntelligenceStore, doc: EvidenceDocument, fp: str) -> str:
    """Guarda el documento clasificándolo nuevo/modificado/duplicado."""
    existing = store.find_by_url(doc.url) if doc.url else None
    if existing:
        if existing.get("content_hash") == fp:
            return "duplicados"
        doc.doc_id = existing["doc_id"]  # misma identidad, contenido nuevo
        doc.metadata = {**doc.metadata, "previous_hash": existing.get("content_hash")}
        store.save_document({**doc.to_dict(), "content_hash": fp})
        return "modificados"
    store.save_document({**doc.to_dict(), "content_hash": fp})
    return "nuevos"


def format_report(report: dict[str, Any]) -> str:
    """Líneas legibles con las cantidades reales del informe."""
    t = report["totals"]
    lines = [
        f"Actualizar fuentes ({report['profile']}{' · OFFLINE' if report['offline'] else ''})",
        f"Consultas: {t['consultas']} · Documentos: {t['documentos']} · "
        f"Nuevos: {t['nuevos']} · Modificados: {t['modificados']} · "
        f"Duplicados: {t['duplicados']} · Errores: {t['errores']}",
    ]
    for s in report["per_source"]:
        state = (f"{s['source_id']}: {s['documents']} docs "
                 f"({s['nuevos']} nuevos, {s['duplicados']} duplicados)")
        if s["offline_blocked"]:
            state += " · BLOQUEADO por modo offline"
        if s["errors"]:
            state += f" · errores: {'; '.join(s['errors'][:3])}"
        lines.append("  " + state)
    return "\n".join(lines)
