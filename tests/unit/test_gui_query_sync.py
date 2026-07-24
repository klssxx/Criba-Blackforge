"""Regression tests for the visible CRIBA query inputs."""
from __future__ import annotations

import os

import pytest

# The suite is also run on hosts without a desktop session.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication

from criba.gui import Window
from criba.storage import Storage


@pytest.fixture(scope="module")
def qapp() -> QApplication:
    return QApplication.instance() or QApplication([])


def _activate(window: Window, query: str, qapp: QApplication) -> None:
    window.show()
    qapp.processEvents()
    window.do_activate()
    qapp.processEvents()
    assert window.packet is not None
    assert window.packet["original_query"] == query
    assert not window.simple_answer.isHidden()
    persisted = Storage(window.store.path).get(window.packet["activation_id"])
    assert persisted["query"] == query


def test_default_visible_query_drives_activation(tmp_path, qapp: QApplication) -> None:
    """The default simple-panel input must be the value executed by the run button."""
    query = "Validar CRIBA desde el panel simple con texto Unicode: áβ"
    window = Window(tmp_path / "simple.sqlite3")
    try:
        window.simple_query.setPlainText(query)
        assert window.advanced_query.toPlainText() == query
        _activate(window, query, qapp)
    finally:
        window.close()
        qapp.processEvents()


def test_advanced_query_stays_synchronized_and_drives_activation(tmp_path, qapp: QApplication) -> None:
    """The advanced editor must remain a functional equivalent of the simple input."""
    query = "Validar BLACKFORGE desde el panel avanzado con texto Unicode: ñ"
    window = Window(tmp_path / "advanced.sqlite3")
    try:
        window.advanced_query.setPlainText(query)
        assert window.simple_query.toPlainText() == query
        _activate(window, query, qapp)
    finally:
        window.close()
        qapp.processEvents()
