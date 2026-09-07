# Changelog

All notable changes to this project are documented here.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added (2026-09-07 — consolidación y bloque bloqueo→desbloqueo)
- **Diversity-aware finalist selection** (MMR local, pesos centralizados):
  el flujo de invención ya no depende del top-N por score. PRE/POST en
  fixtures: duplication_rate 1.0→0.0, mecanismos únicos 1→3.
- **Ficha de bloqueo** (`criba.bloqueo`): resultado buscado, bloqueo con
  origen declarado (hecho/hipótesis/pendiente), rutas de desbloqueo
  (eliminar_necesidad | sustituir_mecanismo | desacoplar_dependencia).
- **Dossier SUPRA** (`criba.supra_dossier`): prueba discriminante con
  estado `SUPRA_EJECUCION_PENDIENTE` (nunca PASS); `inventar --dossier`
  y botón GUI «Desarrollar con SUPRA»; `registrar_resultado` +
  `lecciones_previas` cierran el circuito de aprendizaje.
- **Evidence consumida**: la evidencia local del almacén se entrega en la
  solicitud real al intérprete; CLI conecta el almacén por defecto.
- **Seeds y memoria**: seeds generadas con `secrets.randbits(64)`,
  `run_id` independiente, historial conectado con cooldown por
  decaimiento (sin bans permanentes).
- **Actualizar fuentes REAL** con dedupe por contenido (CH1–CH7) y
  perfil BLACKFORGE (CISA KEV + MITRE ATT&CK STIX).
- **Harness benchmark v0** (A_DIRECT/B_STRONG_PROMPT/C_CRIBA, dataset
  humo 10 problemas, export JSON, 0 llamadas).
- Acción GUI «Inventar» (mismo servicio que la CLI) y guard de
  conmutación con trabajo en curso; módulo `criba.blackforge_gui`.
- Tres ejemplos completos en `docs/ejemplos/` (general, proceso,
  BLACKFORGE).

### Fixed (2026-09-07)
- content_hash separado de identidad documental (abstract/fragmentos
  modificados → `modificados`, no duplicados).
- IDs estables sha256 (fin de `hash()`); offline bloquea la red en el
  transporte común (incluido el proponente con credenciales presentes).
- Módulo de arranque ausente `criba.blackforge_gui` (defecto de
  desarrollo y packaging).
- Botón «Actualizar fuentes» ya no calcula porcentajes sintéticos.
- Conmutación CRIBA→BLACKFORGE retiene el cambio con workers vivos.
- Typo `verdicto`→`veredicto` en CloudInterprete; negación léxica por
  token en el detector (sin falsos positivos de subcadena); mecanismo
  interpretado sin truncar a 200 chars; revisiones auditadas con
  llamadas contadas.

### Added (2026-09-07 — router del canon T001–T130)
- **Trazabilidad v2 del registro de técnicas**: `technique_registry.yaml`
  (regenerado por `gen_registry.py`) lleva `schema_version`, `canon_version`
  y `provenance` (fuente ADDENDUM s87–94, generador, partes) legibles por
  máquina; `TechniqueRegistry` acepta el esquema v2 y el formato plano
  legado, y `validate()` exige la trazabilidad en v2.
- **Router del canon** (`criba.intelligence.router`): selecciona el
  subconjunto mínimo relevante de T001–T130 para una tarea — determinista,
  offline, sin ejecutar nada. Solo técnicas IMPLEMENTED son candidatos de
  ejecución; las PLANNED relevantes aparecen como brechas honestas (nunca
  como capacidad). Puente léxico ES→EN acotado al vocabulario del canon,
  diversidad funcional por familia y supresión de redundancia
  (mismo módulo + pipeline). El resultado arrastra `canon_version` y
  `procedencia` del canon consumido.
- **CLI `criba tecnicas "<tarea>"`**: acceso de solo lectura al router
  (`--perfil CRIBA|BLACKFORGE`, `--max`, `--max-por-familia`, `--con-red`).

### Fixed (2026-09-07 — auditoría qa-win del bloque router)
- El registro v2 con `provenance` incompleto o vacío ahora falla EN CARGA
  (no solo en `validate()`); entradas corruptas de `techniques` (no-mapping,
  sin id, `model` no-mapping) producen `ValueError` claro → el CLI responde
  `Error: ...` + exit 2 sin traceback.
- El truncado del motivo «coincide:…» respeta fronteras de token (sin coma
  colgante ni tokens cortados).
- `tecnicas --max/--max-por-familia` < 1 → error controlado (exit 2), antes
  se aceptaban en silencio.
- Gate de credenciales del router con test de regresión (par sintético
  T900/T901).
- `gen_registry.py` escribe el destino relativo a su BASE (fin de ruta
  absoluta hardcodeada); regeneración idempotente byte a byte re-verificada.

### Changed
- README/README.es provider-neutral; cifra de tests verificada.
- SUPRA retirado de la verificación de entorno; inventario en
  `docs/SUPRA_INVENTORY.md`.
- Lote parches SAFE de dependencias (auditoría OSS sin CVEs): pydantic
  2.13.5, fastapi 0.141.1, uvicorn 0.52.4, mypy 2.3.1, ruff 0.16.6,
  semgrep 1.176.1, types-PyYAML, hypothesis 6.167.1.
- PySide6 6.11.2 + PyInstaller 6.22.2 (hardening del bootloader
  GHSA-9fxf-4qw3-ghmr): portable reconstruido y verificado (exes
  offscreen exit 0, canon v2 dentro del bundle).

### Removed
- `.pytest_tmp2/` (130 artefactos temporales subidos por accidente en
  80362fa); `.gitignore` generalizado a `.pytest_tmp*/`.

## [Unreleased]

### Added
- **Public launch productization**: distribution renamed to `criba` (PyPI-ready,
  `pip install criba`), package metadata with license/classifiers/URLs, and ship the
  `data/` catalog in the wheel as a namespace package so installed copies work out of
  the box (data resolution now falls back to site-packages and user-local SQLite).
- Bilingual public README: `README.md` (English, canonical) and `README.es.md`
  (Spanish); removed the old minimal `README.en.md`/`README_MVP.md`.
- `examples/getting_started.py` and `examples/notebooks/reproducible_ideation.ipynb`:
  a 60-second reproducible demo (same seed, same ideas, 0€, offline).
- Community scaffolding: bug/feature issue templates, PR template, `CONTRIBUTING.md`,
  `SECURITY.md`, `CODE_OF_CONDUCT.md`.
- Apache-2.0 `LICENSE` text aligned with the declared license.

- Canonical `uv 0.11.28` project management for CRIBA and its BLACKFORGE runtime:
  dependencies and audit tools are declared in `pyproject.toml`, resolved in
  `uv.lock`, and installed with `uv sync --all-extras --locked`.
- SUPRA now follows the same contract with its own checked-in `uv.lock`.
- CI uses `astral-sh/setup-uv` v9.0.0 pinned to commit
  `c771a70e6277c0a99b617c7a806ffedaca235ff9`; cache pruning is explicit and
  keyed by `uv.lock`.
- Ruff, mypy, pip-audit, Bandit, Semgrep, pre-commit, and CycloneDX are declared
  in the project development extras instead of being installed ad hoc.

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
