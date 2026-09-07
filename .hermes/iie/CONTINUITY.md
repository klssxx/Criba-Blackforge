# IIE CONTINUITY — CRIBA · BLACKFORGE · SUPRA

**Última actualización:** 2026-09-05 00:28:47+02:00 — P10-T01..T06 COMMITTED/VERIFIED; P10-T07 PARTIAL con contrato local GREEN; P10-T08 Skeptic VERIFIED sin commit; P10-T09 verdict engine pendiente; HIGH_REVIEW/SECOND_PASS abierto; BF-P00-T06 DEFERRED

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
- P08-T10 corrective commit `e863b58`: independent review caught the remaining `but`/`yet`/`however` conjoined-resolution ambiguity; the guard and regression coverage were expanded to `and`/`but`/`yet`/`however`; focused and full suites remained green.
- P09-T01 through P09-T18 closed in atomic commits through `937f150`: additive invention taxonomy/registry, corpus-bounded and evidence-bounded hypothesis operators, generator-backed technique registry reconciliation, and an architecture audit. P09 full regression is `903 passed, 1 warning`; mypy is clean in 127 source files and compileall is clean.
- P10-T01 (adversarial prior-art protocol), P10-T02 (deterministic query lattice), P10-T03 (Google Patents-backed PatentScout), P10-T04 (OpenAlex ScienceScout), P10-T05 (GitHub CodeScout) and P10-T06 (Wikipedia ProductScout) are committed and journaled through `10e1dcc`. Their focused tests and bounded source probes are evidence of normalization only; they do not establish novelty, patentability, originality or market conclusions.
- P10-T07 CrossDomainScout remains PARTIAL in the current dirty tree: the contract ADR defines evidence-only cross-domain collection (not semantic analogy generation), unique source IDs, shared transport budget, stable ordering, partial failures and fail-closed downstream handoff. Its local contract remains GREEN, but end-to-end closure depends on the P10-T09 verdict engine.
- P10-T08 PriorArtSkeptic is VERIFIED in the current dirty tree: it performs deterministic evidence-coverage/provenance review, returns a JSON-safe Mapping-compatible adversarial report and integrates with the real T07 handoff guard. RED covered module/export absence, malformed documents and missing provenance; GREEN is 6 focused tests, 37 directed P10/boundary tests and a current full CRIBA regression at `940 passed, 1 warning`. It is not a final prior-art verdict.
- P09 leaves T054/T056/T058/T061/T066/T067 as `PLANNED`; it does not claim their implementation. T063 consumes already-retrieved documents; P12 owns feature-flagged CRIBA application integration.
- Legacy BLACKFORGE baseline: 138 targeted tests passed; 4 tracked-artifact emission tests intentionally deselected to avoid overwriting goldens in the live tree.

## WHAT IS CURRENTLY IN PROGRESS?
P05–P09 are closed. P10-T01 through P10-T06 are committed and verified by their task journals. P10-T07 remains PARTIAL and uncommitted: its evidence contract, negative tests, shared budget, stable order and partial-failure handling are GREEN. P10-T08 is VERIFIED and uncommitted, supplying the real Skeptic contract; P10-T09 is still absent, so the final handoff cannot yet be proven. The migration/cutover claims remain historical evidence; current CRIBA and SUPRA trees are dirty and must not be cleaned blindly.

## WHAT FAILED?
No unresolved runtime failure in this pass. The intentional TDD RED produced 12 expected contract-test failures before the main production change, followed by 2 expected failures for later budget-state guards; all 14 are now GREEN. The current focused suite and full regression pass. P10-T07 remains open only because passing the local boundary does not prove true semantic analogy generation or end-to-end Skeptic/verdict integration.

## WHAT IS BLOCKED?
P10-T07 remains blocked for closure, not for local execution: P10-T08 Skeptic now exists, but P10-T09 verdict engine is still absent and the full handoff cannot be exercised. BF-P00-T06 is independently deferred until tracked BLACKFORGE goldens are validated in an isolated copy; do not overwrite them in the live worktree.

## WHAT MUST NOT BE TOUCHED?
`engine.py`, `hybrid.py`, `gates.py`, `blackforge_safety.py`, canonical BLACKFORGE catalog, tracked golden outputs, `criba.sqlite3`, and SUPRA providers are read-only unless a specific approved task requires them.

## WHAT IS THE LAST VERIFIED COMMIT?
Last committed verified point: P10-T06 in `10e1dcc`, with its 3 focused ProductScout tests recorded in the journal. P10-T07 and P10-T08 are newer only in the dirty working tree. T07 is `PARTIAL`; T08 is `VERIFIED` locally with 6 focused tests, 37 directed tests and a 940-test regression, but neither is a commit-bound release gate. P10-T09 is still required for downstream integration proof.

