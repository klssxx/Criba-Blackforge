SUPERVISOR AUTOMÁTICO HERMES · CRIBA / BLACKFORGE
=================================================

¿ES DIFÍCIL?
------------
No demasiado. El paquete ya contiene la lógica. El supervisor:

1. extrae el paquete de CRIBA/BLACKFORGE en E:\PROYECTS\CRIBA;
2. coloca el protocolo de autosupervisión;
3. arranca Hermes con una consulta corta;
4. Hermes lee los dos prompts y los datos desde disco;
5. cuando Hermes genera CONTEXT_REGENERATION_REQUIRED, el supervisor comprueba
   HANDOFF.md, session_handoff.json y RESUME_NEXT_SESSION.txt;
6. inicia un proceso nuevo de Hermes, sin --continue ni --resume;
7. se detiene cuando recibe PROJECT_COMPLETED o detecta un bucle.

REQUISITOS
----------
- Windows 11.
- Hermes ya instalado y configurado.
- El comando `hermes` debe funcionar en PowerShell.
- El proyecto debe existir en E:\PROYECTS\CRIBA.
- Nous Portal/HY3 debe estar configurado en Hermes.

USO FÁCIL
---------
1. Extrae este ZIP en una carpeta cualquiera.
2. Haz doble clic en LANZAR_SUPERVISOR.cmd.

USO DESDE POWERSHELL
--------------------
Abre PowerShell en la carpeta extraída y ejecuta:

pwsh -NoProfile -ExecutionPolicy Bypass `
  -File .\Supervisor-Hermes-CRIBA.ps1

PARÁMETROS ÚTILES
-----------------
Otro proyecto:

pwsh -NoProfile -ExecutionPolicy Bypass `
  -File .\Supervisor-Hermes-CRIBA.ps1 `
  -ProjectRoot "E:\OTRA_RUTA\CRIBA"

Usar la configuración de modelo ya guardada en Hermes:

pwsh -NoProfile -ExecutionPolicy Bypass `
  -File .\Supervisor-Hermes-CRIBA.ps1 `
  -Provider "" `
  -Model ""

Otro modelo:

pwsh -NoProfile -ExecutionPolicy Bypass `
  -File .\Supervisor-Hermes-CRIBA.ps1 `
  -Provider "nous" `
  -Model "hy3:free"

Reanudar tras haber instalado ya el paquete:

pwsh -NoProfile -ExecutionPolicy Bypass `
  -File .\Supervisor-Hermes-CRIBA.ps1 `
  -SkipPackageInstall

ARCHIVOS QUE HERMES RECIBE
--------------------------
No se pegan dentro del argumento -q, porque el hiper-megaprompt es demasiado
largo. El supervisor envía una consulta corta que ordena leer desde disco:

1. E:\PROYECTS\CRIBA\HIPER_MEGAPROMPT_CRIBA_BLACKFORGE_V2.txt
2. E:\PROYECTS\CRIBA\.criba\AUTOSUPERVISION_PROMPT.txt
3. HANDOFF.md y RESUME_NEXT_SESSION.txt cuando existan.
4. imports\blackforge_v2\ con catálogo, políticas, motor causal y auditoría.

LOGS
----
E:\PROYECTS\CRIBA\.criba\supervisor_logs

ESTADOS DE SALIDA
-----------------
0  = proyecto completado
20 = pidió regeneración sin handoff completo
21 = dos regeneraciones sin progreso
22 = demasiadas sesiones sin marcador
23 = máximo de generaciones alcanzado

SEGURIDAD
---------
El script no usa --yolo. Hermes conserva los checkpoints y aprobaciones
configuradas. BLACKFORGE sigue limitado a uso autorizado, defensivo, local o
en sandbox.