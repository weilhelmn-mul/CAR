@echo off
REM ============================================================
REM  Sistema AT - IPD DINADAF :: Compilador del EXE PORTABLE
REM  Doble clic -> genera dist\SistemaAT\SistemaAT.exe y
REM                dist\SistemaAT_Portable_v1.0.zip
REM  Requiere: Python 3.12 o 3.13. Solo se ejecuta UNA vez,
REM  en UN equipo con Windows. El resultado es el portable real:
REM  funciona en cualquier PC sin Python ni administrador.
REM ============================================================
setlocal EnableExtensions
cd /d "%~dp0"
title Sistema AT - Compilar portable

set "PYEXE="
if exist ".venv\Scripts\python.exe" set "PYEXE=.venv\Scripts\python.exe"
if not defined PYEXE py -3.12 -c "import sys" >nul 2>&1 && set "PYEXE=py -3.12"
if not defined PYEXE py -3.13 -c "import sys" >nul 2>&1 && set "PYEXE=py -3.13"
if not defined PYEXE (
    python -c "import sys; sys.exit(0 if sys.version_info[:2] in ((3,12),(3,13)) else 1)" >nul 2>&1 && set "PYEXE=python"
)
if not defined PYEXE (
    echo.
    echo  [ERROR] No se encontro Python 3.12 o 3.13.
    echo  Primero ejecute EJECUTAR_SISTEMA.bat o instale Python desde
    echo  https://www.python.org/downloads/ con "Add python.exe to PATH".
    echo.
    pause
    exit /b 1
)

echo  [1/3] Instalando PyInstaller (compilador) ...
%PYEXE% -m pip install --find-links wheels -r requirements-dev.txt -q
if errorlevel 1 (
    echo  [ERROR] Fallo la instalacion de PyInstaller. Verifique internet.
    pause
    exit /b 1
)

echo  [2/3] Compilando SistemaAT.exe (tarda 3-8 minutos) ...
%PYEXE% build.py
if errorlevel 1 (
    echo  [ERROR] La compilacion fallo. Revise los mensajes de arriba.
    pause
    exit /b 1
)

echo.
echo  ============================================================
echo   [3/3] LISTO. Su version portable esta en:
echo.
echo     dist\SistemaAT\SistemaAT.exe          (ejecutable + _internal)
echo     dist\SistemaAT_Portable_v1.0.zip      (para copiar a USB)
echo.
echo   Copie la carpeta dist\SistemaAT completa a la USB o a otro PC.
echo   Los datos se guardan en Data\ junto al exe (modo portable).
echo  ============================================================
echo.
pause
