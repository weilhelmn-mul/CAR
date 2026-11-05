@echo off
setlocal EnableExtensions
title RESPALDO DE DATOS - SISTEMA AT (IPD - DINADAF)

set "APPDIR=%~dp0"
if not exist "%APPDIR%Data" set "APPDIR=%LOCALAPPDATA%\SistemaAT"
if not exist "%APPDIR%\Data" (
  echo ================================================================
  echo   No se encontro la carpeta "Data" del sistema.
  echo.
  echo   Ejecute el sistema al menos una vez y vuelva a intentar,
  echo   o coloque este archivo en la carpeta donde esta instalado
  echo   el sistema (junto a SistemaAT.exe).
  echo ================================================================
  goto :fin
)

for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd_HH-mm"') do set "TS=%%i"
set "DESTINO=%APPDIR%\Data_Backups\Respaldo_%TS%"

echo ================================================================
echo    RESPALDO DE DATOS - SISTEMA AT
echo ================================================================
echo   Origen:  "%APPDIR%\Data"
echo   Destino: "%DESTINO%"
echo.
echo   Copiando, espere...
robocopy "%APPDIR%\Data" "%DESTINO%" /E /NFL /NDL /NJH /NJS /NP >nul
if errorlevel 8 (
  echo   ERROR: no se pudo crear el respaldo.
  goto :fin
)
echo.
echo   RESPALDO CREADO CON EXITO.
echo.
echo   Consejos:
echo   - Copie este respaldo a una USB o a la nube (OneDrive,
echo     Google Drive) una vez por semana.
echo   - Para restaurar: copie el contenido del respaldo de vuelta
echo     a la carpeta "Data" del sistema.
goto :fin

:fin
echo.
pause
endlocal
