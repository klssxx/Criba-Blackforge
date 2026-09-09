"""Tests G2: memoria compartida lotería/selector (BLUEPRINT §12.4).

Contratos verificados:
- Sin outcome_store (default): byte-idéntico al congelado (misma seed = mismo
  output), invariante intacto.
- Con store: el sorteo estratificado se pondera por prior UCB (los métodos con
  outcomes SURVIVED suben en frecuencia de aparición).
- El prior NUNCA excluye un método: catálogo completo disponible siempre.
- El selector diversity-aware suma el bonus de memoria SOLO sobre el suelo de
  calidad (nunca rescata candidatos por debajo del floor).
- Aislamiento por perfil: outcomes BLACKFORGE no contaminan CRIBA.
- La memoria rota o vacía degrada al comportamiento congelado (nunca rompe).
"""
from __future__ import annotations

import pytest

from criba.diversity_selector import _adaptive_bonus, select_finalists
from criba.intelligence.outcome_store import (
    CHANNEL_VERDICT,
    TechniqueOutcomeStore,
)
from criba.lottery import DRAW_CLASSES, LotteryEngine


def _catalog(n_per_class: int = 6) -> list[dict[str, object]]:
    """Catálogo sintético: n métodos por cada clase de pensamiento."""
    out: list[dict[str, object]] = []
    for cls in DRAW_CLASSES:
        for i in range(n_per_class):
            out.append({
                "id": f"{cls}-{i:02d}",
                "name": f"Metodo {cls} {i}",
                "title": f"Metodo {cls} {i}",
                "description": f"metodo de clase {cls}",
                "family": f"fam-{cls}",
                "thinking_class": cls,
                "quality_score_v2": i,
            })
    return out


def _seeded_store(tmp_path, method_id: str, thinking_class: str, n: int = 5,
                  profile: str = "CRIBA") -> TechniqueOutcomeStore:
    store = TechniqueOutcomeStore(tmp_path / "outcomes" / "t.jsonl")
    for _ in range(n):
        store.record(profile=profile, family=thinking_class, technique_id=method_id,
                     channel=CHANNEL_VERDICT, outcome="SURVIVED_SEARCH",
                     canon_version="c")
    return store


class TestFrozenInvariant:
    def test_sin_store_byte_identico_al_congelado(self) -> None:
        """Sin outcome_store el sorteo estratificado es byte-idéntico (G2 opt-in)."""
        cat = _catalog()
        a = LotteryEngine.from_methods(cat, seed=7)
        b = LotteryEngine.from_methods(cat, seed=7)
        batch_a = [m["id"] for m in a.select_stratified_batch(20)]
        batch_b = [m["id"] for m in b.select_stratified_batch(20)]
        assert batch_a == batch_b

    def test_con_store_vacio_no_cambia_la_distribucion(self, tmp_path) -> None:
        """Un store sin outcomes del catálogo: pesos uniformes → misma distribución.

        (No mismo RNG path: rng.choices consume el generador de otro modo que
        rng.choice, así que la comparación exacta byte-a-byte solo aplica a
        outcome_store=None — el modo congelado real. Con store vacío lo que se
        garantiza es que la distribución sigue siendo uniforme: ningún método
        es favorecido sobre las rondas.)
        """
        cat = _catalog(n_per_class=8)
        store = TechniqueOutcomeStore(tmp_path / "empty.jsonl")
        counts: dict[str, int] = {}
        trials = 30
        for seed in range(trials):
            adaptive = LotteryEngine.from_methods(cat, seed=seed, outcome_store=store)
            for m in adaptive.select_stratified_batch(12):
                counts[str(m["id"])] = counts.get(str(m["id"]), 0) + 1
        # sin datos: la frecuencia máxima no se dispara respecto a la media
        avg = sum(counts.values()) / len(counts)
        assert max(counts.values()) <= avg * 2.5, (
            "store vacío no debe favorecer a ningún método"
        )

    def test_store_roto_degrada_a_congelado(self, tmp_path) -> None:
        """Un store que falla en prior() nunca rompe el sorteo (memoria opcional)."""
        class BrokenStore:
            def prior(self, **kw):  # noqa: ANN001
                raise RuntimeError("disco lleno")

        cat = _catalog()
        engine = LotteryEngine.from_methods(cat, seed=7, outcome_store=BrokenStore())
        batch = engine.select_stratified_batch(20)
        assert len(batch) == 20  # funciona; degradación elegante


