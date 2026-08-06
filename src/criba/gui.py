"""PySide6 desktop client. No secrets or provider credentials are stored.

Premium three-column layout (navigation sidebar + central workbench + summary
panel) and a status footer, matching the CRIBA Current Engine reference design.
"""
from __future__ import annotations
import json, os, sys
from datetime import datetime
from .catalog import currents, methods
from .engine import activate, build_prompt
from .storage import Storage

try:
    from PySide6.QtCore import QTimer, Qt
    from PySide6.QtWidgets import (QApplication, QComboBox, QFrame, QGridLayout,
        QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMainWindow,
        QMessageBox, QPushButton, QScrollArea, QSizePolicy, QSpinBox, QStackedWidget,
        QTextEdit, QVBoxLayout, QWidget, QProgressBar)
except ImportError:
    QApplication = None  # gui.run() will report the missing dependency

# ----- palette (reference design) -----
BG        = "#0b1220"
BG_PANEL  = "#0f1b2e"
BG_CARD   = "#13233c"
BORDER    = "#23436e"
ACCENT    = "#3B82F6"
ACCENT_2  = "#8B5CF6"
GREEN     = "#10B981"
AMBER     = "#F59E0B"
RED       = "#EF4444"
TEXT      = "#e6edf8"
TEXT_DIM  = "#94a3b8"
FONT      = "Segoe UI"

GLOBAL_CSS = f"""
QMainWindow,QWidget{{background:{BG};color:{TEXT};font-family:'{FONT}';font-size:13px}}
QLabel{{color:{TEXT}}}
QLineEdit,QTextEdit,QPlainTextEdit,QComboBox,QSpinBox,QListWidget{{
  background:{BG_CARD};border:1px solid {BORDER};border-radius:7px;padding:8px;color:{TEXT}}}
QTextEdit[readonly="true"],QPlainTextEdit[readonly="true"]{{background:#0d1830}}
QComboBox QAbstractItemView{{background:{BG_CARD};selection-background-color:{ACCENT}}}
QPushButton{{background:{ACCENT};border:0;border-radius:8px;padding:10px 16px;color:white;font-weight:600}}
QPushButton:hover{{background:#2384e0}}
QPushButton#ghost{{background:transparent;border:1px solid {BORDER};color:{TEXT}}}
QPushButton#ghost:hover{{background:{BG_CARD}}}
QPushButton#run{{background:{ACCENT};font-size:14px;padding:11px 20px}}
QPushButton#run:hover{{background:#2384e0}}
QFrame#card{{background:{BG_CARD};border:1px solid {BORDER};border-radius:12px}}
QFrame#navbtn{{background:transparent;border:0;border-radius:10px}}
QFrame#navbtn[active="true"]{{background:{BG_CARD};border:1px solid {ACCENT}}}
QLabel#title{{font-size:20px;font-weight:700}}
QLabel#h2{{font-size:14px;font-weight:700;color:{TEXT}}}
QLabel#dim{{color:{TEXT_DIM}}}
QLabel#metric{{font-size:12px;color:{TEXT_DIM}}}
QScrollArea{{border:0;background:transparent}}
QScrollBar:vertical{{width:10px;background:{BG_PANEL}}}
QScrollBar::handle:vertical{{background:{BORDER};border-radius:5px}}
QToolTip{{background:#0d1830;color:#e6edf8;border:1px solid {BORDER};border-radius:6px;padding:8px;font-size:12px}}
"""


