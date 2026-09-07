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

    scout = CrossDomainScout(sources)
    skeptic = PriorArtSkeptic()
    results: dict[str, SourceQueryResult] = scout.cross_search(variant, limit_per_source=3)
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
) -> dict[str, Any]:
    """Ejecuta el loop completo y devuelve la ficha de invención.

    ``methods``/``sources``/``proponer``/``store`` son inyectables para
    pruebas deterministas.

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

    engine = LotteryEngine.from_methods(methods or catalog_methods(), seed=seed)
    for _ in range(rounds):
        engine.run_round(mode="stratified", batch_size=batch_size, query=query)
    domain = engine.draw_domain()
    # Selección finalista diversity-aware (megaprompt §24-§28): pool de alta
    # calidad → selector MMR → finalistas. get_top_ideas sigue existiendo
    # para sus otros consumidores; el flujo de invención ya no depende solo
    # del top-N por score.
    from .diversity_selector import select_finalists

    pool = engine.get_top_ideas(max(top * 6, 12))
    top_ideas, selection_report = select_finalists(pool, top, historical_first_seen=first_seen)
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

    def _desarrollar(idea: dict[str, Any], index: int) -> dict[str, Any]:
        """Propuesta → crítica → antecedentes para un candidato del pool."""
        # 1) Propuesta: aplicar el cruce al problema (con evidencia) ANTES de
        #    buscar antecedentes.
        proposal = proponer_fn(query, idea, domain, local_evidence)
        if proposal.get("estado") != "PROPUESTA" or not str(proposal.get("mecanismo", "")).strip():
            if proposal.get("estado") == "PROPUESTA":
                proposal = _pending_proposal("PROPUESTA sin mecanismo")
        candidate = InventionCandidate(
            candidate_id=f"{candidate_prefix}-{index + 1:02d}",
            title=str(idea.get("title", ""))[:120],
            description=str(idea.get("description", ""))[:400],
            mechanism=str(proposal.get("mecanismo", ""))[:200],
            origin="NEW_IIE",
        )
        # 2) Crítica automática sobre la propuesta (no validación independiente).
        judged = _judge(query, {**idea, "mecanismo": candidate.mechanism}, is_offline)
        # 3) Antecedentes del mecanismo (nunca del título).
        assessment = _assess_candidate(candidate, active_sources)
        return {
            "candidate_id": candidate.candidate_id,
            "title": candidate.title,
            "score": idea.get("score", 0.0),
            "score_kind": "heuristica_local",
            "classes": [idea.get("class1", ""), idea.get("class2", "")],
            "methods": [idea.get("method1", ""), idea.get("method2", "")],
            "hipotesis": proposal.get("hipotesis", ""),
            "mecanismo": candidate.mechanism,
            "estado_interpretacion": proposal.get("estado", "PENDIENTE_INTERPRETACION"),
            "aportacion_por_tecnica": list(proposal.get("aportacion_por_tecnica", [])),
            "supuestos": list(proposal.get("supuestos", [])),
            "prueba_concreta": proposal.get("prueba_concreta", ""),
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
    # interpretados los mecanismos, si dos son esencialmente la misma idea,
    # el redundante se sustituye por el siguiente candidato del pool.
    from .diversity_selector import same_idea_mechanism

    pool_rest = [c for c in pool if all(c is not t for t in top_ideas)]
    revision_log: list[dict[str, Any]] = []
    for idx, entry in enumerate(entries):
        if entry["estado_interpretacion"] != "PROPUESTA" or not entry["mecanismo"]:
            continue
        # Comparar contra los mecanismos de los OTROS finalistas por índice
        # (la identidad de cadenas iguales no distingue entry propia/ajena).
        duplicated_with = next(
            (other["mecanismo"] for j, other in enumerate(entries)
             if j != idx and other["estado_interpretacion"] == "PROPUESTA"
             and other["mecanismo"]
             and same_idea_mechanism(entry["mecanismo"], other["mecanismo"])),
            None,
        )
        if duplicated_with is None or not pool_rest:
            continue
        substitute_idea = pool_rest.pop(0)
        substitute_entry = _desarrollar(substitute_idea, len(entries) + len(revision_log))
        substitute_ok = (
            substitute_entry["estado_interpretacion"] == "PROPUESTA"
            and substitute_entry["mecanismo"]
            and not any(
                same_idea_mechanism(substitute_entry["mecanismo"], other["mecanismo"])
                for j, other in enumerate(entries)
                if j != idx and other["estado_interpretacion"] == "PROPUESTA"
                and other["mecanismo"]
            )
        )
        if substitute_ok:
            revision_log.append({
                "reemplazado": entry["candidate_id"],
                "motivo": "mecanismo interpretado duplicado con otro finalista",
                "sustituto": substitute_entry["candidate_id"],
            })
            entries[idx] = substitute_entry
        else:
            entry["mecanismo_duplicado_con"] = "otro finalista (sin sustituto distinto en el pool)"
    if revision_log or any("mecanismo_duplicado_con" in e for e in entries):
        selection_report["revision_post_interpretacion"] = {
            "sustituciones": revision_log,
            "sin_sustituto": [e["candidate_id"] for e in entries
                              if "mecanismo_duplicado_con" in e],
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
                "title": e["title"],
                "estado_interpretacion": e["estado_interpretacion"],
                "mecanismo": e["mecanismo"],
                "score": e["score"],
                "score_kind": e["score_kind"],
                "methods": e["methods"],
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
