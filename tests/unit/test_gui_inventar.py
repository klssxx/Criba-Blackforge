"""Regression test: la acción «Inventar» de la GUI usa el MISMO servicio
(`criba.inventar.invent`) que la CLI `criba inventar` (mandato §5, Fase 1).

El servicio se inyecta vía monkeypatch para no ejecutar el catálogo real ni
escribir el ledger del usuario; el contrato probado es el cableado GUI→servicio
y la presentación honesta de pendientes.
"""
from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from criba import inventar as inventar_mod
from criba.ui import actions
from criba.ui.main_window import CribaMainWindow


@pytest.fixture(scope="module")
def qapp() -> QApplication:
    return QApplication.instance() or QApplication([])


def _sheet_stub(query: str) -> dict:
    return {
        "query": query,
        "seed": 42,
        "mode": "stratified",
        "entries": [
            {
                "candidate_id": "invent-42-test-01",
                "title": "A x B",
                "score": 0.5,
                "score_kind": "heuristica_local",
                "estado_interpretacion": "PENDIENTE_INTERPRETACION",
                "hipotesis": "",
                "mecanismo": "",
                "interpretacion_error": "sin NOUS_API_KEY",
                "prior_art": {
                    "verdict": "UNRESOLVED",
                    "queries": [],
                    "rounds": 0,
                    "mutations": 0,
                    "detail": "sin-mecanismo: interpretación pendiente",
                },
            }
        ],
        "totals": {
            "ideas": 12,
            "pending_interpretation": 1,
            "unresolved": 1,
            "partial_prior_art": 0,
            "survived_search": 0,
        },
    }


def test_inventar_button_runs_shared_service(qapp, tmp_path, monkeypatch) -> None:
    calls: list[str] = []

    def _fake_invent(query: str, **_kw: object) -> dict:
        calls.append(query)
        return _sheet_stub(query)

    monkeypatch.setattr(inventar_mod, "invent", _fake_invent)
    monkeypatch.setattr(
        inventar_mod, "append_ledger",
        lambda sheet, ledger_dir=None: tmp_path / "verdicts.jsonl",
    )

    win = CribaMainWindow()
    try:
        actions.on_nueva_idea_no_dialog(win, "permisos excesivos de un agente")
        qapp.processEvents()
        actions.on_inventar(win)
        # on_inventar corre el servicio en QThreadPool: espera acotada.
        for _ in range(200):
            qapp.processEvents()
            if getattr(win, "invent_sheet", None) is not None:
                break
            QTest.qWait(10)

        assert win.invent_sheet is not None
        assert calls == ["permisos excesivos de un agente"]
        summary = win.refs["ideaSummary"].text()
        assert "1 candidatos" in summary
        assert "interpretación pendiente: 1" in summary
        assert "pendiente" in win.refs["ideaEstadoChip"].text().lower()
        assert "prior-art: UNRESOLVED" in win.invent_sheet["ficha_texto"]
        assert "interpretación PENDIENTE" in win.invent_sheet["ficha_texto"]
        assert win.nav["navInventar"].isEnabled()
    finally:
        win.close()


def test_inventar_passes_default_store_like_cli(qapp, tmp_path, monkeypatch) -> None:
    """Auditoría de la base: la GUI llamaba a invent() sin almacén de
    evidencia — la interpretación desde la interfaz perdía la evidencia
    local que la CLI sí entrega. El cableado debe ser idéntico."""
    kwargs_captured: dict[str, object] = {}

    def _fake_invent(query: str, **kw: object) -> dict:
        kwargs_captured.update(kw)
        return _sheet_stub(query)

    sentinel = object()  # cualquier almacén no-None sirve: el contrato es pasarlo
    monkeypatch.setattr(inventar_mod, "invent", _fake_invent)
    monkeypatch.setattr(
        inventar_mod, "append_ledger",
        lambda sheet, ledger_dir=None: tmp_path / "verdicts.jsonl",
    )
    import criba.intelligence.refresh as refresh_mod
    monkeypatch.setattr(refresh_mod, "default_store", lambda: sentinel)

    win = CribaMainWindow()
    try:
        actions.on_nueva_idea_no_dialog(win, "permisos excesivos de un agente")
        qapp.processEvents()
        actions.on_inventar(win)
        for _ in range(200):
            qapp.processEvents()
            if getattr(win, "invent_sheet", None) is not None:
                break
            QTest.qWait(10)

        assert win.invent_sheet is not None
        assert kwargs_captured.get("store") is sentinel
    finally:
        win.close()


def test_inventar_without_problem_shows_error(qapp) -> None:
    win = CribaMainWindow()
    try:
        win.problem = ""
        actions.on_inventar(win)
        assert win.errorBanner.isVisibleTo(win)
        assert "Inventar" in win.errorBannerText.text()
    finally:
        win.close()


def test_desarrollar_con_supra_prepara_dossier_pendiente(qapp, tmp_path, monkeypatch) -> None:
    """Paridad GUI==CLI: cada candidato PROPUESTA genera un dossier con
    estado SUPRA_EJECUCION_PENDIENTE (nunca PASS). Offscreen."""
    import json

    from criba.supra_dossier import preparar_dossier as _real  # noqa: F401
    import criba.supra_dossier as sd
    from criba.ui import actions

    sheet = _sheet_stub("permisos")
    sheet["entries"][0]["estado_interpretacion"] = "PROPUESTA"
    sheet["entries"][0]["prueba_concreta"] = "medir reutilizaciones rechazadas"
    sheet["ficha_bloqueo"] = {"bloqueo": "permisos reutilizables", "origen_bloqueo": "hipotesis"}

    rutas = []
    monkeypatch.setattr(sd, "guardar_dossier",
                        lambda d, directory=None: (rutas.append(d), tmp_path / "d.jsonl")[1])
    monkeypatch.setattr(sd, "_dossiers_dir", lambda override=None: tmp_path)

    win = CribaMainWindow()
    try:
        win.invent_sheet = sheet
        actions.on_desarrollar_supra(win)
        qapp.processEvents()
        assert sheet["dossiers"] and sheet["dossiers"][0].startswith("dossier-")
        assert "PENDIENTE" in win.refs["ideaSummary"].text().upper()
        dossier_guardado = rutas[0]
        assert dossier_guardado["estado"] == "SUPRA_EJECUCION_PENDIENTE"
        assert dossier_guardado["prueba_discriminante"]["estado_prueba"] == "NO_EJECUTADA"
        assert dossier_guardado["prueba_discriminante"]["afirmacion_decisiva"]
        # sin propuesta no hay dossier y hay aviso honesto
        sheet2 = _sheet_stub("x")
        sheet2["entries"][0]["estado_interpretacion"] = "PENDIENTE_INTERPRETACION"
        win.invent_sheet = sheet2
        win.errorBanner.hide()
        actions.on_desarrollar_supra(win)
        assert win.errorBanner.isVisibleTo(win)
    finally:
        win.close()


def test_desarrollar_supra_sin_sheet_error(qapp) -> None:
    from criba.ui import actions
    win = CribaMainWindow()
    try:
        actions.on_desarrollar_supra(win)
        assert win.errorBanner.isVisibleTo(win)
    finally:
        win.close()
