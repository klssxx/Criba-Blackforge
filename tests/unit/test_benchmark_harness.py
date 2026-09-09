"""Tests del harness benchmark (hallazgo 6): C_CRIBA ejecuta CRIBA real y la
semilla se propaga. FALSAN el defecto original (C_CRIBA = solo texto de prompt,
semilla sin llegar al callback)."""
from __future__ import annotations

from benchmarks.innovation.criba_adapter import criba_fn
from benchmarks.innovation.harness import run_condition

_PROBLEMA = {"id": "p1", "texto": "reducir consumo energético de sensores"}


class TestSemillaPropagada:
    def test_model_fn_recibe_semilla(self):
        """El callback recibe la semilla (reproducibilidad de la condición)."""
        recibidas: list[int] = []

        def model_fn(prompt: str, seed: int) -> list[dict]:
            recibidas.append(seed)
            return [{"idea_id": "m0", "title": "x", "genome": {}}]

        run_condition("A_DIRECT", _PROBLEMA, seed=42, model_fn=model_fn)
        assert recibidas and recibidas[0] == 42

    def test_model_fn_un_argumento_compat(self):
        """Un stub de un solo argumento sigue funcionando (degradación)."""
        def model_fn(prompt: str) -> list[dict]:
            return [{"idea_id": "m0", "title": "x", "genome": {}}]
        r = run_condition("A_DIRECT", _PROBLEMA, seed=42, model_fn=model_fn)
        assert r["status"] == "OK"


class TestCribaReal:
    def test_c_criba_sin_criba_fn_unavailable(self):
        """Sin criba_fn, C_CRIBA es UNAVAILABLE honesto (nunca prompt de texto)."""
        r = run_condition("C_CRIBA", _PROBLEMA, seed=42)
        assert r["status"] == "UNAVAILABLE"
        assert "criba_fn" in r["nota"]

    def test_c_criba_con_criba_fn_ejecuta_loop(self):
        """Con criba_fn, C_CRIBA ejecuta el loop real y devuelve candidatos."""
        r = run_condition("C_CRIBA", _PROBLEMA, seed=42, criba_fn=criba_fn)
        assert r["status"] == "OK"
        assert r["nota"] == "loop CRIBA real ejecutado via criba_fn"
        assert r["candidates"], "debe producir candidatos estructurados"
        assert r["metrics"] is not None

    def test_c_criba_reproducible_por_semilla(self):
        """Misma semilla => mismos candidatos (la condición es reproducible)."""
        a = run_condition("C_CRIBA", _PROBLEMA, seed=42, criba_fn=criba_fn)
        b = run_condition("C_CRIBA", _PROBLEMA, seed=42, criba_fn=criba_fn)
        titles_a = [c["title"] for c in a["candidates"]]
        titles_b = [c["title"] for c in b["candidates"]]
        assert titles_a == titles_b and titles_a, (
            "C_CRIBA debe ser reproducible por semilla"
        )

    def test_c_criba_no_es_un_prompt_de_texto(self):
        """El defecto original: C_CRIBA solo cambiaba el prompt. Ahora ejecuta
        el loop; el 'prompt' queda documental pero la fuente es criba_fn."""
        r = run_condition("C_CRIBA", _PROBLEMA, seed=42, criba_fn=criba_fn)
        # los candidatos vienen del loop (tienen methods/classes), no del texto
        for c in r["candidates"]:
            assert "methods" in c or "classes" in c, (
                "candidato sin estructura de cruce: sería prosa de prompt, no CRIBA"
            )
