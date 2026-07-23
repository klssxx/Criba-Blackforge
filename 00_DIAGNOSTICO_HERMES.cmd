@echo off
setlocal
cd /d "%~dp0"
echo ===============================================================
echo  DIAGNOSTICO DE HERMES
echo ===============================================================
echo.
where hermes
echo.
hermes --version
echo.
echo --- HERMES GLOBAL HELP ---
hermes --help
echo.
echo --- HERMES CHAT HELP ---
hermes chat --help
echo.
pause