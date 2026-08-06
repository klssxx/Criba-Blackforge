# PLAN POR FASES — CRIBA + BLACKFORGE (desde HIPERMEGAPROMPT_COMPLETO)

Estado: DISEÑO + REVISIÓN (lectura del spec §0–§21 y del repo). Implementación sujeta a gates y autorización por fase.

## Decisiones de diseño (defaults; corregir si no aplican)

- **D1 Orquestador P2–P6 = HÍBRIDO.** Núcleo determinista ya construido (context/task/constraints/output/engine/blackforge_*) se mantiene. La capa "Personas/Ensemble/Cadena/Autorefuerzo" se implementa como:
  - Validadores estructurados pydantic (siempre, determinista).
  - Prompts de persona (solo si `llm_adapter` tiene backend cloud/ollama; si no, fallback determinista que emite el contrato con confianza marcada como `inferred`).
- **D2 P1 = BASELINE ya entregada.** Se audita, no se replanifica como fase nueva.
- **D3 P6 = COMPLETAR** sobre `blackforge_*` existente. Prohibido reescribir (anti-sobrearquitectura, spec §1.3).
- **D4 Este documento** vive en `docs/PLAN_FASES_CRIBA_BLACKFORGE.md`.

## Orden óptimo (no estrictamente secuencial)

P1 (baseline) → **P7 gates + P8 logs (transversales, habilitan auditar)** → P2 → P3 → P4 → P5 → P6 → P9 → P10.

Razón: P7/P8 son la base de auditoría de todas las demás. Sin gates ni logs, P2–P6 no pueden cerrar gate de evidencia.

---

## P1 — Fundación determinista (BASELINE, ya existe — auditar)

**Objetivo:** Confirmar que el núcleo CRIBA cubre spec §0, §2, §3, §4, §5.
**Reutiliza:** `context_layer.py`, `task_layer.py`, `constraints.py`, `output_format.py`, `engine.py`, `methods.py`, `catalog.py`, `storage.py`.
**Entregables de auditoría:**
- Tests unit existentes pasan: `tests/unit/test_context_layer.py`, `test_task_layer.py`, `test_constraints.py`, `test_output_format.py`, `test_engine.py`.
- Golden: `tests/test_mvp_golden_output.py`.
**Gate P1:** todos los tests unit + golden en verde. Sin gate rojo, no arranca P2.

---

## P2 — Personas (spec §1)

**Diseño:** Módulo `src/criba/personas.py` con 4 contratos pydantic:
- `PersonaA` (Arquitecto sistémico) → salida `system_architect_output` (yaml §1.3).
- `PersonaB` (Innovación/cartógrafo) → `innovation_architect_output` (§1.4).
- `PersonaC` (Auditor evidencia) → `evidence_auditor_output` (§1.5).
- `PersonaD` (Adversarial/seguridad) → `adversarial_engineer_output` (§1.6).
- Personas compuestas (Buffett/Jung/Thorp) como mezcla de dimensiones (§1.2).
- `team_protocol` (§1.8): `independent_first_pass`, `minority_report_required`.

**Implementación:**
- Validadores pydantic deterministas (siempre disponibles).
- `build_persona_prompt(persona_id, packet)` reusa `engine.build_prompt` + `llm_adapter.build_llm_prompt`; si backend = none → `PersonaResult(confidence="inferred", source="deterministic_fallback")`.
- No crear "4 voces que dicen lo mismo": cada contrato impone campos distintos; test anti-voz-rep (spec §14.13/14.14).

**Auditoría (gate P2):**
- Cada salida valida su contrato pydantic (G01).
- Test: 4 salidas distintas sobre el mismo packet (`tests/unit/test_personas.py`).
- `minority_report` obligatorio cuando hay desacuerdo (§1.8).
- Rechazo si las 4 producen lo mismo (trigger regen §6.10).

---

## P3 — Ensemble de 4 personas (spec §6)

**Diseño:** `src/criba/ensemble.py`.
- Aislamiento (§6.2): las 4 corren sin verse (`personas_see_other_outputs: false`).
- Normalización + síntesis (§6.4): coincidencia fuerte/parcial/desacuerdo.
- Hallazgos emergentes (§6.5) — NO simple mezcla textual.
- Informe minoritario (§6.7).
- NO votación simple (§6.8): factores de decisión ponderados.
- Regeneración (§6.10): condiciones de disparo.

**Implementación:**
- `run_ensemble(packet)` → 4 `PersonaResult` (reusa P2) → `ensemble_synthesis` (pydantic §6.6).
- Síntesis determinista: intersección de `confirmed_facts`, unión de `hypotheses`, clasificación de desacuerdos (factual/causal/criterio/arquitectónico/irreconciliable).
- `emergent_finding` requiere `intersection_logic` + `why_no_single_persona_found_it` (anti-falso-emergente §14.23).

