# HERMES + HY3 — ORQUESTADOR P2

Trabaja en el repositorio indicado por `PROJECT_ROOT`.

Carga y aplica la skill `modal-criba-orchestrator`.

Objetivo: auditar y, solo cuando `MODO_SOLICITADO=improve`, endurecer P2 Persona System utilizando Modal como
fuente de evidencia ejecutable.

Reglas:

1. No implementes P3–P10.
2. No amplíes P7 ni crees P8 global.
3. No declares éxito a partir de la lectura del código.
4. Ejecuta `.\scripts\modal-verify.ps1 -Action all`.
5. Clasifica cada resultado como producto, test, configuración o infraestructura.
6. En modo audit, no cambies archivos.
7. En modo improve:
   - corrige solo causas demostradas;
   - añade test de regresión;
   - ejecuta gate específico;
   - ejecuta regresión Modal.
8. Produce obligatoriamente:
   `artifacts/hy3/P2_REVIEW.json`
9. El JSON debe validar contra:
   `schemas/hy3_review.schema.json`
10. El `source_hash` debe coincidir con la versión revisada.
11. No uses retórica como evidencia.
12. No continúes a P3.
