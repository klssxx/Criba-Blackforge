"""Constructores de los bloques de zona C (central), D (derecha) y E (footer).

Cada builder devuelve el QFrame contractual y registra widgets nombrados en
`refs` para que CribaMainWindow los actualice (WIDGET_TREE §1).
"""
from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTabBar,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from .ranking import (
    COL_CONV,
    COL_IDEA,
    COL_IMPACT,
    COL_RANK,
    COL_SCORE,
    COL_STATE,
    ChipDelegate,
    RankDelegate,
    RankingFilterProxy,
    RankingModel,
    ScoreBarDelegate,
)
from .tokens import Tokens
from .widgets import (
    ActivityItemWidget,
    DonutChartWidget,
    FeatureWidget,
    HistogramWidget,
    MetricWidget,
    PipelineConnector,
    PipelineStageWidget,
    SourceBarWidget,
    ValueScoreGauge,
    make_chip,
)

PIPELINE_STAGES = [
    ("stageProblema", "◎", "Problema base", "Define el reto central a resolver"),
    ("stageGenerar", "⚙", "Generar", "16 operadores activos"),
    ("stageEvaluar", "▥", "Evaluar", "value_score + convergencia"),
    ("stageGuardar", "▣", "Guardar", "Guardar en catálogo"),
    ("stageEvolucionar", "↻", "Evolucionar", "Itera y mejora continuamente"),
]

FUENTES = ["Tecnología emergente", "Tendencias de negocio",
           "Investigación científica", "Diseño & experiencia",
           "Comunidad & open source"]

BF_FEATURES = [
    ("◉", "Reconocimiento", "Mapa de superficie"),
    ("⇶", "Vectores", "Rutas de ataque"),
    ("▦", "Simulación", "Escenarios seguros"),
    ("⛨", "Contramedidas", "Defensa activa"),
    ("⚗", "Laboratorio", "Pruebas aisladas"),
    ("🎲", "Lotería", "Exploración aleatoria"),
]


def _card(t: Tokens, accent: bool = False) -> tuple[QFrame, QVBoxLayout]:
    f = QFrame()
    f.setObjectName("cardAccent" if accent else "card")
    lay = QVBoxLayout(f)
    lay.setContentsMargins(t.spacing(16), t.spacing(16),
                           t.spacing(16), t.spacing(16))
    lay.setSpacing(t.spacing(12))
    return f, lay


def _section_title(text: str) -> QLabel:
    lbl = QLabel(text.upper())
    lbl.setObjectName("sectionTitle")
    return lbl


def build_motor_card(t: Tokens, refs: dict[str, Any]) -> QFrame:
    card, lay = _card(t)
    lay.addWidget(_section_title("Motor de innovación"))
    desc = QLabel("Convierte problemas en oportunidades. Genera, evalúa y "
                  "prioriza ideas con impacto real.")
    desc.setObjectName("sectionDesc")
    desc.setWordWrap(True)
    lay.addWidget(desc)
    row = QHBoxLayout()
    row.setSpacing(t.spacing(8))
    refs["stages"] = {}
    refs["connectors"] = []
    for i, (key, glyph, title, micro) in enumerate(PIPELINE_STAGES):
        stage = PipelineStageWidget(glyph, title, micro)
        refs["stages"][key] = stage
        row.addWidget(stage, 1)
        if i < len(PIPELINE_STAGES) - 1:
            conn = PipelineConnector()
            refs["connectors"].append(conn)
            row.addWidget(conn)
    lay.addLayout(row)
    return card


