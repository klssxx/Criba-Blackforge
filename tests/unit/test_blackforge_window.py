import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PySide6")
from PySide6.QtWidgets import QApplication

from criba.ui.blackforge_window import BlackforgeWindow


@pytest.fixture(scope="module")
def qt_app():
    app = QApplication.instance() or QApplication([])
    yield app


def test_blackforge_is_a_standalone_target_dashboard(qt_app) -> None:
    window = BlackforgeWindow()
    window.resize(1386, 778)
    window.show()
    qt_app.processEvents()

    assert window.parent() is None
    assert window.sidebar.width() == 260
    assert window.topbar.height() == 74
    assert window.back_button.text() == "←"
    assert window.back_button.accessibleName() == "Volver a CRIBA"
    assert tuple(window.nav_buttons) == (
        "home",
        "generation",
        "associative",
        "pure",
        "models",
        "verify",
        "history",
    )
    assert window.ideas_model.rowCount() == 5
    assert window.mode_cards["optimized"].isChecked()
    assert window.centralWidget().objectName() == "blackforgeRoot"
    window.back_button.click()
    qt_app.processEvents()
    assert not window.isVisible()
    window.close()
