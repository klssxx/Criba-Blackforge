"""Modelo y delegates de la tabla de ranking (WIDGET_TREE §2.5-2.7)."""
from __future__ import annotations

from typing import Any

from PySide6.QtCore import (
    QAbstractTableModel,
    QModelIndex,
    QRectF,
    QSortFilterProxyModel,
    Qt,
)
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QStyledItemDelegate, QStyleOptionViewItem

from .tokens import load_tokens

COLUMNS = ("#", "Idea", "value_score", "Convergencia", "Impacto", "Estado")
COL_RANK, COL_IDEA, COL_SCORE, COL_CONV, COL_IMPACT, COL_STATE = range(6)

KindRole = Qt.ItemDataRole.UserRole + 1       # chip kind / estado key
BarRole = Qt.ItemDataRole.UserRole + 2        # 0..1 proportion for microbar


def impact_label(score: float) -> str:
    if score >= 0.85: return "Muy alto"
    if score >= 0.65: return "Alto"
    if score >= 0.45: return "Medio alto"
    if score >= 0.25: return "Medio"
    return "Bajo"


def impact_kind(score: float) -> str:
    if score >= 0.65: return "candidata"      # violet scale
    if score >= 0.45: return "eval"           # cyan/blue scale
    return "exploracion"


class RankingModel(QAbstractTableModel):
    """Filas: dicts con keys rank, titulo, value_score, convergencia, estado.

    estado in {"eval", "candidata", "exploracion", "guardada"}.
    """

    ESTADO_TEXT = {"eval": "En evaluación", "candidata": "Candidata",
                   "exploracion": "Exploración", "guardada": "Guardada"}

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._rows: list[dict[str, Any]] = []

    def set_rows(self, rows: list[dict[str, Any]]) -> None:
        self.beginResetModel()
        self._rows = list(rows)
        self.endResetModel()

    def mark_saved(self, row: int) -> None:
        if 0 <= row < len(self._rows):
            self._rows[row]["estado"] = "guardada"
            idx = self.index(row, COL_STATE)
            self.dataChanged.emit(idx, idx)

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._rows)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(COLUMNS)

    def headerData(self, section: int, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            return COLUMNS[section]
        return None

    def data(self, index: QModelIndex, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        r = self._rows[index.row()]
        col = index.column()
        score = float(r.get("value_score", 0.0))
        conv = float(r.get("convergencia", 0.0))
        if role == Qt.ItemDataRole.DisplayRole:
            if col == COL_RANK: return str(r.get("rank", index.row() + 1))
            if col == COL_IDEA: return str(r.get("titulo", ""))
            if col == COL_SCORE: return f"{score:.2f}"
            if col == COL_CONV: return f"{int(round(conv * 100))}%"
            if col == COL_IMPACT: return impact_label(score)
            if col == COL_STATE:
                return self.ESTADO_TEXT.get(str(r.get("estado", "exploracion")), "—")
        if role == Qt.ItemDataRole.ToolTipRole and col == COL_IDEA:
            return str(r.get("titulo", ""))
        if role == BarRole:
            if col == COL_SCORE: return min(1.0, score)
            if col == COL_CONV: return min(1.0, conv)
        if role == KindRole:
            if col == COL_IMPACT: return impact_kind(score)
            if col == COL_STATE: return str(r.get("estado", "exploracion"))
        if role == Qt.ItemDataRole.UserRole:
            return r
        return None


class RankingFilterProxy(QSortFilterProxyModel):
    """El QTabBar cambia el filtro; el modelo NO se recarga (contrato §2.5).

    Filtros: '' (todas) | 'top' (3 primeras) | estado exacto.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._mode = ""

    def set_mode(self, mode: str) -> None:
        self._mode = mode
        self.invalidateRowsFilter()

    def filterAcceptsRow(self, source_row: int, parent: QModelIndex) -> bool:
        if not self._mode:
            return True
        if self._mode == "top":
            return source_row < 3
        model = self.sourceModel()
        idx = model.index(source_row, COL_STATE)
        return model.data(idx, KindRole) == self._mode


class ScoreBarDelegate(QStyledItemDelegate):
    """Número tabular + microbarra proporcional (chart.1 conv / chart.2 score)."""

    def __init__(self, chart_index: int, parent=None) -> None:
        super().__init__(parent)
        self._t = load_tokens()
        self._color = QColor(self._t.chart(chart_index))

    def paint(self, painter: QPainter, option: QStyleOptionViewItem,
              index: QModelIndex) -> None:
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        t = self._t
        rect = option.rect.adjusted(6, 0, -10, 0)
        text = str(index.data(Qt.ItemDataRole.DisplayRole) or "")
        frac = float(index.data(BarRole) or 0.0)
        f = painter.font()
        f.setPixelSize(t.type_scale("body").size_px)
        f.setWeight(QFont.Weight(600))
        painter.setFont(f)
        painter.setPen(QColor(t.text_primary))
        text_w = 44
        painter.drawText(rect.adjusted(0, 0, 0, 0),
                         Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                         text)
        # microbarra
        bar_x = rect.x() + text_w
        bar_w = max(20, rect.width() - text_w)
        bar_h = 5
        bar_y = rect.center().y() - bar_h // 2
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(t.bg_inset))
        painter.drawRoundedRect(QRectF(bar_x, bar_y, bar_w, bar_h), 2.5, 2.5)
        painter.setBrush(self._color)
        painter.drawRoundedRect(QRectF(bar_x, bar_y, bar_w * frac, bar_h), 2.5, 2.5)
        painter.restore()


class ChipDelegate(QStyledItemDelegate):
    """Chip redondeado con mapa kind→color (STYLE_GUIDE §4.6)."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._t = load_tokens()

    def _kind_color(self, kind: str) -> QColor:
        t = self._t
        mapping = {"eval": t.accent_blue, "candidata": t.accent_violet,
                   "exploracion": t.text_muted, "guardada": t.success,
                   "error": t.error}
        return QColor(mapping.get(kind, t.text_muted))

    def paint(self, painter: QPainter, option: QStyleOptionViewItem,
              index: QModelIndex) -> None:
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        t = self._t
        text = str(index.data(Qt.ItemDataRole.DisplayRole) or "")
        kind = str(index.data(KindRole) or "exploracion")
        color = self._kind_color(kind)
        f = painter.font()
        f.setPixelSize(t.type_scale("caption").size_px)
        f.setWeight(QFont.Weight(700))
        painter.setFont(f)
        fm = painter.fontMetrics()
        w = fm.horizontalAdvance(text) + 16
        h = fm.height() + 4
        rect = QRectF(option.rect.x() + 6,
                      option.rect.center().y() - h / 2, w, h)
        bg = QColor(color)
        bg.setAlphaF(0.15)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(bg)
        painter.drawRoundedRect(rect, t.radius("sm"), t.radius("sm"))
        painter.setPen(QPen(color))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)
        painter.restore()


class RankDelegate(QStyledItemDelegate):
    """Numeral: accent.cyan para top 3, muted para el resto."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._t = load_tokens()

    def paint(self, painter: QPainter, option: QStyleOptionViewItem,
              index: QModelIndex) -> None:
        painter.save()
        t = self._t
        text = str(index.data(Qt.ItemDataRole.DisplayRole) or "")
        try:
            is_top = int(text) <= 3
        except ValueError:
            is_top = False
        f = painter.font()
        f.setPixelSize(t.type_scale("h3").size_px)
        f.setWeight(QFont.Weight(600))
        painter.setFont(f)
        painter.setPen(QColor(t.accent_cyan if is_top else t.text_muted))
        painter.drawText(option.rect.adjusted(8, 0, 0, 0),
                         Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                         text)
        painter.restore()
