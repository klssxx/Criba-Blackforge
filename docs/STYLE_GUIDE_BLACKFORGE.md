# STYLE_GUIDE_BLACKFORGE.md
Guía de estilo visual de BLACKFORGE — tokens, tipografía, componentes y QSS
Versión: 1.0.0 · Fecha: 2026-07-24 · Estado: CONTRATO (no implementado aún)

Fuente única machine-readable: ../data/theme_blackforge.json
Este documento explica y norma el uso de esos tokens. Si divergen, manda el JSON.
Hermano de STYLE_GUIDE_CRIBA.md: mismos sistemas, firma cromatica naranja.

======================================================================
1. PALETA — TOKENS DE COLOR
======================================================================

Fondos
| Token                | Valor    | Uso |
|----------------------|----------|-----|
| color.bg.app         | #050607  | fondo global de la ventana (negro carbón cálido) |
| color.bg.panel       | #0D1012  | sidebar, top bar, footer strip |
| color.bg.card        | #1D1712  | cards estándar |
| color.bg.card.hover  | #271F17  | hover de cards, filas y botones de nav |
| color.bg.hero        | #0A0806  | base del hero / pozo de la imagen |
| color.bg.inset       | #120E0A  | pozos internos: pistas de barras, inputs, code/json |

Bordes
| color.border.soft    | #3A2E22  | borde por defecto de cards y divisores |
| color.border.active  | #FF6A00  | borde de elemento activo/foco (naranja) |

Texto
| color.text.primary   | #FBF3EA  | títulos, valores, texto principal (blanco cálido) |
| color.text.secondary | #C9B8A6  | descripciones, subtextos (gris arena) |
| color.text.muted     | #8A7866  | captions, etiquetas, metadatos |

Acentos (firma cromática BF)
| color.accent.orange      | #FF6A00  | elemento activo, enlaces, highlights, marca |
| color.accent.orange.dim  | #C2410C  | variantes, bordes destacados al 40% |
| color.accent.orange.glow | #FF8318  | glow naranja, bordes de glow |

Semánticos
| color.success | #21D879  | sesión activa, sandbox OK, guardado |
| color.warning | #F5A623  | revisión requerida, degradación |
| color.error   | #FF573D  | fallos, riesgo alto, autorización faltante |

Charts (orden fijo; no improvisar colores en gráficos)
| color.chart.orange | #FF6A00 | naranja — superficie de ataque, vectores |
| color.chart.neutral| #5C4B39 | gris carbón — residual, "Otros" |
| color.chart.green | #21D879 | verde — contramedidas OK, estados sanos |
| color.chart.red   | #FF573D | rojo — riesgo alto, alertas |

Degradados canónicos (solo estos 3):
- grad.brand:  naranja #FF6A00 → ámbar #FFA126 (logo BF, gauge hero, activos)
- grad.cta:    naranja #FF6A00 → rojo #FF5A1A (botones primarios)
- grad.herald: naranja #FF8318 → hueso #FFD5A0 (overlays del hero)

======================================================================
2. RADIOS, ESPACIADO, SOMBRAS, ICONOS
======================================================================

Radios (idénticos a CRIBA para coherencia de hermanos)
| radio.sm | 6 px  | chips, badges, microbarras |
| radio.md | 10 px | botones, inputs, filas destacadas |
| radio.lg | 14 px | cards |
| radio.xl | 20 px | hero panel, gauge container, módulos |

Espaciado (escala única; prohibidos valores fuera de escala)
spacing.4 / 8 / 12 / 16 / 20 / 24 / 32

Sombras y glow (máximo 2 niveles de glow en pantalla)
| shadow.sm   | 0 1px 3px rgba(0,0,0,0.55)                    | cards en reposo |
| shadow.md   | 0 4px 16px rgba(0,0,0,0.65)                   | popovers, diálogos |
| shadow.glow | 0 0 14px rgba(255,122,26,0.32) (nivel 1)      | elemento activo/hover destacado |
|             | 0 0 26px rgba(255,154,61,0.40) (nivel 2)      | SOLO gauge FORGE_INTEGRITY / hero activo |

