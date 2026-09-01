"""Standalone BLACKFORGE desktop dashboard.

The visual contract is documented in ``docs/UI_CONTRACT_BLACKFORGE.md``: a
dedicated charcoal/orange application, not a page embedded inside CRIBA.
Engine/catalog behaviour remains local and deterministic.
"""

from __future__ import annotations

import random
from datetime import datetime
from typing import Any

from PySide6.QtCore import (
    QAbstractTableModel,
    QPointF,
    QRectF,
    Qt,
    QThreadPool,
    QTimer,
)
from PySide6.QtGui import (
    QColor,
    QFont,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from ..blackforge_catalog import records as bf_records
from ..constants import DATA_ROOT
from ..model_config import load_model_settings
from ..model_runtime import enhance_ideas_with_model
from .interpreter import format_idea
from .tokens import Tokens, load_tokens


def _catalog_snapshot() -> dict[str, Any]:
    records = list(bf_records())
    families = {
        str(row.get("functional_category_primary") or row.get("source_family") or "—")
        for row in records
    }
    top = sorted(
        records,
        key=lambda row: float(row.get("selection_weight", 0) or 0),
        reverse=True,
    )[:5]
    return {
        "records": len(records),
        "families": len(families),
        "top": top,
    }


def _risk_text(value: str) -> str:
    key = (value or "medium").lower()
    if key in {"high", "medium_high", "critical"}:
        return "Alto"
    if key in {"low"}:
        return "Bajo"
    return "Medio"


def _novelty_text(value: float) -> str:
    score = float(value or 0)
    if score >= 17:
        return "Muy alta"
    if score >= 13:
        return "Alta"
    return "Media"


def _priority_text(value: str) -> str:
    tier = (value or "").lower()
    if "critical" in tier or "crít" in tier:
        return "Crítica"
    if tier in {"essential", "core"} or "high" in tier or "alta" in tier:
        return "Alta"
    return "Media"


class IdeasTableModel(QAbstractTableModel):
    """Compact read-only model for the five visible BLACKFORGE candidates."""

    HEADERS = (
        "#",
        "TÍTULO DE LA IDEA",
        "MECANISMO PRINCIPAL",
        "RIESGO",
        "NOVEDAD",
        "PRIORIDAD",
    )

    def __init__(self) -> None:
        super().__init__()
        self._rows: list[tuple[str, ...]] = []

    def set_rows(self, rows: list[tuple[str, ...]]) -> None:
        self.beginResetModel()
        self._rows = rows
        self.endResetModel()

    def rowCount(self, parent=None) -> int:
        return len(self._rows)

    def columnCount(self, parent=None) -> int:
        return len(self.HEADERS)

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        if (
            orientation == Qt.Orientation.Horizontal
            and role == Qt.ItemDataRole.DisplayRole
        ):
            return self.HEADERS[section]
        return None

    def data(self, index, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid():
            return None
        value = self._rows[index.row()][index.column()]
        if role == Qt.ItemDataRole.DisplayRole:
            return value
        if role == Qt.ItemDataRole.TextAlignmentRole:
            if index.column() in {0, 3, 4, 5}:
                return Qt.AlignmentFlag.AlignCenter
            return Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft
        if role == Qt.ItemDataRole.ToolTipRole:
            return value
        return None


class PillDelegate(QStyledItemDelegate):
    """Paint risk/novelty/priority values as the compact target chips."""

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionViewItem,
        index,
    ) -> None:
        if index.column() not in {3, 4, 5}:
            super().paint(painter, option, index)
            return

        text = str(index.data(Qt.ItemDataRole.DisplayRole) or "")
        lowered = text.casefold()
        if index.column() == 4:
            fg, bg = QColor("#41D77A"), QColor(11, 61, 34, 205)
        elif "crítica" in lowered or "alto" in lowered:
            fg, bg = QColor("#FF6B4A"), QColor(70, 25, 20, 210)
        elif "alta" in lowered or "medio" in lowered:
            fg, bg = QColor("#FFA126"), QColor(65, 43, 8, 210)
        else:
            fg, bg = QColor("#C8CDD0"), QColor(39, 45, 49, 210)

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        chip = option.rect.adjusted(9, 5, -9, -5)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(bg)
        painter.drawRoundedRect(chip, 5, 5)
        painter.setPen(fg)
        painter.drawText(chip, Qt.AlignmentFlag.AlignCenter, text)
        painter.restore()


class LineIcon(QWidget):
    """Small dependency-free line icon set drawn with QPainter."""

    def __init__(
        self,
        kind: str,
        size: int = 30,
        *,
        active: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.kind = kind
        self.active = active
        self.setFixedSize(size, size)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

    def set_active(self, active: bool) -> None:
        self.active = active
        self.update()

    def paintEvent(self, event) -> None:
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        color = QColor("#FF6A00" if self.active else "#C7CBCD")
        pen = QPen(color, max(1.4, self.width() / 18))
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        w = float(self.width())
        h = float(self.height())

        def point(x: float, y: float) -> QPointF:
            return QPointF(w * x, h * y)

        def circle(x: float, y: float, radius: float = 0.09) -> None:
            painter.drawEllipse(point(x, y), w * radius, h * radius)

        kind = self.kind
        if kind == "home":
            path = QPainterPath(point(0.18, 0.50))
            path.lineTo(point(0.50, 0.20))
            path.lineTo(point(0.82, 0.50))
            painter.drawPath(path)
            painter.drawRect(QRectF(w * 0.27, h * 0.47, w * 0.46, h * 0.35))
            painter.drawLine(point(0.50, 0.82), point(0.50, 0.62))
        elif kind in {"generation", "optimized"}:
            circle(0.50, 0.50, 0.10)
            for x, y in (
                (0.50, 0.15),
                (0.82, 0.33),
                (0.82, 0.70),
                (0.50, 0.85),
                (0.18, 0.70),
                (0.18, 0.33),
            ):
                painter.drawLine(point(0.50, 0.50), point(x, y))
                circle(x, y, 0.055)
        elif kind == "associative":
            nodes = ((0.25, 0.28), (0.72, 0.22), (0.38, 0.72), (0.78, 0.68))
            for first, second in ((0, 1), (0, 2), (1, 2), (1, 3), (2, 3)):
                painter.drawLine(point(*nodes[first]), point(*nodes[second]))
            for x, y in nodes:
                circle(x, y, 0.075)
        elif kind == "pure":
            path = QPainterPath(point(0.20, 0.34))
            path.lineTo(point(0.50, 0.16))
            path.lineTo(point(0.80, 0.34))
            path.lineTo(point(0.80, 0.70))
            path.lineTo(point(0.50, 0.87))
            path.lineTo(point(0.20, 0.70))
            path.closeSubpath()
            painter.drawPath(path)
            painter.drawLine(point(0.20, 0.34), point(0.50, 0.52))
            painter.drawLine(point(0.80, 0.34), point(0.50, 0.52))
            painter.drawLine(point(0.50, 0.52), point(0.50, 0.87))
            circle(0.38, 0.33, 0.035)
            circle(0.64, 0.34, 0.035)
        elif kind in {"models", "server"}:
            for y in (0.23, 0.49, 0.75):
                painter.drawRoundedRect(
                    QRectF(w * 0.20, h * (y - 0.10), w * 0.60, h * 0.18),
                    3,
                    3,
                )
                circle(0.69, y - 0.01, 0.025)
        elif kind == "verify":
            path = QPainterPath(point(0.50, 0.13))
            path.lineTo(point(0.78, 0.25))
            path.lineTo(point(0.74, 0.62))
            path.quadTo(point(0.62, 0.79), point(0.50, 0.86))
            path.quadTo(point(0.38, 0.79), point(0.26, 0.62))
            path.lineTo(point(0.22, 0.25))
            path.closeSubpath()
            painter.drawPath(path)
            painter.drawLine(point(0.36, 0.50), point(0.46, 0.61))
            painter.drawLine(point(0.46, 0.61), point(0.66, 0.39))
        elif kind in {"history", "results"}:
            painter.drawRoundedRect(
                QRectF(w * 0.20, h * 0.17, w * 0.60, h * 0.66), 2, 2
            )
            for y in (0.34, 0.50, 0.66):
                circle(0.31, y, 0.02)
                painter.drawLine(point(0.39, y), point(0.68, y))
        elif kind == "cloud":
            path = QPainterPath(point(0.22, 0.68))
            path.cubicTo(point(0.08, 0.62), point(0.16, 0.43), point(0.31, 0.44))
            path.cubicTo(point(0.35, 0.20), point(0.66, 0.19), point(0.71, 0.44))
            path.cubicTo(point(0.91, 0.43), point(0.94, 0.68), point(0.77, 0.72))
            path.lineTo(point(0.22, 0.72))
            painter.drawPath(path)
            painter.drawLine(point(0.50, 0.44), point(0.50, 0.67))
            painter.drawLine(point(0.42, 0.59), point(0.50, 0.67))
            painter.drawLine(point(0.58, 0.59), point(0.50, 0.67))
        elif kind == "fingerprint":
            for inset in (0.18, 0.28, 0.38):
                painter.drawArc(
                    QRectF(
                        w * inset,
                        h * (inset - 0.05),
                        w * (1 - 2 * inset),
                        h * (0.78 - inset),
                    ),
                    15 * 16,
                    150 * 16,
                )
            painter.drawLine(point(0.50, 0.45), point(0.50, 0.80))
        elif kind in {"workbench", "agent"}:
            painter.drawRoundedRect(QRectF(w * 0.28, h * 0.28, w * 0.44, h * 0.44), 3, 3)
            circle(0.50, 0.50, 0.08)
            for x, y in ((0.50, 0.14), (0.86, 0.50), (0.50, 0.86), (0.14, 0.50)):
                painter.drawLine(point(0.50, 0.50), point(x, y))
                circle(x, y, 0.04)
        elif kind == "draw":
            circle(0.30, 0.29, 0.08)
            circle(0.70, 0.29, 0.08)
            painter.drawLine(point(0.30, 0.38), point(0.42, 0.67))
            painter.drawLine(point(0.70, 0.38), point(0.58, 0.67))
            painter.drawRoundedRect(
                QRectF(w * 0.38, h * 0.62, w * 0.24, h * 0.18), 2, 2
            )
        elif kind == "back":
            painter.drawLine(point(0.78, 0.50), point(0.22, 0.50))
            painter.drawLine(point(0.22, 0.50), point(0.42, 0.30))
            painter.drawLine(point(0.22, 0.50), point(0.42, 0.70))
        else:
            circle(0.50, 0.50, 0.28)
        painter.end()


class BrandLogo(QWidget):
    """Draw the wide two-line CRIBA BLACKFORGE wordmark from the target."""

    def __init__(self) -> None:
        super().__init__()
        self.setFixedHeight(86)

    def paintEvent(self, event) -> None:
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        criba_font = QFont("Arial Black")
        criba_font.setPixelSize(45)
        criba_font.setWeight(QFont.Weight.Black)
        criba_font.setStretch(118)
        painter.setFont(criba_font)
        painter.setPen(QColor("#FF6A00"))
        painter.drawText(
            QRectF(26, -3, 218, 58),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            "CRIBA",
        )

        forge_font = QFont("Bahnschrift SemiCondensed")
        forge_font.setPixelSize(19)
        forge_font.setWeight(QFont.Weight.DemiBold)
        forge_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 2.8)
        painter.setFont(forge_font)
        painter.setPen(QColor("#F7F5F1"))
        painter.drawText(
            QRectF(27, 49, 220, 28),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            "BLACKFORGE",
        )
        painter.end()


class StatusCheck(QWidget):
    """Green circular check used by the hero status."""

    def __init__(self) -> None:
        super().__init__()
        self.setFixedSize(23, 23)

    def paintEvent(self, event) -> None:
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor("#21D879"), 1.8)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(QColor(5, 35, 22, 100))
        painter.drawEllipse(QRectF(1.5, 1.5, 20, 20))
        painter.drawLine(QPointF(6.5, 11.5), QPointF(10.0, 15.0))
        painter.drawLine(QPointF(10.0, 15.0), QPointF(16.8, 7.7))
        painter.end()


