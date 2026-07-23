HERMES AUTORREGENERACIÓN SIEMPRE ACTIVA V2 — CORREGIDO
======================================================

QUÉ FALLÓ EN V1
---------------
La versión anterior colocaba `-Q` y `--checkpoints` antes de `chat`.

Tu instalación mostró:

hermes: error: unrecognized arguments: -Q --checkpoints

Hermes nunca llegó a arrancar. No se ejecutó el prompt y no se modificó CRIBA.

QUÉ CAMBIA EN V2
----------------
- Lee `hermes --help`.
- Lee `hermes chat --help`.
- Detecta qué opciones soporta TU instalación.
- Coloca opciones globales antes de `chat`.
- Coloca opciones de chat después de `chat`.
- No usa `-Q`.
- Solo usa `--checkpoints` si aparece en `hermes chat --help`.
- Usa `-q` o `--query` según lo que anuncie tu versión.
- Muestra el comando detectado antes de ejecutar.

INSTALACIÓN
-----------
1. Detén Hermes y la versión anterior del supervisor.
2. Extrae este ZIP dentro de la raíz del proyecto:
   E:\PROYECTS\CRIBA
3. Acepta sobrescribir:
   - 02_INICIAR_AUTOREGENERACION.cmd
   - 03_REINICIAR_ESTADO.cmd
   - .autoregen\AUTOREGEN_GLOBAL.txt
   - .autoregen\Supervisor-Hermes-AutoRegen.ps1
4. No sobrescribas 01_TAREA_ACTUAL.txt si ya contiene tu prompt. Windows puede
   preguntarlo; conserva el tuyo.
5. Ejecuta primero 00_DIAGNOSTICO_HERMES.cmd.
6. Después ejecuta 02_INICIAR_AUTOREGENERACION.cmd.

USO
---
Pega una sola tarea en 01_TAREA_ACTUAL.txt.
La autosupervisión se añade automáticamente en todas las sesiones.

No abras Hermes manualmente para esa tarea.
No uses --continue ni --resume.

NOTA
----
Si tu versión no soporta checkpoints por sesión, el supervisor continuará sin
esa opción. La autorregeneración sigue funcionando mediante HANDOFF y sesiones
nuevas.