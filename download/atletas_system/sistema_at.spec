# -*- mode: python ; coding: utf-8 -*-
"""
sistema_at.spec
===============
Spec de PyInstaller 6 para el Sistema AT (modo onedir, aplicación de ventana
sin consola). Empaqueta:
    * main.py + paquete src
    * templates/  (plantillas oficiales IPD)
    * assets/     (icono)
    * datos de customtkinter (temas/idiomas) vía collect_data_files
    * hiddenimports necesarios para PIL+Tkinter y openpyxl con imágenes

Generar:  python -m PyInstaller --clean --noconfirm sistema_at.spec
Salida :  dist/SistemaAT/SistemaAT.exe
"""
import os

from PyInstaller.utils.hooks import collect_data_files

datas = [
    ("templates", "templates"),
    ("assets", "assets"),
] + collect_data_files("customtkinter")

hiddenimports = [
    "PIL._tkinter_finder",      # necesario para que Pillow cargue imágenes en Tk
    "openpyxl",
    "openpyxl.drawing.image",   # inserción de firmas PNG en las plantillas
]

a = Analysis(
    ["main.py"],
    pathex=["."],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

# Icono: se usa si assets/icon.ico existe (incluido en el proyecto)
_icono = "assets/icon.ico" if os.path.exists("assets/icon.ico") else None

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="SistemaAT",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,          # aplicación de escritorio sin consola
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=_icono,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="SistemaAT",
)
