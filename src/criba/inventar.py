"""``criba inventar``: el loop de innovación completo en un comando.

Cadena (siempre 0€, reproducible por semilla, nunca afirma novedad):

1. **Lotería estratificada** — divergencia determinista por clases de
   pensamiento (perspectiva/generación/ruptura/escape) con banco de dominio
   como segundo dado opcional.
2. **Propuesta** — el intérprete aplica el cruce al problema y devuelve
   hipótesis + mecanismo + aportación de cada técnica. Sin modelo disponible
   el estado queda ``PENDIENTE_INTERPRETACION``: no se fabrica contenido.
3. **Juez (crítica automática)** — ``LocalInterprete`` evalúa la propuesta;
   sin clave, scoring offline. Una llamada distinta no es validación
   independiente.
4. **Prior-art del mecanismo** — la búsqueda de antecedentes usa el
   MECANISMO interpretado (no el título del cruce). Sin mecanismo no hay
   búsqueda: ``UNRESOLVED`` honesto. Lattice determinista → par gratuito
   (Wikipedia + Google Patents) → skeptic → verdict → mutation loop
   fail-closed. Veredictos posibles: ``UNRESOLVED`` / ``PARTIAL_PRIOR_ART``
   / ``SURVIVED_SEARCH``.
5. **Ficha + ledger** — salida legible y ``invention_ledger/verdicts.jsonl``
   append-only con el registro completo por candidato.

Modo offline: bloquea TODA adquisición en el transporte común
(``Transport.offline``) y no construye fuentes de red.
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .catalog import methods as catalog_methods
from .intelligence.contracts import InventionCandidate, SourceQueryResult
from .intelligence.prior_art.lattice import build_query_lattice
from .intelligence.prior_art.mutation_loop import run_prior_art_mutation_loop
from .intelligence.prior_art.protocol import AdversarialSearchProtocol
from .intelligence.prior_art.scouts import CrossDomainScout
from .intelligence.prior_art.skeptic import PriorArtSkeptic
from .intelligence.prior_art.verdict import PriorArtVerdictEngine
from .intelligence.sources import build_sources, default_context
from .intelligence.sources.protocol import IntelligenceSource
from .interprete.adaptador import LocalInterprete
from .lottery import LotteryEngine

_PROPOSER = Callable[..., dict[str, Any]]  # (query, idea, domain, evidence) -> dict

_PENDING: dict[str, Any] = {
    "estado": "PENDIENTE_INTERPRETACION",
    "hipotesis": "",
    "mecanismo": "",
    "aportacion_por_tecnica": [],
    "supuestos": [],
    "prueba_concreta": "",
    "error": "",
}


def _pending_proposal(error: str) -> dict[str, Any]:
    pending = dict(_PENDING)
    pending["error"] = error
    return pending


def _ledger_dir() -> Path:
    base = Path(os.environ.get("LOCALAPPDATA") or Path.home())
    return base / "CRIBA-Blackforge" / "invention_ledger"


def _offline_mode(offline: bool | None) -> bool:
    if offline is not None:
        return offline
    return os.environ.get("CRIBA_INVENTAR_OFFLINE", "") == "1"


def _stable_run_id(query: str, seed: int) -> str:
    """Huella estable entre procesos: sha256 de semilla+consulta.

    Sustituye a ``hash()`` de Python (aleatorio entre procesos).
    """
    digest = hashlib.sha256(f"{seed}|{query}".encode("utf-8")).hexdigest()[:12]
    return f"invent-{seed}-{digest}"


def _default_proponer(
    query: str,
    idea: dict[str, Any],
    domain: dict[str, Any] | None,
    offline: bool = False,
    evidence: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Ruta real de propuesta. Con ``offline=True`` nunca toca la red.

    La comprobación vive AQUÍ y no solo dentro de ``LocalInterprete`` (cuyo
    estado depende de NOUS_API_KEY): el modo offline del comando debe bloquear
    la propuesta aunque haya credenciales configuradas. ``evidence`` (documentos
    locales pertinentes) se entrega al intérprete, no solo se archiva.
    """
    if offline:
        return _pending_proposal("modo offline")
    try:
        return LocalInterprete().proponer(query, idea, domain, evidence)
    except Exception as exc:  # noqa: BLE001 - la propuesta nunca rompe el loop
        return _pending_proposal(str(exc))


