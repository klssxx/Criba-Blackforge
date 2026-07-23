# CRIBA / BLACKFORGE — Debate interno de 20 rondas

## Resumen ejecutivo

- Registros trazados: **723**.
- Essential: **72**.
- Core: **180**.
- Extended: **277**.
- Research: **150**.
- Archive: **44**.
- S2/S3 con guardrails: **60**.
- Ejes causales unknown: **169**.

La revisión conserva los 723 elementos para trazabilidad, pero separa el
conocimiento activable, el material de investigación y las entradas archivadas.
Los scores son heurísticos de organización, no eficacia empírica demostrada.

## Ronda 1

**Roles:** Arquitecto de producto; modelador de amenazas; auditor de datos; usuario final; escéptico

**Problema crítico:** La taxonomía de fases no contenía DELIMITAR y mezclaba alcance con ideación.

**Solución A:** Mantener ocho fases y tratar el alcance como metadato externo.

**Solución B:** Añadir DELIMITAR y reclasificar por señales de alcance, activos, riesgo, consentimiento y autorización.

**Votación:** 6-1 a favor de B

**Resolución:** Se adopta una canalización de nueve fases con stage_primary y stage_secondary.

**Actualización aplicada:** 196 registros reubicados; 28 pasan a DELIMITAR.

## Ronda 2

**Roles:** Ingeniero de taxonomías; arquitecto de software; analista SOC; investigador de innovación; auditor QA

**Problema crítico:** La clasificación por primera coincidencia y subcadenas cortas generaba falsos positivos.

**Solución A:** Corregir manualmente las categorías más visibles.

**Solución B:** Usar vocabularios controlados, límites de palabra, puntuación ponderada y categoría secundaria.

**Votación:** Unanimidad por B

**Resolución:** Se sustituye la clasificación lineal por un clasificador determinista versionado.

**Actualización aplicada:** 274 categorías primarias cambiadas; se añade confianza taxonómica.

## Ronda 3

**Roles:** Arquitecto DevTools; ingeniero defensivo; red team autorizado; responsable de producto

**Problema crítico:** El campo hybrid ocultaba si un elemento era útil realmente para DevTools o para ciberseguridad.

**Solución A:** Mantener un enum único de tres valores.

**Solución B:** Añadir puntuaciones independientes y dominio primario/secundario.

**Votación:** 5-1 por B

**Resolución:** Se añaden cybersecurity_fit y developer_tools_fit de 0 a 100.

**Actualización aplicada:** 410 registros reciben una clasificación de dominio distinta.

## Ronda 4

**Roles:** Red team; blue team; responsable legal; operador de laboratorio; auditor de seguridad

**Problema crítico:** El alcance de ejecución no diferenciaba suficientemente diseño defensivo, sandbox y alto control.

**Solución A:** Conservar únicamente execution_scope.

**Solución B:** Introducir S0-S3, autorización explícita, sandbox obligatorio y prohibición de objetivos externos.

**Votación:** Unanimidad por B

**Resolución:** Se adopta una matriz de seguridad ejecutable por registro.

**Actualización aplicada:** 80 alcances endurecidos; 60 registros quedan bajo guardrails.

## Ronda 5

**Roles:** Product owner; auditor de calidad; investigador; usuario; arquitecto de rendimiento

**Problema crítico:** 294 elementos core eran demasiados para una activación predeterminada.

**Solución A:** Reducir core usando solo un umbral de score.

**Solución B:** Crear cinco niveles y seleccionar esencial/núcleo mediante cuotas de diversidad.

**Votación:** 6-1 por B

**Resolución:** Se adoptan essential, core, extended, research y archive.

**Actualización aplicada:** Essential=72; core=180; extended=277; research=150; archive=44. Tres entradas limítrofes se promovieron en una segunda pasada explícita.

## Ronda 6

**Roles:** Ingeniero de ranking; investigador de diversidad; arquitecto de costes; QA

**Problema crítico:** Los pesos 5/2 no distinguían calidad, rareza ni riesgo.

**Solución A:** Aumentar el rango fijo a 1-10.

**Solución B:** Calcular peso por tier, rareza de categoría y penalización de seguridad.

**Votación:** 4-1 por B

**Resolución:** Se introduce selection_weight 0-10 y default_enabled.