def _metric_bar(name: str, value: int) -> "QFrame":
    from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QProgressBar, QSizePolicy, QVBoxLayout
    f = QFrame(); f.setObjectName("card")
    fl = QVBoxLayout(f); fl.setContentsMargins(12, 10, 12, 10); fl.setSpacing(6)
    top = QHBoxLayout()
    name_l = QLabel(name); name_l.setMinimumWidth(120); name_l.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Preferred)
    val = QLabel(f"{value}%"); val.setMinimumWidth(40); val.setAlignment(Qt.AlignRight); val.setStyleSheet(f"color:{TEXT};font-weight:700")
    top.addWidget(name_l); top.addStretch(1); top.addWidget(val)
    bar = QProgressBar(); bar.setRange(0, 100); bar.setValue(value); bar.setTextVisible(False)
    bar.setFixedHeight(8)
    col = GREEN if value >= 70 else (AMBER if value >= 45 else RED)
    bar.setStyleSheet(f"QProgressBar{{background:#0d1830;border-radius:4px}} QProgressBar::chunk{{background:{col};border-radius:4px}}")
    fl.addLayout(top); fl.addWidget(bar)
    return f


class Step(QFrame):
    def __init__(self, n, title, color):
        super().__init__(); self.setObjectName("navbtn")
        self.setFixedWidth(150); lay = QVBoxLayout(self); lay.setContentsMargins(10, 8, 10, 8); lay.setSpacing(2)
        self.dot = QLabel(f"{n}"); self.dot.setFixedSize(26, 26); self.dot.setAlignment(Qt.AlignCenter)
        self.dot.setStyleSheet(f"background:{color};color:white;border-radius:13px;font-weight:700")
        self.t = QLabel(title); self.t.setStyleSheet(f"color:{TEXT};font-weight:600")
        lay.addWidget(self.dot); lay.addWidget(self.t); lay.addStretch()

    def set_done(self, done):
        col = GREEN if done else ACCENT_2
        self.dot.setStyleSheet(f"background:{col};color:white;border-radius:13px;font-weight:700")