def _judge(query: str, idea: dict[str, Any], offline: bool) -> dict[str, Any]:
    """Crítica automática; falla cerrado a PENDIENTE sin red."""
    if offline:
        return {"veredicto": "PENDIENTE_OFFLINE", "labels": [], "score": 0.0, "analisis": ""}
    try:
        return LocalInterprete().interpretar(query, idea)
    except Exception:  # noqa: BLE001 - el juez nunca rompe el loop
        return {"veredicto": "PENDIENTE_OFFLINE", "labels": [], "score": 0.0, "analisis": ""}


def _assess_candidate(
    candidate: InventionCandidate,
    sources: list[IntelligenceSource],
) -> dict[str, Any]:
    """Lattice → scout (≥2 dominios) → skeptic → verdict → mutation loop.

    La búsqueda parte del MECANISMO. Sin mecanismo interpretado no hay
    búsqueda: ``UNRESOLVED`` con detalle honesto (no equivale a novedad).
    """
    protocol = AdversarialSearchProtocol(
        candidate_id=candidate.candidate_id,
        max_prior_art_rounds=2,
        max_mutations_per_candidate=1,
    )
    verdict_engine = PriorArtVerdictEngine()
    mechanism = (candidate.mechanism or "").strip()
    if not mechanism:
        return {
            "verdict": "UNRESOLVED",
            "queries": [],
            "rounds": 0,
            "mutations": 0,
            "detail": "sin-mecanismo: interpretación pendiente, no se buscó antecedente",
        }

    lattice = build_query_lattice(mechanism, max_variants=4)
    variant = lattice[0] if lattice else None
    if variant is None:
        return {
            "verdict": "UNRESOLVED",
            "queries": [],
            "rounds": 0,
            "mutations": 0,
            "detail": "lattice-vacío",
        }

    try:
        scout = CrossDomainScout(sources)
        results: dict[str, SourceQueryResult] = scout.cross_search(variant, limit_per_source=3)
    except ValueError as exc:
        return {
            "verdict": "UNRESOLVED",
            "queries": [],
            "rounds": 0,
            "mutations": 0,
            "detail": f"fuentes no utilizables: {exc}",
        }
    skeptic = PriorArtSkeptic()
    report = skeptic.review(candidate, results)
    assessment = verdict_engine.assess(candidate, results, report, matches=[])

    try:
        mutation = run_prior_art_mutation_loop(
            candidate=candidate,
            initial_assessment=assessment,
            protocol=protocol,
            scout=scout,
        )
        return {
            "verdict": mutation.verdict,
            "queries": list(mutation.queries_executed[:8]),
            "rounds": mutation.rounds_completed,
            "mutations": mutation.mutations_completed,
            "assessments": list(mutation.assessments_by_round),
            "detail": "",
        }
    except ValueError as exc:
        # Fail-closed del loop (UNRESOLVED inicial u otro contrato): el
        # veredicto de la evaluación directa es el resultado honesto.
        return {
            "verdict": assessment.verdict,
            "queries": list(assessment.queries_executed[:8]),
            "rounds": 0,
            "mutations": 0,
            "assessments": [assessment.verdict],
            "detail": f"mutation-loop-fail-closed: {exc}",
        }


def _estado_antecedentes(assessment: dict[str, Any]) -> str:
    """Estado honesto de antecedentes (mandato §7). Ninguno equivale a
    novedad universal; los errores no se convierten en «sin coincidencia»."""
    verdict = assessment.get("verdict")
    detail = str(assessment.get("detail") or "")
    queries = assessment.get("queries") or []
    if verdict == "PARTIAL_PRIOR_ART":
        return "antecedente_cercano_encontrado"
    if verdict == "SURVIVED_SEARCH":
        return "sin_coincidencia_cercana_en_fuentes_consultadas"
    if "sin-mecanismo" in detail or not queries:
        return "pendiente_de_busqueda"
    if detail.startswith("mutation-loop-fail-closed") or "error" in detail:
        return "busqueda_incompleta"
    return "busqueda_incompleta"