**Actualización aplicada:** S3 nunca queda habilitado por defecto; esencial/núcleo forman el conjunto inicial.

## Ronda 7

**Roles:** Auditor estadístico; ingeniero de calidad; escéptico adversarial; arquitecto

**Problema crítico:** audit_score mezclaba heurísticas no calibradas y parecía una medida empírica.

**Solución A:** Eliminar todos los scores.

**Solución B:** Conservar legado y añadir perfil BF-Q2.0 con seis componentes explícitos.

**Votación:** 5-2 por B

**Resolución:** Se añade quality_score_v2 con confianza y componentes trazables.

**Actualización aplicada:** El score v2 queda marcado como heurístico, no como eficacia demostrada.

## Ronda 8

**Roles:** Diseñador de prompts; usuario final; documentalista; auditor de fuentes

**Problema crítico:** Una entrada del catálogo no era directamente ejecutable por un modelo.

**Solución A:** Reescribir manualmente cada técnica.

**Solución B:** Preservar source_text y añadir operational_prompt derivado y etiquetado.

**Votación:** Unanimidad por B

**Resolución:** Se separa fuente canónica de instrucción operacional.

**Actualización aplicada:** 723 registros reciben operational_prompt sin alterar el texto fuente.

## Ronda 9

**Roles:** Auditor de duplicados; experto semántico; arquitecto de conocimiento; escéptico

**Problema crítico:** Títulos iguales podían ocultar duplicados o variantes útiles.

**Solución A:** Eliminar automáticamente todos los títulos repetidos.

**Solución B:** Agrupar, elegir canónico y conservar variantes con descripción distinta.

**Votación:** 6-1 por B

**Resolución:** No se destruyen variantes; se añaden cluster, canonical_item_id y estado.

**Actualización aplicada:** 5 grupos de títulos repetidos quedan trazados.

## Ronda 10

**Roles:** Ingeniero causal; arquitecto de seguridad; investigador de innovación; QA

**Problema crítico:** El catálogo describía técnicas pero no qué variable causal suelen alterar.

**Solución A:** Inferir un mecanismo libre mediante LLM.

**Solución B:** Asignar ejes causales cerrados y dejar unknown cuando no hay evidencia.

**Votación:** Unanimidad por B

**Resolución:** Se añade causal_axis_primary/secondary con confianza.

**Actualización aplicada:** 169 entradas quedan honestamente en unknown y salen de essential.

## Ronda 11

**Roles:** Arquitecto de APIs; integrador MCP; diseñador de workflows; usuario

**Problema crítico:** No estaba definido qué recibe ni qué produce cada técnica.

**Solución A:** Dejar que el modelo decida el contrato en cada ejecución.

**Solución B:** Añadir input_contract y output_artifact por fase.

**Votación:** 5-0 por B

**Resolución:** Cada registro obtiene contrato mínimo de integración.

**Actualización aplicada:** Se habilita selección y encadenamiento determinista en CRIBA.

## Ronda 12

**Roles:** Operador; SRE; responsable de incidentes; escéptico; legal

**Problema crítico:** Faltaban condiciones de uso, contraindicaciones y prerrequisitos.

**Solución A:** Añadir una nota genérica al modo BLACKFORGE.

**Solución B:** Añadir use_when, avoid_when y prerequisites por registro.

**Votación:** 4-1 por B

**Resolución:** La guía de activación pasa a formar parte del esquema.

**Actualización aplicada:** Los elementos de riesgo exigen autorización, sandbox, rollback, logs y stop condition.

## Ronda 13

**Roles:** Ingeniero de pruebas; auditor forense; científico experimental; product owner

**Problema crítico:** No se distinguía una lente conceptual de una técnica verificable.

**Solución A:** Usar audit_score como sustituto de evidencia.

**Solución B:** Añadir evidence_level y verification_method.

**Votación:** Unanimidad por B

**Resolución:** Se clasifican none, conceptual, testable, adversarial y reproducible.

**Actualización aplicada:** Las técnicas reproducibles y adversariales reciben prioridad sin ocultar riesgo.

## Ronda 14

**Roles:** Responsable legal; especialista privacidad; factores humanos; red team; usuario

**Problema crítico:** Impacto humano, privacidad y cumplimiento quedaban diluidos en categorías técnicas.

