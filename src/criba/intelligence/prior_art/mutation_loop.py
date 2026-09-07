"""P10-T10: bounded mutation/re-search loop over a PriorArtAssessment.

El loop consume la salida de P10-T09 (PriorArtAssessment) y re-busca con
variantes mutadas del mecanismo-candidato. No infiere PROVEN_NEW ni novedad;
reclasifica UNRESOLVED como fail-closed. Reusa el motor determinista de
CrossDomainScout -> PriorArtSkeptic -> PriorArtVerdictEngine.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from ..contracts import (
    InventionCandidate,
    PriorArtAssessment,
    PriorArtMatch,
    QueryVariant,
)
from ..enums import PriorArtVerdict
from .protocol import AdversarialSearchProtocol
from .scouts import CrossDomainScout
from .skeptic import PriorArtSkeptic
from .verdict import PriorArtVerdictEngine


@dataclass(frozen=True)
class MutationResult:
    """Resultado final del loop de mutación/re-busqueda."""

    verdict: str
    rounds_completed: int
    mutations_completed: int
    queries_executed: tuple[str, ...]
    assessments_by_round: tuple[str, ...]


def _mutate_query(candidate: InventionCandidate, round_idx: int) -> QueryVariant:
    """Produce un QueryVariant mutado del mecanismo del candidato.

    Es determinista y dependiente del round para que las corridas sean
    reproducibles sin proveedor ni red.
    """
    base = candidate.mechanism or candidate.title or candidate.description
    if not base.strip():
        base = candidate.candidate_id
    mutated_text = base.strip()
    if round_idx == 0:
        return QueryVariant(text=mutated_text, origin="original")
    suffixes = (" alternative", " improvement", " variant", " approach", " method")
    suffix = suffixes[(round_idx - 1) % len(suffixes)]
    return QueryVariant(text=mutated_text + suffix, origin="mutation")


def _execute_round(
    candidate: InventionCandidate,
    scout: CrossDomainScout,
    protocol: AdversarialSearchProtocol,
    skeptic: PriorArtSkeptic,
    verdict_engine: PriorArtVerdictEngine,
    variant: QueryVariant,
    prior_matches: Sequence[PriorArtMatch],
) -> PriorArtAssessment:
    """Ejecuta un round de busqueda + esceptico + veredicto sobre un variante."""
    results = scout.cross_search(variant, limit_per_source=5)
    report = skeptic.review(candidate, results)
    return verdict_engine.assess(candidate, results, report, matches=list(prior_matches))


def run_prior_art_mutation_loop(
    *,
    candidate: InventionCandidate,
    initial_assessment: PriorArtAssessment,
    protocol: AdversarialSearchProtocol,
    scout: CrossDomainScout,
) -> MutationResult:
    """Ejecuta el loop de mutación/re-busqueda de P10-T10.

    Contract (desde test_prior_art_mutation_loop.py):

    1. Si el assessment inicial es UNRESOLVED, falla cerrado con ValueError
       (match "UNRESOLVED"). No se muta ni se re-busca.
    2. Si el assessment es PARTIAL_PRIOR_ART o SURVIVED_SEARCH, se permite
       al menos un round de búsqueda, respetando max_prior_art_rounds y
       max_mutations_per_candidate del protocolo.
    3. El veredicto final nunca es PROVEN_NEW; siempre es UNRESOLVED,
       PARTIAL_PRIOR_ART o SURVIVED_SEARCH.
    4. El resultado conserva rounds_completed y mutations_completed acotados.

    Precedente: ADR P10-T09 prohíbe inferir PROVEN_NEW. El motor de veredicto
    P10-T09 falla cerrado sobre gaps; el loop solo re-busca variantes mutadas
    cuando la cobertura es suficiente (sin limitaciones).
    """
    if initial_assessment.verdict == PriorArtVerdict.UNRESOLVED.value:
        raise ValueError(
            f"P10-T10 refuses to mutate from UNRESOLVED assessment "
            f"(candidate={candidate.candidate_id}): fail-closed, no mutation "
            f"until evidence coverage is sufficient."
        )

    if initial_assessment.verdict not in (
        PriorArtVerdict.PARTIAL_PRIOR_ART.value,
        PriorArtVerdict.SURVIVED_SEARCH.value,
    ):
        raise ValueError(
            f"P10-T10 does not accept verdict '{initial_assessment.verdict}'; "
            f"only PARTIAL_PRIOR_ART or SURVIVED_SEARCH may be re-searched."
        )

    skeptic = PriorArtSkeptic()
    verdict_engine = PriorArtVerdictEngine()

    rounds_completed = 0
    mutations_completed = 0
    all_queries: list[str] = list(initial_assessment.queries_executed)
    assessments: list[str] = [initial_assessment.verdict]
    current_matches = tuple(initial_assessment.matches)
    current_verdict = initial_assessment.verdict

    while protocol.can_execute(
        rounds_completed=rounds_completed,
        mutations_completed=mutations_completed,
    ):
        should_mutate = (
            protocol.can_mutate(mutations_completed=mutations_completed)
            and current_verdict == PriorArtVerdict.SURVIVED_SEARCH.value
        )

        if should_mutate:
            mutations_completed += 1

        round_idx = mutations_completed
        variant = _mutate_query(candidate, round_idx)
        all_queries.append(variant.text)

        assessment = _execute_round(
            candidate, scout, protocol, skeptic, verdict_engine,
            variant, current_matches,
        )

        rounds_completed += 1
        current_verdict = assessment.verdict
        assessments.append(current_verdict)
        current_matches = tuple(assessment.matches)

        all_queries.extend(assessment.queries_executed)

        if current_verdict == PriorArtVerdict.UNRESOLVED.value:
            break

    return MutationResult(
        verdict=current_verdict,
        rounds_completed=rounds_completed,
        mutations_completed=mutations_completed,
        queries_executed=tuple(dict.fromkeys(all_queries)),
        assessments_by_round=tuple(assessments),
    )
