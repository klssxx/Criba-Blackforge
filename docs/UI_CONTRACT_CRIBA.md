# UI_CONTRACT_CRIBA.md
Contrato visual y estructural de CRIBA — Modo Innovación General
Versión: 1.0.0 · Fecha: 2026-07-23 · Estado: CONTRATO (no implementado aún)

Este documento es NORMATIVO. Cualquier implementación futura de la pantalla
principal de CRIBA debe cumplirlo sin desviación relevante. Complementos:
- STYLE_GUIDE_CRIBA.md   -> tokens y reglas estéticas
- WIDGET_TREE_CRIBA.md   -> mapeo PySide6 exacto
- STATE_MATRIX_CRIBA.md  -> estados visuales
- ../data/theme_criba.json -> tokens machine-readable (fuente única)

======================================================================
1. VISIÓN DE DISEÑO
======================================================================

CRIBA es un panel de innovación, no un ERP. Debe percibirse como:
herramienta de alto nivel, elegante, tecnológica, clara, ambiciosa,
seria pero inspiradora.

Lenguaje visual obligatorio:
- dark premium: fondo casi negro con tinte azul profundo;
- acentos neón contenidos: azul eléctrico, cian, violeta;
- glassmorphism ligero (cards con borde suave + glow sutil), nunca excesivo;
- texto blanco / gris frío;
- bordes redondeados coherentes (una sola escala de radios);
- iconografía lineal unificada;
- máximo 2 niveles de glow en toda la pantalla;
- densidad alta pero controlada: mucha información, cero desbordamiento.

Prohibido:
- colores cálidos dominantes, saturación excesiva;
- estética industrial o empresarial genérica;
- look web barato, tablas con apariencia de software viejo;
- mezclar más de 2 estilos de tarjeta;
- tamaños arbitrarios fuera de la escala de tokens.

======================================================================
2. ESTRUCTURA MACRO DE LA PANTALLA (5 ZONAS)
======================================================================

+--------------------------------------------------------------------+
| A SIDEBAR |  B TOP BAR                                              |
| (fijo     |---------------------------------------------------------|
|  232 px)  |  C ÁREA CENTRAL (flexible)      | D COLUMNA DERECHA     |
|           |                                 |   (300-340 px)        |
|           |---------------------------------------------------------|
|           |  E FOOTER STRIP (alto 36 px)                            |
+--------------------------------------------------------------------+

Proporciones y límites:
- A: ancho fijo 232 px (min 208 en 1360x768). Nunca colapsa ni hace scroll horizontal.
- B: alto fijo 72 px, ocupa todo el ancho a la derecha del sidebar.
- C: flexible; contiene scroll vertical PROPIO si hace falta (QScrollArea).
- D: ancho 300-340 px; en 1360x768 se fija a 300. Scroll vertical propio.
- E: alto fijo 36 px, ancho completo bajo C+D (el sidebar puede llegar al suelo).
- Prohibido scroll horizontal global en cualquier resolución objetivo.

Grid interno: gutter estándar spacing.16 entre bloques; márgenes exteriores
spacing.20; separación entre zonas C y D: spacing.20.

======================================================================
3. ZONA A — SIDEBAR IZQUIERDO
======================================================================

Orden vertical:
1. Bloque marca: logo "CRIBA" (typography.display, degradado cian→violeta)
   + subtítulo "INNOVACIÓN SIN LÍMITES" (caption, text.muted, tracking amplio).
2. Separación spacing.24.
3. 7 botones de navegación (contrato en sección 5).
4. Stretch (espacio flexible).
5. Teaser inferior BLACKFORGE: bloque visual con logo "BLACKFORGE",
   lema "PODER SIN LÍMITES", borde violeta suave, glow nivel 1.
   Clic = misma acción que botón 7.

======================================================================
4. ZONA B — TOP BAR
======================================================================

Izquierda: saludo "Hola, Innovador" (h2) + subtexto
  "Listo para transformar ideas en impacto" (caption, secondary).
