# STATE_MATRIX_CRIBA.md
Matriz de estados visuales de CRIBA — pantalla principal
Versión: 1.0.0 · Fecha: 2026-07-23 · Estado: CONTRATO (no implementado aún)

Convenciones:
- "Bloques" = los definidos en UI_CONTRACT §6-8 y WIDGET_TREE.
- Cada estado define: qué bloque cambia, qué texto aparece, qué botones se
  bloquean, qué se resalta. Nada de "mostrar spinner" a secas.
- Los NavButton usan NavButton.set_state() (WIDGET_TREE §2.14).

======================================================================
S1. SIN SESIÓN (arranque frío, sin idea activa ni catálogo cargado)
======================================================================
Cambia:
- Top bar: sessionBadge punto muted + "Sin sesión"; greetingSub =
  "Crea una nueva idea para empezar".
- ideaActivaCard: estado vacío — icono bombilla muted (icon.lg), texto
  "Ninguna idea activa" (h3) + "Pulsa Nueva idea para definir el problema
  base" (caption) + botón #primary "Nueva idea" centrado. Gauge oculto.
- Pipeline: las 5 etapas en state=pending.
- rankingCard: estado vacío — "Aún no hay ideas evaluadas" + caption
  "El ranking aparecerá tras la primera evaluación".
- distribCard/categoriasCard: estado vacío con placeholder muted.
- actividadCard: "Sin actividad todavía".
- Footer: fsSesion "—", fsIdeas "0", fsConvergencia "—".
Botones: Generar, Evaluar, Guardar → disabled. Nueva idea, Actualizar
innovaciones, Historial, Blackforge → habilitados.
Resalta: navNuevaIdea con pulso de glow nivel 1 (única llamada a la acción).

======================================================================
S2. NUEVA IDEA SIN EVALUAR (problema base capturado, sin generar)
======================================================================
Cambia:
- Pipeline: stageProblema state=done (check), stageGenerar state=active.
- ideaActivaCard: título = problema base; chip estado kind=exploracion
  "Sin evaluar"; métricas: Operadores "0/16", Ideas "0", Convergencia "—",
  Mejor score "—". Gauge visible pero en 0.00 con etiqueta "Pendiente".
- rankingCard: mantiene contenido anterior si lo hay; si no, vacío S1.
- actividadCard: nueva entrada "Problema base definido: <resumen 60c>".
Botones: Generar habilitado y resaltado (borde accent.cyan); Evaluar y
Guardar disabled; resto normal.
Resalta: stageGenerar (glow 1) + navGenerar.

======================================================================
S3. GENERANDO (16 operadores en ejecución)
======================================================================
Cambia:
- navGenerar: state=running, subtítulo → "Ejecutando operadores N/16..."
  (actualizado por señal de progreso).
- Pipeline: stageGenerar state=active con spinner en el medallón.
- ideaActivaCard: métrica Operadores se actualiza en vivo "N/16";
  métrica Ideas incrementa si el engine emite parciales.
- Top bar: modeBadge sin cambio; sessionBadge sin cambio.
- actividadCard: entrada "Generación iniciada (16 operadores)".
Botones bloqueados: Nueva idea, Generar, Evaluar, Guardar, Actualizar
innovaciones (todos los que mutan estado). Historial y Blackforge permitidos.
Resalta: solo stageGenerar. GUI nunca congelada (QThread).
Al terminar: navGenerar state=done (flash success <1.2 s), stageGenerar
state=done, transición automática a S4-previo (Evaluar habilitado+resaltado).

======================================================================
S4. EVALUANDO (medición + convergencia en curso)
======================================================================
Cambia:
- navEvaluar: state=running, subtítulo → "Midiendo convergencia...".
- Pipeline: stageEvaluar state=active + spinner.
- rankingCard: overlay sutil (opacidad 60%) + caption centrada
  "Evaluando N ideas..."; la tabla previa sigue visible debajo.
- Gauge: anima hacia el nuevo mejor score al recibir resultado.
Botones bloqueados: los 5 mutadores (como S3).
Al terminar → S5.

======================================================================
S5. RANKING LISTO (evaluación completada)
======================================================================
Cambia:
- Pipeline: stageEvaluar state=done; stageGuardar state=active.
- ideaActivaCard: idea #1 del ranking pasa a idea activa; chip
  kind=eval "En evaluación"; métricas y gauge con valores reales;
  percentil calculado ("Top N% del set").
- rankingCard: tabla poblada, fila #1 con barra izquierda accent.cyan;
  pestaña activa "Ranking de Ideas".
- distribCard: histograma actualizado, bin del máximo resaltado.
- categoriasCard: donut actualizado.
- actividadCard: entrada "Idea evaluada: <título 60c> (score 0.NN)".
- Footer: fsIdeas y fsConvergencia actualizados; fsUltima = ahora.
Botones: todos habilitados; Guardar resaltado (borde accent.cyan).
Resalta: gauge (glow 2, siempre) + fila #1 del ranking.

