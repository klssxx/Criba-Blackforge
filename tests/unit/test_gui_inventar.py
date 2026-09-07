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


def test_inventar_without_problem_shows_error(qapp) -> None:
    win = CribaMainWindow()
    try:
        win.problem = ""
        actions.on_inventar(win)
        assert win.errorBanner.isVisibleTo(win)
        assert "Inventar" in win.errorBannerText.text()
    finally:
        win.close()
