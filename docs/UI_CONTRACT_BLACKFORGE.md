# UI_CONTRACT_BLACKFORGE.md
Contrato visual y estructural de BLACKFORGE — Módulo especializado de ciberseguridad / hacking / innovación técnica
Versión: 1.0.0 · Fecha: 2026-07-24 · Estado: CONTRATO (no implementado aún)

Este documento es NORMATIVO. Cualquier implementación futura de la pantalla
principal de BLACKFORGE debe cumplirlo sin desviación relevante. Complementos:
- STYLE_GUIDE_BLACKFORGE.md  -> tokens y reglas estéticas
- WIDGET_TREE_BLACKFORGE.md  -> mapeo PySide6 exacto
- STATE_MATRIX_BLACKFORGE.md -> estados visuales
- ../data/theme_blackforge.json -> tokens machine-readable (fuente única)

Es hermano de CRIBA (UI_CONTRACT_CRIBA.md) pero con firma cromática propia:
negro carbón + naranja intenso. Mantiene misma calidad visual, distinto tono.

======================================================================
1. VISIÓN DE DISEÑO
======================================================================

BLACKFORGE es el submodo más poderoso y especializado de CRIBA. Debe percibirse
como:
* una "forja" de ideas técnicas;
* un laboratorio de seguridad;
* una capa de análisis serio;
* un módulo premium y exclusivo;
* "entrar en un submodo avanzado" de CRIBA.

