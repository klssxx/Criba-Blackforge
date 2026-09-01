import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PySide6")
from PySide6.QtWidgets import QApplication

from criba.ui.blackforge_screen import BlackforgeScreen
from criba.ui.blackforge_window import BlackforgeWindow


@pytest.fixture(scope="module")
def qt_app():
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture(autouse=True)
def isolated_model_config(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("CRIBA_MODEL_CONFIG", str(tmp_path / "models.json"))


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
        "workbench",
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


def test_standalone_blackforge_reuses_engine_and_dispatches_all_modes(qt_app) -> None:
    window = BlackforgeWindow()
    seen: set[str] = set()
    engine = None

    for mode in ("optimized", "associative", "pure"):
        window._select_mode(mode)
        window._run_generation()
        current = window._lottery_engine
        engine = engine or current
        assert current is engine
        stats = current.round_history[-1]
        assert stats["mode"] == mode
        selected = set(stats["method_ids"])
        assert selected.isdisjoint(seen)
        seen.update(selected)

    window.close()


def test_embedded_blackforge_reuses_engine_and_dispatches_all_modes(qt_app) -> None:
    class Host:
        def show_criba_page(self) -> None:
            pass

    screen = BlackforgeScreen(Host())
    seen: set[str] = set()
    engine = None

    for ui_mode, engine_mode in (
        ("optimizado", "optimized"),
        ("asociativa", "associative"),
        ("pura", "pure"),
    ):
        screen._select_mode(ui_mode)
        screen._do_execute()
        current = screen._lottery_engine
        engine = engine or current
        assert current is engine
        stats = current.round_history[-1]
        assert stats["mode"] == engine_mode
        selected = set(stats["method_ids"])
        assert selected.isdisjoint(seen)
        seen.update(selected)

    screen.close()
