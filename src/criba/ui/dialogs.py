"""Diálogos de la pantalla principal (S2 captura, S7 historial, S10 teaser)."""
from __future__ import annotations

import json
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)


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


# ---------------------------------------------------------------------------
# Retro (canal OBSERVED) y memoria — la cadena G1-G3 llevada a la interfaz
# ---------------------------------------------------------------------------
def ask_retro(win: Any) -> dict[str, str] | None:
    """Captura un resultado OBSERVED (dossier/veredicto humano), sin LLM."""
    from PySide6.QtWidgets import QComboBox, QLineEdit

    dlg = QDialog(win)
    dlg.setWindowTitle("Retro — resultado observado (OBSERVED)")
    dlg.setMinimumSize(520, 320)
    lay = QVBoxLayout(dlg)
    lay.setSpacing(win.t.spacing(12))
    title = QLabel("REGISTRAR RESULTADO OBSERVADO")
    title.setObjectName("sectionTitle")
    lay.addWidget(title)
    desc = QLabel("Cierra el circuito de aprendizaje con observación real: "
                  "qué técnica/método produjo qué resultado. Nunca mezclado "
                  "con verdict/judge automáticos.")
    desc.setObjectName("sectionDesc")
    desc.setWordWrap(True)
    lay.addWidget(desc)

    tecnica = QLineEdit()
    tecnica.setPlaceholderText("T059 · o método de lotería (lentes_1_1700_0001)")
    familia = QLineEdit()
    familia.setPlaceholderText("perspectiva · generacion · ruptura · escape")
    resultado = QComboBox()
    resultado.addItems(["positivo", "negativo", "indeterminado"])
    perfil = QComboBox()
    perfil.addItems(["CRIBA", "BLACKFORGE"])
    for label_txt, widget in (("Técnica", tecnica), ("Familia/clase", familia),
                              ("Resultado", resultado), ("Perfil", perfil)):
        row = QHBoxLayout()
        lab = QLabel(label_txt)
        lab.setMinimumWidth(110)
        row.addWidget(lab)
        row.addWidget(widget, 1)
        lay.addLayout(row)

    buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok
                               | QDialogButtonBox.StandardButton.Cancel)
    ok = buttons.button(QDialogButtonBox.StandardButton.Ok)
    ok.setText("Registrar")
    ok.setObjectName("primary")
    cancel = buttons.button(QDialogButtonBox.StandardButton.Cancel)
    cancel.setText("Cancelar")
    cancel.setObjectName("ghost")
    buttons.accepted.connect(dlg.accept)
    buttons.rejected.connect(dlg.reject)
    lay.addWidget(buttons)
    lay.addStretch(1)
    if dlg.exec() != QDialog.DialogCode.Accepted:
        return None
    if not tecnica.text().strip() or not familia.text().strip():
        return None
    return {
        "tecnica": tecnica.text().strip(),
        "familia": familia.text().strip(),
        "resultado": resultado.currentText(),
        "perfil": perfil.currentText(),
    }


def show_outcome_memory(win: Any) -> None:
    """Panel de solo lectura: qué ha aprendido la memoria de outcomes."""
    from PySide6.QtWidgets import QTableWidget, QTableWidgetItem

    from ..intelligence.outcome_store import default_store

    dlg = QDialog(win)
    dlg.setWindowTitle("Memoria de outcomes (solo lectura)")
    dlg.setMinimumSize(760, 480)
    lay = QVBoxLayout(dlg)
    title = QLabel("MEMORIA TÉCNICA → RESULTADO")
    title.setObjectName("sectionTitle")
    lay.addWidget(title)
    rows = default_store().summary()
    desc = QLabel(f"{len(rows)} celdas con observaciones. Ordena el sorteo "
                  "adaptativo (opt-in); esta vista no modifica nada.")
    desc.setObjectName("sectionDesc")
    desc.setWordWrap(True)
    lay.addWidget(desc)
    table = QTableWidget(len(rows), 6)
    table.setHorizontalHeaderLabels(
        ["perfil", "familia", "técnica", "canal", "outcome", "n / valor"])
    table.verticalHeader().setVisible(False)
    table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    for i, r in enumerate(rows):
        cells = (r["profile"], r["family"], r["technique_id"], r["channel"],
                 r["outcome"], f"{r['n']}" + (f" · {r['value']}" if r["value"] is not None else ""))
        for j, text in enumerate(cells):
            table.setItem(i, j, QTableWidgetItem(text))
    table.resizeColumnsToContents()
    lay.addWidget(table, 1)
    close = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
    close.button(QDialogButtonBox.StandardButton.Close).setObjectName("ghost")
    close.rejected.connect(dlg.reject)
    close.accepted.connect(dlg.reject)
    lay.addWidget(close)
    dlg.exec()


