# CONTEXTO TÉCNICO — CRIBA + BLACKFORGE

Documento de ubicación para un modelo local (GGUF/Ollama). Todo lo escrito aquí
fue verificado contra el código fuente real de `E:\PROJECTS\CRIBA`
(commit canónico main, 723-registros de catálogo BLACKFORGE, motor CRIBA
determinista). No inventa APIs ni números: donde falta una firma exacta, se
describe el comportamiento comprobado.

---

## 0. IDENTIDAD Y PROPÓSITO

**CRIBA (Current Engine)**: motor local, determinista y explicable que prepara
un paquete de análisis ANTES de que un modelo responda. No es un generador de
frases creativas: cartografía el problema, rompe supuestos, genera ideas
estructuralmente distintas, las evalúa con honestidad y las prioriza.

**BLACKFORGE**: módulo de ciberseguridad sobre el mismo núcleo. Aplica el
enfoque a retos defensivos (ethical hacking, pentesting, red/blue/purple team,
threat modeling, AppSec, DevSecOps, forense). Laboratorio de ideas, NO
herramienta de ataque. Toda salida queda sujeta a safety gate S0–S3 y autorización.

**Entrega**: una sola app portable Windows (`CRIBA.exe` + `BLACKFORGE.exe` +
`CRIBA-CLI.exe`) generada con PyInstaller onedir. No requiere Python, Git,
Docker ni API key para el uso básico determinista. El modelo local (opcional)
solo REDACTA lenguaje natural; el motor sigue decidiendo métodos, scores y
seguridad.

**Principios rectores (de spec/CRIBA_BLACKFORGE_MASTER_SPEC.md)**:
- Principio de anclaje: cada idea debe demostrar qué parte de la consulta usa,
  qué actor afecta, qué restricción transforma, qué fallo supera, qué vacío
  explota, qué operador aplica, qué mecanismo propone y cómo se valida.
- Principio de realidad: no inventar archivos, clases, vulnerabilidades, fuentes,
  datos, métricas, resultados, autorizaciones ni capacidades. Distinguir siempre
  HECHO / INFERENCIA / SUPOSICIÓN / HIPÓTESIS / DESCONOCIDO.
- Principio de trazabilidad: cada resultado debe poder reconstruir contexto,
  tarea, restricciones, persona, operador, fase, evidencia, decisión, revisión
  humana, puntuación y razón de selección/descarte.

---

## 1. UBICACIÓN Y ESTRUCTURA REAL (árbol verificado)

Raíz: `E:\PROJECTS\CRIBA`

```
CRIBA-Blackforge.spec          # PyInstaller (build portable)
CRIBA.spec
README.md  README.en.md  README_MVP.md  FIRST_RUN_ES.md  FIRST_RUN_EN.md
HANDOFF.md  RESUME_NEXT_SESSION.txt  CHANGELOG.md  LICENSE  THIRD_PARTY_NOTICES.md
pyproject.toml  uv.lock  requirements-optional.txt  .gitignore
docs/                         # ARCHITECTURE.md, LOCAL_MODELS.md, INTEGRATION.md,
                              # STATE_MATRIX_*, STYLE_GUIDE_*, UI_CONTRACT_*,
                              # WIDGET_TREE_*, prompts/, phases/, assets/
spec/CRIBA_BLACKFORGE_MASTER_SPEC.md   # hipermegaprompt maestro (5477 líneas)
schemas/hy3_review.schema.json
data/
  currents/      # 12 corrientes de selección (01..12 *.json)
  methods/       # library_combined.json + sources/ (11 fuentes) + archive/
  schemas/       # mandatory_model_packet.schema.json, ontology.json
  theme_criba.json  theme_blackforge.json
  assets/blackforge_hero.png
imports/blackforge_v2/        # catálogo canónico 723 registros (JSON/XLSX/CSV)
                              # + causal_engine.py + test_causal_engine.py
src/criba/                    # 53 módulos .py (ver sección 2)
tests/          benchmarks/    verification/    artifacts/    examples/
scripts/        build-portable.ps1
.autoregen/     .github/      .hermes/
```

