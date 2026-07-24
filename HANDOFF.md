# AUTOREGENERATION_CHECKPOINT

Fecha: 2026-07-24

Motivo: checkpoint operativo tras desbloquear la ejecución remota en Modal.

## Estado verificado

- Entorno de verificación: Modal cloud, workspace `klssxx`; nunca ejecutar suites
  ni análisis pesados en la máquina local.
- Suite completa: **200 passed**, 1 warning no bloqueante, 3.67 s.
  Ejecución: https://modal.com/apps/klssxx/main/ap-UjqFcoO9TXIGqdYquvIXtq
- `mypy --strict` en nube: PASS para `src/criba/genome.py`,
  `src/criba/blackforge_causal.py` y `src/criba/blackforge_safety.py`.
- La causa del bloqueo no era el código: el CLI de Modal abortaba al escribir
  un carácter Unicode en una consola Windows `charmap`, y los handoffs antiguos
  ordenaban un falso `HUMAN_DECISION_REQUIRED` si Hermes no mostraba terminal.

## Punto de partida

FASE 3 — TIPADO Y CONTRATOS: **COMPLETADA Y VERIFICADA** (ver gate abajo).
No repitas los checks ya PASS ni la suite completa si no hay cambios de código.
Inspecciona primero los diffs no confirmados y conserva los cambios del
usuario. Crea commits atómicos solo de módulos de FASE 3 que hayas revisado;
no hagas push, reset, clean ni checkout destructivo.

Los invariantes protegidos siguen siendo:

- `value_score = evidence * novelty / cost`;
- `recommended_status` pertenece a `VALID_DECISIONS` y no se adopta por número
  de familias;
- `pipeline_action` es independiente y solo vale `PROTOTIPAR` o `DIVERGIR`;
- no regenerar goldens;
- no tocar `gui.py` ni theme (KI-001 preexistente).

### GATE FASE 3 — CERRADO (2026-07-24, verificación Modal klssxx)

- `mypy --strict` sobre `src/criba` vía `[tool.mypy]` de pyproject.toml:
  **rc=0 — Success: no issues found in 20 source files**.
  Comando: `modal run .autoregen/cloud/modal_runner.py::mypy_scoped`
  Run: https://modal.com/apps/klssxx/main/ap-bFrUh1HzQnT9n000T1NOHM
- Contratos tipados (Idea, Decision, Packet, pipeline_action, recommended_status,
  resultado causal, safety decision) ya en fases previas; `pipeline_action`
  separado de `recommended_status` (ratificado en la directiva).
- Suite completa final del bloque: **204 passed, 1 warning, 3.30 s** (el
  warning es deprecación FastAPI/Starlette por `httpx`, no bloqueante).
  Comando: `modal run .autoregen/cloud/modal_runner.py::pytest_full`
  Run: https://modal.com/apps/klssxx/main/ap-9KyTj5LA8SgYHD7jBnAkCw
- No quedan módulos con errores de tipado: el objetivo "siguiente módulo con
  errores pendientes" de la directiva ya no aplica; FASE 3 terminó.

## Lanzador remoto obligatorio

`02_INICIAR_AUTOREGENERACION.cmd` ya establece UTF-8 y expone
`MODAL_PYTHON=C:\Users\KLSX\AppData\Local\Programs\Python\Python312\python.exe`.

Cada invocación de Modal debe heredar:

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONIOENCODING='utf-8'
& $env:MODAL_PYTHON -m modal run .autoregen\cloud\modal_runner.py::<entrypoint>
```

Si Hermes no recibe terminal pero sí `execute_code`, puede usarlo únicamente
como puente para lanzar ese proceso Modal remoto y para git no destructivo o
commits atómicos. No puede ejecutar pytest, mypy, coverage, benchmarks ni
Python del proyecto en local.

## Próxima acción exacta

FASE 3 completa: no hay más errores de tipado. La próxima fase es **FASE 4 —
RENDIMIENTO Y RECURSOS**, siguiendo la sección 7 de `01_TAREA_ACTUAL.txt`:

1. Leer la sección 7 (FASE 4) de `01_TAREA_ACTUAL.txt`.
2. Benchmark reproducible con el catálogo real de 723 registros, midiendo por
   separado: carga/validación, índices, selección, safety gate, firma
   causal y pipeline headless. Usar el entrypoint existente
   `modal run .autoregen/cloud/modal_runner.py::benchmark_blackforge`
   (warm-up corto, máximo 3–5 repeticiones, sin duplicar el catálogo en
   memoria; respetar límites de RAM).
3. Revisar complejidad (bucles anidados, búsquedas lineales repetidas,
   serialización/copias reiteradas, firmas/índices recalculados) y aplicar
   optimizaciones con perfil previo.
4. Añadir prueba de regresión de performance estable (comparar complejidad /
   reuso de índices, umbral generoso basado en mediciones).
5. Commits atómicos Conventional Commits por cada bloque; actualizar
   HANDOFF.md y `session_handoff.json` con comando, resultado, enlace Modal y
   siguiente acción.
Estado: FASE 3 CLOSED — READY FOR FASE 4.