# ---------------------------------------------------------------------------
# Técnicas del canon en la interfaz (router + ejecución, mismos servicios CLI)
# ---------------------------------------------------------------------------
def show_tecnicas(win: Any) -> None:
    """Router del canon T001-T130 y ejecución de técnicas IMPLEMENTED.

    Mismos servicios que `criba tecnicas` (CLI): TechniqueRouter para rutar,
    execution.execute_technique para ejecutar — el canon decide ejecutabilidad.
    """
    from PySide6.QtWidgets import QComboBox, QLineEdit, QPushButton, QTextEdit

    from ..intelligence.execution import ExecutionError, execute_technique
    from ..intelligence.registry import TechniqueRegistry
    from ..intelligence.router import TechniqueRouter

    registry = TechniqueRegistry()
    router = TechniqueRouter(registry)
    dlg = QDialog(win)
    dlg.setWindowTitle("Técnicas del canon T001–T130")
    dlg.setMinimumSize(760, 560)
    lay = QVBoxLayout(dlg)
    title = QLabel("RUTAR Y EJECUTAR TÉCNICAS CANÓNICAS")
    title.setObjectName("sectionTitle")
    lay.addWidget(title)
    desc = QLabel(f"Canon {registry.canon_version} · {len(registry.implemented())} "
                  "IMPLEMENTED ejecutables. El canon decide qué puede ejecutarse; "
                  "las PLANNED se muestran como brechas, nunca como capacidad.")
    desc.setObjectName("sectionDesc")
    desc.setWordWrap(True)
    lay.addWidget(desc)

    tarea = QLineEdit()
    tarea.setPlaceholderText("Tarea o problema para rutar (p. ej. análisis morfológico…)")
    lay.addWidget(tarea)
    out = QTextEdit()
    out.setReadOnly(True)
    lay.addWidget(out, 1)

    def _rutar() -> None:
        import json as _json

        text = tarea.text().strip()
        if not text:
            return
        result = router.select(text, max_techniques=8)
        payload = {
            "canon_version": result.canon_version,
            "ejecutables": [{"id": c.id, "nombre": c.technique.name}
                            for c in result.selected],
            "brechas (PLANNED relevantes)": [
                {"id": c.id, "nombre": c.technique.name}
                for c in result.coverage_gaps],
        }
        out.setPlainText(_json.dumps(payload, ensure_ascii=False, indent=2))

    tarea.textChanged.connect(_rutar)

    ejecutar_id = QComboBox()
    for technique in registry.implemented():
        ejecutar_id.addItem(f"{technique.id} · {technique.name}", technique.id)
    problema = QLineEdit()
    problema.setPlaceholderText("Problema/entrada para la técnica ejecutada")
    params_txt = QTextEdit()
    params_txt.setPlaceholderText(
        'Parámetros canónicos JSON (opcional), p. ej.\n'
        '{"dimensions": {"a": ["x", "y"], "b": ["1", "2"]}}')
    params_txt.setMaximumHeight(90)
    btn = QPushButton("Ejecutar técnica")
    btn.setObjectName("primary")

    def _ejecutar() -> None:
        import json as _json

        tid = ejecutar_id.currentData()
        if not tid or not problema.text().strip():
            return
        params: dict = {}
        raw = params_txt.toPlainText().strip()
        if raw:
            try:
                params = _json.loads(raw)
            except ValueError as exc:
                out.setPlainText(f"Error: params JSON inválido — {exc}")
                return
        try:
            outcome = execute_technique(
                registry, tid, problema.text().strip(), params=params)
        except (ExecutionError, ValueError) as exc:
            out.setPlainText(f"Error: {exc}")
            return
  
        out.setPlainText(_json.dumps(outcome, ensure_ascii=False, indent=2))

    btn.clicked.connect(_ejecutar)
    for label_txt, widget in (("Técnica", ejecutar_id), ("Problema", problema)):
        row = QHBoxLayout()
        lab = QLabel(label_txt)
        lab.setMinimumWidth(80)
        row.addWidget(lab)
        row.addWidget(widget, 1)
        lay.addLayout(row)
    lay.addWidget(QLabel("Parámetros (input_contracts de la técnica)"))
    lay.addWidget(params_txt)
    lay.addWidget(btn)
    close = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
    close.button(QDialogButtonBox.StandardButton.Close).setObjectName("ghost")
    close.rejected.connect(dlg.reject)
    close.accepted.connect(dlg.reject)
    lay.addWidget(close)
    dlg.exec()