Centro-derecha: indicador de sesión (punto verde color.success + "Sesión activa").
Derecha: fecha (caption uppercase), hora (h3 monoespaciada/tabular),
  icono campana de notificación (icon.md), badge opcional de modo
  ("MODO: INNOVACIÓN" / "MODO: BLACKFORGE").

======================================================================
5. LOS 7 BOTONES OBLIGATORIOS
======================================================================

Exactamente estos, en este orden. No se añaden botones de primer nivel.

| # | Texto principal          | Icono      | Texto secundario                                        | Función |
|---|--------------------------|------------|---------------------------------------------------------|---------|
| 1 | Nueva idea               | bombilla   | Inicia el flujo, pide el problema base                   | Abre captura de problema base; resetea idea activa |
| 2 | Generar                  | engranaje  | Ejecuta los 16 operadores                                | Lanza generación de ideas sobre el problema base |
| 3 | Evaluar                  | barras     | Corre medición + convergencia, ranking por value_score   | Ejecuta evaluación y refresca ranking |
| 4 | Guardar                  | disquete   | Persiste la idea seleccionada en el catálogo             | Guarda idea activa en SQLite/catálogo |
| 5 | Actualizar innovaciones  | refresh    | Fuentes generales: tendencias, tecnología, diseño        | Refresco de fuentes bajo demanda (red) |
| 6 | Historial                | reloj      | Ver ideas generadas anteriormente                        | Abre vista/diálogo de historial |
| 7 | Blackforge               | escudo     | Cambia a la pantalla especializada en ciberseguridad     | Cambia a modo BLACKFORGE (pantalla aparte) |

Anatomía del botón (todos iguales):
- fila horizontal: icono (icon.md, 20px) + columna [texto principal body-strong,
  texto secundario caption text.muted]; alto 52-56 px; radio radius.md;
  padding spacing.12; ancho completo del sidebar menos márgenes.
- El botón 7 (Blackforge) lleva SIEMPRE contenedor destacado: borde
  color.accent.violet al 40%, fondo bg.card, para señalar cambio de modo.

Estados (aplican a los 7; detalle QSS en STYLE_GUIDE):
- normal:     fondo transparente, texto primary, icono secondary.
- hover:      fondo bg.card.hover, icono accent.cyan.
- activo:     fondo bg.card, barra izquierda 3px accent.cyan, glow nivel 1,
              texto primary, icono accent.cyan.
- disabled:   opacidad 40%, sin hover, cursor normal.
- ejecutando: icono sustituido por spinner (o icono girando), barra izquierda
              accent.blue animada, texto secundario cambia a mensaje de progreso
              (p.ej. "Ejecutando operadores 9/16..."). Botón no clicable.
- completado: flash breve (<1.2 s) de barra izquierda color.success + check;
              vuelve a normal/activo.
- error:      barra izquierda color.error, texto secundario = motivo corto;
              persiste hasta nueva acción o dismiss.

======================================================================
6. ZONA C — ÁREA CENTRAL (4 BLOQUES, orden vertical)
======================================================================

6.1 MOTOR DE INNOVACIÓN (pipeline)
- Card ancho completo. Título de sección "MOTOR DE INNOVACIÓN" (h2 uppercase)
  + descripción caption: "Convierte problemas en oportunidades. Genera, evalúa
  y prioriza ideas con impacto real."
- Pipeline horizontal de 5 etapas conectadas por flechas/conectores:
  1 Problema base — "Define el reto central a resolver"
  2 Generar       — "16 operadores activos"
  3 Evaluar       — "value_score + convergencia"
  4 Guardar       — "Guardar en catálogo"
  5 Evolucionar   — "Itera y mejora continuamente"
- Cada etapa: icono (icon.lg) en medallón circular, título (h3),
  microdescripción (caption, muted), estado visual:
  pendiente (borde soft, icono muted) / activa (borde accent.cyan + glow 1)
  / completada (borde success, check pequeño) / error (borde error).
