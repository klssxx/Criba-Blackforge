# Informe final

## IMPLEMENTADO

- Catálogo JSON extensible con las 12 corrientes solicitadas y 16 familias/métodos iniciales.
- Selector determinista con puntuación, razones, descartes y desempate lexicográfico.
- Flujo CRIBA C/R/I/B/A y `MANDATORY_MODEL_PACKET` trazable.
- SQLite para sesiones, paquetes, hashes de consulta, evidencia, decisiones y comparación.
- CLI, API FastAPI local con OpenAPI, servidor MCP stdio, GUI PySide6 y lanzadores PowerShell.
- Protección de tamaño de entrada, no ejecución de comandos de la consulta, sin red ni credenciales por defecto, y experimentos con sandbox/rollback/guardrails.

## PROBADO

- `pytest -q --basetemp=.pytest-temp`: **11 passed** (ejecutado el 2026-07-23).
- Incluye selector, métodos no redundantes, paquete, entradas adversariales, Unicode, persistencia, reapertura, comparación y API FastAPI.
- La GUI inició y cerró limpiamente con Qt en modo `offscreen` (prueba automatizada de ciclo de vida).
- PyInstaller generó correctamente `dist/CRIBA-Current-Engine/CRIBA-Current-Engine.exe`; el ejecutable fue invocado con `list-currents` y cargó el catálogo incluido.

## VERIFICADO

- La demostración se generó con `scripts/demo.py`, guardó evidencia y reabrió su sesión desde SQLite.
- La API usa OpenAPI/Swagger cuando FastAPI está instalado y se niega a escuchar fuera de loopback.

## PARCIAL

- La GUI ofrece activación y resultados completos; Biblioteca, Historial e Integraciones avanzados son accesibles mediante CLI/API, no como pantallas visuales dedicadas.
- La interfaz visual verifica activación y resultado; las pantallas visuales dedicadas para Biblioteca, Historial e Integraciones avanzados siguen pendientes.

## NO IMPLEMENTADO

- Gateway que llame directamente a un proveedor: se entrega el prompt enriquecido independiente de proveedor, pero no un cliente de proveedor para evitar claves, costes y dependencia concreta.
- Forzar técnicamente que un modelo externo use MCP: CRIBA ofrece contrato e instrucción, pero ello depende del cliente que lo orquesta.
