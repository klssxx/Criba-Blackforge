# IIE CONTINUITY — CRIBA · BLACKFORGE · SUPRA

**Última actualización:** 2026-09-03 09:46:00+02:00 — P08-T10 VERIFIED; BF-P00-T06 DEFERRED

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
- P06-T09 committed in `2114144`: graph semantics audit and provenance hardening; repeated `source_doc_ids` accumulate and self-loops are excluded from weak metrics; final targeted graph regression is `32 passed`, full regression is `774 passed`; mypy and compileall are clean.
- P07-T01 committed in `b24efbd`: deterministic topic/period observation series plus isolated SQLite persistence; 21 targeted signal/storage/contract tests passed and full regression is `777 passed`; mypy and compileall are clean.
- P07-T02 committed in `594aa56`: discrete topic velocity and acceleration aligned to observation periods; 23 targeted signal/storage/contract tests passed and full regression is `779 passed`; mypy and compileall are clean.
- P07-T03 committed in `1a7063a`: deterministic threshold-based burst detection with period-addressable events; 24 targeted signal/storage/contract tests passed and full regression is `780 passed`; mypy and compileall are clean.
- P07-T04 committed in `62f0c16`: deterministic two-window change-point framework with signed direction and normalized strength; 25 targeted signal/storage/contract tests passed and full regression is `781 passed`; mypy and compileall are clean.
- P07-T05 committed in `ca89e8c`: robust per-topic median/MAD anomaly detection with normalized direction and score; 26 targeted signal/storage/contract tests passed and full regression is `782 passed`; mypy and compileall are clean.
- P07-T06 committed in `7400168`: deterministic weak-signal aggregation with ID deduplication, bounded support combination and provenance union; 27 targeted signal/storage/contract tests passed and full regression is `783 passed`; mypy and compileall are clean.
- P07-T07 committed in `e638dbc`: bounded Pearson lead/lag analysis over overlapping topic periods; 28 targeted signal/storage/contract tests passed and full regression is `784 passed`; mypy and compileall are clean.
- P07-T08 committed in `a4da1e6`: deterministic logistic S-curve approximation with logit linear fit and strict in-asymptote extrapolation; 30 targeted signal/storage/contract tests passed and full regression is `786 passed`; mypy and compileall are clean.
- P07-T09 committed in `4db46bc`: reusable synthetic time-series fixtures (monotonic ramp, lagged ramp, flat control, single-period spike) exercising every signal component; 41 targeted signal/storage/contract tests passed and full regression is `797 passed`; mypy is clean.
- P07-T10 (signal semantics audit): determinism, input-order independence, cross-topic isolation, lead/lag antisymmetry, aggregation provenance and AST import purity verified; 52 targeted signal/storage/contract tests passed and full regression is `808 passed`; mypy and compileall are clean. No semantic defect required implementation changes.
- P08-T01 through P08-T04 are verified: research gaps, limitations, contradictions and failure mining; full CRIBA regression reached `824 passed` before T071.
- P08-T05 committed in `74ea223`: evidence-backed technology resurrection with the complete blueprint contract, structured-metadata and text extraction paths, and 4 focused tests; full regression is `828 passed`; mypy and compileall are clean.
- P08-T06 committed in `60b710f`: deterministic white-space analysis with research/patent/market classification, explicit provenance and 4 focused tests; full regression is `832 passed`; mypy and compileall are clean.
- P08-T07 committed in `a8b84ba`: evidence-gated patent-expiration opportunity contract and extractor, with 4 focused tests; full regression is `836 passed`; mypy and compileall are clean.
- P08-T08 committed in `86fa59c`: dormant-paper candidate contract and deterministic age/low-attention detector, with 4 focused tests; full regression is `840 passed`; mypy and compileall are clean.
- P08-T09 committed in `77e55b1`: sleeping-beauty candidate contract and delayed-attention detector, with 4 focused tests; full regression is `844 passed`; mypy and compileall are clean.
- P08-T10 committed in `0ecc058`: gap-engine audit fixed negated-resolution handling, generic white-space cues, metadata type normalization and duplicate citation-year ordering; 6 audit regressions, 169 intelligence tests and full regression at `851 passed`; mypy, compileall and staged security scan are clean.
- Legacy BLACKFORGE baseline: 138 targeted tests passed; 4 tracked-artifact emission tests intentionally deselected to avoid overwriting goldens in the live tree.

## WHAT IS CURRENTLY IN PROGRESS?
P05, P06, P07 and P08 are closed. P07-T01 through P07-T10 and P08-T01 through P08-T10 are verified. No in-scope code is currently uncommitted; unrelated docs/FINAL_REPORT.md and untracked files are preserved and excluded from commits; the next task is recorded in `STATE.json`.

