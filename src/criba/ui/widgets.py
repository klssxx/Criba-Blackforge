"""Widgets custom reutilizables del contrato WIDGET_TREE_CRIBA.md §2.

Todos leen tokens desde theme_criba.json; nada hardcodeado fuera de tokens.
Los widgets pintados con QPainter (gauge, donut, histograma, conectores) son
la excepción permitida al QSS global (STYLE_GUIDE §6).
"""
from __future__ import annotations

from PySide6.QtCore import (
    Property,
    QEasingCurve,
    QObject,
    QPropertyAnimation,
    QRectF,
    Qt,
    QTimer,
)
from PySide6.QtGui import QColor, QConicalGradient, QFont, QPainter, QPen
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from .tokens import Tokens, load_tokens


def _qcolor(hex_or_rgba: str) -> QColor:
    if hex_or_rgba.startswith("rgba"):
        vals = hex_or_rgba[hex_or_rgba.index("(") + 1:hex_or_rgba.index(")")].split(",")
        r, g, b = (int(v) for v in vals[:3])
        a = float(vals[3])
        c = QColor(r, g, b)
        c.setAlphaF(a)
        return c
    return QColor(hex_or_rgba)


def _repolish(w: QWidget) -> None:
    w.style().unpolish(w)
    w.style().polish(w)
    w.update()


def make_glow(level: int, t: Tokens | None = None) -> QGraphicsDropShadowEffect:
    """Glow contractual: nivel 1 (activo) / nivel 2 (SOLO gauge)."""
    t = t or load_tokens()
    blur, color = t.glow(level)
    eff = QGraphicsDropShadowEffect()
    eff.setBlurRadius(blur)
    eff.setOffset(0, 0)
    eff.setColor(_qcolor(color))
    return eff