**Auditoría (gate P3):**
- Independencia verificable (test inyecta salida previa y exige que no la consuma).
- Síntesis no borra desacuerdo (§14.23): test con desacuerdo forzado.
- Métricas ensemble (§6.9): `semantic_diversity`, `mechanism_diversity`, `emergent_finding_count`.
- Trigger regen cuando aplica (§6.10).

---

## P4 — Cadena de 6 fases con revisión humana (spec §7)

**Diseño:** `src/criba/chain.py`.
- Máquina de estados (§7.1 + §10.5): `pending → running → awaiting_human_review → approved → completed` (+ `rejected`, `superseded`, `revision_required`).
- Memoria condensada (§7.2): `chain_memory` pydantic; conserva decisiones/hallazgos/feedback, elimina ornamento.
- 6 fases (§7.3–7.8) con salidas `stage_N_output` pydantic.
- Revisión humana (§7.9): `review_actions` + `human_decision_record`.
- Rehidratación selectiva (§7.10): `rehydration_request` (no reprocesa todo).

**Implementación:**
- `ChainRunner` persiste `chain_memory` en `storage.py` (idempotente, §10.5).
- Cada fase consume memoria condensada de la anterior; rehidrata solo lo pedido.
- Transiciones prohibidas rechazadas por `gates.G05_state_transition_valid`.

**Auditoría (gate P4):**
- Transiciones inválidas bloqueadas (G05).
- Sin pérdida entre fases (§14.17): test compara `chain_memory` antes/después.
- G11 `human_review_present` antes de `approved`.
- Rehidratación no duplica (idempotencia G09).

---

## P5 — Autorefuerzo adversarial de 2 pasadas (spec §8)

**Diseño:** `src/criba/adversarial_self.py`.
- Pasada 1: `ARQUITECTO CONSTRUCTOR DE TESIS` → `thesis_pass` (§8.3).
- Pasada 2: `FISCAL ADVERSARIAL` persona DISTINTA → `adversarial_pass` (§8.4); extensión Blackforge (§8.5).
- Microfase resolución determinista (§8.6): `thesis_resolution` por sintetizador neutral / auditor C / revisión humana (NO el constructor original sin ver ataque).
- Rechazo de adversario superficial (§8.7).

**Implementación:**
- `run_self_adversarial(packet)` → `thesis_pass` → aislar → `adversarial_pass` (reusa `PersonaD`/Fiscal) → `thesis_resolution`.
- `kill_criteria` y `survivable_parts` obligatorios en salida.
- Ubicación: se invoca tras Fase 4 y dentro de Fase 5 (§8.8).

**Auditoría (gate P5):**
- La 2ª pasada es realmente distinta (test: diferente `persona_id`, contratos distintos).
- `kill_criteria` presente y no vacío.
- Resolución no la firma el constructor original sin `adversarial_pass` visible.
- En Blackforge, `likely_bypasses` + `residual_risk` presentes (§8.5/§14.9).

---

## P6 — Blackforge (spec §2, §3, §4)

**Diseño:** COMPLETAR sobre `blackforge_safety.py`, `blackforge_selector.py`, `blackforge_pipeline.py`, `blackforge_causal.py`, `blackforge_catalog.py`.
- `authorization_state` obligatorio (G04) antes de cualquier acción ofensiva.
- Threat model (§3.4), hipótesis ofensiva, mecanismo defensivo, bypass, riesgo residual (§5.3).
- Restricciones Blackforge (§4.3): autorización, evidencia>hallazgo, no exagerar severidad, no defensa peor que problema, no cumplimiento=seguridad, no ocultar riesgo residual.

**Implementación:**
- `SafetyDecision` ya tiene autorización con ISO timestamp — extender a `authorization_state` enum (`pending/granted/denied/expired`).
- `blackforge_pipeline.run_headless` ya emite artefactos deterministas — validar contra `BlackforgeOutput` (output_format) y gates.
- Añadir `bypass_probable` y `residual_risk` a salida si faltan.

**Auditoría (gate P6):**
- G04: sin `authorization_state=granted` → bloquea acción ofensiva (metamórfico §10.8: eliminar autorización bloquea).
- `residual_risk` presente en toda recomendación Blackforge.
- Blackforge no degrada a checklist (§14.9): test exige `bypass` + `residual_risk`.
- Tests: `tests/unit/test_blackforge_*.py` ya existen — ampliar con gate G04.

---

## P7 — Determinismo / Gates (spec §10) — TRANSVERSAL

**Diseño:** `src/criba/gates.py`.
- Gates G01–G12 (§10.3): schema_valid, context_complete, required_anchors, authorization_valid, state_transition_valid, no_broken_references, scores_normalized, evidence_requirement_met, no_duplicate_ids, trace_complete, human_review_present, output_contract_valid.
- Invariantes (§10.2), máquina estados (§10.5), idempotencia (§10.5), reintentos (§10.6).
- Golden (§10.7), metamórficos (§10.8), property-based (§10.9), shadow mode (§10.10).
- Veredicto (§10.11): `VERIFIED / PARTIAL / BLOCKED / FAILED`.

