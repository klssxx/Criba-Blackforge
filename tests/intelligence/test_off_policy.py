"""Tests de la evaluación off-policy (G3, BLUEPRINT §12.4).

Contratos verificados:
- El estimador SNIPS RECUPERA el valor verdadero en un escenario sintético
  controlado donde la política de logging y la candidata son conocidas.
- UNRESOLVED honesto (nunca mejora inventada): log vacío, propensión inválida,
  violación de solape, ESS bajo.
- IC bootstrap determinista: misma semilla = mismo IC.
- append/read del log con validación y exclusión de malformados.
"""
from __future__ import annotations

import pytest

from criba.intelligence.off_policy import (
    LoggedDecision,
    append_decision,
    compare_policies,
    evaluate_policy,
    log_hash,
    read_decisions,
)


def _decisions(n: int, boosted_id: str = "good") -> list[LoggedDecision]:
    """Log sintético: política de logging UNIFORME sobre {good, bad} (pi_b=0.5).

    Recompensa: 'good' siempre 1.0, 'bad' siempre 0.0. Como pi_b es uniforme,
    el valor verdadero de una candidata que siempre elige 'good' es 1.0, y el
    de la política de logging 0.5. SNIPS debe recuperar ambos.
    """
    out: list[LoggedDecision] = []
    for i in range(n):
        pick = boosted_id if i % 2 == 0 else "bad"
        out.append(LoggedDecision(
            technique_id=pick, family="f", propensity=0.5,
            reward=1.0 if pick == boosted_id else 0.0,
        ))
    return out


class TestLog:
    def test_append_y_read_roundtrip(self, tmp_path):
        p = tmp_path / "log.jsonl"
        append_decision(p, LoggedDecision("T059", "f", 0.25, 1.0, run_id="r1"))
        got = read_decisions(p)
        assert len(got) == 1
        assert got[0].technique_id == "T059"
        assert got[0].propensity == 0.25
        assert got[0].reward == 1.0
        assert got[0].run_id == "r1"

    def test_append_rechaza_propension_invalida(self, tmp_path):
        p = tmp_path / "log.jsonl"
        with pytest.raises(ValueError, match="propensión"):
            append_decision(p, LoggedDecision("T059", "f", 0.0, 1.0))
        with pytest.raises(ValueError, match="reward"):
            append_decision(p, LoggedDecision("T059", "f", 0.5, 1.7))

    def test_read_excluye_malformados(self, tmp_path):
        p = tmp_path / "log.jsonl"
        p.write_text(
            '{"technique_id":"T059","family":"f","propensity":0.5,"reward":1.0}\n'
            "no-es-json\n"
            '{"roto": true}\n',
            encoding="utf-8",
        )
        import warnings
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            got = read_decisions(p)
        assert len(got) == 1
        assert any(issubclass(w.category, RuntimeWarning) for w in caught)

    def test_log_hash_estable(self, tmp_path):
        p = tmp_path / "log.jsonl"
        h0 = log_hash(p)
        append_decision(p, LoggedDecision("T059", "f", 0.5, 1.0))
        assert log_hash(p) != h0


class TestEvaluate:
    def test_recupera_valor_verdadero_candidata(self):
        """SNIPS recupera el valor 1.0 de una candidata que elige 'good' con
        propensión 1 y 'bad' con la mínima propensión de solape >0.

        Con logging uniforme (pi_b=0.5) y recompensa 1.0 solo en 'good': la
        razón sobre 'good' es 1/0.5=2 y sobre 'bad' ~0/0.5≈0, así SNIPS tiende
        al valor verdadero de la candidata determinista sobre 'good' (=1.0)
        salvo el término de solape mínimo.
        """
        decisions = _decisions(400)
        eps = 1e-6  # solape mínimo: nunca 0 (guard honesto)
        est = evaluate_policy(
            decisions, lambda t, f, pool: 1.0 if t == "good" else eps)
        assert est.verdict == "ESTIMATED"
        assert est.value is not None and est.value == pytest.approx(1.0, abs=0.05)

    def test_recupera_valor_verdadero_logging(self):
        """La política de logging uniforme recupera su media verdadera 0.5."""
        decisions = _decisions(400)
        est = evaluate_policy(decisions, lambda t, f, pool: 1.0)  # razón 1/pi_b
        assert est.verdict == "ESTIMATED"
        assert est.value is not None and est.value == pytest.approx(0.5, abs=0.05)

    def test_log_vacio_unresolved(self):
        est = evaluate_policy([], lambda t, f, pool: 1.0)
        assert est.verdict == "UNRESOLVED"
        assert est.value is None

    def test_propension_invalida_unresolved(self):
        bad = [LoggedDecision("T059", "f", 0.0, 1.0)]  # propensión 0: sin contrafactual
        est = evaluate_policy(bad, lambda t, f, pool: 1.0)
        assert est.verdict == "UNRESOLVED"
        assert "propensión" in est.reason

    def test_violacion_de_solape_unresolved(self):
        decisions = _decisions(50)
        # candidata da propensión 0 a 'bad', que la política de logging tomó
        est = evaluate_policy(decisions, lambda t, f, pool: 1.0 if t == "good" else 0.0)
        assert est.verdict == "UNRESOLVED"
        assert "solape" in est.reason

    def test_ess_bajo_unresolved(self):
        # pocas decisiones -> ESS < 10 -> UNRESOLVED honesto
        decisions = _decisions(6)
        est = evaluate_policy(decisions, lambda t, f, pool: 1.0)
        assert est.verdict == "UNRESOLVED"
        assert "ESS" in est.reason

    def test_ic_determinista_misma_semilla(self):
        decisions = _decisions(200)
        a = evaluate_policy(decisions, lambda t, f, pool: 1.0, seed=7)
        b = evaluate_policy(decisions, lambda t, f, pool: 1.0, seed=7)
        assert (a.ci_low, a.ci_high) == (b.ci_low, b.ci_high)


class TestCompare:
    def test_candidata_mejor_detectada(self):
        """Una candidata que elige 'good' (con solape mínimo) supera al logging
        uniforme, que reparte 50/50 entre 'good' (r=1) y 'bad' (r=0)."""
        decisions = _decisions(600)
        eps = 1e-6
        result = compare_policies(decisions, lambda t, f, pool: 1.0 if t == "good" else eps)
        assert result["verdict"] == "CANDIDATE_BETTER"
        assert result["candidate"]["value"] > result["logging"]["value"]

    def test_sin_diferencia_unresolved(self):
        """Candidata idéntica al logging: IC solapados -> no se afirma mejora."""
        decisions = _decisions(600)
        result = compare_policies(decisions, lambda t, f, pool: 1.0)
        assert result["verdict"] == "UNRESOLVED"

    def test_log_vacio_compare_unresolved(self):
        result = compare_policies([], lambda t, f, pool: 1.0)
        assert result["verdict"] == "UNRESOLVED"