def build_idea_card(t: Tokens, refs: dict[str, Any]) -> QFrame:
    card, _outer = _card(t, accent=True)
    QWidget().setLayout(card.layout())  # replace default VBox with HBox
    lay = QHBoxLayout(card)
    lay.setContentsMargins(t.spacing(20), t.spacing(16),
                           t.spacing(20), t.spacing(16))
    lay.setSpacing(t.spacing(20))
    info = QVBoxLayout()
    info.setSpacing(t.spacing(8))
    head = QHBoxLayout()
    kicker = QLabel("IDEA ACTIVA")
    kicker.setObjectName("ideaKicker")
    refs["ideaEstadoChip"] = make_chip("Sin sesión", "exploracion")
    head.addWidget(kicker)
    head.addWidget(refs["ideaEstadoChip"])
    head.addStretch(1)
    info.addLayout(head)
    refs["ideaTitle"] = QLabel("Ninguna idea activa")
    refs["ideaTitle"].setObjectName("ideaTitle")
    refs["ideaTitle"].setWordWrap(True)
    refs["ideaSummary"] = QLabel("Pulsa Nueva idea para definir el problema base")
    refs["ideaSummary"].setObjectName("ideaSummary")
    refs["ideaSummary"].setWordWrap(True)
    info.addWidget(refs["ideaTitle"])
    info.addWidget(refs["ideaSummary"])
    metrics = QHBoxLayout()
    metrics.setSpacing(t.spacing(24))
    refs["mOperadores"] = MetricWidget("Operadores activos", "0/16")
    refs["mIdeas"] = MetricWidget("Ideas generadas", "0")
    refs["mConvergencia"] = MetricWidget("Convergencia", "—")
    refs["mBestScore"] = MetricWidget("Mejor value_score", "—")
    for m in ("mOperadores", "mIdeas", "mConvergencia", "mBestScore"):
        metrics.addWidget(refs[m])
    metrics.addStretch(1)
    info.addLayout(metrics)
    info.addStretch(1)
    lay.addLayout(info, 1)
    refs["scoreGauge"] = ValueScoreGauge()
    lay.addWidget(refs["scoreGauge"], 0, Qt.AlignmentFlag.AlignVCenter)
    return card


def build_ranking_card(t: Tokens, refs: dict[str, Any]) -> QFrame:
    card, lay = _card(t)
    refs["rankingTabs"] = QTabBar()
    refs["rankingTabs"].setObjectName("rankingTabs")
    for name in ("Ranking de Ideas", "Top ideas", "En evaluación", "Exploración"):
        refs["rankingTabs"].addTab(name)
    refs["rankingTabs"].setExpanding(False)
    refs["rankingTabs"].setDrawBase(False)
    lay.addWidget(refs["rankingTabs"])
    refs["rankingModel"] = RankingModel()
    refs["rankingProxy"] = RankingFilterProxy()
    refs["rankingProxy"].setSourceModel(refs["rankingModel"])
    table = QTableView()
    table.setObjectName("rankingTable")
    table.setModel(refs["rankingProxy"])
    table.setAlternatingRowColors(True)
    table.setShowGrid(False)
    table.verticalHeader().setVisible(False)
    table.verticalHeader().setDefaultSectionSize(t.layout("table_row_height"))
    table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
    table.setSelectionMode(QTableView.SelectionMode.SingleSelection)
    table.setEditTriggers(QTableView.EditTrigger.NoEditTriggers)
    table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    hh = table.horizontalHeader()
    hh.setSectionResizeMode(COL_IDEA, QHeaderView.ResizeMode.Stretch)
    for col, width in ((COL_RANK, 44), (COL_SCORE, 130), (COL_CONV, 130),
                       (COL_IMPACT, 96), (COL_STATE, 110)):
        hh.resizeSection(col, width)
    table.setItemDelegateForColumn(COL_RANK, RankDelegate(table))
    table.setItemDelegateForColumn(COL_SCORE, ScoreBarDelegate(2, table))
    table.setItemDelegateForColumn(COL_CONV, ScoreBarDelegate(1, table))
    table.setItemDelegateForColumn(COL_IMPACT, ChipDelegate(table))
    table.setItemDelegateForColumn(COL_STATE, ChipDelegate(table))
    table.setMinimumHeight(t.layout("table_row_height") * 5 + 40)
    refs["rankingTable"] = table
    refs["rankingEmpty"] = QLabel("Aún no hay ideas evaluadas\n"
                                  "El ranking aparecerá tras la primera evaluación")
    refs["rankingEmpty"].setObjectName("sectionDesc")
    refs["rankingEmpty"].setAlignment(Qt.AlignmentFlag.AlignCenter)
    refs["rankingEmpty"].setMinimumHeight(100)
    lay.addWidget(refs["rankingEmpty"])
    lay.addWidget(table)
    table.hide()
    refs["verTodasBtn"] = QPushButton("Ver todas las ideas →")
    refs["verTodasBtn"].setObjectName("linkBtn")
    refs["verTodasBtn"].setCursor(Qt.CursorShape.PointingHandCursor)
    lay.addWidget(refs["verTodasBtn"])
    return card