class ForgeNavButton(QPushButton):
    """Target-like sidebar row with a line icon and active orange rail."""

    def __init__(self, kind: str, text: str) -> None:
        super().__init__()
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(68)
        self.setObjectName("bfNavButton")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(22, 0, 16, 0)
        layout.setSpacing(18)
        self.icon = LineIcon(kind, 29)
        self.label = QLabel(text.upper())
        self.label.setObjectName("bfNavLabel")
        nav_font = QFont("Segoe UI")
        nav_font.setPixelSize(16)
        nav_font.setWeight(QFont.Weight.Normal)
        nav_font.setStretch(96)
        self.label.setFont(nav_font)
        layout.addWidget(self.icon)
        layout.addWidget(self.label, 1)
        self.toggled.connect(self._sync_state)
        self._sync_state(False)

    def _sync_state(self, active: bool) -> None:
        self.icon.set_active(active)
        color = "#FF6A00" if active else "#C8C9C8"
        self.label.setStyleSheet(f"color:{color}; background:transparent;")


class ModeCard(QPushButton):
    """Selectable generation mode card."""

    def __init__(self, key: str, icon: str, title: str, description: str) -> None:
        super().__init__()
        self.key = key
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setObjectName("bfModeCard")
        self.setMinimumWidth(0)
        self.setMinimumHeight(142)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Expanding)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 10, 8, 10)
        layout.setSpacing(7)
        self.icon = LineIcon(icon, 38)
        self.title_label = QLabel(title)
        self.title_label.setObjectName("bfModeTitle")
        title_font = QFont("Segoe UI")
        title_font.setPixelSize(12)
        title_font.setWeight(QFont.Weight.DemiBold)
        title_font.setStretch(90)
        self.title_label.setFont(title_font)
        self.title_label.setWordWrap(True)
        self.title_label.setMinimumWidth(0)
        self.title_label.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred
        )
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.description_label = QLabel(description)
        self.description_label.setObjectName("bfModeDescription")
        description_font = QFont("Segoe UI")
        description_font.setPixelSize(10)
        description_font.setWeight(QFont.Weight.Normal)
        description_font.setStretch(92)
        self.description_label.setFont(description_font)
        self.description_label.setWordWrap(True)
        self.description_label.setMinimumWidth(0)
        self.description_label.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Expanding
        )
        self.description_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(self.icon, 0, Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(self.title_label)
        layout.addWidget(self.description_label, 1)
        self.toggled.connect(self.icon.set_active)


class HeroCanvas(QWidget):
    """Crops the machinery from the source render instead of nesting its UI."""

    SOURCE_RECT = QRectF(290.0, 178.0, 770.0, 470.0)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.pixmap = QPixmap(str(DATA_ROOT / "assets" / "blackforge_hero.png"))
        self.setMinimumHeight(315)

    def paintEvent(self, event) -> None:
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        bounds = QRectF(self.rect())
        clip = QPainterPath()
        clip.addRoundedRect(bounds.adjusted(1, 1, -1, -1), 12, 12)
        painter.setClipPath(clip)
        painter.fillRect(bounds, QColor("#080B0D"))
        if not self.pixmap.isNull():
            image_bounds = QRectF(
                84.0, 0.0, max(1.0, bounds.width() - 84.0), bounds.height()
            )
            painter.drawPixmap(image_bounds, self.pixmap, self.SOURCE_RECT)

        mask_width = min(365.0, bounds.width() * 0.54)
        text_mask = QLinearGradient(0, 0, mask_width, 0)
        text_mask.setColorAt(0.0, QColor(5, 7, 8, 232))
        text_mask.setColorAt(0.76, QColor(5, 7, 8, 232))
        text_mask.setColorAt(1.0, QColor(5, 7, 8, 0))
        painter.fillRect(QRectF(0, 0, mask_width, 176.0), text_mask)
        left_fade = QLinearGradient(0, 0, bounds.width() * 0.76, 0)
        left_fade.setColorAt(0.0, QColor(5, 7, 8, 235))
        left_fade.setColorAt(0.24, QColor(6, 8, 9, 178))
        left_fade.setColorAt(0.52, QColor(6, 8, 9, 24))
        left_fade.setColorAt(1.0, QColor(6, 8, 9, 0))
        painter.fillRect(bounds, left_fade)

        top_fade = QLinearGradient(0, 0, 0, min(155.0, bounds.height() * 0.45))
        top_fade.setColorAt(0.0, QColor(5, 7, 8, 220))
        top_fade.setColorAt(1.0, QColor(5, 7, 8, 0))
        painter.fillRect(bounds, top_fade)

        bottom_fade = QLinearGradient(0, bounds.height() * 0.65, 0, bounds.height())
        bottom_fade.setColorAt(0.0, QColor(5, 7, 8, 0))
        bottom_fade.setColorAt(1.0, QColor(5, 7, 8, 190))
        painter.fillRect(bounds, bottom_fade)
        painter.end()


class HeroPanel(QFrame):
    """Central machine/state composition."""

    def __init__(self, on_context) -> None:
        super().__init__()
        self.setObjectName("bfHeroPanel")
        grid = QGridLayout(self)
        grid.setContentsMargins(0, 0, 0, 0)
        self.canvas = HeroCanvas()
        grid.addWidget(self.canvas, 0, 0)

        overlay = QWidget()
        overlay.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        layout = QVBoxLayout(overlay)
        layout.setContentsMargins(28, 20, 24, 20)
        layout.setSpacing(8)

        title = QLabel("ESTADO DE BLACKFORGE")
        title.setObjectName("bfHeroTitle")
        status_row = QHBoxLayout()
        status_row.setSpacing(10)
        status_icon = StatusCheck()
        status = QLabel("OPERATIVA")
        status.setObjectName("bfOperational")
        status_row.addWidget(status_icon)
        status_row.addWidget(status)
        status_row.addStretch(1)

        description = QLabel(
            "BLACKFORGE está activa y lista para generar\n"
            "ideas de innovación en ciberseguridad mediante\n"
            "combinaciones estructuradas y verificables."
        )
        description.setObjectName("bfHeroDescription")
        description.setWordWrap(True)
        description.setMaximumWidth(340)
        description_font = QFont("Segoe UI")
        description_font.setPixelSize(13)
        description_font.setWeight(QFont.Weight.Normal)
        description_font.setStretch(88)
        description.setFont(description_font)

        layout.addWidget(title)
        layout.addSpacing(5)
        layout.addLayout(status_row)
        layout.addWidget(description)
        layout.addStretch(1)
        context = QPushButton("▣   VER CONTEXTO")
        context.setObjectName("bfContextButton")
        context.setCursor(Qt.CursorShape.PointingHandCursor)
        context.setFixedSize(180, 44)
        context.clicked.connect(on_context)
        layout.addWidget(context, 0, Qt.AlignmentFlag.AlignLeft)
        grid.addWidget(overlay, 0, 0)


def _section_header(icon: str, text: str) -> QWidget:
    widget = QWidget()
    layout = QHBoxLayout(widget)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(9)
    layout.addWidget(LineIcon(icon, 23))
    label = QLabel(text)
    label.setObjectName("bfSectionHeader")
    layout.addWidget(label)
    layout.addStretch(1)
    return widget


class BlackforgeWindow(QMainWindow):
    """Dedicated BLACKFORGE application window."""

    NAVIGATION = (
        ("home", "Resumen"),
        ("generation", "Generación"),
        ("associative", "Lotería asociativa"),
        ("pure", "Lotería pura"),
        ("workbench", "Agent Workbench"),
        ("models", "Modelos"),
        ("verify", "Verificación"),
        ("history", "Historial"),
    )

    def __init__(self, database: Any = None, query: str = "") -> None:
        super().__init__()
        self.database = database
        self.tokens: Tokens = load_tokens(DATA_ROOT / "theme_blackforge.json")
        self.snapshot = _catalog_snapshot()
        self.mode = "optimized"
        self.initial_query = query.strip()
        self._lottery_engine: Any = None
        self.pool = QThreadPool.globalInstance()
        self._busy = False
        self._spin_index = 0
        self._spin_timer = QTimer(self)
        self._spin_timer.setInterval(120)
        self._spin_timer.timeout.connect(self._spin_tick)

        self.setWindowTitle("BLACKFORGE — Innovación en ciberseguridad")
        self.setMinimumSize(1200, 700)
        self.resize(1386, 778)
        self.setStyleSheet(build_blackforge_qss(self.tokens))
        self._build_ui()
        self._populate_catalog_rows()

        self._clock = QTimer(self)
        self._clock.setInterval(1000)
        self._clock.timeout.connect(self._tick_clock)
        self._clock.start()
        self._tick_clock()

    def _build_ui(self) -> None:
        root = QWidget()
        root.setObjectName("blackforgeRoot")
        self.setCentralWidget(root)
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.sidebar = self._build_sidebar()
        root_layout.addWidget(self.sidebar)

        surface = QWidget()
        surface.setObjectName("bfSurface")
        surface_layout = QVBoxLayout(surface)
        surface_layout.setContentsMargins(28, 14, 8, 8)
        surface_layout.setSpacing(10)
        self.topbar = self._build_topbar()
        surface_layout.addWidget(self.topbar)

        content = QWidget()
        content.setObjectName("bfContent")
        content_layout = QHBoxLayout(content)
        content_layout.setContentsMargins(2, 0, 0, 0)
        content_layout.setSpacing(12)

        center = QWidget()
        center_layout = QVBoxLayout(center)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(10)
        self.hero = HeroPanel(self._show_context)
        self.hero.setMinimumHeight(315)
        self.ideas_card = self._build_ideas_card()
        center_layout.addWidget(self.hero, 3)
        center_layout.addWidget(self.ideas_card, 2)
        content_layout.addWidget(center, 1)

        right_scroll = QScrollArea()
        right_scroll.setObjectName("bfRightScroll")
        right_scroll.setWidgetResizable(True)
        right_scroll.setFrameShape(QFrame.Shape.NoFrame)
        right_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        right_scroll.setFixedWidth(388)
        self.right_column = self._build_right_column()
        right_scroll.setWidget(self.right_column)
        content_layout.addWidget(right_scroll)
        surface_layout.addWidget(content, 1)
        root_layout.addWidget(surface, 1)

    def _build_sidebar(self) -> QFrame:
        sidebar = QFrame()
        sidebar.setObjectName("bfSidebar")
        sidebar.setFixedWidth(260)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(12, 14, 12, 12)
        layout.setSpacing(4)

        layout.addWidget(BrandLogo())
        layout.addSpacing(16)

        self.nav_buttons: dict[str, ForgeNavButton] = {}
        for key, label in self.NAVIGATION:
            button = ForgeNavButton(key, label)
            button.clicked.connect(
                lambda checked=False, selected=key: self._select_navigation(selected)
            )
            self.nav_buttons[key] = button
            layout.addWidget(button)
        layout.addStretch(1)

        brand = QWidget()
        brand.setObjectName("bfBottomBrand")
        brand.setFixedHeight(76)
        brand_layout = QVBoxLayout(brand)
        brand_layout.setContentsMargins(0, 0, 0, 0)
        brand_layout.setSpacing(-1)
        monogram = QLabel("BF")
        monogram.setObjectName("bfMonogram")
        monogram.setAlignment(Qt.AlignmentFlag.AlignCenter)
        brand_name = QLabel("BLACKFORGE")
        brand_name.setObjectName("bfBottomName")
        brand_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        brand_layout.addWidget(monogram)
        brand_layout.addWidget(brand_name)
        layout.addWidget(brand)

        self.nav_buttons["home"].setChecked(True)
        return sidebar

    def _build_topbar(self) -> QFrame:
        topbar = QFrame()
        topbar.setObjectName("bfTopbar")
        topbar.setFixedHeight(74)
        layout = QHBoxLayout(topbar)
        layout.setContentsMargins(22, 10, 14, 10)
        layout.setSpacing(12)

        layout.addWidget(LineIcon("generation", 35, active=True))
        heading = QVBoxLayout()
        heading.setSpacing(1)
        self.mode_heading = QLabel("MODO OPTIMIZADO")
        self.mode_heading.setObjectName("bfTopMode")
        self.status_subtitle = QLabel("Motor de innovación activo")
        self.status_subtitle.setObjectName("bfTopSubtitle")
        subtitle_font = QFont("Segoe UI")
        subtitle_font.setPixelSize(12)
        subtitle_font.setWeight(QFont.Weight.Normal)
        self.status_subtitle.setFont(subtitle_font)
        heading.addWidget(self.mode_heading)
        heading.addWidget(self.status_subtitle)
        layout.addLayout(heading)
        layout.addStretch(1)

        layout.addWidget(LineIcon("history", 21))
        self.date_label = QLabel()
        self.date_label.setObjectName("bfTopMeta")
        layout.addWidget(self.date_label)
        layout.addSpacing(18)
        self.clock_icon = QLabel("◷")
        self.clock_icon.setObjectName("bfClockIcon")
        layout.addWidget(self.clock_icon)
        self.time_label = QLabel()
        self.time_label.setObjectName("bfTopMeta")
        layout.addWidget(self.time_label)
        layout.addSpacing(8)

        self.back_button = QPushButton("←")
        self.back_button.setObjectName("bfBackButton")
        self.back_button.setAccessibleName("Volver a CRIBA")
        self.back_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.back_button.setToolTip("Cerrar BLACKFORGE y volver a CRIBA")
        self.back_button.setFixedSize(34, 32)
        self.back_button.clicked.connect(self.close)
        layout.addWidget(self.back_button)
        return topbar

    def _switch_to_criba(self) -> None:
        from .main_window import CribaMainWindow
        self.criba_win = CribaMainWindow()
        self.criba_win.show()
        self.close()

    def _build_ideas_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("bfCard")
        card.setMinimumHeight(214)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 18, 14, 8)
        layout.setSpacing(9)
        title = QLabel("IDEAS GENERADAS (TOP 5)")
        title.setObjectName("bfCardTitle")
        layout.addWidget(title)

        self.ideas_model = IdeasTableModel()
        self.ideas_table = QTableView()
        self.ideas_table.setObjectName("bfIdeasTable")
        self.ideas_table.setModel(self.ideas_model)
        table_font = QFont("Segoe UI")
        table_font.setPixelSize(10)
        table_font.setWeight(QFont.Weight.Normal)
        self.ideas_table.setFont(table_font)
        self.ideas_table.setItemDelegate(PillDelegate(self.ideas_table))
        self.ideas_table.setShowGrid(False)
        self.ideas_table.setAlternatingRowColors(False)
        self.ideas_table.setSelectionMode(QTableView.SelectionMode.NoSelection)
        self.ideas_table.setEditTriggers(QTableView.EditTrigger.NoEditTriggers)
        self.ideas_table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.ideas_table.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.ideas_table.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.ideas_table.verticalHeader().setVisible(False)
        self.ideas_table.verticalHeader().setDefaultSectionSize(34)
        header = self.ideas_table.horizontalHeader()
        header.setFixedHeight(37)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        for column in (3, 4, 5):
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.Fixed)
            self.ideas_table.setColumnWidth(column, 78)
        layout.addWidget(self.ideas_table, 1)
        self.idea_detail_label = QLabel(
            "Ejecuta una generación para ver la propuesta explicada en lenguaje natural."
        )
        self.idea_detail_label.setObjectName("bfIdeaDetail")
        self.idea_detail_label.setWordWrap(True)
        self.idea_detail_label.setMaximumHeight(58)
        layout.addWidget(self.idea_detail_label)
        return card

    def _build_right_column(self) -> QWidget:
        column = QWidget()
        column.setObjectName("bfRightColumn")
        column.setMinimumHeight(670)
        layout = QVBoxLayout(column)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        layout.addWidget(self._build_modes_panel())
        layout.addWidget(self._build_models_panel())
        layout.addWidget(self._build_verification_panel())
        layout.addStretch(1)
        return column

    def _build_modes_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("bfCard")
        panel.setMinimumHeight(330)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(14, 16, 14, 12)
        layout.setSpacing(11)
        layout.addWidget(_section_header("generation", "MODOS DE GENERACIÓN"))

        query_label = QLabel("RETO / CONTEXTO")
        query_label.setObjectName("bfQueryLabel")
        layout.addWidget(query_label)
        self.query_input = QLineEdit()
        self.query_input.setObjectName("bfQueryInput")
        self.query_input.setPlaceholderText(
            "Ej.: reducir fraude sin perjudicar a clientes legítimos"
        )
        self.query_input.setText(
            self.initial_query
            or "Diseñar una mejora de ciberseguridad concreta, reversible y medible"
        )
        self.query_input.setMaxLength(20_000)
        layout.addWidget(self.query_input)

        row = QHBoxLayout()
        row.setSpacing(7)
        specs = (
            (
                "optimized",
                "optimized",
                "Modo optimizado",
                "Equilibra novedad\ny factibilidad.",
            ),
            (
                "associative",
                "associative",
                "Lotería asociativa",
                "Combina familias\ny mecanismos\nrelacionados.",
            ),
            (
                "pure",
                "pure",
                "Lotería pura",
                "Explora combinaciones\naleatorias sin repetición\nentre sorteos.",
            ),
        )
        self.mode_cards: dict[str, ModeCard] = {}
        for key, icon, title, description in specs:
            mode_card = ModeCard(key, icon, title, description)
            mode_card.clicked.connect(
                lambda checked=False, selected=key: self._select_mode(selected)
            )
            self.mode_cards[key] = mode_card
            row.addWidget(mode_card, 1)
        layout.addLayout(row, 1)

        self.execute_button = QPushButton("▶    EJECUTAR GENERACIÓN")
        self.execute_button.setObjectName("bfExecuteButton")
        self.execute_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.execute_button.setFixedHeight(42)
        self.execute_button.clicked.connect(self._execute)
        layout.addWidget(self.execute_button)
        self.mode_cards["optimized"].setChecked(True)
        return panel

    def _build_models_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("bfCard")
        panel.setMinimumHeight(186)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(14, 12, 14, 10)
        layout.setSpacing(8)
        layout.addWidget(_section_header("models", "INTEGRACIÓN DE MODELOS"))

        self.model_name_label = QLabel()
        self.model_name_label.setObjectName("bfInnerTitle")
        self.model_status_label = QLabel()
        self.model_status_label.setObjectName("bfAvailable")
        self.model_status_label.setWordWrap(True)
        layout.addWidget(self.model_name_label)
        layout.addWidget(self.model_status_label)
        configure = QPushButton("◇  CONFIGURAR / AÑADIR GGUF")
        configure.setObjectName("bfModelConfigButton")
        configure.clicked.connect(self._open_models)
        layout.addWidget(configure)
        self._refresh_model_panel()
        return panel

    def _build_verification_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("bfCard")
        panel.setMinimumHeight(198)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(14, 15, 14, 8)
        layout.setSpacing(20)
        layout.addWidget(_section_header("verify", "VERIFICACIÓN Y TRAZABILIDAD"))
        row = QHBoxLayout()
        row.setSpacing(6)
        specs = (
            ("verify", "JUEZ /\nVERIFICADOR", "Activo"),
            ("draw", "SORTEOS\nREALES", "Registrados"),
            ("fingerprint", "TRAZABILIDAD", "Completa"),
            ("results", "RESULTADOS\nESTRUCTURADOS", "Disponibles"),
        )
        for icon, title, status in specs:
            tile = QFrame()
            tile.setObjectName("bfVerifyTile")
            tile.setMinimumWidth(0)
            tile.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Expanding)
            tile_layout = QVBoxLayout(tile)
            tile_layout.setContentsMargins(5, 7, 5, 6)
            tile_layout.setSpacing(4)
            tile_layout.addWidget(
                LineIcon(icon, 38, active=True), 0, Qt.AlignmentFlag.AlignHCenter
            )
            title_label = QLabel(title)
            title_label.setObjectName("bfVerifyTitle")
            title_label.setMinimumWidth(0)
            title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            status_label = QLabel(f"●  {status}")
            status_label.setObjectName("bfVerifyStatus")
            status_label.setMinimumWidth(0)
            status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            tile_layout.addWidget(title_label, 1)
            tile_layout.addWidget(status_label)
            row.addWidget(tile, 1)
        layout.addLayout(row, 1)
        return panel

    def _populate_catalog_rows(self) -> None:
        rows: list[tuple[str, ...]] = []
        for index, record in enumerate(self.snapshot["top"], start=1):
            rows.append(
                (
                    str(index),
                    str(record.get("title") or "Idea técnica verificable"),
                    str(
                        record.get("functional_category_primary")
                        or record.get("source_family")
                        or "Análisis + IA"
                    ),
                    _risk_text(str(record.get("risk_level") or "medium")),
                    _novelty_text(float(record.get("uniqueness_score", 0) or 0)),
                    _priority_text(str(record.get("activation_tier") or "")),
                )
            )
        self.ideas_model.set_rows(rows)

    def _select_navigation(self, key: str) -> None:
        for name, button in self.nav_buttons.items():
            button.setChecked(name == key)
        if key == "associative":
            self._select_mode("associative")
        elif key == "pure":
            self._select_mode("pure")
        elif key == "generation":
            self._select_mode(self.mode)
        elif key == "workbench":
            from PySide6.QtCore import QUrl
            from PySide6.QtGui import QDesktopServices
            QDesktopServices.openUrl(QUrl("http://localhost:8080/workbench"))
        elif key == "models":
            self._open_models()
        elif key == "history":
            QMessageBox.information(
                self,
                "BLACKFORGE · Historial",
                "El historial de sesiones permanece en CRIBA y se abre desde "
                "su catálogo persistente.",
            )

    def _select_mode(self, key: str) -> None:
        if key not in self.mode_cards:
            return
        self.mode = key
        for name, card in self.mode_cards.items():
            card.setChecked(name == key)
        labels = {
            "optimized": "MODO OPTIMIZADO",
            "associative": "LOTERÍA ASOCIATIVA",
            "pure": "LOTERÍA PURA",
        }
        self.mode_heading.setText(labels[key])

    def _execute(self) -> None:
        if self._busy:
            return
        self._set_busy(True)
        from .actions import Worker, _start_worker

        query = self.query_input.text().strip()
        worker = Worker(lambda: self._build_generation_result(query))
        worker.signals.done.connect(self._apply_generation_result)
        worker.signals.fail.connect(self._on_generation_error)
        _start_worker(self, worker)

    def _run_generation(self) -> None:
        """Synchronous compatibility path used by focused engine/UI tests."""

        try:
            self._apply_generation_result(self._build_generation_result())
        except Exception as exc:  # noqa: BLE001
            self._on_generation_error(str(exc))

    def _build_generation_result(self, query: str | None = None) -> dict[str, Any]:
        """Run lottery plus optional language synthesis away from the GUI thread."""

        from ..lottery import LotteryEngine

        records = list(bf_records())
        if self._lottery_engine is None:
            methods = [dict(row) for row in records]
            self._lottery_engine = LotteryEngine.from_methods(
                methods, seed=random.SystemRandom().randint(0, 2**31 - 1)
            )
        self._lottery_engine.run_round(self.mode, batch_size=12)
        deterministic = self._lottery_engine.last_round_ideas
        active_query = (
            self.query_input.text().strip() if query is None else query.strip()
        )
        enhanced, semantic = enhance_ideas_with_model(
            active_query,
            deterministic,
            product="BLACKFORGE",
        )
        return {"ideas": enhanced, "semantic": semantic, "query": active_query}

    def _apply_generation_result(self, result: Any) -> None:
        """Render a completed result on the Qt GUI thread."""

        try:
            if not isinstance(result, dict):
                raise ValueError("Resultado de generación no válido.")
            ideas = result.get("ideas", [])
            rows: list[tuple[str, ...]] = []
            for index, idea in enumerate(ideas[:5], start=1):
                formatted = format_idea(idea, "es", index - 1)
                convergence = idea.get("convergence") or {}
                viability = float(convergence.get("viability", 0.8) or 0.8)
                risk = (
                    "Alto"
                    if viability < 0.5
                    else "Medio"
                    if viability < 0.7
                    else "Bajo"
                )
                rows.append(
                    (
                        str(index),
                        str(formatted["title"]),
                        str(idea.get("family1") or idea.get("family") or "—"),
                        risk,
                        str(formatted["novelty"]),
                        str(formatted["quality"]),
                    )
                )
            self.ideas_model.set_rows(rows)
            if rows:
                lead = ideas[0]
                detail = str(lead.get("description") or "").strip()
                experiment = str(lead.get("semantic_experiment") or "").strip()
                if experiment:
                    detail = f"{detail} · Prueba: {experiment}"
                self.idea_detail_label.setText(detail or str(lead.get("title") or ""))
            semantic = result.get("semantic", {})
            if semantic.get("status") in {"ok", "partial"}:
                enhanced_count = int(semantic.get("enhanced_count", 0))
                candidate_count = int(semantic.get("candidate_count", len(ideas)))
                suffix = " · parcial" if semantic.get("status") == "partial" else ""
                self.status_subtitle.setText(
                    f"{enhanced_count}/{candidate_count} ideas redactadas por "
                    f"{semantic.get('model', 'modelo local')}{suffix}"
                )
            elif semantic.get("status") == "fallback":
                self.status_subtitle.setText(
                    "Fallback determinista · revisa Modelos IA"
                )
                self.idea_detail_label.setText(
                    f"Modelo local no disponible: {semantic.get('error', 'error desconocido')}"
                )
            else:
                self.status_subtitle.setText(
                    "Generación determinista · modelo desactivado"
                )
        except Exception as exc:  # noqa: BLE001
            self._on_generation_error(str(exc))
        finally:
            self._set_busy(False)

    def _on_generation_error(self, message: str) -> None:
        self._set_busy(False)
        first_line = message.splitlines()[0]
        QMessageBox.warning(
            self,
            "BLACKFORGE",
            f"No se pudo completar la generación:\n{first_line}",
        )
        self.status_subtitle.setText("Motor disponible · generación no completada")

    def _open_models(self) -> None:
        from .model_settings_dialog import open_model_settings

        open_model_settings(self)
        self._refresh_model_panel()
        self.nav_buttons["models"].setChecked(False)
        self.nav_buttons["home"].setChecked(True)

    def _refresh_model_panel(self) -> None:
        settings = load_model_settings()
        profile = settings.active_profile()
        self.model_name_label.setText(
            profile.name
            if settings.enabled and profile is not None
            else "Motor determinista"
        )
        if settings.enabled and profile is not None:
            backend = "llama.cpp / GGUF" if profile.backend == "llama_cpp" else "Ollama"
            self.model_status_label.setText(
                f"● Activo · {backend} · reasoning {profile.reasoning}"
            )
        else:
            self.model_status_label.setText("○ Modelo de lenguaje desactivado")

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        self.execute_button.setEnabled(not busy)
        if busy:
            self._spin_index = 0
            self.status_subtitle.setText("Combinando familias y mecanismos…")
            self._spin_timer.start()
        else:
            self._spin_timer.stop()
            self.execute_button.setText("▶    EJECUTAR GENERACIÓN")

    def _spin_tick(self) -> None:
        chars = "◐◓◑◒"
        self._spin_index = (self._spin_index + 1) % len(chars)
        self.execute_button.setText(
            f"{chars[self._spin_index]}    GENERANDO COMBINACIONES"
        )

    def _show_context(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("BLACKFORGE · Contexto BF-516")
        dialog.resize(960, 620)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(12, 12, 12, 12)
        canvas = HeroCanvas()
        layout.addWidget(canvas)
        dialog.exec()

    def _tick_clock(self) -> None:
        now = datetime.now()
        months = (
            "ENE",
            "FEB",
            "MAR",
            "ABR",
            "MAY",
            "JUN",
            "JUL",
            "AGO",
            "SEP",
            "OCT",
            "NOV",
            "DIC",
        )
        self.date_label.setText(f"{now.day:02d} {months[now.month - 1]} {now.year}")
        self.time_label.setText(now.strftime("%H:%M:%S"))

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.close()
            return
        super().keyPressEvent(event)


def build_blackforge_qss(tokens: Tokens) -> str:
    """Create the standalone BLACKFORGE stylesheet from its own token file."""

    raw = tokens.raw
    orange = tokens.accent_orange
    orange_bright = str(raw["color"]["accent"].get("orange_bright", "#FF8318"))
    return f"""
QMainWindow {{
    background: {tokens.bg_app};
}}
QWidget#blackforgeRoot, QWidget#bfSurface, QWidget#bfContent {{
    background: {tokens.bg_app};
    color: {tokens.text_primary};
    font-family: "Segoe UI", "Segoe UI Variable";
    font-weight: 400;
}}
QLabel {{
    background: transparent;
    color: {tokens.text_primary};
}}
QFrame#bfSidebar {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #050708, stop:1 #080B0D);
    border-right: 1px solid #161B1E;
}}
QLabel#bfCribaLogo {{
    color: {orange};
    font-family: "Bahnschrift SemiCondensed", "Segoe UI";
    font-size: 41px;
    font-weight: 800;
    letter-spacing: -1px;
}}
QLabel#bfForgeLogo {{
    color: #F7F5F1;
    font-family: "Bahnschrift SemiCondensed", "Segoe UI";
    font-size: 19px;
    font-weight: 600;
    letter-spacing: 3px;
}}
QPushButton#bfNavButton {{
    background: transparent;
    border: none;
    border-left: 2px solid transparent;
    border-radius: 7px;
    text-align: left;
}}
QPushButton#bfNavButton:hover {{
    background: #111518;
    border-left-color: #65401E;
}}
QPushButton#bfNavButton:checked {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #161616, stop:1 #20201F);
    border-left: 2px solid {orange};
}}
QLabel#bfNavLabel {{
    color: #C8C9C8;
    font-size: 16px;
    font-weight: 500;
}}
QPushButton#bfNavButton:checked QLabel#bfNavLabel {{
    color: {orange};
}}
QWidget#bfBottomBrand {{
    background: transparent;
}}
QLabel#bfMonogram {{
    color: #22282B;
    font-family: "Bahnschrift SemiCondensed";
    font-size: 43px;
    font-weight: 900;
}}
QLabel#bfBottomName {{
    color: #C4C7C8;
    font-size: 16px;
    font-weight: 600;
    letter-spacing: 3px;
}}
QFrame#bfTopbar, QFrame#bfCard {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #0B0E10, stop:1 #0D1113);
    border: 1px solid #23282B;
    border-radius: 11px;
}}
QLabel#bfTopMode {{
    color: {orange};
    font-size: 15px;
    font-weight: 700;
}}
QLabel#bfTopSubtitle {{
    color: #A8A8A5;
    font-size: 12px;
    font-weight: 400;
}}
QLabel#bfTopMeta, QLabel#bfClockIcon {{
    color: #AEB0B0;
    font-size: 13px;
}}
QPushButton#bfBackButton {{
    background: #0B0E10;
    border: 1px solid #384047;
    border-radius: 7px;
    color: #C8CDD0;
    padding: 7px 10px;
    font-size: 11px;
    font-weight: 600;
}}
QPushButton#bfBackButton:hover {{
    border-color: {orange};
    color: {orange};
    background: #17120D;
}}
QFrame#bfHeroPanel {{
    background: #080B0D;
    border: 1px solid #20262A;
    border-radius: 12px;
}}
QLabel#bfHeroTitle {{
    color: #F5F4F1;
    font-size: 18px;
    font-weight: 700;
}}
QLabel#bfStatusCheck {{
    min-width: 21px;
    max-width: 21px;
    min-height: 21px;
    max-height: 21px;
    color: {tokens.success};
    border: 2px solid {tokens.success};
    border-radius: 10px;
    font-size: 12px;
    font-weight: 800;
}}
QLabel#bfOperational {{
    color: {tokens.success};
    font-size: 16px;
    font-weight: 700;
}}
QLabel#bfHeroDescription {{
    color: #D2D2CF;
    font-size: 13px;
    font-weight: 400;
    line-height: 1.35;
}}
QPushButton#bfContextButton {{
    background: rgba(7, 8, 9, 210);
    border: 1px solid {orange};
    border-radius: 7px;
    color: {orange};
    font-size: 13px;
    font-weight: 600;
}}
QPushButton#bfContextButton:hover {{
    background: #24170D;
    border-color: {orange_bright};
    color: {orange_bright};
}}
QLabel#bfCardTitle, QLabel#bfSectionHeader {{
    color: #F1F0ED;
    font-size: 15px;
    font-weight: 700;
}}
QPushButton#bfModeCard {{
    background: #101417;
    border: 1px solid #2A3034;
    border-radius: 8px;
    color: #D9D9D6;
}}
QPushButton#bfModeCard:hover {{
    background: #171B1E;
    border-color: #5B4130;
}}
QPushButton#bfModeCard:checked {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #17130F, stop:1 #111315);
    border: 1px solid {orange};
}}
QLabel#bfModeTitle {{
    color: #E9E7E3;
    font-size: 12px;
    font-weight: 600;
}}
QPushButton#bfModeCard:checked QLabel#bfModeTitle {{
    color: {orange};
}}
QLabel#bfModeDescription {{
    color: #B5B5B2;
    font-size: 10px;
    font-weight: 400;
}}
QPushButton#bfExecuteButton {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #A84500, stop:0.48 #D35E00, stop:1 #B34800);
    border: 1px solid #F17A18;
    border-radius: 7px;
    color: white;
    font-size: 14px;
    font-weight: 650;
}}
QPushButton#bfExecuteButton:hover {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #DD6205, stop:0.48 {orange_bright}, stop:1 #C85300);
}}
QPushButton#bfExecuteButton:disabled {{
    color: #CAB5A6;
    background: #6D3109;
}}
QLabel#bfQueryLabel {{
    color: #AEB0AE;
    font-size: 10px;
    font-weight: 650;
}}
QLineEdit#bfQueryInput {{
    background: #090C0E;
    border: 1px solid #343A3E;
    border-radius: 7px;
    color: #F0EFEC;
    padding: 7px 9px;
    min-height: 25px;
}}
QLineEdit#bfQueryInput:focus {{
    border-color: {orange};
}}
QPushButton#bfModelConfigButton {{
    background: #17120D;
    border: 1px solid {orange};
    border-radius: 6px;
    color: {orange};
    padding: 7px;
    font-size: 10px;
    font-weight: 650;
}}
QPushButton#bfModelConfigButton:hover {{
    background: #28180B;
    color: {orange_bright};
}}
QLabel#bfIdeaDetail {{
    color: #C7C8C5;
    background: #0A0D0F;
    border-left: 2px solid {orange};
    padding: 6px 8px;
    font-size: 10px;
}}
QFrame#bfInnerCard, QFrame#bfVerifyTile {{
    background: #0D1113;
    border: 1px solid #252B2F;
    border-radius: 8px;
}}
QLabel#bfInnerTitle {{
    color: #F0EFEC;
    font-size: 12px;
    font-weight: 600;
}}
QLabel#bfAvailable, QLabel#bfVerifyStatus {{
    color: {tokens.success};
    font-size: 10px;
}}
QLabel#bfInnerDescription, QLabel#bfFootnote {{
    color: #AEB0AE;
    font-size: 10px;
    font-weight: 400;
}}
QLabel#bfVerifyTitle {{
    color: #E3E2DF;
    font-size: 9px;
    font-weight: 600;
}}
QTableView#bfIdeasTable {{
    background: transparent;
    alternate-background-color: transparent;
    border: none;
    color: #C6C7C5;
    font-size: 10px;
    font-weight: 400;
    selection-background-color: transparent;
    gridline-color: #202528;
}}
QTableView#bfIdeasTable::item {{
    border-bottom: 1px solid #24292C;
    padding-left: 5px;
}}
QHeaderView::section {{
    background: #111518;
    color: #AEB1B2;
    border: none;
    border-bottom: 1px solid #2B3033;
    padding: 4px 5px;
    font-size: 9px;
    font-weight: 600;
}}
QScrollArea#bfRightScroll {{
    background: transparent;
    border: none;
}}
QScrollArea#bfRightScroll > QWidget > QWidget {{
    background: transparent;
}}
QScrollArea#bfRightScroll QScrollBar:vertical {{
    width: 0px;
}}
QScrollBar:vertical {{
    width: 6px;
    background: transparent;
}}
QScrollBar::handle:vertical {{
    background: #343A3E;
    border-radius: 3px;
    min-height: 30px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QToolTip {{
    background: #111518;
    color: #ECEBE8;
    border: 1px solid {orange};
    padding: 6px;
}}
"""
