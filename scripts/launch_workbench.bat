@echo off
title CRIBA BLACKFORGE Workbench Launcher
cd /d "%~dp0.."
set "LOCALAPPDATA=%~dp0..\..\..\RUNTIME_STATE"


echo ==============================================================================
echo   CRIBA BLACKFORGE Workbench Launcher
echo ==============================================================================
echo.
echo Iniciando interfaz BLACKFORGE...
echo.

uv run --locked --all-extras python -m criba.cli blackforge-gui

pause