class TestAdaptiveLottery:
    def test_metodo_con_outcomes_sube_en_frecuencia(self, tmp_path) -> None:
        """El método con prior SURVIVED es sorteado más a menudo que sin memoria."""
        cat = _catalog(n_per_class=8)
        target = "perspectiva-00"
        store = _seeded_store(tmp_path, target, "perspectiva", n=8)
        counts_frozen = 0
        counts_adaptive = 0
        trials = 30
        for seed in range(trials):
            frozen = LotteryEngine.from_methods(cat, seed=seed)
            adaptive = LotteryEngine.from_methods(cat, seed=seed, outcome_store=store)
            frozen_batch = {m["id"] for m in frozen.select_stratified_batch(12)}
            adaptive_batch = {m["id"] for m in adaptive.select_stratified_batch(12)}
            counts_frozen += int(target in frozen_batch)
            counts_adaptive += int(target in adaptive_batch)
        assert counts_adaptive > counts_frozen, (
            f"con memoria el método premiado debe subir: "
            f"frozen={counts_frozen}, adaptive={counts_adaptive}"
        )

    def test_prior_nunca_excluye_metodos(self, tmp_path) -> None:
        """Ningún método desaparece del catálogo aunque no tenga outcomes."""
        cat = _catalog(n_per_class=4)
        store = _seeded_store(tmp_path, "perspectiva-00", "perspectiva", n=8)
        engine = LotteryEngine.from_methods(cat, seed=1, outcome_store=store)
        available = engine.get_available_methods()
        assert len(available) == len(cat)  # catálogo completo disponible

    def test_aislamiento_por_perfil(self, tmp_path) -> None:
        """Outcomes BLACKFORGE no favorecen a CRIBA (§13.6, medido en frecuencia)."""
        cat = _catalog(n_per_class=8)
        target = "perspectiva-00"
        store = _seeded_store(tmp_path, target, "perspectiva", n=8,
                              profile="BLACKFORGE")
        counts = 0
        trials = 30
        for seed in range(trials):
            engine = LotteryEngine.from_methods(
                cat, seed=seed, outcome_store=store, outcome_profile="CRIBA")
            batch = {m["id"] for m in engine.select_stratified_batch(12)}
            counts += int(target in batch)
        # la memoria de BF no impulsa al método en CRIBA: frecuencia básica
        # comparable a la del sorteo uniforme (12/32 ≈ 0.375 por ronda)
        assert counts <= trials * 0.75, (
            f"la memoria BLACKFORGE no debe impulsar a CRIBA: {counts}/{trials}"
        )