`src/criba/` completo (verificado):
```
__init__.py  __main__.py  agentic.py  api.py
blackforge_catalog.py  blackforge_causal.py  blackforge_gui.py
blackforge_pipeline.py  blackforge_safety.py  blackforge_selector.py
catalog.py  cli.py  constants.py  constraints.py  context_layer.py
engine.py  engine_v1_audit_intent.py  gates.py  genome.py  gui.py
llm_adapter.py  lottery.py  mcp_server.py  methods.py  migration.py
model_config.py  model_runtime.py  output_format.py  personas.py  selector.py
similarity.py  storage.py  task_layer.py
ui/  __init__.py  actions.py  app_bridge.py  blackforge_screen.py
     blackforge_window.py  dialogs.py  i18n.py  interpreter.py
     main_window.py  model_settings_dialog.py  panels.py  ranking.py
     theme.py  tokens.py  widgets.py
```

---

## 2. MÓDULOS CORE — RESPONSABILIDADES Y CONTRATOS

### 2.1 engine.py — orquestador CRIBA (flujo C/R/I/B/A)
- `activate(query, current="auto", mode="balanced", supporting_methods=8)`
  → MANDATORY_MODEL_PACKET (schema `"mandatory_model_packet"`, versión
  `"2.0.0"`). Es la única salida canónica; `packet["ideas"]` ES el mismo objeto
  que `packet["innovation"]["ideas"]` (una sola colección).
- `cartograph_and_break(query, context, selection)` — Fases 1+2: detecta dominio
  (tecnologia/seguridad/negocio/ia/gobernanza/etica/salud/educacion/transporte/
  energia/alimentos/recursos_humanos/general), actores, activos, supuestos,
  mecanismos saturados y rupturas.
- `diverge(...)` — Fase 3: genera ideas con 16 familias de operadores y 5 ejes
  causales (cada eje: `quien_decide`, `cuando`, `topologia`, `evidencia_requerida`,
  `si_falla`).
- `cross_consistency_assessment(...)` — Fase 4 (banco de pruebas): detecta
  candidatos cosméticos.
- `_evaluate_idea(...)` / `value_score(evidence, novelty, cost)` — convergencia:
  `value_score = evidence * novelty / cost`, con `cost > 0` obligatorio
  (ValueError si no), todos finitos, redondeo a 4 decimales.
- `build_prompt(packet)` — vuelca el paquete a texto para el modelo.
- `activate_with_llm(...)` — variante legacy con adaptador LLM (ver 5).
- INSTRUCTION embebida: obliga al modelo a aplicar el paquete, separar
  (ideas / combinaciones / experimentos / riesgos), no revelar chain-of-thought
  privado y no inventar datos faltantes.

### 2.2 selector.py — selección determinista de corrientes
- `select(...)` elige corriente por señales léxicas
  (siempre/nunca/garant/seguro/safety/security/causa/innov/atac/ia/baseline/
  módulo/permiso/tiempo/persona/interdisciplinar/sesgo/...).
- 12 corrientes (data/currents/01..12): falsacion_invariantes,
  causal_contrafactual, novedad_diversidad, coevolucion_atacante_defensor,
  metamorficas_diferenciales, ejecucion_sombra, ablacion_reintroduccion,
  fronteras_estados_transiciones, deriva_longitudinal, factores_humanos,
  trasplante_interdisciplinar, metaexperimento_jueces.

### 2.3 genome.py — ontología cerrada (ONTOLOGY_VERSION "1.0.0")
5 dimensiones con vocabulario cerrado:
- ACTOR: end_user, operator, administrator, autonomous_agent, external_auditor,
  organization, infrastructure, adversary, regulator, community, unknown
- MECHANISM: elimination, inversion, isolation, verification, delegation,
  prediction, coordination, consensus, redundancy, adaptation, automation,
  transformation, market_exchange, capability_proof, unknown
- TOPOLOGY: centralized, decentralized, federated, peer_to_peer, hierarchical,
  mesh, pipeline, hub_and_spoke, cellular, ephemeral, hybrid, unknown