def _fts_query(query: str) -> str:
    """Consulta FTS tolerante: OR de tokens relevantes (el MATCH exacto de
    una frase completa exige TODOS los términos y casi nunca coincide)."""
    tokens = [t for t in query.split() if len(t) >= 4][:8]
    return " OR ".join(tokens) if tokens else query


def invent(
    query: str,
    *,
    seed: int | None = None,
    rounds: int = 2,
    batch_size: int = 8,
    top: int = 3,
    offline: bool | None = None,
    methods: list[dict[str, Any]] | None = None,
    sources: list[IntelligenceSource] | None = None,
    proponer: _PROPOSER | None = None,
    store: Any | None = None,
    history_storage: Any = True,
    ficha_bloqueo: dict[str, Any] | None = None,
    adaptive: bool = False,
    outcome_store: Any | None = None,
    canon_version: str | None = None,
) -> dict[str, Any]:
    """Ejecuta el loop completo y devuelve la ficha de invención.

    ``methods``/``sources``/``proponer``/``store`` son inyectables para
    pruebas deterministas.

    ``adaptive`` (G2, opt-in, BLUEPRINT §12.4): con ``outcome_store`` presente
    la lotería pondera el sorteo por prior UCB y el selector suma el bonus de
    memoria por técnica aportante. ``adaptive=False`` (default) es byte-
    idéntico al congelado: mismo seed = mismo output, invariante intacto.

    Semilla (megaprompt §31-§33): ``seed=None`` genera una NUEVA semilla
    reproducible con ``secrets.randbits(64)`` (registra seed_source
    "generated"); una semilla explícita reproduce la exploración
    (seed_source "explicit"). Nunca timestamps ni ``hash()``.

    Historial (§35-§36): ``history_storage=True`` abre el Storage por
    defecto y aplica cooldown por decaimiento sobre pares usados (nunca
    prohibición permanente); ``False``/``None`` desactiva el historial;
    una instancia de Storage se usa tal cual. Los fallos de historial
    degradan a ejecución sin memoria (§ DV9).
    """
    if not query.strip():
        raise ValueError("query must not be blank")
    is_offline = _offline_mode(offline)
    proponer_fn = proponer or (lambda q, i, d, ev=None: _default_proponer(q, i, d, is_offline, ev))

    import secrets
    import uuid

    if seed is None:
        seed = secrets.randbits(64)
        seed_source = "generated"
    else:
        seed_source = "explicit"
    run_id = uuid.uuid4().hex  # identidad de ejecución independiente de la seed

    history = None
    first_seen: dict[tuple[str, str], str] | None = None
    if history_storage is True:
        try:
            from .storage import Storage

            history = Storage()
        except Exception:  # noqa: BLE001 — DV9: sin historial el motor funciona
            history = None
    elif history_storage:
        history = history_storage
    if history is not None:
        try:
            import hashlib as _hashlib

            ids = sorted(str(m["id"]) for m in (methods or catalog_methods()))
            fingerprint = _hashlib.sha256(",".join(ids).encode("utf-8")).hexdigest()
            first_seen = history.load_combination_first_seen(fingerprint)
        except Exception:  # noqa: BLE001 — degradación elegante (DV9)
            first_seen = None

    active_outcome_store = outcome_store if adaptive else None
    engine = LotteryEngine.from_methods(
        methods or catalog_methods(),
        seed=seed,
        outcome_store=active_outcome_store,
        outcome_profile="CRIBA",
        outcome_canon_version=canon_version,
    )
    for _ in range(rounds):
        engine.run_round(mode="stratified", batch_size=batch_size, query=query)
    domain = engine.draw_domain()
    # Selección finalista diversity-aware (megaprompt §24-§28): pool de alta
    # calidad → selector MMR → finalistas. get_top_ideas sigue existiendo
    # para sus otros consumidores; el flujo de invención ya no depende solo
    # del top-N por score.
    from .diversity_selector import select_finalists

    pool = engine.get_top_ideas(max(top * 6, 12))
    top_ideas, selection_report = select_finalists(
        pool,
        top,
        historical_first_seen=first_seen,
        outcome_store=active_outcome_store,
        outcome_profile="CRIBA",
        outcome_canon_version=canon_version,
    )
    if history is not None and selection_report.get("pool_size"):
        try:  # registrar los pares de ESTA ejecución (first_seen=ahora)
            history.save_lottery_combinations(
                engine.catalog_fingerprint,
                sorted(engine.used_combos),
                run_id=run_id,
                mode="stratified",
                seed=seed,
            )
        except Exception:  # noqa: BLE001 — DV9: persistencia opcional
            pass

    # Offline: sin fuentes de red. El transporte común también bloquea
    # cualquier intento de conexión que escape (defensa en profundidad).
    if sources is not None:
        active_sources = sources
    elif is_offline:
        active_sources = []
    else:
        active_sources = build_sources(default_context(offline=is_offline))
    candidate_prefix = _stable_run_id(query, seed)  # reproducible por seed

    # Evidencia local para el intérprete (FTS del almacén): se RECUPERA UNA
    # VEZ y se ENTREGA a la llamada de interpretación — no solo se guarda.
    local_evidence: list[dict[str, Any]] = []
    if store is not None:
        try:
            local_evidence = [
                {"title": d.get("title", ""), "abstract": (d.get("abstract") or "")[:300],
                 "url": d.get("url", "")}
                for d in (store.search_documents(_fts_query(query), limit=3) or [])
            ]
        except Exception:  # noqa: BLE001 — la evidencia nunca rompe el loop
            local_evidence = []

    # Lecciones de dossiers previos (circuito de aprendizaje, astra!.txt §5):
    # un resultado observado vuelve a la búsqueda como evidencia trazable.
    lecciones: list[str] = []
    if ficha_bloqueo:
        try:
            from .supra_dossier import lecciones_previas
            lecciones = lecciones_previas(query)
        except Exception:  # noqa: BLE001 — el aprendizaje nunca rompe el loop
            lecciones = []

    def _desarrollar(idea: dict[str, Any], index: int) -> dict[str, Any]:
        """Propuesta → crítica → antecedentes para un candidato del pool."""
        idea_enviada = idea
        if ficha_bloqueo:
            idea_enviada = {**idea, "bloqueo": {
                **ficha_bloqueo, "lecciones_previas": lecciones}}
        # 1) Propuesta: aplicar el cruce al problema (con evidencia) ANTES de
        #    buscar antecedentes.
        proposal = proponer_fn(query, idea_enviada, domain, local_evidence)
        if proposal.get("estado") != "PROPUESTA" or not str(proposal.get("mecanismo", "")).strip():
            if proposal.get("estado") == "PROPUESTA":
                proposal = _pending_proposal("PROPUESTA sin mecanismo")
        candidate = InventionCandidate(
            candidate_id=f"{candidate_prefix}-{index + 1:02d}",
            title=str(idea.get("title", ""))[:120],
            description=str(idea.get("description", ""))[:400],
            mechanism=str(proposal.get("mecanismo", "")),
            origin="NEW_IIE",
        )
        # 2) Crítica automática sobre la propuesta (no validación independiente).
        judged = _judge(query, {**idea, "mecanismo": candidate.mechanism}, is_offline)
        # 3) Antecedentes del mecanismo (nunca del título).
        assessment = _assess_candidate(candidate, active_sources)
        return {
            "candidate_id": candidate.candidate_id,
            "run_id": run_id,  # cada entry arrastra su ejecución (trazabilidad dossier)
            "title": candidate.title,
            "score": idea.get("score", 0.0),
            "score_kind": "heuristica_local",
            "classes": [idea.get("class1", ""), idea.get("class2", "")],
            "methods": [idea.get("method1", ""), idea.get("method2", "")],
            "method_ids": [idea.get("method1_id", ""), idea.get("method2_id", "")],
            "hipotesis": proposal.get("hipotesis", ""),
            "mecanismo": candidate.mechanism,
            "estado_interpretacion": proposal.get("estado", "PENDIENTE_INTERPRETACION"),
            "aportacion_por_tecnica": list(proposal.get("aportacion_por_tecnica", [])),
            "supuestos": list(proposal.get("supuestos", [])),
            "prueba_concreta": proposal.get("prueba_concreta", ""),
            "ruta_desbloqueo": proposal.get("ruta_desbloqueo", ""),
            "interpretacion_error": proposal.get("error", ""),
            "evidencia_local_usada": local_evidence,
            "judge": judged,
            "prior_art": assessment,
            "estado_antecedentes": _estado_antecedentes(assessment),
        }

    entries: list[dict[str, Any]] = [
        _desarrollar(idea, i) for i, idea in enumerate(top_ideas)
    ]

    # 4) Revisión post-interpretación (mandato §22: una revisión por candidato;
    # megaprompt §28): el selector eligió finalistas sobre estructura/técnicas
    # porque interpretar TODO el pool no cabe en presupuesto. Una vez
    # interpretados los mecanismos, si dos son la MISMA idea, el redundante
    # se sustituye por el siguiente candidato del pool. Cada intento
    # (aceptado o rechazado) se registra con identidad y llamadas consumidas;
    # UNKNOWN no descarta automáticamente (mandato de verificación §2).
    from .diversity_selector import compare_mechanisms

    pool_rest = [c for c in pool if all(c is not t for t in top_ideas)]
    intentos: list[dict[str, Any]] = []
    model_calls = len(entries)  # cada finalista interpretado = 1 llamada
    for idx, entry in enumerate(entries):
        if entry["estado_interpretacion"] != "PROPUESTA" or not entry["mecanismo"]:
            continue
        duplicated_with = next(
            (other["mecanismo"] for j, other in enumerate(entries)
             if j != idx and other["estado_interpretacion"] == "PROPUESTA"
             and other["mecanismo"]
             and compare_mechanisms(entry["mecanismo"], other["mecanismo"]) == "DUPLICATE"),
            None,
        )
        if duplicated_with is None:
            continue
        if not pool_rest:
            intentos.append({
                "reemplazado_id": entry["candidate_id"],
                "reemplazado_titulo": entry["title"],
                "motivo": "mecanismo duplicado; pool sin sustituto disponible",
                "resultado": "rechazado",
                "sustituto_id": None,
                "llamadas_modelo": 0,
            })
            entry["mecanismo_duplicado_con"] = "otro finalista (sin sustituto en el pool)"
            continue
        sustituto_idea = pool_rest.pop(0)
        sustituto_entry = _desarrollar(sustituto_idea, len(entries) + len(intentos))
        model_calls += 1  # el sustituto consume su propia llamada de propuesta
        distinto_de_todos = all(
            compare_mechanisms(sustituto_entry["mecanismo"], other["mecanismo"]) != "DUPLICATE"
            for j, other in enumerate(entries)
            if j != idx and other["estado_interpretacion"] == "PROPUESTA"
            and other["mecanismo"]
        )
        if (sustituto_entry["estado_interpretacion"] == "PROPUESTA"
                and sustituto_entry["mecanismo"] and distinto_de_todos):
            intentos.append({
                "reemplazado_id": entry["candidate_id"],
                "reemplazado_titulo": entry["title"],
                "motivo": "mecanismo interpretado duplicado con otro finalista",
                "resultado": "aceptado",
                "sustituto_id": sustituto_entry["candidate_id"],
                "sustituto_titulo": sustituto_entry["title"],
                "llamadas_modelo": 1,
            })
            entries[idx] = sustituto_entry
        else:
            motivo = "sustituto sin propuesta válida o aún duplicado"
            if sustituto_entry["estado_interpretacion"] == "PROPUESTA" and sustituto_entry["mecanismo"]:
                motivo = "sustituto aún duplicado o incomparable (UNKNOWN no descarta)"
            intentos.append({
                "reemplazado_id": entry["candidate_id"],
                "reemplazado_titulo": entry["title"],
                "motivo": motivo,
                "resultado": "rechazado",
                "sustituto_id": sustituto_entry["candidate_id"],
                "sustituto_titulo": sustituto_entry["title"],
                "llamadas_modelo": 1,
            })
            entry["mecanismo_duplicado_con"] = "otro finalista (sustitución rechazada)"
    if intentos:
        selection_report["revision_post_interpretacion"] = {
            "intentos": intentos,
            "llamadas_revision": len(intentos),
            "llamadas_modelo_total": model_calls,
            "sustituciones_aceptadas": sum(1 for i in intentos if i["resultado"] == "aceptado"),
        }

    sheet = {
        "query": query,
        "seed": seed,
        "seed_source": seed_source,
        "run_id": run_id,
        "mode": "stratified",
        "rounds": rounds,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "domain_coupling": {
            "id": domain.get("id") if domain else None,
            "title": domain.get("title") if domain else None,
            "usado_en_interpretacion": True,
        },
        "seleccion_finalista": selection_report,
        "ficha_bloqueo": dict(ficha_bloqueo) if ficha_bloqueo else None,
        "entries": entries,
        "totals": {
            "ideas": len(engine.all_ideas),
            "pending_interpretation": sum(
                1 for e in entries if e["estado_interpretacion"] != "PROPUESTA"
            ),
            "unresolved": sum(1 for e in entries if e["prior_art"]["verdict"] == "UNRESOLVED"),
            "partial_prior_art": sum(1 for e in entries if e["prior_art"]["verdict"] == "PARTIAL_PRIOR_ART"),
            "survived_search": sum(1 for e in entries if e["prior_art"]["verdict"] == "SURVIVED_SEARCH"),
        },
    }
    return sheet


