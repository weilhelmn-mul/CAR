@echo off
rem Sistema AT v2.1 - lanzador alternativo SIN ejecutable .exe
rem Util cuando el antivirus o SmartScreen bloquean SistemaAT.exe
title Sistema AT v2.1 - IPD DINADAF
cd /d "%~dp0"
if not exist "py\pythonw.exe" (
    echo [ERROR] Falta la carpeta py - extraiga el ZIP completo.
    pause
    exit /b 1
)
start "" "py\pythonw.exe" "main.py"
exit /b 0