- TRUST_MODEL: implicit, identity_based, capability_based, evidence_based,
  zero_trust, reputation_based, quorum_based, adversarial, unknown
- TIME_MODEL: synchronous, asynchronous, event_driven, continuous, periodic,
  staged, delayed, ephemeral_per_operation, unknown
- `UnclassifiedProperty` para conceptos nuevos → revisión humana.

### 2.4 blackforge_catalog.py — catálogo inmutable (723 registros)
- Fuente canónica: `imports/blackforge_v2/criba_blackforge_catalogo_final_debate20.json`
  (record_count=723, verificado).
- Carga UNA vez: lista envuelta en tuple, cada registro en `MappingProxyType`
  (inmutable), índice O(1) por `blackforge_id`, sin referencias mutables.
- Las políticas (taxonomy_policy / safety_policy / selection_policy) viven DENTRO
  del catálogo; el loader las REPORTA, no "arregla" nada. `reset_cache()` solo
  para tests.
- SHA-256 documentado del catálogo:
  `1c698d540fbb22d6aa7e2f65bb8e59847109de1d093cfab4de8e817b4eab51cc`

### 2.5 blackforge_selector.py — cuotas deterministas
- `select_blackforge(seed=1, session_size=12, profile="hybrid",
  session_context=None)` → resultado con `selected_ids` y `failure`.
- Tiers permitidos por defecto: essential, core.
- Cuotas (verificadas en docs/ARCHITECTURE.md): máx 3 por categoría primaria,
  máx 2 por familia de origen, máx 2 ejes causales desconocidos, mín 3 catálogos
  de origen, mín 5 categorías primarias, mín 4 ejes causales, etapas obligatorias
  ROMPER/DIVERGIR/ATACAR/EVALUAR.

### 2.6 blackforge_safety.py — safety gate (S0–S3)
- `evaluate_blackforge_safety(item, session_context, *, session_id)` →
  `SafetyDecision` (dataclass con decision, policy_version, item_id, reasons,
  unmet_requirements, allowed_scope, session_id, timestamp). Función PURA,
  sin efectos laterales, corre ANTES de materializar/simular/atacar.
- Decisiones: ALLOW_CONCEPTUAL, ALLOW_DEFENSIVE_DESIGN,
  ALLOW_LOCAL_NON_DESTRUCTIVE, REQUIRE_SANDBOX, REQUIRE_HUMAN_APPROVAL, DENY.
- DENY siempre para `prohibited_automatic_actions` del catálogo, sin importar
  tier/aprobaciones. policy_version `"BF-SAFE-2.0.0"`.

### 2.7 blackforge_causal.py — validación causal
- `validate_against_frozen_model()`, `build_causal_signature()` (SHA-256
  auditable), `analyze_causal_pair()`, `sensitivity_analysis()`.
- Modelo causal: primary_variable, primary_transition, intervention_set,
  outcome_set, failure_behavior.

### 2.8 blackforge_pipeline.py — pipeline headless (Packet 2.1)
- `run_headless(query=REFERENCE_QUERY, seed=1, session_size=12, profile="hybrid",
  session_context=None, session_id="blackforge-headless")` → dict PACKET 2.1
  (schema `"blackforge_headless_packet"`, versión `"2.1.0"`).
- Orden: selector → safety gate (filtra DENY) → señal causal por ítem →
  medición (CCA + convergencia con `_evaluate_idea` importado de engine, NO
  re-derivado) → ideas rankeadas → packet 2.1.
- Si `selection.failure` no es None → devuelve `status: "SELECTION_FAILED"` con
  ideas vacías (honesto, no fabrica).
- Mapea ejes BLACKFORGE (inglés) → ejes CRIBA (español) para reusar el mismo
  scoring (`_AXIS_MAP`).
- Artefactos: `verification/blackforge_headless_output.json` y
  `...normalized.json` (sin UUID/timestamp/path).

