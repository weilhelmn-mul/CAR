"""
Ensambla el PORTABLE USB real del Sistema AT v1.1:
    SistemaAT.exe (lanzador nativo v2) + carpeta py (CPython 3.12 Windows con
    tkinter) + src + main.py + templates + assets + dependencias preinstaladas.
Salida: download/SistemaAT_Portable_v1.1.zip
"""
import ast
import shutil
import sys
import zipfile
from pathlib import Path

RAIZ = Path("/home/z/my-project/download")
KIT = RAIZ / "SistemaAT"                      # fuente maestra (v1.1 ya aplicada)
PYWIN = Path("/tmp/pyextract/python")         # CPython 3.12.16 windows install_only
EXE = Path("/home/z/my-project/scripts/SistemaAT.exe")
DEST = Path("/tmp/SistemaAT_Portable")        # carpeta de ensamblaje
ZIP_FINAL = RAIZ / "SistemaAT_Portable_v1.1.zip"

RUEDAS = [
    "customtkinter-5.2.2-py3-none-any.whl",
    "darkdetect-0.8.0-py3-none-any.whl",
    "pillow-10.4.0-cp312-cp312-win_amd64.whl",
    "openpyxl-3.1.5-py2.py3-none-any.whl",
    "et_xmlfile-2.0.0-py3-none-any.whl",
    "pywin32-312-cp312-cp312-win_amd64.whl",
]

LEEME = r"""Sistema AT v1.1 · IPD - DINADAF — PORTABLE PARA USB (LISTO PARA USAR)
==========================================================================

CÓMO USAR
  1. EXTRAIGA COMPLETO el contenido de este ZIP a una memoria USB o a
     cualquier carpeta del equipo (clic derecho → "Extraer todo...").
  2. Entre a la carpeta SistemaAT_Portable y haga DOBLE CLIC en
     SistemaAT.exe. No requiere instalación, ni Python, ni permisos
     de administrador.
  3. Si Windows SmartScreen avisa la primera vez: pulse
     «Más información» → «Ejecutar de todas formas».

SI NO ABRE — REVISE EN ESTE ORDEN
  1. ¿Lo ejecutó DENTRO del ZIP sin extraer? Extraiga todo primero.
  2. Use INICIAR_SISTEMA.bat (doble clic): abre el sistema sin pasar
     por el ejecutable (útil si el antivirus bloquea SistemaAT.exe).
  3. Use CONSOLA_DEBUG.bat (doble clic): muestra el error exacto en
     pantalla. Copie ese mensaje si solicita soporte.
  4. Antivirus: agregue una EXCLUSIÓN para esta carpeta. Algunos
     antivirus eliminan silenciosamente el ejecutable.
  5. Requisito del equipo: Windows 10 u 11 de 64 BITS. En Windows 7/8
     o en sistemas de 32 bits el sistema no puede ejecutarse.
  6. No ejecute desde C:\Program Files (sin permisos): use el
     Escritorio, Documentos, C:\SistemaAT o una memoria USB.

IMPORTANTE
  · Mantenga SIEMPRE juntas estas carpetas/archivos:
      SistemaAT.exe · py · src · templates · assets · main.py
  · «py» contiene un Python 3.12 completo incluido por el sistema:
      NO lo abra, NO lo renombre y NO borre nada de su interior.

SUS DATOS (MODO PORTABLE)
  · Todo se guarda en la carpeta "Data" junto al SistemaAT.exe:
      Data\sistema_at.db      → base de datos
      Data\firmas\            → firmas registradas
      Data\generados\         → Excel/PDF generados
      Data\sistema_at.log     → registro de eventos (diagnóstico)
  · RESPALDO: copie la carpeta Data\ completa.
  · MUDANZA: copie TODA la carpeta del sistema a la nueva ubicación.
  · El archivo marcador PORTABLE activa este comportamiento; si se
    elimina, los datos irán a %LOCALAPPDATA%\SistemaAT.

PDF (OPCIONAL)
  · Para exportar PDF instale LibreOffice (https://es.libreoffice.org).
  · Con Microsoft Excel instalado la conversión se hace automáticamente
    vía COM. Sin ambos, igual puede generar todos los Excel.

PLANTILLAS
  · Los formatos AT-F3 / AT-F1 / AT-F8 / AT-F9 usan las plantillas
    oficiales incluidas en templates\. No renombre esos archivos.

Soporte: DINADAF · Instituto Peruano del Deporte — 2026
"""

CONSOLA_DEBUG = """@echo off
title Sistema AT - Consola de diagnostico
cd /d "%~dp0"
echo ============================================================
echo  Sistema AT v1.1 - modo consola de diagnostico
echo  Si el sistema no abre, el error aparecera aqui abajo.
echo ============================================================
echo.
echo Motor Python incluido:
py\\python.exe --version
echo.
echo Iniciando el sistema...
py\\python.exe main.py
echo.
echo (Sistema cerrado. Si ve un error arriba, copielo para soporte.)
pause
"""

INICIAR = """@echo off
rem Sistema AT v1.1 - lanzador alternativo SIN ejecutable .exe
rem Util cuando el antivirus o SmartScreen bloquean SistemaAT.exe
title Sistema AT v1.1 - IPD DINADAF
cd /d "%~dp0"
if not exist "py\\pythonw.exe" (
    echo [ERROR] Falta la carpeta py - extraiga el ZIP completo.
    pause
    exit /b 1
)
start "" "py\\pythonw.exe" "main.py"
exit /b 0
"""

# ---------------------------------------------------------------- limpiar
if DEST.exists():
    shutil.rmtree(DEST)
DEST.mkdir(parents=True)

