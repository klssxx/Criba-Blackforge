# IIE CONTINUITY — CRIBA · BLACKFORGE · SUPRA

**Última actualización:** 2026-09-03 06:20:07+02:00 — P06-T08 VERIFIED

## WHAT IS THE PROJECT?
Preservation-first extension of CRIBA with the additive `src/criba/intelligence/` engine. CRIBA remains the canonical innovation engine; IIE owns external evidence intelligence; BLACKFORGE specializes cyber safety and authorization; SUPRA orchestrates workflows.

## WHAT IS ALREADY DONE? (VERIFIED)
- P00–P04 are committed through `709f16b` (P04 full suite: 733 passed).
- P05 group committed through `6de29de` and `89b0657`: epistemic provenance, deterministic claim extraction, isolated claim persistence, deterministic entity extraction/resolution and aliases.
- Checkpoint tooling committed through `cd95d80`; it distinguishes a metadata-only checkpoint commit from a code divergence.
- P05 targeted verification: `65 passed`; full CRIBA regression: `746 passed`; strict mypy over storage/claims/provenance/entities: success.
- P06-T01 committed in `f8dba0a`: SQLite knowledge graph store with 11 graph/boundary tests; full regression is `753 passed`; mypy is clean.
- P06-T02 committed in `6de1f6e`: deterministic document graph builder with 13 graph/builder/boundary tests; full regression is `755 passed`; mypy is clean.
- P06-T03 committed in `6d8eb3f`: bounded directed graph traversal with 16 graph/builder/traversal/boundary tests; full regression is `758 passed`; mypy is clean.
- P06-T04 committed in `f57038e`: deterministic degree centrality with 18 graph/builder/traversal/centrality/boundary tests; full regression is `760 passed`; mypy is clean.
- P06-T05 committed in `04b31c2`: deterministic weak community detection with 20 graph/builder/traversal/centrality/community/boundary tests; full regression is `762 passed`; mypy is clean.
- P06-T06 committed in `e1e96cf`: iterative articulation-point bridge analysis with 22 graph/builder/traversal/centrality/community/bridge/boundary tests; full regression is `764 passed`; mypy is clean.
- P06-T07 committed in `0266852`: deterministic common-neighbor link prediction interface with 25 graph/builder/traversal/centrality/community/bridge/link-prediction/boundary tests; full regression is `767 passed`; mypy is clean.
- P06-T08 committed in `d2dc31e`: reusable synthetic graph fixtures with 27 graph/builder/traversal/centrality/community/bridge/link-prediction/fixture/boundary tests; full regression is `769 passed`; mypy is clean.
- Legacy BLACKFORGE baseline: 138 targeted tests passed; 4 tracked-artifact emission tests intentionally deselected to avoid overwriting goldens in the live tree.

## WHAT IS CURRENTLY IN PROGRESS?
P05 is closed. P06-T01 through P06-T08 are verified. P06-T09 (graph semantics audit) is **NOT_STARTED**. No code is currently uncommitted; the next task is recorded in `STATE.json`.

## WHAT FAILED?
No runtime failure. The prior state ledger was stale: it omitted P00-T04/P00-GATE, listed P02-T01 both complete and pending, and did not identify the P05 WIP. It is reconciled in `STATE.json` from Git and actual test evidence.

## WHAT IS BLOCKED?
Nothing. BF-P00-T06 is deferred until existing tracked goldens are validated in an isolated copy; do not overwrite them in the live worktree.

## WHAT MUST NOT BE TOUCHED?
`engine.py`, `hybrid.py`, `gates.py`, `blackforge_safety.py`, canonical BLACKFORGE catalog, tracked golden outputs, `criba.sqlite3`, and SUPRA providers are read-only unless a specific approved task requires them.

## WHAT IS THE LAST VERIFIED COMMIT?
`d2dc31e` — P06-T08 reusable synthetic graph fixtures, with graph/builder/traversal/centrality/community/bridge/link-prediction/fixture/boundary tests and full CRIBA regression green.

