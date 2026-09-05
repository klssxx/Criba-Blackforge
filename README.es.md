# CRIBA

**El motor de ideación reproducible.** Determinista, auditable y local-first: la misma semilla siempre produce las mismas ideas — sin APIs de pago para obtener resultados útiles.

Motor local y determinista para exploración combinatoria, análisis causal e ideación de ciberseguridad defensiva. CRIBA combina un catálogo inmutable y versionado de métodos de innovación y seguridad con un selector reproducible basado en semilla, una pista de auditoría SQLite para cada idea y una expansión opcional con modelos gratuitos (Z.ai GLM y Nous `:free`).

> Versión en inglés: [README.md](./README.md).

---

## Por qué CRIBA

La mayoría de herramientas de "ideación con IA" son cajas negras: pides, sale texto, sin forma de saber por qué ni de reproducir el mismo resultado dos veces.

- **Determinista por defecto** — `--seed 42` produce resultados idénticos byte a byte en cualquier máquina.
- **Cada idea queda auditada** — traza SQLite por activación: métodos usados, puntuaciones, orden y versión exacta del catálogo.
- **Local sin fricción** — sin API key, sin red y sin telemetría para ejecutar el núcleo.
- **Expansión cloud gratis** — interpretación opcional de ideas con `GLM-5.3-flash` (Z.ai) y `poolside/laguna-s-2.1:free` (Nous Research), con fallback determinista si no hay red.
- **Catálogo integrado** — más de 130 técnicas de innovación y seguridad (TRIZ, Design Thinking, JTBD, FMEA, MITRE ATT&CK, OWASP, STRIDE, Kill Chain…) congeladas en JSON con esquema versionado.
- **Probado a conciencia** — más de 940 tests; el pipeline de release construye un ejecutable portable de Windows firmado con procedencia SLSA.

## Funcionalidades

| Capacidad | Descripción |
|---|---|
| `criba run` / `activate` | Selección determinista de métodos para una consulta, con puntuación reproducible y sesión persistida. |
| `criba lottery` | Doble lotería de ideación (asociativa + pura) con semilla explícita. |
| `criba blackforge` | Pipeline de ciberseguridad defensiva: amenazas, causalidad, propuestas y gates S0–S3. |
| `criba hybrid` | Pipeline completo ensemble → cadena → adversarial, con mejora semántica opcional. |
| `criba explain` / `compare` | Inspecciona por qué una sesión dio un resultado; compara dos sesiones. |
| `criba serve` | API JSON solo loopback (Swagger en `/docs`). |
| `criba mcp` | Servidor MCP por stdio: `activate_current`, `list_currents`, `explain_selection`, `build_model_prompt`, `record_decision`, `compare_runs`. |
| `criba gui` / `blackforge-gui` | Escritorio nativo PySide6 para CRIBA y BLACKFORGE. |
| Diálogo Modelos IA | Registra perfiles locales GGUF (llama.cpp) / Ollama; opción de expandir ideas con modelos cloud gratis. |

## Instalación

### Desde PyPI

```bash
pip install criba
```

o sin instalar nada:

```bash
uvx --from criba criba --help
```

> Las funciones opcionales de escritorio y de modelo requieren extras:
> `pip install "criba[gui,api,mcp]"`

### Desde el código fuente

```bash
git clone https://github.com/klssxx/Criba-Blackforge.git
cd Criba-Blackforge
uv sync --all-extras --locked
uv run criba --help
```

> En Windows también puedes usar el ejecutable portable precompilado (ver
> [Releases](https://github.com/klssxx/Criba-Blackforge/releases)).

## Demo de 60 segundos

```bash
criba lottery --query "¿cómo diseñar aprobaciones seguras para agentes autónomos?" --seed 42 --rounds 3 --batch-size 5
```

Ejecútalo dos veces. La misma semilla, las mismas rondas y el mismo batch producen **las mismas ideas**
— ese es el contrato de reproducibilidad sobre el que se construye todo.

Activación determinista simple:

```bash
criba run --query "reducir la energía de un datacenter en frío" --current auto --mode balanced --json
```

Workbench en Windows:

```powershell
scripts\launch_workbench.bat
```

## Garantía de reproducibilidad

- Los catálogos están congelados y versionados (`CURRENT_CATALOG_VERSION`, `SELECTOR_VERSION`).
- El selector usa semilla y orden canónico; el resultado es estable entre ejecuciones y máquinas.
- Cada activación escribe un registro auditable en SQLite (`artifacts/criba.sqlite3` por defecto).

## Expansión cloud gratis (opcional, 0€)

Cuando configuras un perfil GGUF/Ollama local *o* activas las rutas cloud gratuitas, CRIBA
conserva su núcleo determinista y usa el modelo solo para redactar ideas coherentes:

- **Z.ai** — `glm-5.3-flash` en `https://api.z.ai/v1`
- **Nous Research** — `poolside/laguna-s-2.1:free` en `https://api.nousresearch.com/v1` (env `NOUS_API_KEY`)

Si el modelo no responde, CRIBA degrada a su fallback determinista offline — la salida
nunca depende de la red. Las claves de cloud se leen solo de variables de entorno y
jamás se guardan en el repositorio.

## Inteligencia de innovación expandida (IIE)

El motor incluye adaptadores de prior art gratuitos y sin clave — OpenAlex, Crossref,
patentes EPO, fondos NSF, GitHub, Wikipedia — pensados para conectar las ideas generadas
con la evidencia que las apoya o las descarta, con controles de presupuesto y límites de
tasa (sin red en los tests de CI).

## Desarrollo

```bash
uv run pytest -q            # más de 940 tests
uv run mypy src/criba       # tipado estricto sobre el motor
uv run ruff check src       # lint
```

Las contribuciones son bienvenidas — ver [CONTRIBUTING](./CONTRIBUTING.md) y la
[política de seguridad](./SECURITY.md). Los releases se construyen desde tags y se
publican automáticamente con procedencia SLSA y un SBOM.

## Licencia

Apache License 2.0. Ver [LICENSE](./LICENSE) y [THIRD_PARTY_NOTICES](./THIRD_PARTY_NOTICES.md).