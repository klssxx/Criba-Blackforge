# CHECKPOINT — 2026-07-23 (fin de sesión, con interrupciones anotadas)

Estado del gate tras este checkpoint: VERDE. 50 passed en los 5 archivos de gate
(antes 28; +22 de las nuevas capas de colisión de mecanismo causal).

## QUÉ SE HIZO EN ESTA SESIÓN (sin omitir interrupciones)
1. Corregido error de categoría en ideación: las 16 técnicas (methods) son
   OPERADORES (verbos TRIZ, capa de GENERACIÓN), NO ejes de divergencia. Los únicos
   ejes que miden divergencia real son las 5 causal_variables (Zwicky box):
   quien_decide, cuando, evidencia_requerida, si_falla, topologia.
2. Rediseñado diverge() a recombinación POR PARES de operadores (combinatorial
   divergence), cruzando ejes distintos. Cada operador declara (eje, valor_normal,
   valor_extremo) — el extremo es ESPECÍFICO del operador (no genérico por eje),
   para que dos operadores sobre el mismo eje produzcan vectores distintos.
3. Añadido filtro CCA (cross-consistency assessment): ideas cuyo operador no movió
   ningún eje causal se marcan divergence_real=False (divergencia cosmética) y se
   descartan del conteo de innovación real.
4. Corregido similarity.py: pesos normalizados solo a las 5 dims del genoma MVP
   (suman 1.0), unknown eliminado antes de Jaccard (all-unknown -> similitud 0.0),
   salida con matching_fields/different_fields/unknown_fields.
5. Corregido migration.py: captura de schema_version ORIGINAL antes de sobreescribir
   (bug "leer después de escribir" del Fallo 1).
6. Aclarada la confusión Hy3: llm_backend="hy3" (modelo ya en uso) vs mode=
   LOCAL_MVP/AGENTIC (arquitectura). Creado src/criba/agentic.py con interfaz
   AgenticLayer + stub LocalAgenticLayer (hook futuro AGENTIC: multiagente+RAG+
   evaluador SPARK). README_MVP.md documenta la distinción.
7. Añadida REGLA 9 (Comet) de causalidad: campo causal_claim por idea
   (MECHANISM_VERIFIED) + confianza diferenciada en metrics
   (conf_code_executes=1.0 verificable por lectura; conf_causal_root=
   "INFERRED_NOT_PROVEN" requiere prueba contrafactual).
8. Implementadas 4 CAPAS de test de colisión (per moli): capa1 determinismo por
   family, capa2 valor esperado explícito por contrato, capa3 paramétrica sobre
   TODOS los pares de riesgo, capa4 escaneo del mapa debe encontrar >=1 par.
   Refactor: engine._apply_family() es el código REAL que usan diverge y los tests
   (no réplica en el test).

## INTERRUPCIONES DEL USUARIO Y CÓMO SE RESOLVIERON (anotado, sin omitir)
- El usuario interrumpió para corregir el error de categoría (operadores vs ejes).
  Resuelto: se rediseñó diverge a dos capas (generación por operadores / medición
  por causal_variables) + CCA.
- El usuario aclaró que "hook futuro" no significa que Hy3 no se use hoy (ya lo usa
  como modelo). Resuelto: separación de nombres en agentic.py + README_MVP.md.
- El usuario pidió la regla 9 de correlación vs mecanismo causal. Resuelto:
  causal_claim + confianza diferenciada + test.
- El usuario pidió las 4 capas de test con jerarquía de fallo por capa. Resuelto.
- El usuario planteó 4 PEROS antes de aceptar el patch de las 4 capas:
  PERO1 docstring truncado (verificado: el archivo real tiene docstrings cerrados;
    el truncado era del diff de la herramienta, no del archivo).
  PERO2 _VALID_MECH no verificado (verificado: existe en engine.py línea 145).
  PERO3 _build_idea era réplica (corregido: ahora llama a engine._apply_family,
    código real).
  PERO4 falta conteo real de pares de riesgo (corregido y medido: 18 pares de
    riesgo con las 16 families reales; capa 4 válida y los cubre todos).
- El usuario pidió checkpoint y parar. Se redacta este archivo.

