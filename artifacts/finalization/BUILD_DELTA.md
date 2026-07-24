# BUILD_DELTA — CRIBA + BLACKFORGE Portable v0.1.0

Scope of change versus the previous CLI-only portable build.

## Qué cambió
- El portable pasa de **solo-CLI** a **GUI + CLI** (dos ejecutables, un runtime).
  - `CRIBA-Blackforge.exe` ahora es la app de escritorio PySide6 (ventana, sin
    consola), pensada para usuario no técnico.
  - `CRIBA-Blackforge-CLI.exe` es la interfaz de línea de comandos para
    automatización.
- Se empaqueta PySide6/Qt6 y el módulo `criba.gui` (antes excluidos).
- Se empaqueta `imports/blackforge_v2/` (catálogo BLACKFORGE 723) explícitamente.

## Qué se corrigió
- **GUI runtime bug (defecto real)**: `gui.render()` leía claves inexistentes del
  motor (`changed_variable`, `primary_metric`, `proposal`,
  `main_assumption_attacked`, `rival_hypothesis`, `adversarial_case`) →
  `KeyError` en cada activación. Reescrito contra el esquema real del engine
  (`damage_limit`, `sandbox`, `rollback`, `broken_assumptions`, `operations`,
  `ideas[].title`). La GUI ya no crashea al ejecutar CRIBA.
- **Subcomando `gui` roto en el .exe CLI-only anterior**: lanzaba
  `ModuleNotFoundError: No module named 'criba.gui'`. Resuelto: la GUI ahora es
  un ejecutable dedicado con el módulo empaquetado.
- **Acentos corruptos en consola (cp1252)**: `portable_entry.py` fuerza UTF-8 en
  stdout/stderr. Salida en español correcta.
- **Referencia rota en el spec**: `CRIBA-Blackforge.spec` apuntaba a
  `scripts/portable_entry_gui.py`, que no estaba versionado. Añadido el archivo.
- **Comentarios mypy obsoletos**: se retiró la mención a "KI-001 SyntaxError"
  (ya resuelto); se documenta que `gui.py` se verifica por ejecución, no por tipos.

## Qué NO cambió
- Motor CRIBA y pipeline BLACKFORGE (algoritmos intactos; sin tocar para "pasar"
  pruebas).
- Catálogo BLACKFORGE inmutable (mismo SHA-256, 723 registros).
- Arquitectura general (entrypoints CLI/API/MCP/GUI; sin reinvención).

## Qué se descartó / queda fuera
- Capa AGENTIC: sigue siendo un future hook (NotImplementedError by design).
  No se implementa; no se promete en la GUI.
- Tipado estricto de `gui.py`: fuera de alcance (código de vista; verificado por
  smoke + contrato UI 11/11). Desviación documentada.
- No se restauran ni se mezclan los borrados del usuario en el working tree
  (`01_TAREA_ACTUAL.txt`, `README_PRIMERO*.txt`, `*.cmd`, `*.zip`, supervisor).

## Qué continúa pendiente
- Publicación del GitHub Release (dejado PREPARADO, no publicado, salvo tu orden).
