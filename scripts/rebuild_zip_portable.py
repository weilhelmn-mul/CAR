"""Reconstruye SistemaAT_v1.0_KIT_PORTABLE.zip desde la carpeta download/SistemaAT."""
import zipfile
from pathlib import Path

RAIZ = Path("/home/z/my-project/download")
CARPETA = RAIZ / "SistemaAT"
ZIP_FINAL = RAIZ / "SistemaAT_v1.0_KIT_PORTABLE.zip"

excluir = {"dist", "build", ".venv", "__pycache__"}
with zipfile.ZipFile(ZIP_FINAL, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as paquete:
    for archivo in sorted(CARPETA.rglob("*")):
        if not archivo.is_file():
            continue
        if any(parte in excluir for parte in archivo.relative_to(CARPETA).parts):
            continue
        paquete.write(archivo, Path("SistemaAT") / archivo.relative_to(CARPETA))

with zipfile.ZipFile(ZIP_FINAL) as z:
    nombres = z.namelist()
print(f"ZIP reconstruido: {ZIP_FINAL.name} · {ZIP_FINAL.stat().st_size / 1e6:.1f} MB · {len(nombres)} entradas")
print("Nuevos archivos incluidos:", [n for n in nombres if n.endswith((".bat", "COMO_EJECUTAR.txt", "pywin32_ctypes-0.2.3-py3-none-any.whl"))])
