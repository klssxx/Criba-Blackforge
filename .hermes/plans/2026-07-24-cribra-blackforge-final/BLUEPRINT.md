# BLUEPRINT — CRIBA + BLACKFORGE Finalización, Auditoría, Ejecutable y Release

Fecha: 2026-07-24
Perfil: KLSX_HERMES_UNIFICADO (equipo sénior coordinado)
Contrato: KLSX_TASK_CONTRACT_V1 (modo EXEC, gates GREEN/YELLOW automático; RED requiere gate literal)

## Objetivo medible (FASE 5.1)

Entrega verificable cuando exista:
- [x] aplicación funcional (engine + Blackforge pipeline, 204 passed)
- [x] GUI verificable (KI-001: gui.py SyntaxError → FUERA de alcance; no se promete)
- [x] suite crítica aprobada (204 passed, Modal)
- [x] análisis estático aprobado (mypy strict rc=0, 20 archivos)
- [~] build Windows reproducible (spec existe; .ps1 debe corregirse)
- [ ] ejecutable portable (.exe no generado aún en esta sesión)
- [ ] ZIP final + SHA-256 + manifest
- [ ] guía de primer uso (FIRST_RUN_ES/EN)
- [ ] documentación bilingüe mínima
- [x] evidencias (runs Modal, commits, handoffs)
- [~] Git limpio (borrados del usuario respetados, fuera de mis commits)
- [ ] Release listo o bloqueo externo documentado

## Arquitectura actual (FASE 5.2)

Entrypoints:
- CLI: `src/criba/cli.py` → `criba.cli:main` (entrypoint pyproject)
- API: `src/criba/api.py` (HTTP loopback / FastAPI opcional)
- MCP: `src/criba/mcp_server.py` (JSON-RPC stdio)
- GUI: `src/criba/gui.py` (PySide6, KI-001 SyntaxError → FUERA alcance)
- Portable entry: `scripts/portable_entry.py` (usado por PyInstaller spec)

Módulos CRIBA:
- engine.py (orquestación activate/build_prompt/value_score)
- genome.py (ontología cerrada, normalize_proposal)
- similarity.py (detección de duplicados)
- selector.py / methods.py / catalog.py / constants.py / storage.py / agentic.py
- engine_v1_audit_intent.py / migration.py

Módulos BLACKFORGE:
- blackforge_catalog.py (723 regs inmutables, MappingProxyType)
- blackforge_selector.py (cuotas deterministas)
- blackforge_safety.py (gate S0–S3)
- blackforge_causal.py (firma causal SHA-256)
- blackforge_pipeline.py (headless packet 2.1)

Recursos:
- data/ (currents, methods, assets, temas, esquemas)
- imports/blackforge_v2/ (catálogo 723)
- verification/ (artifacts de golden/benchmark)

Build:
- CRICA-Current-Engine.spec (PyInstaller, entry scripts/portable_entry.py, pathex src/, datas data/)
- scripts/build-portable.ps1 (⚠️ USA PYTHON DE BLENDER → debe corregirse)
- requirements-optional.txt (PySide6, fastapi, uvicorn, mcp, pytest, pyinstaller)

Tests:
- tests/unit (24), tests/integration, tests/adversarial

## Arquitectura objetivo (FASE 5.3)

La actual es suficiente. NO se reinventa arquitectura.
Cambios mínimos necesarios:
1. Corregir `build-portable.ps1` para usar el launcher Python 3.12 autorizado
   (C:\Users\KLSX\AppData\Local\Programs\Python\Python312\python.exe), no Blender.
2. El spec actual NO incluye PySide6/Qt ni imports/ (Blackforge catalog).
   Para un build SOLO-CLI portable basta; si se quiere GUI hay que añadir Qt + imports/.
   Decisión: build CLI portable primero (alcance seguro); GUI queda fuera por KI-001.
3. Documentación + SHA + manifest + Release.

## DAG de fases (FASE 5.4)

| ID | Objetivo | Dependencias | Skill | Evidencia | Criterio |
|----|----------|------------|-------|-----------|----------|
| F0 | Blueprint + baseline | - | codebases-inspection | BLUEPRINT.md, BASELINE_REPORT | VERIFIED |
| F1 | Inspect repo Git/estado | F0 | - | GIT_STATE_BEFORE | VERIFIED |
| F2 | Deuda/TODO/placeholders | F1 | - | DEBT_AUDIT | VERIFIED (limpio) |
| F3 | Revisión funcional motor | F2 | - | ENGINE_VERIFICATION | VERIFIED (204 passed) |
| F4 | Property-based (Hypothesis) | F3 | - | PROPERTY_TEST_DECISION | NO_CHANGE_JUSTIFIED si no aporta |
| F5 | Review pyproject/deps | F3 | - | PACKAGING_DEPENDENCY_AUDIT | VERIFIED |
| F6 | Audit GUI PySide6 | F5 | pyside6-desktop-gui | UI/ACCESSIBILITY/VISUAL | N/A (KI-001 fuera alcance) |
| F7 | Correcciones | F2-F6 | systematic-debugging | diff + tests | por-fase |
| F8 | Validación técnica | F7 | - | TEST_EVIDENCE | 204 passed re-run |
| F9 | Build Windows portable | F8 | klsxbuild/appbuilder | dist/ ZIP | PORTABLE_EXECUTABLE_PASS |
| F10 | Smoke test .exe real | F9 | - | EXECUTABLE_SMOKE_TEST | PASS |
| F11 | Manifest + SHA + provenance | F10 | - | BUILD_MANIFEST/SHA | HASH_VERIFIED |
| F12 | Docs usuario | F11 | - | README/USER_GUIDE | docs listas |
| F13 | Git profesional | F12 | github-repo-management | commits atómicos | GIT_STATE_VERIFIED |
| F14 | Repo GitHub | F13 | gh-cli-pitfalls | gh repo view | REPO_OK o BLOCKED |
| F15 | Release GitHub | F14 | - | gh release | RELEASE_PUBLISHED o BLOCKED |

Gates: BASELINE_VERIFIED → BLUEPRINT_VERIFIED → QUALITY_GATES_PASS →
GUI_SMOKE_PASS (N/A) → PORTABLE_EXECUTABLE_PASS → HASH_AND_MANIFEST_VERIFIED →
GIT_STATE_VERIFIED → RELEASE_PUBLISHED/BLOCKED.