class TestAdaptiveBonus:
    def _pool(self) -> list[dict[str, object]]:
        return [
            {"idea_id": "a", "score": 0.90, "family": "f1",
             "method_ids": ["T-A"], "genome": {}},
            {"idea_id": "b", "score": 0.88, "family": "f2",
             "method_ids": ["T-B"], "genome": {}},
        ]

    def test_sin_store_bonus_cero(self, tmp_path) -> None:
        cand = {"method_ids": ["T059"], "classes": ["perspectiva"], "family": "f"}
        bonus, label = _adaptive_bonus(cand, None, "CRIBA", "c")
        assert bonus == 0.0 and label == ""

    def test_bonus_solo_con_outcomes(self, tmp_path) -> None:
        store = _seeded_store(tmp_path, "T059", "perspectiva", n=4)
        cand = {"method_ids": ["T059"], "classes": ["perspectiva"], "family": "f"}
        bonus, label = _adaptive_bonus(cand, store, "CRIBA", "c")
        assert bonus > 0.0 and "memoria:bonus=" in label

    def test_bonus_nunca_negativo(self, tmp_path) -> None:
        store = TechniqueOutcomeStore(tmp_path / "o.jsonl")
        for _ in range(4):
            store.record(profile="CRIBA", family="perspectiva", technique_id="T059",
                         channel=CHANNEL_VERDICT, outcome="UNRESOLVED",
                         canon_version="c")
        cand = {"method_ids": ["T059"], "classes": ["perspectiva"], "family": "f"}
        bonus, _ = _adaptive_bonus(cand, store, "CRIBA", "c")
        assert bonus >= 0.0

    def test_store_roto_bonus_cero(self, tmp_path) -> None:
        class BrokenStore:
            def prior(self, **kw):  # noqa: ANN001
                raise RuntimeError("disco lleno")

        cand = {"method_ids": ["T059"], "classes": ["perspectiva"], "family": "f"}
        bonus, label = _adaptive_bonus(cand, BrokenStore(), "CRIBA", "c")
        assert bonus == 0.0 and label == ""


class TestAdaptiveSelector:
    def test_sin_store_selector_congelado(self, tmp_path) -> None:
        """Sin store el selector es byte-idéntico (G2 opt-in)."""
        pool = [
            {"idea_id": "a", "score": 0.90, "family": "f1",
             "method_ids": ["T-A"], "genome": {}},
            {"idea_id": "b", "score": 0.89, "family": "f2",
             "method_ids": ["T-B"], "genome": {}},
        ]
        x, _ = select_finalists(pool, 2)
        y, _ = select_finalists(pool, 2, outcome_store=None)
        assert [c["idea_id"] for c in x] == [c["idea_id"] for c in y]

    def test_bonus_reordena_respetando_suelo(self, tmp_path) -> None:
        """El bonus puede reordenar candidatos sobre el suelo, nunca rescatar bajos.

        El primer pick es siempre el mejor score sobre el suelo; el bonus se
        aplica a partir del segundo pick (utilidad marginal). Lo comprobable:
        el informe audita el bonus aplicado en el pick donde actúa.
        """
        store = _seeded_store(tmp_path, "T-B", "perspectiva", n=8)
        pool = [
            {"idea_id": "a", "score": 0.900, "family": "f1",
             "classes": ["perspectiva"], "method_ids": ["T-A"], "genome": {}},
            {"idea_id": "b", "score": 0.899, "family": "f2",
             "classes": ["perspectiva"], "method_ids": ["T-B"], "genome": {}},
        ]
        finalists, report = select_finalists(
            pool, 2, outcome_store=store,
            outcome_profile="CRIBA", outcome_canon_version="c",
        )
        ids = [c["idea_id"] for c in finalists]
        assert "b" in ids and "a" in ids
        # el informe audita el bonus aplicado en el pick por utilidad marginal
        assert any("memoria:bonus=" in str(pick.get("why", ""))
                   for pick in report["picks"]), (
            f"el bonus debe quedar auditado en picks: {report['picks']}"
        )

    def test_bonus_no_rescata_bajo_el_suelo(self, tmp_path) -> None:
        """Un candidato bajo el floor NO entra aunque tenga bonus de memoria."""
        store = _seeded_store(tmp_path, "T-LOW", "perspectiva", n=10)
        pool = [
            {"idea_id": "top", "score": 1.00, "family": "f1",
             "method_ids": ["T-TOP"], "genome": {}},
            {"idea_id": "low", "score": 0.10, "family": "f2",
             "method_ids": ["T-LOW"], "genome": {}},
        ]
        finalists, report = select_finalists(
            pool, 2, outcome_store=store,
            outcome_profile="CRIBA", outcome_canon_version="c",
        )
        ids = [c["idea_id"] for c in finalists]
        assert "low" not in ids  # el suelo de calidad manda sobre la memoria
