"""
Ensambla el PORTABLE USB real del Sistema AT:
    SistemaAT.exe (lanzador nativo) + carpeta py (CPython 3.12 Windows con
    tkinter) + src + main.py + templates + assets + dependencias preinstaladas.
Salida: download/SistemaAT_Portable_USB_v1.0.zip
"""
import ast
import shutil
import sys
import zipfile
from pathlib import Path

RAIZ = Path("/home/z/my-project/download")
KIT = RAIZ / "SistemaAT"                      # fuente maestra (config.py ya parcheado)
PYWIN = Path("/tmp/pyextract/python")         # CPython 3.12.16 windows install_only
EXE = Path("/home/z/my-project/scripts/SistemaAT.exe")
DEST = Path("/tmp/SistemaAT_Portable")        # carpeta de ensamblaje
ZIP_FINAL = RAIZ / "SistemaAT_Portable_USB_v1.0.zip"

RUEDAS = [
    "customtkinter-5.2.2-py3-none-any.whl",
    "darkdetect-0.8.0-py3-none-any.whl",
    "pillow-10.4.0-cp312-cp312-win_amd64.whl",
    "openpyxl-3.1.5-py2.py3-none-any.whl",
    "et_xmlfile-2.0.0-py3-none-any.whl",
    "pywin32-312-cp312-cp312-win_amd64.whl",
]

LEEME = r"""Sistema AT v1.0 · IPD - DINADAF — PORTABLE PARA USB (LISTO PARA USAR)
==========================================================================

CÓMO USAR
  1. Copie esta carpeta completa a una memoria USB (o a cualquier
     carpeta del equipo) y haga DOBLE CLIC en SistemaAT.exe.
  2. No requiere instalación, ni Python, ni permisos de administrador.
  3. Windows SmartScreen puede avisar la primera vez: pulse
     «Más información» → «Ejecutar de todas formas».

IMPORTANTE
  · Mantenga SIEMPRE juntas estas carpetas/archivos:
      SistemaAT.exe · py · src · templates · assets · main.py
  · «py» contiene un Python 3.12 completo incluido por el sistema:
      NO lo abra, NO lo renombre y NO borre nada de su interior.
  · Para diagnóstico técnico existe CONSOLA_DEBUG.bat (muestra errores
    en pantalla si el sistema no llegara a abrir).

SUS DATOS (MODO PORTABLE)
  · Todo se guarda en la carpeta Data\ junto al SistemaAT.exe:
      Data\sistema_at.db      → base de datos
      Data\firmas\            → firmas registradas
      Data\generados\         → Excel/PDF generados
      Data\sistema_at.log     → registro de eventos
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
echo  Sistema AT v1.0 - modo consola de diagnostico
echo  Si el sistema no abre, el error aparecera aqui abajo.
echo ============================================================
echo.
py\\python.exe main.py
echo.
echo (Sistema cerrado. Si ve un error arriba, reportelo con captura.)
pause
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
consola = DEST / "CONSOLA_DEBUG.bat"
consola.write_text(CONSOLA_DEBUG.replace("\n", "\r\n"), encoding="ascii")

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
    "CONSOLA_DEBUG.bat",
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
    "py/Lib/site-packages/PIL/_imaging.cp312-win_amd64.pyd",
    "py/Lib/site-packages/openpyxl/__init__.py",
    "py/Lib/site-packages/win32/win32api.pyd",
    "py/Lib/site-packages/pywin32_system32/pywintypes312.dll",
]
for relativo in requeridos:
    if not (DEST / relativo).exists():
        errores.append("FALTA: " + relativo)

# sintaxis Python (ast, sin crear __pycache__)
for py_arch in DEST.rglob("*.py"):
    relativo_py = py_arch.relative_to(DEST)
    if relativo_py.parts[0] == "py":
        continue
    try:
        ast.parse(py_arch.read_text(encoding="utf-8"))
    except SyntaxError as exc:
        errores.append(f"SINTAXIS {relativo_py}: {exc}")

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
