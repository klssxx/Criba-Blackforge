# ADR-001 — Architecture Boundaries IIE (P01-T01, rol MAX)

Fecha: 2026-09-03 · Estado: APPROVED (P01-T01) · Aplica: ADDENDUM secciones B, C, D, J

## Por qué
El ecosistema CRIBA/BLACKFORGE/SUPRA debe añadir un Innovation Intelligence Engine (IIE)
sin duplicar capacidades (ONE CAPABILITY → ONE CANONICAL OWNER) y sin dependencias
circulares. Este ADR fija las fronteras ANTES de escribir código (frontera conceptual
antes que física, regla BB del addendum).

## Dominios y owners canónicos (D01-D15)
| Dominio | Owner | Resto |
|---|---|---|
| INTAKE, CONTEXT, INVENTION(estructura), SCORING(fórmula) | CRIBA | consumidores |
| EXTERNAL INTELLIGENCE, RETRIEVAL, EVIDENCE, KNOWLEDGE GRAPH, SIGNALS, GAP DISCOVERY, PRIOR ART | CRIBA IIE (`criba.intelligence.*`) | consumidores vía contratos |
| SECURITY SPECIALIZATION (taxonomy/causal/safety) | BLACKFORGE | consume IIE, nunca reimplementa fuentes |
| ORCHESTRATION (long-running, checkpoints, routing) | SUPRA | NO implementa intelligence |
| MODEL PROVIDERS | Provider Interface (SUPRA `providers/base.py` + CRIBA `llm_adapter`) | nadie conoce internals |
| PRESENTATION | `criba/ui` + `criba.gui` | sólo presentan |

## Jerarquía de dependencias (C) — sólo hacia abajo
```
L4 PRESENTATION      criba.ui, criba.gui, CLI, REST(api.py), MCP(mcp_server.py)
L3 APPLICATION       criba.intelligence.orchestrator, pipeline, capabilities, monitoring
L2 DOMAIN ENGINES    retrieval, graph, signals, gaps, invention, prior_art, scoring, problems, sources
L1 CONTRACTS+STORAGE criba.intelligence.contracts, enums, storage/, cache, dedup, provenance, claims, budget, config
L0 EXTERNAL ADAPTERS sources/* (HTTP), external vector/graph backends (opcionales)
```

## Reglas duras (auditables por test)
1. `criba.intelligence.contracts` y `criba.intelligence.enums` NO importan nada de `criba.*` fuera de `criba.intelligence` (contratos puros).
2. `criba.intelligence.*` NO importa: `criba.ui`, `criba.gui`, `criba.engine`, `criba.hybrid`, `criba.ensemble`, `criba.chain`, `criba.personas`, `criba.lottery`, `criba.blackforge_*`, ni `supra_agentic`. La integración legacy (P12) va en el SENTIDO INVERSO: un único módulo puente `criba/intelligence/legacy_bridge.py` es la única excepción permitida, y sólo expone hooks.
3. L2 no importa L3/L4; L1 no importa L2/L3/L4 (sin ciclos, addendum J).
4. SUPRA consume IIE solo vía contrato HTTP/MCP/intelligence_client — nunca `import criba.intelligence.*` internals (P14).
5. BLACKFORGE consume técnicas IIE (retrieval/evidence/graph/prior_art) y añade taxonomy+causal+safety DESPUÉS. Prohibido `BlackforgePatentSearch`-style duplicados.
6. IIE usa `intelligence.sqlite3` (NUNCA `criba.sqlite3`).
7. Fallback: si IIE falla, legacy CRIBA/BLACKFORGE/SUPRA siguen funcionando (flags false por defecto).

## Decisión sobre migración
NEW CODE → NEW SECTORS. Legacy queda donde está (BA/BB/BC). Nada se mueve "por estética".

## Consecuencias
- Test `tests/intelligence/test_boundaries.py` parsea los imports reales y hace fallar el build si se viola (implementa addendum J sin ciclos).
- El TechniqueRegistry (P01-T05) será la única fuente de verdad de T001-T130 (machine-readable, addendum §105).
