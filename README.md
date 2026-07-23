# CRIBA CURRENT ENGINE

Motor local, determinista y explicable que prepara un paquete de análisis antes de que otro modelo responda. El paquete no contiene cadena de pensamiento: contiene supuestos, contraejemplos, hipótesis falsables, propuestas trazables, guardrails y una decisión provisional.

## Inicio rápido en Windows

Desde PowerShell:

```powershell
.\scripts\criba.ps1 activate --query "¿Cómo diseñar aprobaciones seguras para agentes?" --current auto
.\scripts\criba.ps1 serve
.\scripts\criba.ps1 gui
```

La API queda ligada exclusivamente a `127.0.0.1:8765`; OpenAPI/Swagger está en `http://127.0.0.1:8765/docs`.

## Interfaces

- CLI: `activate`, `run`, `build-prompt`, `list-currents`, `explain`, `compare`, `serve`, `mcp`, `gui`.
- API: `POST /v1/activate`, `/v1/run`, `/v1/build-prompt`, `/v1/compare`, `/v1/decisions`; `GET /v1/currents`, `/v1/methods`, `/v1/sessions/{id}`, `/health`.
- MCP stdio: `activate_current`, `list_currents`, `explain_selection`, `run_criba`, `build_model_prompt`, `record_decision`, `compare_runs`.
- GUI PySide6: activación, resultados por pestaña y copia del prompt. La biblioteca e historial están disponibles por API/CLI; su editor visual es una ampliación pendiente.

## Integración MCP

Configure su cliente para lanzar (ajuste la ruta si es necesario):

```json
{"command":"powershell.exe","args":["-ExecutionPolicy","Bypass","-File","E:\\PROYECTS\\CRIBA\\scripts\\criba.ps1","mcp"]}
```

El cliente debe invocar `activate_current` antes de su respuesta final. El campo `model_instruction` y `response_contract` expresan esta obligación, pero CRIBA no puede imponer el comportamiento de un cliente/modelo externo.

## Seguridad

CRIBA no ejecuta comandos provenientes de consultas, no lee credenciales, no envía consultas a red ni modifica proyectos. Los experimentos son planes para sandbox con límite de daño, rollback y stop criterion. Las sesiones SQLite guardan la consulta: protéjalas como información potencialmente sensible.

## Paquete Windows

Con PyInstaller instalado, ejecute `./scripts/build-portable.ps1`. El resultado se genera en `dist/CRIBA-Current-Engine`. La build incluye los catálogos JSON. No se distribuye un intérprete Python independiente en este repositorio.

## Verificación

```powershell
$env:PYTHONPATH = (Resolve-Path .\src).Path
& 'C:\Program Files\Blender Foundation\Blender 5.2\5.2\python\bin\python.exe' -m pytest -q --basetemp=.pytest-temp
```

Ver [`docs/FINAL_REPORT.md`](docs/FINAL_REPORT.md) para el estado verificable.