**Implementación:**
- `evaluate_gates(packet)` → `GateReport` (todos los G* con PASS/FAIL + reason).
- Reusa `blackforge_causal.canonical_hash` para hashes de reproducibilidad (§10.2).
- `VERIFIED` prohibido sin prueba reproducible de función principal (§10.11).

**Auditoría (gate P7):**
- Todos los gates implementados y ejercitados por tests.
- Golden tests (canónicos CRIBA/Blackforge/sin-auth/evidence-insufficient/duplicados/divergencia/desacuerdo/minoritario/autorefuerzo/rehidratación).
- Metamórficos: los 6 del §10.8.
- Shadow mode antes de promover cambio de pipeline.

---

## P8 — Logs y trazabilidad (spec §11) — TRANSVERSAL

**Diseño:** `src/criba/logging.py`.
- 5 tipos (§11.2): event / audit / operational / security / model_interaction.
- Esquema de evento (§11.3), correlación `chain_id`/`stage_id` (§11.4), integridad (§11.5), minimización (§11.6), niveles (§11.7).
- Trazabilidad de hallazgo (§11.8) e idea (§11.9), observabilidad (§11.10), reconstrucción fría (§11.11), exportación (§11.12), pruebas (§11.13).

**Implementación:**
- `LogEmitter` con `emit(event)`; `correlate(chain_id, stage_id)`.
- NUNCA secretos en claro (§11.1): redactor antes de escribir.
- Persistencia vía `storage.py`.

**Auditoría (gate P8):**
- Test: reconstrucción fría reproduce sesión desde logs (§11.11).
- Test: ningún secreto en claro en fixtures de log (§11.1).
- Trazabilidad completa (G10) en cada idea/hallazgo.

---

## P9 — Latencia (spec §9)

**Diseño:** `src/criba/latency.py`.
- Presupuesto adaptativo (§9.3), lotes (§9.4), paralelismo controlado (§9.5), caché semántica (§9.6, reusa `similarity.py`), early-exit (§9.9), separación de modelos (§9.11), planificador (§9.12), métricas (§9.14).
- Restricción crítica (§9.15): presupuesto nunca excedido sin abortar.

**Implementación:**
- `LatencyBudget` con `spend(token_est)` y `early_exit()`.
- Caché semántica sobre `genome_distance`/`similarity`.
- Solo aplica cuando hay backend LLM; en modo determinista es no-op medido.

**Auditoría (gate P9):**
- Presupuesto respetado (test inyecta overrun → aborta, §9.15).
- Early-exit reduce coste (test con lote grande + umbral).
- Métricas de latencia presentes (§9.14).

---

## P10 — Métricas y feedback (spec §13)

**Diseño:** `src/criba/metrics.py`.
- Entrada/generación/evaluación/blackforge/proceso/resultado (§13.2–13.8).
- Feedback explícito/implícito (§13.8/13.9), bucle mejora (§13.10), registro cambios (§13.11), deriva (§13.11/13.12), gates promoción (§13.13), HITL (§13.14), métrica compuesta (§13.15).

**Implementación:**
- `MetricsCollector` agrega de P7 (gates) y P8 (logs).
- Alimenta selección dinámica de modo (§15.2).
- Detección de deriva compara contra golden (P7).

**Auditoría (gate P10):**
- Métricas definidas (no arbitrarias, §14.18): cada una con fórmula.
- Gate de promoción (§13.13) bloquea regresión.
- HITL presente donde el spec lo exige (Blackforge autorización).

---

## Criterios de aceptación globales (spec §16, §20)

- Checklist CRIBA (§20.1) y Blackforge (§20.2) en verde por fase.
- Multiagente (§20.3) y Pipeline (§20.4) validados.
- Todo entregable tiene evidencia ejecutada (pytest green), no solo markers estructurales.
- Principio final (§21): realidad > novedad aparente.

## Comandos de verificación por fase

```
Set-Location C:/ruta/al/clon/Criba-Blackforge
.venv/Scripts/python -m pytest tests/unit -q        # P1, P2, P3, P6, P7
.venv/Scripts/python -m pytest tests -q              # regresión completa
.venv/Scripts/python -m pytest tests/test_mvp_golden_output.py -q   # P1 golden
.venv/Scripts/python scripts/benchmark_real.py       # P9 latencia (si backend)
```

## Notas de reversibilidad

- Cada fase en su propio commit (git, no push sin autorización).
- `migration.py` cubre v1→v2; nuevos contratos pydantic versionados.
- Rollback = `git revert` de la fase; estado en `storage` versionado por `chain_id`.