# ---------------------------------------------------------------------------
# 2.14 NavButton
# ---------------------------------------------------------------------------
class NavButton(QPushButton):
    """Botón de navegación del sidebar (UI_CONTRACT §5).

    Estados: normal | running | done | error (propiedad dinámica 'navstate')
    + checked (activo) + property 'suggested' (siguiente acción sugerida).
    """

    def __init__(self, icon_glyph: str, text: str, subtitle: str,
                 blackforge: bool = False, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        t = load_tokens()
        self.setObjectName("navbtnBlackforge" if blackforge else "navbtn")
        self.setCheckable(not blackforge)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(t.layout("nav_button_height"))
        self._default_sub = subtitle
        lay = QHBoxLayout(self)
        lay.setContentsMargins(t.spacing(12), t.spacing(4), t.spacing(8), t.spacing(4))
        lay.setSpacing(t.spacing(8))
        self._icon = QLabel(icon_glyph)
        self._icon.setObjectName("navIcon")
        self._icon.setFixedWidth(t.icon_size("md") + 4)
        col = QVBoxLayout()
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(0)
        self._text = QLabel(text)
        self._text.setObjectName("navText")
        self._sub = QLabel(subtitle)
        self._sub.setObjectName("navSub")
        self._sub.setWordWrap(False)
        col.addWidget(self._text)
        col.addWidget(self._sub)
        lay.addWidget(self._icon)
        lay.addLayout(col, 1)
        self._spin_timer = QTimer(self)
        self._spin_timer.setInterval(120)
        self._spin_timer.timeout.connect(self._spin_tick)
        self._spin_phase = 0
        self._icon_glyph = icon_glyph
        self.set_state("normal")

    _SPIN = "◐◓◑◒"

    def _spin_tick(self) -> None:
        self._spin_phase = (self._spin_phase + 1) % len(self._SPIN)
        self._icon.setText(self._SPIN[self._spin_phase])

    def set_state(self, state: str, msg: str | None = None) -> None:
        """state: normal | running | done | error (UI_CONTRACT §5)."""
        self._state = state
        for w in (self, self._sub):
            w.setProperty("navstate", state)
        if state == "running":
            self._spin_timer.start()
            self.setEnabled(False)
            self._sub.setText(msg or "Ejecutando...")
        else:
            self._spin_timer.stop()
            self._icon.setText("✓" if state == "done" else
                               ("!" if state == "error" else self._icon_glyph))
            self.setEnabled(True)
            self._sub.setText(msg if (state == "error" and msg) else self._default_sub)
            if state == "done":
                QTimer.singleShot(1200, self._back_to_normal)
        for w in (self, self._sub):
            _repolish(w)

    def _back_to_normal(self) -> None:
        if self._state == "done":
            self.set_state("normal")

    def set_suggested(self, on: bool) -> None:
        self.setProperty("suggested", "true" if on else "false")
        self.setGraphicsEffect(make_glow(1) if on else None)
        _repolish(self)


# ---------------------------------------------------------------------------
# 2.1 PipelineStageWidget + 2.2 PipelineConnector
# ---------------------------------------------------------------------------
class PipelineStageWidget(QFrame):
    """Etapa del Motor de Innovación. set_state(pending|active|done|error)."""

    def __init__(self, icon_glyph: str, title: str, micro: str,
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._t = load_tokens()
        self._state = "pending"
        self._glyph = icon_glyph
        lay = QVBoxLayout(self)
        lay.setContentsMargins(4, 4, 4, 4)
        lay.setSpacing(4)
        self._medal = QLabel(icon_glyph)
        self._medal.setAlignment(Qt.AlignmentFlag.AlignCenter)
        d = self._t.icon_size("lg") + 20
        self._medal.setFixedSize(d, d)
        self._title = QLabel(title)
        self._title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ts = self._t.type_scale("h3")
        f = self._title.font(); f.setPixelSize(ts.size_px); f.setWeight(QFont.Weight(600))
        self._title.setFont(f)
        self._micro = QLabel(micro)
        self._micro.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._micro.setWordWrap(True)
        cap = self._t.type_scale("caption")
        f2 = self._micro.font(); f2.setPixelSize(cap.size_px)
        self._micro.setFont(f2)
        self._micro.setStyleSheet("")  # colors handled in _apply
        lay.addWidget(self._medal, 0, Qt.AlignmentFlag.AlignHCenter)
        lay.addWidget(self._title)
        lay.addWidget(self._micro)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self._spin_timer = QTimer(self)
        self._spin_timer.setInterval(120)
        self._spin_timer.timeout.connect(self._spin_tick)
        self._spin_phase = 0
        self._apply()

    _SPIN = "◐◓◑◒"

    def _spin_tick(self) -> None:
        self._spin_phase = (self._spin_phase + 1) % len(self._SPIN)
        self._medal.setText(self._SPIN[self._spin_phase])

    def state(self) -> str:
        return self._state

    def set_state(self, state: str, spinning: bool = False) -> None:
        self._state = state
        if spinning and state == "active":
            self._spin_timer.start()
        else:
            self._spin_timer.stop()
            self._medal.setText("✓" if state == "done" else
                                ("!" if state == "error" else self._glyph))
        self._apply()

    def _apply(self) -> None:
        t = self._t
        border = {"pending": t.border_soft, "active": t.accent_cyan,
                  "done": t.success, "error": t.error}[self._state]
        icon_col = {"pending": t.text_muted, "active": t.accent_cyan,
                    "done": t.success, "error": t.error}[self._state]
        d = self._medal.width()
        # medallón circular: único setStyleSheet permitido (widget custom pintado)
        self._medal.setStyleSheet(
            f"border:2px solid {border}; border-radius:{d // 2}px;"
            f" color:{icon_col}; font-size:{t.icon_size('lg') - 6}px;"
            f" background:{t.bg_inset};")
        self._title.setStyleSheet(f"color:{t.text_primary}; border:none;")
        self._micro.setStyleSheet(f"color:{t.text_muted}; border:none;")
        self.setGraphicsEffect(make_glow(1, t) if self._state == "active" else None)


class PipelineConnector(QWidget):
    """Línea 2px entre etapas; set_lit(True) la tiñe accent.cyan."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._lit = False
        self._t = load_tokens()
        self.setFixedWidth(28)
        self.setMinimumHeight(10)

    def set_lit(self, lit: bool) -> None:
        self._lit = lit
        self.update()

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        color = _qcolor(self._t.accent_cyan if self._lit else self._t.border_soft)
        pen = QPen(color, 2)
        p.setPen(pen)
        y = self.height() * 0.32  # a la altura del medallón
        p.drawLine(2, int(y), self.width() - 2, int(y))
        p.end()


# ---------------------------------------------------------------------------
# 2.3 MetricWidget
# ---------------------------------------------------------------------------
class MetricWidget(QWidget):
    def __init__(self, label: str, value: str = "—",
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(2)
        self._value = QLabel(value)
        self._value.setObjectName("metricValue")
        self._label = QLabel(label)
        self._label.setObjectName("metricLabel")
        lay.addWidget(self._value)
        lay.addWidget(self._label)

    def set_value(self, value: str) -> None:
        self._value.setText(value)


# ---------------------------------------------------------------------------
# 2.4 ValueScoreGauge
# ---------------------------------------------------------------------------
class ValueScoreGauge(QWidget):
    """Gauge circular 270° con degradado grad.brand. Glow nivel 2 (único)."""

    def __init__(self, parent: QWidget | None = None,
                 diameter: int | None = None) -> None:
        super().__init__(parent)
        self._t = load_tokens()
        d = diameter if diameter is not None else self._t.layout("gauge_diameter")
        self._diam = d
        self.setFixedSize(d + 20, d + 44)
        self._score = 0.0
        self._percentile = "Pendiente"
        self._inner_label = "VALUE_SCORE"
        self.setGraphicsEffect(make_glow(2, self._t))
        self._anim = QPropertyAnimation(self, b"score", self)
        self._anim.setDuration(300)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    def get_score(self) -> float:
        return self._score

    def _set_score_prop(self, v: float) -> None:
        # value_score real puede superar 1.0 (evidence*novelty/cost); se guarda
        # el valor REAL (se muestra tal cual) y el arco se satura en 1.0.
        self._score = max(0.0, float(v))
        self.update()

    score = Property(float, get_score, _set_score_prop)

    def set_score(self, value: float, animate: bool = True) -> None:
        if animate:
            self._anim.stop()
            self._anim.setStartValue(self._score)
            self._anim.setEndValue(max(0.0, value))
            self._anim.start()
        else:
            self._set_score_prop(value)

    def set_percentile(self, text: str) -> None:
        self._percentile = text
        self.update()

    def paintEvent(self, event) -> None:
        t = self._t
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        d = self._diam
        stroke = 10
        rect = QRectF(10 + stroke / 2, 8 + stroke / 2, d - stroke, d - stroke)
        start_deg, span_deg = 225, -270  # 270° arc, gap at bottom
        # pista
        p.setPen(QPen(_qcolor(t.bg_inset), stroke, Qt.PenStyle.SolidLine,
                      Qt.PenCapStyle.RoundCap))
        p.drawArc(rect, start_deg * 16, span_deg * 16)
        # progreso con degradado naranja (BLACKFORGE)
        a, b = t.gradient("blackforge")
        grad = QConicalGradient(rect.center(), start_deg)
        grad.setColorAt(0.0, _qcolor(a))
        grad.setColorAt(0.75, _qcolor(b))
        grad.setColorAt(1.0, _qcolor(b))
        p.setPen(QPen(grad, stroke, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawArc(rect, start_deg * 16, int(span_deg * 16 * min(1.0, self._score)))
        # centro
        disp = t.type_scale("display")
        f = p.font(); f.setPixelSize(disp.size_px); f.setWeight(QFont.Weight(800))
        p.setFont(f)
        p.setPen(_qcolor(t.text_primary))
        p.drawText(rect, Qt.AlignmentFlag.AlignCenter, f"{self._score:.2f}")
        cap = t.type_scale("caption")
        f2 = p.font(); f2.setPixelSize(cap.size_px); f2.setWeight(QFont.Weight(500))
        p.setFont(f2)
        p.setPen(_qcolor(t.text_muted))
        label_rect = QRectF(rect.x(), rect.y() + rect.height() * 0.66,
                            rect.width(), 16)
        p.drawText(label_rect, Qt.AlignmentFlag.AlignHCenter, self._inner_label)
        # percentil bajo el gauge
        p.setPen(_qcolor(t.accent_violet))
        foot = QRectF(0, 8 + d + 4, self.width(), 24)
        p.drawText(foot, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
                   self._percentile)
        p.end()


# ---------------------------------------------------------------------------
# 2.8 HistogramWidget
# ---------------------------------------------------------------------------
class HistogramWidget(QWidget):
    """Histograma vertical chart.2; barra máxima resaltada + etiqueta."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._t = load_tokens()
        self._bins: list[tuple[float, int]] = []
        self.setMinimumHeight(110)

    def set_bins(self, bins: list[tuple[float, int]]) -> None:
        self._bins = list(bins)
        self.update()

    def paintEvent(self, event) -> None:
        t = self._t
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if not self._bins:
            p.setPen(_qcolor(t.text_muted))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter,
                       "Sin datos de evaluación")
            p.end()
            return
        counts = [c for _, c in self._bins]
        peak = max(counts) or 1
        peak_idx = counts.index(max(counts))
        n = len(self._bins)
        gap = 6
        top_pad, bottom_pad = 18, 14
        bw = max(6, (self.width() - gap * (n + 1)) // n)
        h_avail = self.height() - top_pad - bottom_pad
        cap = t.type_scale("caption")
        f = p.font(); f.setPixelSize(cap.size_px)
        p.setFont(f)
        for i, (edge, count) in enumerate(self._bins):
            x = gap + i * (bw + gap)
            bh = max(3, int(h_avail * (count / peak)))
            y = top_pad + (h_avail - bh)
            color = _qcolor(t.chart(2))
            if i != peak_idx:
                color.setAlphaF(0.55)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(color)
            p.drawRoundedRect(x, y, bw, bh, 3, 3)
            if i == peak_idx:
                p.setPen(_qcolor(t.text_primary))
                p.drawText(QRectF(x - gap, 2, bw + 2 * gap, 14),
                           Qt.AlignmentFlag.AlignHCenter, f"{edge:.2f}")
            # eje x: primera y última etiqueta
            if i in (0, n - 1):
                p.setPen(_qcolor(t.text_muted))
                p.drawText(QRectF(x - gap, self.height() - 13, bw + 2 * gap, 12),
                           Qt.AlignmentFlag.AlignHCenter, f"{edge:.1f}")
        p.end()


# ---------------------------------------------------------------------------
# 2.9 SourceBarWidget
# ---------------------------------------------------------------------------
class SourceBarWidget(QWidget):
    def __init__(self, label: str, percent: int = 0,
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        t = load_tokens()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(3)
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        self._label = QLabel(label)
        self._label.setObjectName("metricLabel")
        self._pct = QLabel(f"{percent}%")
        self._pct.setObjectName("footerVal")
        row.addWidget(self._label, 1)
        row.addWidget(self._pct)
        self._bar = QProgressBar()
        self._bar.setObjectName("sourceBar")
        self._bar.setRange(0, 100)
        self._bar.setTextVisible(False)
        self._bar.setFixedHeight(6)
        lay.addLayout(row)
        lay.addWidget(self._bar)
        self.set_percent(percent)

    def set_percent(self, percent: int) -> None:
        percent = max(0, min(100, int(percent)))
        self._bar.setValue(percent)
        self._pct.setText(f"{percent}%")


# ---------------------------------------------------------------------------
# 2.10 DonutChartWidget
# ---------------------------------------------------------------------------
class DonutChartWidget(QWidget):
    """Donut con huecos de 2° y centro de texto (STYLE_GUIDE §4.10)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._t = load_tokens()
        self._segments: list[tuple[str, float, QColor]] = []
        self._center = ("0", "ideas totales")
        self.setMinimumSize(130, 130)

    def set_segments(self, segments: list[tuple[str, float, QColor]]) -> None:
        self._segments = list(segments)
        self.update()

    def set_center(self, big: str, small: str) -> None:
        self._center = (big, small)
        self.update()

    def paintEvent(self, event) -> None:
        t = self._t
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        side = min(self.width(), self.height())
        ring = 20
        rect = QRectF((self.width() - side) / 2 + ring / 2 + 2,
                      (self.height() - side) / 2 + ring / 2 + 2,
                      side - ring - 4, side - ring - 4)
        total = sum(v for _, v, _ in self._segments)
        if total <= 0:
            p.setPen(QPen(_qcolor(t.bg_inset), ring))
            p.drawArc(rect, 0, 360 * 16)
            p.setPen(_qcolor(t.text_muted))
            p.drawText(rect, Qt.AlignmentFlag.AlignCenter, "Sin datos")
            p.end()
            return
        gap_deg = 2.0
        start = 90.0
        for _, value, color in self._segments:
            frac = value / total
            span = max(0.0, frac * 360.0 - gap_deg)
            p.setPen(QPen(color, ring, Qt.PenStyle.SolidLine,
                          Qt.PenCapStyle.FlatCap))
            p.drawArc(rect, int(start * 16), int(-span * 16))
            start -= frac * 360.0
        h2 = t.type_scale("h2")
        f = p.font(); f.setPixelSize(h2.size_px); f.setWeight(QFont.Weight(700))
        p.setFont(f)
        p.setPen(_qcolor(t.text_primary))
        up = QRectF(rect.x(), rect.y() + rect.height() * 0.28, rect.width(), 22)
        p.drawText(up, Qt.AlignmentFlag.AlignHCenter, self._center[0])
        cap = t.type_scale("caption")
        f2 = p.font(); f2.setPixelSize(cap.size_px); f2.setWeight(QFont.Weight(500))
        p.setFont(f2)
        p.setPen(_qcolor(t.text_muted))
        low = QRectF(rect.x(), rect.y() + rect.height() * 0.52, rect.width(), 16)
        p.drawText(low, Qt.AlignmentFlag.AlignHCenter, self._center[1])
        p.end()


class LegendRow(QWidget):
    """Punto de color + etiqueta + % (leyenda del donut)."""

    def __init__(self, color: str, label: str, pct: str,
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)
        dot = QLabel("●")
        dot.setStyleSheet(f"color:{color}; font-size:10px; background:transparent;")
        lbl = QLabel(label)
        lbl.setObjectName("metricLabel")
        val = QLabel(pct)
        val.setObjectName("footerVal")
        lay.addWidget(dot)
        lay.addWidget(lbl, 1)
        lay.addWidget(val)


# ---------------------------------------------------------------------------
# 2.11 ActivityItemWidget
# ---------------------------------------------------------------------------
class ActivityItemWidget(QWidget):
    """[timestamp][punto semántico][texto] (STYLE_GUIDE §4.11)."""

    KIND_TOKEN = {"success": "success", "blue": "accent_blue",
                  "cyan": "accent_cyan", "error": "error"}

    def __init__(self, timestamp: str, kind: str, text: str,
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        t = load_tokens()
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 2, 0, 2)
        lay.setSpacing(8)
        ts = QLabel(timestamp)
        ts.setObjectName("footerVal")
        ts.setStyleSheet(f"color:{t.text_muted};")
        ts.setFixedWidth(42)
        color = getattr(t, self.KIND_TOKEN.get(kind, "accent_cyan"))
        dot = QLabel("●")
        dot.setStyleSheet(f"color:{color}; font-size:9px; background:transparent;")
        body = QLabel(text)
        body.setObjectName("metricLabel")
        body.setStyleSheet(f"color:{t.text_primary};")
        body.setWordWrap(True)
        lay.addWidget(ts, 0, Qt.AlignmentFlag.AlignTop)
        lay.addWidget(dot, 0, Qt.AlignmentFlag.AlignTop)
        lay.addWidget(body, 1)


# ---------------------------------------------------------------------------
# 2.12 FeatureWidget (teaser Blackforge)
# ---------------------------------------------------------------------------
class FeatureWidget(QWidget):
    def __init__(self, icon_glyph: str, title: str, micro: str,
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        t = load_tokens()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(4, 4, 4, 4)
        lay.setSpacing(2)
        ic = QLabel(icon_glyph)
        ic.setStyleSheet(f"color:{t.accent_violet}; font-size:{t.icon_size('lg') - 8}px;"
                         " background:transparent;")
        ic.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        ti = QLabel(title)
        ti.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        ti.setStyleSheet(f"color:{t.text_primary}; font-size:11px; font-weight:700;"
                         " background:transparent;")
        mi = QLabel(micro)
        mi.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        mi.setWordWrap(True)
        mi.setStyleSheet(f"color:{t.text_muted}; font-size:10px; background:transparent;")
        lay.addWidget(ic)
        lay.addWidget(ti)
        lay.addWidget(mi)


# ---------------------------------------------------------------------------
# 2.13 FooterSegment
# ---------------------------------------------------------------------------
class FooterSegment(QWidget):
    def __init__(self, label: str, value: str = "—",
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)
        self._key = QLabel(label)
        self._key.setObjectName("footerKey")
        self._val = QLabel(value)
        self._val.setObjectName("footerVal")
        lay.addWidget(self._key)
        lay.addWidget(self._val)

    def set_value(self, value: str) -> None:
        self._val.setText(value)

    def set_freshness(self, level: str) -> None:
        """level: ok | warn | stale (solo fsFuentes)."""
        self._val.setProperty("freshness", level)
        _repolish(self._val)


# ---------------------------------------------------------------------------
# Chip helper (STYLE_GUIDE §4.6)
# ---------------------------------------------------------------------------
def make_chip(text: str, kind: str) -> QLabel:
    chip = QLabel(text)
    chip.setObjectName("chip")
    chip.setProperty("kind", kind)
    chip.setAlignment(Qt.AlignmentFlag.AlignCenter)
    return chip


def set_chip(chip: QLabel, text: str, kind: str) -> None:
    chip.setText(text)
    chip.setProperty("kind", kind)
    _repolish(chip)


# ---------------------------------------------------------------------------
# 2.15 LineChartWidget (BLACKFORGE — producción en tiempo real)
# ---------------------------------------------------------------------------
def _rgba_local(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{int(alpha * 255)})"


class LineChartWidget(QWidget):
    """Gráfica de línea + área con degradado. Lee tokens (grad. blackforge)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._t = load_tokens()
        self._series: list[float] = []
        self._ymin = 0.0
        self._ymax = 1.0
        self.setMinimumHeight(120)

    def set_series(self, values: list[float],
                   ymin: float | None = None, ymax: float | None = None) -> None:
        self._series = list(values)
        self._ymin = ymin if ymin is not None else (min(values) if values else 0.0)
        self._ymax = ymax if ymax is not None else (max(values) if values else 1.0)
        self.update()

    def paintEvent(self, event) -> None:
        t = self._t
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = self.rect()
        if not self._series or r.width() < 10:
            p.setPen(_qcolor(t.text_muted))
            p.drawText(r, Qt.AlignmentFlag.AlignCenter, "Sin datos")
            p.end()
            return
        pad_l, pad_r, pad_t, pad_b = 8, 8, 12, 16
        w = r.width() - pad_l - pad_r
        h = r.height() - pad_t - pad_b
        x0, y0 = r.x() + pad_l, r.y() + pad_t
        # rejilla horizontal
        p.setPen(QPen(_qcolor(t.border_soft), 1))
        for i in range(4):
            gy = y0 + int(h * i / 3)
            p.drawLine(x0, gy, x0 + w, gy)
        a, b = t.gradient("blackforge")
        n = len(self._series)
        span = (self._ymax - self._ymin) or 1.0
        pts = []
        for i, v in enumerate(self._series):
            x = x0 + (w * i / max(1, n - 1))
            yy = y0 + h - int(h * (v - self._ymin) / span)
            pts.append((x, yy))
        # área
        from PySide6.QtGui import QLinearGradient, QPainterPath
        path = QPainterPath()
        path.moveTo(pts[0][0], pts[0][1])
        for x, yy in pts[1:]:
            path.lineTo(x, yy)
        path.lineTo(pts[-1][0], y0 + h)
        path.lineTo(pts[0][0], y0 + h)
        path.closeSubpath()
        grad = QLinearGradient(0, y0, 0, y0 + h)
        grad.setColorAt(0.0, _qcolor(_rgba_local(a, 0.35)))
        grad.setColorAt(1.0, _qcolor(_rgba_local(a, 0.02)))
        p.fillPath(path, grad)
        # línea
        pen = QPen(_qcolor(a), 2)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        ppath = QPainterPath()
        ppath.moveTo(pts[0][0], pts[0][1])
        for x, yy in pts[1:]:
            ppath.lineTo(x, yy)
        p.drawPath(ppath)
        # punto final
        p.setBrush(_qcolor(b))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(int(pts[-1][0]) - 3, int(pts[-1][1]) - 3, 6, 6)
        p.end()


# ---------------------------------------------------------------------------
# Neon breathing border (BLACKFORGE nav) — solo el contorno respira en turquesa
# ---------------------------------------------------------------------------
class _NeonBreath(QObject):
    """Anima el blur de un QGraphicsDropShadowEffect turquesa en bucle 6s.

    El brillo nunca llega a 0: oscila entre `min_blur` (siempre visible) y
    `max_blur`. Es tolerante a que el widget/sefecto se destruyan (cierre de
    ventana): detiene la animación y no escribe sobre un C++ object borrado.
    """

    def __init__(self, widget: QWidget, color: str = "#22E0D6",
                 min_blur: int = 8, max_blur: int = 22,
                 period_ms: int = 6000) -> None:
        super().__init__(widget)
        self._alive = True
        self._eff = QGraphicsDropShadowEffect(widget)
        self._eff.setOffset(0, 0)
        self._eff.setColor(_qcolor(color))
        self._eff.setBlurRadius(min_blur)
        self._widget = widget
        widget.setGraphicsEffect(self._eff)
        widget.destroyed.connect(self._on_destroyed)
        self._min = min_blur
        self._max = max_blur
        self._blur = min_blur
        self._anim = QPropertyAnimation(self, b"blur", self)
        self._anim.setDuration(period_ms // 2)  # 3s sube, 3s baja
        self._anim.setStartValue(min_blur)
        self._anim.setEndValue(max_blur)
        self._anim.setLoopCount(-1)  # infinito
        self._anim.setDirection(QPropertyAnimation.Direction.Forward)
        self._anim.finished.connect(self._reverse)  # ping-pong
        self._anim.start()

    def _on_destroyed(self, _obj=None) -> None:
        self._alive = False
        try:
            self._anim.stop()
        except RuntimeError:
            pass

    def _reverse(self) -> None:
        if not self._alive:
            return
        if self._anim.direction() == QPropertyAnimation.Direction.Forward:
            self._anim.setDirection(QPropertyAnimation.Direction.Backward)
        else:
            self._anim.setDirection(QPropertyAnimation.Direction.Forward)
        self._anim.start()

    def get_blur(self) -> int:
        return self._blur

    def set_blur(self, v: int) -> None:
        if not self._alive:
            return
        try:
            self._blur = int(v)
            self._eff.setBlurRadius(self._blur)
        except RuntimeError:
            self._alive = False

    blur = Property(int, get_blur, set_blur)


def apply_neon_breath(widget: QWidget, **kwargs) -> None:
    """Aplica respiración neón turquesa SOLO al contorno del widget."""
    _NeonBreath(widget, **kwargs)
