# Changelog

All notable changes to this project are documented here.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added
- **Meta-level methodology libraries**: 11 new sources with 235 items total:
  - Innovation Frameworks (35): Design Thinking, JTBD, Blue Ocean, FMEA, etc.
  - Security Frameworks (15): MITRE ATT&CK, OWASP, STRIDE, Kill Chain, etc.
  - Pentest Methodologies (12): PTES, OSSTMM, OWASP Testing, etc.
  - Red Team Playbooks (11): Red Team Ops, Purple Team, Atomic Red Team, etc.
  - Incident Response (11): NIST IR, SANS, Forensics, etc.
  - Decision Frameworks (14): RICE, Weighted Scoring, Delphi, Six Hats, etc.
  - Research Taxonomies (20): Experimental, Grounded Theory, Ethnography, etc.
  - IDEO Method Cards (51): 51 design research methods (Ask/Look/Learn/Try)
  - Liberating Structures (25): 1-2-4-All, 9 Whys, Fishbowl, etc.
  - Brainstorming Techniques (22): Brainwriting, SCAMPER, Synectics, Crazy 8s, etc.
  - Gamestorming (19): Anti-Problem, Dot Voting, Mind Map, etc.
- **Enriched schema**: granularity, categories, tags, origin, normalized_mechanism,
  related_internal_ids, relationship_type for all 4002 methods.
- **New catalog functions**: `frameworks()`, `facilitation_patterns()`, `group_games()`,
  `methods_by_source()`, `methods_by_granularity()`.
- **Equivalence mapping**: 121 items with detected equivalences between frameworks
  and micro-techniques (TRIZ↔rupture, SCAMPER↔inversion, etc.)
- **Ontology**: `data/schemas/ontology.json` with categories, granularities, and
  relationship types.
- Integrated 5 methodology catalogs from `imports/ee/` expanding the methods library
  from 66 to 3767 methods across 28 families. Sources: 800 disruptive methods,
  1000 frame-breaking techniques, 800 jump techniques, 1700 viewpoints, and
  600 advanced lenses. (`feat: integrate ee methodology catalogs`)
- New documentation: `docs/METHODS_INTEGRATION.md` with full integration details.
- Utility scripts: `scripts/parse_ee_catalogs_v2.py`, `scripts/merge_libraries.py`,
  `scripts/regenerate_golden.py`, `scripts/merge_libraries_v3.py`,
  `scripts/verify_library.py` for catalog management.
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
