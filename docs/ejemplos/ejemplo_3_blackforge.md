# Ejemplo 3 · BLACKFORGE — autorizaciones excesivas de un agente

Especialización de seguridad sobre el mismo motor. **Solo laboratorio autorizado**: la clasificación S0–S3 no concede autorización; S3 requiere la triada de aprobación completa.

## 1. Problema

Reducir autorizaciones excesivas de un agente autónomo sin pedir aprobación al usuario para cada operación.

- **Bloqueo:** el permiso se concede una vez por sesión y queda reutilizable para cualquier operación del agente (origen: hipótesis).
- **Restricciones:** entorno de laboratorio; sin producción; auditoría de cada autorización.
- **Supuestos cuestionables:** «la granularidad por sesión es suficiente».

## 2. Fuentes de seguridad (perfil BLACKFORGE)

```bash
uv run python -m criba inventar "reducir permisos excesivos de un agente autonomo" --dossier
```

La actualización de fuentes del perfil BLACKFORGE adquiere **CISA KEV** (JSON oficial) y **MITRE ATT&CK** (STIX oficial) con deduplicación por contenido y cantidades reales.offline: fuentes bloqueadas declaradas como bloqueadas — un error nunca pasa a «sin antecedentes».

## 3. Hipótesis ilustrativa del cruce (requiere modelo para producirla)

Capacidades de **un solo uso**: cada autorización es una credencial ligada a una operación, recursos concretos y plazo breve. Mecanismo: limita reutilización y amplificación de privilegios. Ruta de desbloqueo: `sustituir_mecanismo` (de permiso persistente a capacidad por operación). La perspectiva del auditor exige registro legible de cada concesión.

**Antecedentes:** autorización por transacción, capacidades temporales — pueden existir referentes muy cercanos; `SURVIVED_SEARCH` ≠ novedad.

## 4. Prueba discriminante en laboratorio

Comparar sesión-permisos vs capacidades de un solo uso midiendo: reutilizaciones rechazadas, tareas legítimas completadas, interrupciones al usuario y latencia. Umbrales fijados **antes** de ver resultados. Condición de fracaso: si las capacidades de un solo uso bloquean tareas legítimas sin reducir reutilizaciones, la propuesta se descarta.

## 5. Verificación del mecanismo (test DV10)

El selector de BLACKFORGE respeta `safety > authorization > diversity`: un registro S3_HIGH_CONTROL con score y diversidad máximos no entra sin la triada de aprobación; con ella, respeta el cap de 1. La diversidad nunca debilita los gates.

## Qué NO es

No es herramienta ofensiva ni ejecuta acciones sobre objetivos externos. El dossier prepara la prueba; su ejecución requiere permisos reales verificados.
