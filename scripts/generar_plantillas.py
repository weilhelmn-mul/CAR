"""
generar_plantillas.py — Construye las 4 plantillas Excel oficiales
del Sistema AT con coordenadas EXACTAMENTE alineadas a los mapas de
celdas de src/config.py (MAPA_AT_F3 / F1 / F8 / F9).

Se ejecuta UNA sola vez desde la carpeta del proyecto:
    python generar_plantillas.py
Uso interno de fábrica/compilación: los .xlsx resultantes viajan
empaquetados en la carpeta templates/.
"""
from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path("/home/z/my-project/download/SistemaAT")
sys.path.insert(0, str(RAIZ))

from openpyxl import Workbook  # noqa: E402
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side  # noqa: E402
from openpyxl.utils import get_column_letter  # noqa: E402

from src.config import CATEGORIAS, MAPA_AT_F1, MAPA_AT_F3, MAPA_AT_F8, MAPA_AT_F9, PLANTILLAS  # noqa: E402

AZUL_OSCURO = "0F172A"
INDIGO = "6366F1"
GRIS_CLARO = "E2E8F0"
BLANCO = "FFFFFF"
GRIS_TEXTO = "64748B"

FUENTE_TITULO = Font(name="Segoe UI", size=14, bold=True, color=BLANCO)
FUENTE_INSTITUCION = Font(name="Segoe UI", size=11, bold=True, color=AZUL_OSCURO)
FUENTE_ETIQUETA = Font(name="Segoe UI", size=10, bold=True, color=AZUL_OSCURO)
FUENTE_NORMAL = Font(name="Segoe UI", size=10, color="334155")
FUENTE_CABECERA = Font(name="Segoe UI", size=10, bold=True, color=BLANCO)
RELLENO_TITULO = PatternFill("solid", fgColor=INDIGO)
RELLENO_CABECERA = PatternFill("solid", fgColor=AZUL_OSCURO)
RELLENO_SUAVE = PatternFill("solid", fgColor=GRIS_CLARO)
BORDE = Border(*[Side(style="thin", color="94A3B8")] * 4)
ALINEACION_CENTRO = Alignment(horizontal="center", vertical="center", wrap_text=True)
ALINEACION_IZQUIERDA = Alignment(horizontal="left", vertical="center", wrap_text=True)


def ancho(ws: dict, letra: str, valor: float) -> None:
    ws.column_dimensions[letra].width = valor


def titulo(ws: dict, fila_hasta: int, texto: str) -> None:
    ws.merge_cells(f"A1:J1")
    ws["A1"] = "INSTITUTO PERUANO DEL DEPORTE · DINADAF"
    ws["A1"].font = FUENTE_INSTITUCION
    ws.merge_cells(f"A2:J2")
    ws["A2"] = "Centro de Alto Rendimiento (CAR) — Dirección Nacional de Deporte Afiliado y Afines"
    ws["A2"].font = FUENTE_NORMAL
    ws.merge_cells(f"A{fila_hasta}:J{fila_hasta}")
    celda = ws[f"A{fila_hasta}"]
    celda.value = texto
    celda.font = FUENTE_TITULO
    celda.fill = RELLENO_TITULO
    celda.alignment = ALINEACION_CENTRO
    ws.row_dimensions[fila_hasta].height = 26


def etiqueta(ws: dict, celda: str, texto: str) -> None:
    ws[celda] = texto
    ws[celda].font = FUENTE_ETIQUETA
    ws[celda].alignment = ALINEACION_IZQUIERDA


def bloque(ws: dict, rango: str) -> None:
    ws.merge_cells(rango)
    primera = rango.split(":")[0]
    ws[primera].font = FUENTE_NORMAL
    ws[primera].alignment = Alignment(horizontal="left", vertical="top", wrap_text=True)
    ws[primera].fill = RELLENO_SUAVE
    ws[primera].border = BORDE


def cabecera_tabla(ws: dict, fila: int, columnas: dict[str, str]) -> None:
    for letra, texto in columnas.items():
        celda = ws[f"{letra}{fila}"]
        celda.value = texto
        celda.font = FUENTE_CABECERA
        celda.fill = RELLENO_CABECERA
        celda.alignment = ALINEACION_CENTRO
        celda.border = BORDE


def area_firma(ws: dict, celda_ancla: str, etiqueta_texto: str, fila_etiqueta: int) -> None:
    fila = int("".join(ch for ch in celda_ancla if ch.isdigit()))
    letra = celda_ancla[:len(celda_ancla) - len(str(fila))]
    col_i = ws[f"{letra}{fila}"].column
    col_f = min(col_i + 2, 10)
    ws.merge_cells(start_row=fila, start_column=col_i, end_row=fila + 2, end_column=col_f)
    ws[f"{letra}{fila}"].border = BORDE
    destino = ws.cell(row=fila_etiqueta, column=col_i)
    destino.value = etiqueta_texto
    destino.font = FUENTE_ETIQUETA
    destino.alignment = ALINEACION_CENTRO


