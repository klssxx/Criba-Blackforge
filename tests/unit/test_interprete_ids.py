"""Tests del determinismo de IDs del interprete-serendipia (PR-0).

Contrato (store.py:13): MISMA comb_id + MISMO seed + MISMO modelo → MISMO veredicto.
Hoy engine.py:1015-1016 genera activation_id/run_id con uuid4(), rompiendo la
deduplicación determinista: misma seed produce SIEMPRE registros nuevos.

PR-0: los IDs se derivan de sha256(query|seed|modelo) → misma seed+query+modelo
produce los mismos IDs y la segunda pasada deduplica.
"""
from __future__ import annotations

import hashlib

from criba.interprete.ids import interprete_ids


def test_ids_deterministas_misma_seed_y_query() -> None:
    a = interprete_ids(query="mejorar disipadores", seed=42, modelo="glm-5.3-flash")
    b = interprete_ids(query="mejorar disipadores", seed=42, modelo="glm-5.3-flash")
    assert a == b


def test_ids_cambian_con_seed() -> None:
    a = interprete_ids(query="q", seed=1, modelo="m")
    b = interprete_ids(query="q", seed=2, modelo="m")
    assert a.activation_id != b.activation_id
    assert a.run_id != b.run_id


def test_ids_cambian_con_query() -> None:
    a = interprete_ids(query="reto A", seed=7, modelo="m")
    b = interprete_ids(query="reto B", seed=7, modelo="m")
    assert a.run_id != b.run_id


def test_ids_cambian_con_modelo() -> None:
    a = interprete_ids(query="q", seed=7, modelo="modelo-1")
    b = interprete_ids(query="q", seed=7, repo="", modelo="modelo-2")
    assert a.run_id != b.run_id


def test_ids_formato_estable() -> None:
    ids = interprete_ids(query="q", seed=0, modelo="m")
    assert ids.activation_id.startswith("interprete-act-") and len(ids.activation_id) == len("interprete-act-") + 12
    assert ids.run_id.startswith("interprete-run-") and len(ids.run_id) == len("interprete-run-") + 12


def test_ids_formato_prefijo_sha256() -> None:
    # El prefijo debe ser derivable manualmente: sha256("q|0|m|")[:12] (repo vacio)
    esperado = hashlib.sha256("q|0|m|".encode("utf-8")).hexdigest()[:12]
    ids = interprete_ids(query="q", seed=0, modelo="m")
    assert ids.run_id.endswith(esperado)


def test_ids_seed_none_diferido_de_seed_cero() -> None:
    # seed None (sin seed) no debe colisionar con seed 0
    a = interprete_ids(query="q", seed=None, modelo="m")
    b = interprete_ids(query="q", seed=0, modelo="m")
    assert a.run_id != b.run_id


def test_ids_diferencia_repo() -> None:
    # repo distinto -> IDs distintos (mismo query, seed, modelo)
    i1 = interprete_ids(query="q", seed=42, modelo="m", repo="")
    i2 = interprete_ids(query="q", seed=42, modelo="m", repo="repo-x")
    assert i1.activation_id != i2.activation_id
    assert i1.run_id != i2.run_id
