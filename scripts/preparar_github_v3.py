#!/usr/bin/env python3
"""Prepara el paquete GitHub del Sistema AT v3.0:
1. Elimina __pycache__ de la copia GitHub.
2. Valida sintaxis de todos los .py.
3. Reconstruye el ZIP final sin artefactos.
4. Verifica el ZIP resultante.
"""
import py_compile
import shutil
import sys
import zipfile
from pathlib import Path

RAIZ = Path("/home/z/my-project/download/SistemaAT-v3.0-GitHub/SistemaAT")
ZIP_FINAL = Path("/home/z/my-project/download/SistemaAT_v3.0_GITHUB.zip")

# --- 1. Limpiar __pycache__ -------------------------------------------------
eliminados = 0
for pyc_dir in list(RAIZ.rglob("__pycache__")):
    if pyc_dir.is_dir():
        shutil.rmtree(pyc_dir)
        eliminados += 1
print(f"[1] __pycache__ eliminados: {eliminados}")

# --- 2. Validar sintaxis de todos los .py ----------------------------------
errores = []
pys = sorted(RAIZ.rglob("*.py"))
for py in pys:
    try:
        py_compile.compile(str(py), doraise=True)
    except py_compile.PyCompileError as e:
        errores.append(str(e))
print(f"[2] Archivos .py validados: {len(pys)} | errores: {len(errores)}")
for e in errores:
    print("    !", e)
if errores:
    sys.exit(1)

# --- 3. Reconstruir ZIP -----------------------------------------------------
EXTRA = {"__pycache__", ".venv", "venv", "build", "dist", "data", "Data",
         "Data_Backups", ".pytest_cache", ".mypy_cache", ".idea", ".vscode"}
EXTRA_FILES = {"*.pyc", "*.pyo", "*.db", "*.log", "config_ia.json"}

def incluir(ruta: Path) -> bool:
    for parte in ruta.relative_to(RAIZ).parts[:-1]:
        if parte in EXTRA:
            return False
    nombre = ruta.name
    if ruta.is_dir() and nombre in EXTRA:
        return False
    for pat in EXTRA_FILES:
        if nombre.endswith(pat.lstrip("*")) and pat.startswith("*"):
            return False
    return True

if ZIP_FINAL.exists():
    ZIP_FINAL.unlink()

entradas = []
for ruta in sorted(RAIZ.rglob("*")):
    if not incluir(ruta):
        continue
    arcname = "SistemaAT/" + str(ruta.relative_to(RAIZ)).replace("\\", "/")
    entradas.append((ruta, arcname))

with zipfile.ZipFile(ZIP_FINAL, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
    for ruta, arcname in entradas:
        zf.write(ruta, arcname)

print(f"[3] ZIP creado: {ZIP_FINAL.name} | entradas: {len(entradas)} | "
      f"{ZIP_FINAL.stat().st_size / 1_048_576:.1f} MB")

# --- 4. Verificación final --------------------------------------------------
with zipfile.ZipFile(ZIP_FINAL) as zf:
    nombres = zf.namelist()
    malos = zf.testzip()
    pyc = [n for n in nombres if "__pycache__" in n or n.endswith((".pyc", ".pyo"))]
    db = [n for n in nombres if n.endswith((".db", ".log")) or "config_ia" in n]
    claves = {"README.md", "LICENSE", ".gitignore", ".gitattributes",
              "CHANGELOG.md", "main.py", "requirements.txt",
              "requirements-dev.txt", "docs/COMO_SUBIR_A_GITHUB.md",
              "docs/Guia_Instalacion_y_Uso_Frecuente_SistemaAT.pdf"}
    faltan = [c for c in claves
              if f"SistemaAT/{c}" not in nombres]
    vistas = [n for n in nombres if n.startswith("SistemaAT/src/views/") and n.endswith(".py")]
    services = [n for n in nombres if n.startswith("SistemaAT/src/services/") and n.endswith(".py")]
    plantillas = [n for n in nombres if n.startswith("SistemaAT/templates/") and n.endswith(".xlsx")]
    wheels = [n for n in nombres if n.startswith("SistemaAT/wheels/") and n.endswith(".whl")]
    bat = [n for n in nombres if n.startswith("SistemaAT/") and n.endswith(".bat")]

    print(f"[4] testzip: {'OK' if malos is None else 'CORRUPTO: ' + malos}")
    print(f"    pyc residuales: {len(pyc)} | db/log/clave: {len(db)}")
    print(f"    archivos clave faltantes: {faltan if faltan else 'ninguno'}")
    print(f"    vistas: {len(vistas)} | servicios: {len(services)} | "
          f"plantillas xlsx: {len(plantillas)} | wheels: {len(wheels)} | bat: {len(bat)}")
    ok = (malos is None and not pyc and not db and not faltan
          and len(vistas) == 13 and len(services) == 5  # 12 vistas + __init__.py
          and len(plantillas) == 4 and len(bat) == 2)
    print("RESULTADO FINAL:", "APROBADO ✅" if ok else "REVISAR ❌")
    sys.exit(0 if ok else 1)