- Conector entre etapas: línea 2px border.soft; se tiñe accent.cyan cuando
  la etapa origen está completada.

6.2 IDEA ACTIVA
- Card grande de 2 columnas.
- Columna izquierda (flexible):
  * cabecera: "IDEA ACTIVA" (h3 uppercase, accent.cyan) + chip de estado
    ("En evaluación" / "Candidata" / "Guardada"...);
  * título de la idea (h1, primary, hasta 2 líneas con elipsis);
  * problema base / resumen (body, secondary, hasta 3 líneas);
  * fila de 4 métricas (número destacado h2 + etiqueta caption):
    Operadores activos (16/16) · Ideas generadas · Convergencia % ·
    Mejor value_score.
- Columna derecha (fija ~180 px): gauge circular de value_score:
  arco degradado violeta→cian, valor central (display, p.ej. "0.87"),
  etiqueta "VALUE_SCORE" (caption) y CTA/percentil debajo
  ("Alto impacto · Top 5% del set", caption, accent.violet). Glow nivel 2
  (este es el ÚNICO elemento con glow máximo de la pantalla).

6.3 RANKING DE IDEAS
- Card ancho completo con pestañas: Ranking de Ideas (default) / Top ideas /
  En evaluación / Exploración.
- Tabla de 6 columnas: # · Idea · value_score · Convergencia · Impacto · Estado.
  * #: numeral destacado (h3, accent.cyan para top 3, muted resto);
  * Idea: texto body primary, elipsis a 1 línea, tooltip con texto completo;
  * value_score: número tabular + microbarra horizontal proporcional
    (chart.2 violeta);
  * Convergencia: porcentaje + microbarra (chart.1 cian);
  * Impacto: chip textual (Muy alto / Alto / Medio alto / Medio / Bajo);
  * Estado: chip (En evaluación=accent.blue, Candidata=accent.violet,
    Exploración=muted, Guardada=success).
- Filas: alto 44 px, zebra sutil (bg.card vs bg.card +2% luz), hover
  bg.card.hover, selección con barra izquierda accent.cyan.
- Pie del card: enlace "Ver todas las ideas ->" (accent.cyan, hover subrayado).
- Muestra 5 filas por defecto; más filas = scroll interno del card.

6.4 BLOQUE TEASER BLACKFORGE
- Card ancho completo, separado visualmente (borde superior degradado
  violeta→rosa o borde soft violeta).
- Cabecera: "BLACKFORGE | MÓDULO ESPECIALIZADO EN CIBERSEGURIDAD" (h3)
  + descripción caption + botón primario "Ir a Blackforge ->"
  (fondo degradado azul→violeta).
- Fila de 5 features (icono lineal + título caption-strong + microdescripción):
  Reconocimiento · Vectores · Simulación · Contramedidas · Laboratorio.
- Este bloque NO ejecuta funcionalidad Blackforge en esta pantalla: es teaser
  y CTA de cambio de modo. En esta fase el modo Blackforge NO se implementa.

======================================================================
7. ZONA D — COLUMNA DERECHA (4 BLOQUES, orden vertical)
======================================================================

7.1 DISTRIBUCIÓN DE VALUE_SCORE
- Card con título h3 + histograma de barras verticales (chart.2 violeta,
  barra del máximo resaltada con glow 1 y etiqueta del valor pico, p.ej. 0.87).

7.2 FUENTES DE INNOVACIÓN
- Card con 5 barras horizontales (etiqueta caption + % tabular + barra chart.1):
  Tecnología emergente · Tendencias de negocio · Investigación científica ·
  Diseño & experiencia · Comunidad & open source.
- Botón secundario ancho completo "Actualizar innovaciones" (variante ghost,
  espejo del botón 5 del sidebar; ambos comparten estado ejecutando/error).

7.3 CATEGORÍAS DE INNOVACIÓN
- Card con donut chart (colores chart.1..chart.5), cifra central
  "128 ideas totales" (h2 + caption), leyenda con punto de color + etiqueta + %:
  Ciberseguridad · Automatización · Plataformas · Datos & IA · Otros.

