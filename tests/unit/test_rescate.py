"""Tests del rescate de ideas fallidas por complementariedad (propuesta astra).

Contratos que FALSAN un mal diseño:
- Sin evaluador -> UNRESOLVED (nunca se fabrica un rescate).
- RESCUED SOLO si A+B supera a A Y a B con el mismo evaluador.
- NOT_RESCUED si A+B no supera a alguna (misma conducta con explicación larga).
- Puntuación fuera de [0,1] o evaluador que falla -> UNRESOLVED.
- Bloqueo exige condicion+cambio estructurados (no etiqueta vaga).
"""
from __future__ import annotations

import pytest

from criba.rescate import (
    Bloqueo,
    Complemento,
    append_bloqueo,
    bloqueos_hash,
    buscar_complementos,
    probar_rescate,
    read_bloqueos,
)


def _bloqueo() -> Bloqueo:
    return Bloqueo(
        idea_id="idea-a", mecanismo="transmisión continua de telemetría",
        condicion="presupuesto energético",
        cambio="transmitir solo excepciones o calcular localmente",
        evidencia_fallo="pierde 3x el presupuesto",
    )


def _complemento() -> Complemento:
    return Complemento(
        idea_id="idea-b", mecanismo="agregación local con envío por ráfagas",
        transforma="reduce el presupuesto energético",
    )


class TestBloqueo:
    def test_append_y_read_roundtrip(self, tmp_path):
        p = tmp_path / "b.jsonl"
        append_bloqueo(p, _bloqueo())
        got = read_bloqueos(p)
        assert len(got) == 1
        assert got[0].condicion == "presupuesto energético"
        assert got[0].cambio  # cambio estructurado presente

    def test_bloqueo_sin_condicion_rechazado(self, tmp_path):
        p = tmp_path / "b.jsonl"
        with pytest.raises(ValueError, match="condicion"):
            append_bloqueo(p, Bloqueo("i", "m", "", "cambio"))

    def test_hash_estable(self, tmp_path):
        p = tmp_path / "b.jsonl"
        h0 = bloqueos_hash(p)
        append_bloqueo(p, _bloqueo())
        assert bloqueos_hash(p) != h0


class TestProbarRescate:
    def test_sin_evaluador_unresolved(self):
        """Sin prueba que ejecutar: UNRESOLVED, nunca rescate fabricado."""
        v = probar_rescate(_bloqueo(), _complemento(), None)
        assert v.verdict == "UNRESOLVED"
        assert v.score_ab is None

    def test_rescued_solo_si_supera_a_ambas(self):
        """A+B supera a A y a B -> RESCUED."""
        def ev(m: str, ctx: str) -> float:
            if "+" in m:
                return 0.9
            return 0.5 if "transmisión" in m else 0.4
        v = probar_rescate(_bloqueo(), _complemento(), ev)
        assert v.verdict == "RESCUED"
        assert v.score_ab == 0.9 and v.score_ab > v.score_a and v.score_ab > v.score_b

    def test_not_rescued_si_no_supera_a_alguna(self):
        """A+B no supera a A -> NOT_RESCUED (explicación más larga, se descarta)."""
        def ev(m: str, ctx: str) -> float:
            if "+" in m:
                return 0.5  # igual que A
            return 0.5 if "transmisión" in m else 0.4
        v = probar_rescate(_bloqueo(), _complemento(), ev)
        assert v.verdict == "NOT_RESCUED"

    def test_puntuacion_fuera_de_rango_unresolved(self):
        def ev(m: str, ctx: str) -> float:
            return 1.7
        v = probar_rescate(_bloqueo(), _complemento(), ev)
        assert v.verdict == "UNRESOLVED"

    def test_evaluador_que_falla_unresolved(self):
        def ev(m: str, ctx: str) -> float:
            raise RuntimeError("boom")
        v = probar_rescate(_bloqueo(), _complemento(), ev)
        assert v.verdict == "UNRESOLVED"


class TestBuscarComplementos:
    def test_orden_por_score_y_rescued_primero(self):
        def ev(m: str, ctx: str) -> float:
            if "transmisión" in m and "agregación" in m:
                return 0.95  # A+B alto
            if "agregación" in m:
                return 0.4
            return 0.5
        candidatos = [
            Complemento("b1", "agregación local con envío por ráfagas", "reduce energía"),
            Complemento("b2", "otra cosa", "nada"),
        ]
        veredictos = buscar_complementos(_bloqueo(), candidatos, ev)
        assert veredictos[0].verdict == "RESCUED"
        assert veredictos[0].score_ab == 0.95
