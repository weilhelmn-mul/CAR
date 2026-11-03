# -*- coding: utf-8 -*-
"""Inspecciona las plantillas XLSX subidas por el usuario.

Imprime: hojas, dimensiones, celdas combinadas, contenido celda por celda
(coordenada + valor truncado), alturas de fila y anchos de columna.
Sirve para derivar los MAPA_* de src/services/excel.py con coordenadas reales.
"""
import openpyxl
from pathlib import Path

CARPETA = Path("/home/z/my-project/upload")

for archivo in sorted(CARPETA.glob("*.xlsx")):
    print("=" * 110)
    print("ARCHIVO:", archivo.name)
    wb = openpyxl.load_workbook(archivo)
    print("HOJAS:", wb.sheetnames, "| activa:", wb.active.title)
    for ws in wb.worksheets:
        print(f"\n--- HOJA '{ws.title}' dims={ws.dimensions} max_fila={ws.max_row} max_col={ws.max_column}")
        merges = sorted(str(m) for m in ws.merged_cells.ranges)
        print("COMBINADAS:", merges)
        for fila in ws.iter_rows():
            for c in fila:
                if c.value not in (None, ""):
                    v = str(c.value).replace("\n", "\\n")
                    if len(v) > 70:
                        v = v[:70] + f"…(len={len(str(c.value))})"
                    print(f"   {c.coordinate}: {v!r}")
        alturas = {r: d.height for r, d in ws.row_dimensions.items() if d.height}
        anchos = {k: round(d.width, 1) for k, d in ws.column_dimensions.items() if d.width}
        print("ALTURAS FILA:", alturas)
        print("ANCHOS COL:", anchos)
        try:
            print("IMAGENES:", len(ws._images))
        except Exception:
            pass
