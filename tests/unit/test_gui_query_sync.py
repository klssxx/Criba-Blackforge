"""Regression tests for the canonical CRIBA GUI query flow.

Validates the APPROVED interface (ui.main_window.CribaMainWindow) end to end
in offscreen mode: a real query drives generation, evaluation, ranking and
persistence, and the saved session survives a reopen.

The previous version targeted the obsolete ``gui.Window`` "CRIBA Current
Engine" screen, which is no longer the canonical route (see run_legacy).
"""
from __future__ import annotations

import os

import pytest

# The suite is also run on hosts without a desktop session.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest

from criba.storage import Storage
from criba.ui import actions
from criba.ui.main_window import CribaMainWindow


@pytest.fixture(scope="module")
def qapp() -> QApplication:
    return QApplication.instance() or QApplication([])


def _drive_flow(win: CribaMainWindow, query: str, qapp: QApplication) -> str:
    """Exercise the real navigation state machine without modal dialogs."""
    actions.on_nueva_idea_no_dialog(win, query)
    qapp.processEvents()
    assert win.problem == query
    actions.on_generar(win)
    # on_generar runs activate() in a QThreadPool worker; wait for the async
    # done signal to populate win.packet (bounded wait).
    for _ in range(200):
        qapp.processEvents()
        if win.packet is not None:
            break
        QTest.qWait(10)
    assert win.packet is not None
    actions.on_evaluar(win)
    for _ in range(200):
        qapp.processEvents()
        if win.refs["rankingModel"].rowCount() > 0:
            break
        QTest.qWait(10)
    actions.on_guardar(win)
    qapp.processEvents()
    ident = next(iter(win.saved_ids))
    persisted = Storage(win.store.path).get(ident)
    assert persisted is not None
    assert persisted["query"] == query
    return ident


def test_query_drives_full_flow_and_persists(tmp_path, qapp: QApplication) -> None:
    query = "Validar CRIBA con texto Unicode: áβ — proteger API"
    win = CribaMainWindow(tmp_path / "criba.sqlite3")
    try:
        win.show()
        qapp.processEvents()
        _drive_flow(win, query, qapp)
    finally:
        win.close()
        qapp.processEvents()


def test_persisted_session_survives_reopen(tmp_path, qapp: QApplication) -> None:
    query = "Validar BLACKFORGE con Unicode: ñ — red team"
    db = tmp_path / "criba2.sqlite3"
    # First session: generate, evaluate, save.
    win = CribaMainWindow(db)
    try:
        win.show()
        qapp.processEvents()
        _drive_flow(win, query, qapp)
    finally:
        win.close()
        qapp.processEvents()
    # Reopen against the SAME database and confirm the session is present.
    win2 = CribaMainWindow(db)
    try:
        win2.show()
        qapp.processEvents()
        sessions = win2.store.list_sessions(20)
        assert any(s["query"] == query for s in sessions)
    finally:
        win2.close()
        qapp.processEvents()
