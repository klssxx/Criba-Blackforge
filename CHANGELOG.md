# Changelog

All notable changes to this project are documented here.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added
- Explicit `value_score(evidence, novelty, cost)` public function with a
  `ValueScoreError` contract: rejects `cost <= 0`, non-finite inputs and
  non-numeric types instead of silently returning `0.0`. The ratified formula
  `evidence * novelty / cost` is unchanged. (`fix: enforce value_score cost>0 contract`)
- Branch-coverage test suites for the engine decision boundaries, BLACKFORGE
  safety/selector, and the causal validation/rejection paths. Global branch
  coverage 73% → 77%; priority modules: engine 95%, safety 99%, selector 93%,
  causal 84%, pipeline 97%.
- Pre-hardening baseline evidence (`verification/baseline_fase0.json`) and
  FASE 1 coverage report (`verification/coverage_fase1.json`).

### Fixed
- BLACKFORGE S3 safety denial now surfaces an unconfirmed `authorized_scope`
  in `unmet_requirements`; previously it was appended to a local list that was
  never returned, hiding the precise blocker from callers.

### Security
- Reaffirmed that `recommended_status` stays within `VALID_DECISIONS` and never
  becomes `ADOPTAR` solely from the number of idea families; `pipeline_action`
  (`PROTOTIPAR`/`DIVERGIR`) is a separate, non-business dimension (alternativa C).

## 0.1.0

- Initial local CRIBA engine: deterministic selector, packet generation,
  SQLite evidence store, CLI, local API, MCP stdio server and optional GUI.
