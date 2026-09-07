"""Harness benchmark v0 (megaprompt §45-§47): COMPARABILIDAD, no conclusiones.

Condiciones reservadas (misma evidencia/presupuesto cuando se ejecute de verdad):
- A_DIRECT:      prompt mínimo  «Genera N soluciones innovadoras para…»
- B_STRONG_PROMPT: prompt de innovación bien diseñado, sin CRIBA
- C_CRIBA:       mismo modelo vía cruces/selector/evidencia de CRIBA

Este harness v0 NO llama a ningún modelo: `model_fn` es inyectable (stub en
tests/smoke). Con modelo ausente las comparaciones quedan UNAVAILABLE. Un
smoke pequeño prueba funcionamiento, no superioridad (§48). Estudio completo:
DEFERRED_SEPARATE_STUDY.
"""
from __future__ import annotations

import hashlib
import json
import time
import uuid
from pathlib import Path
from typing import Any, Callable

from benchmarks.diversity_measure import measure  # reutiliza métricas del contrato

DIR = Path(__file__).resolve().parent

CONDITIONS: dict[str, dict[str, str]] = {
    "A_DIRECT": {
        "plantilla": "Genera {n} soluciones innovadoras para: {problema}",
    },
    "B_STRONG_PROMPT": {
        "plantilla": (
            "Genera {n} soluciones para: {problema}\n"
            "Requisitos: mecanismo causal explícito, qué supuesto cambias, "
            "respecto de qué solución de referencia, restricciones conservadas, "
            "y una prueba mínima con condición de fracaso."
        ),
    },
    "C_CRIBA": {
        "plantilla": "CRIBA: cruces + selector diversity-aware + evidencia para: {problema}",
    },
}


def _run_id(problema_id: str, condition: str, seed: int) -> str:
    digest = hashlib.sha256(f"{problema_id}|{condition}|{seed}".encode("utf-8")).hexdigest()[:12]
    return f"bench-{digest}"


def run_condition(
    condition: str,
    problema: dict[str, Any],
    *,
    seed: int,
    n_candidatos: int = 3,
    model_fn: Callable[[str], list[dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    """Ejecuta UNA condición sobre UN problema. Sin modelo → UNAVAILABLE."""
    if condition not in CONDITIONS:
        raise ValueError(f"condición desconocida: {condition}")
    prompt = CONDITIONS[condition]["plantilla"].format(
        n=n_candidatos, problema=problema["texto"])
    record: dict[str, Any] = {
        "run_id": uuid.uuid4().hex,
        "bench_run_id": _run_id(problema["id"], condition, seed),
        "problem_id": problema["id"],
        "condition": condition,
        "seed": seed,
        "seed_source": "explicit",
        "prompt": prompt,
        "candidates": [],
        "metrics": None,
        "status": "UNAVAILABLE",
        "nota": "sin modelo configurado: comparación no ejecutada",
    }
    started = time.monotonic()
    if model_fn is not None:
        candidates = model_fn(prompt)
        for c in candidates:
            c.setdefault("genome", {})
        record["candidates"] = candidates
        record["metrics"] = measure(candidates[:n_candidatos], candidates)
        record["status"] = "OK"
        record["latencia_s"] = round(time.monotonic() - started, 3)
    return record


def run_smoke(model_fn: Callable[[str], list[dict[str, Any]]] | None = None,
              *, seed: int = 7) -> dict[str, Any]:
    """Smoke ≤10 problemas × todas las condiciones. Funcionalidad, no ciencia."""
    data = json.loads((DIR / "problems_smoke.json").read_text(encoding="utf-8"))
    runs = [run_condition(cond, p, seed=seed, model_fn=model_fn)
            for p in data["problemas"] for cond in CONDITIONS]
    return {
        "dataset": data["version"],
        "n_problemas": len(data["problemas"]),
        "conditions": list(CONDITIONS),
        "runs": runs,
        "advertencia": "smoke funcional; NO concluye superioridad (§53)",
        "generado_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


def exportar(report: dict[str, Any], out: Path) -> Path:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return out
