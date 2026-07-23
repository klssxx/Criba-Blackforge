@echo off
setlocal
cd /d "%~dp0"
echo.
echo ================================================================
echo  SUPERVISOR HERMES - CRIBA / BLACKFORGE
echo ================================================================
echo.
where pwsh >nul 2>nul
if %ERRORLEVEL% EQU 0 (
  pwsh -NoProfile -ExecutionPolicy Bypass -File "%~dp0Supervisor-Hermes-CRIBA.ps1"
) else (
  powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Supervisor-Hermes-CRIBA.ps1"
)
set EXITCODE=%ERRORLEVEL%
echo.
echo Supervisor terminado con codigo %EXITCODE%.
pause
exit /b %EXITCODE%