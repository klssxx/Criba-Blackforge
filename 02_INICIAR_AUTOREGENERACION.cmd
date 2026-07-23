@echo off
setlocal
cd /d "%~dp0"
echo.
echo ===============================================================
echo  HERMES - AUTORREGENERACION SIEMPRE ACTIVA V2
echo ===============================================================
echo.
where pwsh >nul 2>nul
if %ERRORLEVEL% EQU 0 (
  pwsh -NoProfile -ExecutionPolicy Bypass -File "%~dp0.autoregen\Supervisor-Hermes-AutoRegen.ps1"
) else (
  powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0.autoregen\Supervisor-Hermes-AutoRegen.ps1"
)
set EXITCODE=%ERRORLEVEL%
echo.
echo Supervisor terminado con codigo %EXITCODE%.
pause
exit /b %EXITCODE%