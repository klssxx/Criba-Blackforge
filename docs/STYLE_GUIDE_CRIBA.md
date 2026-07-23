# STYLE_GUIDE_CRIBA.md
Guía de estilo visual de CRIBA — tokens, tipografía, componentes y QSS
Versión: 1.0.0 · Fecha: 2026-07-23 · Estado: CONTRATO (no implementado aún)

Fuente única machine-readable: ../data/theme_criba.json
Este documento explica y norma el uso de esos tokens. Si divergen, manda el JSON.

======================================================================
1. PALETA — TOKENS DE COLOR
======================================================================

Fondos
| Token                | Valor    | Uso |
|----------------------|----------|-----|
| color.bg.app         | #070D1A  | fondo global de la ventana (casi negro, tinte azul) |
| color.bg.panel       | #0B1424  | sidebar, top bar, footer strip |
| color.bg.card        | #101D33  | cards estándar |
| color.bg.card.hover  | #16263F  | hover de cards, filas y botones de nav |
| color.bg.inset       | #0A1526  | pozos internos: pistas de barras, inputs, code/json |

Bordes
| color.border.soft    | #1E3355  | borde por defecto de cards y divisores |
| color.border.active  | #22D3EE  | borde de elemento activo/foco (cian) |

Texto
| color.text.primary   | #EAF2FF  | títulos, valores, texto principal |
| color.text.secondary | #9FB3D1  | descripciones, subtextos |
| color.text.muted     | #64748B  | captions, etiquetas, metadatos |

Acentos
| color.accent.blue    | #3B82F6  | acciones primarias, estado "en evaluación" |
| color.accent.cyan    | #22D3EE  | elemento activo, enlaces, highlights |
| color.accent.violet  | #8B5CF6  | value_score, marca, chips "candidata" |

Semánticos
| color.success        | #10B981  | sesión activa, guardado, fuentes frescas |
| color.warning        | #F59E0B  | fuentes viejas, degradación |
| color.error          | #EF4444  | fallos de operación |

Charts (orden fijo; no improvisar colores en gráficos)
| color.chart.1 | #22D3EE | cian — convergencia, fuentes |
| color.chart.2 | #8B5CF6 | violeta — value_score, histograma |
| color.chart.3 | #3B82F6 | azul — series secundarias |
| color.chart.4 | #EC4899 | rosa/magenta — acento Blackforge y 4ª serie |
| color.chart.5 | #64748B | gris frío — "Otros", residual |

Degradados canónicos (solo estos 3):
- grad.brand:    cian #22D3EE → violeta #8B5CF6 (logo CRIBA, gauge)
- grad.cta:      azul #3B82F6 → violeta #8B5CF6 (botones primarios)
- grad.blackforge: violeta #8B5CF6 → rosa #EC4899 (teaser/borde Blackforge)

======================================================================
2. RADIOS, ESPACIADO, SOMBRAS, ICONOS
======================================================================

Radios
| radio.sm | 6 px  | chips, badges, microbarras |
| radio.md | 10 px | botones, inputs, filas destacadas |
| radio.lg | 14 px | cards |
| radio.xl | 20 px | card Idea Activa, gauge container, teaser Blackforge |

Espaciado (escala única; prohibidos valores fuera de escala)
spacing.4 / 8 / 12 / 16 / 20 / 24 / 32

Sombras y glow (máximo 2 niveles de glow en pantalla)
| shadow.sm   | 0 1px 3px rgba(0,0,0,0.45)                    | cards en reposo |
| shadow.md   | 0 4px 16px rgba(0,0,0,0.55)                   | popovers, diálogos |
| shadow.glow | 0 0 12px rgba(34,211,238,0.28) (nivel 1)      | elemento activo/hover destacado |
|             | 0 0 24px rgba(139,92,246,0.38) (nivel 2)      | SOLO gauge value_score |

Nota Qt: QSS no soporta box-shadow. El glow se implementa con
QGraphicsDropShadowEffect (blurRadius 12/24, color con alpha) o con bordes
de 1px en color acento + fondo ligeramente iluminado. Contrato: el efecto
percibido debe respetar los 2 niveles; el mecanismo es libre.

Iconos
| icon.size.sm | 16 px | chips, footer, actividad |
| icon.size.md | 20 px | botones de nav, top bar |
| icon.size.lg | 28 px | etapas del pipeline, features Blackforge |
Set único lineal (stroke 1.5-2 px). Recomendado: SVG propios monocromos
teñidos por código, o glifos Unicode/Segoe Fluent Icons como fallback.

