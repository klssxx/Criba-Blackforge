"""CribaMainWindow — pantalla principal del contrato UI_CONTRACT_CRIBA.md.

Árbol normativo: WIDGET_TREE_CRIBA.md §1. Estados: STATE_MATRIX_CRIBA.md.
Datos reales del engine (activate/Storage); sin datos fake permanentes.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from PySide6.QtCore import QProcess, QThreadPool, QTimer, Qt
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QMainWindow,
                               QMessageBox, QPushButton, QScrollArea,
                               QToolButton, QVBoxLayout, QWidget)

from ..storage import Storage
from .panels import (build_idea_card, build_motor_card, build_ranking_card,
                     build_right_column, build_teaser_card)
from .theme import build_qss
from .tokens import load_tokens
from .i18n import on_change, t as _t
from .widgets import FooterSegment, NavButton, apply_neon_breath
from . import actions

NAV_SPEC = [
    ("navNuevaIdea", "◉", "Nueva idea", "Inicia el flujo, pide el problema base"),
    ("navGenerar", "⚙", "Generar", "Ejecuta los 16 operadores"),
    ("navEvaluar", "▥", "Evaluar", "Ranking por value_score"),
    ("navGuardar", "▣", "Guardar", "Persiste la idea en el catálogo"),
    ("navActualizar", "↻", "Actualizar innovaciones", "Tendencias, tecnología, diseño"),
    ("navHistorial", "◷", "Historial", "Ideas generadas antes"),
    ("navModelos", "◇", "Modelos IA", "Añadir GGUF y ajustar reasoning"),
    ("navBlackforge", "⛨", "Blackforge", "Panel de control BLACKFORCE"),
]


class CribaMainWindow(QMainWindow):
    def __init__(self, database: Any = None) -> None:
        super().__init__()
        # Force fresh token load (clears lru_cache for theme updates)
        from .tokens import reload_tokens
        reload_tokens()
        self.t = load_tokens()
        self.store = Storage(database)
        self.packet: dict[str, Any] | None = None
        self.problem: str = ""
        self.saved_ids: set[str] = set()
        self.sources_updated_at: datetime | None = None
        self.pool = QThreadPool.globalInstance()
        self.refs: dict[str, Any] = {}
        self._blackforge_process: QProcess | None = None
        self.setWindowTitle("CRIBA — Innovación sin límites")
        self.setMinimumSize(1360, 768)
        self.resize(1680, 1050)
        self.setStyleSheet(build_qss(self.t))
        self._build_ui()
        self._clock = QTimer(self)
        self._clock.setInterval(1000)
        self._clock.timeout.connect(self._tick_clock)
        self._clock.start()
        self._tick_clock()
        on_change(self._on_lang_change)
        actions.enter_s1(self)

    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        root = QWidget()
        root.setObjectName("appRoot")
        self.setCentralWidget(root)
        rl = QHBoxLayout(root)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(0)
        self.sidebar = self._build_sidebar()
        self.sidebar.setVisible(True)  # Visible por defecto en CRIBA
        rl.addWidget(self.sidebar)
        criba_page = QWidget()
        criba_page.setObjectName("mainColumn")
        ml = QVBoxLayout(criba_page)
        ml.setContentsMargins(0, 0, 0, 0)
        ml.setSpacing(0)
        ml.addWidget(self._build_topbar())
        ml.addWidget(self._build_content(), 1)
        ml.addWidget(self._build_footer())
        rl.addWidget(criba_page, 1)

    def show_criba_page(self) -> None:
        """Restore CRIBA after the standalone BLACKFORGE app exits."""
        self.show()
        self.raise_()
        self.activateWindow()

    def show_blackforge_page(
        self, history_packet: dict[str, Any] | None = None
    ) -> None:
        """Launch BLACKFORGE as a separate, shell-free child process.

        ``history_packet`` is accepted for compatibility with the history
        action.  The active problem is passed as one bounded argv value; no
        shell is invoked or command line is interpolated.
        """
        del history_packet
        if (
            self._blackforge_process is not None
            and self._blackforge_process.state()
            != QProcess.ProcessState.NotRunning
        ):
            self.hide()
            return

        from .app_bridge import (
            BlackforgeLaunchError,
            resolve_blackforge_launch,
        )

        try:
            launch = resolve_blackforge_launch()
        except BlackforgeLaunchError as exc:
            QMessageBox.warning(self, "CRIBA · BLACKFORGE", str(exc))
            return

        process = QProcess(self)
        process.setProgram(launch.program)
        arguments = list(launch.arguments)
        if self.problem:
            # QProcess receives an argv list directly: no shell interpolation.
            arguments.extend(("--query", self.problem[:20_000]))
        process.setArguments(arguments)
        if launch.arguments:
            process.setWorkingDirectory(str(Path(__file__).resolve().parents[3]))
        else:
            process.setWorkingDirectory(str(Path(launch.program).resolve().parent))
        process.started.connect(self.hide)
        process.finished.connect(self._on_blackforge_finished)
        process.errorOccurred.connect(self._on_blackforge_error)
        self._blackforge_process = process
        process.start()

    def _on_blackforge_finished(
        self, exit_code: int, exit_status: QProcess.ExitStatus
    ) -> None:
        del exit_code, exit_status
        process = self._blackforge_process
        self._blackforge_process = None
        if process is not None:
            process.deleteLater()
        self.show_criba_page()

    def _on_blackforge_error(self, error: QProcess.ProcessError) -> None:
        if error == QProcess.ProcessError.FailedToStart:
            process = self._blackforge_process
            detail = process.errorString() if process is not None else str(error)
            self._blackforge_process = None
            QMessageBox.warning(
                self,
                "CRIBA · BLACKFORGE",
                f"No se pudo iniciar BLACKFORGE:\n{detail}",
            )
            self.show_criba_page()


    def _build_sidebar(self) -> QFrame:
        t = self.t
        sb = QFrame()
        sb.setObjectName("sidebar")
        sb.setFixedWidth(t.layout("sidebar_width"))
        lay = QVBoxLayout(sb)
        lay.setContentsMargins(t.spacing(16), t.spacing(16),
                               t.spacing(16), t.spacing(16))
        lay.setSpacing(t.spacing(8))
        a, b = t.gradient("brand")
        logo = QLabel(f'<span style="color:{a}">CRI</span>'
                      f'<span style="color:{b}">BA</span>')
        logo.setObjectName("brandLogo")
        tag = QLabel("INNOVACIÓN SIN LÍMITES")
        tag.setObjectName("brandTagline")
        lay.addWidget(logo)
        lay.addWidget(tag)
        lay.addSpacing(t.spacing(24))
        self.nav: dict[str, NavButton] = {}
        for key, glyph, text, sub in NAV_SPEC:
            btn = NavButton(glyph, text, sub, blackforge=(key == "navBlackforge"))
            self.nav[key] = btn
            lay.addWidget(btn)
        lay.addStretch(1)
        teaser = QFrame()
        teaser.setObjectName("blackforgeTeaserMini")
        teaser.setCursor(Qt.CursorShape.PointingHandCursor)
        tl = QVBoxLayout(teaser)
        tl.setContentsMargins(t.spacing(12), t.spacing(12),
                              t.spacing(12), t.spacing(12))
        tl.setSpacing(2)
        bfl = QLabel("BLACKFORGE")
        bfl.setObjectName("bfMiniLogo")
        bft = QLabel("PODER SIN LÍMITES")
        bft.setObjectName("bfMiniTag")
        tl.addWidget(bfl)
        tl.addWidget(bft)
        teaser.mousePressEvent = lambda e: actions.on_blackforge(self)  # type: ignore[method-assign]
        lay.addWidget(teaser)
        # conexiones nav
        self.nav["navNuevaIdea"].clicked.connect(lambda: actions.on_nueva_idea(self))
        self.nav["navGenerar"].clicked.connect(lambda: actions.on_generar(self))
        self.nav["navEvaluar"].clicked.connect(lambda: actions.on_evaluar(self))
        self.nav["navGuardar"].clicked.connect(lambda: actions.on_guardar(self))
        self.nav["navActualizar"].clicked.connect(lambda: actions.on_actualizar(self))
        self.nav["navHistorial"].clicked.connect(lambda: actions.on_historial(self))
        self.nav["navModelos"].clicked.connect(lambda: actions.on_modelos(self))
        self.nav["navBlackforge"].clicked.connect(lambda: actions.on_blackforge(self))
        # contorno neón turquesa que respira (3s sube / 3s baja) en bucle
        apply_neon_breath(self.nav["navBlackforge"])
        return sb

    def _build_topbar(self) -> QFrame:
        t = self.t
        tb = QFrame()
        tb.setObjectName("topbar")
        tb.setFixedHeight(t.layout("topbar_height"))
        lay = QHBoxLayout(tb)
        lay.setContentsMargins(t.spacing(20), t.spacing(12),
                               t.spacing(20), t.spacing(12))
        lay.setSpacing(t.spacing(16))
        greet = QVBoxLayout()
        greet.setSpacing(0)
        self.greetingTitle = QLabel("Hola, Innovador")
        self.greetingTitle.setObjectName("greetingTitle")
        self.greetingSub = QLabel("Listo para transformar ideas en impacto")
        self.greetingSub.setObjectName("greetingSub")
        greet.addWidget(self.greetingTitle)
        greet.addWidget(self.greetingSub)
        lay.addLayout(greet)
        lay.addStretch(1)
        badge = QHBoxLayout()
        badge.setSpacing(6)
        self.sessionDot = QLabel("●")
        self.sessionLabel = QLabel("Sin sesión")
        self.sessionLabel.setObjectName("greetingSub")
        badge.addWidget(self.sessionDot)
        badge.addWidget(self.sessionLabel)
        bw = QWidget()
        bw.setLayout(badge)
        lay.addWidget(bw)
        self.modeBadge = QLabel("MODO: INNOVACIÓN")
        self.modeBadge.setObjectName("chip")
        self.modeBadge.setProperty("kind", "eval")
        lay.addWidget(self.modeBadge)
        clock = QVBoxLayout()
        clock.setSpacing(0)
        self.dateLabel = QLabel()
        self.dateLabel.setObjectName("dateLabel")
        self.timeLabel = QLabel()
        self.timeLabel.setObjectName("timeLabel")
        clock.addWidget(self.dateLabel)
        clock.addWidget(self.timeLabel)
        cw = QWidget()
        cw.setLayout(clock)
        lay.addWidget(cw)
        self._lang_btn_main = QPushButton(_t("lang.btn"))
        self._lang_btn_main.setObjectName("ghost")
        self._lang_btn_main.setFixedWidth(46)
        self._lang_btn_main.setCursor(Qt.CursorShape.PointingHandCursor)
        self._lang_btn_main.setToolTip("Cambiar idioma / Switch language")
        self._lang_btn_main.clicked.connect(self._toggle_lang)
        lay.addWidget(self._lang_btn_main)
        notif = QToolButton()
        notif.setObjectName("notifBtn")
        notif.setText("◔")
        notif.setToolTip("Notificaciones")
        lay.addWidget(notif)
        return tb

    def _build_content(self) -> QWidget:
        t = self.t
        row = QWidget()
        row.setObjectName("contentRow")
        lay = QHBoxLayout(row)
        lay.setContentsMargins(t.spacing(20), t.spacing(20),
                               t.spacing(20), t.spacing(20))
        lay.setSpacing(t.spacing(20))
        center_scroll = QScrollArea()
        center_scroll.setObjectName("centerScroll")
        center_scroll.setWidgetResizable(True)
        center_scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        center_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        center = QWidget()
        center.setObjectName("centerColumn")
        cl = QVBoxLayout(center)
        cl.setContentsMargins(0, 0, 6, 0)
        cl.setSpacing(t.spacing(16))
        # banner error S9 (oculto por defecto)
        self.errorBanner = QFrame()
        self.errorBanner.setObjectName("errorBanner")
        eb = QHBoxLayout(self.errorBanner)
        eb.setContentsMargins(t.spacing(12), t.spacing(8),
                              t.spacing(12), t.spacing(8))
        self.errorBannerText = QLabel()
        self.errorBannerText.setObjectName("errorBannerText")
        self.errorBannerText.setWordWrap(True)
        eb.addWidget(QLabel("⚠"))
        eb.addWidget(self.errorBannerText, 1)
        from PySide6.QtWidgets import QPushButton
        self.errorDismissBtn = QPushButton("Cerrar")
        self.errorDismissBtn.setObjectName("ghost")
        self.errorDismissBtn.clicked.connect(lambda: self.errorBanner.hide())
        eb.addWidget(self.errorDismissBtn)
        cl.addWidget(self.errorBanner)
        self.errorBanner.hide()
        cl.addWidget(build_motor_card(t, self.refs))
        cl.addWidget(build_idea_card(t, self.refs))
        cl.addWidget(build_ranking_card(t, self.refs))
        cl.addWidget(build_teaser_card(t, self.refs))
        cl.addStretch(1)
        center_scroll.setWidget(center)
        lay.addWidget(center_scroll, 1)
        right_scroll = QScrollArea()
        right_scroll.setObjectName("rightScroll")
        right_scroll.setWidgetResizable(True)
        right_scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        right_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        width = t.layout("right_column_width")
        screen = self.screen()
        if screen and screen.availableGeometry().width() < 1500:
            width = t.layout("right_column_width_min")
        right_scroll.setFixedWidth(width)
        right_scroll.setWidget(build_right_column(t, self.refs))
        lay.addWidget(right_scroll)
        # conexiones bloque derecho / central
        self.refs["actualizarFuentesBtn"].clicked.connect(
            lambda: actions.on_actualizar(self))
        self.refs["historialCompletoBtn"].clicked.connect(
            lambda: actions.on_historial(self))
        self.refs["verTodasBtn"].clicked.connect(
            lambda: actions.on_ver_todas(self))
        self.refs["irBlackforgeBtn"].clicked.connect(
            lambda: actions.on_blackforge(self))
        self.refs["rankingTabs"].currentChanged.connect(
            lambda i: actions.on_tab_changed(self, i))
        return row

    def _build_footer(self) -> QFrame:
        t = self.t
        foot = QFrame()
        foot.setObjectName("footerStrip")
        foot.setFixedHeight(t.layout("footer_height"))
        lay = QHBoxLayout(foot)
        lay.setContentsMargins(t.spacing(20), 4, t.spacing(20), 4)
        lay.setSpacing(t.spacing(12))
        self.footerSegs: dict[str, FooterSegment] = {}
        specs = [("fsModelo", "Modelo activo"), ("fsSesion", "ID de sesión"),
                 ("fsIdeas", "Ideas generadas"),
                 ("fsConvergencia", "Convergencia global"),
                 ("fsUltima", "Última actualización"),
                 ("fsFuentes", "Fuentes actualizadas")]
        for i, (key, label) in enumerate(specs):
            seg = FooterSegment(label)
            self.footerSegs[key] = seg
            lay.addWidget(seg)
            if i < len(specs) - 1:
                div = QFrame()
                div.setObjectName("vline")
                lay.addWidget(div)
        lay.addStretch(1)
        # 1360x768: los 6 segmentos siempre visibles (contrato: footer
        # completo); en pantallas estrechas solo se compacta el espaciado.
        screen = self.screen()
        if screen and screen.availableGeometry().width() < 1500:
            lay.setSpacing(t.spacing(8))
            lay.setContentsMargins(t.spacing(12), 4, t.spacing(12), 4)
        return foot

    # ------------------------------------------------------------------
    def _toggle_lang(self) -> None:
        from .i18n import toggle
        toggle()

    def _on_lang_change(self) -> None:
        from .i18n import t
        self._lang_btn_main.setText(t("lang.btn"))
        self.greetingTitle.setText(t("greeting.title"))
        self.greetingSub.setText(t("greeting.sub"))
        self.modeBadge.setText(t("mode.innovacion"))
        for key, spec_txt, spec_sub in [
            ("navNuevaIdea",   "nav.nueva_idea",   "nav.nueva_idea.sub"),
            ("navGenerar",     "nav.generar",       "nav.generar.sub"),
            ("navEvaluar",     "nav.evaluar",       "nav.evaluar.sub"),
            ("navGuardar",     "nav.guardar",       "nav.guardar.sub"),
            ("navActualizar",  "nav.actualizar",    "nav.actualizar.sub"),
            ("navHistorial",   "nav.historial",     "nav.historial.sub"),
            ("navBlackforge",  "nav.blackforge",    "nav.blackforge.sub"),
        ]:
            btn = self.nav.get(key)
            if btn:
                btn._text.setText(t(spec_txt))
                btn._sub.setText(t(spec_sub))
                btn._default_sub = t(spec_sub)

    # ------------------------------------------------------------------
    def _tick_clock(self) -> None:
        now = datetime.now()
        dias = ["LUN", "MAR", "MIÉ", "JUE", "VIE", "SÁB", "DOM"]
        meses = ["ENE", "FEB", "MAR", "ABR", "MAY", "JUN",
                 "JUL", "AGO", "SEP", "OCT", "NOV", "DIC"]
        self.dateLabel.setText(
            f"{dias[now.weekday()]} {now.day} {meses[now.month - 1]} {now.year}")
        self.timeLabel.setText(now.strftime("%H:%M:%S"))
        actions.refresh_sources_freshness(self)
