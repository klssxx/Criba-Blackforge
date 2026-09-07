# Auditoría CBAC469 — matriz de recuperación selectiva

Estado: **SLICE 1/3 EN CURSO — CBAC469_RECOVERY ≠ DONE** (§84: no se declara
completa hasta que todo bloque sustancial tenga disposición ejecutada).

Fuente de verdad: diff real de `cbac469` vs padre `311927b` (93 paths
borrados, ~7.080 líneas). Reglas: §74–§85 de la CBAC469 Recovery
Constitution v2.1. Unidad de decisión: CAPACIDAD, no LOC.

## Matriz de triage (100% de paths borrados)

| Bloque | Paths | LOC | Tests históricos | Equivalente actual | Consumidores en HEAD | Txxx del canon | DECISIÓN | Evidencia |
|---|---|---|---|---|---|---|---|---|
| `invention/` (16 módulos) | 16 | ~1.100 | taxonomy(318)+triz(84)+registry(57) | ninguno | canon (router) | T053/55/57/59/60/62–65/116/129 | **RESTORED (slice 1)** — commit 1fc1b5e | §79 completo: capability proof (39 tests históricos verdes), §78 dispatch-only auditado, §82 cadena canon→router→operador, canon 2026-09-08.1 |
| `gaps/` (10 módulos) | 10 | 1.684 | 9 archivos (~900 líneas de tests) | ninguno | 0 (grep HEAD) | sleeping_beauty/resurrection/patent_expiration/dormant (T126–T128), white_space (×4), contradictions, failures, limitations, research | **DEFER slice 2** (candidato RESTORE P1) | Familia ADVERSARIAL_FUTURES hoy 100% PLANNED; §81 aplica. Sin §79 aún: nada promovido por parecido (§80) |
| `signals/` (8 módulos) | 8 | 606 | 10 tests + 2 fixtures | ninguno | 0 | dynamics/convergence/topics (T046–T052), anomaly/bursts/changepoints/lead_lag/weak_signals/scurve (T096–T115, T130) | **DEFER slice 2** (candidato RESTORE P1) | Sin consumidores ni equivalente; contrato EvidenceDocument vivo → adaptación plausible |
| `graph/` (8 módulos) | 8 | 625 | 8 tests + fixtures | store.py moderno es de EVIDENCIA, no de grafo de entidades — distinto | 0 | bridges/communities/link_prediction/… (T031–T045 RETRIEVAL_GRAPH) | **DEFER slice 3** (candidato RESTORE_AND_ADAPT P1) | graph/store (264 LOC) solapa parcialmente con almacenamiento moderno: auditar separación en su slice |
| `entities/` (3 módulos) | 3 | 107 | (dentro de tests de graph) | ninguno | 0 | canon referencia `entities.ontology` — módulo que NUNCA existió en cbac469~1 (GAP del canon) | **DEFER slice 3** + registrar GAP `entities.ontology` | extractor/resolver son P2; el gap de ontología es un UNKNOWN canónico, no recuperable de este diff |
| `provenance.py` | 1 | 70 | test_provenance (113) | content_hash: SÍ superseded (CH1–CH7 modernos, commit 714d0b8); `assess_claims` (FACT→INFERENCE downgrade, grounded_claim_ratio): SIN equivalente moderno | 0 | transversal | **DEFER slice 2** (RESTORE_AND_ADAPT parcial; content_hash queda SUPERSEDED) | La mitad epistémica (downgrade determinista de claims) es capacidad real sin sucesor |
| `claims.py` | 1 | 31 | (dentro de tests de claims) | contratos Claim/ClaimAssessment vivos; extracción regex sin sucesor | 0 | transversal | **DEFER slice 2** (pareja de provenance) | Pequeño; se restaura con provenance o se reimplementa |
| 12 stubs raíz + 4 `__init__` de dir | 16 | 16 | — | — | 0 | — | **KEEP_DELETED_DEAD** | 1 línea cada uno: `"""IIE X — skeleton (P0x). Implementation lands in its phase."""` — placeholders puros |
| 31 tests no-invention | 31 | — | — | — | — | — | **Sigue a su bloque** | Se restauran en el slice de su fuente; los de bloques DEAD/SUPERSEDED quedan borrados con ella |

## NEGATIVE_KNOWLEDGE (§76: por qué NO volver)

1. **Stubs (budget, cache, capabilities, config, dedup, pipeline,
   orchestrator, legacy_bridge, techniques/, scoring/, problems/,
   monitoring/)**: skeletons de 1 línea sin comportamiento. Reabrir solo si
   su fase llega con diseño real. No son capacidad perdida.
2. **provenance.content_hash**: superseded por la maquinaria moderna de
   huella de contenido (CH1–CH7, content_hash separado de identidad
   documental). Restaurar la versión histórica sería un REGRESO (§83).
3. **graph/store.py como almacenamiento**: el HEAD tiene almacenamiento de
   evidencia propio y probado; si el grafo vuelve, su store debe adaptarse
   o subordinarse al moderno, nunca convivir dos stores de autoridad.

## Condiciones de reapertura (slices 2–3)

- Slice 2 (gaps + signals + provenance/claims): mismo protocolo §79 por
  técnica; mapeo por §80 (SEMANTIC+CONTRACT+BEHAVIOR+CANONICAL match, no
  por docstring); promoción solo tras §82. Prerequisito: presupuesto para
  ~2.900 LOC src + ~1.100 LOC tests.
