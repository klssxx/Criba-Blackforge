# WIDGET_TREE_BLACKFORGE.md
Árbol de widgets PySide6 de la pantalla principal BLACKFORGE
Versión: 1.0.0 · Fecha: 2026-07-24 · Estado: CONTRATO (no implementado aún)

Objetivo: que dos sesiones distintas implementen la misma pantalla con mínima
desviación. Los objectName son NORMATIVOS (el QSS global depende de ellos).
Hermano de WIDGET_TREE_CRIBA.md: misma estructura de árbol y convenciones.

======================================================================
1. ÁRBOL COMPLETO
======================================================================

QMainWindow "BlackforgeMainWindow"  (min 1360x768, título "BLACKFORGE — Fuerza técnica")
└── QWidget central  #appRoot        [QHBoxLayout, margins 0, spacing 0]
    ├── QFrame #sidebar              (ancho fijo 240) [QVBoxLayout, margins 16, spacing 8]
    │   ├── QWidget #brandBlock      [QVBoxLayout]
    │   │   ├── QLabel #brandCriba       ("CRIBA", caption muted)
    │   │   ├── QLabel #brandLogo        ("BLACKFORGE", display, degradado naranja via QPainter/rich)
    │   │   └── QLabel #brandTagline     ("FUERZA TÉCNICA", caption muted)
    │   ├── (spacing 24)
    │   ├── QPushButton #navbtn  navResumen         (checkable, grupo exclusivo)
    │   ├── QPushButton #navbtn  navReconocimiento
    │   ├── QPushButton #navbtn  navVectores
    │   ├── QPushButton #navbtn  navSimulacion
    │   ├── QPushButton #navbtn  navContramedidas
    │   ├── QPushButton #navbtn  navLaboratorio
    │   ├── QPushButton #navbtn  navHistorial
    │   ├── QPushButton #navbtnReturn navVolverCriba   (contenedor destacado naranja)
    │   ├── stretch
    │   └── QFrame #bfMarkMini   [QVBoxLayout]  (logo "BF" + "PODER SIN LÍMITES", clicable)
    │
    └── QWidget #mainColumn          [QVBoxLayout, margins 0, spacing 0]
        ├── QFrame #topbar           (alto fijo 72) [QHBoxLayout, margins 20/12, spacing 16]
        │   ├── QWidget #greetingBlock   [QVBoxLayout]
        │   │   ├── QLabel #greetingTitle    ("Blackforge · <modo>", h2)
        │   │   └── QLabel #greetingSub      (caption secondary, estado de sesión)
        │   ├── stretch
        │   ├── QWidget #sandboxBadge   [QHBoxLayout]  (punto success/warning + texto)
        │   ├── QLabel  #modeBadge       ("MODO: BLACKFORGE", chip naranja)
        │   ├── QWidget #clockBlock      [QVBoxLayout]
        │   │   ├── QLabel #dateLabel        (caption uppercase muted)
        │   │   └── QLabel #timeLabel        (h3 tabular; QTimer 1 s)
        │   └── QToolButton #notifBtn    (icono campana, icon.md)
        │
        ├── QWidget #contentRow      [QHBoxLayout, margins 20, spacing 20, stretch central]
        │   ├── QScrollArea #centerScroll  (frameless, solo vertical, widgetResizable)
        │   │   └── QWidget #centerColumn  [QVBoxLayout, spacing 16]
        │   │       ├── QFrame #cardAccent  heroPanel   [QVBoxLayout/overlay]
        │   │       │   ├── QLabel #heroImage   (QPixmap data/assets/blackforge_hero.png,
        │   │       │   │                         scaled KeepAspectRatioByExpanding)
        │   │       │   ├── QWidget #heroOverlay [QVBoxLayout]
        │   │       │   │   ├── QLabel #heroTitle   ("BLACKFORGE ENGINE", display)
        │   │       │   │   ├── QLabel #heroSub     (caption)
        │   │       │   │   ├── QWidget [QHBoxLayout]: QLabel #heroStatus (chip estado forja)
        │   │       │   │   └── ForgeIntegrityGauge #forgeGauge  (custom QPainter, ~170)
        │   │       │   └── QWidget #heroPipelineRow [QHBoxLayout, 4x HeroStageWidget]
        │   │       │       (Reconocer · Vectorizar · Simular · Contrarrestar)
        │   │       │
        │   │       └── QFrame #card  modulesCard [QVBoxLayout]
        │   │           ├── QLabel #sectionTitle ("MÓDULOS PRINCIPALES")
        │   │           └── QWidget #modulesRow [QHBoxLayout, 5x ModuleWidget]
        │   │               (Reconocimiento · Vectores · Simulación ·
        │   │                Contramedidas · Laboratorio)
        │   │
        │   └── QScrollArea #rightScroll  (ancho fijo 300-340, frameless, vertical)
        │       └── QWidget #rightColumn [QVBoxLayout, spacing 16]
        │           ├── QFrame #card metricCard
        │           │   ├── QLabel #sectionTitle ("ESTADO DE SESIÓN BLACKFORGE")
        │           │   ├── QWidget #sessionMetricRow [QHBoxLayout|QGridLayout]
        │           │   │   ├── MetricWidget mIdeas     ("Ideas técnicas activas", N)
        │           │   │   ├── MetricWidget mCandidatos("Candidatos válidos", N)
        │           │   │   ├── MetricWidget mCoverage  ("Coverage simulación", NN%)
        │           │   │   └── MetricWidget mScore     ("Score medio", 0.NN)
        │           │   └── QLabel #chip sessionStatusChip
        │           ├── QFrame #card compositionCard
        │           │   ├── QLabel #sectionTitle ("SUPERFICIE / COBERTURA")
        │           │   └── CompositionWidget #compoDonut (custom QPainter donut/barras)
        │           └── QFrame #card alertsCard
        │               ├── QLabel #sectionTitle ("ALERTAS / GUARDRAILS")
        │               ├── QVBoxLayout con N x AlertItemWidget (máx 6 visibles)
        │               └── QPushButton #linkBtn verTodasAlertasBtn (si aplica)
        │
        └── QFrame #footerStrip      (alto fijo 36) [QHBoxLayout, margins 20/6, spacing 12]
            ├── FooterSegment fsModelo       ("Modelo activo", valor)
            ├── divisor (QFrame #vline)
            ├── FooterSegment fsSesion       ("ID de sesión", valor tabular)
            ├── divisor
            ├── FooterSegment fsPerfil       ("Perfil", valor)
            ├── divisor
            ├── FooterSegment fsSandbox      ("Sandbox", OK/Requerido,
                                              propiedad dinámica sandbox=ok|req)
            ├── divisor
            ├── FooterSegment fsRiesgo       ("Riesgo", Bajo/Medio/Alto,
                                              propiedad dinámica risk=low|med|high)
            ├── divisor
            └── FooterSegment fsUltima       ("Última actualización", fecha hora)

======================================================================
2. WIDGETS CUSTOM REUTILIZABLES (clases a crear en ui/widgets_bf.py futuro)
======================================================================

2.1 ForgeIntegrityGauge(QWidget)
    paintEvent con QPainter: arco 270°, pista bg.inset, progreso con
    QConicalGradient (grad.brand), cap redondo. Centro: valor display +
    "FORGE_INTEGRITY" + percentil. API: set_score(float 0-1), set_percentile(str).
    QGraphicsDropShadowEffect nivel 2. Animación de valor con
    QPropertyAnimation sobre property "score" (300 ms, OutCubic).
    ÚNICO elemento con glow máximo.

2.2 HeroStageWidget(QFrame)
    API: set_state(state: "pending"|"active"|"done"|"error")
    Contenido: medallón circular con icono (icon.lg) + QLabel título (h3)
    + QLabel micro (caption muted). Propiedad dinámica "state" → QSS.

2.3 HeroConnector(QWidget)
    Línea 2px pintada en paintEvent; set_lit(bool) tiñe accent.orange.

2.4 MetricWidget(QWidget)
    QVBoxLayout: QLabel valor (#metricValue, h2 tabular) + QLabel etiqueta
    (#metricLabel, caption muted). API: set_value(str). (Reutilizable de CRIBA.)

2.5 CompositionWidget(QWidget)
    Donut o barras: colores chart.orange/neutral/green/red por magnitud.
    API: set_segments(list[tuple[str, float, QColor]]), set_center(str, str).

2.6 AlertItemWidget(QWidget)
    [icono semántico] [texto caption primary, máx 2 líneas] [badge severidad].
    API: from_alert(dict). Estado vacío: "Sin alarmas · sandbox estable".

2.7 ModuleWidget(QWidget)
    icono lineal (icon.lg) + título caption-strong + micro caption muted.
    (Equivalente a FeatureWidget de CRIBA.) Clic = nav correspondiente.

2.8 FooterSegment(QWidget)
    QHBoxLayout: QLabel etiqueta muted + QLabel valor primary tabular.
    API: set_value(str), set_sandbox("ok"|"req"), set_risk("low"|"med"|"high").

2.9 NavButton(QPushButton)  (hereda de CRIBA NavButton)
    checkable; subtítulo secundario pintado o vía layout interno;
    API: set_state("normal"|"running"|"done"|"error", msg: str|None).
    Estados running/done/error según UI_CONTRACT §7.

======================================================================
3. LAYOUT Y COMPORTAMIENTO
======================================================================

- QHBoxLayout raíz: sidebar (fijo) + mainColumn (stretch 1). Sin QSplitter:
  las columnas tienen anchos contractuales, el usuario no las redimensiona.
- contentRow: centerScroll stretch 1, rightScroll ancho fijo
  (340 → setFixedWidth; a 300 si QScreen disponible < 1500 px de ancho útil).
- Hero SIEMPRE arriba del centerScroll y dominante; nunca bajo scroll inicial.
- Todos los QScrollArea: setFrameShape(NoFrame), horizontal OFF,
  scrollbar estilizada por QSS global.
- Ejecuciones (Simulación/Reconocimiento) SIEMPRE en QThread/QThreadPool
  + señales; la GUI nunca se congela. Los NavButton reflejan running.
- Reloj: QTimer 1000 ms actualiza #timeLabel y #dateLabel.
- QSS: un único QSS global generado desde data/theme_blackforge.json aplicado
  en QApplication.setStyleSheet(). Prohibido setStyleSheet por widget salvo
  casos pintados por delegate/QPainter.
- Densidad: fuente base 13 px; probar con QT_SCALE_FACTOR=1 en 1360x768.
- Imagen hero: cargada desde data/assets/blackforge_hero.png en #heroImage;
  escalado KeepAspectRatioByExpanding, alineada centro; overlay con
  grad.herald para legibilidad. No se recoloriza ni se oculta.

======================================================================
4. ARCHIVOS FUTUROS PREVISTOS (no crear aún)
======================================================================

src/criba/ui/tokens_bf.py    — dataclasses frozen cargadas desde theme_blackforge.json
src/criba/ui/theme_bf.py     — render QSS desde tokens + apply()
src/criba/ui/widgets_bf.py   — clases §2 (ForgeIntegrityGauge, HeroStageWidget, ...)
src/criba/ui/blackforge_window.py — árbol §1
gui.py actual queda intacto hasta el gate de implementación.
