# ENGINE VERIFICATION REPORT — CRIBA + BLACKFORGE

Fecha: 2026-07-24 | FASE 3 (revisión funcional del motor)

## CRIBA (flujos principales)

Verificado por suite Modal (204 passed) + smoke local end-to-end:

- Creación de idea: `activate()` genera 12 ideas por defecto. ✅
- Operadores: diverge por 5 ejes causales (Zwicky box). ✅
- Evaluación: `_evaluate_idea` usa `value_score = evidence*novelty/cost`. ✅
- Ranking: orden por value_score descendente. ✅
- Guardado: `storage.Storage` (SQLite loopback). ✅
- Historial / innovaciones: endpoints de api.py + storage. ✅
- Cambio a BLACKFORGE: `criba blackforge ...` / `blackforge_pipeline.run_headless`. ✅

## BLACKFORGE (flujos)

- Carga catálogo: `blackforge_catalog.load()` 723 regs, MappingProxyType, inmutable. ✅
- Selección determinista: `select_blackforge(seed, session_size, profile)` cuotas. ✅
- Safety gate: `evaluate_blackforge_safety` S0-S3; DENY excluye ítem. ✅
- Trazabilidad: packet 2.1 + normalized (sin UUID/timestamp/path). ✅
- Persistencia: `save_artifacts` escribe verification/*.json. ✅

## Invariantes comprobados

| Invariante | Estado | Evidencia |
|-----------|--------|-----------|
| misma semilla + misma config = mismo resultado | ✅ | test_deterministic_same_seed (7/7 blackforge) |
| la selección nunca viola silenciosamente una restricción | ✅ | test_selection_respects_policy |
| si una cuota es imposible, fallo estructurado | ✅ | sel.failure no None → SELECTION_FAILED |
| los elementos archivados no son seleccionables | ✅ | catálogo inmutable + filtro |
| elementos de alto control exigen autorizaciones | ✅ | safety_gate_12_items |
| score dentro del rango declarado | ✅ | value_score contract test |

## Conclusión

Motor CRIBA + BLACKFORGE **verificado funcionalmente**. 204 passed, sin regresión.
No se cambia algoritmo (se prohíbe "hacer pasar una prueba mal diseñada").
