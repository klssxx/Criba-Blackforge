# STATE_MATRIX_BLACKFORGE.md
Matriz de estados visuales de BLACKFORGE — pantalla principal
Versión: 1.0.0 · Fecha: 2026-07-24 · Estado: CONTRATO (no implementado aún)

Convenciones:
- "Bloques" = los definidos en UI_CONTRACT §2-9 y WIDGET_TREE.
- Cada estado define: qué bloque cambia, qué texto aparece, qué botones se
  bloquean, qué se resalta. Nada de "mostrar spinner" a secas.
- Los NavButton usan NavButton.set_state() (WIDGET_TREE §2.9).

Estados obligatorios (tarea §13): modo resumen · sin sesión activa · sesión
operativa · simulación ejecutándose · laboratorio listo · revisión manual
requerida · autorización faltante · sandbox no disponible · sin alertas ·
alerta crítica · vuelta a CRIBA.

======================================================================
S1. MODO RESUMEN (estado base al entrar a BLACKFORGE)
======================================================================
Cambia:
- Top bar: greetingSub = "Resumen del laboratorio Blackforge".
- heroPanel: heroStatus chip kind=operativa "Operativa"; forgeGauge con
  último score conocido (o 0.00 si nunca).
- metricCard: métricas con datos reales del engine (o "—" si no hay).
- compositionCard/alertsCard: contenido real o estados vacíos.
- Footer: fsModelo "BLACKFORGE-X", fsSandbox "OK", fsRiesgo "Bajo".
Botones: todos habilitados; navResumen activo (barra naranja).
Resalta: heroPanel (glow 2 solo en gauge). Sin llamadas a la acción forzadas.

======================================================================
S2. SIN SESIÓN ACTIVA (arranque frío, sin laboratorio cargado)
======================================================================
Cambia:
- Top bar: sandboxBadge punto muted + "Sin sesión"; greetingSub =
  "Inicia una sesión de laboratorio para empezar".
- heroPanel: estado vacío — icono muted (icon.lg) + texto "Sin sesión de
  forja" (h3) + "Pulsa Resumen o un módulo para iniciar" (caption); gauge
  oculto o en 0.00 con etiqueta "Pendiente".
- heroPipeline: las 4 etapas en state=pending.
- metricCard: "—" en todas las métricas; sessionStatusChip oculto.
- compositionCard/alertsCard: placeholder muted; alertsCard "Sin alarmas".
- Footer: fsSesion "—", fsSandbox "Requerido", fsRiesgo "—".
Botones: Reconocimiento, Vectores, Simulación, Contramedidas, Laboratorio,
  Historial, Volver a CRIBA → habilitados. (No hay sesión que mutar.)
Resalta: navResumen con pulso de glow nivel 1 (única llamada a la acción).

======================================================================
S3. SESIÓN OPERATIVA (laboratorio activo y estable)
======================================================================
Cambia:
- Top bar: sandboxBadge punto success + "Sandbox OK".
- heroPanel: heroStatus chip kind=operativa "Operativa"; forgeGauge con
  score real; heroPipeline etapa "Reconocer" state=done, resto pending.
- metricCard: sessionStatusChip kind=operativa "Operativa"; métricas reales.
- alertsCard: "Sin alarmas · sandbox estable".
- Footer: fsSandbox "OK", fsRiesgo "Bajo".
Botones: todos habilitados. Resalta: gauge (glow 2, siempre) + heroPipeline.

======================================================================
S4. SIMULACIÓN EJECUTÁNDOSE (motor de simulación en curso)
======================================================================
Cambia:
- navSimulacion: state=running, subtítulo → "Simulando vectores N/16..."
  (actualizado por señal de progreso).
- heroPanel: etapa "Simular" state=active con spinner en el medallón;
  heroStatus chip kind=simulacion "En simulación".
- metricCard: métrica Coverage se actualiza en vivo "NN%"; candidatos
  incrementa si el engine emite parciales.
- Top bar: sandboxBadge sin cambio (sandbox sigue OK).
- alertsCard: entrada "Simulación en curso (sandbox)" con punto orange.
Botones bloqueados: Reconocimiento, Vectores, Simulación, Contramedidas,
  Laboratorio (los que mutan estado). Historial y Volver a CRIBA permitidos.
Resalta: solo etapa "Simular". GUI nunca congelada (QThread).
Al terminar: navSimulacion state=done (flash success <1.2 s), etapa
"Simular" state=done, transición a S3/S5 con coverage actualizado.

======================================================================
S5. LABORATORIO LISTO (experimentos preparados, listos para ejecutar)
======================================================================
Cambia:
- heroPanel: heroStatus chip kind=sandbox "Laboratorio listo"; etapa
  "Contrarrestar" state=active.
- metricCard: sessionStatusChip kind=sandbox "Listo"; ideas técnicas y
  candidatos con valores reales; gauge con score real.
- modulesCard: tarjeta "Laboratorio" resaltada (borde accent.orange).
- alertsCard: "Sin alarmas" o guardrails informativos.
- Footer: fsRiesgo "Bajo"/"Medio" según readiness.
Botones: todos habilitados. Resalta: modulesCard "Laboratorio" + gauge.

======================================================================
S6. REVISIÓN MANUAL REQUERIDA
======================================================================
Cambia:
- heroPanel: heroStatus chip kind=revision "Revisión requerida".
- metricCard: sessionStatusChip kind=revision "Revisión manual".
- alertsCard: entrada warning "Revisión manual requerida en <módulo>"
  (punto warning) + badge "REVIEW".
- Banner inline superior del área central (no popup): fondo warning al 12%,
  borde warning, icono + "Revisión manual requerida" + botón ghost
  "Revisar" (abre el módulo implicado).
