# EXECUTABLE_SMOKE_TEST — CRIBA + BLACKFORGE v0.1.0

Fecha: 2026-07-24 (UTC)
Build probado: dist/CRIBA-Blackforge-Portable-Windows-x64/ (dual GUI+CLI onedir)

## Método
Se probó el/los ejecutable(s) REAL(es) desde dist, no el código fuente.
El build dual expone:
- CRIBA-Blackforge.exe      → GUI windowed (PySide6/Qt)
- CRIBA-Blackforge-CLI.exe  → CLI console (UTF-8 forzado)

## Resultados por flujo
| # | Flujo | Ejecutable | Estado | Evidencia |
|---|-------|-----------|--------|-----------|
| 1 | GUI: primera apertura | GUI.exe | PASS | proceso vivo, ventana 1364x779 |
| 2 | GUI: pantalla principal + render fuentes | GUI.exe | PASS | vision_analyze: layout premium, texto legible |
| 3 | GUI: botones/nav visibles | GUI.exe | PASS | EJECUTAR CRIBA + panel derecho + nav |
| 4 | GUI: conectividad BD | GUI.exe | PASS | barra estado "Base de datos: ✔" |
| 5 | CLI: list-currents | CLI.exe | PASS | JSON de corrientes, rc=0 |
| 6 | CLI: activate (consulta con acentos) | CLI.exe | PASS | selected_current + value_score=0.5524, rc=0 |
| 7 | CLI: UTF-8 acentos correctos | CLI.exe | PASS | "Cómo/detección" sin mojibake |
| 8 | CLI: flag --database (persistencia) | CLI.exe | PASS | escribe sqlite en ruta indicada, rc=0 |
| 9 | Qt/DLL bundladas | ambos | PASS | _internal/PySide6/*.dll presentes |
| 10 | Catálogo BLACKFORGE (723) bundled | ambos | PASS | _internal/imports/blackforge_v2 en ZIP |
| 11 | GUI: interacción por CLIC (rellenar + Ejecutar en ventana) | GUI.exe | NOT_EXECUTED | denegado por usuario (computer_use) |

## Estado global
PARTIAL

Motivo: el CLI .exe está COMPLETAMENTE probado (list-currents, activate con
acentos, persistencia, rc=0). La GUI .exe arranca y renderiza con BD conectada,
pero el clic-through dentro de la ventana NO se ejecutó (denegado por usuario);
no se inventa su resultado. La lógica que ese botón dispara es idéntica a la del
CLI, que sí está verificado end-to-end sobre el ejecutable real.
