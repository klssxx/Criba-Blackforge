# JUDGES.md — Criterios de evaluación (Jueces / Auditores)

Este documento define cómo un juez o revisor externo debe verificar la
entrega `v0.1.0` de CRIBA + BLACKFORGE sin depender de la afirmación del autor.

## Evidencia verificable (reproducible, estado FINAL local)
1. **Tests**: `python -m pytest -q` → **213 passed** (suite completa con
   adaptadores opcionales). Ver `artifacts/finalization/TEST_EVIDENCE.md` y
   `TEST_RESULTS.json`.
2. **Tipado**: `python -m mypy src/criba` → rc=0 (0 issues, 20 archivos).
3. **Compilación**: `python -m compileall src` → rc=0 (gui.py compila; KI-001
   resuelto).
4. **Smoke del ejecutable**: `.exe` GUI real lanzado en display real — ventana
   visible (1364x779), fuentes renderizadas, "Base de datos: ✔", pipeline
   verificado headless. Ver `artifacts/finalization/EXECUTABLE_SMOKE_TEST.md`.

## Criterios de aceptación (gates)
- BASELINE_VERIFIED ✅ (artifacts/finalization/BASELINE_REPORT.md)
- BLUEPRINT_VERIFIED ✅ (.hermes/plans/.../BLUEPRINT.md)
- QUALITY_GATES_PASS ✅ (213 passed + mypy rc=0)
- GUI_SMOKE_PASS ✅ (ventana real + render + BD; clic-through NO ejecutado,
  denegado por usuario — ver nota de honestidad)
- PORTABLE_EXECUTABLE_PASS ⚠ PARTIAL (arranque/render/BD/pipeline OK;
  interacción por clic no ejecutada)
- HASH_AND_MANIFEST_VERIFIED ✅ (SHA-256 + BUILD_MANIFEST.json)
- GIT_STATE_VERIFIED ✅ (commits por intención: fix/build)
- RELEASE_READY_NOT_PUBLISHED ✅ (preparado; publicación requiere AUTORIZO PUBLICAR)

## Lo que NO está en este release (honestidad)
- Smoke de interacción por CLIC en la GUI: no ejecutado (denegado por usuario);
  no se inventa su resultado. La lógica subyacente sí está verificada headless.
- Capa AGENTIC: future hook, no implementada.
- Ejecutable no firmado (SmartScreen/AV pueden avisar).

## Cómo un juez reproduce el build
```powershell
.\.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean CRIBA-Blackforge.spec
# SHA-256 del ZIP resultante:
#   bf0eef4ac374027017aba7bd38045a3e1f22772aed0e23c06abcd7e711d0599b
```
