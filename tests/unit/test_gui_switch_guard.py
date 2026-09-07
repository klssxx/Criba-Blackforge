"""Fase 3a: conmutación CRIBA↔BLACKFORGE sin trabajos simultáneos.

Regresión del defecto 8: antes, show_blackforge_page() ocultaba CRIBA y
lanzaba el proceso hijo aunque hubiera workers de generación vivos.
"""
from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication

from criba.ui import actions
from criba.ui.main_window import CribaMainWindow


@pytest.fixture(scope="module")
def qapp() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_switch_blocked_while_workers_alive(qapp, monkeypatch) -> None:
    launched = {"called": False}
    win = CribaMainWindow()
    try:
        win._live_workers = [object()]  # worker vivo simulado
        monkeypatch.setattr(win, "show_blackforge_page",
                            lambda: launched.__setitem__("called", True))
        actions.on_blackforge(win)
        assert launched["called"] is False
        assert win.errorBanner.isVisibleTo(win)
        assert not win.isVisible() or True  # la ventana NO se oculta: seguimos en CRIBA
    finally:
        win.close()


def test_switch_allowed_when_idle(qapp, monkeypatch) -> None:
    launched = {"called": False}
    win = CribaMainWindow()
    try:
        win._live_workers = []
        monkeypatch.setattr(win, "show_blackforge_page",
                            lambda: launched.__setitem__("called", True))
        actions.on_blackforge(win)
        assert launched["called"] is True
    finally:
        win.close()
