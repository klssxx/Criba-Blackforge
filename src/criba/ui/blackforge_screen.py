"""Pantalla BLACKFORGE — dashboard de innovación en ciberseguridad (FASE 10).

Es CRIBA pero maximizado a la temática de hacking ético / ciberseguridad:
mismo motor (modo normal + doble lotería asociativa/pura), mismo contrato
visual (sidebar de CRIBA compartido, «VOLVER A CRIBA»), pero piel y datos
propios. El hero es el render de la criba BF-516 (CRIBA LITERAL) con destellos
de luz lentos y alternos.

Datos: la tabla «Ideas Generadas (Top 5)» y el donut de cobertura se alimentan
del catálogo real de BLACKFORGE (723 records) — nada inventado. Los botones de
lotería ejecutan LotteryEngine sobre ese catálogo y pueblan la tabla con ideas
estructuradas y verificables.

Salidas interpretadas: el módulo interpreter.py traduce las combinaciones del
motor a frases legibles en ES/EN sin modelo externo (offline, determinista).
"""
from __future__ import annotations

import random
from datetime import datetime
from typing import Any

from PySide6.QtCore import (
    QAbstractTableModel,
    QEasingCurve,
    QPropertyAnimation,
    Qt,
    QTimer,
)
from PySide6.QtGui import QColor, QPainter, QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QGraphicsOpacityEffect,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from ..blackforge_catalog import records as bf_records
from ..constants import DATA_ROOT
from .i18n import on_change, t
from .interpreter import format_idea
from .tokens import Tokens
from .widgets import (
    DonutChartWidget,
    LegendRow,
    SourceBarWidget,
    apply_neon_breath,
    make_chip,
)


# --- métricas reales del catálogo (se calculan una vez) -------------------
def _catalog_metrics() -> dict[str, Any]:
    recs = list(bf_records())
    fams: set[str] = set()
    for r in recs:
        f = r.get("functional_category_primary") or r.get("source_family") or "—"
        fams.add(f)
    total = len(recs) or 1
    target_fams = 28
    cov = min(100, round(100 * len(fams) / target_fams))
    top = sorted(recs,
                 key=lambda r: float(r.get("selection_weight", 0) or 0),
                 reverse=True)[:5]
    return {"n_records": len(recs), "n_families": len(fams),
            "coverage_pct": cov, "top5": top}


_RISK_COLOR = {
    "low": "#3DDC84", "low_medium": "#F5A623", "medium": "#F5A623",
    "medium_high": "#FF7A1A", "high": "#FF4D4D", "critical": "#FF4D4D",
}


def _risk_label(key: str) -> str:
    m = {"low": "risk.low", "low_medium": "risk.medium", "medium": "risk.medium",
         "medium_high": "risk.high", "high": "risk.high", "critical": "risk.critical"}
    return t(m.get(key, "risk.medium"))


def _novelty_key(score: float) -> str:
    s = float(score or 0)
    if s >= 0.85:
        return "nov.muy_alta"
    if s >= 0.65:
        return "nov.alta"
    return "nov.media"


def _priority_key(tier: str) -> str:
    x = (tier or "").lower()
    if "crít" in x or "critical" in x:
        return "pri.critica"
    if "alta" in x or "high" in x or "essential" in x or "core" in x:
        return "pri.alta"
    return "pri.media"


# ---------------------------------------------------------------------------
# Fade-in helper
# ---------------------------------------------------------------------------
def _fade_in(widget: QWidget, duration: int = 280) -> None:
    eff = QGraphicsOpacityEffect(widget)
    widget.setGraphicsEffect(eff)
    anim = QPropertyAnimation(eff, b"opacity", widget)
    anim.setDuration(duration)
    anim.setStartValue(0.0)
    anim.setEndValue(1.0)
    anim.setEasingCurve(QEasingCurve.Type.OutCubic)
    anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)


