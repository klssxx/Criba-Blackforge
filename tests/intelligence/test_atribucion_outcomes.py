"""Tests de atribución (P4): cada método sorteado recibe SU clase y SU outcome.

El defecto original: record_outcomes atribuía todo a aportacion_por_tecnica
(vacío offline) y a la PRIMERA clase del cruce — la lotería aprende por
method_ids y clases de pensamiento, así que el circuito quedaba desconectado.
La prueba que lo falsan: dos métodos de clases distintas deben recibir cada uno
la atribución correcta, y el prior debe ser consultable por la MISMA clave que
usa la lotería.
"""
from __future__ import annotations

from criba.inventar import record_outcomes
from criba.intelligence.outcome_store import (
    CHANNEL_VERDICT,
    TechniqueOutcomeStore,
)


def _entry_dos_clases() -> dict:
    """Un cruce de dos métodos de clases de pensamiento DISTINTAS."""
    return {
        "candidate_id": "c1",
        "run_id": "run-atrib",
        "classes": ["perspectiva", "ruptura"],
        "method_ids": ["lentes_p_001", "metafora_r_007"],
        "methods": ["Lentes P", "Metafora R"],
        "aportacion_por_tecnica": [],
        "prior_art": {"verdict": "SURVIVED_SEARCH"},
        "judge": {"score": 0.8},
    }


class TestAtribucionPorClase:
    def test_cada_metodo_recibe_su_clase(self, tmp_path):
        """Cada method_id se registra con SU clase, no la primera del cruce."""
        store = TechniqueOutcomeStore(tmp_path / "o.jsonl")
        sheet = {"run_id": "run-atrib", "entries": [_entry_dos_clases()]}
        record_outcomes(sheet, store, canon_version="c")
        recs = store._read_valid()
        verdicts = {(r["technique_id"], r["family"]) for r in recs
                    if r["channel"] == CHANNEL_VERDICT and r["technique_id"] != "__family__"}
        assert ("lentes_p_001", "perspectiva") in verdicts
        assert ("metafora_r_007", "ruptura") in verdicts
        # y NINGUNO quedó mal atribuido a la clase del otro
        assert ("metafora_r_007", "perspectiva") not in verdicts
        assert ("lentes_p_001", "ruptura") not in verdicts

    def test_agregado_de_familia_por_cada_clase(self, tmp_path):
        """El back-off agrega por CADA clase presente, no solo la primera."""
        store = TechniqueOutcomeStore(tmp_path / "o.jsonl")
        sheet = {"run_id": "run-atrib", "entries": [_entry_dos_clases()]}
        record_outcomes(sheet, store, canon_version="c")
        recs = store._read_valid()
        familias = {r["family"] for r in recs if r["technique_id"] == "__family__"}
        assert "perspectiva" in familias and "ruptura" in familias

    def test_prior_consultable_por_clave_de_loteria(self, tmp_path):
        """El circuito se CIERRA: lo escrito se lee con la clave que usa la
        lotería (method_id + su thinking_class), no otra."""
        store = TechniqueOutcomeStore(tmp_path / "o.jsonl")
        sheet = {"run_id": "run-atrib", "entries": [_entry_dos_clases()]}
        record_outcomes(sheet, store, canon_version="c")
        # la lotería consulta (method_id, thinking_class): ambos deben tener prior
        p1, n1, _ = store.prior(profile="CRIBA", family="perspectiva",
                                technique_id="lentes_p_001", canon_version="c")
        p2, n2, _ = store.prior(profile="CRIBA", family="ruptura",
                                technique_id="metafora_r_007", canon_version="c")
        assert n1 >= 1 and p1 > 0.0
        assert n2 >= 1 and p2 > 0.0

    def test_tecnicas_tcanon_siguen_registradas(self, tmp_path):
        """Los IDs T-canon del intérprete siguen registrándose (circuito G1)."""
        store = TechniqueOutcomeStore(tmp_path / "o.jsonl")
        entry = _entry_dos_clases()
        entry["aportacion_por_tecnica"] = [{"tecnica": "T059"}]
        sheet = {"run_id": "run-atrib", "entries": [entry]}
        record_outcomes(sheet, store, canon_version="c")
        recs = store._read_valid()
        t_ids = {r["technique_id"] for r in recs if r["channel"] == CHANNEL_VERDICT}
        assert "T059" in t_ids