## EVIDENCIA DE VERIFICACIÓN (ad-hoc + gate)
- Gate completo: pytest 5 archivos -> RC=0, 50 passed.
- Capas de colisión aisladas (-k layer -v): 21 passed.
- Conteo de pares de riesgo reales (16 families): 18 pares
  (mismo mechanism + mismo eje). Ejes congestionados:
  evidencia_requerida=5 families, quien_decide=3, si_falla=3, cuando=3, topologia=2.
  Esto es INFO ÚTIL: evidencia_requerida es el eje más solapado -> candidato a
  más granularidad causal en el futuro si se quiere bajar el solapamiento.

## ARCHIVOS CREADOS/MODIFICADOS EN ESTA SESIÓN
Creados:
- src/criba/agentic.py (AgenticLayer stub LOCAL_MVP; hook futuro AGENTIC)
- src/criba/engine_v1_audit_intent.py (copia recuperable del motor anterior)
- tests/test_packet_ideas_invariant.py
- tests/test_genome_similarity_unknown.py
- tests/test_packet_v1_regression.py
- tests/fixtures/mandatory_model_packet_v1.json (real, de engine_v1)
- tests/test_mvp_golden_output.py
- tests/test_causal_mechanism.py (con 4 capas de colisión)
- scripts/verify-mvp.ps1
- verification/mvp_output_sample.json + .normalized.json (golden master)
- README_MVP.md
- HANDOFF.md
Modificados:
- src/criba/engine.py (esquema innovation v2.0.0, _OPERATOR_EFFECT con extremo por
  operador, _apply_family, diverge por pares, CCA, confianza diferenciada,
  causal_claim)
- src/criba/genome.py (ontología cerrada + UnclassifiedProperty)
- src/criba/similarity.py (pesos normalizados, unknown handling, contratos)
- src/criba/migration.py (captura schema_version original)

## SESIÓN 2026-07-23 (continuación, backend sin GUI)
- Añadida CAPA DE CONVERGENCIA (SPEC de moli): `_evaluate_idea(idea)` evalúa la
  calidad de lo que la GENERACIÓN produjo. Novead se lee de la capa de MEDICIÓN
  (ejes movidos vs base), nunca como eje de diseño. Fórmula:
  value_score = evidencia * novedad / coste. Ideas rankeadas por value_score
  (colección canónica ordenada), innovation.top_ideas + mean_value_score,
  metrics.mean_value_score. CCA intacto como medidor (no se toca).
- Flag `extreme` añadido a cada idea (input de la convergencia = lo que el
  operador produjo).
- Test de guardia `test_convergence_layer_uses_measurement_not_generators`:
  verifica la fórmula, que novedad es gradiente de la medición (no eje-generador),
  que CCA sigue decidiendo cosmética, y que el rankeo es por value_score.
- Golden master regenerado (contrato aditivo: convergence/extreme/top_ideas/
  mean_value_score).
- GATE: 51 passed (5 archivos).

## REGLA DE GUARDIA (de la especificación CRIBA, fase actual)
Antes de cualquier cambio futuro sobre el pipeline, confirmar explícitamente que
ningún eje (causal_variable) se trata como generador de ideas, ni ningún operador
como medidor. Si una modificación difumina esa frontera, detenerla y preguntar.
BLACKFORGE queda aislado para activación futura.

## ARCHIVOS MODIFICADOS EN ESTA CONTINUACIÓN
- src/criba/engine.py (_evaluate_idea, flag extreme, rankeo, top_ideas,
  mean_value_score en innovation+metrics)
- tests/test_causal_mechanism.py (test de guardia de convergencia)
- verification/mvp_output_sample.json + .normalized.json (golden regenerado)
- HANDOFF.md / CHECKPOINT_2026-07-23.md (actualizados)

## PRÓXIMO PASO HABILITADO
Reescritura de GUI (pantalla única estable) mostrando causal_variables + score de
convergencia por idea. Pendiente, no iniciado.


## NOTAS DE DEUDA TÉCNICA
- engine_v1_audit_intent.py es copia de referencia, no se importa en runtime.
- Genoma MVP en 5 dims; las otras 3 son backlog.
- Evaluador de novedad externo y capa AGENTIC son hook futuro (no implementados).
- GUI no reescrita todavía (pendiente del paso 1).