Lenguaje visual obligatorio:
- dark industrial-premium: fondo negro carbón con tinte cálido (no azul);
- acento naranja intenso (#FF7A1A) como color de marca y fuego de la forja;
- glassmorphism oscuro ligero (cards con borde suave + glow naranja sutil);
- texto blanco cálido / gris arena;
- bordes redondeados coherentes (una sola escala de radios);
- iconografía lineal unificada, coherente con CRIBA;
- máximo 2 niveles de glow en toda la pantalla (naranja, no cian);
- densidad alta pero controlada: mucha información, cero desbordamiento;
- hero central: el render de la criba se conserva como elemento icónico, pero
  sus overlays hablan de BLACKFORGE (laboratorio, sandbox, superficie de
  ataque simulada), no de producción fabril.

Prohibido:
- paleta azul/cian/violeta dominante (eso es CRIBA, no BLACKFORGE);
- estética industrial literal (SCADA, ERP fabril, panel IoT);
- look ciberpunk caótico o videojuego;
- software de mantenimiento genérico;
- ciberseguridad ofensiva no autorizada / malware operativo / instrucciones de
  explotación real / targets externos reales: la interfaz es innovación,
  simulación y análisis controlado (sandbox + guardrails + autorización).

======================================================================
2. ESTRUCTURA MACRO DE LA PANTALLA (8 ZONAS)
======================================================================

+--------------------------------------------------------------------------+
| A SIDEBAR |  B TOP BAR                                                    |
| (fijo     |---------------------------------------------------------------|
|  240 px)  |  C HERO CENTRAL (flexible, dominante) | D PANEL DER. SUP 300px |
|           |                                     |------------------------|
|           |                                     | E PANEL DER. MEDIO      |
|           |---------------------------------------------------------------|
|           |  G PANEL INFERIOR CENTRAL (módulos/acciones) | F PANEL DER. INF |
|           |---------------------------------------------------------------|
|           |  H FOOTER STRIP (alto 36 px)                                   |
+--------------------------------------------------------------------------+

Proporciones y límites (coherentes con CRIBA, mismo ancho de sidebar/base):
- A: ancho fijo 240 px (min 216 en 1360x768). Nunca colapsa ni scroll horizontal.
- B: alto fijo 72 px, ocupa todo el ancho a la derecha del sidebar.
- C: flexible; contiene el hero dominante + overlays. Scroll vertical propio si hace falta.
- D/E/F: columna derecha 300-340 px; en 1360x768 se fija a 300. Cada bloque
  scroll vertical propio (QScrollArea por bloque o columna).
- G: panel inferior central, alineado bajo el hero, mismo ancho que C.
- H: alto fijo 36 px, ancho completo bajo C+D+E+F+G.
- Prohibido scroll horizontal global en cualquier resolución objetivo.

Grid interno: gutter spacing.16 entre bloques; márgenes exteriores
spacing.20; separación entre zonas C y D: spacing.20.

======================================================================
3. ZONA A — SIDEBAR IZQUIERDO
======================================================================

Orden vertical:
1. Bloque marca combinada: logo "CRIBA" (pequeño, text.muted) + "BLACKFORGE"
   (typography.display, degradado naranja grad.brand) + subtítulo
   "FUERZA TÉCNICA" (caption, text.muted, tracking amplio).
2. Separación spacing.24.
3. 8 botones de navegación (contrato en sección 7), cada uno con icono +
   nombre + descripción implícita; estados normal/hover/activo/disabled.
4. Stretch (espacio flexible).
5. Marca BF inferior: bloque "BF" con lema "PODER SIN LÍMITES", borde naranja
   suave, glow nivel 1; y botón "Volver a CRIBA" (acción de retorno al modo
   innovación de CRIBA).

======================================================================
4. ZONA B — TOP BAR
======================================================================

Izquierda: saludo "Blackforge · <modo actual>" (h2) + subtexto
  "<estado de sesión>" (caption, secondary).
Centro-derecha: indicador de sandbox (punto color.success + "Sandbox OK" /
  warning + "Autorización requerida").
Derecha: fecha (caption uppercase), hora (h3 monoespaciada/tabular),
  icono campana de notificación (icon.md), badge de modo
  ("MODO: BLACKFORGE" con acento naranja).

======================================================================
5. ZONA C — HERO CENTRAL (LA CRIBA REINTERPRETADA)
======================================================================

- Gran panel visual (QFrame#heroPanel) con la imagen de la criba
  (data/assets/blackforge_hero.png) como fondo icónico conservado.
- La imagen NO es decorativa: funciona como pieza de identidad y como
  "superficie de ataque simulada" / "motor Blackforge en ejecución".
- Overlays (sobre la imagen, con grad.herald y text.primary):
  * Título principal: "BLACKFORGE ENGINE" + subtítulo "Laboratorio de
    innovación en ciberseguridad · sandbox activo".
  * Estado de forja (badge): operativa / en análisis / en simulación /
    en sandbox / revisión requerida.
  * Métrica destacada central (gauge único, glow nivel 2): "FORGE_INTEGRITY"
    (0-1) — índice compuesto de readiness del laboratorio.
  * Mini-pipeline técnico de 4 etapas conectadas (Reconocer → Vectorizar →
    Simular → Contrarrestar) como ribbon inferior del hero.
- Nada de texto industrial literal (producción/hidráulica/granulometría) salvo
  como inspiración de composición, no como contenido final.

======================================================================
6. ZONAS D / E / F — COLUMNA DERECHA (3 BLOQUES)
======================================================================

6.1 D — PANEL SUPERIOR: MÉTRICA PRINCIPAL / ESTADO DE SESIÓN
- Card con título h3 + métrica principal (número h2 tabular) que representa
  ideas técnicas activas / candidatos válidos / coverage de simulación /
  score medio / readiness de laboratorio.
- Chip de estado de sesión Blackforge (operativa / en análisis / en simulación
  / en sandbox / revisión requerida).

6.2 E — PANEL MEDIO: DISTRIBUCIÓN / COMPOSICIÓN
- Card con donut o barras representando la "superficie de ataque" o
  "cobertura por tipo de vector" o "distribución de ideas por categoría"
  técnica (familias ofensivas/defensivas, mix). Colores chart.orange /
  chart.neutral / chart.green / chart.red en orden de magnitud.

6.3 F — PANEL INFERIOR: ALERTAS / GUARDRAILS
- Card con lista de alertas/guardrails: sin alarmas / revisión manual
  requerida / autorización requerida / sandbox obligatorio / riesgo alto.
- Cada item: icono semántico (success/warning/error) + texto caption + badge
  de severidad. Estado vacío diseñado ("Sin alarmas · sandbox estable").

======================================================================
7. NAVEGACIÓN INTERNA DE BLACKFORGE (8 BOTONES)
======================================================================

La navegación NO es industrial literal. Refleja el módulo de innovación
técnica. Exactamente estos, en este orden. No se añaden botones de primer nivel.

| # | Texto principal   | Icono      | Descripción implícita                              | Función |
|---|-------------------|------------|----------------------------------------------------|---------|
| 1 | Resumen           | cuadrícula | Vista general del laboratorio Blackforge          | Muestra el dashboard resumen (hero + paneles) |
| 2 | Reconocimiento    | radar      | Superficie, activos, huella simulada              | Abre módulo de reconocimiento (sandbox) |
| 3 | Vectores          | diana      | Catálogo de vectores técnicos                      | Abre catálogo de vectores simulados |
| 4 | Simulación        | engranaje  | Ejecuta el motor de simulación controlada          | Lanza simulación en sandbox |
| 5 | Contramedidas     | escudo     | Candidatos a contramedida                          | Abre módulo de contramedidas |
| 6 | Laboratorio       | matraz     | Experimentación, lab notes, ideas técnicas         | Abre laboratorio / notas |
| 7 | Historial        | reloj      | Sesiones y experimentos previos                    | Abre vista de historial |
| 8 | Volver a CRIBA    | flecha-atrás| Sale del modo Blackforge                           | Cambia a modo INNOVACIÓN de CRIBA (QStackedWidget raíz) |

Anatomía del botón (todos iguales, hereda de NavButton de CRIBA):
- fila horizontal: icono (icon.md, 20px) + columna [texto principal body-strong,
  texto secundario caption text.muted]; alto 54 px; radio radius.md;
  padding spacing.12; ancho completo del sidebar menos márgenes.
- El botón 8 (Volver a CRIBA) lleva SIEMPRE contenedor destacado: borde
  color.accent.orange al 40%, fondo bg.card, para señalar retorno de modo.

Estados (aplican a los 8; detalle QSS en STYLE_GUIDE):
- normal:    fondo transparente, texto primary, icono secondary.
- hover:     fondo bg.card.hover, icono accent.orange.
- activo:    fondo bg.card, barra izquierda 3px accent.orange, glow nivel 1,
             texto primary, icono accent.orange.
- disabled:  opacidad 40%, sin hover, cursor normal.
- ejecutando: icono sustituido por spinner; barra izquierda accent.orange
             animada; texto secundario = mensaje de progreso
             (p.ej. "Simulando vectores 9/16..."). Botón no clicable.
- completado: flash breve (<1.2 s) de barra izquierda color.success + check.
- error:     barra izquierda color.error, texto secundario = motivo corto.

======================================================================
8. ZONA G — PANEL INFERIOR CENTRAL (MÓDULOS PRINCIPALES)
======================================================================

- Card ancho completo bajo el hero, con 5 tarjetas de acceso rápido
  (FeatureWidget) a los módulos principales:
  Reconocimiento · Vectores · Simulación · Contramedidas · Laboratorio.
- Cada tarjeta: icono lineal (icon.lg) + título caption-strong + microdescripción
  caption muted. Clic = misma acción que el botón de sidebar correspondiente.
- Alineadas en fila; en 1360x768 pasan a grid 2x3 o scroll horizontal interno
  del card (nunca scroll horizontal global de la ventana).

======================================================================
9. ZONA H — FOOTER STRIP
======================================================================

Franja única alto 36 px, fondo bg.panel, borde superior border.soft.
6 segmentos separados por divisores verticales, todos caption:
etiqueta muted + valor primary/tabular.

1 Modelo activo: BLACKFORGE-X (o versión real del engine)
2 ID de sesión: BF-XXXX-XXXX-XXXX
3 Perfil: <perfil>
4 Sandbox: OK / Requerido
5 Riesgo: Bajo / Medio / Alto
6 Última actualización: fecha hora

En 1360x768 pueden ocultarse los segmentos 1 y 6 (prioridad de recorte: 6, luego 1).
Los segmentos 2, 3, 4 y 5 nunca se ocultan.

======================================================================
10. RESPONSIVE — RESOLUCIONES OBJETIVO
======================================================================

Objetivo mínimo: 1360x768. Objetivo cómodo: 1680x1050.

Reglas 1680x1050 (base):
- Sidebar 240 · Columna derecha 340 · Hero dominante ~1050 con gutters.
- Todos los bloques visibles; hero sin scroll o scroll mínimo.

Reglas 1360x768 (degradación controlada, en este orden):
1. Columna derecha baja a 300 px; charts se compactan (donut 120 px).
2. Hero obtiene scroll vertical propio; métrica central SIEMPRE visible al
   abrir (above the fold); paneles D/E/F pueden quedar bajo scroll.
3. Métricas de panel superior pasan de 4 en fila a grid 2x2 si no caben.
4. Footer recorta segmentos según sección 9.
5. Nada de scroll horizontal; nada de colapsar el sidebar.

======================================================================
11. REGLAS DE CONSISTENCIA (resumen normativo)
======================================================================

- Un solo estilo de card (QFrame#card) + una variante destacada
  (QFrame#cardAccent para hero y módulos). Nada más.
- Títulos de sección SIEMPRE: h3/h2 uppercase + tracking, color primary,
  con posible prefijo de acento naranja.
- Números importantes SIEMPRE tabulares y en jerarquía h2/display.
- Glow: nivel 1 (sutil) para elementos activos; nivel 2 SOLO el gauge hero
  FORGE_INTEGRITY.
- Iconografía: un único set lineal (stroke 1.5-2 px), tamaños icon.sm/md/lg,
  coherente con el set de CRIBA (mismo lenguaje visual).
- Todos los colores, radios, espaciados y tipografías salen de
  data/theme_blackforge.json. Prohibido hardcodear valores fuera de tokens.
- Textos visibles en español, sentence case salvo títulos de sección
  (uppercase) y marca.
- Relación con CRIBA: misma calidad visual y sistemas; distinta paleta
  (naranja vs cian/violeta) y distinto tono emocional.

======================================================================
12. RELACIÓN CON EL ESTADO ACTUAL DEL REPO
======================================================================

- gui.py actual (CRIBA Current Engine) queda intacto. BLACKFORGE es un
  QStackedWidget hermano; navBlackforge hace switch y modeBadge → naranja.
- La nota "MODO BLACKFORGE NO ACTIVO" de STATE_MATRIX_CRIBA.md queda
  SUPERSEDIDA por este contrato: cuando exista la pantalla, navBlackforge
  navega a este layout (8 zonas) y modeBadge = "MODO: BLACKFORGE" con
  acento grad.brand.
- Datos reales del engine (si los hay) alimentan cada bloque; los valores de
  ejemplo de este documento (0.87, 16/16, "Bajo") son ilustrativos y NUNCA
  deben quedar hardcodeados en la implementación.
- La imagen hero (data/assets/blackforge_hero.png) es el activo icónico;
  se conserva y se reinterpreta, no se elimina ni se cambia la paleta.
