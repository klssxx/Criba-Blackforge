# Changelog

All notable changes to this project are documented here.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.3.0] - 2026-09-10

### Added (2026-09-08 — restauración selectiva cbac469, slice 3)
- **`graph/` restaurado** (8 módulos + 8 suites, 26 tests verdes sin
  cambios). Canon `2026-09-08.3`: **29 IMPLEMENTED** (+T091 link
  prediction, T094 comunidades, T095 bridge-nodes). §78: el graph store se
  apoya en IntelligenceStore — sin almacenamiento paralelo. §80 estricto:
  T092 PLANNED (monocultivo con T091), T093 PLANNED (embeddings nunca
  existió — GAP canónico), T040–T045 PLANNED (infraestructura sin lógica
  específica). Positivo semántico en tests: línea a-b-c → b articulación,
  ciclo → vacío.

### Added (2026-09-08 — restauración selectiva cbac469, slice 2)
- **`gaps/`, `signals/`, `entities/`, `provenance`, `claims` restaurados**
  (~2.900 LOC + ~1.100 de tests, 85 tests históricos verdes contra
  contratos vivos sin cambios). Canon `2026-09-08.2`: **26 IMPLEMENTED**
  (las 11 del slice 1 + 15 nuevas: T019/T048/T049 dinámica de temas,
  T067–T071 minería de contradicciones/gaps/limitaciones/fallos/resurrección,
  T086 white-spaces, T096–T099 detección de bursts/cambios/anomalías/señales
  débiles, T101 lead-lag, T128 expiración+dormant+sleeping-beauty+resurrection
  compuesta). Mapeo §80 por función real: T047 (emergentes) y T087–T089
  (white-spaces por tipo) quedan PLANNED con gap documentado (el módulo no
  distingue esas capacidades). Ejecutables desde el producto con los mismos
  guardrails (`--ejecutar` + `--entrada` con observaciones/señales o
  `--desde-almacen`); 16 tests de cadena nuevos.

### Added (2026-09-08 — restauración selectiva cbac469, slice 1)
- **Operadores `invention/` restaurados** (16 módulos + 3 suites de tests
  históricos, ~1.100 LOC) desde `cbac469~1` bajo la CBAC469 Recovery
  Constitution §74–§85: recuperación selectiva por capacidad, no revert
  global. Canon `2026-09-08.1`: las 11 técnicas (T053/T055/T057/T059/T060/
  T062–T065/T116/T129) vuelven a IMPLEMENTED tras la secuencia §79 completa:
  capability proof (tests históricos verdes contra contratos vivos), §78
  (`invention/registry`+`taxonomy` auditados como dispatch puro — nunca
  canon paralelo), §82 (test de cadena canon→router→resolver→operador→
  salida contractual + negativos), promoción solo vía generador canónico.
- **`docs/recovery/CBAC469_AUDIT.md`**: triage del 100% de los 93 paths
  borrados por cbac469 con matriz de decisiones (gaps/signals/graph/
  entities/provenance DEFER slices 2–3 con condiciones de reapertura;
  stubs KEEP_DELETED_DEAD con NEGATIVE_KNOWLEDGE).
- **`.hermes/iie/assurance_ledger.json`**: ledger append-only de assurance
  (local/premise/effective, attestation A2 por CI objetivo, premises
  críticas certificadas, eventos de época canónica .1→.2→.3, estados
  runtime SHADOW — A2 no autoriza más).
- **Ejecución de técnicas desde el producto** (`criba.intelligence.execution`
  + `criba tecnicas --ejecutar TXXX`): resolver runtime canon→operador con
  adaptadores por input_contracts y guardrails (PLANNED/desconocida/creds →
  error controlado; el canon decide ejecutabilidad). Evidencia por
  `--entrada docs.json` o `--desde-almacen`. Cierra la cadena §82 de forma
  accesible E2E; tabla de verificación por técnica en
  `docs/recovery/CBAC469_AUDIT.md`.

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

### Fixed (2026-09-07 — atribución del historial de dossiers)
- **Un resultado positivo antiguo podía atribuirse a un mecanismo nuevo**:
  el ID del dossier se derivaba del candidate_id (se repetía) y la lectura
  del historial retenía la última versión del contenido. `supra_dossier.py`:
  cada preparación recibe un UUID propio; un ID guardado no admite cambios
  de contenido (solo reexportación idéntica, idempotente); registrar un
  resultado exige un dossier existente y no ambiguo; el historial antiguo
  con contenidos distintos bajo un mismo ID queda excluido del aprendizaje
  con `RuntimeWarning` (archivos intactos); referencias huérfanas omitidas.
  11 regresiones nuevas (`test_dossier_integrity.py`). Parche externo
  aislado (base `2f46d37`), integrado con normalización CRLF→LF y una
  anotación de tipos para mypy estricto.

### Fixed (2026-09-08 — frontera abierta del parche de dossiers)
- **Inversión de actores no se clasifica como duplicado**: con vocabulario
  idéntico, solo una secuencia idéntica es paráfrasis segura; un reorden
  distinto (p. ej. «el banco concede crédito al cliente» vs «el cliente… al
  banco» con prefijo compartido) es UNKNOWN — antes podía marcarse DUPLICATE
  y descartarse un mecanismo genuino.
- **Las entries arrastran `run_id`** y el **ledger conserva los campos de la
  propuesta** (hipótesis, prueba concreta, ruta de desbloqueo, supuestos,
  estado de antecedentes, clases): el historial append-only basta para
  reconstruir el porqué de cada candidato y la trazabilidad dossier→run.
- **La GUI «Inventar» entrega el almacén de evidencia** (`store=
  default_store()`), igual que la CLI — la interpretación desde la interfaz
  ya no pierde la evidencia local.

### Fixed (2026-09-07 — integridad del registro de técnicas, P0)
- **El registro declaraba 11 técnicas IMPLEMENTED sobre código eliminado**:
  el commit cbac469 (cirugía ~5.1k líneas, 2026-09-05) retiró los módulos
  `intelligence/invention/*` y sus tests, pero `technique_registry.yaml`
  siguió marcando T053/T055/T057/T059/T060/T062–T065/T116/T129 como
  IMPLEMENTED con `implementation` apuntando a módulos borrados — el router
  las ofrecía como `executable: true`. Corrección: vuelven a PLANNED
  (canon `2026-09-07.2`, regenerado; 0 IMPLEMENTED hasta re-implementación
  real). Guard nuevo (`test_technique_runtime_traceability.py`): toda
  IMPLEMENTED debe importar de verdad y sus tests declarados deben existir;
  todo override futuro en `gen_registry.py` debe citar el commit que
  introduce el módulo. El router sigue operativo: las técnicas relevantes
  se ofrecen como brechas honestas, nunca como capacidad.

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
- Extra `[mcp]` del paquete: el servidor `criba mcp` es stdlib puro y nunca
  importó el paquete `mcp` (queda solo como transitiva de semgrep en dev);
  READMEs actualizados a `pip install "criba[gui,api]"`.

### Changed (CI)
- Python 3.12 añadido al matrix de CI: el classifier ya lo declaraba sin
  probarlo; ahora se prueba en cada push. 3.10/3.11 se mantienen (retirada
  de 3.10 diferida a su EOL, oct-2026).

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