- Slice 3 (graph + entities): auditar antes la separación graph/store vs
  storage moderno; resolver GAP `entities.ontology` (canon referencia un
  módulo jamás implementado — opción: mantener PLANNED con nota o
  reasignar en una época canónica futura, jamás silenciosamente).

## Registro de época canónica (apéndice)

- `2026-09-07.1`: canon v2 con 11 IMPLEMENTED (estado previo al hallazgo).
- `2026-09-07.2`: DEGRADATION_EVENT — 11→0 IMPLEMENTED al descubrir que
  cbac469 borró el código (falso IMPLEMENTED). Tombstone en el ledger de
  assurance; PR #12.
- `2026-09-08.1`: PROMOTION_EVENT — 11 técnicas restauradas con §79
  completo (commit 1fc1b5e); promoción por el generador canónico, nunca
  por el módulo restaurado (§77).

## Slice 1 — verificación por técnica tras construcción (criterio corregido)

Auditoría → CONSTRUCCIÓN: el gap común era "capacidad presente pero
inaccesible desde el producto". Ruta canónica de integración construida:
`criba/intelligence/execution.py` (resolver runtime + adaptadores por
input_contracts + guardrails de canon) y CLI `criba tecnicas --ejecutar
TXXX --problema ... [--entrada docs.json] [--desde-almacen]`. La cadena
§82 queda accesible E2E desde el producto. Negativos de producto: PLANNED
→ exit 2 «el canon decide»; desconocida → exit 2; params faltantes → exit 2.

Estado común a las 11: implementación real + contratos + tests positivos y
negativos históricos + cadena canon→router→operador + **integración de
producto (CLI)** + procedencia (overrides del generador canónico) →
**IMPLEMENTED_VERIFIED** (nivel A2 del ledger; techo runtime SHADOW por
assurance, no por desconexión).

| Txxx | requisito_canonico | implementacion | operador_runtime | integracion | tests(+/-) | falsifier |
|---|---|---|---|---|---|---|
| T053 | Rare-combination detection (corpus explícito) | invention/rare_combinations.py | detect_rare_combinations | CLI --ejecutar con evidencia --entrada/--desde-almacen | determinism/corpus-local(+); limits/unsupported-metadata(−) | par «raro» que afirme novedad global o no determinismo con mismo corpus |
| T055 | Cross-domain analogy | invention/cross_domain.py | detect_cross_domain_analogies | CLI ídem | shared-concepts-and-domains(+); limit(−) | analogía sin conceptos compartidos explícitos o sin dominios distintos |
| T057 | TRIZ (catálogo canónico de principios; la minería de contradicciones es T058, PLANNED) | invention/triz.py | list_principles/get_principle | CLI --ejecutar T057 | 40/unicidad/orden(+); lookup inválido, inmutabilidad, sin-matriz-de-contradicciones(−) | catálogo mutable, número fuera de 1..40, o afirmación de matriz de contradicciones |
| T059 | Morphological analysis | invention/morphology.py | generate_morphological_hypotheses | CLI --problema+dimensions | determinismo(+) | hipótesis no deterministas o fuera del producto cartesiano declarado |
| T060 | SCAMPER | invention/scamper.py | generate_scamper_hypotheses | CLI --problema+components | 7 tipos sin-afirmar-solución(+); dedup/limits(−) | menos de 7 tipos o hipótesis que afirme resolver el problema |
| T062 | Functional decomposition | invention/functions.py | decompose_functional_hypotheses | CLI --problema+component_functions | explícito/determinista(+) | descomposición que invente funciones no declaradas |
| T063 | Function-to-mechanism search (solo con evidencia recuperada explícita) | invention/functions.py | search_function_to_mechanism_hypotheses | CLI con --entrada/--desde-almacen | source-metadata obligatoria(+) | mecanismo sin doc_id fuente o metadata fabricada |
| T064 | First-principles decomposition | invention/first_principles.py | decompose_first_principles_hypotheses | CLI --problema+premise_implications | premisas explícitas(+) | conclusión que oculte la premisa de la que deriva |
| T065 | Constraint inversion | invention/inversion.py | generate_constraint_inversion_hypotheses | CLI --problema+constraint_inversions | nunca-afirma-remoción(−/+) | hipótesis que afirme que la restricción desaparece |
| T116 | Adjacent possible (solo pares ausentes de lo conocido) | invention/adjacent_possible.py | generate_adjacent_possible_hypotheses | CLI --problema+capabilities(+known) | excluye-conocidas(−); corpus-local(+) | proponer un par presente en known_combinations |
| T129 | Second/Nth-order/counterfactual/future-back/bottleneck | invention/{counterfactual,future_back,bottlenecks,nth_order}.py | 4 generadores | CLI --problema+temporal_map (contrafactual; resto vía API) | 4 nunca-afirman(−); hipótesis(+) | efecto futuro afirmado como ocurrirá, o cuello de botella como causal |

remaining_gap común: consumidor adicional en el flujo `invent` (los operadores
generan; el intérprete sigue siendo el proponente del loop principal —
decisión de arquitectura vigente, no olvido: mezclarlos cambiaría la
semántica del loop y excede el canon actual).

MAPPED_ONLY sin módulo (taxonomy declara, código ausente → PLANNED correcto):
T054/T061 (invention.recombination), T056 (biomimicry), T058
(triz_contradiction_mining), T066 (assumption_mining), T067
(contradiction_mining → gaps.contradictions, borrado por cbac469).