**Solución A:** Crear catálogos separados.

**Solución B:** Añadir flags transversales y mantener un catálogo único.

**Votación:** 5-2 por B

**Resolución:** Se añaden human_impact y compliance_impact.

**Actualización aplicada:** Las selecciones pueden exigir representación humana/legal sin duplicar registros.

## Ronda 15

**Roles:** Arquitecto DevTools; blue team; red team autorizado; gestor de producto

**Problema crítico:** Un único orden no servía a DevTools, defensa, investigación ofensiva e híbrido.

**Solución A:** Crear cuatro CSV independientes.

**Solución B:** Mantener una fuente y añadir cuatro puntuaciones de perfil.

**Votación:** 6-0 por B

**Resolución:** Se añaden perfiles offensive_research, defensive_engineering, devtools e hybrid.

**Actualización aplicada:** CRIBA puede construir vistas sin fragmentar la procedencia.

## Ronda 16

**Roles:** Diseñador multiagente; arquitecto de prompts; investigador de creatividad; QA

**Problema crítico:** Combinar técnicas del mismo papel producía redundancia y ruido.

**Solución A:** Permitir combinaciones aleatorias.

**Solución B:** Asignar combination_role y recommended_pair_roles.

**Votación:** 5-1 por B

**Resolución:** Las combinaciones se realizan entre funciones complementarias.

**Actualización aplicada:** Se evita emparejar sistemáticamente generador con generador o juez con juez.

## Ronda 17

**Roles:** Investigador de diversidad; estadístico; product owner; escéptico

**Problema crítico:** El ranking podía volver a concentrarse en categorías dominantes.

**Solución A:** Elegir siempre los elementos con score más alto.

**Solución B:** Aplicar cuotas por categoría, eje causal, etapa, catálogo y familia.

**Votación:** Unanimidad por B

**Resolución:** Se crea una política de muestreo para sesiones de 12 elementos.

**Actualización aplicada:** Essential se selecciona con máximos por categoría/fase/fuente y mínimo de diversidad causal.

## Ronda 18

**Roles:** Cumplimiento legal; red team; blue team; operador de sandbox; auditor

**Problema crítico:** El catálogo podía describir técnicas duales sin imponer límites de ejecución.

**Solución A:** Eliminar todo elemento dual-use.

**Solución B:** Retener conocimiento, pero bloquear ejecución automática y objetivos externos.

**Votación:** 5-2 por B

**Resolución:** Se adopta política authorized_defensive_only con controles por clase.

**Actualización aplicada:** S2/S3 son diseño/sandbox; no hay ejecución automática contra terceros.

## Ronda 19

**Roles:** Ingeniero de datos; auditor de configuración; mantenedor; SRE

**Problema crítico:** Cambios futuros podían volver irreproducible una selección anterior.

**Solución A:** Versionar solo el archivo completo.

**Solución B:** Versionar esquema, reglas, score y hash por registro.

**Votación:** Unanimidad por B

**Resolución:** Se añaden hashes, fingerprints y versiones estables.

**Actualización aplicada:** Cada registro puede auditarse y compararse entre releases.

## Ronda 20

**Roles:** Consejo completo: seguridad, software, QA, legal, usuario, innovación y operaciones

**Problema crítico:** Faltaba un gate único de aceptación para declarar el catálogo integrable.

**Solución A:** Aprobar por revisión visual del CSV.

**Solución B:** Exigir invariantes estructurales, taxonómicos, de seguridad y diversidad.

**Votación:** 7-0 por B

**Resolución:** Se aprueba v2.0.0-debate20 con una cola explícita de revisión.

**Actualización aplicada:** Gate verde: 723 IDs y referencias únicos, cuotas exactas, S2/S3 bajo sandbox y S3 deshabilitado por defecto.

## Gate final

- 723 IDs BLACKFORGE únicos.
- 723 referencias de fuente únicas.
- Todos conservan source_text y fingerprints.
- S3 nunca queda habilitado por defecto.
- S2/S3 exigen sandbox.
- El catálogo contiene las nueve fases.
- Essential + core forman la carga predeterminada.
- Las variantes de título quedan trazadas y no se borran a ciegas.
- Los ejes causales unknown no entran en essential.