def build_teaser_card(t: Tokens, refs: dict[str, Any]) -> QFrame:
    card, lay = _card(t, accent=True)
    card.setProperty("accent", "blackforge")
    head = QHBoxLayout()
    head.addWidget(_section_title("Blackforge | Módulo especializado en ciberseguridad"))
    head.addStretch(1)
    refs["irBlackforgeBtn"] = QPushButton("Ir a Blackforge →")
    refs["irBlackforgeBtn"].setObjectName("primary")
    refs["irBlackforgeBtn"].setCursor(Qt.CursorShape.PointingHandCursor)
    head.addWidget(refs["irBlackforgeBtn"])
    lay.addLayout(head)
    desc = QLabel("Reconocimiento, vectores y contramedidas con el mismo motor "
                  "determinista de CRIBA, orientado a defensa.")
    desc.setObjectName("sectionDesc")
    desc.setWordWrap(True)
    lay.addWidget(desc)
    feats = QHBoxLayout()
    feats.setSpacing(t.spacing(8))
    for glyph, title, micro in BF_FEATURES:
        feats.addWidget(FeatureWidget(glyph, title, micro), 1)
    lay.addLayout(feats)
    return card


def build_right_column(t: Tokens, refs: dict[str, Any]) -> QWidget:
    col = QWidget()
    col.setObjectName("rightColumn")
    lay = QVBoxLayout(col)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(t.spacing(16))
    # 7.1 distribución
    dist, dl = _card(t)
    dl.addWidget(_section_title("Distribución de value_score"))
    refs["scoreHistogram"] = HistogramWidget()
    dl.addWidget(refs["scoreHistogram"])
    lay.addWidget(dist)
    # 7.2 fuentes
    fu, fl = _card(t)
    fl.addWidget(_section_title("Fuentes de innovación"))
    refs["staleBand"] = QFrame()
    refs["staleBand"].setObjectName("staleBand")
    sb_lay = QHBoxLayout(refs["staleBand"])
    sb_lay.setContentsMargins(8, 4, 8, 4)
    sb_txt = QLabel("Fuentes desactualizadas. Pulsa Actualizar innovaciones.")
    sb_txt.setObjectName("staleBandText")
    sb_txt.setWordWrap(True)
    sb_lay.addWidget(sb_txt)
    fl.addWidget(refs["staleBand"])
    refs["sourceBars"] = {}
    for name in FUENTES:
        bar = SourceBarWidget(name, 0)
        refs["sourceBars"][name] = bar
        fl.addWidget(bar)
    refs["actualizarFuentesBtn"] = QPushButton("Actualizar innovaciones")
    refs["actualizarFuentesBtn"].setObjectName("ghost")
    refs["actualizarFuentesBtn"].setCursor(Qt.CursorShape.PointingHandCursor)
    fl.addWidget(refs["actualizarFuentesBtn"])
    lay.addWidget(fu)
    # 7.3 categorías
    cat, catl = _card(t)
    catl.addWidget(_section_title("Categorías de innovación"))
    refs["catDonut"] = DonutChartWidget()
    refs["catDonut"].setMinimumHeight(140)
    catl.addWidget(refs["catDonut"], 0, Qt.AlignmentFlag.AlignHCenter)
    refs["donutLegend"] = QVBoxLayout()
    refs["donutLegend"].setSpacing(4)
    catl.addLayout(refs["donutLegend"])
    lay.addWidget(cat)
    # 7.4 actividad
    act, al = _card(t)
    al.addWidget(_section_title("Actividad reciente"))
    refs["activityList"] = QVBoxLayout()
    refs["activityList"].setSpacing(4)
    al.addLayout(refs["activityList"])
    refs["activityEmpty"] = QLabel("Sin actividad todavía")
    refs["activityEmpty"].setObjectName("sectionDesc")
    refs["activityList"].addWidget(refs["activityEmpty"])
    refs["historialCompletoBtn"] = QPushButton("Ver historial completo")
    refs["historialCompletoBtn"].setObjectName("linkBtn")
    refs["historialCompletoBtn"].setCursor(Qt.CursorShape.PointingHandCursor)
    al.addWidget(refs["historialCompletoBtn"])
    lay.addWidget(act)
    lay.addStretch(1)
    return col


def add_activity(t: Tokens, refs: dict[str, Any], timestamp: str,
                 kind: str, text: str, max_visible: int = 6) -> None:
    refs["activityEmpty"].hide()
    item = ActivityItemWidget(timestamp, kind, text)
    refs["activityList"].insertWidget(0, item)
    # cap: máx 6 visibles (contrato 7.4)
    count = refs["activityList"].count()
    for i in range(count - 1, -1, -1):
        w = refs["activityList"].itemAt(i).widget()
        if isinstance(w, ActivityItemWidget) and i >= max_visible:
            refs["activityList"].removeWidget(w)
            w.deleteLater()
