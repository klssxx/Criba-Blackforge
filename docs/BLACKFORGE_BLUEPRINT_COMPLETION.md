# CRIBA / BLACKFORGE — Blueprint completo

Estado: VERIFIED en worktree aislado
Rama: `blackforge-blueprint-complete`
Base de auditoría: `4a6b6e02af49960272dfaa9702ed6c5de197ff65`
Tip de implementación antes de este journal: `476b782da7403fde41122302629a7f891b0557df`

## Cobertura por fase

- P1: baseline CRIBA existente, conservado y cubierto por regresión.
- P2: personas independientes y contratos estrictos, existente y auditado.
- P3: ensemble, diversidad, regeneración y minority report, existente y auditado.
- P4: estados HITL, persistencia de outputs/reviews y rehidratación selectiva.
- P5: extensión adversarial específica de BLACKFORGE con bypasses y riesgo residual.
- P6: autorización explícita `granted`, artefactos LF deterministas, propagación de bypass/riesgo y winner estructurado.
- P7: G01–G12, comparación shadow sin mutación y seis pruebas metamórficas.
- P8: recuperación de hash-chain tras reinicio e idempotencia de eventos.
- P9: presupuesto atómico, intervalos de latencia y percentiles observados.
- P10: feedback explícito validado, ingestión de gates/logs y quality breakdown con fórmula/versionado.

## Cambios versionados

Código: `src/criba/adversarial_self.py`, `blackforge_causal.py`, `blackforge_pipeline.py`, `blackforge_safety.py`, `chain.py`, `gates.py`, `latency.py`, `logging.py`, `metrics.py`, `output_format.py`, `storage.py`.

Pruebas: `tests/unit/test_adversarial_self.py`, `test_blackforge_causal.py`, `test_blackforge_pipeline.py`, `test_blackforge_safety.py`, `test_blueprint_metamorphic.py`, `test_chain.py`, `test_gates.py`, `test_latency.py`, `test_logging.py`, `test_metrics.py`.

## Evidencia ejecutada

- Baseline: `pytest -q -p no:cacheprovider` → 893 passed.
- Verificación final: `compileall -q src` → OK.
- Regresión final: `pytest -q -p no:cacheprovider` → 919 passed, 1 warning externo de Starlette/httpx.
- End-to-end: `run_headless(seed=1)` → `OK`, 12 seleccionadas, 11 ideas tras CCA.
- Gates end-to-end: G01–G12 → 12/12 passed, veredicto `VERIFIED`.
- Artefactos temporales: raw 22688 B, normalizado 21904 B, UUID/timestamp eliminados del normalizado, tempfile eliminado.
- `git diff --check` → limpio.
- Worktree aislado → limpio.

## Commits de implementación

`2922541`, `d9154ea`, `25f499c`, `5295edc`, `ff2a658`, `a441e1d`, `bddb878`, `e71a019`, `928d1ab`, `476b782`.

## Coste y límites

COST=0. Todo se ejecutó localmente; no se llamó a proveedores LLM de pago.

La rama no se integró ni se hizo push. `E:/PROYECTS/CRIBA` conserva cambios previos ajenos a esta rama; este blueprint no los modifica ni afirma que estén incorporados al árbol vivo.

Rollback reversible del resultado aislado: `git -C E:/PROYECTS/_BF_BLUEPRINT_WT switch --detach 4a6b6e0`.
