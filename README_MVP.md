# CRIBA — MVP (LOCAL_MVP)

Estado: MVP local, offline, determinista. CRIBA genera NUEVAS IDEAS E INNOVAR
como propósito único. El motor produce ideas por RECOMBINACIÓN CRUZADA de
operadores sobre 5 variables causales, con filtro CCA que descarta la divergencia
cosmética.

## Dos nombres que NO se deben confundir

- `llm_backend = "hy3"` -> el modelo MoE Tencent Hy3 que YA se usa en Hermes para
  generar. Es el MODELO. En uso hoy.
- `mode = "LOCAL_MVP"` vs `mode = "AGENTIC"` -> el ESTADIO DE ARQUITECTURA.

LOCAL_MVP (ahora): sin red, determinista, genoma de 5 dimensiones causales,
cruce de families, divergencia forzada. Hy3 solo como motor de generación, no
como orquestador ni como evaluador externo.

AGENTIC (hook futuro): multiagente real + RAG/búsqueda + evaluadores dedicados de
novedad (SPARK/LiveIdeaBench-like). Hy3 sería un worker más, no el núcleo.

El contrato de esa capa futura ya existe en `src/criba/agentic.py` (interfaz
`AgenticLayer` + stub `LocalAgenticLayer`). Activarla es implementar
`Hy3AgenticLayer`, no reescribir el motor.

## Modelo de datos (packet v2.0.0)

Un único contrato canónico: `MANDATORY_MODEL_PACKET` (schema_version "2.0.0").
Campos legacy conservados (selected_current, supporting_methods, contextualization,
rupture, experiment, decision, model_instruction, response_contract). Bloque
aditivo `innovation` con: known_space, saturated_mechanisms, assumptions, ruptures,
idea_families, ideas, real_divergent_count, cosmetic_rejected, duplicate_report,
unclassified_properties.

`packet["ideas"]` es el MISMO objeto que `packet["innovation"]["ideas"]` (una sola
colección canónica, sin fuentes divergentes).

## Cómo se mide la innovación real (no cosmética)

- 5 variables causales (Zwicky box): quien_decide, cuando, evidencia_requerida,
  si_falla, topologia. Son los únicos ejes que miden divergencia.
- Los 16 operadores (catálogo methods) son VERBOS de generación (estilo TRIZ), no
  ejes. Cada uno perturba un eje causal.
- Divergencia = RECOMBINACIÓN POR PARES de operadores, cruzando ejes distintos.
- CCA: si un operador no movió ningún eje causal -> idea cosmética, se descarta del
  conteo de innovación real (`cosmetic_rejected`).
- La 4ª verificación (tests/test_causal_mechanism.py) garantiza que dos ideas con
  el mismo mechanism pero distinto cruce tienen vectores causales distintos; y que
  dos ideas con el mismo vector son detectadas como la misma idea.

## Genoma

5 dimensiones cerradas (MVP): actor, mechanism, topology, trust_model, time_model.
Vocabulario cerrado en `genome.py`. Valor inválido -> unknown. Concepto nuevo ->
`unclassified_properties` (con campo/valor/evidencia/origen/pending_review), nunca
se amplía la ontología automáticamente.

## Cómo verificar (gate)

Ejecutar `scripts/verify-mvp.ps1` ANTES de abrir la GUI, reconstruir el portable o
declarar terminado. Cubre:
- tests/test_packet_ideas_invariant.py (condición 13)
- tests/test_genome_similarity_unknown.py (condición 14)
- tests/test_packet_v1_regression.py (condición 15, fixture real)
- tests/test_mvp_golden_output.py (condición 16, golden master)
- tests/test_causal_mechanism.py (verificación de mecanismo causal)

## Backlog explícito (NO en el MVP)

B01 Cruce de ideas distantes · B02 Evolución por generaciones · B03 Pila de tres
corrientes · B04 Adversario bajo demanda · B05 Diseñador experimental · B06 Memoria
negativa · B07 Lista tabú · B08 Genealogía · B09 Atlas visual · B10 Cuatro
puntuaciones · B11 Juez ciego · B12 Metaexperimentos · B13 Banco experimental.
Capa AGENTIC (multiagente + RAG + evaluador SPARK) como hook futuro en agentic.py.
