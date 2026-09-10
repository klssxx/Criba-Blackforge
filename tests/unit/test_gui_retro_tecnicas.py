"""La cadena G1-G3 (retro OBSERVED + memoria) y las técnicas del canon
T001-T130 son ACCESIBLES desde la interfaz — mismos servicios que la CLI,
sin duplicar lógica. Verifica el wiring y el comportamiento honesto."""
from __future__ import annotations

import json
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication

from criba import cli as cli_mod
from criba.ui import actions


@pytest.fixture(scope="module")
def qapp() -> QApplication:
    return QApplication.instance() or QApplication([])


class _RecordingStore:
    def __init__(self) -> None:
        self.records: list[dict] = []

    def record(self, **kw: object) -> dict:
        self.records.append(dict(kw))
        return {"ok": True}

    def summary(self, **kw: object) -> list[dict]:
        return [{"profile": "CRIBA", "family": "generacion",
                 "technique_id": "T059", "channel": "OBSERVED",
                 "outcome": "positivo", "n": 2, "value": None}]


def test_retro_registra_observed_por_el_canal_correcto(qapp, monkeypatch) -> None:
    """on_retro usa CHANNEL_OBSERVED y normaliza el ID del canon (t059→T059)."""
    from criba.intelligence import outcome_store as os_mod

    store = _RecordingStore()
    monkeypatch.setattr(os_mod, "default_store", lambda: store)

    actions._register_retro_for_test(  # ruta de trabajo separada del diálogo
        qapp, tecnica="t059", familia="generacion", resultado="positivo",
        perfil="CRIBA",
    )
    assert len(store.records) == 1
    rec = store.records[0]
    assert rec["technique_id"] == "T059"  # normalizado al canon
    assert rec["channel"] == os_mod.CHANNEL_OBSERVED
    assert rec["outcome"] == "positivo"
    assert rec["canon_version"]  # arrastra el canon vigente


def test_retro_rechaza_campos_vacios_sin_escribir(qapp, monkeypatch) -> None:
    from criba.intelligence import outcome_store as os_mod

    store = _RecordingStore()
    monkeypatch.setattr(os_mod, "default_store", lambda: store)
    with pytest.raises(ValueError):
        actions._register_retro_for_test(
            qapp, tecnica="  ", familia="generacion", resultado="positivo",
            perfil="CRIBA",
        )
    assert store.records == []


def test_memoria_muestra_summary_sin_modificar(qapp, monkeypatch, capsys) -> None:
    from criba.intelligence import outcome_store as os_mod

    store = _RecordingStore()
    monkeypatch.setattr(os_mod, "default_store", lambda: store)
    rows = actions._memory_rows_for_test(qapp)
    assert rows and rows[0]["technique_id"] == "T059"


def test_tecnicas_ejecuta_desde_la_interfaz(qapp) -> None:
    """Ejecutar T059 desde la UI usa el MISMO execute_technique que la CLI:
    salida con trazabilidad de operador."""
    outcome = actions._run_technique_for_test(
        qapp, technique_id="T059", problem="vehículo urbano",
        params={"dimensions": {"motor": ["eléctrico"], "freno": ["regenerativo"]}},
    )
    assert outcome["technique"] == "T059"
    assert outcome["results"]
    assert all("T059" in c["operators"] for c in outcome["results"])


def test_tecnicas_rechaza_planned_desde_la_interfaz(qapp) -> None:
    """El canon decide ejecutabilidad también en la GUI: T130 PLANNED → error."""
    from criba.intelligence.execution import ExecutionError

    with pytest.raises(ExecutionError, match="PLANNED"):
        actions._run_technique_for_test(
            qapp, technique_id="T130", problem="curvas", params={},
        )


def test_retro_cli_normalizador_compartido() -> None:
    """GUI y CLI comparten _normalize_tecnica_id (un solo normalizador)."""
    assert cli_mod._normalize_tecnica_id("t059") == "T059"
    assert cli_mod._normalize_tecnica_id("lentes_1_1700_0001") == "lentes_1_1700_0001"