### 2.9 lottery.py — Doble Lotería
- `run_lottery(methods_file, rounds=20, batch_size=20, mode="alternating",
  seed=42, query=None, output_dir=None)`.
- Modos: optimized, associative, pure, alternating. `VALID_LOTTERY_MODES`.
- Catálogo de métodos por defecto: `data/methods/library_combined.json`.
- Salida por defecto: `%LOCALAPPDATA%\CRIBA-Blackforge\lottery_results`.

### 2.10 storage.py — persistencia SQLite
- `Storage(db_path)`: `save(query, packet, config)`, `get(session_id)`,
  `compare(session_a, session_b)`.
- DB por defecto: portable → `%LOCALAPPDATA%\CRIBA-Blackforge\criba.sqlite3`;
  dev → `artifacts/criba.sqlite3`.
- Tablas: sessions (ID, timestamp, query_hash, query, current_id, status,
  config, packet, evidence), decisions (ID, session_id, timestamp, status,
  evidence, note).

### 2.11 cli.py — entrada de línea de comandos
Subcomandos (verificados): `activate`, `run`, `build-prompt`, `list-currents`,
`explain`, `compare`, `blackforge`, `lottery`, `serve`, `mcp`, `gui`.
- Flags comunes: `--query` / `--file`, `--current`, `--mode`,
  `--supporting-methods`, `--llm {none,offline,cloud}`, `--llm-model`,
  `--llm-url`, `--llm-api-key`, `--use-configured-model`, `--reasoning
  {fast,balanced,deep}`, `--output`.
- `criba blackforge --query "..." --seed 11 --use-configured-model --reasoning deep`
- `criba lottery --mode alternating --rounds 20 --seed 42`

### 2.12 api.py / mcp_server.py — HTTP y MCP
- FastAPI: `serve(host, port, db)`; endpoints /health, /v1/currents, /v1/methods,
  /v1/sessions/{id}, POST /v1/activate, /v1/run, /v1/build-prompt, /v1/compare,
  /v1/decisions. Escucha SOLO en loopback (127.0.0.1).
- MCP stdio: `run_stdio(db)`; herramienta `activate_current`.

### 2.13 gui.py / ui/* — interfaces PySide6
- `main_window.py` (CRIBA), `blackforge_window.py` (BLACKFORGE). Desde CRIBA,
  pulsar "Blackforge" lanza `BLACKFORGE.exe` hermano; CRIBA se oculta y vuelve
  al cerrarlo. Mismos datos y config de modelo.
- `model_settings_dialog.py`: gestión de perfiles GGUF/Ollama compartidos.
- `theme.py` / `tokens.py`: tokens visuales (CRIBA azul cian / BLACKFORGE naranja
  oscuro). `i18n.py`: es/en.

---

## 3. INTEGRACIÓN DE MODELO LOCAL (capa GGUF/Ollama)

Esta es la parte crítica para "pasarle a un modelo local". Tres módulos
concilian: `model_config.py` (perfiles), `model_runtime.py` (síntesis
semántica acotada), `llm_adapter.py` (adaptador legacy).

### 3.1 model_config.py — perfiles persistentes (sin secretos)
- Ruta: `%LOCALAPPDATA%\CRIBA-Blackforge\models.json` (override con env
  `CRIBA_MODEL_CONFIG`). Compartida entre CRIBA y BLACKFORGE.
- `ModelProfile` (dataclass): id, name, backend (`"llama_cpp"` |
  `"ollama"`), endpoint (`"http://127.0.0.1:8080"`), model (`"criba-local"`),
  gguf_path, server_path, auto_start (bool), reasoning
  (`"fast"|"balanced"|"deep"`), context_size (2048–131072, def 8192),
  gpu_layers (-1..999, def -1 = auto), temperature (0.0–1.5, def 0.45),
  max_output_tokens (256–16384, def 2400).
- `ModelSettings`: schema_version=1, enabled (bool), active_profile_id, profiles.
- `load_model_settings()` / `save_model_settings()` — si el archivo está
  corrupto o falta, degrada a defaults deshabilitados (no rompe).