======================================================================
3. TIPOGRAFÍA
======================================================================

Familia: "Inter" si está empaquetada; fallback "Segoe UI Variable",
"Segoe UI", sans-serif. Números SIEMPRE con cifras tabulares
(font-feature "tnum" o fuente monoespaciada solo para hora/IDs).

| Token               | Tamaño | Peso | Uso |
|---------------------|--------|------|-----|
| typography.display  | 28 px  | 800  | logo CRIBA, valor del gauge |
| typography.h1       | 22 px  | 700  | título de idea activa |
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
  Idea Activa, grad.blackforge para teaser). Únicos usos permitidos.

4.3 Botón primario (QPushButton#primary)
- fondo grad.cta, texto primary, radio.md, alto 38 px, padding h spacing.16;
- hover: +8% luz; pressed: -8% luz; disabled: gris #24344F texto muted;
- ejecutando: texto → "Ejecutando..." + spinner, no clicable.

4.4 Botón ghost/secundario (QPushButton#ghost)
- fondo transparente, borde 1px border.soft, texto secondary;
- hover: borde accent.cyan + texto primary; disabled: opacidad 40%.

4.5 Botón de navegación sidebar (QPushButton#navbtn, checkable)
- contrato de estados en UI_CONTRACT_CRIBA.md §5;
- checked = activo: fondo bg.card + barra izquierda 3px accent.cyan.

4.6 Chip de estado (QLabel#chip + propiedad dinámica "kind")
- radio.sm, padding 2x8, caption-strong, fondo = color al 15% alpha,
  texto = color pleno:
  kind=eval → accent.blue · kind=candidata → accent.violet ·
  kind=exploracion → text.muted · kind=guardada → success ·
  kind=error → error · kind=impacto-* → escala warning/cyan/violet.

4.7 Barra de progreso / microbarra (QProgressBar delgada, 6 px)
- pista bg.inset radio.sm; chunk color de serie (chart.1/chart.2) radio.sm;
- sin texto interno; el % va como QLabel tabular al lado.

4.8 Gauge circular value_score (widget custom, QPainter)
- diámetro 150-170 px, arco 270°, grosor 10 px, pista bg.inset,
  progreso grad.brand con cap redondeado, glow nivel 2;
- centro: valor display + "VALUE_SCORE" caption + subtítulo percentil.

4.9 Tabla ranking (QTableView estilizado)
- header: fondo transparente, caption uppercase muted, sin gridlines verticales;
- filas 44 px, zebra bg.card/bg.card+2%, hover bg.card.hover,
  selección barra izquierda 3px accent.cyan (delegate), sin focus rect punteado.

4.10 Donut chart (widget custom QPainter)
- grosor de anillo 18-22 px, huecos de 2° entre segmentos, colores chart.1..5
  en orden de magnitud; centro con total (h2) + etiqueta (caption).

4.11 Item de actividad (fila custom)
- [timestamp caption tabular muted] [punto 8px color semántico] [texto caption
  primary, máx 2 líneas]; separador inferior border.soft al 50%.

======================================================================
5. REGLAS DE COMPOSICIÓN
======================================================================

1. Grid: gutter spacing.16 entre cards; margen exterior spacing.20.
2. Alineación: todos los cards de una columna comparten borde izquierdo/derecho.
3. Jerarquía de brillo: fondo < panel < card < elemento activo < gauge.
4. Números clave siempre destacados (h2/display + tabular).
5. Un card = un propósito. No mezclar chart + tabla + formulario en un card.
6. Estados vacíos SIEMPRE diseñados (icono muted + frase corta + CTA),
   nunca un card en blanco.
7. Contraste mínimo AA: body sobre bg.card ≥ 4.5:1 (los tokens lo cumplen;
   no introducir grises más oscuros que text.muted para texto informativo).
8. Animaciones: 150-200 ms ease-out para hover/estado; sin animaciones
   decorativas permanentes salvo spinner de ejecución.

======================================================================
6. NO PERMITIDO (lista de bloqueo)
======================================================================

- Colores fuera de tokens; cálidos dominantes; glow en más de 2 niveles.
- Bordes de 3+ estilos, radios fuera de escala, sombras duras negras 100%.
- Tipografías serif/decorativas; texto gris oscuro ilegible.
- Tablas con gridlines completas estilo Excel; headers con fondo sólido claro.
- Iconos emoji de colores mezclados con set lineal (elegir uno: set lineal).
- Inline setStyleSheet() por widget en la implementación futura: todo por
  QSS global generado desde tokens + objectName/propiedades dinámicas.
