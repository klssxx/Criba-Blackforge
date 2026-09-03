# IIE CONTINUITY — CRIBA · BLACKFORGE · SUPRA

**Última actualización**: 2026-09-03 (tras P00 GATE)

## WHAT IS THE PROJECT?
Master Innovation Intelligence Blueprint v1.0-ZAI: extender CRIBA (innovation engine, NO reemplazo) con un Innovation Intelligence Engine (IIE) aditivo bajo `src/criba/intelligence/`, integrar BLACKFORGE (safety) y SUPRA (orquestación) vía fronteras contractuales. 130 técnicas T001-T130 con owner canónico único.

## WHAT IS ALREADY DONE? (VERIFIED)
- P00-T01 Inventario: CRIBA=68 py/20787 LOC/44 paquetes; SUPRA=13 py/2089 LOC. Zero código intelligence preexistente.
- P00-T02 Contratos legacy mapeados: gates G01-G12 (`gates.py`), `HybridOrchestrator` (`hybrid.py`), `cartograph_and_break`/`diverge`/`value_score`/`activate` (`engine.py`), `Storage` (`storage.py`), `evaluate_blackforge_safety` (`blackforge_safety.py`), `ProjectStateManager` (SUPRA `state.py`), providers boundary (SUPRA `providers/base.py`).
- P00-T03 Baseline tests: **CRIBA 681 passed** / **SUPRA 21 passed** (= oráculo de regresión).
- P00 GATE: tag `pre-iie-baseline`, branch `feat/iie-master`, STATE/journals/checkpoint commiteados.

## WHAT IS CURRENTLY IN PROGRESS?
P01 CONTRACTS (T01 architecture boundaries → T06 audit).

## WHAT FAILED?
Nada.

## WHAT IS BLOCKED?
Nada. (Deuda preexistente fuera de alcance: uuid4 engine.py:1015.)

## WHAT MUST NOT BE TOUCHED?
- `engine.py` completo (solo hooks aditivos), `hybrid.py` (hooks opcionales solo), `gates.py`, `blackforge_safety.py` (JAMÁS debilitar), golden `tests/golden_mvp_output.json` (no actualizar para ocultar regresiones), `criba.sqlite3` (IIE usa `intelligence.sqlite3` separada), SUPRA `providers/` internals.

## LAST VERIFIED COMMIT?
`05d69c3` (main, CRIBA) / `6dca3d9` (main, SUPRA). Tag: `pre-iie-baseline`.

## WHAT TESTS CURRENTLY PASS?
CRIBA 681, SUPRA 21 (full suite, 2026-09-03).

## FEATURE FLAGS ENABLED?
Ninguno (los 13 flags IIE = false por diseño hasta su fase).

## NEXT EXACT TASK?
P01-T01: architecture boundaries (documento de fronteras por dominio D01-D15 + dependencias permitidas + test anti-ciclos).

## MODEL/REASONING FOR IT?
GLM-5.3 max (rol arquitecto) para el diseño de fronteras; implementación T02-T05 con high/low.