# ---------------------------------------------------------------- app
shutil.copy2(KIT / "main.py", DEST / "main.py")
shutil.copytree(KIT / "src", DEST / "src",
                ignore=shutil.ignore_patterns("__pycache__"))
shutil.copytree(KIT / "templates", DEST / "templates")
shutil.copytree(KIT / "assets", DEST / "assets")
shutil.copy2(EXE, DEST / "SistemaAT.exe")
(DEST / "PORTABLE").write_text("", encoding="utf-8")
(DEST / "LEEME_PORTABLE.txt").write_text(LEEME, encoding="utf-8")
for nombre, contenido in (("CONSOLA_DEBUG.bat", CONSOLA_DEBUG),
                          ("INICIAR_SISTEMA.bat", INICIAR)):
    (DEST / nombre).write_text(contenido.replace("\n", "\r\n"), encoding="ascii")

# ---------------------------------------------------------------- python
py_dest = DEST / "py"
py_dest.mkdir()
excluir_pdb = shutil.ignore_patterns("*.pdb")
for item in PYWIN.iterdir():
    if item.name in ("include", "libs", "Scripts"):
        continue                                    # solo desarrollo
    if item.is_dir():
        shutil.copytree(item, py_dest / item.name,
                        ignore=excluir_pdb)
    else:
        if item.suffix == ".pdb":
            continue
        shutil.copy2(item, py_dest / item.name)
idle = py_dest / "Lib" / "idlelib"
if idle.exists():
    shutil.rmtree(idle)                             # 1.3 MB innecesarios

# ------------------------------------------------- dependencias (wheels)
site_packages = py_dest / "Lib" / "site-packages"
site_packages.mkdir(exist_ok=True)
for rueda in RUEDAS:
    with zipfile.ZipFile(KIT / "wheels" / rueda) as z:
        z.extractall(site_packages)
    print(f"  wheel instalado: {rueda}")

# ---------------------------------------------------------------- verif.
errores: list[str] = []
requeridos = [
    "SistemaAT.exe", "main.py", "PORTABLE", "LEEME_PORTABLE.txt",
    "CONSOLA_DEBUG.bat", "INICIAR_SISTEMA.bat",
    "src/config.py", "src/main_window.py", "src/database.py",
    "templates/PLANTILLA FORMATO AT-F3.xlsx",
    "templates/PLANTILLA FORMATO AT-F1 CAR.xlsx",
    "templates/PLANTILLA FORMATO ATF8.xlsx",
    "templates/PLANTILLA FORMATO AT -F9.xlsx",
    "assets/icon.ico",
    "py/python.exe", "py/pythonw.exe", "py/python312.dll",
    "py/vcruntime140.dll", "py/DLLs/_tkinter.pyd", "py/DLLs/tcl86t.dll",
    "py/tcl/tcl8.6/init.tcl", "py/tcl/tk8.6/tk.tcl",
    "py/Lib/tkinter/__init__.py",
    "py/Lib/site-packages/customtkinter/__init__.py",
    "py/Lib/site-packages/customtkinter/assets/themes/blue.json",
    "py/Lib/site-packages/PIL/_imaging.cp312-win_amd64.pyd",
    "py/Lib/site-packages/openpyxl/__init__.py",
    "py/Lib/site-packages/win32/win32api.pyd",
    "py/Lib/site-packages/win32/lib/pywin32_bootstrap.py",
    "py/Lib/site-packages/pywin32_system32/pywintypes312.dll",
]
for relativo in requeridos:
    if not (DEST / relativo).exists():
        errores.append("FALTA: " + relativo)

# v1.1 presente en config y arranque protegido
cfg = (DEST / "src" / "config.py").read_text(encoding="utf-8")
if 'APP_VERSION: str = "1.1"' not in cfg:
    errores.append("FALTA: APP_VERSION 1.1 en config.py")
mn = (DEST / "main.py").read_text(encoding="utf-8")
if "report_callback_exception" not in mn or "El sistema no pudo iniciarse" not in mn:
    errores.append("FALTA: arranque protegido v1.1 en main.py")

# sintaxis Python (ast, sin crear __pycache__)
for py_arch in DEST.rglob("*.py"):
    relativo = py_arch.relative_to(DEST)
    if relativo.parts[0] == "py":
        continue
    try:
        ast.parse(py_arch.read_text(encoding="utf-8"))
    except SyntaxError as exc:
        errores.append(f"SINTAXIS {relativo}: {exc}")

if errores:
    mensaje = "\n".join(errores)
    print(mensaje, flush=True)
    print(mensaje, file=sys.stderr, flush=True)
    raise SystemExit("Ensamblaje con errores — revise arriba.")

# ---------------------------------------------------------------- zip
if ZIP_FINAL.exists():
    ZIP_FINAL.unlink()
total = sum(1 for _ in DEST.rglob("*") if _.is_file())
with zipfile.ZipFile(ZIP_FINAL, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as paquete:
    for archivo in sorted(DEST.rglob("*")):
        if archivo.is_file():
            paquete.write(archivo, Path("SistemaAT_Portable") / archivo.relative_to(DEST))
with zipfile.ZipFile(ZIP_FINAL) as z:
    malo = z.testzip()
    n_entradas = len(z.namelist())
print(f"[OK] Carpeta portable: {total} archivos, {sum(f.stat().st_size for f in DEST.rglob('*') if f.is_file())/1e6:.0f} MB descomprimido")
print(f"[OK] ZIP: {ZIP_FINAL.name} · {ZIP_FINAL.stat().st_size/1e6:.1f} MB · {n_entradas} entradas · test={malo}")
