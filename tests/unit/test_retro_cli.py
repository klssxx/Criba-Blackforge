"""Tests del cierre de circuito G1 (inventar --adaptive escribe outcomes) y del
canal OBSERVED vía `criba retro` — ambos sin LLM (offline)."""
from __future__ import annotations

from criba.cli import main
from criba.intelligence.outcome_store import (
    CHANNEL_OBSERVED,
    CHANNEL_VERDICT,
    TechniqueOutcomeStore,
)


def _store_path(tmp_path):
    return tmp_path / "CRIBA-Blackforge" / "outcomes" / "technique_outcomes.jsonl"


class TestRetroCli:
    def test_retro_registra_observed_etiquetado(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
        code = main([
            "retro", "--tecnica", "t059", "--familia", "perspectiva",
            "--resultado", "positivo",
        ])
        assert code == 0
        store = TechniqueOutcomeStore(_store_path(tmp_path))
        recs = store._read_valid()
        observed = [r for r in recs if r["channel"] == CHANNEL_OBSERVED]
        assert observed, "debe registrar al menos un outcome OBSERVED"
        rec = observed[0]
        assert rec["technique_id"] == "T059"  # normalizado a mayúsculas
        assert rec["outcome"] == "positivo"
        assert rec["value"] == 1.0
        assert rec["channel"] == CHANNEL_OBSERVED  # etiquetado, nunca mezclado

    def test_retro_resultado_invalido_rechazado_por_argparse(self, tmp_path, monkeypatch):
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
        try:
            main(["retro", "--tecnica", "T059", "--familia", "x",
                  "--resultado", "novedad_absoluta"])  # jamás
        except SystemExit as exc:
            assert exc.code != 0  # argparse lo rechaza (choices fijos)
        else:
            raise AssertionError("argparse debió rechazar el resultado inválido")

    def test_retro_aislamiento_por_perfil(self, tmp_path, monkeypatch):
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
        main(["retro", "--tecnica", "T059", "--familia", "perspectiva",
              "--resultado", "negativo", "--perfil", "BLACKFORGE"])
        store = TechniqueOutcomeStore(_store_path(tmp_path))
        p_criba, n_criba, _ = store.prior(
            profile="CRIBA", family="perspectiva", technique_id="T059",
            channel=CHANNEL_OBSERVED, canon_version=None)
        p_bf, n_bf, _ = store.prior(
            profile="BLACKFORGE", family="perspectiva", technique_id="T059",
            channel=CHANNEL_OBSERVED, canon_version=None)
        assert n_criba == 0 and n_bf >= 1  # BF no contamina CRIBA


class TestInventarCierraCircuito:
    def test_inventar_adaptive_escribe_outcomes(self, tmp_path, monkeypatch):
        """Con --adaptive, inventar registra outcomes en el store (circuito G1)."""
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
        code = main([
            "inventar", "test circuito g1",
            "--seed", "7", "--rounds", "1", "--batch-size", "4",
            "--top", "1", "--offline", "--adaptive",
        ])
        assert code == 0
        store = TechniqueOutcomeStore(_store_path(tmp_path))
        recs = store._read_valid()
        # al menos el agregado de familia (verdict) se escribe
        assert any(r["channel"] == CHANNEL_VERDICT for r in recs), (
            "inventar --adaptive debe escribir outcomes verdict al store"
        )

    def test_inventar_sin_adaptive_no_escribe_outcomes(self, tmp_path, monkeypatch):
        """Sin --adaptive (default congelado) no se escribe nada al store."""
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
        code = main([
            "inventar", "test congelado",
            "--seed", "7", "--rounds", "1", "--batch-size", "4",
            "--top", "1", "--offline",
        ])
        assert code == 0
        store = TechniqueOutcomeStore(_store_path(tmp_path))
        assert store._read_valid() == []  # el modo congelado no alimenta memoria
