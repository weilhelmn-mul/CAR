@echo off
REM ============================================================
REM  Sistema AT - IPD DINADAF :: Lanzador de doble clic
REM  Ejecuta el sistema desde el codigo fuente (sin compilar).
REM  Requiere: Python 3.12 o 3.13 (python.org, marcar
REM  "Add python.exe to PATH"). No requiere internet: usa wheels\
REM ============================================================
setlocal EnableExtensions
cd /d "%~dp0"
title Sistema AT - IPD DINADAF

REM ---- 1. Localizar Python 3.12 o 3.13 ----
set "PYEXE="
py -3.12 -c "import sys" >nul 2>&1 && set "PYEXE=py -3.12"
if not defined PYEXE py -3.13 -c "import sys" >nul 2>&1 && set "PYEXE=py -3.13"
if not defined PYEXE (
    python -c "import sys; sys.exit(0 if sys.version_info[:2] in ((3,12),(3,13)) else 1)" >nul 2>&1 && set "PYEXE=python"
)
if not defined PYEXE (
    echo.
    echo  [ERROR] No se encontro Python 3.12 o 3.13 en este equipo.
    echo.
    echo  1. Descargue Python de: https://www.python.org/downloads/
    echo  2. Al instalar, marque la casilla "Add python.exe to PATH".
    echo  3. NO use Python 3.14.
    echo  4. Vuelva a ejecutar este archivo.
    echo.
    pause
    exit /b 1
)
echo  Python detectado: %PYEXE%

REM ---- 2. Entorno virtual y dependencias (solo la primera vez) ----
if not exist ".venv\Scripts\python.exe" (
    echo  [1/3] Creando entorno virtual .venv ...
    %PYEXE% -m venv .venv || goto :fallo_instalar
    echo  [2/3] Instalando dependencias (primera vez, tarda ~1 minuto) ...
    ".venv\Scripts\python.exe" -m pip install --no-index --find-links wheels -r requirements.txt -q >nul 2>&1
    if errorlevel 1 ".venv\Scripts\python.exe" -m pip install --find-links wheels -r requirements.txt -q
    if errorlevel 1 goto :fallo_instalar
) else (
    echo  [1/3] Entorno virtual ya preparado.
)

REM ---- 3. Ejecutar el sistema ----
echo  [3/3] Iniciando Sistema AT v1.0 ...
".venv\Scripts\python.exe" main.py
if errorlevel 1 (
    echo.
    echo  [ERROR] El sistema se cerro con problemas.
    echo  Revise el log en data\sistema_at.log
    pause
)
endlocal
exit /b 0

:fallo_instalar
echo.
echo  [ERROR] Fallo la instalacion de dependencias.
echo  - Si no hay internet: verifique que la carpeta wheels\ exista junto
echo    a este archivo y que su Python sea 3.12 o 3.13 de 64 bits.
echo  - Con internet: ejecute manualmente
echo    .venv\Scripts\python.exe -m pip install -r requirements.txt
echo.
pause
exit /b 1
