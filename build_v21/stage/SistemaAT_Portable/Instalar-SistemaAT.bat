@echo off
setlocal EnableExtensions
title INSTALADOR - SISTEMA AT (IPD - DINADAF)

echo ================================================================
echo    SISTEMA DE GESTION DE FORMATOS AT - IPD / DINADAF
echo    INSTALACION EN SU PC (Windows 10 / 11)
echo ================================================================
echo.
echo  Este instalador hace 3 cosas:
echo    1. Copia el sistema a su PC en la carpeta:
echo         %LOCALAPPDATA%\SistemaAT
echo    2. Crea el icono "Sistema AT" en su ESCRITORIO.
echo    3. Crea el icono "Sistema AT" en su MENU INICIO.
echo.
echo  No necesita internet, ni hosting, ni permisos de administrador.
echo  No borra datos: si ya usaba el sistema, se conservan.
echo.
pause

set "ORIGEN=%~dp0"
set "DESTINO=%LOCALAPPDATA%\SistemaAT"

if /i "%ORIGEN%"=="%DESTINO%\" (
  echo.
  echo  El sistema ya esta instalado en esta carpeta.
  echo  Solo se recrearan los accesos directos.
  goto :accesos
)

echo.
echo [1/3] Copiando archivos, espere (1-2 minutos la primera vez)...
if not exist "%DESTINO%" mkdir "%DESTINO%"
robocopy "%ORIGEN%." "%DESTINO%" /E /NFL /NDL /NJH /NJS /NP /XD Data Data_Backups >nul
if errorlevel 8 (
  echo.
  echo  ERROR al copiar archivos. Cierre el sistema si esta abierto
  echo  y vuelva a ejecutar este instalador.
  goto :fin
)
echo       Archivos copiados.

rem Si el instalador se ejecuta desde una carpeta donde ya se usaba
rem el sistema (por ejemplo una USB), migra tambien esa carpeta Data.
if exist "%DESTINO%\Data" goto :accesos
if not exist "%ORIGEN%Data" goto :accesos
echo       Copiando tambien sus datos existentes (carpeta Data)...
robocopy "%ORIGEN%Data" "%DESTINO%\Data" /E /NFL /NDL /NJH /NJS /NP >nul

:accesos
echo [2/3] Creando acceso directo en el Escritorio...
powershell -NoProfile -Command "$w=(New-Object -ComObject WScript.Shell);$s=$w.CreateShortcut([Environment]::GetFolderPath('Desktop')+'\Sistema AT.lnk');$s.TargetPath='%DESTINO%\SistemaAT.exe';$s.WorkingDirectory='%DESTINO%';$s.IconLocation='%DESTINO%\SistemaAT.exe,0';$s.Save()"
echo [3/3] Creando acceso directo en el Menu Inicio...
powershell -NoProfile -Command "$w=(New-Object -ComObject WScript.Shell);$s=$w.CreateShortcut([Environment]::GetFolderPath('Programs')+'\Sistema AT.lnk');$s.TargetPath='%DESTINO%\SistemaAT.exe';$s.WorkingDirectory='%DESTINO%';$s.IconLocation='%DESTINO%\SistemaAT.exe,0';$s.Save()"

echo.
echo ================================================================
echo    INSTALACION COMPLETADA
echo ================================================================
echo   El sistema quedo instalado en:
echo     %DESTINO%
echo.
echo   PARA ABRIRLO:
echo     - Icono "Sistema AT" del ESCRITORIO, o
echo     - Tecla Windows, escriba:  Sistema AT
echo.
echo   Sus datos se guardan en la subcarpeta "Data" de esa carpeta.
echo   Para respaldos semanales use: Respaldar-Datos.bat
echo.
echo   NOTA: si Windows SmartScreen avisa la primera vez, pulse
echo   "Mas informacion" y luego "Ejecutar de todas formas".
echo ================================================================
goto :fin

:fin
echo.
pause
endlocal
