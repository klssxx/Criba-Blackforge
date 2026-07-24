# TEST_EVIDENCE — CRIBA + BLACKFORGE (estado final)

Todos los comandos ejecutados sobre el estado FINAL del repo (post-fix), no
reutilizados de runs previos.

## Entorno
- Directorio: E:/PROYECTS/CRIBA
- Intérprete: .venv (Python 3.11.15)
- PYTHONPATH=src ; QT_QPA_PLATFORM=offscreen (para tests GUI)
- Fecha: 2026-07-24 (UTC)

## Comandos y resultados

### 1. Compilación
```
python -m compileall src
```
- exit code: 0
- resultado: OK (gui.py compila tras fix KI-001)

### 2. Suite completa
```
python -m pytest -q
```
- exit code: 0
- resultado: **213 passed, 1 warning** (~2.7s)
- warning: StarletteDeprecationWarning (httpx en TestClient) — no bloqueante

### 3. Análisis estático estricto
```
python -m mypy src/criba
```
- exit code: 0
- resultado: **Success: no issues found in 20 source files**
- nota: gui.py excluida vía config pyproject (KI-001 histórico ya resuelto;
  la exclusión se mantiene porque gui.py no está en el scope tipado ratificado)

## Por qué el número cambió (203/204 → 213)
El conteo previo (project_completed.json: 203 passed) se hizo SIN las
dependencias opcionales instaladas, por lo que los tests de los adaptadores
API/MCP/GUI no se recogían o se saltaban. Tras instalar
fastapi/uvicorn/mcp/httpx/PySide6 en el .venv, la suite canónica recoge y pasa
**213** tests. No se añadieron ni eliminaron tests de producto; el delta es por
recolección completa de la suite ya existente.

## Gate
QUALITY_GATES_PASS = TRUE (pytest verde + mypy strict 0 issues)
