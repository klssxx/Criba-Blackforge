"""Tests de inventar.record_outcomes (escritura técnica→outcome, BLUEPRINT §4.4)."""
from __future__ import annotations

import pytest

from criba.inventar import _entry_technique_ids, record_outcomes
from criba.intelligence.outcome_store import (
    CHANNEL_JUDGE,
    CHANNEL_VERDICT,
    TechniqueOutcomeStore,
)


def _sheet(entries):
    return {"run_id": "run-test", "entries": entries}


def _entry(**kw):
    base = {
        "candidate_id": "c1",
        "run_id": "run-test",
        "classes": ["perspectiva", "generacion"],
        "aportacion_por_tecnica": [],
        "prior_art": {"verdict": "SURVIVED_SEARCH"},
        "judge": {"score": 0.7},
    }
    base.update(kw)
    return base


class TestTechniqueIds:
    def test_extrae_ids_de_dicts(self):
        e = _entry(aportacion_por_tecnica=[{"tecnica": "t059"}, {"id": "T129"}])
        assert _entry_technique_ids(e) == ["T059", "T129"]

    def test_extrae_ids_de_strings_y_dedup(self):
        e = _entry(aportacion_por_tecnica=["T057", "t057", "T060"])
        assert _entry_technique_ids(e) == ["T057", "T060"]

    def test_sin_aportacion_lista_vacia(self):
        assert _entry_technique_ids(_entry()) == []


class TestRecordOutcomes:
    def test_escribe_canales_etiquetados_por_tecnica(self, tmp_path):
        store = TechniqueOutcomeStore(tmp_path / "o.jsonl")
        sheet = _sheet([_entry(aportacion_por_tecnica=[{"tecnica": "T059"}])])
        n = record_outcomes(sheet, store, canon_version="2026-09-08.3")
        # 1 verdict (técnica) + 1 judge (técnica) + 1 agregado familia
        assert n == 3
        recs = store._read_valid()
        channels = {(r["technique_id"], r["channel"]) for r in recs}
        assert ("T059", CHANNEL_VERDICT) in channels
        assert ("T059", CHANNEL_JUDGE) in channels
        # etiquetados, nunca mezclados: verdict y judge son registros distintos
        assert len(recs) == 3

    def test_prior_disponible_tras_escritura(self, tmp_path):
        """El circuito se cierra: lo escrito por record_outcomes lo lee el router."""
        store = TechniqueOutcomeStore(tmp_path / "o.jsonl")
        for _ in range(3):
            sheet = _sheet([_entry(aportacion_por_tecnica=[{"tecnica": "T059"}])])
            record_outcomes(sheet, store, canon_version="2026-09-08.3")
        prior, n, _ = store.prior(profile="CRIBA", family="perspectiva",
                                  technique_id="T059", canon_version="2026-09-08.3")
        assert n >= 3 and prior > 0.0

    def test_sin_tecnicas_no_escribe_nada(self, tmp_path):
        store = TechniqueOutcomeStore(tmp_path / "o.jsonl")
        n = record_outcomes(_sheet([_entry()]), store, canon_version="c")
        # solo el agregado de familia (back-off), sin técnicas individuales
        recs = store._read_valid()
        assert all(r["technique_id"] == "__family__" for r in recs)

    def test_verdict_invalido_normalizado_a_unresolved(self, tmp_path):
        store = TechniqueOutcomeStore(tmp_path / "o.jsonl")
        e = _entry(aportacion_por_tecnica=[{"tecnica": "T059"}],
                   prior_art={"verdict": "PROVEN_NEW"})  # jamás
        record_outcomes(_sheet([e]), store, canon_version="c")
        recs = [r for r in store._read_valid() if r["channel"] == CHANNEL_VERDICT]
        assert all(r["outcome"] == "UNRESOLVED" for r in recs)

    def test_nunca_rompe_el_loop_con_store_roto(self, tmp_path):
        """Un store que falla en record() no rompe la escritura (memoria opcional)."""
        class BrokenStore:
            def record(self, **kw):
                raise RuntimeError("disco lleno")
            def record_family_outcome(self, **kw):
                raise RuntimeError("disco lleno")
        n = record_outcomes(_sheet([_entry(aportacion_por_tecnica=[{"tecnica": "T059"}])]),
                            BrokenStore(), canon_version="c")
        assert n == 0  # degradación elegante, cero excepción propagada

    def test_aislamiento_por_perfil(self, tmp_path):
        """Outcomes BLACKFORGE no contaminan priors CRIBA (§13.6)."""
        store = TechniqueOutcomeStore(tmp_path / "o.jsonl")
        sheet = _sheet([_entry(aportacion_por_tecnica=[{"tecnica": "T059"}])])
        record_outcomes(sheet, store, profile="BLACKFORGE", canon_version="c")
        p_criba, n_criba, _ = store.prior(profile="CRIBA", family="perspectiva",
                                          technique_id="T059", canon_version="c")
        p_bf, n_bf, _ = store.prior(profile="BLACKFORGE", family="perspectiva",
                                    technique_id="T059", canon_version="c")
        assert n_criba == 0 and p_criba == 0.0
        assert n_bf >= 1 and p_bf > 0.0
