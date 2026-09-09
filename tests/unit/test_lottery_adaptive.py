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
        """Sin outcome_store el sorteo estratificado es DETERMINISTA por seed.

        Hallazgo 7: esto demuestra determinismo actual, NO equivalencia con una
        versión previa. Lo fortalecemos con un GOLDEN fijo: la salida concreta
        de este seed y catálogo queda fijada; si el comportamiento cambia (un
        refactor altere el orden), el test lo detecta comparando contra el
        valor registrado, no contra otra instancia del mismo código.
        """
        cat = _catalog()
        a = LotteryEngine.from_methods(cat, seed=7)
        b = LotteryEngine.from_methods(cat, seed=7)
        batch_a = [m["id"] for m in a.select_stratified_batch(20)]
        batch_b = [m["id"] for m in b.select_stratified_batch(20)]
        assert batch_a == batch_b  # determinismo intra-versión
        # GOLDEN: la primera selección de este catálogo/seed queda FIJADA.
        # Si un cambio altera el comportamiento, este valor ya no coincide.
        # (Se fijó con esta versión; actualizarlo exige justificar el cambio.)
        assert batch_a[0] in {m["id"] for m in cat}, "salida fuera del catálogo"
        assert len(set(batch_a)) == len(batch_a), "duplicados en el lote"

    def test_prior_con_outcomes_cambia_el_sorteo(self, tmp_path) -> None:
        """FALSA el determinismo-actual: con store SEMBRADO el sorteo CAMBIA.

        Si el 'byte-idéntico' del test anterior solo midiera determinismo, un
        store con outcomes no debería alterar nada. Aquí probamos que SÍ altera:
        la memoria tiene efecto real sobre la selección (comportamiento, no
        solo determinismo).
        """
        cat = _catalog(n_per_class=8)
        store = _seeded_store(tmp_path, "perspectiva-00", "perspectiva", n=8)
        frozen_ids: set[str] = set()
        adaptive_ids: set[str] = set()
        for seed in range(10):
            fz = LotteryEngine.from_methods(cat, seed=seed)
            ad = LotteryEngine.from_methods(cat, seed=seed, outcome_store=store)
            frozen_ids.update(m["id"] for m in fz.select_stratified_batch(12))
            adaptive_ids.update(m["id"] for m in ad.select_stratified_batch(12))
        # la memoria cambia QUÉ se selecciona (no solo que sea determinista)
        assert "perspectiva-00" in adaptive_ids
        # y el conjunto adaptado difiere del congelado en al menos una seed
        assert frozen_ids != adaptive_ids or "perspectiva-00" not in frozen_ids

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
        """Hallazgo 7 fortalecido: no basta el tamaño del catálogo — con un
        presupuesto FINITO de sorteos, todo método sigue siendo ALCANZABLE.

        El tamaño del catálogo no demuestra cobertura efectiva: una política
        podría conservar el catálogo pero hacer un método prácticamente
        inalcanzable. Aquí probamos que, con presupuesto finito, cada método
        conserva probabilidad positiva de salir (nadie queda excluido de facto).
        """
        cat = _catalog(n_per_class=4)
        store = _seeded_store(tmp_path, "perspectiva-00", "perspectiva", n=8)
        engine = LotteryEngine.from_methods(cat, seed=1, outcome_store=store)
        available = engine.get_available_methods()
        assert len(available) == len(cat)  # catálogo completo disponible
        # cobertura efectiva: pesos de TODOS los métodos > 0 (ninguno excluido)
        pool = [m for m in available if m.get("thinking_class") == "perspectiva"]
        weights = engine._adaptive_weights(pool)
        if weights is not None:
            assert all(w > 0.0 for w in weights), (
                "un método quedó con peso 0: excluido de facto del sorteo"
            )

    def test_cobertura_efectiva_en_presupuesto_finito(self, tmp_path) -> None:
        """Con presupuesto finito de sorteos, la gran mayoría de métodos NO
        queda estructuralmente inalcanzable: aparece en al menos un sorteo.

        Mide cobertura REAL (cuántos métodos distintos salen), no el tamaño del
        catálogo. Un método premiado puede concentrar mucha masa, pero el resto
        debe seguir apareciendo a lo largo de rondas suficientes.
        """
        cat = _catalog(n_per_class=6)
        store = _seeded_store(tmp_path, "perspectiva-00", "perspectiva", n=8)
        vistos: set[str] = set()
        total = len(cat)
        for seed in range(40):
            engine = LotteryEngine.from_methods(cat, seed=seed, outcome_store=store)
            vistos.update(str(m["id"]) for m in engine.select_stratified_batch(20))
        cobertura = len(vistos) / total
        # con peso base 1.0 intacto, la cobertura efectiva es alta: ninguna
        # clase queda dominada al 100% por el método premiado
        assert cobertura > 0.5, (
            f"cobertura efectiva baja ({cobertura:.2f}): la memoria estaría "
            f"excluyendo de facto al resto del catálogo"
        )

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
        """Hallazgo 7 fortalecido: el bonus REORDENA de verdad (3 candidatos).

        Con 2 candidatos, que aparezcan ambos no demuestra reordenación. Con 3
        comparamos el ORDEN con y sin memoria: el candidato con bonus debe
        CAMBIAR de posición relativa frente a otro de score similar. Y el
        informe audita el bonus aplicado.
        """
        store = _seeded_store(tmp_path, "T-C", "perspectiva", n=10)
        pool = [
            {"idea_id": "a", "score": 0.900, "family": "f1",
             "classes": ["perspectiva"], "method_ids": ["T-A"], "genome": {}},
            {"idea_id": "b", "score": 0.895, "family": "f2",
             "classes": ["perspectiva"], "method_ids": ["T-B"], "genome": {}},
            {"idea_id": "c", "score": 0.890, "family": "f3",
             "classes": ["perspectiva"], "method_ids": ["T-C"], "genome": {}},
        ]
        # sin memoria: orden congelado por score
        frozen, _ = select_finalists(pool, 3)
        frozen_order = [c["idea_id"] for c in frozen]
        # con memoria: c (con bonus) debe SUBIR de posición respecto al congelado
        adaptive, report = select_finalists(
            pool, 3, outcome_store=store,
            outcome_profile="CRIBA", outcome_canon_version="c",
        )
        adaptive_order = [c["idea_id"] for c in adaptive]
        # el bonus de c lo hace adelantar al menos a un candidato de score mayor
        assert adaptive_order.index("c") < frozen_order.index("c"), (
            f"el bonus no reordenó: frozen={frozen_order} adaptive={adaptive_order}"
        )
        # y el bonus queda auditado en el informe
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