def _entry_technique_ids(entry: dict[str, Any]) -> list[str]:
    """IDs T0xx que aportaron a un candidato (aportacion_por_tecnica).

    Forma tolerante: acepta dicts con 'tecnica'/'id'/'technique_id' o strings
    planos. Devuelve IDs únicos normalizados a mayúsculas; nunca inventa IDs.
    """
    out: list[str] = []
    for item in entry.get("aportacion_por_tecnica") or []:
        tid = ""
        if isinstance(item, dict):
            tid = str(item.get("tecnica") or item.get("id") or item.get("technique_id") or "")
        elif isinstance(item, str):
            tid = item
        tid = tid.strip().upper()
        if tid.startswith("T") and tid not in out:
            out.append(tid)
    return out


def record_outcomes(
    sheet: dict[str, Any],
    store: Any,
    *,
    profile: str = "CRIBA",
    canon_version: str = "",
) -> int:
    """Escribe outcomes técnica→resultado en el store (BLUEPRINT §4.4).

    Por candidato y por técnica que aportó: registra el canal verdict (prior-art)
    y el canal judge (score de la crítica) ETIQUETADOS por separado (§12.2.3) —
    nunca mezclados. También registra el outcome agregado por clase de pensamiento
    (familia de la lotería) para el back-off jerárquico (§12.2.1).

    Nunca rompe el loop: cualquier fallo de escritura se ignora (la memoria es
    aprendizaje, no requisito del resultado). Devuelve el nº de registros.
    """
    from .intelligence.outcome_store import CHANNEL_JUDGE, CHANNEL_VERDICT

    written = 0
    for entry in sheet.get("entries", []):
        verdict = entry.get("prior_art", {}).get("verdict", "UNRESOLVED")
        if verdict not in ("SURVIVED_SEARCH", "PARTIAL_PRIOR_ART", "UNRESOLVED"):
            verdict = "UNRESOLVED"
        judge_score = entry.get("judge", {}).get("score")
        run_id = entry.get("run_id", sheet.get("run_id", ""))

        # P4 (atribución): el resultado se vincula al candidato y a los MÉTODOS
        # REALMENTE sorteados (method_ids), cada uno con SU clase de pensamiento
        # — no a la primera clase del cruce ni solo a los IDs T-canon del
        # intérprete (que offline quedan vacíos y rompían el circuito). Si el
        # intérprete aporta además IDs T-canon, también se registran con la
        # clase del primer método (aproximación documentada: la clase de un
        # T-canon no es recuperable sin el intérprete).
        method_ids = [m for m in (entry.get("method_ids") or []) if m]
        classes = [c for c in (entry.get("classes") or []) if c]
        pares = list(zip(method_ids, classes)) if method_ids else []
        # técnica T-canon aportada por el intérprete (si la hay) -> clase[0]
        t_ids = _entry_technique_ids(entry)
        familia_t = classes[0] if classes else "unknown"

        def _escribe(tid: str, familia: str) -> None:
            nonlocal written
            try:
                store.record(profile=profile, family=familia, technique_id=tid,
                             channel=CHANNEL_VERDICT, outcome=verdict,
                             canon_version=canon_version, run_id=run_id)
                written += 1
                if isinstance(judge_score, (int, float)):
                    store.record(profile=profile, family=familia, technique_id=tid,
                                 channel=CHANNEL_JUDGE, outcome="score",
                                 value=float(judge_score),
                                 canon_version=canon_version, run_id=run_id)
                    written += 1
            except Exception:  # noqa: BLE001 — la memoria nunca rompe el loop
                return

        # 1) métodos sorteados: cada uno con SU clase (atribución correcta).
        for mid, clase in pares:
            _escribe(mid, clase)
        # 2) IDs T-canon del intérprete (circuito G1 original), si existen.
        for tid in t_ids:
            _escribe(tid, familia_t)
        # 3) agregados de familia para back-off: uno por CLASE presente (no solo
        #    la primera), para que el back-off jerárquico sea coherente con la
        #    atribución por clase.
        for clase in dict.fromkeys(classes):
            try:
                store.record_family_outcome(profile=profile, family=clase,
                                            channel=CHANNEL_VERDICT, outcome=verdict,
                                            canon_version=canon_version, run_id=run_id)
                written += 1
            except Exception:  # noqa: BLE001
                pass
    return written


