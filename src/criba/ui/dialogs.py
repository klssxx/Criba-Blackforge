"""Diálogos de la pantalla principal (S2 captura, S7 historial, S10 teaser)."""
from __future__ import annotations

import json
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDialog, QDialogButtonBox, QHBoxLayout, QLabel,
                               QListWidget, QListWidgetItem, QPushButton,
                               QTextEdit, QVBoxLayout)


def ask_problem(win: Any) -> str | None:
    """Captura del problema base (botón 1, Nueva idea)."""
    dlg = QDialog(win)
    dlg.setWindowTitle("Nueva idea — Problema base")
    dlg.setMinimumSize(560, 300)
    lay = QVBoxLayout(dlg)
    lay.setSpacing(win.t.spacing(12))
    title = QLabel("DEFINE EL PROBLEMA BASE")
    title.setObjectName("sectionTitle")
    lay.addWidget(title)
    desc = QLabel("Describe el reto central a resolver. El motor generará "
                  "ideas con los 16 operadores sobre este problema.")
    desc.setObjectName("sectionDesc")
    desc.setWordWrap(True)
    lay.addWidget(desc)
    editor = QTextEdit()
    editor.setPlaceholderText("Ej.: Reducir el tiempo de auditoría de "
                              "dependencias sin añadir servicios externos…")
    lay.addWidget(editor, 1)
    buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok
                               | QDialogButtonBox.StandardButton.Cancel)
    ok = buttons.button(QDialogButtonBox.StandardButton.Ok)
    ok.setText("Definir problema")
    ok.setObjectName("primary")
    cancel = buttons.button(QDialogButtonBox.StandardButton.Cancel)
    cancel.setText("Cancelar")
    cancel.setObjectName("ghost")
    buttons.accepted.connect(dlg.accept)
    buttons.rejected.connect(dlg.reject)
    lay.addWidget(buttons)
    if dlg.exec() != QDialog.DialogCode.Accepted:
        return None
    text = editor.toPlainText().strip()
    return text or None


def show_history(win: Any) -> dict[str, Any] | None:
    """S7: diálogo modal 80% con sesiones; devuelve sesión a cargar o None."""
    sessions = win.store.list_sessions(50)
    dlg = QDialog(win)
    dlg.setWindowTitle("Historial de ideas")
    dlg.resize(int(win.width() * 0.8), int(win.height() * 0.8))
    lay = QVBoxLayout(dlg)
    lay.setSpacing(win.t.spacing(12))
    title = QLabel("HISTORIAL")
    title.setObjectName("sectionTitle")
    lay.addWidget(title)
    result: dict[str, Any] = {}
    if not sessions:
        empty = QLabel("Aún no hay ideas guardadas.\n"
                       "Genera, evalúa y guarda tu primera idea para verla aquí.")
        empty.setObjectName("sectionDesc")
        empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(empty, 1)
    else:
        lst = QListWidget()
        for s in sessions:
            label = (f"{s['created_at'][:16].replace('T', ' ')}   ·   "
                     f"{s['query'][:70]}   ·   {s['status']}")
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, s["id"])
            lst.addItem(item)
        lay.addWidget(lst, 1)
        row = QHBoxLayout()
        load_btn = QPushButton("Cargar como idea activa")
        load_btn.setObjectName("primary")
        load_btn.setEnabled(False)
        lst.itemSelectionChanged.connect(
            lambda: load_btn.setEnabled(bool(lst.selectedItems())))

        def _load() -> None:
            item = lst.currentItem()
            if item is None:
                return
            try:
                session = win.store.get(item.data(Qt.ItemDataRole.UserRole))
            except ValueError:
                return
            result["packet"] = session["packet"]
            dlg.accept()

        load_btn.clicked.connect(_load)
        lst.itemDoubleClicked.connect(lambda _i: _load())
        row.addStretch(1)
        row.addWidget(load_btn)
        lay.addLayout(row)
    close_btn = QPushButton("Cerrar")
    close_btn.setObjectName("ghost")
    close_btn.clicked.connect(dlg.reject)
    lay.addWidget(close_btn, 0, Qt.AlignmentFlag.AlignRight)
    dlg.exec()
    return result if result else None


def show_blackforge_info(win: Any) -> None:
    """S10: el modo Blackforge completo es pantalla aparte (fase posterior)."""
    dlg = QDialog(win)
    dlg.setWindowTitle("BLACKFORGE")
    dlg.setMinimumWidth(420)
    lay = QVBoxLayout(dlg)
    lay.setSpacing(win.t.spacing(12))
    title = QLabel("BLACKFORGE")
    title.setObjectName("bfMiniLogo")
    lay.addWidget(title)
    msg = QLabel("El módulo de ciberseguridad se activará en una fase "
                 "posterior.\n\nMientras tanto, el pipeline determinista de "
                 "Blackforge está disponible por CLI:\n"
                 "criba blackforge --help")
    msg.setObjectName("sectionDesc")
    msg.setWordWrap(True)
    lay.addWidget(msg)
    ok = QPushButton("Entendido")
    ok.setObjectName("primary")
    ok.clicked.connect(dlg.accept)
    lay.addWidget(ok, 0, Qt.AlignmentFlag.AlignRight)
    dlg.exec()


def show_packet_json(win: Any) -> None:
    if not win.packet:
        return
    dlg = QDialog(win)
    dlg.setWindowTitle("Paquete completo (JSON)")
    dlg.resize(760, 560)
    lay = QVBoxLayout(dlg)
    view = QTextEdit()
    view.setReadOnly(True)
    view.setPlainText(json.dumps(win.packet, ensure_ascii=False, indent=2))
    lay.addWidget(view)
    dlg.exec()