## WHAT FAILED?
No runtime failure. The prior state ledger was stale: it omitted P00-T04/P00-GATE, listed P02-T01 both complete and pending, and did not identify the P05 WIP. It is reconciled in `STATE.json` from Git and actual test evidence.

## WHAT IS BLOCKED?
Nothing. BF-P00-T06 is deferred until existing tracked goldens are validated in an isolated copy; do not overwrite them in the live worktree.

## WHAT MUST NOT BE TOUCHED?
`engine.py`, `hybrid.py`, `gates.py`, `blackforge_safety.py`, canonical BLACKFORGE catalog, tracked golden outputs, `criba.sqlite3`, and SUPRA providers are read-only unless a specific approved task requires them.

## WHAT IS THE LAST VERIFIED COMMIT?
P08-T10 code verified in `0ecc058`: gap-engine audit fixes, with 6 focused audit tests, 169 intelligence tests, and full CRIBA regression at 851 passed.

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
- `python -m pytest tests/intelligence/test_graph_store.py tests/intelligence/test_graph_builder.py tests/intelligence/test_graph_traversal.py tests/intelligence/test_graph_centrality.py tests/intelligence/test_graph_communities.py tests/intelligence/test_graph_bridges.py tests/intelligence/test_graph_link_prediction.py tests/intelligence/test_graph_fixtures.py tests/intelligence/test_graph_semantics.py tests/intelligence/test_boundaries.py -q -p no:cacheprovider` → 32 passed.
- `python -m pytest -q -p no:cacheprovider` → 774 passed, 1 dependency deprecation warning.
- `python -m pytest tests/intelligence/test_signal_observations.py -q -p no:cacheprovider` → 3 passed.
- `python -m pytest tests/intelligence/test_signal_observations.py tests/intelligence/test_storage.py tests/intelligence/test_contracts.py -q -p no:cacheprovider` → 21 passed.
- `python -m pytest -q -p no:cacheprovider` → 777 passed, 1 dependency deprecation warning.
- `python -m pytest tests/intelligence/test_signal_observations.py -q -p no:cacheprovider` → 5 passed.
- `python -m pytest tests/intelligence/test_signal_observations.py tests/intelligence/test_storage.py tests/intelligence/test_contracts.py -q -p no:cacheprovider` → 23 passed.
- `python -m pytest -q -p no:cacheprovider` → 779 passed, 1 dependency deprecation warning.
- `python -m pytest tests/intelligence/test_signal_bursts.py tests/intelligence/test_signal_observations.py tests/intelligence/test_storage.py tests/intelligence/test_contracts.py -q -p no:cacheprovider` → 24 passed.
- `python -m pytest -q -p no:cacheprovider` → 780 passed, 1 dependency deprecation warning.
- `python -m pytest tests/intelligence/test_signal_changepoints.py tests/intelligence/test_signal_bursts.py tests/intelligence/test_signal_observations.py tests/intelligence/test_storage.py tests/intelligence/test_contracts.py -q -p no:cacheprovider` → 25 passed.
- `python -m pytest -q -p no:cacheprovider` → 781 passed, 1 dependency deprecation warning.
- `python -m pytest tests/intelligence/test_signal_anomaly.py tests/intelligence/test_signal_changepoints.py tests/intelligence/test_signal_bursts.py tests/intelligence/test_signal_observations.py tests/intelligence/test_storage.py tests/intelligence/test_contracts.py -q -p no:cacheprovider` → 26 passed.
- `python -m pytest -q -p no:cacheprovider` → 782 passed, 1 dependency deprecation warning.
- `python -m pytest tests/intelligence/test_signal_weak_signals.py tests/intelligence/test_signal_anomaly.py tests/intelligence/test_signal_changepoints.py tests/intelligence/test_signal_bursts.py tests/intelligence/test_signal_observations.py tests/intelligence/test_storage.py tests/intelligence/test_contracts.py -q -p no:cacheprovider` → 27 passed.
- `python -m pytest -q -p no:cacheprovider` → 783 passed, 1 dependency deprecation warning.
- `python -m pytest tests/intelligence/test_signal_lead_lag.py tests/intelligence/test_signal_weak_signals.py tests/intelligence/test_signal_anomaly.py tests/intelligence/test_signal_changepoints.py tests/intelligence/test_signal_bursts.py tests/intelligence/test_signal_observations.py tests/intelligence/test_storage.py tests/intelligence/test_contracts.py -q -p no:cacheprovider` → 28 passed.
- `python -m pytest -q -p no:cacheprovider` → 784 passed, 1 dependency deprecation warning.
- `python -m pytest tests/intelligence/test_signal_scurve.py tests/intelligence/test_signal_lead_lag.py tests/intelligence/test_signal_weak_signals.py tests/intelligence/test_signal_anomaly.py tests/intelligence/test_signal_changepoints.py tests/intelligence/test_signal_bursts.py tests/intelligence/test_signal_observations.py tests/intelligence/test_storage.py tests/intelligence/test_contracts.py -q -p no:cacheprovider` → 30 passed.
- `python -m pytest tests/intelligence/test_signal_synthetic.py tests/intelligence/test_signal_observations.py tests/intelligence/test_signal_bursts.py tests/intelligence/test_signal_changepoints.py tests/intelligence/test_signal_anomaly.py tests/intelligence/test_signal_weak_signals.py tests/intelligence/test_signal_lead_lag.py tests/intelligence/test_signal_scurve.py tests/intelligence/test_storage.py tests/intelligence/test_contracts.py -q -p no:cacheprovider` → 41 passed.
- `python -m pytest -q -p no:cacheprovider` → 797 passed, 1 dependency deprecation warning.
- `python -m pytest tests/intelligence/test_signal_semantics.py tests/intelligence/test_signal_synthetic.py tests/intelligence/test_signal_observations.py tests/intelligence/test_signal_bursts.py tests/intelligence/test_signal_changepoints.py tests/intelligence/test_signal_anomaly.py tests/intelligence/test_signal_weak_signals.py tests/intelligence/test_signal_lead_lag.py tests/intelligence/test_signal_scurve.py tests/intelligence/test_storage.py tests/intelligence/test_contracts.py -q -p no:cacheprovider` → 52 passed.
- `python -m pytest -q -p no:cacheprovider` → 808 passed, 1 dependency deprecation warning.
- `python -m pytest tests/intelligence/test_failures.py -q -p no:cacheprovider` → 5 passed.
- `python -m pytest tests/intelligence/test_failures.py tests/intelligence/test_gaps.py tests/intelligence/test_limitations.py tests/intelligence/test_contradictions.py -q -p no:cacheprovider` → 16 passed.
- `mypy --no-incremental src/criba/intelligence/gaps` → success.
- `python -m compileall -q src/criba/intelligence/gaps` → success.
- `python -m pytest -q -p no:cacheprovider` → 824 passed, 1 dependency deprecation warning.
- `python -m pytest tests/intelligence/test_resurrection.py -q -p no:cacheprovider` → 4 passed.
- `python -m pytest tests/intelligence/test_resurrection.py tests/intelligence/test_gaps.py tests/intelligence/test_limitations.py tests/intelligence/test_contradictions.py tests/intelligence/test_contracts.py -q -p no:cacheprovider` → 22 passed.
- `mypy --no-incremental src/criba/intelligence/gaps src/criba/intelligence/contracts.py` → success.
- `python -m compileall -q src/criba/intelligence/gaps src/criba/intelligence/contracts.py` → success.
- `python -m pytest -q -p no:cacheprovider` → 828 passed, 1 dependency deprecation warning.
- `python -m pytest tests/intelligence/test_white_space.py -q -p no:cacheprovider` → 4 passed.
- `python -m pytest tests/intelligence/test_white_space.py tests/intelligence/test_resurrection.py tests/intelligence/test_failures.py tests/intelligence/test_gaps.py tests/intelligence/test_limitations.py tests/intelligence/test_contradictions.py tests/intelligence/test_contracts.py -q -p no:cacheprovider` → 31 passed.
- `mypy --no-incremental src/criba/intelligence/gaps src/criba/intelligence/contracts.py` → success.
- `python -m compileall -q src/criba/intelligence/gaps src/criba/intelligence/contracts.py` → success.
- `python -m pytest -q -p no:cacheprovider` → 832 passed, 1 dependency deprecation warning.
- `python -m pytest tests/intelligence/test_patent_expiration.py -q -p no:cacheprovider` → 4 passed.
- `python -m pytest tests/intelligence/test_patent_expiration.py tests/intelligence/test_contracts.py tests/intelligence/test_white_space.py tests/intelligence/test_resurrection.py -q -p no:cacheprovider` → 19 passed.
- `python -m pytest tests/intelligence/test_patent_expiration.py tests/intelligence/test_white_space.py tests/intelligence/test_resurrection.py tests/intelligence/test_failures.py tests/intelligence/test_gaps.py tests/intelligence/test_limitations.py tests/intelligence/test_contradictions.py tests/intelligence/test_contracts.py -q -p no:cacheprovider` → 35 passed.
- `mypy --no-incremental src/criba/intelligence/gaps src/criba/intelligence/contracts.py` → success.
- `python -m compileall -q src/criba/intelligence/gaps src/criba/intelligence/contracts.py` → success.
- `python -m pytest -q -p no:cacheprovider` → 836 passed, 1 dependency deprecation warning.
- `python -m pytest tests/intelligence/test_dormant.py -q -p no:cacheprovider` → 4 passed.
- `python -m pytest tests/intelligence/test_dormant.py tests/intelligence/test_patent_expiration.py tests/intelligence/test_white_space.py tests/intelligence/test_resurrection.py tests/intelligence/test_failures.py tests/intelligence/test_gaps.py tests/intelligence/test_limitations.py tests/intelligence/test_contradictions.py tests/intelligence/test_contracts.py -q -p no:cacheprovider` → 39 passed.
- `mypy --no-incremental src/criba/intelligence/gaps src/criba/intelligence/contracts.py` → success.
- `python -m compileall -q src/criba/intelligence/gaps src/criba/intelligence/contracts.py` → success.
- `python -m pytest -q -p no:cacheprovider` → 840 passed, 1 dependency deprecation warning.
- `python -m pytest tests/intelligence/test_sleeping_beauty.py -q -p no:cacheprovider` → 4 passed.
- `python -m pytest tests/intelligence/test_sleeping_beauty.py tests/intelligence/test_dormant.py tests/intelligence/test_patent_expiration.py tests/intelligence/test_white_space.py tests/intelligence/test_resurrection.py tests/intelligence/test_failures.py tests/intelligence/test_gaps.py tests/intelligence/test_limitations.py tests/intelligence/test_contradictions.py tests/intelligence/test_contracts.py -q -p no:cacheprovider` → 43 passed.
- `mypy --no-incremental src/criba/intelligence/gaps src/criba/intelligence/contracts.py` → success.
- `python -m compileall -q src/criba/intelligence/gaps src/criba/intelligence/contracts.py` → success.
- `python -m pytest -q -p no:cacheprovider` → 844 passed, 1 dependency deprecation warning.
- `python -m pytest tests/intelligence/test_gap_audit.py -q -p no:cacheprovider` → 6 passed.
- `python -m pytest tests/intelligence/test_gap_audit.py tests/intelligence/test_gaps.py tests/intelligence/test_limitations.py tests/intelligence/test_white_space.py -q -p no:cacheprovider` → 19 passed.
- `python -m pytest tests/intelligence -q -p no:cacheprovider` → 169 passed.
- `mypy --no-incremental src/criba/intelligence/gaps src/criba/intelligence/contracts.py` → success.
- `python -m compileall -q src/criba/intelligence/gaps src/criba/intelligence/contracts.py` → success.
- staged added-line security scan → no hardcoded secrets, shell execution, eval/exec, pickle or SQL-format findings.
- `python -m pytest -q -p no:cacheprovider` → 851 passed, 1 dependency deprecation warning.
- `mypy --no-incremental src/criba/intelligence/claims.py src/criba/intelligence/provenance.py src/criba/intelligence/entities` → success.
- `mypy --no-incremental src/criba/intelligence/storage/store.py src/criba/intelligence/claims.py src/criba/intelligence/provenance.py src/criba/intelligence/entities` → success.
- `mypy --no-incremental src/criba/intelligence/graph/store.py src/criba/intelligence/graph/builder.py src/criba/intelligence/graph/traversal.py src/criba/intelligence/graph/centrality.py src/criba/intelligence/graph/communities.py src/criba/intelligence/graph/bridges.py src/criba/intelligence/graph/link_prediction.py src/criba/intelligence/graph/__init__.py` → success.
- `python -m pytest tests/unit/test_blackforge*.py -q -p no:cacheprovider -k 'not emits_report'` → 138 passed, 4 deselected.

## WHAT FEATURE FLAGS ARE ENABLED?
None. All IIE feature flags remain `false`.

## NEON ADDENDUM — ACTIVE CONSTRAINT
The Neon steering directive is recorded as a cross-cutting architecture addendum, not as a signal-layer dependency. Before any provider implementation: audit the existing persistence/configuration boundary; keep PostgreSQL as the standard contract; isolate Neon-specific code under infrastructure/adapters; never write to Neon `production`; do not expose connection strings; and stop only billable, admin, destructive, production-write or authentication-gated actions for explicit user approval. Local PostgreSQL portability remains mandatory.

## WHAT IS THE NEXT EXACT TASK?
BF-P00-T06 remains deferred until tracked BLACKFORGE goldens are validated in an isolated copy. Do not start BF-P01 or overwrite live goldens.

## WHAT MODEL/REASONING SHOULD EXECUTE IT?
No model execution is needed for the checkpoint. If BF-P00-T06 is resumed, use its existing isolated-golden validation protocol; do not modify tracked BLACKFORGE goldens in the live tree.
