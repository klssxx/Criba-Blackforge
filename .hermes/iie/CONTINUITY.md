# IIE CONTINUITY — CRIBA · BLACKFORGE · SUPRA

**Última actualización:** 2026-09-03 — STATE_RECONCILIATION

## WHAT IS THE PROJECT?
Preservation-first extension of CRIBA with the additive `src/criba/intelligence/` engine. CRIBA remains the canonical innovation engine; IIE owns external evidence intelligence; BLACKFORGE specializes cyber safety and authorization; SUPRA orchestrates workflows.

## WHAT IS ALREADY DONE? (VERIFIED)
- P00–P04 are committed through `709f16b` (P04 full suite: 733 passed).
- P05 group committed through `6de29de`: epistemic provenance, deterministic claim extraction, deterministic entity extraction/resolution and aliases.
- Checkpoint tooling committed through `cd95d80`; it distinguishes a metadata-only checkpoint commit from a code divergence.
- P05 targeted verification: `9 passed`; strict mypy over claims/provenance/entities: success.
- Legacy BLACKFORGE baseline: 138 targeted tests passed; 4 tracked-artifact emission tests intentionally deselected to avoid overwriting goldens in the live tree.

## WHAT IS CURRENTLY IN PROGRESS?
P05 remains open. P05-T03 (Claim store) is **NOT_STARTED**. No code is currently uncommitted outside the continuity artifacts being recorded.

## WHAT FAILED?
No runtime failure. The prior state ledger was stale: it omitted P00-T04/P00-GATE, listed P02-T01 both complete and pending, and did not identify the P05 WIP. It is reconciled in `STATE.json` from Git and actual test evidence.

## WHAT IS BLOCKED?
Nothing. BF-P00-T06 is deferred until existing tracked goldens are validated in an isolated copy; do not overwrite them in the live worktree.

## WHAT MUST NOT BE TOUCHED?
`engine.py`, `hybrid.py`, `gates.py`, `blackforge_safety.py`, canonical BLACKFORGE catalog, tracked golden outputs, `criba.sqlite3`, and SUPRA providers are read-only unless a specific approved task requires them.

## WHAT IS THE LAST VERIFIED COMMIT?
`cd95d80` — IIE state validation tooling; P05 feature code is `6de29de`.

## WHAT TESTS CURRENTLY PASS?
- `python -m pytest tests/intelligence/test_provenance.py tests/intelligence/test_multi_repo_state.py -q -p no:cacheprovider` → 9 passed.
- `mypy --no-incremental src/criba/intelligence/claims.py src/criba/intelligence/provenance.py src/criba/intelligence/entities` → success.
- `python -m pytest tests/unit/test_blackforge*.py -q -p no:cacheprovider -k 'not emits_report'` → 138 passed, 4 deselected.

## WHAT FEATURE FLAGS ARE ENABLED?
None. All IIE feature flags remain `false`.

## WHAT IS THE NEXT EXACT TASK?
P05-T03: inspect `IntelligenceStore`’s existing schema/API and add a minimal claim-store path with isolated SQLite tests. Do not change legacy CRIBA storage.

## WHAT MODEL/REASONING SHOULD EXECUTE IT?
GPT-5.6 Terra, high reasoning. Required verification: targeted claim-store tests, strict mypy for touched modules, `git diff --check`, then commit.