- Footer: fsRiesgo "Medio".
Botones: el módulo implicado habilitado y resaltado; Volver a CRIBA libre.
Resto según corresponda. Ningún dato se persiste hasta la revisión.

======================================================================
S7. AUTORIZACIÓN FALTANTE
======================================================================
Cambia:
- heroPanel: heroStatus chip kind=auth "Autorización requerida".
- topbar sandboxBadge: punto warning + "Autorización requerida".
- metricCard: sessionStatusChip kind=auth "Auth requerida"; métricas
  visibles pero marcadas como "pendientes de auth".
- alertsCard: entrada warning "Autorización requerida para <acción>"
  + badge "AUTH".
- Banner inline: fondo warning al 12%, borde warning, botón ghost
  "Solicitar autorización" + botón ghost "Detalles".
- Footer: fsSandbox "Requerido".
Botones: acciones que requieren auth → disabled hasta obtenerla (p.ej.
  Simulación/Contramedidas). Reconocimiento (solo superficie simulada),
  Resumen, Historial, Volver a CRIBA → habilitados.

======================================================================
S8. SANDBOX NO DISPONIBLE
======================================================================
Cambia:
- heroPanel: heroStatus chip kind=error "Sandbox no disponible"; gauge
  oculto o 0.00 con etiqueta "Sandbox OFF".
- topbar sandboxBadge: punto error + "Sandbox no disponible".
- metricCard: sessionStatusChip kind=error "Sandbox OFF"; métricas "—"
  (no se ejecuta nada fuera de sandbox).
- alertsCard: entrada error "Sandbox obligatorio no disponible" + badge "BLOCK".
- Banner inline: fondo error al 12%, borde error, icono alerta +
  "Sandbox obligatorio: la simulación no puede ejecutarse" + botón ghost
  "Reintentar sandbox" + botón ghost "Detalles".
- Footer: fsSandbox "Requerido", fsRiesgo "Alto" (no se puede aislar).
Botones: Simulación, Contramedidas, Laboratorio → disabled (requieren sandbox).
  Reconocimiento (modo superficie), Resumen, Historial, Volver a CRIBA → ON.
Ningún dato parcial se persiste; el estado de datos vuelve al previo.

======================================================================
S9. SIN ALERTAS (estado limpio)
======================================================================
Cambia:
- alertsCard: estado vacío — icono success (icon.lg) + "Sin alarmas"
  (h3) + "Sandbox estable · guardrails OK" (caption). Sin badges.
- heroPanel: heroStatus chip kind=ok "Operativa".
- topbar sandboxBadge: punto success "Sandbox OK".
- Footer: fsRiesgo "Bajo".
Botones: sin bloqueos. Es el estado deseado por defecto tras S3.

======================================================================
S10. ALERTA CRÍTICA (riesgo alto / guardrail violado)
======================================================================
Cambia:
- alertsCard: entrada error "Alerta crítica: <motivo corto>" (punto error)
  + badge "CRÍTICO" en color.error; alertas previas se mantienen debajo.
- heroPanel: heroStatus chip kind=error "Alerta crítica"; glow del panel
  nivel 1 (naranja) parpadea suave (≤200 ms, no permanente decorativo).
- topbar sandboxBadge: punto error + "Revisar".
- Banner inline superior: fondo error al 14%, borde error, icono alerta +
  mensaje + botón ghost "Mitigar" (abre Contramedidas) + botón ghost "Detalles".
- Footer: fsRiesgo "Alto".
Botones: Contramedidas habilitado y resaltado; el resto según criticidad.
Tras mitigar: transición a S9 (sin alertas) o S6 (revisión) según corresponda.

======================================================================
S11. VUELTA A CRIBA (cierre de modo Blackforge)
======================================================================
Cambia:
- El control accesible "Volver a CRIBA" cierra la ventana/proceso BLACKFORGE.
- `QProcess.finished` restaura y activa la ventana CRIBA.
- Si BLACKFORGE falla o termina de otra forma, CRIBA también se restaura.
- No se construye una shell ni se interpolan datos de sesión en argumentos.
- La persistencia compartida permite volver a abrir una sesión posteriormente.
Botones: en CRIBA, navBlackforge queda disponible para ejecutar BLACKFORGE otra vez.

======================================================================
MATRIZ RESUMEN (botón × estado)
======================================================================
          | S1 | S2 | S3 | S4 | S5 | S6 | S7 | S8 | S9 | S10| S11
----------|----|----|----|----|----|----|----|----|----|----|----
Resumen   | ON*| ON | ON | ON | ON | ON | ON | ON | ON | ON |  - (en CRIBA)
Reconoc.  | ON | ON | ON | OFF| ON | ON | ON | ON | ON | ON |  -
Vectores  | ON | ON | ON | OFF| ON | ON | ON | ON | ON | ON |  -
Simulac.  | ON | ON | ON |RUN | ON | ON |OFF†|OFF‡| ON | ON |  -
Contramed.| ON | ON | ON | OFF| ON | ON |OFF†|OFF‡| ON | ON*|  -
Laborat.  | ON | ON | ON | OFF| ON*| ON | ON |OFF‡| ON | ON |  -
Historial | ON | ON | ON | ON | ON | ON | ON | ON | ON | ON |  -
VolverCR. | ON | ON | ON | ON | ON | ON | ON | ON | ON | ON | DONE
ON*  = habilitado y resaltado (siguiente acción sugerida).
OFF† = disabled hasta autorización.
OFF‡ = disabled hasta sandbox disponible.
RUN  = state=running (bloqueado, con progreso).
DONE = navVolverCriba flash success al cambiar de modo.
"ON" en S11 = BLACKFORGE terminó y CRIBA vuelve a estar visible.
