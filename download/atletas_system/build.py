# -*- coding: utf-8 -*-
"""
build.py
========
Script de compilación del Sistema AT para Windows.

Pasos que ejecuta:
    1. Limpia build/, dist/ e installer_output/.
    2. Verifica que PyInstaller esté disponible.
    3. Verifica que templates/ contenga las 4 plantillas oficiales.
    4. Compila el ejecutable con PyInstaller (sistema_at.spec).
    5. Verifica que dist/SistemaAT/SistemaAT.exe exista.
    6. Localiza Inno Setup 6 (ISCC.exe) y compila installer.iss.
    7. Reporta la ruta del instalador final:
       installer_output/SistemaAT_Setup_1.0.0.exe

Uso:
    python build.py               # exe + instalador
    python build.py --exe-only    # solo el ejecutable (sin instalador)
    python build.py --clean       # limpieza profunda (también __pycache__)
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
RUTAS_ISCC = [
    r"C:\Program Files\Inno Setup 6\ISCC.exe",
    r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
]
PLANTILLAS_ESPERADAS = [
    "PLANTILLA FORMATO AT-F1 CAR.xlsx",
    "PLANTILLA FORMATO AT-F3.xlsx",
    "PLANTILLA FORMATO ATF8.xlsx",
    "PLANTILLA FORMATO AT -F9.xlsx",
]


def _ejecutar(comando: list[str]) -> None:
    print(f"  $ {' '.join(str(c) for c in comando)}")
    resultado = subprocess.run(comando, cwd=str(RAIZ))  # noqa: S603
    if resultado.returncode != 0:
        raise SystemExit(f"  ✗ El comando falló con código {resultado.returncode}: {comando}")


def _limpiar(profundo: bool) -> None:
    print("• Limpiando carpetas de compilación…")
    for carpeta in ("build", "dist", "installer_output"):
        ruta = RAIZ / carpeta
        if ruta.exists():
            shutil.rmtree(ruta, ignore_errors=True)
            print(f"  − eliminada {carpeta}/")
    if profundo:
        for cache in RAIZ.rglob("__pycache__"):
            shutil.rmtree(cache, ignore_errors=True)
        print("  − eliminados __pycache__")


def _verificar_pyinstaller() -> None:
    print("• Verificando PyInstaller…")
    try:
        resultado = subprocess.run(  # noqa: S603
            [sys.executable, "-m", "PyInstaller", "--version"],
            capture_output=True, text=True, cwd=str(RAIZ),
        )
        if resultado.returncode == 0:
            print(f"  ✓ PyInstaller {resultado.stdout.strip()}")
            return
    except FileNotFoundError:
        pass
    raise SystemExit(
        "  ✗ PyInstaller no está instalado. Ejecute:\n"
        "      pip install -r requirements-dev.txt\n"
        "    y vuelva a intentar."
    )


def _verificar_plantillas() -> None:
    print("• Verificando plantillas oficiales en templates/…")
    faltantes = [n for n in PLANTILLAS_ESPERADAS if not (RAIZ / "templates" / n).exists()]
    if faltantes:
        print("  ⚠ FALTAN plantillas oficiales (la app abre, pero no generará Excel/PDF):")
        for nombre in faltantes:
            print(f"      - {nombre}")
        print("    Colóquelas en templates/ con esos nombres EXACTOS y recompile.")
    else:
        print("  ✓ Las 4 plantillas oficiales están presentes.")


def _buscar_iscc() -> str | None:
    localizado = shutil.which("ISCC")
    if localizado:
        return localizado
    for ruta in RUTAS_ISCC:
        if Path(ruta).exists():
            return ruta
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Compila el Sistema AT (exe y/o instalador).")
    parser.add_argument("--exe-only", action="store_true", help="solo compila el ejecutable")
    parser.add_argument("--clean", action="store_true", help="limpieza profunda (caches)")
    argumentos = parser.parse_args()

    print("=" * 62)
    print("COMPILACIÓN DEL SISTEMA AT · DINADAF")
    print("=" * 62)
    _limpiar(profundo=argumentos.clean)
    _verificar_pyinstaller()
    _verificar_plantillas()

    print("• Compilando ejecutable con PyInstaller…")
    _ejecutar([sys.executable, "-m", "PyInstaller", "--clean", "--noconfirm", "sistema_at.spec"])

    exe = RAIZ / "dist" / "SistemaAT" / "SistemaAT.exe"
    if not exe.exists():
        raise SystemExit("  ✗ No se encontró dist/SistemaAT/SistemaAT.exe tras la compilación.")
    print(f"  ✓ Ejecutable listo: {exe}")

    if argumentos.exe_only:
        print("\nListo (modo --exe-only). Distribuya la carpeta dist/SistemaAT/ completa.")
        return

    print("• Buscando Inno Setup 6 (ISCC.exe)…")
    iscc = _buscar_iscc()
    if not iscc:
        raise SystemExit(
            "  ✗ Inno Setup 6 no se encontró. Instálelo desde https://jrsoftware.org/isdl.php\n"
            "    (ruta esperada: C:\\Program Files\\Inno Setup 6\\ISCC.exe) y vuelva a ejecutar\n"
            "    'python build.py'. También puede compilarlo a mano: ISCC installer.iss"
        )
    print(f"  ✓ ISCC localizado: {iscc}")
    print("• Compilando instalador con Inno Setup…")
    _ejecutar([iscc, "installer.iss"])

    instalador = RAIZ / "installer_output" / "SistemaAT_Setup_1.0.0.exe"
    if not instalador.exists():
        raise SystemExit("  ✗ No se encontró el instalador en installer_output/.")
    print("=" * 62)
    print(f"INSTALADOR GENERADO:\n  {instalador}")
    print("=" * 62)


if __name__ == "__main__":
    main()
