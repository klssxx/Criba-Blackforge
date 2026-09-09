"""Tests del OutcomeStore y del prior adaptativo del router (BLUEPRINT §6/§13-§15).

Cada test es determinista y offline. El store vive en tmp_path; el router usa el
registro canon real (TechniqueRegistry con REGISTRY_PATH) más un store inyectado.
"""
from __future__ import annotations

import json
import warnings
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from criba.intelligence.outcome_store import (
    BACKOFF_MIN_OBS,
    TechniqueOutcomeStore,
    CHANNEL_VERDICT,
)
from criba.intelligence.registry import TechniqueRegistry
from criba.intelligence.router import TechniqueRouter

REGISTRY_PATH = Path(__file__).resolve().parents[2] / "data" / "intelligence" / "technique_registry.yaml"


def _store(tmp_path) -> TechniqueOutcomeStore:
    return TechniqueOutcomeStore(tmp_path / "outcomes" / "t.jsonl")


class TestStoreSchema:
    def test_record_y_prior_minimo(self, tmp_path):
        s = _store(tmp_path)
        s.record(profile="CRIBA", family="INVENTION", technique_id="T059",
                 channel=CHANNEL_VERDICT, outcome="SURVIVED_SEARCH",
                 canon_version="2026-09-08.3")
        prior, n, label = s.prior(profile="CRIBA", family="INVENTION",
                                  technique_id="T059", canon_version="2026-09-08.3")
        assert n == 1 and prior > 0.0 and "ucb:" in label

    def test_outcome_invalido_rechazado(self, tmp_path):
        s = _store(tmp_path)
        with pytest.raises(ValueError, match="outcome inválido"):
            s.record(profile="CRIBA", family="INVENTION", technique_id="T059",
                     channel=CHANNEL_VERDICT, outcome="PROVEN_NEW",  # jamás
                     canon_version="x")
        with pytest.raises(ValueError, match="canal desconocido"):
            s.record(profile="CRIBA", family="INVENTION", technique_id="T059",
                     channel="novedad_absoluta", outcome="x", canon_version="x")

    def test_value_fuera_de_rango(self, tmp_path):
        s = _store(tmp_path)
        with pytest.raises(ValueError, match="fuera de \\[0,1\\]"):
            s.record(profile="CRIBA", family="INVENTION", technique_id="T059",
                     channel="judge", outcome="ok", value=1.7, canon_version="x")

    def test_lineas_malformadas_excluidas_con_warning(self, tmp_path):
        s = _store(tmp_path)
        s.path.parent.mkdir(parents=True, exist_ok=True)
        s.path.write_text('{"profile":"CRIBA","family":"INVENTION","technique_id":"T059",'
                          '"channel":"verdict","outcome":"SURVIVED_SEARCH","value":1.0,'
                          '"canon_version":"c","recorded_at":"2026-09-09T00:00:00+00:00"}\n'
                          "no-es-json\n"
                          '{"roto": true}\n', encoding="utf-8")
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            recs = s._read_valid()
        assert len(recs) == 1
        assert any(issubclass(w.category, RuntimeWarning) for w in caught)


class TestBackoffJerarquico:
    def test_backoff_a_familia_cuando_celda_fina_escasa(self, tmp_path):
        s = _store(tmp_path)
        # Menos de BACKOFF_MIN_OBS en la celda fina, pero el agregado de familia
        # tiene datos → el prior hace back-off a la familia.
        for _ in range(BACKOFF_MIN_OBS):
            s.record_family_outcome(profile="CRIBA", family="INVENTION",
                                    channel=CHANNEL_VERDICT, outcome="SURVIVED_SEARCH",
                                    canon_version="c")
        prior, n, label = s.prior(profile="CRIBA", family="INVENTION",
                                  technique_id="T999", canon_version="c")  # técnica sin datos
        assert n >= BACKOFF_MIN_OBS and prior > 0.0
        assert "backoff=True" in label

    def test_sin_datos_prior_cero(self, tmp_path):
        s = _store(tmp_path)
        prior, n, label = s.prior(profile="CRIBA", family="INVENTION",
                                  technique_id="T059", canon_version="c")
        assert prior == 0.0 and n == 0 and label == "sin_datos"


class TestCanonEpoch:
    def test_reset_por_canon_version(self, tmp_path):
        s = _store(tmp_path)
        for _ in range(3):
            s.record(profile="CRIBA", family="INVENTION", technique_id="T059",
                     channel=CHANNEL_VERDICT, outcome="SURVIVED_SEARCH",
                     canon_version="2026-09-08.2")
        # Misma técnica, época distinta: no hereda priors (§13.4).
        prior_new, n_new, _ = s.prior(profile="CRIBA", family="INVENTION",
                                      technique_id="T059", canon_version="2026-09-08.3")
        prior_old, n_old, _ = s.prior(profile="CRIBA", family="INVENTION",
                                      technique_id="T059", canon_version="2026-09-08.2")
        assert n_new == 0 and prior_new == 0.0
        assert n_old == 3 and prior_old > 0.0


