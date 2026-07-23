HERMES AUTORREGENERACIÓN V3 — CORRECCIÓN DE SEÑALES
===================================================

CORRIGE
-------
1. Las señales se reconocen solo cuando comienzan una línea.
   Una frase como:
   "NO corresponde CONTEXT_REGENERATION_REQUIRED"
   ya no provoca una regeneración falsa.

2. Reconoce:
   - PROJECT_COMPLETED
   - CONTEXT_REGENERATION_REQUIRED
   - HUMAN_DECISION_REQUIRED
   - BASELINE_DECISION_REQUIRED

3. Una decisión humana detiene el supervisor limpiamente con código 10.

4. Para una decisión humana exige:
   - HANDOFF.md
   - .autoregen\session_handoff.json

   No exige RESUME_NEXT_SESSION.txt.

5. Puede continuar desde HANDOFF + session_handoff aunque no exista todavía
   RESUME_NEXT_SESSION.txt.

INSTALACIÓN
-----------
Extrae el ZIP dentro de E:\PROYECTS\CRIBA y acepta sobrescribir:

- 02_INICIAR_AUTOREGENERACION.cmd
- 03_REINICIAR_ESTADO.cmd
- .autoregen\AUTOREGEN_GLOBAL.txt
- .autoregen\Supervisor-Hermes-AutoRegen.ps1

No borres HANDOFF.md ni .autoregen\session_handoff.json.

DECISIÓN ACTUAL
---------------
El archivo 04_AUTORIZAR_ALTERNATIVA_C.txt contiene el bloque que debes añadir al
principio de 01_TAREA_ACTUAL.txt para ratificar la alternativa C.

Después ejecuta 02_INICIAR_AUTOREGENERACION.cmd.