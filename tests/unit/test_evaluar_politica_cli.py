"""Tests del comando `criba evaluar-politica` (G3, off-policy).

Contratos:
- Log vacío -> verdict UNRESOLVED honesto (nunca afirma mejora sin evidencia).
- Política uniforme (--boost ausente) sobre log uniforme -> UNRESOLVED (sin
  diferencia demostrable).
- Con prior alto sembrado + --boost -> CANDIDATE_BETTER detectado.
"""
from __future__ import annotations

import json

from criba.cli import main
from criba.intelligence.off_policy import LoggedDecision, append_decision, _default_log_path
from criba.intelligence.outcome_store import TechniqueOutcomeStore, CHANNEL_OBSERVED


def _seed_log(n: int = 600) -> None:
    p = _default_log_path()
    for i in range(n):
        pick = "good" if i % 2 == 0 else "bad"
        append_decision(p, LoggedDecision(pick, "f", 0.5, 1.0 if pick == "good" else 0.0))


class TestEvaluarPoliticaCli:
    def test_log_vacio_unresolved(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
        assert main(["evaluar-politica"]) == 0
        out = json.loads(capsys.readouterr().out)
        assert out["verdict"] == "UNRESOLVED"

    def test_uniforme_sin_diferencia(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
        _seed_log()
        assert main(["evaluar-politica"]) == 0
        out = json.loads(capsys.readouterr().out)
        assert out["verdict"] == "UNRESOLVED"  # candidata uniforme == logging

    def test_boost_con_prior_detecta_mejora(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
        store = TechniqueOutcomeStore()
        for _ in range(10):
            store.record(profile="CRIBA", family="f", technique_id="good",
                         channel=CHANNEL_OBSERVED, outcome="positivo", canon_version="")
        _seed_log()
        assert main(["evaluar-politica", "--boost", "100"]) == 0
        out = json.loads(capsys.readouterr().out)
        assert out["verdict"] == "CANDIDATE_BETTER"
        assert out["candidate"]["value"] > out["logging"]["value"]