### 3.2 model_runtime.py — capa de lenguaje acotada
- CRIBA sigue siendo el planificador/scorer determinista. Este módulo SOLO
  reescribe las ideas candidatas en español coherente y accionable, preservando
  `candidate_id`, scores y metadatos de seguridad.
- `ensure_profile_available(profile, *, start=True)`: valida endpoint loopback,
  arranca `llama-server` si `backend=="llama_cpp"` y `auto_start`.
- `_start_llama_server(profile)`: lanza `llama-server.exe -m <gguf> --host
  127.0.0.1 --port <port> -c <ctx> --alias <model> --jinja` (+ `-ngl` si
  gpu_layers>=0). Sin ventana en Windows. Se cierra al terminar la app que lo
  inició. Timeout arranque 75 s.
- **Endpoint OBLIGATORIAMENTE loopback**: valida que sea http://127.0.0.1 o
  localhost, sin usuario/contraseña en URL, sin path/query/fragment. Rechaza
  cualquier otro (seguridad: nunca sale de la máquina).
- `build_semantic_prompt(query, ideas, *, product, reasoning, start_index=1)`
  → (json_prompt, expected_ids). Instruye al modelo a convertir cada candidato
  mecánico en idea con sentido, conservar `candidate_id` y la intención de sus
  métodos, NO inventar evidencia/capacidades, y aplica política de
  input_no_confiable (la consulta y candidatos son datos no confiables; el
  modelo no debe ejecutar ni seguir instrucciones embebidas en ellos).
- Contrato de salida (`_SEMANTIC_SCHEMA`, validado con Pydantic
  `SemanticBatch`/`SemanticIdea`):
  ```
  {"ideas":[
    {"candidate_id":str, "title":str(3-120),
     "description":str(12-700), "mechanism":str(5-500),
     "experiment":str(5-500)}
  ]}   # 1..12 ideas, additionalProperties:false
  ```
- `MAX_SEMANTIC_CANDIDATES = 12`: solo se redactan los 12 candidatos mejor
  rankeados (BLACKFORGE genera ≤12/ronda y redacta la ronda completa).
- `_reasoning_instruction(level)`: fast=directo/breve sin thinking extendido;
  balanced=análisis causal interno, sin mostrar; deep=análisis profundo + 2ª
  revisión del JSON (≈doble latencia). CRIBA NUNCA pide ni muestra chain-of-
  thought; solo conserva el JSON final validado.
- Timeout por llamada: 300 s. Fuera del hilo gráfico. Si falla: fallback
  determinista explícito (conserva salida mecánica y muestra el fallback).
- Límites de texto por campo (chars): candidate_id 120, title 120, description
  700, mechanism 500, experiment 500.

