# Inventario y retirada de SUPRA (2026-09-07)

Mandato §1: SUPRA queda retirado del producto activo, sin destruirlo.

## Proyecto conservado (inactivo)

- Ubicación: `C:\Users\KLSX\Music\INNOVATIONS\ACTIVE\SUPRA`
- Git: rama `main` @ `6dca3d9` (up to date con origin/main), con cambios preexistentes sin confirmar (6 modificados + 4 sin seguimiento: CI, Dockerfile, README, pyproject, launch_supra.bat, service.py; release.yml, pre-commit, CHANGELOG, uv.lock). **No se han tocado.**
- Sin dependencia de empaquetado ni de arranque en CRIBA (verificado abajo).

## Referencias restantes en el repo de CRIBA (históricas, permitidas)

| Archivo | Referencia | Por qué se conserva |
|---|---|---|
| `src/criba/intelligence/enums.py:52` | `LEGACY_SUPRA = "LEGACY_SUPRA"` | Valor de enum para procedencia de datos históricos. |
| `src/criba/intelligence/registry.py:15` | owner `SUPRA_ORCHESTRATION`, `CRIBA_PLUS_SUPRA` | Aliases de procedencia de registros antiguos. |

## Retirada aplicada

- `scripts/verify-dev-environment.sh` / `.ps1`: SUPRA eliminado de la
  verificación del entorno (ya no se exige su checkout para validar CRIBA).

## Evidencia de que el producto no requiere SUPRA

- `grep -rni supra src/ scripts/ pyproject.toml CRIBA.spec CRIBA-Blackforge.spec` → solo las 7 referencias listadas arriba (2 históricas en código + comentarios de los scripts).
- Sin imports de `supra_agentic` en `src/` (verificado por búsqueda).
- Suite completa (826 tests en la fecha de este documento) pasa sin SUPRA.
- La app arranca, genera y exporta sin lanzar o requerir SUPRA (smoke offscreen de `criba.gui` y `criba.blackforge_gui`).
