# Integración de catálogos de métodos

## Estado runtime

CRIBA compone en tiempo de ejecución **7.201 métodos con ID único** desde
fuentes JSON versionadas. `src/criba/catalog.py` es el punto de composición y
rechaza cualquier colisión de ID antes de entregar el catálogo al motor.

| Capa | Entradas | Ubicación |
|---|---:|---|
| Catálogo unificado base | 6.870 | `data/methods/library_combined.json` |
| Fuentes meta aprobadas | 235 | `data/methods/sources/source_*.json` |
| Extensión exclusiva del MASTER | 30 | `data/methods/sources/source_escape_master_unique.json` |
| Métodos fundacionales | 66 | `data/methods/archive/library_expanded.json` |
| **Total runtime** | **7.201** | `criba.catalog.methods()` |

La ubicación histórica de los 66 métodos se conserva, pero el cargador los
incluye explícitamente y añade en memoria `source=foundational_methods`,
`granularity=method` y `origin=internal` cuando faltan esos campos. No se carga
ningún otro archivo de `archive/`.

## Composición por granularidad

| Granularidad | Cantidad |
|---|---:|
| `micro_technique` | 5.394 |
| `method` | 1.178 |
| `framework` | 585 |
| `facilitation_pattern` | 25 |
| `group_game` | 19 |

Las 301 entradas meta/fundacionales sin eje canónico se mantienen como
`unspecified`; el selector las asigna por familia al eje funcional apropiado.
Los cinco ejes base suman 6.900 entradas: 1.700 perspectivas, 900 técnicas de
generación, 1.100 de ruptura, 1.130 de escape y 2.070 metodologías.

## Extensión MASTER trazable

El MASTER de 1.030 técnicas y el ampliado de escape se comparan por nombre
normalizado Unicode. El resultado son exactamente las entradas 1001–1030,
ausentes del ampliado. Cada registro conserva `source_number` y `source_ref`.
La entrada 1 del MASTER no se volvió a añadir porque ya tiene equivalente en la
base ampliada.

Para regenerar la fuente desde los documentos originales:

```powershell
uv run python scripts/import_escape_master.py `
  --master C:\ruta\1030_tecnicas_salto_fuera_espacio_conocido_MASTER.txt `
  --expanded C:\ruta\1100_tecnicas_salto_espacio_conocido_AMPLIADO_VALIDADO.txt `
  --output data\methods\sources\source_escape_master_unique.json
```

El importador aborta si el resultado deja de ser 30, evitando cambios
silenciosos por una fuente distinta o un parser regresivo.

## Uso

```python
from criba.catalog import methods, frameworks, methods_by_source

all_methods = methods()  # 7.201
meta_frameworks = frameworks()
master_extension = methods_by_source("escape_1030_master")
```

La lotería usa este catálogo compuesto cuando no se proporciona
`--methods-file`. Un JSON personalizado sigue siendo válido mediante esa
opción.

## Verificación

```powershell
uv run python scripts/count_catalogs.py
uv run python scripts/verify_library.py
uv run pytest -q tests/unit/test_catalog_runtime.py
```

Los documentos de investigación, el PDF y la imagen de referencia de `ee` no
forman parte del catálogo ejecutable y no se publican automáticamente.