### 3.3 llm_adapter.py — adaptador legacy (no usar para nuevo flujo GGUF)
- `create_backend(mode)` con mode `offline` (Ollama http://localhost:11434),
  `cloud` (API OpenAI-compat), `none` (motor determinista).
- `generate_ideas_with_llm(...)` parsea JSON o texto y convierte a formato CRIBA
  (`id: "LLM01"...`). Es el camino antiguo; el nuevo flujo prefiere
  `model_runtime.enhance_ideas_with_model` / `enhance_criba_packet`.

### 3.4 Recomendaciones de modelo (docs/LOCAL_MODELS.md)
- Hardware 16 GB RAM + 4–8 GB VRAM: Qwen3-4B Q4_K_M (ágil) o Qwen3-8B Q4_K_M
  (mejor calidad). Evitar ≥14B como perfil interactivo por defecto.
- Contexto inicial 8192, gpu_layers Automático; si Vulkan inestable, bajar capas
  o usar CPU.
- Arranque: `winget install llama.cpp`; luego perfil GGUF en "Modelos IA".

---

## 4. INVARIANTES Y REGLAS DE DECISIÓN (NO NEGOCIABLES)

- `value_score = evidence * novelty / cost` (cost>0, finito, 4 decimales).
- `recommended_status` ∈ VALID_DECISIONS = {ADOPTAR, AMPLIAR PRUEBA, ABANDONAR,
  ARCHIVAR PARA RECOMBINAR}. ADOPTAR NO se infiere por nº de familias.
- `pipeline_action` es CAMPO INDEPENDIENTE ∈ {PROTOTIPAR, DIVERGIR}:
  - len(families) >= 4 → PROTOTIPAR + AMPLIAR PRUEBA
  - len(families) < 4  → DIVERGIR  + AMPLIAR PRUEBA
- Genoma: vocabulario cerrado; concepto desconocido → UnclassifiedProperty →
  revisión humana.
- Catálogo BLACKFORGE inmutable (723, MappingProxyType). Safety DENY para
  acciones prohibidas automáticas, siempre.
- Sin red por defecto (API loopback 127.0.0.1); sin credenciales almacenadas;
  sin ejecución de la consulta como comando.
- `FEATURES` (flags de hipermegaprompt) todas OFF por defecto en constants.py;
  el comportamiento base se preserva mientras estén False.

---

## 5. CÓMO "UBICARSE" Y AYUDAR (para el modelo local)

Cuando recibas este contexto, tu rol es ASISTENTE del ingeniero (moli/KLSX) que
trabaja en este repo. Puedes:

1. **Explicar y navegar** el código: cita archivos reales (`src/criba/engine.py`,
   `blackforge_pipeline.py`, etc.) y funciones verificadas arriba.
2. **Generar/redactar ideas** cuando el motor determinista ya produjo
   candidatos: respeta el contrato SemanticBatch y conserva `candidate_id`.
3. **Sugerir cambios de código** (patches) siguiendo estilo existente: Python
   3.10+, pydantic v2, tipado estricto en módulos core (mypy strict excluye
   `ui/` y `gui.py`), sin secretos, sin red externa, sin inventar APIs.
4. **Ejecutar comandos** vía terminal/uv cuando el usuario lo pida (tests, build,
   CLI). Entorno: `uv sync --all-extras --locked`; tests `uv run pytest`; tipos
   `uv run mypy src/criba` (la suite pesada en Modal es opcional aquí).
5. **No** afirmar que probaste/ejecutaste algo que no comprobaste; **no** romper
   invariantes de la sección 4; **no** sugerir que el modelo local decida scores,
   métodos o seguridad (eso es del motor).

Límites conocidos (verídicos):
- Ejecutable no firmado → SmartScreen la primera vez.
- Adaptadores API/MCP no activos por defecto.
- El modelo GGUF NO se incluye en el ZIP portable.
- Working tree puede contener material preexistente/no atribuido preservado.

---

## 6. REFERENCIAS RÁPIDAS (rutas reales)

- Arquitectura: `docs/ARCHITECTURE.md`
- Modelos locales: `docs/LOCAL_MODELS.md`
- Spec maestra: `spec/CRIBA_BLACKFORGE_MASTER_SPEC.md`
- Contratos UI: `docs/UI_CONTRACT_CRIBA.md`, `docs/UI_CONTRACT_BLACKFORGE.md`
- Estado/matrices: `docs/STATE_MATRIX_CRIBA.md`, `docs/STATE_MATRIX_BLACKFORGE.md`
- Estilo: `docs/STYLE_GUIDE_CRIBA.md`, `docs/STYLE_GUIDE_BLACKFORGE.md`
- Esquemas: `data/schemas/mandatory_model_packet.schema.json`,
  `data/schemas/ontology.json`, `schemas/hy3_review.schema.json`
- Build: `scripts/build-portable.ps1`, `CRIBA-Blackforge.spec`
- Config modelo usuario: `%LOCALAPPDATA%\CRIBA-Blackforge\models.json`
- DB usuario: `%LOCALAPPDATA%\CRIBA-Blackforge\criba.sqlite3`

---
*Generado como dossier de ubicación técnica. Todo lo aquí descrito fue
verificado contra el árbol de archivos y el código fuente de
E:\PROJECTS\CRIBA al momento de la creación. No contiene secretos ni
credenciales.*
