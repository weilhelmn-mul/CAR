@echo off
setlocal EnableExtensions
title DESINSTALADOR - SISTEMA AT (IPD - DINADAF)

set "DESTINO=%LOCALAPPDATA%\SistemaAT"
set "CARPETA="

if exist "%DESTINO%\SistemaAT.exe" set "CARPETA=%DESTINO%"
if not defined CARPETA if exist "%~dp0SistemaAT.exe" set "CARPETA=%~dp0"

echo ================================================================
echo    DESINSTALADOR - SISTEMA AT (IPD / DINADAF)
echo ================================================================
echo  Esta herramienta:
echo    1. Guarda una COPIA DE SEGURIDAD de sus datos (carpeta Data)
echo       en su ESCRITORIO: "SistemaAT-Datos-Respaldo".
echo    2. Elimina los iconos del Escritorio y del Menu Inicio.
echo    3. Elimina la carpeta del programa.
echo.
if not defined CARPETA (
  echo  No se encontro la carpeta instalada del sistema.
  echo  Se eliminaran solo los accesos directos si existieran.
) else (
  echo  Carpeta encontrada: "%CARPETA%"
)
echo.
choice /C SN /M "Desea continuar con la desinstalacion? (S = Si / N = No)"
if errorlevel 2 goto :cancelado

echo.
echo [1/3] Copia de seguridad de sus datos...
if defined CARPETA if exist "%CARPETA%\Data" (
  powershell -NoProfile -Command "$d=[Environment]::GetFolderPath('Desktop')+'\SistemaAT-Datos-Respaldo'; if(Test-Path -LiteralPath $d){Remove-Item -LiteralPath $d -Recurse -Force}; Copy-Item -LiteralPath '%CARPETA%\Data' -Destination $d -Recurse -Force"
  echo       Lista: carpeta "SistemaAT-Datos-Respaldo" en su Escritorio.
) else (
  echo       No habia carpeta Data que respaldar.
)

echo [2/3] Eliminando accesos directos...
powershell -NoProfile -Command "$dt=[Environment]::GetFolderPath('Desktop')+'\Sistema AT.lnk'; $sm=[Environment]::GetFolderPath('Programs')+'\Sistema AT.lnk'; Remove-Item -LiteralPath $dt -ErrorAction SilentlyContinue; Remove-Item -LiteralPath $sm -ErrorAction SilentlyContinue"
echo       Listo.

echo [3/3] Eliminando la carpeta del programa...
if defined CARPETA (
  rmdir /s /q "%CARPETA%"
  echo       Listo.
)
echo.
echo  DESINSTALACION COMPLETADA.
echo  Sus datos quedaron guardados en su Escritorio.
goto :fin

:cancelado
echo.
echo  Operacion cancelada. No se modifico nada.
goto :fin

:fin
echo.
pause
endlocal