Nota Qt: QSS no soporta box-shadow. El glow se implementa con
QGraphicsDropShadowEffect (blurRadius 14/26, color con alpha) o con bordes
de 1px en color acento + fondo ligeramente iluminado. Contrato: el efecto
percibido debe respetar los 2 niveles; el mecanismo es libre.

Iconos
| icon.size.sm | 16 px | chips, footer, actividad |
| icon.size.md | 20 px | botones de nav, top bar |
| icon.size.lg | 28 px | hero, módulos, etapas del pipeline |
Set único lineal (stroke 1.5-2 px), mismo lenguaje visual que el set de CRIBA.

======================================================================
3. TIPOGRAFÍA
======================================================================

Familia: "Inter" si está empaquetada; fallback "Segoe UI Variable",
"Segoe UI", sans-serif. Números SIEMPRE con cifras tabulares
(font-feature "tnum" o fuente monoespaciada solo para hora/IDs).

| Token               | Tamaño | Peso | Uso |
|---------------------|--------|------|-----|
| typography.display  | 28 px  | 800  | logo BLACKFORGE, valor del gauge hero |
| typography.h1       | 22 px  | 700  | título de idea/sesión activa |
| typography.h2       | 17 px  | 700  | títulos de sección, métricas grandes |
| typography.h3       | 14 px  | 600  | subtítulos, cabeceras de card derecha |
| typography.body     | 13 px  | 400  | texto general, celdas de tabla |
| typography.caption  | 11 px  | 500  | etiquetas, microdescripciones, footer |

Reglas:
- Títulos de sección: uppercase + letter-spacing 1-1.5 px.
- Nunca más de 3 tamaños distintos dentro de un mismo card.
- Line-height: 1.35 body, 1.2 títulos.

======================================================================
4. COMPONENTES CANÓNICOS
======================================================================

