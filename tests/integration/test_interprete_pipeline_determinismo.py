"""Test de integración del determinismo PR-0 con flag ON (usa LocalInterprete).

Verifica el contrato completo: dos runs con misma (query, seed) sobre la MISMA
base de datos producen los mismos IDs deterministas, y la segunda pasada
devuelve status='deduplicated' para las ideas ya registradas.
"""
from __future__ import annotations

import pytest

from criba.constants import FEATURES
from criba.interprete.pipeline import build_interprete_block


@pytest.fixture
def flag_on(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(FEATURES, "interprete_serendipia", True)


def _ideas() -> list[dict]:
    return [
        {"id": "idea-t1",
         "description": "Sistema distribuido donde cada nodo ajusta su umbral local según la carga del vecino.",
         "proposal": "Usar impedancia térmica variable", "family": "f1",
         "causal_axes_changed": ["estructura", "feedback"],
         "genome": {}, "convergence": {"value_score": 0.5}},
        {"id": "idea-t2",
         "description": "Reorganizar el flujo en contracorriente con recirculación controlada y buffer intermedio.",
         "proposal": "Ciclado rápido de material fase", "family": "f2",
         "causal_axes_changed": ["flujo", "estructura"],
         "genome": {}, "convergence": {"value_score": 0.4}},
    ]


def test_flag_on_ids_deterministas_y_dedup(flag_on, tmp_path) -> None:
    from criba.storage import Storage

    db = tmp_path / "criba_test.sqlite3"
    ctx = {"seed": 1234, "database": str(db)}
    r1 = build_interprete_block("reto de prueba determinista", _ideas(), ctx)
    assert r1["applied"] is True
    ids1 = {r["registro"] for r in r1["interpretados"]}
    assert "recorded" in ids1

    # Segunda pasada: misma seed+query+modelo -> mismos IDs -> dedup
    r2 = build_interprete_block("reto de prueba determinista", _ideas(), ctx)
    assert r2["applied"] is True
    ids2 = {r["registro"] for r in r2["interpretados"]}
    assert "recorded" not in ids2, f"PR-0 roto: segunda pasada volvió a grabar {ids2}"
    assert ids2 == {"deduplicated"}, ids2


def test_flag_on_seed_distinta_no_dedup(flag_on, tmp_path) -> None:
    from criba.storage import Storage

    db = tmp_path / "criba_test2.sqlite3"
    r1 = build_interprete_block("reto", _ideas(), {"seed": 1, "database": str(db)})
    r2 = build_interprete_block("reto", _ideas(), {"seed": 2, "database": str(db)})
    assert r1["applied"] and r2["applied"]
    # seeds distintas -> IDs distintos -> la segunda graba de nuevo
    assert any(r["registro"] == "recorded" for r in r2["interpretados"])
