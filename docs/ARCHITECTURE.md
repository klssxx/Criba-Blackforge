# ARCHITECTURE.md — CRIBA + BLACKFORGE

Versión: 1.0.0 · Fecha: 2026-07-24 · Estado: DOCUMENTADO

## Visión general

CRIBA (Current Engine) es un motor local, determinista y explicable que prepara un paquete de análisis antes de que otro modelo responda. BLACKFORGE es el módulo de ciberseguridad que opera sobre el mismo núcleo.

```
┌─────────────────────────────────────────────────────────────────────┐
│                        USUARIO                                       │
│  (consulta: "¿Cómo controlar agentes sin autoridad central?")     │
└───────────────────────┬─────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    CLI / API / MCP                                   │
│  - `criba activate --query "..."`                                   │
│  - `criba blackforge --query "..." --seed 11`                       │
│  - POST /v1/activate                                                │
│  - MCP: activate_current                                            │
└───────────────────────┬─────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   ENGINE (src/criba/engine.py)                       │
│  - activate() → MANDATORY_MODEL_PACKET                              │
│  - cartograph_and_break() → rupturas de supuestos                   │
│  - diverge() → ideas candidatas                                     │
│  - cross_consistency_assessment() → filtro CCA                      │
│  - value_score(evidence, novelty, cost) = evidence*novelty/cost    │
└───────────────────────┬─────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────────┐
│                 SELECTOR (src/criba/selector.py)                     │
│  - Señales: absolute, causal, novelty, adversary, ai, baseline,     │
│             ablation, states, time, human, transfer, meta           │
│  - Puntuación: falsacion_invariantes, causal_contrafactual,         │
│                novedad_diversidad, coevolucion_atacante_defensor,   │
│                metamorficas_diferenciales, ejecucion_sombra,        │
│                ablacion_reintroduccion, fronteras_estados,           │
│                deriva_longitudinal, factores_humanos,               │
│                trasplante_interdisciplinar, metaexperimento_jueces  │
└───────────────────────┬─────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────────┐
│                 GENOME (src/criba/genome.py)                         │
│  - Ontología cerrada: ACTOR, MECHANISM, TOPOLOGY, TRUST_MODEL,      │
│    TIME_MODEL                                                       │
│  - Normalización y validación contra vocabulario cerrado            │
│  - UnclassifiedProperty para conceptos nuevos (revisión humana)   │
└─────────────────────────────────────────────────────────────────────┘
```

## Componentes principales

### 1. Módulo engine (`src/criba/engine.py`)

**Responsabilidad**: Orquestación del flujo CRIBA C/R/I/B/A.

**Flujo**:
1. **Contextualizar**: `activate()` recibe la consulta y selecciona la corriente.
2. **Romper**: `cartograph_and_break()` identifica supuestos conocidos y rupturas posibles.
3. **Idear**: `diverge()` genera ideas mediante operadores (16 familias) y CAUSAL VARIABLES (5 ejes).
4. **Banco de Pruebas**: `cross_consistency_assessment()` detecta candidatos cosméticos.
5. **Decidir**: `value_score()` mide calidad = evidence * novelty / cost.

**Contratos**:
- `value_score(evidence, novelty, cost)` → float
  - `cost > 0` obligatorio (ValueScoreError si no)
  - Todos los inputs deben ser finitos
  - Resultado redondeado a 4 decimales

### 2. Módulo selector (`src/criba/selector.py`)

**Responsabilidad**: Selección determinista de corrientes e ideas.

**Señales de selección**:
- `siempre`, `nunca`, `garant`, `imposible`, `seguro`, `fiable`, `safety`, `security`
- `causa`, `causal`, `correl`, `tratamiento`, `compar`, `intervenci`
- `innov`, `disrupt`, `alternativa`, `ideas`, `estanc`
- `atac`, `fraude`, `advers`, `seguridad`, `security`, `gobernanza`, `negoci`, `compet`
- `ia`, `ai`, `modelo`, `llm`, `agente`, `probabil`, `oráculo`
- `actual`, `baseline`, `sustitu`, `reemplaz`, `automat`, `candidato`
- `módulo`, `regla`, `agente`, `dependencia`, `componente`, `complej`
- `permiso`, `estado`, `transici`, `flujo`, `protocolo`, `fase`, `umbral`, `aprob`
- `tiempo`, `longitud`, `deriva`, `mantenimiento`, `reputación`, `degrad`
- `persona`, `operador`, `experto`, `usuario`, `aprobar`, `fatiga`, `equipo`
- `interdisciplin`, `aviación`, `ecología`, `inmunología`, `radical`, `dominio`
- `sesgo`, `evaluador`, `métrica`, `jueces`, `homogene`, `proceso`