## WHAT TESTS CURRENTLY PASS?
- `uv run --locked pytest -q tests/intelligence/test_invention_taxonomy.py tests/intelligence/test_invention_registry.py tests/intelligence/test_technique_registry.py tests/intelligence/test_triz.py` → 49 passed.
- `uv run --locked pytest -q --no-header` → 903 passed, 1 Starlette/httpx deprecation warning.
- `uv run --locked mypy src/criba` → success in 127 source files.
- `uv run --locked python -m compileall -q src` → success.
- `python -m pytest tests/intelligence/test_provenance.py tests/intelligence/test_multi_repo_state.py -q -p no:cacheprovider` → 9 passed.
- `uv run --locked pytest -q -p no:cacheprovider tests/intelligence/test_patent_scout.py tests/intelligence/test_sources.py` → 21 passed.
- `LOCALAPPDATA=C:/Users/KLSX/Music/INNOVATIONS/RUNTIME_STATE uv run --locked pytest -q -p no:cacheprovider` → 908 passed, 1 dependency deprecation warning.
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
- direct tempfile-backed conjunction probe → direct negation retained; `and`/`but`/`yet`/`however` conjoined resolutions excluded; `TEMPFILE_REMOVED=True`.
- independent focused review → `passed=true`, no security concerns, no logic errors; test coverage adequate. Reviewer did not re-run the full suite; local full-suite evidence above was rerun after the corrective patch.
- `mypy --no-incremental src/criba/intelligence/claims.py src/criba/intelligence/provenance.py src/criba/intelligence/entities` → success.
- `mypy --no-incremental src/criba/intelligence/storage/store.py src/criba/intelligence/claims.py src/criba/intelligence/provenance.py src/criba/intelligence/entities` → success.
- `mypy --no-incremental src/criba/intelligence/graph/store.py src/criba/intelligence/graph/builder.py src/criba/intelligence/graph/traversal.py src/criba/intelligence/graph/centrality.py src/criba/intelligence/graph/communities.py src/criba/intelligence/graph/bridges.py src/criba/intelligence/graph/link_prediction.py src/criba/intelligence/graph/__init__.py` → success.
- `python -m pytest tests/unit/test_blackforge*.py -q -p no:cacheprovider -k 'not emits_report'` → 138 passed, 4 deselected.
- `LOCALAPPDATA=C:/Users/KLSX/Music/INNOVATIONS/RUNTIME_STATE uv run --locked pytest -q -p no:cacheprovider tests/intelligence/test_cross_domain_scout.py` → 17 passed after intentional RED of 12 initial failures plus 2 incremental failures.
- `LOCALAPPDATA=C:/Users/KLSX/Music/INNOVATIONS/RUNTIME_STATE uv run --locked pytest -q -p no:cacheprovider tests/intelligence/test_prior_art_skeptic.py` → 6 passed after expected RED for the missing module/export, malformed document and missing provenance.
- `LOCALAPPDATA=C:/Users/KLSX/Music/INNOVATIONS/RUNTIME_STATE uv run --locked pytest -q -p no:cacheprovider tests/intelligence/test_prior_art_skeptic.py tests/intelligence/test_cross_domain_scout.py tests/intelligence/test_prior_art_protocol.py tests/intelligence/test_contracts.py tests/intelligence/test_boundaries.py` → 37 passed.
- `LOCALAPPDATA=C:/Users/KLSX/Music/INNOVATIONS/RUNTIME_STATE uv run --locked --all-extras pytest -q -p no:cacheprovider` → 940 passed, 1 dependency deprecation warning.
- `uv run --locked ruff check src/criba/intelligence/prior_art/skeptic.py src/criba/intelligence/prior_art/__init__.py tests/intelligence/test_prior_art_skeptic.py` → All checks passed; mypy and compileall also passed.

## WHAT FEATURE FLAGS ARE ENABLED?
None. All IIE feature flags remain `false`.

## NEON ADDENDUM — ACTIVE CONSTRAINT
The Neon steering directive is recorded as a cross-cutting architecture addendum, not as a signal-layer dependency. Before any provider implementation: audit the existing persistence/configuration boundary; keep PostgreSQL as the standard contract; isolate Neon-specific code under infrastructure/adapters; never write to Neon `production`; do not expose connection strings; and stop only billable, admin, destructive, production-write or authentication-gated actions for explicit user approval. Local PostgreSQL portability remains mandatory.

## HIGH_REVIEW / SECOND_PASS
- **P10-T07 — OPEN / Terra high:** the local evidence contract is defined in `docs/architecture/adr/ADR-P10-T07-cross-domain-contract.md` and covered by negative tests for same-domain input, duplicate IDs, global budget exhaustion, ordering and partial failures. It now hands off to the real P10-T08 Skeptic contract, but still does not generate semantic analogy records or final verdicts.
- **P10-T09 — NOT_STARTED / Terra high:** P10-T08 is verified, but the verdict engine is absent. Its end-to-end integration with T07/T08 remains the explicit P10-T07 closure blocker.

## POST-CUTOVER CLEANUP
- `MIGRATION_STATUS=PARTIAL`; `POST_CUTOVER_CLEANUP=PARTIAL`; canonical root: `C:\Users\KLSX\Music\INNOVATIONS`.
- Current session verified only that `E:\PROYECTS\CRIBA` and `E:\PROYECTS\SUPRA` are absent. Prior model/GGUF, smoke and operational-scan claims remain historical evidence and are not a fresh cutover gate.
- No model, worktree, legacy, quarantine or external-data path was deleted in this continuation.
- `ARCHIVE\CRIBABLACKFORGE_LEGACY_BACKUP\.git` remains intentionally preserved as archive metadata, outside `ACTIVE`/`WORKTREES`; its retirement requires a separate review.

## WHAT IS THE NEXT EXACT TASK?
`P10-T09 — verdict engine`: definir y probar una decisión determinista que consuma `PriorArtSkepticReport` y `SourceQueryResult`, emita exclusivamente los valores existentes de `PriorArtVerdict` y nunca infiera `PROVEN_NEW`. Después, ejecutar el handoff completo `CrossDomainScout -> PriorArtSkeptic -> verdict` y reevaluar P10-T07. No iniciar BF-P01, migración/GGUF ni sobrescribir goldens vivos.

## WHAT MODEL/REASONING SHOULD EXECUTE IT?
P10-T07 remains a high-reasoning architecture boundary. The local evidence/budget/order/failure contract is now fixed and tested; any future downstream integration must use the real Skeptic/verdict interfaces and be separately authorized. If BF-P00-T06 is resumed, use its isolated-golden validation protocol; do not modify tracked BLACKFORGE goldens in the live tree.