4.1 Card (QFrame#card)
- fondo bg.card, borde 1px border.soft, radio radio.lg, padding spacing.16;
- cabecera: título h3 uppercase + acción opcional a la derecha;
- hover (solo cards interactivas): bg.card.hover + borde border.soft aclarado.

4.2 Card acentuada (QFrame#cardAccent)
- igual que card + radio.xl + borde superior 2px degradado (grad.brand para
  hero y módulos). Únicos usos permitidos.

4.3 Botón primario (QPushButton#primary)
- fondo grad.cta, texto primary, radio.md, alto 38 px, padding h spacing.16;
- hover: +8% luz; pressed: -8% luz; disabled: gris #2A221A texto muted;
- ejecutando: texto → "Ejecutando..." + spinner, no clicable.

4.4 Botón ghost/secundario (QPushButton#ghost)
- fondo transparente, borde 1px border.soft, texto secondary;
- hover: borde accent.orange + texto primary; disabled: opacidad 40%.

4.5 Botón de navegación sidebar (QPushButton#navbtn, checkable)
- contrato de estados en UI_CONTRACT_BLACKFORGE.md §7;
- checked = activo: fondo bg.card + barra izquierda 3px accent.orange.

4.6 Chip de estado (QLabel#chip + propiedad dinámica "kind")
- radio.sm, padding 2x8, caption-strong, fondo = color al 15% alpha,
  texto = color pleno:
  kind=operativa → success · kind=analisis → accent.orange ·
  kind=simulacion → accent.orange · kind=sandbox → accent.orange ·
  kind=revision → warning · kind=auth → warning · kind=riesgo → error ·
  kind=ok → success · kind=error → error.

4.7 Barra de progreso / microbarra (QProgressBar delgada, 6 px)
- pista bg.inset radio.sm; chunk color.chart.orange radio.sm;
- sin texto interno; el % va como QLabel tabular al lado.

4.8 Gauge circular FORGE_INTEGRITY (widget custom, QPainter)
- diámetro 150-170 px, arco 270°, grosor 10 px, pista bg.inset,
  progreso grad.brand con cap redondeado, glow nivel 2;
- centro: valor display + "FORGE_INTEGRITY" caption + subtítulo percentil.
  ÚNICO elemento con glow máximo de la pantalla.

4.9 Donut / barras de composición (widget custom QPainter)
- grosor de anillo 18-22 px, colores chart.orange/neutral/green/red en orden
  de magnitud; centro con total (h2) + etiqueta (caption).

4.10 Lista de alertas/guardrails (fila custom)
- [icono semántico] [texto caption primary, máx 2 líneas] [badge severidad];
  separador inferior border.soft al 50%. Estado vacío: "Sin alarmas".

4.11 Tabla/ranking (QTableView estilizado, si se usa en Historial)
- header: fondo transparente, caption uppercase muted, sin gridlines verticales;
- filas 44 px, zebra bg.card/bg.card+2%, hover bg.card.hover,
  selección barra izquierda 3px accent.orange (delegate).

4.12 Hero panel (QFrame#heroPanel)
- fondo bg.hero + QPixmap de data/assets/blackforge_hero.png escalado
  (KeepAspectRatioByExpanding, alineado centro); overlay QGraphicsOpacity/
  gradiente grad.herald para legibilidad de texto; gauge FORGE_INTEGRITY
  anclado; ribbon de mini-pipeline inferior.

======================================================================
5. REGLAS DE COMPOSICIÓN
======================================================================

1. Grid: gutter spacing.16 entre cards; margen exterior spacing.20.
2. Alineación: todos los cards de una columna comparten borde izquierdo/derecho.
3. Jerarquía de brillo: fondo < panel < card < elemento activo < gauge hero.
4. Números clave siempre destacados (h2/display + tabular).
5. Un card = un propósito. No mezclar chart + tabla + formulario en un card.
6. Estados vacíos SIEMPRE diseñados (icono muted + frase corta + CTA),
   nunca un card en blanco.
7. Contraste mínimo AA: body sobre bg.card ≥ 4.5:1 (los tokens lo cumplen).
8. Animaciones: 150-200 ms ease-out para hover/estado; sin animaciones
   decorativas permanentes salvo spinner de ejecución.
9. Hero SIEMPRE visible y dominante; la imagen de la criba nunca se oculta
   ni se reemplaza por otra paleta.

======================================================================
6. RELACIÓN CROMÁTICA CON CRIBA (hermanos, no gemelos)
======================================================================

- Mismos radios, spacing, tipografía, densidad y disciplina QSS global.
- CRIBA usa cian/violeta (grad.brand azul→violeta). BLACKFORGE usa
  naranja (grad.brand naranja→ámbar). Esa es la única diferencia de firma.
- chip/active/border.active en CRIBA = cian; en BLACKFORGE = naranja.
- El glow en CRIBA es cian/violeta; en BLACKFORGE es naranja.
- Ambos comparten la misma familia de calidad visual y el mismo set de iconos.

======================================================================
7. NO PERMITIDO (lista de bloqueo)
======================================================================

- Colores fuera de tokens; azul/cian/violeta dominantes; glow en >2 niveles.
- Bordes de 3+ estilos, radios fuera de escala, sombras duras negras 100%.
- Tipografías serif/decorativas; texto gris oscuro ilegible.
- Tablas con gridlines completas estilo Excel; headers con fondo sólido claro.
- Iconos emoji de colores mezclados con set lineal.
- Inline setStyleSheet() por widget en la implementación futura: todo por
  QSS global generado desde tokens + objectName/propiedades dinámicas.
- Mostrar contenido ofensivo no autorizado / malware / instrucciones de
  explotación real / targets externos reales: la UI es simulación + sandbox.
- Eliminar o recolorir la imagen hero de la criba (es activo icónico fijo).