# ---------------------------------------------------------------------------
# Ideas table model
# ---------------------------------------------------------------------------
class _BFIdeasModel(QAbstractTableModel):
    _HEADER_KEYS = ["#", "col.titulo", "col.mecanismo",
                    "col.riesgo", "col.novedad", "col.prioridad"]
    RISK_COL, NOV_COL, PRI_COL = 3, 4, 5

    def __init__(self) -> None:
        super().__init__()
        self._rows: list[dict[str, Any]] = []

    def set_rows(self, rows: list[dict[str, Any]]) -> None:
        self.beginResetModel()
        self._rows = rows
        self.endResetModel()

    def refresh_headers(self) -> None:
        self.headerDataChanged.emit(Qt.Orientation.Horizontal, 0, 5)

    def rowCount(self, parent=None) -> int:
        return len(self._rows)

    def columnCount(self, parent=None) -> int:
        return len(self._HEADER_KEYS)

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            k = self._HEADER_KEYS[section]
            return t(k) if k != "#" else "#"
        return None

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        row = self._rows[index.row()]
        col = index.column()
        if role == Qt.ItemDataRole.DisplayRole:
            return row.get(col, "")
        if role == Qt.ItemDataRole.TextAlignmentRole and col in (0, 3, 4, 5):
            return Qt.AlignmentFlag.AlignCenter
        if role == Qt.ItemDataRole.ForegroundRole and col == self.RISK_COL:
            return QColor(_RISK_COLOR.get(row.get("risk_key", ""), "#FBF3EA"))
        if role == Qt.ItemDataRole.ForegroundRole and col == self.PRI_COL:
            p = (row.get("priority_key", "")).lower()
            if "crít" in p or "critical" in p:
                return QColor("#FF4D4D")
            if "alta" in p or "high" in p:
                return QColor("#F5A623")
        return None