## WHAT TESTS CURRENTLY PASS?
- `python -m pytest tests/intelligence/test_provenance.py tests/intelligence/test_multi_repo_state.py -q -p no:cacheprovider` → 9 passed.
- `python -m pytest tests/intelligence -q -p no:cacheprovider` → 65 passed.
- `python -m pytest tests/intelligence/test_graph_store.py tests/intelligence/test_graph_builder.py tests/intelligence/test_boundaries.py -q -p no:cacheprovider` → 13 passed.
- `python -m pytest tests/intelligence/test_graph_store.py tests/intelligence/test_graph_builder.py tests/intelligence/test_graph_traversal.py tests/intelligence/test_boundaries.py -q -p no:cacheprovider` → 16 passed.
- `python -m pytest tests/intelligence/test_graph_store.py tests/intelligence/test_graph_builder.py tests/intelligence/test_graph_traversal.py tests/intelligence/test_graph_centrality.py tests/intelligence/test_boundaries.py -q -p no:cacheprovider` → 18 passed.
- `python -m pytest tests/intelligence/test_graph_store.py tests/intelligence/test_graph_builder.py tests/intelligence/test_graph_traversal.py tests/intelligence/test_graph_centrality.py tests/intelligence/test_graph_communities.py tests/intelligence/test_boundaries.py -q -p no:cacheprovider` → 20 passed.
- `python -m pytest tests/intelligence/test_graph_store.py tests/intelligence/test_graph_builder.py tests/intelligence/test_graph_traversal.py tests/intelligence/test_graph_centrality.py tests/intelligence/test_graph_communities.py tests/intelligence/test_graph_bridges.py tests/intelligence/test_boundaries.py -q -p no:cacheprovider` → 22 passed.
- `python -m pytest tests/intelligence/test_graph_store.py tests/intelligence/test_graph_builder.py tests/intelligence/test_graph_traversal.py tests/intelligence/test_graph_centrality.py tests/intelligence/test_graph_communities.py tests/intelligence/test_graph_bridges.py tests/intelligence/test_graph_link_prediction.py tests/intelligence/test_boundaries.py -q -p no:cacheprovider` → 25 passed.
- `python -m pytest tests/intelligence/test_graph_store.py tests/intelligence/test_graph_builder.py tests/intelligence/test_graph_traversal.py tests/intelligence/test_graph_centrality.py tests/intelligence/test_graph_communities.py tests/intelligence/test_graph_bridges.py tests/intelligence/test_graph_link_prediction.py tests/intelligence/test_graph_fixtures.py tests/intelligence/test_boundaries.py -q -p no:cacheprovider` → 27 passed.
- `python -m pytest -q -p no:cacheprovider` → 769 passed, 1 dependency deprecation warning.
- `mypy --no-incremental src/criba/intelligence/claims.py src/criba/intelligence/provenance.py src/criba/intelligence/entities` → success.
- `mypy --no-incremental src/criba/intelligence/storage/store.py src/criba/intelligence/claims.py src/criba/intelligence/provenance.py src/criba/intelligence/entities` → success.
- `mypy --no-incremental src/criba/intelligence/graph/store.py src/criba/intelligence/graph/builder.py src/criba/intelligence/graph/traversal.py src/criba/intelligence/graph/centrality.py src/criba/intelligence/graph/communities.py src/criba/intelligence/graph/bridges.py src/criba/intelligence/graph/link_prediction.py src/criba/intelligence/graph/__init__.py` → success.
- `python -m pytest tests/unit/test_blackforge*.py -q -p no:cacheprovider -k 'not emits_report'` → 138 passed, 4 deselected.

## WHAT FEATURE FLAGS ARE ENABLED?
None. All IIE feature flags remain `false`.

## WHAT IS THE NEXT EXACT TASK?
P06-T09: run graph semantics audit without changing legacy CRIBA storage. BF-P00-T06 remains deferred until tracked BLACKFORGE goldens are validated in an isolated copy.

## WHAT MODEL/REASONING SHOULD EXECUTE IT?
GPT-5.6 Sol xhigh, per blueprint. Required verification: graph semantics audit, targeted graph tests, strict mypy for touched modules, `git diff --check`, full regression, then commit a phase checkpoint if all semantics are coherent.
