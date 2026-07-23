# WIDGET_TREE_CRIBA.md
Árbol de widgets PySide6 de la pantalla principal CRIBA
Versión: 1.0.0 · Fecha: 2026-07-23 · Estado: CONTRATO (no implementado aún)

Objetivo: que dos sesiones distintas implementen la misma pantalla con mínima
desviación. Los objectName son NORMATIVOS (el QSS global depende de ellos).

======================================================================
1. ÁRBOL COMPLETO
======================================================================

QMainWindow "CribaMainWindow"  (min 1360x768, título "CRIBA — Innovación sin límites")
└── QWidget central  #appRoot        [QHBoxLayout, margins 0, spacing 0]
    ├── QFrame #sidebar              (ancho fijo 232) [QVBoxLayout, margins 16, spacing 8]
    │   ├── QWidget #brandBlock      [QVBoxLayout]
    │   │   ├── QLabel #brandLogo        ("CRIBA", display, degradado vía QPainter o rich text)
    │   │   └── QLabel #brandTagline     ("INNOVACIÓN SIN LÍMITES", caption muted)
    │   ├── (spacing 24)
    │   ├── QPushButton #navbtn  navNuevaIdea        (checkable, grupo exclusivo)
    │   ├── QPushButton #navbtn  navGenerar
    │   ├── QPushButton #navbtn  navEvaluar
    │   ├── QPushButton #navbtn  navGuardar
    │   ├── QPushButton #navbtn  navActualizar
    │   ├── QPushButton #navbtn  navHistorial
    │   ├── QPushButton #navbtnBlackforge navBlackforge   (contenedor destacado violeta)
    │   ├── stretch
    │   └── QFrame #blackforgeTeaserMini   [QVBoxLayout]  (logo + "PODER SIN LÍMITES", clicable)
    │
    └── QWidget #mainColumn          [QVBoxLayout, margins 0, spacing 0]
        ├── QFrame #topbar           (alto fijo 72) [QHBoxLayout, margins 20/12, spacing 16]
        │   ├── QWidget #greetingBlock   [QVBoxLayout]
        │   │   ├── QLabel #greetingTitle    ("Hola, Innovador", h2)
        │   │   └── QLabel #greetingSub      (caption secondary)
        │   ├── stretch
        │   ├── QWidget #sessionBadge    [QHBoxLayout]  (punto success + "Sesión activa")
        │   ├── QLabel  #modeBadge       ("MODO: INNOVACIÓN", chip)
        │   ├── QWidget #clockBlock      [QVBoxLayout]
        │   │   ├── QLabel #dateLabel        (caption uppercase muted)
        │   │   └── QLabel #timeLabel        (h3 tabular; QTimer 1 s)
        │   └── QToolButton #notifBtn    (icono campana, icon.md)
        │
        ├── QWidget #contentRow      [QHBoxLayout, margins 20, spacing 20, stretch central]
        │   ├── QScrollArea #centerScroll  (frameless, solo vertical, widgetResizable)
        │   │   └── QWidget #centerColumn  [QVBoxLayout, spacing 16]
        │   │       ├── QFrame #card  motorCard
        │   │       │   ├── QLabel #sectionTitle ("MOTOR DE INNOVACIÓN")
        │   │       │   ├── QLabel #sectionDesc  (caption)
        │   │       │   └── QWidget #pipelineRow [QHBoxLayout, spacing 8]
        │   │       │       ├── PipelineStageWidget stageProblema   (custom, ver §2.1)
        │   │       │       ├── PipelineConnector
        │   │       │       ├── PipelineStageWidget stageGenerar
        │   │       │       ├── PipelineConnector
        │   │       │       ├── PipelineStageWidget stageEvaluar
        │   │       │       ├── PipelineConnector
        │   │       │       ├── PipelineStageWidget stageGuardar
        │   │       │       ├── PipelineConnector
        │   │       │       └── PipelineStageWidget stageEvolucionar
        │   │       │
        │   │       ├── QFrame #cardAccent  ideaActivaCard  [QHBoxLayout, spacing 20]
        │   │       │   ├── QWidget #ideaInfo [QVBoxLayout]  (stretch 1)
        │   │       │   │   ├── QWidget [QHBoxLayout]: QLabel #ideaKicker ("IDEA ACTIVA")
        │   │       │   │   │   + QLabel #chip ideaEstadoChip
        │   │       │   │   ├── QLabel #ideaTitle    (h1, wrap, máx 2 líneas)
        │   │       │   │   ├── QLabel #ideaSummary  (body secondary, wrap, máx 3 líneas)
        │   │       │   │   └── QWidget #ideaMetricsRow [QHBoxLayout|QGridLayout 2x2]
        │   │       │   │       ├── MetricWidget mOperadores  ("Operadores activos", "16/16")
        │   │       │   │       ├── MetricWidget mIdeas       ("Ideas generadas", N)
        │   │       │   │       ├── MetricWidget mConvergencia("Convergencia", NN%)
        │   │       │   │       └── MetricWidget mBestScore   ("Mejor value_score", 0.NN)
        │   │       │   └── ValueScoreGauge #scoreGauge  (custom QPainter, fijo ~180)
        │   │       │
        │   │       ├── QFrame #card  rankingCard [QVBoxLayout]
        │   │       │   ├── QTabBar #rankingTabs  (Ranking de Ideas / Top ideas /
        │   │       │   │                          En evaluación / Exploración)
        │   │       │   ├── QTableView #rankingTable
        │   │       │   │     model: RankingModel (QAbstractTableModel)
        │   │       │   │     delegates: ScoreBarDelegate (cols score/convergencia),
        │   │       │   │                ChipDelegate (cols impacto/estado)
        │   │       │   └── QPushButton #linkBtn verTodasBtn ("Ver todas las ideas ->")
        │   │       │
        │   │       └── QFrame #cardAccent  blackforgeTeaserCard [QVBoxLayout]
        │   │           ├── QWidget [QHBoxLayout]
        │   │           │   ├── QLabel #sectionTitle ("BLACKFORGE | MÓDULO ...")
        │   │           │   ├── stretch
        │   │           │   └── QPushButton #primary irBlackforgeBtn ("Ir a Blackforge ->")
        │   │           ├── QLabel #sectionDesc
        │   │           └── QWidget #bfFeaturesRow [QHBoxLayout, 5x FeatureWidget]
        │   │               (Reconocimiento · Vectores · Simulación ·
        │   │                Contramedidas · Laboratorio)
        │   │
        │   └── QScrollArea #rightScroll  (ancho fijo 300-340, frameless, vertical)
        │       └── QWidget #rightColumn [QVBoxLayout, spacing 16]
        │           ├── QFrame #card distribCard
        │           │   ├── QLabel #sectionTitle ("DISTRIBUCIÓN DE VALUE_SCORE")
        │           │   └── HistogramWidget #scoreHistogram (custom QPainter)
        │           ├── QFrame #card fuentesCard
        │           │   ├── QLabel #sectionTitle ("FUENTES DE INNOVACIÓN")
        │           │   ├── 5x SourceBarWidget (QLabel + QProgressBar 6px + QLabel %)
        │           │   └── QPushButton #ghost actualizarFuentesBtn
        │           ├── QFrame #card categoriasCard
        │           │   ├── QLabel #sectionTitle ("CATEGORÍAS DE INNOVACIÓN")
        │           │   ├── DonutChartWidget #catDonut (custom QPainter)
        │           │   └── QWidget #donutLegend [QVBoxLayout, 5x LegendRow]
        │           └── QFrame #card actividadCard
        │               ├── QLabel #sectionTitle ("ACTIVIDAD RECIENTE")
        │               ├── QVBoxLayout con N x ActivityItemWidget (máx 6 visibles)
        │               └── QPushButton #linkBtn historialCompletoBtn
        │
        └── QFrame #footerStrip      (alto fijo 36) [QHBoxLayout, margins 20/6, spacing 12]
            ├── FooterSegment fsModelo       ("Modelo activo", valor)
            ├── divisor (QFrame #vline)
            ├── FooterSegment fsSesion       ("ID de sesión", valor tabular)
            ├── divisor
            ├── FooterSegment fsIdeas        ("Ideas generadas", N)
            ├── divisor
            ├── FooterSegment fsConvergencia ("Convergencia global", NN%)
            ├── divisor
            ├── FooterSegment fsUltima       ("Última actualización", fecha hora)
            ├── divisor
            └── FooterSegment fsFuentes      ("Fuentes actualizadas", "Hace N min",
                                              propiedad dinámica freshness=ok|warn|stale)

======================================================================
2. WIDGETS CUSTOM REUTILIZABLES (clases a crear en ui/widgets.py futuro)
======================================================================

2.1 PipelineStageWidget(QFrame)
    API: set_state(state: "pending"|"active"|"done"|"error")
    Contenido: medallón circular con icono (icon.lg) + QLabel título (h3)
    + QLabel micro (caption muted). Propiedad dinámica "state" → QSS.

2.2 PipelineConnector(QWidget)
    Línea 2px pintada en paintEvent; set_lit(bool) tiñe accent.cyan.

2.3 MetricWidget(QWidget)
    QVBoxLayout: QLabel valor (#metricValue, h2 tabular) + QLabel etiqueta
    (#metricLabel, caption muted). API: set_value(str).

2.4 ValueScoreGauge(QWidget)
    paintEvent con QPainter: arco 270°, pista bg.inset, progreso con
    QConicalGradient (grad.brand), cap redondo. Centro: valor display +
    "VALUE_SCORE" + percentil. API: set_score(float 0-1), set_percentile(str).
    QGraphicsDropShadowEffect nivel 2. Animación de valor con
    QPropertyAnimation sobre property "score" (300 ms, OutCubic).

2.5 RankingModel(QAbstractTableModel) + QSortFilterProxyModel
    Columnas: rank, titulo, value_score, convergencia, impacto, estado.
    El QTabBar cambia el filtro del proxy (estado), NO recarga el modelo.

2.6 ScoreBarDelegate(QStyledItemDelegate)
    Pinta número tabular + microbarra proporcional (color por columna).

2.7 ChipDelegate(QStyledItemDelegate)
    Pinta chip redondeado con mapa kind→color de STYLE_GUIDE §4.6.

2.8 HistogramWidget(QWidget)
    Barras verticales chart.2; barra máxima resaltada + etiqueta de valor.
    API: set_bins(list[tuple[float, int]]).

2.9 SourceBarWidget(QWidget)
    QGridLayout: etiqueta caption / % tabular / QProgressBar 6px chart.1.
    API: set_percent(int).

2.10 DonutChartWidget(QWidget)
    paintEvent QPainter, drawArc por segmento con hueco 2°, centro texto.
    API: set_segments(list[tuple[str, float, QColor]]), set_center(str, str).

2.11 ActivityItemWidget(QWidget)
    timestamp + punto semántico + texto. API: from_event(dict).

2.12 FeatureWidget(QWidget)
    icono lineal + título caption-strong + micro caption muted.

2.13 FooterSegment(QWidget)
    QHBoxLayout: QLabel etiqueta muted + QLabel valor primary tabular.
    API: set_value(str), set_freshness("ok"|"warn"|"stale") (solo fsFuentes).

2.14 NavButton(QPushButton)
    checkable; subtítulo secundario pintado o vía layout interno;
    API: set_state("normal"|"running"|"done"|"error", msg: str|None).
    Estados running/done/error según UI_CONTRACT §5.

======================================================================
3. LAYOUT Y COMPORTAMIENTO
======================================================================

- QHBoxLayout raíz: sidebar (fijo) + mainColumn (stretch 1). Sin QSplitter:
  las 3 columnas tienen anchos contractuales, el usuario no las redimensiona.
- contentRow: centerScroll stretch 1, rightScroll ancho fijo
  (340 → setFixedWidth; a 300 si QScreen disponible < 1500 px de ancho útil).
- Todos los QScrollArea: setFrameShape(NoFrame), horizontal OFF,
  scrollbar estilizada por QSS global.
- Ejecuciones (Generar/Evaluar/Actualizar) SIEMPRE en QThread/QThreadPool
  + señales; la GUI nunca se congela. Los NavButton reflejan running.
- Reloj: QTimer 1000 ms actualiza #timeLabel y #dateLabel.
- QSS: un único QSS global generado desde data/theme_criba.json aplicado en
  QApplication.setStyleSheet(). Prohibido setStyleSheet por widget salvo
  casos pintados por delegate/QPainter.
- Densidad: fuente base 13 px; probar con QT_SCALE_FACTOR=1 en 1360x768.

======================================================================
4. ARCHIVOS FUTUROS PREVISTOS (no crear aún)
======================================================================

src/criba/ui/tokens.py    — dataclasses frozen cargadas desde theme_criba.json
src/criba/ui/theme.py     — render QSS desde tokens + apply()
src/criba/ui/widgets.py   — clases §2
src/criba/ui/main_window.py — árbol §1
gui.py actual queda intacto hasta el gate de implementación.
