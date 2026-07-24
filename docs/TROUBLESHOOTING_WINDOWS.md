# Troubleshooting — Windows (CRIBA + BLACKFORGE portable)

## El `.exe` no arranca
- Verifica que extrajiste TODO el ZIP, incluido la carpeta `_internal`.
- No ejecutes desde una ruta de red; usa disco local.
- Si Windows SmartScreen bloquea el archivo, permite la ejecución (el build
  no está firmado; es responsabilidad del usuario según su política).

## Caracteres corruptos al redirigir la salida
- Causa: la consola de Windows usa cp1252 y el `.exe` imprime JSON con
  `ensure_ascii=False`. No es un defecto del motor.
- Solución: usa `--database` + `explain` (SQLite guarda UTF-8 real), o bien
  ejecuta en una consola configurada en UTF-8 (`chcp 65001`).

## La base de datos no se crea
- Pasa `--database ruta/absoluta.sqlite3`. Sin `--database`, usa
  `artifacts/criba.sqlite3` (requiere permiso de escritura en `artifacts/`).
- Asegúrate de que la carpeta de destino existe y es escribible.

## El catálogo BLACKFORGE no carga
- El catálogo está empaquetado dentro del `.exe` (módulo `blackforge_catalog`
  + `imports/blackforge_v2`). No necesitas copiar `data/` aparte.
- Si ves un error de `FileNotFoundError` sobre `imports/`, el build se hizo
  sin el catálogo; reconstruye con `--add-data "data;data"` y el intérprete
  autorizado.

## Rendimiento
- El motor corre en CPU. El catálogo se carga una sola vez por proceso
  (índice O(1) inmutable). No se satura la RAM (perfil: 16 GB).
- No se usa GPU; no instales controladores CUDA.

## Reportar un problema
Incluye: salida del `.exe`, `--database` usada, comando exacto, y el
`activation_id` del paquete.
