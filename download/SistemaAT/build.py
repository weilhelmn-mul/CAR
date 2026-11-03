"""
=============================================================
 Sistema AT · Instituto Peruano del Deporte (IPD - DINADAF)
 build.py — Compila la aplicación y arma la distribución PORTABLE.

 Comandos (ejecutar en Windows con Python 3.12/3.13):
     python build.py            → portable onedir + ZIP  (recomendado)
     python build.py onefile    → un único SistemaAT.exe portable
     python build.py installer  → onedir + recordatorio de Inno Setup
     python build.py clean      → limpia build/, dist/ y __pycache__

 Salida principal: dist/SistemaAT_Portable_v1.0.zip
   ├─ SistemaAT.exe (carpeta _internal incluida en onedir)
   ├─ PORTABLE      (marcador: los datos viven en .\\Data junto al exe)
   └─ LEEME_PORTABLE.txt
=============================================================
"""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
DIST = RAIZ / "dist"
BUILD = RAIZ / "build"
LEEME_PORTABLE = """Sistema AT v{version} · IPD - DINADAF — VERSIÓN PORTABLE
=========================================================

CÓMO USAR
  1. Descomprima esta carpeta donde desee (incluida una memoria USB).
  2. Ejecute SistemaAT.exe (en modo onefile es un único archivo .exe).
  3. Windows SmartScreen puede mostrar un aviso la primera vez:
     pulse «Más información» → «Ejecutar de todas formas».

MODO PORTABLE (SIN INSTALACIÓN)
  · Junto al ejecutable hay un archivo marcador llamado PORTABLE.
  · Mientras exista, TODOS los datos (base SQLite, firmas, Excel
    generados, registro) se guardan en la carpeta .\\Data junto al
    exe → copie esa carpeta para respaldar o mover el sistema.
  · Si borra el marcador PORTABLE, los datos irán a
    %LOCALAPPDATA%\\SistemaAT (modo instalado).

PDF (OPCIONAL)
  · Para exportar PDF instale LibreOffice (https://es.libreoffice.org).
  · Alternativa en Windows con Microsoft Excel instalado: se usa
    automáticamente vía COM. Sin ambos, igual puede generar los Excel.

PLANTILLAS
  · Los formatos AT-F3/AT-F1/AT-F8/AT-F9 usan las plantillas oficiales
    incluidas en templates\\. No renombre esos archivos.

Soporte: DINADAF · Instituto Peruano del Deporte — 2026
"""


def _version() -> str:
    """Lee APP_VERSION desde src/config.py sin importar el paquete."""
    texto = (RAIZ / "src" / "config.py").read_text(encoding="utf-8")
    coincidencia = re.search(r'APP_VERSION:\s*str\s*=\s*"([^"]+)"', texto)
    return coincidencia.group(1) if coincidencia else "1.0"


def _requisitos_previos() -> None:
    if sys.platform != "win32":
        sys.exit("La compilación de Windows debe ejecutarse en Windows (PyInstaller no cruza plataformas).")
    if sys.version_info[:2] not in ((3, 12), (3, 13)):
        sys.exit("Use Python 3.12 o 3.13 (NO 3.14: PyInstaller aún no lo soporta de forma estable).")
    faltantes = [nombre for nombre in (
        "PLANTILLA FORMATO AT-F3.xlsx", "PLANTILLA FORMATO AT-F1 CAR.xlsx",
        "PLANTILLA FORMATO ATF8.xlsx", "PLANTILLA FORMATO AT -F9.xlsx")
        if not (RAIZ / "templates" / nombre).exists()]
    if faltantes:
        sys.exit("Faltan plantillas oficiales en templates/: " + ", ".join(faltantes))
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        sys.exit("PyInstaller no está instalado: pip install -r requirements-dev.txt")


def _pyinstaller(argumentos: list[str]) -> None:
    comando = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", *argumentos]
    print("»", " ".join(comando))
    subprocess.run(comando, check=True, cwd=RAIZ)


def _crear_zip(carpeta_o_exe: Path, nombre_zip: str, destino_interno: str) -> Path:
    """Empaqueta la distribución portable junto al marcador PORTABLE y el LEEME."""
    version = _version()
    ruta_zip = DIST / f"SistemaAT_Portable_v{version}.zip"
    ruta_zip.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(ruta_zip, "w", zipfile.ZIP_DEFLATED) as paquete:
        if carpeta_o_exe.is_dir():
            for archivo in carpeta_o_exe.rglob("*"):
                if archivo.is_file():
                    paquete.write(archivo, Path(destino_interno) / archivo.relative_to(carpeta_o_exe))
        else:
            paquete.write(carpeta_o_exe, Path(destino_interno) / carpeta_o_exe.name)
        paquete.writestr(Path(destino_interno) / "PORTABLE", "")
        paquete.writestr(Path(destino_interno) / "LEEME_PORTABLE.txt",
                         LEEME_PORTABLE.format(version=version))
    return ruta_zip


def _portable_onefile() -> None:
    _pyinstaller([
        "--onefile", "--noconsole", "--name", "SistemaAT",
        "--icon", str(RAIZ / "assets" / "icon.ico"),
        "--add-data", f"{RAIZ / 'templates'};templates",
        "--add-data", f"{RAIZ / 'assets'};assets",
        "--collect-data", "customtkinter",
        "--hidden-import", "PIL._tkinter_finder",
        "--hidden-import", "openpyxl.drawing.image",
        str(RAIZ / "main.py"),
    ])
    exe = DIST / "SistemaAT.exe"
    if not exe.exists():
        sys.exit("PyInstaller no generó el ejecutable; revise los mensajes anteriores.")
    ruta_zip = _crear_zip(exe, "portable_onefile", "SistemaAT_Portable")
    print(f"[OK] Portable ONEFILE: {ruta_zip}")


def _portable_onedir() -> Path:
    _pyinstaller([str(RAIZ / "sistema_at.spec")])
    carpeta = DIST / "SistemaAT"
    if not (carpeta / "SistemaAT.exe").exists():
        sys.exit("PyInstaller no generó dist/SistemaAT/SistemaAT.exe; revise los mensajes.")
    ruta_zip = _crear_zip(carpeta, "portable_onedir", "SistemaAT_Portable")
    print(f"[OK] Portable ONEDIR: {ruta_zip}")
    return carpeta


def principal() -> None:
    modo = sys.argv[1] if len(sys.argv) > 1 else "portable"
    if modo == "clean":
        for carpeta in (BUILD, DIST):
            shutil.rmtree(carpeta, ignore_errors=True)
        for pycache in RAIZ.rglob("__pycache__"):
            shutil.rmtree(pycache, ignore_errors=True)
        print("[OK] Limpieza completada.")
        return
    _requisitos_previos()
    if modo == "portable":
        _portable_onedir()
    elif modo == "onefile":
        _portable_onefile()
    elif modo == "installer":
        carpeta = _portable_onedir()
        print(f"[SIGUIENTE PASO] Compile installer.iss con Inno Setup 6 apuntando a: {carpeta}")
    else:
        sys.exit("Modo desconocido. Use: portable (defecto) | onefile | installer | clean")


if __name__ == "__main__":
    principal()
