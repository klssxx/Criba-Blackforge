# CRIBA + BLACKFORGE

Motor local y determinista para exploración combinatoria, análisis causal y
ciberseguridad defensiva. Esta aplicación es independiente de SUPRA y no
requiere conexión a un proveedor de modelos para ejecutar su núcleo.

## Componentes

- **CRIBA Current Engine**: catálogo inmutable de métodos, selección
  reproducible, puntuación y persistencia SQLite.
- **BLACKFORGE**: análisis de amenazas, causalidad, propuestas defensivas y
  gates de seguridad S0–S3.
- **Interfaces**: CLI, GUI Windows, API/MCP local y workbench web.
- **Modelos opcionales**: `llama_cpp` y `ollama`; el fallback determinista
  conserva la salida si un runtime externo no está disponible.

## Organización local

```text
E:\PROYECTS\
├── CRIBA\                         # esta aplicación
├── SUPRA\                         # aplicación agentic independiente
└── CRIBABLACKFORGE_LEGACY_BACKUP\ # copia histórica aislada
```

CRIBA no importa módulos de SUPRA y SUPRA no importa módulos de CRIBA. El
backup histórico se conserva fuera de ambos runtimes y no se usa en ejecución.

## Ejecución

Desde la raíz del repositorio:

```bash
python -m criba.cli
```

En Windows también está disponible:

```text
scripts\launch_workbench.bat
```

La GUI y los servicios locales permanecen separados del proveedor de modelos.
La configuración opcional de modelos se guarda fuera del repositorio en
`%LOCALAPPDATA%\CRIBA-Blackforge\models.json`; las claves no se incluyen en
archivos del proyecto.

## Verificación

```bash
python -m pytest -q
```

Las pruebas cubren catálogo, selección reproducible, causalidad, seguridad,
interfaces, persistencia y contratos de UI. Los artefactos de auditoría se
escriben en `artifacts/` y `verification/`.

## Relación con SUPRA

SUPRA vive en `E:\PROYECTS\SUPRA` como aplicación separada. Su runner
provider-neutral soporta Hermes/Nous, Ollama, OpenAI y endpoints compatibles
con OpenAI; esa integración no modifica el motor local CRIBA/BLACKFORGE.

## Licencia

Apache License 2.0. Consulte [LICENSE](LICENSE).