# ----------------------------------------------------------------------
def crear_at_f3() -> Workbook:
    libro = Workbook()
    ws = libro.active
    ws.title = "AT-F3"
    titulo(ws, 4, "FORMATO AT-F3 · INFORME TÉCNICO MENSUAL DEL DEPORTISTA")
    for letra, ancho_val in {"A": 14, "B": 12, "C": 22, "D": 12, "E": 14, "F": 12,
                             "G": 12, "H": 12, "I": 12, "J": 12}.items():
        ancho(ws, letra, ancho_val)

    etiqueta(ws, "A10", "Apellidos y nombres:")
    etiqueta(ws, "A11", "Deporte:")
    etiqueta(ws, "A12", "Mes:")
    etiqueta(ws, "A13", "Entrenador:")
    etiqueta(ws, "I10", "Región:")
    etiqueta(ws, "I11", "Año:")
    for fila in range(10, 14):
        for letra in ("C", "J"):
            ws[f"{letra}{fila}"].fill = RELLENO_SUAVE
            ws[f"{letra}{fila}"].border = BORDE

    etiqueta(ws, "A15", "Objetivos del mes:")
    bloque(ws, "C15:J18")

    etiqueta(ws, "A20", "Horario semanal (Lun–Dom):")
    bloque(ws, "C20:C26")

    etiqueta(ws, "A30", "% Asistencia:")
    etiqueta(ws, "A35", "% Plan cumplido:")
    for celda in (MAPA_AT_F3["pct_asist"], MAPA_AT_F3["pct_cump"]):
        ws[celda].number_format = "0%"
        ws[celda].fill = RELLENO_SUAVE
        ws[celda].border = BORDE
        ws[celda].alignment = ALINEACION_CENTRO

    etiqueta(ws, "A38", "Resultados / logros:")
    bloque(ws, "C40:J43")
    etiqueta(ws, "A45", "Competencias SISDENA:")
    bloque(ws, "C45:C49")
    etiqueta(ws, "A50", "Evaluación técnica:")
    bloque(ws, "C50:J52")

    area_firma(ws, MAPA_AT_F3["firma"], "Firma del Entrenador o JUT", 58)
    return libro


def crear_at_f1() -> Workbook:
    libro = Workbook()
    ws = libro.active
    ws.title = "AT-F1"
    titulo(ws, 4, "FORMATO AT-F1 · CONSOLIDADO MENSUAL DEL CAR")
    for letra, ancho_val in {"A": 20, "B": 22, "C": 13, "D": 13, "E": 13, "F": 8,
                             "G": 12, "H": 14, "I": 10, "J": 12}.items():
        ancho(ws, letra, ancho_val)

    etiqueta(ws, "A8", "CAR:")
    etiqueta(ws, "A9", "Mes:")
    etiqueta(ws, "I9", "Año:")
    etiqueta(ws, "A10", "JUT / Representante DINADAF:")
    for fila in range(8, 11):
        for letra in ("C", "J"):
            ws[f"{letra}{fila}"].fill = RELLENO_SUAVE
            ws[f"{letra}{fila}"].border = BORDE

    etiqueta(ws, "A13", "Movimiento de matrículas")
    cabecera_tabla(ws, 13, {"B": "Categoría", "C": "Altas", "D": "Bajas", "E": "Saldo"})
    for indice, categoria in enumerate(CATEGORIAS):
        fila = 14 + indice
        ws[f"B{fila}"] = categoria
        ws[f"B{fila}"].font = FUENTE_ETIQUETA
        for letra in ("B", "C", "D", "E"):
            ws[f"{letra}{fila}"].border = BORDE

    etiqueta(ws, "A21", "Tabla de % por deportista (automática)")
    cabecera_tabla(ws, 21, {"B": "Deportista", "C": "Categoría", "D": "% Asistencia", "E": "% Cumplimiento"})
    for fila in range(22, 41):
        for letra in ("B", "C", "D", "E"):
            ws[f"{letra}{fila}"].border = BORDE
        ws[f"D{fila}"].number_format = "0%"
        ws[f"E{fila}"].number_format = "0%"

    etiqueta(ws, "A35", "Evaluación médica:")
    bloque(ws, "C35:J35")
    etiqueta(ws, "A36", "Evaluación nutricional:")
    bloque(ws, "C36:J36")
    etiqueta(ws, "A37", "Evaluación del CAR:")
    bloque(ws, "C37:J37")
    etiqueta(ws, "A40", "Observaciones:")
    bloque(ws, "C40:J42")

    area_firma(ws, MAPA_AT_F1["firma_jut"], "Firma JUT / Rep. DINADAF", 61)
    area_firma(ws, MAPA_AT_F1["firma_entrenador"], "Firma del Entrenador", 61)
    return libro


