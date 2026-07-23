@echo off
setlocal
cd /d "%~dp0"
echo Borrara solo el estado de autorregeneracion, no el codigo.
choice /C SN /M "Continuar"
if errorlevel 2 exit /b 0
del /q ".autoregen\regeneration_request.json" 2>nul
del /q ".autoregen\project_completed.json" 2>nul
del /q ".autoregen\session_handoff.json" 2>nul
del /q ".autoregen\supervisor_state.json" 2>nul
del /q "RESUME_NEXT_SESSION.txt" 2>nul
echo Estado reiniciado. HANDOFF.md se conserva.
pause