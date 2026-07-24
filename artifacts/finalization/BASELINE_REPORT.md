# BASELINE_REPORT — CRIBA + BLACKFORGE

Fecha: 2026-07-24
Perfil: KLSX_HERMES_UNIFICADO (KLSX Windows 11 profile) | Contrato: KLSX_TASK_CONTRACT_V1

## Estado confirmado (CONFIRMADO, no asumido; verificado con comandos)

- Raíz Git: `E:/PROYECTS/CRIBA` (git rev-parse --show-toplevel).
- Rama: `main` (git branch --show-current), tracking `origin/main`.
- Remoto: `https://github.com/klssxx/Criba-Blackforge.git` (existe; push hasta `f7ae486` OK).
- Commits HEAD: f7ae486 (docs FASE5) → d7d2bd6 → 7a375c5 → 53e669d → ca673ac → ed5467f.
- Tests: 204 passed verificado en Modal klssxx (run ap-GjvKog3yV2ykiMwhgp9PCz).
- mypy strict `src/criba`: rc=0, 20 archivos (run ap-bFrUh1HzQnT9n000T1NOHM).
- Engine end-to-end (smoke local): 12 ideas, pipeline_action=DIVERGIR, status=AMPLIAR PRUEBA.
- Blackforge pipeline (Modal): 7/7 tests passed (run ap-GOv3rzWwCEtAmDKVZwbKW4).

## Qué está realmente terminado

- Motor CRIBA (activate/diverge/value_score/cross_consistency).
- Motor Blackforge (catalog inmutable 723 / selector cuotas / safety S0-S3 /
  causal signature / headless pipeline 2.1).
- Tipado estricto FASE 3. Benchmark FASE 4. Handoffs FASE 4/5.
- Doc arquitectura: docs/ARCHITECTURE.md (Mermaid).
- Build spec PyInstaller: CRICA-Current-Engine.spec (entry scripts/portable_entry.py = CLI).

## Qué está parcialmente implementado / fuera de alcance

- GUI PySide6 (`src/criba/gui.py`): KI-001 SyntaxError preexistente, FUERA de
  alcance ratificado. El spec/build actual NO lo incluye (es CLI-only).
- Capa AGENTIC (`src/criba/agentic.py`): `get_layer("AGENTIC")` lanza
  NotImplementedError by-design (future hook). LOCAL_MVP es el único adapter activo.

## Build / packaging actual

- `CRICA-Current-Engine.spec`: PyInstaller onedir, entry `scripts/portable_entry.py`,
  pathex `src/`, datas `data/`→`data`. console=True, nombre `CRIBA-Current-Engine`.
  NO incluye Qt/PySide6 (correcto para CLI). NO incluye `imports/` (catálogo Blackforge)
  → el build CLI no empaqueta Blackforge a menos que se añada datas imports/.
- `scripts/build-portable.ps1`: ⚠️ USA `C:\Program Files\Blender Foundation\Blender 5.2\...python.exe`
  como intérprete. Esa ruta NO existe en este entorno → BLOCKER para FASE 9/14.
- `requirements-optional.txt`: PySide6, fastapi, uvicorn, mcp, pytest, pyinstaller.
- `pyproject.toml`: dependencies vacío (runtime solo stdlib) ✓; entrypoint `criba=criba.cli:main` ✓.

## Qué bloquea el release (hallazgos de build)

1. **BLOCKER-1 (build script)**: `scripts/build-portable.ps1` referencia Python de
   Blender inexistente. Debe usar el launcher fijado:
   `C:\Users\KLSX\AppData\Local\Programs\Python\Python312\python.exe` (o `.venv`).
2. **BLOCKER-2 (datas Blackforge)**: el spec NO añade `imports/blackforge_v2` a datas.
   El entry CLI `criba.cli:main` expone Blackforge vía `criba blackforge ...` (ver cli.py).
   Sin el catálogo empaquetado, el .exe no cargará Blackforge. Hay que añadir el datas.
3. **BLOCKER-3 (potencial, release)**: GitHub Release no verificado. Requiere `gh auth`
   + visibilidad. Fallback: dejar ZIP + SHA versionado en repo (RELEASE_REMOTE_BLOCKED).

## Riesgos tempranos

- Borrados del usuario en working tree (`D` sin stage): 01_TAREA_ACTUAL.txt, README_*.txt,
  *.cmd, *.zip, supervisor, etc. → NO se restauran ni se mezclan en commits de release.
- `.autoregen/*.json` modificados por automatización previa → fuera de mis commits.
- RAM: build PyInstaller puede usar >4GB. Ejecutar en isolation, un solo proceso pesado.

## Baselines numéricos

- Tests: 204 passed (Modal, 2026-07-24).
- mypy: rc=0, 20 archivos.
- Catálogo Blackforge inmutable: 723 registros, SHA-256
  1c698d540fbb22d6aa7e2f65bb8e59847109de1d093cfab4de8e817b4eab51cc.