======================================================================
S6. GUARDADO COMPLETADO
======================================================================
Cambia:
- navGuardar: state=done → flash success + check 1.2 s, vuelve a normal.
- ideaActivaCard: chip pasa a kind=guardada "Guardada en catálogo".
- Pipeline: stageGuardar state=done; stageEvolucionar state=active.
- rankingCard: fila guardada muestra chip estado "Guardada".
- actividadCard: entrada "Idea guardada en catálogo: <título 60c>".
- Toast no modal (2.5 s, esquina inferior derecha del área central):
  "Idea guardada" + icono success.
Botones: Guardar disabled hasta que cambie la selección (evita duplicados);
resto normal.

======================================================================
S7. HISTORIAL CARGADO
======================================================================
Cambia:
- navHistorial: state=active mientras la vista/diálogo esté abierta.
- Se abre QDialog #card grande (80% de la ventana) con lista de ideas
  pasadas: fecha, título, score, estado, botón "Cargar como idea activa".
- La pantalla principal queda debajo sin cambios; al cargar una idea del
  historial → transición a S5 con esa idea.
Botones: durante el diálogo, la pantalla de fondo no recibe input (modal).

======================================================================
S8. SIN FUENTES ACTUALIZADAS (nunca refrescadas o >24 h)
======================================================================
Cambia:
- Footer fsFuentes: freshness=stale → valor "Sin actualizar" en color.error
  (o "Hace N h" en color.warning si 1-24 h).
- fuentesCard: banda superior fina warning + caption "Fuentes desactualizadas.
  Pulsa Actualizar innovaciones."; barras en opacidad 70%.
- actualizarFuentesBtn: borde warning (llamada de atención suave).
Botones: sin bloqueos. Al pulsar Actualizar → navActualizar y
actualizarFuentesBtn en running ("Actualizando fuentes..."), fuentesCard
con overlay 60%; al terminar: freshness=ok, entrada en actividad
"Nuevas tendencias incorporadas", flash done.

======================================================================
S9. ERROR DE OPERACIÓN (fallo en generar/evaluar/guardar/actualizar)
======================================================================
Cambia:
- NavButton implicado: state=error, subtítulo = motivo corto
  (p.ej. "Error: motor no disponible"). Persiste hasta nueva acción.
- Etapa de pipeline implicada: state=error (borde color.error, icono alerta).
- Banner inline en la parte superior del área central (no popup):
  fondo error al 12%, borde error, icono alerta + mensaje + botón ghost
  "Reintentar" + botón ghost "Detalles" (muestra stderr/log en diálogo).
- actividadCard: entrada con punto error "Fallo en <operación>: <motivo 60c>".
- Footer: sin cambios (no se corrompe con datos parciales).
Botones: se desbloquean todos los bloqueados por la operación fallida.
Ningún dato parcial se persiste; el estado de datos vuelve al previo.

======================================================================
S10. MODO BLACKFORGE NO ACTIVO (estado permanente de esta fase)
======================================================================
Cambia:
- blackforgeTeaserCard y navBlackforge visibles y clicables.
- Al pulsar en esta fase (pantalla Blackforge aún no implementada):
  diálogo informativo #card: título "BLACKFORGE" + texto "El módulo de
  ciberseguridad se activará en una fase posterior." + botón "Entendido".
  NO se navega a una pantalla vacía ni se rompe nada.
- modeBadge permanece "MODO: INNOVACIÓN".
Cuando exista: navBlackforge hace switch de QStackedWidget raíz y
modeBadge → "MODO: BLACKFORGE" con acento grad.blackforge.

======================================================================
MATRIZ RESUMEN (botón × estado)
======================================================================
        |  S1  |  S2  |  S3  |  S4  |  S5  |  S6  |  S8run |  S9
--------|------|------|------|------|------|------|--------|------
Nueva   |  ON* |  ON  | OFF  | OFF  |  ON  |  ON  |  ON    |  ON
Generar | OFF  |  ON* | RUN  | OFF  |  ON  |  ON  |  ON    |  ON
Evaluar | OFF  | OFF  | OFF  | RUN  |  ON  |  ON  |  ON    |  ON
Guardar | OFF  | OFF  | OFF  | OFF  |  ON* | OFF† |  ON    |  ON
Actual. |  ON  |  ON  | OFF  | OFF  |  ON  |  ON  | RUN    |  ON
Histor. |  ON  |  ON  |  ON  |  ON  |  ON  |  ON  |  ON    |  ON
Blackf. |  ON  |  ON  |  ON  |  ON  |  ON  |  ON  |  ON    |  ON

ON* = habilitado y resaltado (siguiente acción sugerida).
OFF† = disabled hasta cambiar la selección de idea.
RUN = state=running (bloqueado, con progreso).
El botón implicado en S9 muestra state=error en lugar de ON hasta reintento.
