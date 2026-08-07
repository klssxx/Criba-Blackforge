from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication

from criba.model_config import load_model_settings
from criba.ui.model_settings_dialog import ModelSettingsDialog


@pytest.fixture(scope="module")
def qt_app() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_model_dialog_switches_runtime_defaults_and_persists(
    tmp_path, monkeypatch, qt_app: QApplication
) -> None:
    target = tmp_path / "models.json"
    monkeypatch.setenv("CRIBA_MODEL_CONFIG", str(target))
    dialog = ModelSettingsDialog()
    try:
        dialog.show()
        qt_app.processEvents()
        assert dialog.endpoint_edit.text() == "http://127.0.0.1:8080"

        dialog.backend_combo.setCurrentIndex(dialog.backend_combo.findData("ollama"))
        assert dialog.endpoint_edit.text() == "http://127.0.0.1:11434"
        assert not dialog.gguf_row.isEnabled()
        assert not dialog.server_row.isEnabled()

        dialog.name_edit.setText("Ollama para CRIBA")
        dialog.model_edit.setText("qwen3:4b")
        dialog.use_model.setChecked(True)
        dialog._save()
    finally:
        dialog.close()

    loaded = load_model_settings(target)
    profile = loaded.active_profile()
    assert loaded.enabled
    assert profile is not None
    assert profile.name == "Ollama para CRIBA"
    assert profile.backend == "ollama"
    assert profile.endpoint == "http://127.0.0.1:11434"
    assert profile.model == "qwen3:4b"