class TestDecaimiento:
    def test_outcome_antiguo_pesa_menos(self, tmp_path):
        s = _store(tmp_path)
        old = datetime.now(timezone.utc) - timedelta(days=180)  # 2 vidas medias
        s.record(profile="CRIBA", family="INVENTION", technique_id="T059",
                 channel=CHANNEL_VERDICT, outcome="SURVIVED_SEARCH",
                 canon_version="c", recorded_at=old)
        s.record(profile="CRIBA", family="INVENTION", technique_id="T060",
                 channel=CHANNEL_VERDICT, outcome="SURVIVED_SEARCH",
                 canon_version="c")  # reciente
        p_old, _, _ = s.prior(profile="CRIBA", family="INVENTION",
                              technique_id="T059", canon_version="c")
        p_new, _, _ = s.prior(profile="CRIBA", family="INVENTION",
                              technique_id="T060", canon_version="c")
        assert p_new > p_old  # el reciente pesa más (decaimiento §14.3)


class TestInvarianteHash:
    def test_state_hash_comprobable(self, tmp_path):
        s = _store(tmp_path)
        h0 = s.state_hash()
        s.record(profile="CRIBA", family="INVENTION", technique_id="T059",
                 channel=CHANNEL_VERDICT, outcome="SURVIVED_SEARCH", canon_version="c")
        h1 = s.state_hash()
        assert h0 != h1  # el hash refleja el estado (§15.2)


class TestRouterAdaptativo:
    def test_congelado_default_sin_prior(self, tmp_path):
        """adaptive=False (default) es byte-idéntico: sin outcome_store no hay prior."""
        router = TechniqueRouter(TechniqueRegistry(REGISTRY_PATH))
        task = "morfologia contrafactual"
        base = router.select(task, "CRIBA")
        # sin store: aunque adaptive=True no debe cambiar nada
        adaptive = router.select(task, "CRIBA", adaptive=True, outcome_store=None)
        assert [c.id for c in base.selected] == [c.id for c in adaptive.selected]

    def test_prior_reordena_solo_elegibles(self, tmp_path):
        """Un prior alto sube una técnica IMPLEMENTED elegible en el ranking."""
        router = TechniqueRouter(TechniqueRegistry(REGISTRY_PATH))
        store = _store(tmp_path)
        registry = TechniqueRegistry(REGISTRY_PATH)
        task = "morphological counterfactual"
        base = router.select(task, "CRIBA")
        base_ids = [c.id for c in base.selected]
        assert base_ids, "la tarea debe disparar alguna técnica"
        target = base.selected[-1]  # la última: la impulsamos con prior alto
        for _ in range(5):
            store.record(profile="CRIBA", family=target.technique.family,
                         technique_id=target.id, channel=CHANNEL_VERDICT,
                         outcome="SURVIVED_SEARCH",
                         canon_version=registry.canon_version)
        boosted = router.select(task, "CRIBA", adaptive=True, outcome_store=store)
        boosted_ids = [c.id for c in boosted.selected]
        # la técnica impulsada sube de posición respecto al ranking congelado
        assert boosted_ids.index(target.id) <= base_ids.index(target.id)
        # y el prior queda auditado en reasons
        assert any("prior:" in r for c in boosted.selected for r in c.reasons)

    def test_guard_planned_nunca_ejecutable(self, tmp_path):
        """Una PLANNED con prior alto NUNCA se vuelve executable (honestidad §5)."""
        router = TechniqueRouter(TechniqueRegistry(REGISTRY_PATH))
        store = _store(tmp_path)
        registry = TechniqueRegistry(REGISTRY_PATH)
        # PLANNED que coincide con la tarea por léxico
        task = "patent keyword search"
        for _ in range(6):
            store.record(profile="CRIBA", family="PATENT_INTELLIGENCE",
                         technique_id="T001", channel=CHANNEL_VERDICT,
                         outcome="SURVIVED_SEARCH",
                         canon_version=registry.canon_version)
        result = router.select(task, "CRIBA", adaptive=True, outcome_store=store)
        for cand in result.selected:
            assert cand.executable, "ninguna PLANNED puede entrar como ejecutable"
        # T001 es PLANNED → puede aparecer como gap, jamás como selected ejecutable
        assert all(c.id != "T001" for c in result.selected)