def crear_at_f8() -> Workbook:
    libro = Workbook()
    ws = libro.active
    ws.title = "AT-F8"
    titulo(ws, 4, "FORMATO AT-F8 · PLAN MENSUAL DE TRABAJO DEL JUT")
    for letra, ancho_val in {"A": 3, "B": 6, "C": 44, "D": 14, "E": 12, "F": 20, "G": 30,
                             "H": 10, "I": 10, "J": 12}.items():
        ancho(ws, letra, ancho_val)

    etiqueta(ws, "A10", "JUT (Jefe de Unidad Técnica):")
    etiqueta(ws, "A11", "CAR:")
    etiqueta(ws, "A12", "Mes planificado:")
    etiqueta(ws, "I12", "Año:")
    for fila in range(10, 13):
        for letra in ("C", "J"):
            ws[f"{letra}{fila}"].fill = RELLENO_SUAVE
            ws[f"{letra}{fila}"].border = BORDE

    cabecera_tabla(ws, 16, {"B": "N°", "C": "Actividad", "D": "Fecha", "E": "Hora",
                            "F": "Lugar", "G": "Observaciones"})
    for fila in range(17, 37):
        ws[f"B{fila}"] = fila - 16
        ws[f"B{fila}"].alignment = ALINEACION_CENTRO
        ws[f"B{fila}"].font = FUENTE_ETIQUETA
        for letra in ("B", "C", "D", "E", "F", "G"):
            ws[f"{letra}{fila}"].border = BORDE

    area_firma(ws, MAPA_AT_F8["firma"], "Firma del JUT", 43)
    return libro


def crear_at_f9() -> Workbook:
    libro = Workbook()
    ws = libro.active
    ws.title = "AT-F9"
    titulo(ws, 4, "FORMATO AT-F9 · EVALUACIÓN DEL PLAN DEL MES ANTERIOR")
    for letra, ancho_val in {"A": 34, "B": 4, "C": 16, "D": 12, "E": 14, "F": 12,
                             "G": 12, "H": 14, "I": 10, "J": 12}.items():
        ancho(ws, letra, ancho_val)

    etiqueta(ws, "A10", "JUT (Jefe de Unidad Técnica):")
    etiqueta(ws, "A11", "CAR:")
    etiqueta(ws, "A12", "Mes evaluado:")
    etiqueta(ws, "I12", "Año:")
    for fila in range(10, 13):
        for letra in ("C", "J"):
            ws[f"{letra}{fila}"].fill = RELLENO_SUAVE
            ws[f"{letra}{fila}"].border = BORDE

    etiqueta(ws, "A15", "Plan evaluado (AT-F8 · periodo):")
    ws[MAPA_AT_F9["periodo_plan"]].fill = RELLENO_SUAVE
    ws[MAPA_AT_F9["periodo_plan"]].border = BORDE

    etiqueta(ws, "A18", "% Asistencia promedio (AT-F3):")
    etiqueta(ws, "A19", "% Cumplimiento promedio (AT-F3):")
    etiqueta(ws, "A20", "Tareas programadas:")
    etiqueta(ws, "A21", "Tareas cumplidas:")
    etiqueta(ws, "A22", "% de tareas cumplidas:")
    for clave in ("pct_asist_prom", "pct_cump_prom", "pct_tareas"):
        celda = MAPA_AT_F9[clave]
        ws[celda].number_format = "0%"
        ws[celda].fill = RELLENO_SUAVE
        ws[celda].border = BORDE
        ws[celda].alignment = ALINEACION_CENTRO
    for clave in ("tareas_programadas", "tareas_cumplidas"):
        ws[MAPA_AT_F9[clave]].fill = RELLENO_SUAVE
        ws[MAPA_AT_F9[clave]].border = BORDE
        ws[MAPA_AT_F9[clave]].alignment = ALINEACION_CENTRO

    etiqueta(ws, "A25", "Fecha de visita técnica:")
    etiqueta(ws, "A26", "Visita realizada por:")
    etiqueta(ws, "A27", "Observaciones de la visita:")
    bloque(ws, "C27:J29")

    etiqueta(ws, "A30", "Calificación final (BUENO/REGULAR/MALO):")
    ws[MAPA_AT_F9["calificacion_final"]].fill = RELLENO_SUAVE
    ws[MAPA_AT_F9["calificacion_final"]].border = BORDE
    ws[MAPA_AT_F9["calificacion_final"]].alignment = ALINEACION_CENTRO
    ws[MAPA_AT_F9["calificacion_final"]].font = FUENTE_ETIQUETA
    etiqueta(ws, "A33", "Opinión del Presidente FDN (opcional):")
    bloque(ws, "C33:J35")

    area_firma(ws, MAPA_AT_F9["firma_jut"], "Firma del JUT", 41)
    area_firma(ws, MAPA_AT_F9["firma_presidente"], "Firma Presidente FDN (si opinó)", 41)
    return libro


def principal() -> None:
    carpeta = RAIZ / "templates"
    carpeta.mkdir(exist_ok=True)
    generadores = {
        "AT-F3": crear_at_f3,
        "AT-F1": crear_at_f1,
        "AT-F8": crear_at_f8,
        "AT-F9": crear_at_f9,
    }
    for clave, generador in generadores.items():
        destino = carpeta / PLANTILLAS[clave]
        generador().save(destino)
        print(f"[OK] {clave} → {destino.name}")


if __name__ == "__main__":
    principal()
