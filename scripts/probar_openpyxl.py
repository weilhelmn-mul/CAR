# -*- coding: utf-8 -*-
"""Prueba detalles finos de openpyxl necesarios para services/excel.py:
- área de impresión y configuración de página de cada plantilla
- ancla de las imágenes (logo) existentes
- formatos numéricos de celdas clave
- comportamiento de insert_rows con celdas combinadas y alturas de fila
"""
import openpyxl
from pathlib import Path

UP = Path("/home/z/my-project/upload")

for nombre in ["PLANTILLA FORMATO AT -F9.xlsx", "PLANTILLA FORMATO AT-F1 CAR.xlsx",
               "PLANTILLA FORMATO AT-F3.xlsx", "PLANTILLA FORMATO ATF8.xlsx"]:
    wb = openpyxl.load_workbook(UP / nombre)
    ws = wb.active
    print("=" * 90)
    print(nombre, "| hoja:", ws.title)
    print("  print_area:", ws.print_area)
    ps = ws.page_setup
    print("  page_setup: orient=", ps.orientation, "fitToWidth=", ps.fitToWidth, "fitToHeight=", ps.fitToHeight, "scale=", ps.scale)
    print("  sheet_properties.pageSetUpPr:", ws.sheet_properties.pageSetUpPr)
    for img in ws._images:
        try:
            frm = img.anchor._from
            print(f"  imagen: col={frm.col} fila={frm.row} (0-index) ancho={img.width} alto={img.height}")
        except Exception as e:
            print("  imagen (anchor raro):", e)
    if "AT-F1" in nombre:
        print("  H24 fmt:", ws["H24"].number_format, "| I24 fmt:", ws["I24"].number_format,
              "| C13 fmt:", ws["C13"].number_format, "| H12(AT-F9-style) n/a")
        print("  A67 estilo borde:", ws["A67"].border.left.style, ws["A67"].border.top.style)
        print("  B24 (AT-F3) fmt:", end=" ")
    if "AT-F3" in nombre:
        print("B24 fmt:", ws["B24"].number_format, "| borde B24:", ws["B24"].border.left.style)
        print("  B14 (libre) borde:", ws["B14"].border.left.style, "| B60 borde:", ws["B60"].border.left.style)
        print("  D65 borde:", ws["D65"].border.top.style, "| fuente B24:", ws["B24"].font.name, ws["B24"].font.size)

# ---- prueba insert_rows con merges y alturas ----
print("=" * 90)
print("PRUEBA insert_rows (copia de AT-F9):")
wb = openpyxl.load_workbook(UP / "PLANTILLA FORMATO AT -F9.xlsx")
ws = wb.active
antes = sorted(str(m) for m in ws.merged_cells.ranges)
h20 = ws.row_dimensions[20].height
ws.insert_rows(17, 1)  # insertar 1 fila en 17
despues = sorted(str(m) for m in ws.merged_cells.ranges)
print("  merges antes (20-30):", [m for m in antes if m.startswith(('B2', 'B3'))][:12])
print("  merges después (20-31):", [m for m in despues if m.startswith(('B2', 'B3'))][:12])
print("  altura fila 20 antes:", h20, "-> fila 21 después:", ws.row_dimensions[21].height)
print("  valor B23 (antes B22):", repr(ws["B23"].value)[:50])
print("  valor B21 (antes B20 dif):", repr(ws["B21"].value)[:50])
