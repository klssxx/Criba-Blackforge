@echo off
title CRIBA BLACKFORGE Workbench Launcher
cd /d "E:\PROYECTS\CRIBA"

echo ==============================================================================
echo   CRIBA BLACKFORGE Workbench Launcher
echo ==============================================================================
echo.
echo Iniciando interfaz BLACKFORGE...
echo.

python -m criba.cli blackforge-gui

pause
