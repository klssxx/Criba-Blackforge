# Guía de usuario — CRIBA + BLACKFORGE (Español)

## ¿Qué es?
Un motor de innovación estructural determinista. Toma una consulta, aplica
operadores de ruptura sobre 5 ejes causales, genera ideas, las evalúa por
`value_score = evidence * novelty / cost`, y emite un paquete con decisión.
BLACKFORGE es una especialización que usa un catálogo inmutable de 723
registros con un gate de seguridad (S0–S3).

## Uso básico (GUI portable)
Doble clic en `CRIBA-Blackforge.exe` abre la interfaz de escritorio:
1. Escribe tu consulta en el cuadro inferior.
2. Pulsa **▶ EJECUTAR CRIBA** (o elige el modo en el desplegable *Balanced*).
3. Revisa a la derecha: *Resumen de activación*, *Métricas clave* y
   *Decisión recomendada*.
4. **Copiar para el modelo** lleva el prompt a tu LLM; **Ver paquete completo
   (JSON)** muestra el resultado íntegro; el historial se guarda solo.

La base de datos se guarda en `%LOCALAPPDATA%\CRIBA-Blackforge\criba.sqlite3`.

## Uso avanzado (CLI, opcional)
Si ejecutas desde el código fuente con la CLI instalada (`pip install -e .`):
```text
criba list-currents
criba activate --query "tu pregunta de innovación"
criba activate --file samples\query_example.txt
criba --database mi.sqlite3 explain --session <activation_id>
```

## Flujos
- **Nueva idea**: `activate` genera 12 ideas por defecto.
- **Generar**: implícito en `activate` (divergencia + cross-consistency).
- **Evaluar**: el paquete incluye `value_score`, `pipeline_action`, `recommended_status`.
- **Guardar**: `activate` persiste en SQLite (vía `--database`).
- **Historial**: `explain --session <id>`, `compare --session-a A --session-b B`.
- **Blackforge**: se ejecuta internamente como librería (213 tests lo verifican).

## Buenas prácticas
- Usa `--database` para no tocar la base por defecto (`artifacts/criba.sqlite3`).
- Para automatizar, captura `activation_id` del JSON de salida.

## Requisitos
Windows 10/11 x64, 16 GB RAM (corre en CPU). No requiere instalación.
