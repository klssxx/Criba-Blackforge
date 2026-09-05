"""``criba inventar``: el loop de innovación completo en un comando.

Cadena (siempre 0€, reproducible por semilla, nunca afirma novedad):

1. **Lotería estratificada** — divergencia determinista por clases de
   pensamiento (perspectiva/generación/ruptura/escape) con banco de dominio
   como segundo dado opcional.
2. **Juez** — ``LocalInterprete`` (pool free de Nous con NOUS_API_KEY; sin
   clave usa scoring semántico offline, sin red).
3. **Prior-art adversarial acotado** — lattice determinista → par gratuito
   (Wikipedia + Google Patents) → skeptic → verdict → mutation loop
   fail-closed. Veredictos posibles: ``UNRESOLVED`` / ``PARTIAL_PRIOR_ART`` /
   ``SURVIVED_SEARCH``.
4. **Ficha + ledger** — salida legible y ``invention_ledger/verdicts.jsonl``
   append-only (trazabilidad de cada veredicto emitido).
"""
from __future__ import annotations

import json
import os
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

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


def _ledger_dir() -> Path:
    base = Path(os.environ.get("LOCALAPPDATA") or Path.home())
    return base / "CRIBA-Blackforge" / "invention_ledger"


def _offline_mode(offline: bool | None) -> bool:
    if offline is not None:
        return offline
    return os.environ.get("CRIBA_INVENTAR_OFFLINE", "") == "1"


def _judge(query: str, idea: dict[str, Any], offline: bool) -> dict[str, Any]:
    """Interpretación por el juez; falla cerrado a PENDIENTE sin red."""
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
    """Lattice → scout (≥2 dominios) → skeptic → verdict → mutation loop."""
    protocol = AdversarialSearchProtocol(
        candidate_id=candidate.candidate_id,
        max_prior_art_rounds=2,
        max_mutations_per_candidate=1,
    )
    lattice = build_query_lattice(candidate.mechanism or candidate.title, max_variants=4)
    variant = lattice[0] if lattice else None
    scout = CrossDomainScout(sources)
    skeptic = PriorArtSkeptic()
    verdict_engine = PriorArtVerdictEngine()

    if variant is None:
        return {"verdict": "UNRESOLVED", "queries": [], "rounds": 0, "mutations": 0, "detail": "empty lattice"}

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


def invent(
    query: str,
    *,
    seed: int = 42,
    rounds: int = 2,
    batch_size: int = 8,
    top: int = 3,
    offline: bool | None = None,
    methods: list[dict[str, Any]] | None = None,
    sources: list[IntelligenceSource] | None = None,
) -> dict[str, Any]:
    """Ejecuta el loop completo y devuelve la ficha de invención.

    ``methods``/``sources`` son inyectables para pruebas deterministas.
    """
    if not query.strip():
        raise ValueError("query must not be blank")
    is_offline = _offline_mode(offline)

    engine = LotteryEngine.from_methods(methods or catalog_methods(), seed=seed)
    for _ in range(rounds):
        engine.run_round(mode="stratified", batch_size=batch_size, query=query)
    domain = engine.draw_domain()
    top_ideas = engine.get_top_ideas(top)

    active_sources = sources if sources is not None else build_sources(default_context())
    interpreter_id = f"invent-{seed}-{abs(hash(query)) % 10_000:04d}"
    rng = random.Random(seed)

    entries: list[dict[str, Any]] = []
    for idea in top_ideas:
        candidate = InventionCandidate(
            candidate_id=f"{interpreter_id}-{len(entries) + 1:02d}",
            title=str(idea.get("title", ""))[:120],
            description=str(idea.get("description", ""))[:400],
            mechanism=str(idea.get("title", ""))[:200],
            origin="NEW_IIE",
        )
        judged = _judge(query, idea, is_offline)
        assessment = _assess_candidate(candidate, active_sources)
        entries.append(
            {
                "candidate_id": candidate.candidate_id,
                "title": candidate.title,
                "score": idea.get("score", 0.0),
                "quality": idea.get("quality", ""),
                "classes": [idea.get("class1", ""), idea.get("class2", "")],
                "methods": [idea.get("method1", ""), idea.get("method2", "")],
                "judge": judged,
                "prior_art": assessment,
            }
        )
        rng.random()  # consume para mantener el ritmo determinista del loop

    sheet = {
        "query": query,
        "seed": seed,
        "mode": "stratified",
        "rounds": rounds,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "domain_coupling": {
            "id": domain.get("id") if domain else None,
            "title": domain.get("title") if domain else None,
        },
        "entries": entries,
        "totals": {
            "ideas": len(engine.all_ideas),
            "unresolved": sum(1 for e in entries if e["prior_art"]["verdict"] == "UNRESOLVED"),
            "partial_prior_art": sum(1 for e in entries if e["prior_art"]["verdict"] == "PARTIAL_PRIOR_ART"),
            "survived_search": sum(1 for e in entries if e["prior_art"]["verdict"] == "SURVIVED_SEARCH"),
        },
    }
    return sheet


def append_ledger(sheet: dict[str, Any], ledger_dir: Path | None = None) -> Path:
    """Añade la ficha al ledger append-only (JSONL)."""
    directory = ledger_dir or _ledger_dir()
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "verdicts.jsonl"
    record = {
        "generated_at": sheet["generated_at"],
        "query": sheet["query"],
        "seed": sheet["seed"],
        "totals": sheet["totals"],
        "entries": [
            {"candidate_id": e["candidate_id"], "verdict": e["prior_art"]["verdict"]}
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
        print(f"   clases: {' x '.join(c or '?' for c in entry['classes'])} | score {entry['score']}")
        print(f"   juez: {judge.get('veredicto', '?')} ({judge.get('score', 0)})")
        print(f"   prior-art: {prior['verdict']} (rondas={prior['rounds']}, mutaciones={prior['mutations']})")
    totals = sheet["totals"]
    print()
    print(line)
    print(
        f"Ideas: {totals['ideas']} | UNRESOLVED: {totals['unresolved']} | "
        f"PARTIAL: {totals['partial_prior_art']} | SURVIVED: {totals['survived_search']}"
    )
    print(line)
