# -*- mode: python ; coding: utf-8 -*-
"""
=============================================================
 Sistema AT · IPD - DINADAF
 sistema_at.spec — Receta de PyInstaller 6+ para la app portable.

 Uso:  pyinstaller sistema_at.spec
 Genera: dist/SistemaAT/  (carpeta onedir lista para comprimir)
=============================================================
"""
from PyInstaller.utils.hooks import collect_data_files

datas = [
    ("templates", "templates"),   # plantillas oficiales de los formatos
    ("assets", "assets"),         # icono de la aplicación
] + collect_data_files("customtkinter")  # temas/JSON internos de CustomTkinter

hiddenimports = [
    "PIL._tkinter_finder",        # necesario para que Pillow cargue imágenes en Tk
    "openpyxl.drawing.image",     # inserción de firmas PNG en Excel
]

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    exclude_binaries=True,
    name="SistemaAT",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,                    # UPX desactivado: evita falsos positivos de antivirus
    console=False,                # aplicación de ventanas, sin consola
    icon="assets/icon.ico",
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="SistemaAT",
)