**Puntuaciones**:
- `falsacion_invariantes`: 36 (absoluto + adversario + estados)
- `causal_contrafactual`: 42 (causal + baseline)
- `novedad_diversidad`: 45 (novelty + transfer)
- `coevolucion_atacante_defensor`: 48 (adversario + ai)
- `metamorficas_diferenciales`: 42 (ai + causal)
- `ejecucion_sombra`: 48 (baseline + estados)
- `ablacion_reintroduccion`: 45 (ablation + baseline)
- `fronteras_estados_transiciones`: 48 (estados + adversario)
- `deriva_longitudinal`: 48 (tiempo + baseline)
- `factores_humanos`: 42 (human + estados)
- `trasplante_interdisciplinar`: 48 (transfer + novelty)
- `metaexperimento_jueces`: 48 (meta + novelty)

### 3. Módulo genome (`src/criba/genome.py`)

**Ontología cerrada** (versión ONTOLOGY_VERSION = "1.0.0"):

| Dimensión | Valores |
|-----------|---------|
| ACTOR | end_user, operator, administrator, autonomous_agent, external_auditor, organization, infrastructure, adversary, regulator, community, unknown |
| MECHANISM | elimination, inversion, isolation, verification, delegation, prediction, coordination, consensus, redundancy, adaptation, automation, transformation, market_exchange, capability_proof, unknown |
| TOPOLOGY | centralized, decentralized, federated, peer_to_peer, hierarchical, mesh, pipeline, hub_and_spoke, cellular, ephemeral, hybrid, unknown |
| TRUST_MODEL | implicit, identity_based, capability_based, evidence_based, zero_trust, reputation_based, quorum_based, adversarial, unknown |
| TIME_MODEL | synchronous, asynchronous, event_driven, continuous, periodic, staged, delayed, ephemeral_per_operation, unknown |

**Familias de operadores** (16 familias):
- diagnóstico, inversión, sustracción, restricciones, actores_roles, incentivos, morfología, recombinación, analogías, arquitectura, gobernanza, diseño_adversarial, escenarios, prototipado, verificación, decision_riesgo

### 4. Módulo blackforge_catalog (`src/criba/blackforge_catalog.py`)

**Catálogo**: 723 registros (SHA-256: `1c698d540fbb22d6aa7e2f65bb8e59847109de1d093cfab4de8e817b4eab51cc`)

**Inmutabilidad**:
- Registros envueltos en `MappingProxyType`
- Índice O(1) por `blackforge_id`
- `reset_cache()` solo para testing

**Políticas embebidas**:
- `taxonomy_policy`: clases de seguridad, etapas de pipeline, categorías funcionales
- `safety_policy`: acciones prohibidas
- `selection_policy`: cuotas y restricciones

### 5. Módulo blackforge_selector (`src/criba/blackforge_selector.py`)

**Selección determinista**:
- Semilla: 1 (por defecto)
- Tamaño sesión: 12 (por defecto)
- Perfil: hybrid (por defecto)
- Tier permitidos: essential, core (por defecto)

**Cuotas**:
- Máximo por categoría primaria: 3
- Máximo por familia de origen: 2
- Máximo ejes causales desconocidos: 2
- Mínimo catálogos de origen: 3
- Mínimo categorías primarias: 5
- Mínimo ejes causales: 4
- Etapas obligatorias: ROMPER, DIVERGIR, ATACAR, EVALUAR

### 6. Módulo blackforge_safety (`src/criba/blackforge_safety.py`)

**Clases de seguridad**:
- S0_CONCEPTUAL: solo análisis e ideación
- S1_DEFENSIVE: diseño defensivo / análisis local no destructivo
- S2_SANDBOX: necesita sandbox + approval + rollback + logging + stop
- S3_HIGH_CONTROL: mayor control; sandbox aislado + human approval

