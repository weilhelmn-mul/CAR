@echo off
title Sistema AT - Consola de diagnostico
cd /d "%~dp0"
echo ============================================================
echo  Sistema AT v2.1 - modo consola de diagnostico
echo  Si el sistema no abre, el error aparecera aqui abajo.
echo ============================================================
echo.
echo Motor Python incluido:
py\python.exe --version
echo.
echo Iniciando el sistema...
py\python.exe main.py
echo.
echo (Sistema cerrado. Si ve un error arriba, copielo para soporte.)
pause
