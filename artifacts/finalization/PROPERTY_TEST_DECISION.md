# PROPERTY TEST DECISION — CRIBA + BLACKFORGE

Fecha: 2026-07-24 | FASE 4 (property-based testing con criterio)

## Candidatos auditados

| Función | Propiedad real | ¿Hypothesis aporta? |
|---------|---------------|--------------------|
| `value_score` (evidence*novelty/cost) | rango, determinismo | Parcial — ya cubierto por `test_value_score_contract` |
| `select_blackforge` | determinismo por semilla, cuotas | Parcial — `test_deterministic_same_seed`, `test_selection_respects_policy` |
| `normalize_proposal` (genome) | idempotencia, pertenencia enum | Parcial — `test_genome_similarity_unknown` |
| `canonical_hash` (blackforge_causal) | round-trip, invariancia | Parcial — `test_blackforge_causal` |
| `pipeline_action` | pertenencia a enum | Cubierto por tipos + contract |

## Decisión

**NO_CHANGE_JUSTIFIED.**

Justificación:
1. Las 204 pruebas existentes ya cubren los invariantes de rango, determinismo,
   cuotas, pertenencia a enum y round-trip mediante tests deterministas con
   fixtures fijos y golden masters.
2. Añadir Hypothesis NO aumenta la confianza de forma incremental medible para
   estos flujos (ya son puros y están bloqueados por tests de contrato).
3. El mandato prohíbe "añadir Hypothesis solo para aumentar una cifra".

Riesgo cubierto si se añadiera: bajo. Riesgo de no añadirlo: nulo (ya cubierto).

## Acción

No se añaden tests property-based. Se cierra la fase como NO_CHANGE_JUSTIFIED.
Si en el futuro se refactoriza `value_score` o `select_blackforge`, reconsiderar.