# ---------------------------------------------------------------------------
# Hero glow overlay
# ---------------------------------------------------------------------------
class _HeroGlow(QWidget):
    """Destellos tipo estrella lentos y alternos sobre el hero."""

    def __init__(self, points: list[tuple[float, float]],
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._points = points
        self._active = -1
        self._timer = QTimer(self)
        self._timer.setInterval(4200)
        self._timer.timeout.connect(self._next)
        self._off_timer = QTimer(self)
        self._off_timer.setSingleShot(True)
        self._off_timer.timeout.connect(self._off)

    def start(self) -> None:
        self._timer.start()
        self._next()

    def _next(self) -> None:
        n = len(self._points)
        if not n:
            return
        nxt = random.randrange(n)
        if nxt == self._active:
            nxt = (nxt + 1) % n
        self._active = nxt
        interval = random.randint(3000, 6000)
        self._timer.setInterval(interval)
        self.update()
        self._off_timer.start(600)

    def _off(self) -> None:
        self._active = -1
        self.update()

    def paintEvent(self, event) -> None:
        if self._active < 0:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        x = self._points[self._active][0] * self.width()
        y = self._points[self._active][1] * self.height()
        p.setPen(Qt.PenStyle.NoPen)
        # halo
        p.setBrush(QColor(255, 154, 61, 60))
        p.drawEllipse(int(x - 2), int(y - 16), 4, 32)
        p.drawEllipse(int(x - 16), int(y - 2), 32, 4)
        # núcleo
        p.setBrush(QColor(255, 226, 170, 235))
        p.drawEllipse(int(x - 2), int(y - 2), 4, 4)
        p.setBrush(QColor(255, 154, 61, 110))
        p.drawEllipse(int(x - 5), int(y - 5), 10, 10)
        p.end()


# ---------------------------------------------------------------------------
# Main screen
# ---------------------------------------------------------------------------
class BlackforgeScreen(QWidget):
    """Dashboard BLACKFORGE dentro de CRIBA (página del QStackedWidget)."""

    def __init__(self, main_window: Any) -> None:
        super().__init__()
        self.win = main_window
        # Tokens ya recargados por main_window, pero obtener instancia fresca
        from .tokens import load_tokens, reload_tokens
        reload_tokens()
        self.t: Tokens = load_tokens()
        self.setObjectName("mainColumn")
        self._hero_pixmap = QPixmap()
        self._metrics = _catalog_metrics()
        self._mode = "optimizado"
        self._lottery_engine: Any = None
        self._busy = False
        self._run_btn: QPushButton | None = None
        self._spin_timer = QTimer(self)
        self._spin_timer.setInterval(120)
        self._spin_phase = 0
        self._spin_timer.timeout.connect(self._spin_tick)
        self._build_ui()
        on_change(self._on_lang_change)

    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        tok = self.t
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(self._build_header())

        row = QHBoxLayout()
        row.setContentsMargins(tok.spacing(20), tok.spacing(20),
                               tok.spacing(20), tok.spacing(20))
        row.setSpacing(tok.spacing(20))

        scroll = QScrollArea()
        scroll.setObjectName("centerScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        center = QWidget()
        center.setObjectName("centerColumn")
        cl = QVBoxLayout(center)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(tok.spacing(16))
        cl.addWidget(self._build_status_section())
        cl.addWidget(self._build_modes_card())
        cl.addWidget(self._build_ideas_card())
        cl.addStretch(1)
        scroll.setWidget(center)
        row.addWidget(scroll, 1)

        right = QScrollArea()
        right.setObjectName("rightScroll")
        right.setWidgetResizable(True)
        right.setFrameShape(QScrollArea.Shape.NoFrame)
        right.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        width = tok.layout("right_column_width")
        screen = self.screen()
        if screen and screen.availableGeometry().width() < 1500:
            width = tok.layout("right_column_width_min")
        right.setFixedWidth(width)
        right.setWidget(self._build_kpi_panel())
        row.addWidget(right)

        outer.addLayout(row, 1)

    # ------------------------------------------------------------------
    def _build_header(self) -> QFrame:
        tok = self.t
        tb = QFrame()
        tb.setObjectName("topbar")
        tb.setFixedHeight(tok.layout("topbar_height"))
        lay = QHBoxLayout(tb)
        lay.setContentsMargins(tok.spacing(20), tok.spacing(12),
                               tok.spacing(20), tok.spacing(12))
        lay.setSpacing(tok.spacing(16))

        wm = QLabel()
        wm.setObjectName("bfWordmark")
        wm.setText('<span style="color:#FF7A1A">CRIBA</span> '
                   '<span style="color:#FBF3EA">BLACKFORGE</span>')
        lay.addWidget(wm)
        lay.addSpacing(tok.spacing(12))

        self._mode_chip = make_chip("● MODO OPTIMIZADO", "guardada")
        lay.addWidget(self._mode_chip)
        self._header_sub = QLabel(t("bf.estado.desc")[:60] + "…")
        self._header_sub.setObjectName("greetingSub")
        lay.addWidget(self._header_sub)
        lay.addStretch(1)

        # Reloj
        self.bfDate = QLabel()
        self.bfDate.setObjectName("dateLabel")
        self.bfTime = QLabel()
        self.bfTime.setObjectName("timeLabel")
        clk = QVBoxLayout()
        clk.setSpacing(0)
        clk.addWidget(self.bfDate)
        clk.addWidget(self.bfTime)
        cw = QWidget()
        cw.setLayout(clk)
        lay.addWidget(cw)

        # toggle idioma
        self._lang_btn = QPushButton(t("lang.btn"))
        self._lang_btn.setObjectName("ghost")
        self._lang_btn.setFixedWidth(46)
        self._lang_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._lang_btn.setToolTip("Cambiar idioma / Switch language")
        self._lang_btn.clicked.connect(self._toggle_lang)
        lay.addWidget(self._lang_btn)

        self.backBtn = QPushButton(t("bf.volver"))
        self.backBtn.setObjectName("ghost")
        self.backBtn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.backBtn.clicked.connect(self._go_back)
        # respiración neón cyan (regreso a CRIBA desde BLACKFORGE)
        apply_neon_breath(self.backBtn, color="#00DDF2", min_blur=6, max_blur=18, period_ms=6000)
        lay.addWidget(self.backBtn)
        return tb

    def _build_status_section(self) -> QFrame:
        tok = self.t
        card = QFrame()
        card.setObjectName("card")
        lay = QHBoxLayout(card)
        lay.setContentsMargins(tok.spacing(16), tok.spacing(16),
                               tok.spacing(16), tok.spacing(16))
        lay.setSpacing(tok.spacing(20))

        left = QVBoxLayout()
        left.setSpacing(tok.spacing(8))
        head = QHBoxLayout()
        self._status_title = QLabel(t("bf.estado"))
        self._status_title.setObjectName("sectionTitle")
        head.addWidget(self._status_title)
        head.addStretch(1)
        self._operativa_chip = make_chip(t("bf.operativa"), "guardada")
        head.addWidget(self._operativa_chip)
        left.addLayout(head)
        self._status_desc = QLabel(t("bf.estado.desc"))
        self._status_desc.setObjectName("sectionDesc")
        self._status_desc.setWordWrap(True)
        left.addWidget(self._status_desc)
        left.addStretch(1)
        lay.addLayout(left, 1)

        hero = self._build_hero()
        lay.addWidget(hero, 0)
        return card

    def _build_hero(self) -> QFrame:
        tok = self.t
        hero = QFrame()
        hero.setObjectName("bfHero")
        hero.setFixedSize(360, 230)
        g = QGridLayout(hero)
        g.setContentsMargins(0, 0, 0, 0)
        g.setSpacing(0)

        pix = QPixmap(str(DATA_ROOT / "assets" / "blackforge_hero.png"))
        self._hero_pixmap = pix
        img = QLabel()
        img.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if not pix.isNull():
            img.setPixmap(pix.scaled(360, 230, Qt.AspectRatioMode.KeepAspectRatio,
                                     Qt.TransformationMode.SmoothTransformation))
        g.addWidget(img, 0, 0)

        ov = QWidget()
        ov.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        ovl = QVBoxLayout(ov)
        ovl.setContentsMargins(tok.spacing(12), tok.spacing(12),
                               tok.spacing(12), tok.spacing(12))
        ovl.addStretch(1)
        bot = QHBoxLayout()
        ctx = QPushButton(t("bf.ver_contexto"))
        ctx.setObjectName("bf3d")
        ctx.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        ctx.setCursor(Qt.CursorShape.PointingHandCursor)
        ctx.clicked.connect(self._ver_contexto)
        bot.addWidget(ctx)
        bot.addStretch(1)
        ovl.addLayout(bot)
        g.addWidget(ov, 0, 0)

        glow = _HeroGlow([(0.30, 0.35), (0.62, 0.28), (0.48, 0.62),
                          (0.74, 0.55), (0.22, 0.66)])
        glow.start()
        g.addWidget(glow, 0, 0)
        return hero

    def _build_modes_card(self) -> QFrame:
        tok = self.t
        card = QFrame()
        card.setObjectName("card")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(tok.spacing(16), tok.spacing(16),
                               tok.spacing(16), tok.spacing(16))
        lay.setSpacing(tok.spacing(12))
        self._modos_title = QLabel(t("bf.modos"))
        self._modos_title.setObjectName("sectionTitle")
        lay.addWidget(self._modos_title)

        grid = QHBoxLayout()
        grid.setSpacing(tok.spacing(12))
        self._mode_cards: dict[str, QFrame] = {}
        self._mode_name_labels: dict[str, QLabel] = {}
        self._mode_desc_labels: dict[str, QLabel] = {}
        specs = [
            ("optimizado", "bf.modo.optimizado", "bf.modo.optimizado.desc"),
            ("asociativa",  "bf.modo.asociativa",  "bf.modo.asociativa.desc"),
            ("pura",        "bf.modo.pura",        "bf.modo.pura.desc"),
        ]
        for key, name_k, desc_k in specs:
            mc = QFrame()
            mc.setObjectName("bfSysCard")
            if key == self._mode:
                mc.setProperty("accent", "blackforge")
            ml = QVBoxLayout(mc)
            ml.setContentsMargins(tok.spacing(12), tok.spacing(12),
                                  tok.spacing(12), tok.spacing(12))
            ml.setSpacing(tok.spacing(8))
            nm = QLabel(t(name_k))
            nm.setObjectName("bfSysName")
            nm.setStyleSheet("color:#FBF3EA; font-size:13px; font-weight:700;")
            de = QLabel(t(desc_k))
            de.setObjectName("sectionDesc")
            de.setWordWrap(True)
            ml.addWidget(nm)
            ml.addWidget(de)
            mc.mousePressEvent = (lambda k=key:
                                  (lambda e: self._select_mode(k)))  # type: ignore[method-assign]
            self._mode_cards[key] = mc
            self._mode_name_labels[key] = nm
            self._mode_desc_labels[key] = de
            grid.addWidget(mc)
        grid.addStretch(1)
        lay.addLayout(grid)

        self._run_btn = QPushButton(t("bf.ejecutar"))
        self._run_btn.setObjectName("primary")
        self._run_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        apply_neon_breath(self._run_btn,
                          color="#FF6A00", min_blur=6, max_blur=18, period_ms=4000)
        self._run_btn.clicked.connect(self._on_execute)
        lay.addWidget(self._run_btn)
        return card

    def _build_ideas_card(self) -> QFrame:
        tok = self.t
        card = QFrame()
        card.setObjectName("card")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(tok.spacing(16), tok.spacing(16),
                               tok.spacing(16), tok.spacing(16))
        lay.setSpacing(tok.spacing(12))
        self._ideas_title = QLabel(t("bf.ideas"))
        self._ideas_title.setObjectName("sectionTitle")
        lay.addWidget(self._ideas_title)

        # interpretación de última ejecución
        self._interp_label = QLabel("")
        self._interp_label.setObjectName("sectionDesc")
        self._interp_label.setWordWrap(True)
        self._interp_label.hide()
        lay.addWidget(self._interp_label)

        table = QTableView()
        table.setObjectName("rankingTable")
        table.setAlternatingRowColors(True)
        table.setShowGrid(False)
        table.verticalHeader().setVisible(False)
        table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        table.setEditTriggers(QTableView.EditTrigger.NoEditTriggers)
        table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.ideasModel = _BFIdeasModel()
        table.setModel(self.ideasModel)
        hh = table.horizontalHeader()
        hh.setSectionResizeMode(0, hh.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(1, hh.ResizeMode.Stretch)
        hh.setSectionResizeMode(2, hh.ResizeMode.ResizeToContents)
        for col, w in ((3, 90), (4, 90), (5, 90)):
            hh.resizeSection(col, w)
        table.setMinimumHeight(180)
        lay.addWidget(table)
        self._populate_ideas()
        return card

    def _build_kpi_panel(self) -> QWidget:
        tok = self.t
        panel = QWidget()
        panel.setObjectName("centerColumn")
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(tok.spacing(12))

        # Cobertura
        cov = QFrame()
        cov.setObjectName("bfKpiCard")
        cl = QVBoxLayout(cov)
        cl.setContentsMargins(tok.spacing(12), tok.spacing(12),
                              tok.spacing(12), tok.spacing(12))
        cl.setSpacing(tok.spacing(8))
        self._kpi_cov_title = QLabel(t("kpi.cobertura"))
        self._kpi_cov_title.setObjectName("bfKpiHead")
        cl.addWidget(self._kpi_cov_title)
        donut = DonutChartWidget()
        ao = QColor(tok.accent_orange)
        grey = QColor(tok.text_muted)
        covered = self._metrics["coverage_pct"]
        donut.set_segments([("cov", covered, ao), ("rest", 100 - covered, grey)])
        donut.set_center(f"{covered}%", t("kpi.cubierto"))
        cl.addWidget(donut)
        leg = QHBoxLayout()
        leg.setSpacing(tok.spacing(8))
        self._kpi_cov_leg = LegendRow("#FF7A1A", t("kpi.cubierto"), f"{covered}%")
        leg.addWidget(self._kpi_cov_leg)
        leg.addStretch(1)
        cl.addLayout(leg)
        lay.addWidget(cov)

        # Integridad
        integ = QFrame()
        integ.setObjectName("bfKpiCard")
        il = QVBoxLayout(integ)
        il.setContentsMargins(tok.spacing(12), tok.spacing(12),
                              tok.spacing(12), tok.spacing(12))
        il.setSpacing(tok.spacing(8))
        self._kpi_int_title = QLabel(t("kpi.integridad"))
        self._kpi_int_title.setObjectName("bfKpiHead")
        il.addWidget(self._kpi_int_title)
        self._kpi_int_val = QLabel(f"⛨  94% {t('kpi.excelente')}")
        self._kpi_int_val.setObjectName("bfAlarms")
        il.addWidget(self._kpi_int_val)
        bar = SourceBarWidget(t("kpi.integridad"), 94)
        il.addWidget(bar)
        lay.addWidget(integ)

        # Verificador
        ver = QFrame()
        ver.setObjectName("bfKpiCard")
        vl = QVBoxLayout(ver)
        vl.setContentsMargins(tok.spacing(12), tok.spacing(12),
                              tok.spacing(12), tok.spacing(12))
        vl.setSpacing(tok.spacing(8))
        self._kpi_ver_title = QLabel(t("kpi.verificador"))
        self._kpi_ver_title.setObjectName("bfKpiHead")
        vl.addWidget(self._kpi_ver_title)
        self._kpi_ver_st = QLabel(t("kpi.activo"))
        self._kpi_ver_st.setObjectName("bfSysOk")
        vl.addWidget(self._kpi_ver_st)
        self._kpi_ver_ok = QLabel(t("kpi.todo_ok"))
        self._kpi_ver_ok.setObjectName("sectionDesc")
        vl.addWidget(self._kpi_ver_ok)
        lay.addWidget(ver)
        return panel

    # --- datos del catálogo -----------------------------------------------
    def _populate_ideas(self) -> None:
        rows = []
        for i, r in enumerate(self._metrics["top5"], start=1):
            rk = (r.get("risk_level") or "low").lower()
            pri_tier = r.get("activation_tier", "")
            nov_score = float(r.get("uniqueness_score", 0))
            rows.append({
                0: str(i),
                1: r.get("title", "—"),
                2: r.get("functional_category_primary") or r.get("source_family") or "—",
                3: _risk_label(rk),
                "risk_key": rk,
                4: t(_novelty_key(nov_score / 20)),   # uniqueness_score 0-20 → 0-1
                5: t(_priority_key(pri_tier)),
                "priority_key": pri_tier,
            })
        self.ideasModel.set_rows(rows)

    # --- interacción -------------------------------------------------------
    def _select_mode(self, key: str) -> None:
        self._mode = key
        for k, mc in self._mode_cards.items():
            mc.setProperty("accent", "blackforge" if k == key else None)
            mc.style().unpolish(mc)
            mc.style().polish(mc)

    _SPIN_CHARS = "◐◓◑◒"

    def _spin_tick(self) -> None:
        self._spin_phase = (self._spin_phase + 1) % len(self._SPIN_CHARS)
        if self._run_btn:
            self._run_btn.setText(
                f"{self._SPIN_CHARS[self._spin_phase]}  {t('bf.ejecutando')}")

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        if self._run_btn:
            self._run_btn.setEnabled(not busy)
        if busy:
            self._spin_phase = 0
            self._spin_timer.start()
        else:
            self._spin_timer.stop()
            if self._run_btn:
                self._run_btn.setText(t("bf.ejecutar"))

    def _on_execute(self) -> None:
        if self._busy:
            return
        self._set_busy(True)
        # Ejecutar de forma diferida para que el spinner aparezca
        QTimer.singleShot(30, self._do_execute)

    def _do_execute(self) -> None:
        from ..lottery import LotteryEngine
        from .i18n import lang as cur_lang
        try:
            recs = list(bf_records())
            if self._lottery_engine is None:
                methods = [dict(record) for record in recs]
                if not methods:
                    return
                self._lottery_engine = LotteryEngine.from_methods(
                    methods, seed=random.SystemRandom().randint(0, 2**31 - 1)
                )
            engine_mode = {
                "optimizado": "optimized",
                "asociativa": "associative",
                "pura": "pure",
            }[self._mode]
            self._lottery_engine.run_round(engine_mode, batch_size=12)
            ideas = self._lottery_engine.last_round_ideas
            if not ideas:
                return
            rows = []
            sentences = []
            lng = cur_lang()
            for i, idea in enumerate(ideas[:5], start=1):
                fmt = format_idea(idea, lng, i - 1)
                conv = idea.get("convergence") or {}
                via = float(conv.get("viability", 0.8) or 0.8)
                rk = ("high" if via < 0.5 else "medium" if via < 0.7 else "low_medium")
                rows.append({
                    0: str(i),
                    1: fmt["title"],
                    2: idea.get("family1") or idea.get("family") or "—",
                    3: _risk_label(rk),
                    "risk_key": rk,
                    4: fmt["novelty"],
                    5: fmt["quality"],
                    "priority_key": fmt["quality"],
                })
                sentences.append(f"{i}. {fmt['sentence']}")
            self.ideasModel.set_rows(rows)
            # Mostrar interpretación
            self._interp_label.setText("\n".join(sentences))
            self._interp_label.show()
            _fade_in(self._interp_label, 350)
            # Fade tabla
            _fade_in(self.ideasModel.parent() or self, 250)  # best-effort
        except Exception as exc:  # noqa: BLE001
            print("Blackforge execute error:", exc)
        finally:
            self._set_busy(False)

    def _ver_contexto(self) -> None:
        dlg = QDialog(self)
        dlg.setWindowTitle("CRIBA BLACKFORGE · BF-516")
        dlg.setMinimumSize(900, 600)
        vl = QVBoxLayout(dlg)
        vl.setContentsMargins(0, 0, 0, 0)
        lab = QLabel()
        lab.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lab.setStyleSheet(f"background:{self.t.bg_hero};")
        pix = self._hero_pixmap
        if not pix.isNull():
            lab.setPixmap(pix.scaled(
                dlg.width() - 40, dlg.height() - 40,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation))
        vl.addWidget(lab)
        _fade_in(lab, 300)
        dlg.exec()

    def _go_back(self) -> None:
        self.win.show_criba_page()

    def _toggle_lang(self) -> None:
        from .i18n import toggle
        toggle()

    # --- i18n refresh -------------------------------------------------------
    def _on_lang_change(self) -> None:
        self.backBtn.setText(t("bf.volver"))
        self._lang_btn.setText(t("lang.btn"))
        self._status_title.setText(t("bf.estado"))
        self._status_desc.setText(t("bf.estado.desc"))
        self._modos_title.setText(t("bf.modos"))
        self._ideas_title.setText(t("bf.ideas"))
        self._kpi_cov_title.setText(t("kpi.cobertura"))
        self._kpi_int_title.setText(t("kpi.integridad"))
        self._kpi_int_val.setText(f"⛨  94% {t('kpi.excelente')}")
        self._kpi_ver_title.setText(t("kpi.verificador"))
        self._kpi_ver_st.setText(t("kpi.activo"))
        self._kpi_ver_ok.setText(t("kpi.todo_ok"))
        if self._run_btn and not self._busy:
            self._run_btn.setText(t("bf.ejecutar"))
        for key, nm_lbl in self._mode_name_labels.items():
            nm_lbl.setText(t(f"bf.modo.{key}"))
        for key, de_lbl in self._mode_desc_labels.items():
            de_lbl.setText(t(f"bf.modo.{key}.desc"))
        self.ideasModel.refresh_headers()
        # Re-render tabla con nuevas etiquetas
        self._populate_ideas()

    # --- ciclo de vida -------------------------------------------------------
    def on_enter(self) -> None:
        now = datetime.now()
        meses = ["ENE", "FEB", "MAR", "ABR", "MAY", "JUN",
                 "JUL", "AGO", "SEP", "OCT", "NOV", "DIC"]
        self.bfDate.setText(f"{now.day:02d} {meses[now.month - 1]} {now.year}")
        self.bfTime.setText(now.strftime("%H:%M:%S"))

    def load_from_history(self, packet: dict[str, Any]) -> None:
        self.on_enter()
