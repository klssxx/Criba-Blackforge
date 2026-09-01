"""Shared Modelos IA dialog for the CRIBA and BLACKFORGE desktops."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, QThreadPool, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ..model_config import (
    ModelProfile,
    load_model_settings,
    save_model_settings,
)
from ..model_runtime import test_model_profile
from .actions import Worker, _start_worker


class ModelSettingsDialog(QDialog):
    """Edit, test and activate local GGUF/Ollama profiles."""

    settings_saved = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.settings = load_model_settings()
        self.pool = QThreadPool.globalInstance()
        self._loading = False
        self._current_profile_id = ""
        self.setWindowTitle("CRIBA · Modelos IA")
        self.setMinimumSize(900, 640)
        self.resize(980, 690)
        self.setModal(True)
        self._build_ui()
        self._populate_profiles()
        self.setStyleSheet(
            "QDialog { background:#101722; color:#e9f1fb; }"
            "QFrame#modelPanel { background:#151f2d; border:1px solid #2b3c51; "
            "border-radius:10px; }"
            "QLabel#modelTitle { font-size:22px; font-weight:700; color:#eef8ff; }"
            "QLabel#modelHint { color:#99abc0; }"
            "QLabel#modelStatus { color:#67d9ff; padding:8px; }"
            "QLineEdit,QComboBox,QSpinBox,QDoubleSpinBox,QListWidget { "
            "background:#0c131d; color:#eef6ff; border:1px solid #344a63; "
            "border-radius:6px; padding:6px; min-height:24px; }"
            "QLineEdit:focus,QComboBox:focus,QListWidget:focus { border-color:#28c8f6; }"
            "QPushButton { background:#24364a; color:#f3f8ff; border:1px solid #3c5874; "
            "border-radius:6px; padding:8px 13px; }"
            "QPushButton:hover { border-color:#28c8f6; }"
            "QPushButton#primaryModelButton { background:#087ca8; border-color:#31d2ff; "
            "font-weight:700; }"
        )

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(22, 20, 22, 18)
        root.setSpacing(14)

        title = QLabel("Modelos IA")
        title.setObjectName("modelTitle")
        hint = QLabel(
            "Añade perfiles GGUF mediante llama.cpp u Ollama. CRIBA conserva el motor "
            "determinista y usa el modelo solo para redactar ideas coherentes."
        )
        hint.setObjectName("modelHint")
        hint.setWordWrap(True)
        root.addWidget(title)
        root.addWidget(hint)

        self.use_model = QCheckBox(
            "Usar el perfil activo al pulsar Generar en CRIBA o Ejecutar en BLACKFORGE"
        )
        root.addWidget(self.use_model)

        body = QHBoxLayout()
        body.setSpacing(14)
        profiles_panel = QFrame()
        profiles_panel.setObjectName("modelPanel")
        profiles_panel.setFixedWidth(250)
        profiles_layout = QVBoxLayout(profiles_panel)
        profiles_layout.setContentsMargins(12, 12, 12, 12)
        profiles_layout.addWidget(QLabel("PERFILES"))
        self.profile_list = QListWidget()
        self.profile_list.currentItemChanged.connect(self._on_profile_changed)
        profiles_layout.addWidget(self.profile_list, 1)
        profile_buttons = QHBoxLayout()
        add_button = QPushButton("＋ Añadir")
        add_button.clicked.connect(self._add_profile)
        remove_button = QPushButton("Eliminar")
        remove_button.clicked.connect(self._remove_profile)
        profile_buttons.addWidget(add_button)
        profile_buttons.addWidget(remove_button)
        profiles_layout.addLayout(profile_buttons)
        body.addWidget(profiles_panel)

        editor_panel = QFrame()
        editor_panel.setObjectName("modelPanel")
        editor_layout = QVBoxLayout(editor_panel)
        editor_layout.setContentsMargins(18, 16, 18, 14)
        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.name_edit = QLineEdit()
        form.addRow("Nombre del perfil", self.name_edit)

        self.backend_combo = QComboBox()
        self.backend_combo.addItem("GGUF local · llama.cpp", "llama_cpp")
        self.backend_combo.addItem("Ollama local", "ollama")
        self.backend_combo.currentIndexChanged.connect(self._update_backend_fields)
        form.addRow("Runtime", self.backend_combo)

        self.model_edit = QLineEdit()
        self.model_edit.setPlaceholderText("criba-local o qwen3:8b")
        form.addRow("Modelo / alias", self.model_edit)

        self.endpoint_edit = QLineEdit()
        self.endpoint_edit.setPlaceholderText("http://127.0.0.1:8080")
        form.addRow("Endpoint local", self.endpoint_edit)

        self.gguf_row = self._path_picker(
            "Seleccionar un archivo GGUF", "Modelos GGUF (*.gguf);;Todos (*.*)", "gguf"
        )
        form.addRow("Archivo .gguf", self.gguf_row)

        self.server_row = self._path_picker(
            "Seleccionar llama-server.exe",
            "llama-server (llama-server.exe);;Ejecutables (*.exe);;Todos (*.*)",
            "server",
        )
        form.addRow("llama-server", self.server_row)

        self.auto_start = QCheckBox(
            "Iniciar llama-server automáticamente si no responde"
        )
        form.addRow("Autoarranque", self.auto_start)

        self.reasoning_combo = QComboBox()
        self.reasoning_combo.addItem("Rápido · respuesta directa", "fast")
        self.reasoning_combo.addItem("Equilibrado · análisis interno", "balanced")
        self.reasoning_combo.addItem("Profundo · análisis + segunda revisión", "deep")
        form.addRow("Reasoning", self.reasoning_combo)

        self.context_spin = QSpinBox()
        self.context_spin.setRange(2048, 131072)
        self.context_spin.setSingleStep(1024)
        self.context_spin.setSuffix(" tokens")
        form.addRow("Contexto", self.context_spin)

        self.gpu_spin = QSpinBox()
        self.gpu_spin.setRange(-1, 999)
        self.gpu_spin.setSpecialValueText("Automático")
        form.addRow("Capas GPU", self.gpu_spin)

        self.temperature_spin = QDoubleSpinBox()
        self.temperature_spin.setRange(0.0, 1.5)
        self.temperature_spin.setSingleStep(0.05)
        self.temperature_spin.setDecimals(2)
        form.addRow("Temperatura", self.temperature_spin)

        self.output_spin = QSpinBox()
        self.output_spin.setRange(256, 16384)
        self.output_spin.setSingleStep(256)
        self.output_spin.setSuffix(" tokens")
        form.addRow("Salida máxima", self.output_spin)

        editor_layout.addLayout(form)
        self.status_label = QLabel("Configura un perfil y prueba la conexión.")
        self.status_label.setObjectName("modelStatus")
        self.status_label.setWordWrap(True)
        editor_layout.addWidget(self.status_label)
        editor_layout.addStretch(1)
        body.addWidget(editor_panel, 1)
        root.addLayout(body, 1)

        footer = QHBoxLayout()
        test_button = QPushButton("Probar / iniciar modelo")
        test_button.clicked.connect(self._test_profile)
        self.test_button = test_button
        footer.addWidget(test_button)
        footer.addStretch(1)
        close_button = QPushButton("Cerrar")
        close_button.clicked.connect(self.reject)
        save_button = QPushButton("Guardar configuración")
        save_button.setObjectName("primaryModelButton")
        save_button.clicked.connect(self._save)
        footer.addWidget(close_button)
        footer.addWidget(save_button)
        root.addLayout(footer)

    def _path_picker(self, title: str, file_filter: str, kind: str) -> QWidget:
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        line = QLineEdit()
        button = QPushButton("Examinar…")
        button.clicked.connect(
            lambda checked=False, target=line: self._browse_path(
                target, title, file_filter
            )
        )
        layout.addWidget(line, 1)
        layout.addWidget(button)
        if kind == "gguf":
            self.gguf_edit = line
        else:
            self.server_edit = line
        return container

    def _browse_path(self, target: QLineEdit, title: str, file_filter: str) -> None:
        initial = target.text().strip()
        if initial and Path(initial).is_file():
            initial = str(Path(initial).parent)
        selected, _ = QFileDialog.getOpenFileName(self, title, initial, file_filter)
        if selected:
            target.setText(selected)

    def _populate_profiles(self) -> None:
        self._loading = True
        self.use_model.setChecked(self.settings.enabled)
        self.profile_list.clear()
        active_row = 0
        for row, profile in enumerate(self.settings.profiles):
            item = QListWidgetItem(profile.name)
            item.setData(Qt.ItemDataRole.UserRole, profile.id)
            self.profile_list.addItem(item)
            if profile.id == self.settings.active_profile_id:
                active_row = row
        self._loading = False
        self.profile_list.setCurrentRow(active_row)

    def _profile_by_id(self, profile_id: str) -> ModelProfile | None:
        return next(
            (profile for profile in self.settings.profiles if profile.id == profile_id),
            None,
        )

    def _on_profile_changed(
        self, current: QListWidgetItem | None, previous: QListWidgetItem | None
    ) -> None:
        if self._loading:
            return
        if previous is not None and self._current_profile_id:
            self._store_form(self._profile_by_id(self._current_profile_id))
        if current is None:
            return
        profile_id = str(current.data(Qt.ItemDataRole.UserRole) or "")
        profile = self._profile_by_id(profile_id)
        if profile is not None:
            self._current_profile_id = profile.id
            self.settings.active_profile_id = profile.id
            self._load_form(profile)

    def _load_form(self, profile: ModelProfile) -> None:
        self._loading = True
        self.name_edit.setText(profile.name)
        self.backend_combo.setCurrentIndex(
            max(0, self.backend_combo.findData(profile.backend))
        )
        self.model_edit.setText(profile.model)
        self.endpoint_edit.setText(profile.endpoint)
        self.gguf_edit.setText(profile.gguf_path)
        self.server_edit.setText(profile.server_path)
        self.auto_start.setChecked(profile.auto_start)
        self.reasoning_combo.setCurrentIndex(
            max(0, self.reasoning_combo.findData(profile.reasoning))
        )
        self.context_spin.setValue(profile.context_size)
        self.gpu_spin.setValue(profile.gpu_layers)
        self.temperature_spin.setValue(profile.temperature)
        self.output_spin.setValue(profile.max_output_tokens)
        self._loading = False
        self._update_backend_fields()

    def _store_form(self, profile: ModelProfile | None) -> None:
        if profile is None or self._loading:
            return
        profile.name = self.name_edit.text().strip() or "Modelo local"
        profile.backend = str(self.backend_combo.currentData() or "llama_cpp")  # type: ignore[assignment]
        profile.model = self.model_edit.text().strip() or "criba-local"
        profile.endpoint = self.endpoint_edit.text().strip().rstrip("/")
        profile.gguf_path = self.gguf_edit.text().strip()
        profile.server_path = self.server_edit.text().strip()
        profile.auto_start = self.auto_start.isChecked()
        profile.reasoning = str(self.reasoning_combo.currentData() or "balanced")  # type: ignore[assignment]
        profile.context_size = self.context_spin.value()
        profile.gpu_layers = self.gpu_spin.value()
        profile.temperature = self.temperature_spin.value()
        profile.max_output_tokens = self.output_spin.value()
        item = self.profile_list.currentItem()
        if item is not None:
            item.setText(profile.name)

    def _update_backend_fields(self) -> None:
        if not hasattr(self, "gguf_row"):
            return
        llama_cpp = self.backend_combo.currentData() == "llama_cpp"
        self.gguf_row.setEnabled(llama_cpp)
        self.server_row.setEnabled(llama_cpp)
        self.auto_start.setEnabled(llama_cpp)
        if not self._loading:
            expected = (
                "http://127.0.0.1:8080" if llama_cpp else "http://127.0.0.1:11434"
            )
            previous_default = (
                "http://127.0.0.1:11434" if llama_cpp else "http://127.0.0.1:8080"
            )
            self.endpoint_edit.setPlaceholderText(expected)
            if self.endpoint_edit.text().strip() in {"", previous_default}:
                self.endpoint_edit.setText(expected)

    def _add_profile(self) -> None:
        self._store_form(self._profile_by_id(self._current_profile_id))
        profile = ModelProfile(
            id=str(uuid.uuid4()),
            name=f"Modelo local {len(self.settings.profiles) + 1}",
        )
        self.settings.profiles.append(profile)
        item = QListWidgetItem(profile.name)
        item.setData(Qt.ItemDataRole.UserRole, profile.id)
        self.profile_list.addItem(item)
        self.profile_list.setCurrentItem(item)

    def _remove_profile(self) -> None:
        if len(self.settings.profiles) <= 1:
            QMessageBox.information(
                self, "Modelos IA", "Debe existir al menos un perfil."
            )
            return
        item = self.profile_list.currentItem()
        if item is None:
            return
        profile_id = str(item.data(Qt.ItemDataRole.UserRole) or "")
        self.settings.profiles = [
            p for p in self.settings.profiles if p.id != profile_id
        ]
        row = self.profile_list.row(item)
        self._current_profile_id = ""
        self.profile_list.takeItem(row)
        self.profile_list.setCurrentRow(max(0, row - 1))

    def _test_profile(self) -> None:
        profile = self._profile_by_id(self._current_profile_id)
        self._store_form(profile)
        if profile is None:
            return
        self.test_button.setEnabled(False)
        self.status_label.setText(
            "Comprobando el runtime y cargando el GGUF si es necesario…"
        )
        worker = Worker(lambda: test_model_profile(profile, start=True))
        worker.signals.done.connect(self._on_test_ok)
        worker.signals.fail.connect(self._on_test_error)
        _start_worker(self, worker)

    def _on_test_ok(self, result: Any) -> None:
        self.test_button.setEnabled(True)
        self.status_label.setText(f"✓ {result}")

    def _on_test_error(self, message: str) -> None:
        self.test_button.setEnabled(True)
        first_line = message.splitlines()[0]
        self.status_label.setText(f"✕ {first_line}")

    def _save(self) -> None:
        profile = self._profile_by_id(self._current_profile_id)
        self._store_form(profile)
        self.settings.enabled = self.use_model.isChecked()
        if profile is not None:
            self.settings.active_profile_id = profile.id
        try:
            destination = save_model_settings(self.settings)
        except OSError as exc:
            QMessageBox.warning(self, "Modelos IA", f"No se pudo guardar:\n{exc}")
            return
        self.status_label.setText(f"✓ Configuración guardada en {destination}")
        self.settings_saved.emit()
        self.accept()


def open_model_settings(parent: QWidget | None = None) -> bool:
    """Open the shared settings dialog and return whether it was saved."""

    dialog = ModelSettingsDialog(parent)
    return dialog.exec() == QDialog.DialogCode.Accepted
