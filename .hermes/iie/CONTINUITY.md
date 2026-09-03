# IIE CONTINUITY — CRIBA · BLACKFORGE · SUPRA

**Ultima actualizacion**: 2026-09-03 (tras P02 GATE)

## WHAT IS THE PROJECT?
Master Innovation Intelligence Blueprint v1.0-ZAI: extender CRIBA (NO reemplazo) con Innovation Intelligence Engine aditivo bajo src/criba/intelligence/. 130 tecnicas T001-T130 con owner canonico. Addendums: SECTORIZATION + T001-T130.

## WHAT IS ALREADY DONE? (VERIFIED)
- P00: baseline congelado (tag pre-iie-baseline, branch feat/iie-master; CRIBA 681 + SUPRA 21 tests)
- P01: ADR-001 boundaries, skeleton 13 sectores, 43 contratos + 9 enums, technique_registry.yaml (130 exactas) + TechniqueRegistry, boundaries test AST. 21 tests.
- P02: IntelligenceStore (intelligence.sqlite3 separada, 18 tablas + FTS5, migraciones v1, cache TTL, technique_runs). 12 tests.
- Full suite: 713 passed, cero regresion legacy.

## WHAT IS CURRENTLY IN PROGRESS?
P03 SOURCES (empezando por T01 source protocol).

## WHAT FAILED?
Nada critico. 3 bugs menores P02 corregidos en ciclo (ver checkpoint P02).

## WHAT IS BLOCKED?
Nada.

## WHAT MUST NOT BE TOUCHED?
engine.py, hybrid.py, gates.py, blackforge_safety.py, golden tests, criba.sqlite3, SUPRA providers/.

## LAST VERIFIED COMMIT?
(commit P02 en feat/iie-master). Baseline tag: pre-iie-baseline = 05d69c3.

## WHAT TESTS CURRENTLY PASS?
CRIBA 713 (681 legacy + 32 IIE). SUPRA 21.

## FEATURE FLAGS ENABLED?
Ninguno (13 flags IIE = false).

## NEXT EXACT TASK?
P03-T01: IntelligenceSource protocol (capabilities/search/fetch/health; estados AVAILABLE/DEGRADED/UNCONFIGURED/RATE_LIMITED/UNAVAILABLE/DISABLED; free-first con cache; sin red en tests).

## MODEL/REASONING FOR IT?
GLM-5.3 high (protocol + OpenAlex/GitHub/arXiv adapters); low para fixtures.
