# PACKAGING DEPENDENCY AUDIT — CRIBA + BLACKFORGE

Fecha: 2026-07-24 | FASE 5 (revisión de pyproject y dependencias)

## pyproject.toml (estado actual)

```toml
[project]
name = "criba-current-engine"
version = "0.1.0"            # semver válido
requires-python = ">=3.10"
[project.scripts]
criba = "criba.cli:main"    # entrypoint apunta a función real ✅
[tool.setuptools]
package-dir = {"": "src"}
[tool.mypy]
strict = true; exclude gui.py (KI-001)
```

## Hallazgos

| Ítem | Estado | Nota |
|------|--------|------|
| Nombre paquete | ✅ | `criba-current-engine` coherente con `__init__.__version__=0.1.0` |
| Versión semver | ✅ | 0.1.0 |
| requires-python | ✅ | >=3.10 (compatible con launcher 3.12) |
| build backend | ✅ | setuptools (estándar) |
| packages | ✅ | find where=src |
| entrypoint | ✅ | `criba=criba.cli:main` real |
| runtime deps | ✅ | vacío → core usa solo stdlib (óptimo) |
| dev/optional deps | ⚠️ | en `requirements-optional.txt` suelto, NO en `[project.optional-dependencies]` |

## Recomendación

El pyproject ya está **óptimo para runtime mínimo**. No se rompe el formato.
Mejora menor opcional (NO bloqueante, NO obligatoria): mover
`requirements-optional.txt` a `[project.optional-dependencies]` formal:

```toml
[project.optional-dependencies]
gui = ["PySide6>=6.7"]
api = ["fastapi>=0.115", "uvicorn>=0.30"]
mcp = ["mcp>=1.0"]
dev = ["pytest>=8.0", "mypy", "pyinstaller>=6.0"]
```

Decisión: **NO cambiar** (el prompt prohíbe cambiar formato sin necesidad;
`requirements-optional.txt` ya documenta las dependencias opcionales y el build
las resuelve). Se mantiene tal cual.

## Dependencias para el build portable

El build CLI portable requiere (en .venv local, no global):
- `pyinstaller>=6.0` (empaquetado)
- El core NO requiere PySide6 (es CLI). PySide6 solo si se empaqueta GUI (fuera alcance KI-001).
- Blackforge CATÁLOGO (`imports/blackforge_v2`) es data JSON, no dependencia pip.

## Acción

No se modifica pyproject.toml. Se documenta el estado óptimo.
