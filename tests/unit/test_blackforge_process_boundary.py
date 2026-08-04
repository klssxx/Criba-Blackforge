import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PySide6")
from PySide6.QtWidgets import QApplication

from criba.ui import app_bridge
from criba.ui.main_window import CribaMainWindow


@pytest.fixture(scope="module")
def qt_app():
    app = QApplication.instance() or QApplication([])
    yield app


def test_criba_hides_only_while_blackforge_child_is_running(
    qt_app, monkeypatch, tmp_path: Path
) -> None:
    launch = app_bridge.BlackforgeLaunchSpec(
        program=sys.executable,
        arguments=("-c", "import time; time.sleep(0.15)"),
    )
    monkeypatch.setattr(app_bridge, "resolve_blackforge_launch", lambda: launch)

    window = CribaMainWindow(database=tmp_path / "bridge.sqlite3")
    window.show()
    qt_app.processEvents()
    window.show_blackforge_page()

    process = window._blackforge_process
    assert process is not None
    assert process.waitForStarted(5_000)
    qt_app.processEvents()
    assert not window.isVisible()

    assert process.waitForFinished(5_000)
    qt_app.processEvents()
    assert window.isVisible()
    assert window._blackforge_process is None
    window.close()