**Decisiones**:
- ALLOW_CONCEPTUAL
- ALLOW_DEFENSIVE_DESIGN
- ALLOW_LOCAL_NON_DESTRUCTIVE
- REQUIRE_SANDBOX
- REQUIRE_HUMAN_APPROVAL
- DENY

### 7. Módulo blackforge_causal (`src/criba/blackforge_causal.py`)

**Validación causal**:
- `validate_against_frozen_model()`: valida propuestas contra modelo congelado
- `build_causal_signature()`: genera firma SHA-256 auditable
- `analyze_causal_pair()`: compara pares de propuestas
- `sensitivity_analysis()`: análisis de sensibilidad por peso

**Modelo causal**:
- `primary_variable`, `primary_transition`, `intervention_set`, `outcome_set`, `failure_behavior`

### 8. Módulo blackforge_pipeline (`src/criba/blackforge_pipeline.py`)

**Pipeline headless**:
1. Selector → 2. Safety gate → 3. Firma causal → 4. Medición (CCA + convergencia) → 5. Ideas rankeadas → 6. Packet 2.1

**Salida**:
- `verification/blackforge_headless_output.json`
- `verification/blackforge_headless_output.normalized.json`

## Comandos Modal

```bash
# Suite completa
python -m modal run .autoregen/cloud/modal_runner.py::pytest_full

# Test focalizado
python -m modal run .autoregen/cloud/modal_runner.py::pytest_file --path tests/unit/test_cli.py

# Mypy estricto
python -m modal run .autoregen/cloud/modal_runner.py::mypy_strict

# Mypy scoped (pyproject.toml)
python -m modal run .autoregen/cloud/modal_runner.py::mypy_scoped

# Coverage
python -m modal run .autoregen/cloud/modal_runner.py::coverage_run

# Benchmark
python -m modal run .autoregen/cloud/modal_runner.py::benchmark_blackforge --repetitions 3
```

## Artefactos de verificación

| Archivo | Propósito |
|---------|-----------|
| `verification/blackforge_benchmark_baseline.json` | Baseline de rendimiento |
| `verification/blackforge_benchmark.json` | Resultados posteriores |
| `verification/blackforge_benchmark_comparison.json` | Comparación delta |
| `verification/blackforge_catalog_report.json` | Informe de validación del catálogo |
| `verification/blackforge_headless_output.json` | Salida del pipeline headless |
| `verification/blackforge_headless_output.normalized.json` | Salida normalizada (determinista) |

## Diagrama Mermaid (arquitectura)

```mermaid
graph TD
    A[Usuario<br/>Consulta] --> B[CLI/API/MCP]
    B --> C[Engine<br/>activate()]
    C --> D[Selector<br/>señales]
    D --> E[Genome<br/>ontología]
    E --> F[Ideas<br/>divergencia]
    F --> G[Convergence<br/>value_score]

    subgraph BLACKFORGE
        H[Catalog<br/>723 registros]
        I[Selector<br/>cuotas]
        J[Safety Gate<br/>S0-S3]
        K[Causal<br/>validación]
        L[Pipeline<br/>headless]

        I --> J
        J --> K
        K --> L
        L --> M[Packet 2.1]
    end

    G --> N[Packet 2.0]
    N --> O[Modelo]
    M --> P[Verificación]

    style A fill:#070D1A,stroke:#22D3EE,color:#EAF2FF
    style B fill:#0B1424,stroke:#22D3EE,color:#9FB3D1
    style C fill:#101D33,stroke:#22D3EE,color:#EAF2FF
    style D fill:#101D33,stroke:#22D3EE,color:#EAF2FF
    style E fill:#101D33,stroke:#22D3EE,color:#EAF2FF
    style F fill:#101D33,stroke:#22D3EE,color:#EAF2FF
    style G fill:#101D33,stroke:#22D3EE,color:#EAF2FF
    style H fill:#0C0A08,stroke:#FF7A1A,color:#FBF3EA
    style I fill:#15110D,stroke:#FF7A1A,color:#C9B8A6
    style J fill:#1D1712,stroke:#FF7A1A,color:#FBF3EA
    style K fill:#1D1712,stroke:#FF7A1A,color:#FBF3EA
    style L fill:#1D1712,stroke:#FF7A1A,color:#FBF3EA
    style M fill:#1D1712,stroke:#FF7A1A,color:#FBF3EA
    style N fill:#101D33,stroke:#22D3EE,color:#EAF2FF
    style O fill:#070D1A,stroke:#22D3EE,color:#EAF2FF
    style P fill:#101D33,stroke:#22D3EE,color:#EAF2FF
```

