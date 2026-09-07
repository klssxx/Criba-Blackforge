"""Tests del selector finalista diversity-aware (megaprompt §29, §63, §66).

Se testea COMPORTAMIENTO, no valores de pesos: ante un candidato casi
duplicado ligeramente mejor puntuado y otro estructuralmente distinto algo
peor, el distinto debe ganar (DV1/DV2/DV3/DV12).
"""
from __future__ import annotations

import pytest

from benchmarks.diversity_fixtures import ANTI_CONVERGENCE_POOL, PAIR_REUSE_POOL
from criba.diversity_selector import select_finalists
from criba.similarity import classify


def _by_id(pool, idea_id):
    return next(c for c in pool if c["idea_id"] == idea_id)


def test_dv1_anti_convergence_prefers_distinct_candidate() -> None:
    """A 0.90, A2 0.89 casi-duplicado, B 0.84 distinto → finalistas A+B, no A+A2."""
    finalists, report = select_finalists(ANTI_CONVERGENCE_POOL, 3)
    ids = [c["idea_id"] for c in finalists]
    assert "A" in ids, "el mejor válido entra primero"
    assert "A2" not in ids or "B" in ids, "un casi-duplicado no puede desplazar a B"
    assert "B" in ids, "el candidato estructuralmente distinto debe ser finalista"
    assert report["status"] == "OK"


def test_dv2_probable_duplicate_excluded_when_alternatives_exist() -> None:
    finalists, _ = select_finalists(ANTI_CONVERGENCE_POOL, 3)
    ids = {c["idea_id"] for c in finalists}
    for a, b in (("A", "A2"), ("A", "A3"), ("A2", "A3")):
        if a in ids and b in ids:
            verdict = classify(_by_id(ANTI_CONVERGENCE_POOL, a)["genome"],
                               _by_id(ANTI_CONVERGENCE_POOL, b)["genome"])["verdict"]
            assert verdict != "probable_duplicate", (
                f"{a} y {b} son probable_duplicate y no pueden coexistir con alternativas"
            )


def test_dv3_close_variant_penalized_but_not_banned_when_pool_short() -> None:
    """R1/R2 son close_variant: con N=4 el pool obliga a aceptar uno; la
    penalización debe preferir R3/R4 antes que acumular variantes cercanas."""
    finalists, _ = select_finalists(PAIR_REUSE_POOL, 4)
    ids = [c["idea_id"] for c in finalists]
    assert "R3" in ids and "R4" in ids, "los distintos deben entrar antes que la 2ª variante"
    assert ids.index("R3") < ids.index("R2")


def test_dv4_diversity_constrained_honest_when_pool_short() -> None:
    pool = ANTI_CONVERGENCE_POOL[:1]  # un solo candidato válido
    finalists, report = select_finalists(pool, 3)
    assert len(finalists) == 1
    assert report["status"] == "DIVERSITY_CONSTRAINED"


def test_dv12_quality_floor_blocks_novelty_without_relevance() -> None:
    """Un candidato muy diverso pero por debajo del suelo NO entra."""
    pool = [
        {"idea_id": "GOOD", "score": 0.90, "family": "f1", "methods": ["T1"],
         "genome": {"mechanism": ["m1"], "trust_model": ["t1"], "topology": ["x1"],
                    "actor": ["a1"], "time_model": ["tt1"]}},
        {"idea_id": "RARE_BUT_BAD", "score": 0.50, "family": "f999", "methods": ["T99"],
         "genome": {"mechanism": ["m-raro"], "trust_model": ["t99"], "topology": ["x99"],
                    "actor": ["a99"], "time_model": ["tt99"]}},
    ]
    finalists, report = select_finalists(pool, 2)
    assert [c["idea_id"] for c in finalists] == ["GOOD"]
    assert "RARE_BUT_BAD" in report["discarded_by_floor"]


def test_candidates_without_genome_do_not_crash_selector() -> None:
    """Genoma ausente → distancia neutra; el selector funciona por score."""
    pool = [
        {"idea_id": "S1", "score": 0.9, "family": "f1", "methods": ["T1"]},
        {"idea_id": "S2", "score": 0.8, "family": "f2", "methods": ["T2"]},
    ]
    finalists, report = select_finalists(pool, 2)
    assert [c["idea_id"] for c in finalists] == ["S1", "S2"]
    assert report["status"] == "OK"


def test_selection_is_deterministic() -> None:
    a, _ = select_finalists(ANTI_CONVERGENCE_POOL, 3)
    b, _ = select_finalists(ANTI_CONVERGENCE_POOL, 3)
    assert [c["idea_id"] for c in a] == [c["idea_id"] for c in b]


# ---------------------------------------------------------------------------
# Clasificación semántica de mecanismos (mandato de verificación §2)
# ---------------------------------------------------------------------------

from criba.diversity_selector import NEUTRAL_DISTANCE, _structural_distance, same_idea_mechanism

MEC = "limitar cada autorizacion a un unico uso por operacion"


def test_parafraasis_del_mismo_mecanismo_se_detecta() -> None:
    assert same_idea_mechanism(MEC, "restringir cada autorizacion a un unico uso por operacion")


def test_vocabulario_compartido_con_mecanismo_distinto_no_se_confunde() -> None:
    assert not same_idea_mechanism(
        MEC, "auditar cada autorizacion otorgada por operadores externos semanalmente")


def test_mecanismo_incompleto_no_es_diverso_ni_duplicado() -> None:
    assert not same_idea_mechanism("", MEC)
    assert not same_idea_mechanism("m1", MEC)  # texto insuficiente
    a = {"genome": {"mechanism": ["unknown"], "trust_model": ["unknown"],
                    "topology": ["unknown"], "actor": ["unknown"], "time_model": ["unknown"]}}
    b = {"genome": {"mechanism": ["otro"], "trust_model": ["x"], "topology": ["y"],
                    "actor": ["z"], "time_model": ["w"]}}
    assert _structural_distance(a, b) == NEUTRAL_DISTANCE


def test_mecanismo_duplicado_exacto_se_detecta() -> None:
    assert same_idea_mechanism(MEC, MEC.upper())
