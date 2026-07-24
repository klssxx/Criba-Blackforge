# CRIBA + BLACKFORGE

**C**urrent **R**ebels **I**nnovation **B**reakthrough **A**rchitecture — motor de
innovación estructural determinista, con el pipeline **BLACKFORGE** (catálogo
inmutable de 723 registros, selector determinista, safety gate S0–S3, firma
causal, salida packet 2.1).

> Estado: funcional end-to-end con **GUI de escritorio PySide6 incluida** en el
> release portable. Suite de **213 tests** en verde y `mypy --strict` rc=0 sobre
> 20 archivos fuente (ver `artifacts/finalization/TEST_EVIDENCE.md`). El defecto
> KI-001 (`SyntaxError` en `gui.py`) está **resuelto**.

## Arquitectura

Ver `docs/ARCHITECTURE.md` (diagrama Mermaid, contratos y flujos).

- **Motor CRIBA** (`src/criba/engine.py`): `activate()` → selección de corriente,
  métodos, rupturas, divergencia por 5 ejes causales, cross-consistency,
  similitud, scoring (`value_score = evidence*novelty/cost`), decisión.
- **Pipeline BLACKFORGE** (`src/criba/blackforge_pipeline.py`): `run_headless()`
  sobre catálogo inmutable → selector + safety + firma causal + convergencia →
  packet 2.1.
- **GUI** (`src/criba/gui.py`): app PySide6/Qt6, tema oscuro premium.
- **Entrypoints**: GUI (`criba.gui:run`), CLI (`criba.cli:main`), API loopback
  (`api.py`), MCP stdio (`mcp_server.py`).

## Desarrollo

```bash
# Entorno (Windows 11 x64, .venv local del proyecto)
python -m pip install -e ".[gui,api,mcp,dev,build]"
python -m pytest                     # suite: 213 passed
python -m mypy src/criba             # tipado strict: 0 issues
```

## Build portable (Windows)

El build usa PyInstaller `onedir` (windowed, con Qt/PySide6 empaquetado) desde
`CRIBA-Blackforge.spec`:

```powershell
.\scripts\build-portable.ps1
# equivalente a:
.\.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean CRIBA-Blackforge.spec
```

Salida: `dist\CRIBA-Blackforge\CRIBA-Blackforge.exe`.

## Download the Windows portable build

Descarga el ZIP portable (no requiere Python/Git/Docker/API key):

1. **Descargar** el asset `CRIBA-Blackforge-Portable-Windows-x64.zip` desde
   [GitHub Releases](https://github.com/klssxx/Criba-Blackforge/releases).
2. **Verificar SHA-256** (PowerShell):

   ```powershell
   Get-FileHash -Algorithm SHA256 .\CRIBA-Blackforge-Portable-Windows-x64.zip
   ```

   SHA-256 esperado:

   ```
   bf0eef4ac374027017aba7bd38045a3e1f22772aed0e23c06abcd7e711d0599b
   ```

   Compáralo siempre con el fichero `.sha256` que acompaña al ZIP.

3. **Extraer** en una carpeta (p.ej. `C:\CRIBA`).
4. **Ejecutar** `CRIBA-Blackforge.exe` (doble clic; abre la GUI).
5. **Demo en 60 segundos**: escribe una consulta en el cuadro inferior y pulsa
   **▶ EJECUTAR CRIBA**; revisa el resumen, métricas y decisión a la derecha.

Consulta `FIRST_RUN_ES.md` / `FIRST_RUN_EN.md` dentro del ZIP para la guía
completa.

## Limitaciones conocidas

- La base de datos SQLite portable se guarda en
  `%LOCALAPPDATA%\CRIBA-Blackforge\criba.sqlite3`.
- Capa `AGENTIC` es un future hook (no implementado by design); solo el flujo
  `LOCAL_MVP` está activo.
- El ejecutable no está firmado (SmartScreen/AV pueden avisar en el primer uso).
- Adaptadores API local / MCP no activos por defecto; el flujo básico no los
  necesita.

## Licencia

Ver `THIRD_PARTY_NOTICES.md` en el build portable y el archivo LICENSE del
repositorio.