## Flujo de datos

```
┌─────────────────────────────────────────────────────────────────┐
│                    FLUJO DE DATOS                                │
└─────────────────────────────────────────────────────────────────┘

Entrada: Usuario → Consulta (string, max 20.000 chars)
         │
         ▼
Preprocesamiento: Normalización Unicode (NFKC)
         │
         ▼
Selección: Señales → Puntuación → Corriente seleccionada
         │
         ▼
Cartografía: Espacio conocido → Supuestos → Rupturas
         │
         ▼
Divergencia: Operadores × Operadores → Ideas candidatas
         │
         ▼
CCA: Filtrado de candidatos cosméticos
         │
         ▼
Convergencia: value_score = evidence × novelty / cost
         │
         ▼
Salida: MANDATORY_MODEL_PACKET (JSON, esquema 2.0.0)
         │
         ▼
Persistencia: SQLite → Sesiones, decisiones, evidencia
```

## Seguridad

1. **No ejecución de comandos**: La consulta nunca se ejecuta como comando.
2. **Sin red por defecto**: La API solo escucha en loopback (127.0.0.1).
3. **Sin credenciales**: No se almacenan ni leen credenciales.
4. **Sandbox para experimentos**: Los experimentos tienen rollback automático.
5. **Safety gate BLACKFORGE**: S0-S3 controlan el nivel de riesgo.

## Almacén de datos

- **SQLite**: `artifacts/criba.sqlite3`
- **Tablas**:
  - `sessions`: ID, timestamp, query_hash, query, current_id, status, config, packet, evidence
  - `decisions`: ID, session_id, timestamp, status, evidence, note
- **Catálogo**: `imports/blackforge_v2/criba_blackforge_catalogo_final_debate20.json`

## APIs

### CLI

```bash
criba activate --query "..." --current auto --mode balanced
criba blackforge --query "..." --seed 11
criba run --query "..."
criba build-prompt --query "..." --output prompt.md
criba list-currents
criba explain --session <id>
criba compare --session-a <id1> --session-b <id2>
criba serve --host 127.0.0.1 --port 8765
criba mcp
criba gui
```

### HTTP API (FastAPI)

```
GET  /health                    → {status: "ok"}
GET  /v1/currents               → lista de corrientes
GET  /v1/methods                → lista de métodos
GET  /v1/sessions/{id}          → sesión específica
POST /v1/activate               → activar corriente
POST /v1/run                    → ejecutar flujo
POST /v1/build-prompt           → generar prompt
POST /v1/compare                 → comparar sesiones
POST /v1/decisions               → registrar decisión
```

### MCP Stdio

```json
{"method": "tools/list", "id": 1}
{"method": "tools/call", "id": 2, "params": {"tool": "activate_current", "arguments": {"query": "..."}}}
```

## Decisión de negocio (alternativa C ratificada)

La alternativa C está aprobada y no debe volver a discutirse:

- `pipeline_action` representa la acción interna del pipeline:
  - `PROTOTIPAR`: llevar la idea a prototipo en sombra
  - `DIVERGIR`: generar ideas divergentes

- `recommended_status` representa una decisión de negocio:
  - `ADOPTAR`
  - `AMPLIAR PRUEBA`
  - `ABANDONAR`
  - `ARCHIVAR PARA RECOMBINAR`

**Regla conservadora**: Mientras no exista una regla de negocio explícita y probada que justifique `ADOPTAR`:

- `len(families) >= 4` → `pipeline_action = "PROTOTIPAR"`, `recommended_status = "AMPLIAR PRUEBA"`
- `len(families) < 4` → `pipeline_action = "DIVERGIR"`, `recommended_status = "AMPLIAR PRUEBA"`

## Referencias

- `docs/INTEGRATION.md`: Integración con modelos
- `docs/STATE_MATRIX_CRIBA.md`: Matriz de estados visuales
- `docs/STYLE_GUIDE_CRIBA.md`: Tokens y estilo visual CRIBA
- `docs/STYLE_GUIDE_BLACKFORGE.md`: Tokens y estilo visual BLACKFORGE
- `docs/FINAL_REPORT.md`: Estado verificable actual