7.4 ACTIVIDAD RECIENTE
- Card con lista vertical de eventos: timestamp (caption tabular, muted)
  + punto de color por tipo (success=guardado, blue=evaluación, cyan=fuentes,
  error=fallo) + descripción (caption, primary, elipsis 2 líneas).
- Pie: enlace "Ver historial completo" (accent.cyan).

======================================================================
8. ZONA E — FOOTER STRIP
======================================================================

Franja única alto 36 px, fondo bg.panel, borde superior border.soft.
6 segmentos separados por divisores verticales, todos caption:
etiqueta muted + valor primary/tabular.

1 Modelo activo: CRIBA-1.8 PRO (o versión real del engine)
2 ID de sesión: CRB-XXXX-XXXX-XXXX
3 Ideas generadas: N
4 Convergencia global: NN%
5 Última actualización: fecha hora
6 Fuentes actualizadas: "Hace N min" (verde si <60 min, warning si más,
  error+texto "Sin actualizar" si nunca)

En 1360x768 pueden ocultarse los segmentos 1 y 5 (prioridad de recorte:
5, luego 1). Los segmentos 2, 3, 4 y 6 nunca se ocultan.

======================================================================
9. RESPONSIVE — RESOLUCIONES OBJETIVO
======================================================================

Objetivo mínimo: 1360x768. Objetivo cómodo: 1680x1050.

Reglas 1680x1050 (base):
- Sidebar 232 · Columna derecha 340 · Central ~1050 con gutters.
- Todos los bloques visibles; central sin scroll o scroll mínimo.

Reglas 1360x768 (degradación controlada, en este orden):
1. Columna derecha baja a 300 px; charts se compactan (donut 120 px).
2. Área central obtiene scroll vertical propio; pipeline y ranking SIEMPRE
   visibles al abrir (above the fold); teaser Blackforge puede quedar bajo scroll.
3. Métricas de Idea Activa pasan de 4 en fila a grid 2x2 si no caben.
4. Footer recorta segmentos según sección 8.
5. Nada de scroll horizontal; nada de colapsar el sidebar.

======================================================================
10. REGLAS DE CONSISTENCIA (resumen normativo)
======================================================================

- Un solo estilo de card (QFrame#card) + una variante destacada
  (QFrame#cardAccent para Idea Activa y teaser Blackforge). Nada más.
- Títulos de sección SIEMPRE: h3/h2 uppercase + tracking, color primary,
  con posible prefijo de acento cian.
- Números importantes SIEMPRE tabulares y en jerarquía h2/display.
- Glow: nivel 1 (sutil) para elementos activos; nivel 2 SOLO el gauge.
- Iconografía: un único set lineal (stroke 1.5-2 px), tamaños icon.sm/md/lg.
- Todos los colores, radios, espaciados y tipografías salen de
  data/theme_criba.json. Prohibido hardcodear valores fuera de tokens.
- Textos visibles en español, sentence case salvo títulos de sección
  (uppercase) y marca.

======================================================================
11. RELACIÓN CON EL ESTADO ACTUAL DEL REPO
======================================================================

- gui.py actual (CRIBA Current Engine, pipeline 5 pasos Entender→Decidir)
  queda como implementación vigente y NO se rompe en esta fase.
- La nota "PRÓXIMA ACCIÓN" de HANDOFF.md (pantalla única Sidebar 230 /
  pipeline 3 pasos Cartografiar-Romper-Divergir) queda SUPERSEDIDA por este
  contrato en lo visual: el layout objetivo es el descrito aquí (7 botones,
  pipeline 5 etapas). La compatibilidad CLI/API/MCP/SQLite y el contrato
  innovation v2.0.0 se mantienen intactos.
- Datos reales del engine alimentan cada bloque; los valores de ejemplo de
  este documento (0.87, 128, 78%) son ilustrativos y NUNCA deben quedar
  hardcodeados en la implementación.
