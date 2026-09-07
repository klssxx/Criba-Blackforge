# Ejemplo 2 · Problema de software/proceso — cola de atención

Ejemplo de la guía ASTRA: reducir una cola sin contratar personal. Ilustra la **ficha de bloqueo**, las **rutas de desbloqueo** y el **circuito de aprendizaje**.

## 1. Ficha de bloqueo

| Campo | Contenido |
|---|---|
| Resultado buscado | Reducir el tiempo de espera de la cola. |
| Solución de referencia | Más puestos de atención. |
| Bloqueo | Cada atención genera una segunda visita por errores previos (origen: hipótesis). |
| Explicación | El volumen depende de retornos, no solo de capacidad. |
| Evidencia | Muestra de retornos pendiente de medir (falta_comprobar). |
| Restricciones | Misma plantilla; misma calidad. |
| Supuestos cuestionables | «La duración media de la atención es el factor dominante». |

## 2. Exploración guiada por el bloqueo

En la GUI: **Nueva idea → Inventar** con el problema activo y la ficha cargada; o CLI con `--dossier`. El intérprete recibe el bloqueo en su solicitud y declara una ruta: p. ej. `desacoplar_dependencia` (separar la validación de errores del momento de atención) o `eliminar_necesidad` (que el error no llegue a generar segunda visita). La ruta elegida y su justificación quedan en la ficha de cada candidato (`ruta_desbloqueo`).

Prueba discriminante (antes de automatizar nada): medir una muestra de llegadas, duraciones y **retornos**; si los retornos dominan, acelerar atenciones no reduce la cola — eso decide entre las dos explicaciones.

## 3. Sustitución por mecanismo duplicado

Si dos finalistas interpretan el mismo mecanismo (paráfrasis), el redundante se sustituye desde el pool (1 revisión por candidato, registrado en `seleccion_finalista.revision_post_interpretacion` con llamadas contadas). Lo desconocido no se descarta: mecanismos incomparables quedan UNKNOWN.

## 4. Cierre del circuito

```text
resultado observado (negativo: retornos dominados por errores de formulario)
        ↓ registrar_resultado(dossier_id, "negativo", condiciones)
        ↓ siguiente exploración del mismo problema recibe la lección
        ↓ nueva hipótesis dirigida al retorno, no a la velocidad
```

La prueba más importante: **un resultado registrado modifica una decisión posterior pertinente**, visible en el prompt y en el ledger.

## Qué NO afirma este ejemplo

Que CRIBA encuentre mejores soluciones que un buen prompt directo: eso lo mide el harness (`benchmarks/innovation/`, condiciones A/B/C) con evaluación ciega — pendiente de ejecución con modelo autorizado.