def append_ledger(sheet: dict[str, Any], ledger_dir: Path | None = None) -> Path:
    """Añade el registro completo al ledger append-only (JSONL)."""
    directory = ledger_dir or _ledger_dir()
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "verdicts.jsonl"
    record = {
        "generated_at": sheet["generated_at"],
        "query": sheet["query"],
        "seed": sheet["seed"],
        "seed_source": sheet["seed_source"],
        "run_id": sheet["run_id"],
        "mode": sheet["mode"],
        "rounds": sheet["rounds"],
        "domain_coupling": sheet["domain_coupling"],
        "totals": sheet["totals"],
        "entries": [
            {
                "candidate_id": e["candidate_id"],
                "run_id": e["run_id"],
                "title": e["title"],
                "estado_interpretacion": e["estado_interpretacion"],
                "mecanismo": e["mecanismo"],
                "score": e["score"],
                "score_kind": e["score_kind"],
                "classes": e["classes"],
                "methods": e["methods"],
                "technique_ids": _entry_technique_ids(e),  # §4.1: qué T0xx aportó
                "hipotesis": e["hipotesis"],
                "prueba_concreta": e["prueba_concreta"],
                "ruta_desbloqueo": e["ruta_desbloqueo"],
                "supuestos": e["supuestos"],
                "estado_antecedentes": e["estado_antecedentes"],
                "evidencia_local_usada": e["evidencia_local_usada"],
                "verdict": e["prior_art"]["verdict"],
                "queries": e["prior_art"]["queries"],
                "detail": e["prior_art"]["detail"],
            }
            for e in sheet["entries"]
        ],
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return path


def print_sheet(sheet: dict[str, Any]) -> None:
    """Imprime la ficha de invención en consola."""
    line = "=" * 64
    print(line)
    print(f"INVENTAR · {sheet['query'][:50]} · seed={sheet['seed']} · {sheet['mode']}")
    print(line)
    domain = sheet.get("domain_coupling") or {}
    if domain.get("title"):
        print(f"Dominio de acoplamiento: {domain['title']}")
    for i, entry in enumerate(sheet["entries"], 1):
        prior = entry["prior_art"]
        judge = entry["judge"]
        print()
        print(f"{i}. {entry['title']}")
        print(f"   clases: {' x '.join(c or '?' for c in entry['classes'])} | score {entry['score']} ({entry['score_kind']})")
        print(f"   interpretación: {entry['estado_interpretacion']}")
        if entry["hipotesis"]:
            print(f"   hipótesis: {entry['hipotesis'][:200]}")
            print(f"   mecanismo: {entry['mecanismo'][:200]}")
            print(f"   prueba: {entry['prueba_concreta'][:200]}")
        print(f"   juez: {judge.get('veredicto', '?')} ({judge.get('score', 0)})")
        print(f"   prior-art: {prior['verdict']} (rondas={prior['rounds']}, mutaciones={prior['mutations']})")
    totals = sheet["totals"]
    print()
    print(line)
    print(
        f"Ideas: {totals['ideas']} | pendientes: {totals['pending_interpretation']} | "
        f"UNRESOLVED: {totals['unresolved']} | "
        f"PARTIAL: {totals['partial_prior_art']} | SURVIVED: {totals['survived_search']}"
    )
    print(line)