class Window(QMainWindow):
    def __init__(self, database=None):
        super().__init__(); self.store = Storage(database); self.packet = None
        self.setWindowTitle("CRIBA Current Engine")
        self.resize(1440, 860); self.setMinimumSize(1024, 680)
        self.setStyleSheet(GLOBAL_CSS)
        root = QWidget(); self.setCentralWidget(root)
        root_layout = QVBoxLayout(root); root_layout.setContentsMargins(0, 0, 0, 0); root_layout.setSpacing(0)
        content = QWidget(); page = QHBoxLayout(content); page.setContentsMargins(0, 0, 0, 0); page.setSpacing(0)
        root_layout.addWidget(content, 1)

        # ---------- left nav ----------
        nav = QFrame(); nav.setFixedWidth(74); nav.setStyleSheet(f"background:{BG_PANEL};border-right:1px solid {BORDER}")
        nv = QVBoxLayout(nav); nv.setContentsMargins(10, 14, 10, 14); nv.setSpacing(8)
        logo = QLabel("⌁"); logo.setStyleSheet(f"color:{ACCENT};font-size:26px;font-weight:800"); logo.setAlignment(Qt.AlignCenter)
        nv.addWidget(logo)
        self.nav_buttons = {}
        for icon, name in [("◰", "Inicio"), ("▦", "Biblioteca"), ("⟳", "Historial"), ("⌗", "Integraciones"), ("⚙", "Configuración")]:
            b = QFrame(); b.setObjectName("navbtn"); b.setFixedSize(54, 54)
            bl = QVBoxLayout(b); bl.setContentsMargins(0, 0, 0, 0); bl.setSpacing(0)
            ic = QLabel(icon); ic.setStyleSheet(f"color:{TEXT};font-size:20px"); ic.setAlignment(Qt.AlignCenter)
            bl.addWidget(ic)
            b.mousePressEvent = (lambda n=name: (lambda e: self._nav(n)))
            nv.addWidget(b); self.nav_buttons[name] = b
        nv.addStretch()
        page.addWidget(nav)

        # ---------- central ----------
        central = QWidget(); cl = QVBoxLayout(central); cl.setContentsMargins(18, 16, 18, 0); cl.setSpacing(14)
        # header
        hdr = QHBoxLayout()
        title = QLabel("CRIBA Current Engine"); title.setObjectName("title")
        hdr.addWidget(title); hdr.addStretch()
        self.mode = QComboBox(); self.mode.addItems(["Balanced", "Strict", "Creative", "Adversarial", "Minimal"])
        self.mode.setFixedWidth(150)
        self.adv_btn = QPushButton("Avanzado ▾"); self.adv_btn.setObjectName("ghost"); self.adv_btn.setFixedWidth(120)
        self.adv_btn.setToolTip("Muestra las opciones técnicas (corriente, métodos, experimento, métricas y el prompt).\nSi solo quieres la recomendación, déjalo cerrado.")
        self.adv_btn.setCheckable(True); self.adv_btn.clicked.connect(self.toggle_advanced)
        self.run_btn = QPushButton("▶  EJECUTAR CRIBA"); self.run_btn.setObjectName("run"); self.run_btn.clicked.connect(self.do_activate)
        self.run_btn.setToolTip("Analiza tu consulta con CRIBA y muestra la recomendación.\nNo necesitas saber cómo funciona: escribe tu problema y pulsa aquí.")
        hdr.addWidget(self.mode); hdr.addWidget(self.adv_btn); hdr.addWidget(self.run_btn)
        cl.addLayout(hdr)

        # ---------- LOTTERY MODES ----------
        lottery_row = QHBoxLayout(); lottery_row.setSpacing(10)
        lottery_label = QLabel("Modos de innovación:"); lottery_label.setStyleSheet(f"color:{TEXT_DIM};font-weight:600")
        lottery_row.addWidget(lottery_label)
        self.lottery_associative = QPushButton("🔗 Lotería Asociativa"); self.lottery_associative.setObjectName("ghost")
        self.lottery_associative.setToolTip("Selección aleatoria buscando asociaciones temáticas.\nExplora conexiones inesperadas entre métodos.")
        self.lottery_associative.clicked.connect(self.do_lottery_associative)
        self.lottery_pure = QPushButton("🎲 Lotería Pura"); self.lottery_pure.setObjectName("ghost")
        self.lottery_pure.setToolTip("Selección 100% aleatoria.\nLa mayoría serán basura, pero algo único podría surgir.")
        self.lottery_pure.clicked.connect(self.do_lottery_pure)
        self.lottery_alternating = QPushButton("🔄 Lotería Alternada"); self.lottery_alternating.setObjectName("ghost")
        self.lottery_alternating.setToolTip("Alterna entre asociativa y pura.\nMáxima diversidad de exploración.")
        self.lottery_alternating.clicked.connect(self.do_lottery_alternating)
        lottery_row.addWidget(self.lottery_associative); lottery_row.addWidget(self.lottery_pure); lottery_row.addWidget(self.lottery_alternating)
        lottery_row.addStretch()
        cl.addLayout(lottery_row)

        # ---------- SIMPLE panel (default) ----------
        self.simple_panel = QFrame(); sp = QVBoxLayout(self.simple_panel); sp.setContentsMargins(0, 0, 0, 0); sp.setSpacing(12)
        sprob = QFrame(); sprob.setObjectName("card"); spc = QVBoxLayout(sprob); spc.setContentsMargins(14, 12, 14, 12)
        spc.addWidget(QLabel("Tu consulta")); self.simple_query = QTextEdit(); self.simple_query.setPlaceholderText("Describe el problema o decisión que quieres validar con CRIBA…")
        self.simple_query.setFixedHeight(72); spc.addWidget(self.simple_query)
        # Keep the historical attribute pointing at the default, visible editor.
        # The advanced editor is synchronized after it has been created below.
        self.query = self.simple_query
        sp.addWidget(sprob)
        self.simple_answer = QFrame(); self.simple_answer.setObjectName("card"); self.simple_answer.hide()
        sa_lay = QVBoxLayout(self.simple_answer); sa_lay.setContentsMargins(14, 12, 14, 12); sp.addWidget(self.simple_answer)
        cl.addWidget(self.simple_panel)

        # ---------- ADVANCED container (collapsible) ----------
        self.advanced_container = QWidget(); ac = QVBoxLayout(self.advanced_container); ac.setContentsMargins(0, 0, 0, 0); ac.setSpacing(14)
        self.advanced_container.hide()
        # stepper
        steps = QHBoxLayout(); steps.setSpacing(10)
        self.steps = [
            Step(1, "Contextualizar", ACCENT), Step(2, "Romper", ACCENT_2),
            Step(3, "Idear", "#64748b"), Step(4, "Banco de Pruebas", "#64748b"), Step(5, "Decidir", "#64748b"),
        ]
        for s in self.steps: steps.addWidget(s)
        steps.addStretch(); ac.addLayout(steps)

        # scroll area for the workbench
        sa = QScrollArea(); sa.setWidgetResizable(True); wb = QWidget(); sa.setWidget(wb)
        wl = QVBoxLayout(wb); wl.setContentsMargins(0, 0, 0, 0); wl.setSpacing(14)

        # config row (3 cols)
        cfg_row = QHBoxLayout(); cfg_row.setSpacing(14)
        # problem
        prob_card = QFrame(); prob_card.setObjectName("card"); pc = QVBoxLayout(prob_card); pc.setContentsMargins(14, 12, 14, 12)
        pc.addWidget(QLabel("Consulta / Problema")); self.advanced_query = QTextEdit(); self.advanced_query.setPlaceholderText("Pega la consulta para activar CRIBA…")
        self.advanced_query.setMinimumHeight(120); pc.addWidget(self.advanced_query)
        self.simple_query.textChanged.connect(
            lambda: self._sync_query_fields(self.simple_query, self.advanced_query)
        )
        self.advanced_query.textChanged.connect(
            lambda: self._sync_query_fields(self.advanced_query, self.simple_query)
        )
        # current
        cur_card = QFrame(); cur_card.setObjectName("card"); cc = QVBoxLayout(cur_card); cc.setContentsMargins(14, 12, 14, 12)
        cc.addWidget(QLabel("Corriente")); self.current = QComboBox(); self.current.addItem("Selección automática (recomendada)", "auto")
        [self.current.addItem(x["name"], x["id"]) for x in currents()]
        cc.addWidget(self.current); cc.addWidget(QLabel("Selección automática por señales deterministas."))
        # options
        opt_card = QFrame(); opt_card.setObjectName("card"); oc = QVBoxLayout(opt_card); oc.setContentsMargins(14, 12, 14, 12)
        oc.addWidget(QLabel("Opciones"))
        chips = QHBoxLayout(); self.count = QSpinBox(); self.count.setRange(1, 8); self.count.setValue(4)
        chips.addWidget(QLabel("Métodos aux.")); chips.addWidget(self.count); chips.addStretch()
        oc.addLayout(chips)
        self.analysis_mode = QComboBox(); self.analysis_mode.addItems(["Profundidad estándar", "Profundidad alta", "Rápido"])
        self.safety = QComboBox(); self.safety.addItems(["Strict", "Standard"])
        self.depth = QComboBox(); self.depth.addItems(["Superficial", "Media", "Profunda"])
        for lab, w in [("Modo de análisis", self.analysis_mode), ("Nivel de seguridad", self.safety), ("Profundidad", self.depth)]:
            row = QHBoxLayout(); row.addWidget(QLabel(lab)); row.addWidget(w); oc.addLayout(row)
        cfg_row.addWidget(prob_card, 3); cfg_row.addWidget(cur_card, 1); cfg_row.addWidget(opt_card, 1)
        wl.addLayout(cfg_row)

        # grid 2x2
        grid = QGridLayout(); grid.setSpacing(14)
        self.card_current = self._card_frame(); grid.addWidget(self.card_current, 0, 0)
        self.card_methods = self._card_frame(); grid.addWidget(self.card_methods, 0, 1)
        self.card_experiment = self._card_frame(); grid.addWidget(self.card_experiment, 1, 0)
        self.card_rupture = self._card_frame(); grid.addWidget(self.card_rupture, 1, 1)
        wl.addLayout(grid)

        # enriched prompt
        pp = QFrame(); pp.setObjectName("card"); ppl = QVBoxLayout(pp); ppl.setContentsMargins(14, 12, 14, 12)
        ppl.addWidget(QLabel("Prompt enriquecido")); self.prompt_view = QTextEdit(); self.prompt_view.setReadOnly(True); self.prompt_view.setMinimumHeight(120)
        ppl.addWidget(self.prompt_view)
        wl.addWidget(pp)
        ac.addWidget(sa)
        cl.addWidget(self.advanced_container)

        page.addWidget(central, 1)

        # ---------- right summary ----------
        right = QFrame(); right.setFixedWidth(340); right.setStyleSheet(f"background:{BG_PANEL};border-left:1px solid {BORDER}")
        rl = QVBoxLayout(right); rl.setContentsMargins(16, 16, 16, 16); rl.setSpacing(14)
        rl.addWidget(QLabel("Resumen de activación"))
        self.sum_card = QFrame(); self.sum_card.setObjectName("card"); self.sum_lay = QVBoxLayout(self.sum_card)
        self.sum_lay.setContentsMargins(14, 12, 14, 12); rl.addWidget(self.sum_card)
        self.json_btn = QPushButton("Ver paquete completo (JSON)"); self.json_btn.setObjectName("ghost"); self.json_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed); self.json_btn.setMinimumHeight(38); self.json_btn.clicked.connect(self.show_json)
        self.json_btn.setToolTip("Abre el análisis completo en formato JSON (datos técnicos para quien los sepa leer).")
        self.copy_btn = QPushButton("Copiar para el modelo"); self.copy_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed); self.copy_btn.setMinimumHeight(38); self.copy_btn.clicked.connect(self.copy_prompt)
        self.copy_btn.setToolTip("Copia el texto preparado al portapapeles para pegarlo en tu asistente de IA.")
        rl.addWidget(self.json_btn); rl.addWidget(self.copy_btn)
        rl.addWidget(QLabel("Métricas clave"))
        self.metrics_box = QVBoxLayout(); self.metrics_box.setSpacing(8)
        mw = QWidget(); mw.setLayout(self.metrics_box); rl.addWidget(mw)
        rl.addWidget(QLabel("Decisión recomendada"))
        self.dec_card = QFrame(); self.dec_card.setObjectName("card"); self.dec_lay = QVBoxLayout(self.dec_card)
        self.dec_lay.setContentsMargins(14, 12, 14, 12); rl.addWidget(self.dec_card)
        self.dec_just = QPushButton("Ver justificación"); self.dec_just.setObjectName("ghost"); self.dec_just.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed); self.dec_just.setMinimumHeight(38); self.dec_just.clicked.connect(self.show_json)
        self.dec_just.setToolTip("Explica por qué CRIBA sugiere esa decisión (el razonamiento detrás de la recomendación).")
        rl.addWidget(self.dec_just); rl.addStretch()
        page.addWidget(right)

        # ---------- footer ----------
        self.footer = QLabel("MCP: ✕   ·   API local: ✕   ·   Base de datos: ✓")
        self.footer.setStyleSheet(f"background:{BG_PANEL};border-top:1px solid {BORDER};padding:6px 16px;color:{TEXT_DIM}")
        self.footer.setFixedHeight(30)
        root_layout.addWidget(self.footer)

    # ---------- helpers ----------
    def _card_frame(self) -> QFrame:
        f = QFrame(); f.setObjectName("card"); return f

    def _fill_card(self, card: QFrame, title: str, body: str, accent: str = ACCENT):
        old = card.layout()
        if old: QWidget().setLayout(old)
        lay = QVBoxLayout(card); lay.setContentsMargins(14, 12, 14, 12); lay.setSpacing(8)
        h = QHBoxLayout(); t = QLabel(title); t.setObjectName("h2"); h.addWidget(t); h.addStretch()
        tag = QLabel("●"); tag.setStyleSheet(f"color:{accent}"); h.addWidget(tag); lay.addLayout(h)
        body_l = QLabel(body); body_l.setWordWrap(True); body_l.setTextInteractionFlags(Qt.TextSelectableByMouse)
        lay.addWidget(body_l)

    def _nav(self, name):
        for n, b in self.nav_buttons.items():
            b.setProperty("active", n == name); b.style().polish(b)
        if name == "Historial":
            self.show_history()
        elif name == "Biblioteca":
            self.show_library()
        else:
            QMessageBox.information(self, "CRIBA", f"Sección '{name}' en construcción.\nEl workbench principal ya está activo.")

    def toggle_advanced(self, checked):
        self.advanced_container.setVisible(checked)
        self.adv_btn.setText("Avanzado ▴" if checked else "Avanzado ▾")

    @staticmethod
    def _sync_query_fields(source, target):
        """Mirror text between the simple and advanced query inputs without a signal loop."""
        text = source.toPlainText()
        if target.toPlainText() != text:
            target.blockSignals(True)
            try:
                target.setPlainText(text)
            finally:
                target.blockSignals(False)

    # ---------- actions ----------
    def do_activate(self):
        try:
            q = self.simple_query.toPlainText().strip()
            if not q:
                QMessageBox.warning(self, "CRIBA", "Escribe una consulta antes de ejecutar.")
                return
            mode_map = {"Balanced": "balanced", "Strict": "strict", "Creative": "creative", "Adversarial": "adversarial", "Minimal": "minimal"}
            safety = "standard" if self.safety.currentText() == "Standard" else "strict"
            self.packet = activate(q, self.current.currentData(), mode_map[self.mode.currentText()], self.count.value(), safety_level=safety)
            self.store.save(self.packet["original_query"], self.packet, {"gui": True, "mode": self.mode.currentText(), "safety": safety})
            self.render()
        except ValueError as exc:
            QMessageBox.warning(self, "CRIBA", str(exc))

    def _render_simple(self, p):
        old = self.simple_answer.layout()
        if old: QWidget().setLayout(old)
        lay = QVBoxLayout(self.simple_answer); lay.setContentsMargins(14, 12, 14, 12); lay.setSpacing(8)
        sc = p["selected_current"]; d = p["decision"]
        head = QLabel(f"Corriente recomendada: <b>{sc['name']}</b>  ·  score {sc['score']}/100")
        head.setStyleSheet(f"color:{TEXT};font-weight:700;font-size:15px"); lay.addWidget(head)
        dec = QLabel(f"Decisión sugerida: <b>{d['recommended_status']}</b>  ({int(d['confidence']*100)}% confianza)")
        dec.setStyleSheet(f"color:{AMBER};font-weight:600"); lay.addWidget(dec)
        steps = " → ".join(["Contextualizar", "Romper", "Idear", "Banco de Pruebas", "Decidir"])
        st = QLabel(f"<b>Ruta CRIBA:</b> {steps}")
        st.setWordWrap(True); st.setStyleSheet(f"color:{TEXT_DIM}"); lay.addWidget(st)
        hint = QLabel("Pulsa 'Avanzado ▾' para ver corriente, métodos, experimento, métricas y el prompt enriquecido.")
        hint.setWordWrap(True); hint.setStyleSheet(f"color:{TEXT_DIM}"); lay.addWidget(hint)
        self.simple_answer.show()

    def render(self):
        p = self.packet
        self._render_simple(p)
        for i, s in enumerate(self.steps): s.set_done(i < 3)
        # current card
        sc = p["selected_current"]
        self._fill_card(self.card_current, "Corriente seleccionada",
                        f"<b>{sc['name']}</b>  —  score {sc['score']}/100\n\n" + "\n".join(f"• {r}" for r in sc["selection_reasons"][:3]))
        # methods card
        ms = "\n".join(f"▦ {m['id']}  {m['name']}" for m in p["supporting_methods"])
        self._fill_card(self.card_methods, "Métodos auxiliares", ms, ACCENT_2)
        # experiment card
        ex = p["experiment"]
        rows = [("Hipótesis falsable", ex.get("falsifiable_hypothesis", "—")), ("Baseline", ex.get("baseline", "—")),
                ("Variante", ex.get("variant", "—")), ("Límite de daño", ex.get("damage_limit", "—")),
                ("Sandbox", ex.get("sandbox", "—")), ("Rollback", ex.get("rollback", "—"))]
        tbl = "<table cellpadding='4'>" + "".join(f"<tr><td style='color:{TEXT_DIM}'>{k}</td><td>{v}</td></tr>" for k, v in rows) + "</table>"
        self._fill_card(self.card_experiment, "Diseño de experimento", tbl, GREEN)
        # rupture + ideas
        rp = p["rupture"]
        ideas = "\n".join(f"{i+1}. {d.get('title') or d.get('description', '')}" for i, d in enumerate(p["ideas"]))
        ops = rp.get("operations", [])
        first_op = ops[0].get("result", "") if ops else "—"
        rupture = (f"<b>Ruptura de supuestos</b>\n• Supuestos rotos: {', '.join(rp.get('broken_assumptions', [])) or '—'}\n"
                   f"• Operación principal: {first_op}\n• Contraejemplo: {rp.get('counterexample', '—')}\n\n<b>Ideas generadas</b>\n{ideas}")
        self._fill_card(self.card_rupture, "Ruptura de supuestos e ideas", rupture, AMBER)
        # summary card
        old = self.sum_card.layout()
        if old: QWidget().setLayout(old)
        sl = QVBoxLayout(self.sum_card); sl.setContentsMargins(14, 12, 14, 12); sl.setSpacing(6)
        dt = datetime.fromisoformat(p["timestamp"]).strftime("%d/%m/%Y %H:%M")
        for k, v in [("ID activación", p["activation_id"][:8] + "…"), ("Fecha", dt), ("Modo", self.mode.currentText()),
                     ("Métodos", str(len(p["supporting_methods"]))), ("Nivel seg.", self.safety.currentText())]:
            kk = QLabel(k); kk.setStyleSheet(f"color:{TEXT_DIM}")
            vv = QLabel(str(v)); vv.setStyleSheet(f"color:{TEXT};font-weight:600")
            r2 = QHBoxLayout(); r2.addWidget(kk); r2.addStretch(); r2.addWidget(vv); sl.addLayout(r2)
        # metrics
        self._render_metrics(p["metrics"])
        # decision
        old = self.dec_card.layout()
        if old: QWidget().setLayout(old)
        dl = QVBoxLayout(self.dec_card); dl.setContentsMargins(14, 12, 14, 12); dl.setSpacing(6)
        d = p["decision"]
        rec = QLabel(d["recommended_status"]); rec.setStyleSheet(f"color:{AMBER};font-weight:700;font-size:15px")
        conf = QLabel(f"{int(d['confidence']*100)}% confianza"); conf.setStyleSheet(f"color:{TEXT_DIM}")
        dl.addWidget(rec); dl.addWidget(conf)
        # prompt
        self.prompt_view.setPlainText(build_prompt(p))

    def _render_metrics(self, m: dict):
        while self.metrics_box.count():
            w = self.metrics_box.takeAt(0).widget()
            if w: w.deleteLater()
        labels = {"potential_novelty": "Novedad potencial", "feasibility": "Viabilidad",
                  "controlled_risk": "Riesgo controlado", "reversibility": "Reversibilidad", "uncertainty": "Incertidumbre"}
        for key, lab in labels.items():
            self.metrics_box.addWidget(_metric_bar(lab, m.get(key, 0)))

    def do_prompt(self):
        if not self.packet: self.do_activate()
        if self.packet:
            self.prompt_view.setPlainText(build_prompt(self.packet))

    def copy_prompt(self):
        self.do_prompt()
        QApplication.clipboard().setText(self.prompt_view.toPlainText())

    def show_json(self):
        if not self.packet:
            QMessageBox.information(self, "CRIBA", "Aún no hay activación. Ejecuta CRIBA primero.")
            return
        dlg = QTextEdit(); dlg.setReadOnly(True); dlg.setPlainText(json.dumps(self.packet, ensure_ascii=False, indent=2))
        dlg.setMinimumSize(720, 540)
        box = QMessageBox(self); box.setWindowTitle("Paquete completo (JSON)"); box.layout().addWidget(dlg)
        box.exec()

    def do_lottery_associative(self):
        """Ejecuta lotería asociativa."""
        q = self.simple_query.toPlainText().strip()
        if not q:
            QMessageBox.warning(self, "CRIBA", "Escribe una consulta para la lotería asociativa.")
            return
        try:
            from .lottery import run_lottery
            summary = run_lottery(rounds=5, batch_size=10, mode="associative", query=q)
            QMessageBox.information(self, "Lotería Asociativa",
                f"Completada.\n{summary['total_ideas']} ideas generadas.\n"
                f"{summary['extraordinary_ideas']} extraordinarias.\n"
                f"{summary['good_ideas']} buenas.")
        except Exception as exc:
            QMessageBox.warning(self, "CRIBA", f"Error: {exc}")

    def do_lottery_pure(self):
        """Ejecuta lotería pura."""
        try:
            from .lottery import run_lottery
            summary = run_lottery(rounds=5, batch_size=10, mode="pure")
            QMessageBox.information(self, "Lotería Pura",
                f"Completada.\n{summary['total_ideas']} ideas generadas.\n"
                f"{summary['extraordinary_ideas']} extraordinarias.\n"
                f"{summary['good_ideas']} buenas.")
        except Exception as exc:
            QMessageBox.warning(self, "CRIBA", f"Error: {exc}")

    def do_lottery_alternating(self):
        """Ejecuta lotería alternada."""
        q = self.simple_query.toPlainText().strip()
        try:
            from .lottery import run_lottery
            summary = run_lottery(rounds=10, batch_size=10, mode="alternating", query=q or None)
            QMessageBox.information(self, "Lotería Alternada",
                f"Completada.\n{summary['total_ideas']} ideas generadas.\n"
                f"{summary['extraordinary_ideas']} extraordinarias.\n"
                f"{summary['good_ideas']} buenas.")
        except Exception as exc:
            QMessageBox.warning(self, "CRIBA", f"Error: {exc}")

    def show_history(self):
        sessions = self.store.list_sessions(20)
        if not sessions:
            QMessageBox.information(self, "CRIBA", "No hay sesiones previas.")
            return
        items = "\n".join(f"• {s['id'][:8]}  {s['created_at'][:19]}  —  {s['current_id']}" for s in sessions)
        QMessageBox.information(self, "Historial", f"{len(sessions)} sesiones:\n\n{items}")

    def show_library(self):
        cs = currents(); ms = methods()
        QMessageBox.information(self, "Biblioteca", f"{len(cs)} corrientes y {len(ms)} métodos cargados desde catálogo JSON.")


def run(database=None):
    if QApplication is None:
        print("PySide6 no está instalado. Instala requirements-optional.txt para usar 'criba gui'.", file=sys.stderr)
        return 2
    from .ui.main_window import CribaMainWindow
    app = QApplication.instance() or QApplication(sys.argv)
    window = CribaMainWindow(database); window.show()
    smoke_exit_ms = os.environ.get("CRIBA_SMOKE_EXIT_MS")
    if smoke_exit_ms:
        QTimer.singleShot(max(0, int(smoke_exit_ms)), window.close)
    return app.exec()


def run_legacy(database=None):
    """Ruta obsoleta. La interfaz canónica es CribaMainWindow (criba gui).

    Se desactiva explícitamente: no debe abrirse ninguna UI antigua. Usa
    ``python -m criba gui`` (gui.run) que lanza CribaMainWindow.
    """
    raise RuntimeError(
        "Interfaz 'CRIBA Current Engine' obsoleta. Usa 'criba gui' "
        "(CribaMainWindow) como ruta canónica."
    )


if __name__ == "__main__":
    raise SystemExit(run())
