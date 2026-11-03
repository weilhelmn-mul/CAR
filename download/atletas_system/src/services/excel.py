# -*- coding: utf-8 -*-
"""
src/services/excel.py
=====================
Generación de los formatos oficiales AT-F1, AT-F3, AT-F8 y AT-F9 en Excel,
rellenando las plantillas oficiales del IPD con openpyxl (preserva formato,
logos y estilos) e insertando la imagen de la firma correspondiente.

Funciones públicas:
    generar_at_f3(registro_id) -> str
    generar_at_f1(consolidado_id) -> str
    generar_at_f8(plan_id) -> str
    generar_at_f9(evaluacion_id) -> str

IMPORTANTE — MAPEO DE CELDAS
    Los diccionarios MAPA_* contienen las coordenadas VERIFICADAS contra las
    plantillas oficiales entregadas por la DINADAF (archivo de octubre 2026):
        * AT-F3  → hoja 'Hoja1' (rótulos en columna B, valores en D8:D11,
                   cuadros de respuesta combinados B24/B28/B32/B36/B40/B46/B51).
        * AT-F1  → hoja 'Hoja1' (matrículas filas 13–17, tabla de deportistas
                   filas 24–43, valoraciones en filas 45–67, firmas fila 68).
        * AT-F8  → hoja 'Hoja3' (rótulos de cabecera EN LÍNEA en A7/A8/A9,
                   tareas filas 12–21, firma fila 26).
        * AT-F9  → hoja 'Hoja1' (cabecera D7/D9/H9/J9, sección 1 fila 12,
                   textos B20/B23/B30/B38/B42, calificación C48–C50).
    Si el IPD actualiza una plantilla, revise y ajuste SOLO estos diccionarios.

Comportamiento con plantillas faltantes:
    Si falta el .xlsx en templates/, se lanza FileNotFoundError con el nombre
    exacto del archivo a colocar; la aplicación sigue funcionando.
"""
from __future__ import annotations

import getpass
import io
import json
import logging
import math
import sqlite3
from copy import copy
from pathlib import Path

from openpyxl import load_workbook
from openpyxl.drawing.image import Image as XLImage
from openpyxl.styles import Alignment, Border, Font, Side
from openpyxl.utils import column_index_from_string, get_column_letter
from openpyxl.utils.cell import range_boundaries
from PIL import Image as PILImage

from src import config
from src.database import get_connection, transaccion

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# MAPEOS DE CELDAS (ajustar aquí si cambia una plantilla oficial)
# ---------------------------------------------------------------------------
# Entradas de texto: tupla (celda_ancla, fila_ini, fila_fin, caracteres_por_linea)
# Las áreas marcadas como "creadas" son recuadros que el generador agrega al
# vuelo sobre filas libres de la plantilla (borde fino, fuente Arial 9).

MAPA_AT_F3 = {
    "nombre": "D8",       # NOMBRE DEL DEPORTISTA (combinado D8:H8)
    "deporte": "D9",      # DEPORTE (D9:H9)
    "mes": "D10",         # MES (D10:H10)
    "entrenador": "D11",  # ENTRENADOR (D11:H11)
    "region": "J8",       # REGION:
    "anio": "J9",         # AÑO:
    "objetivos": ("B14", 14, 16, 75),          # 1. Objetivos (recuadro creado B14:J16)
    "horario": {                               # 2. Matriz sesión × día
        "fila_manana": 19, "fila_tarde": 20, "fila_noche": 21,
        "col_inicio": "D", "col_fin": "J",     # LUNES= D … DOMINGO= J
    },
    "pct_asist": "B24",                        # 3. % asistencia (cuadro B24:J25)
    "pct_cump": "B28",                         # 4. % cumplimiento (cuadro B28:J29)
    "resultados": ("B32", 32, 33, 75),         # 5. Test pedagógicos
    "detalle": ("B36", 36, 37, 75),            # 6. Detalle de la preparación
    "participacion": ("B40", 40, 43, 75),      # 7. Participación en competencias (SISDENA)
    "cumplimiento_objetivos": ("B46", 46, 48, 75),  # 8. Cumplimiento de objetivos
    "evaluacion": ("B51", 51, 54, 75),         # 9. Evaluación general
    "observaciones": ("B60", 60, 63, 75),      # Observaciones (recuadro creado B60:J63)
    "firma": "D65",                            # Imagen de firma sobre el rótulo D66
}

MAPA_AT_F1 = {
    "car": "C7", "mes": "C8", "anio": "E8",
    "matriculas": {                            # Sección I: filas 13–17 + TOTAL 18
        "fila_inicio": 13, "fila_total": 18,
        "col_retiros": "C", "col_ingresos": "D", "col_damas": "E", "col_varones": "F",
        "col_total": "G", "col_sesiones": "H", "col_manana": "I", "col_tarde": "J",
    },
    "tabla": {                                 # Sección II.I: filas 24–43 (20 cupos)
        "fila_inicio": 24,
        "col_n": "A", "col_nombre": "B", "col_deporte": "F", "col_prueba": "G",
        "col_asist": "H", "col_cump": "I", "col_resultados": "J",
        "alto_fila_extra": 54.0,
    },
    "valoracion_tecnica": ("A45", 45, 45, 160),      # II-II
    "dificultades": ("A48", 48, 48, 160),            # II.III
    "valoracion_medica": ("A51", 51, 51, 160),       # III
    "plan_profilactico": ("A54", 54, 54, 160),       # III-I
    "balance_nutricional": ("A58", 58, 58, 160),     # III-II
    "valoracion_car": ("A61", 61, 61, 160),          # IV
    "aspectos_logros": ("A64", 64, 64, 160),         # IV-I (negativos + logros)
    "otros_aspectos": ("A67", 67, 67, 160),          # IV.II (recuadro creado A67:J67)
    "firma_jut": "B69",                              # bajo el rótulo de la fila 68
    "firma_entrenador": "H69",
}

MAPA_AT_F8 = {
    # La cabecera oficial lleva el valor EN LÍNEA tras el rótulo (A7/A8/A9)
    "federacion": ("A7", "FEDERACION:"),
    "nombres": ("A8", "NOMBRES Y APELLIDOS:"),
    "mes_anio": "A9",
    "tareas": {
        "fila_inicio": 12, "fila_fin": 21,     # 10 filas de tareas en la plantilla
        "col_n": "A", "col_actividad": "B", "col_fecha": "C",
        "col_hora": "D", "col_lugar": "E", "col_obs": "F",
        "alto_fila": 40.5,
    },
    "firma": "C26",                            # sobre el rótulo C27
}

MAPA_AT_F9 = {
    "nombres": "D7", "federacion": "D9", "mes": "H9", "anio": "J9",
    "tareas_planificadas": "D12", "tareas_cumplidas": "F12", "pct": "H12",
    "evaluacion_cumplimiento": ("B15", 15, 15, 110),   # recuadro creado B15:I15
    "fila_reseña": 17,                                  # fila insertada para la reseña si hace falta
    "pct_cumplimiento_prep": "G17",                     # tras el rótulo B17:F17
    "pct_asistencia": "G18",                            # tras el rótulo B18
    "dificultades_analizadas": ("B20", 20, 20, 110),
    "resumen_documentacion": ("B23", 23, 23, 110),
    "cantidad_visitas": "D26", "evaluacion_visitas": "D27",
    "resumen_dificultades": ("B30", 30, 30, 110),
    "actualizacion_bd": "F33", "cumplimiento_calendario": "F34", "capacitaciones": "F35",
    "analisis_poa": ("B38", 38, 38, 110),
    "otros_datos": ("B42", 42, 42, 110),
    "opinion_presidente": ("B45", 45, 45, 110),
    "calif_bueno": "C48", "calif_regular": "C49", "calif_malo": "C50",
    "firma_jut": "D55",                                 # sobre el rótulo D56
    "firma_presidente": "H55",                          # a la derecha (si hay opinión)
}

_LADO = Side(style="thin")
_FUENTE_TEXTO = Font(name="Arial", size=9)


# ---------------------------------------------------------------------------
# Utilidades generales
# ---------------------------------------------------------------------------
def _ruta_plantilla(tipo: str) -> Path:
    """Ruta de la plantilla oficial; FileNotFoundError con nombre exacto si falta."""
    nombre = config.PLANTILLAS[tipo]
    ruta = config.TEMPLATES_DIR / nombre
    if not ruta.exists():
        raise FileNotFoundError(
            f"No se encontró la plantilla oficial '{nombre}'.\n"
            f"Colóquela en la carpeta: {config.TEMPLATES_DIR}\n"
            f"(el nombre del archivo debe ser exactamente ese)."
        )
    return ruta


def _escribir(ws, coordenada: str, valor) -> None:
    """Escribe un valor simple; None limpia la celda (evita datos residuales)."""
    ws[coordenada] = None if valor in (None, "") else valor


def _desplazar(coordenada: str, filas: int) -> str:
    """'B69' + 2 → 'B71' (tras insertar filas por encima)."""
    if filas <= 0:
        return coordenada
    letra = "".join(ch for ch in coordenada if ch.isalpha())
    numero = int("".join(ch for ch in coordenada if ch.isdigit()))
    return f"{letra}{numero + filas}"


def _desplazar_entrada(entrada: tuple, filas: int) -> tuple:
    """Desplaza una entrada de texto (celda, f1, f2, chars) `filas` hacia abajo."""
    celda, f1, f2, chars = entrada
    return (_desplazar(celda, filas), f1 + filas, f2 + filas, chars)


def _texto_area(ws, entrada: tuple, texto) -> None:
    """Escribe texto multilínea en un cuadro (celda ancla, normalmente combinada),
    activa el ajuste de texto y aumenta la altura de las filas del área si hace falta.
    Con texto vacío limpia el cuadro (evita datos residuales de la plantilla)."""
    celda, f1, f2, chars = entrada
    valor = (str(texto).strip() if texto else "") or None
    ws[celda] = valor
    if not valor:
        return
    actual = ws[celda].alignment
    ws[celda].alignment = Alignment(
        horizontal=actual.horizontal or "left", vertical=actual.vertical or "top", wrap_text=True
    )
    lineas = sum(max(1, math.ceil(len(p) / chars)) for p in str(valor).split("\n"))
    necesario = lineas * 12.75 + 8.0
    actual_px = sum((ws.row_dimensions[r].height or 15.0) for r in range(f1, f2 + 1))
    if necesario > actual_px:
        extra = (necesario - actual_px) / (f2 - f1 + 1)
        for r in range(f1, f2 + 1):
            ws.row_dimensions[r].height = (ws.row_dimensions[r].height or 15.0) + extra


def _crear_area_texto(ws, rango: str) -> None:
    """Convierte un rango libre de la plantilla en un recuadro de texto con el
    estilo oficial (borde fino, fuente Arial 9, ajuste de texto, alineado arriba)."""
    ws.merge_cells(rango)
    c1, f1, c2, f2 = range_boundaries(rango)
    ancla = ws.cell(row=f1, column=c1)
    ancla.font = copy(_FUENTE_TEXTO)
    ancla.alignment = Alignment(wrap_text=True, vertical="top", horizontal="left")
    for r in range(f1, f2 + 1):
        for c in range(c1, c2 + 1):
            ws.cell(row=r, column=c).border = Border(
                left=_LADO if c == c1 else None,
                right=_LADO if c == c2 else None,
                top=_LADO if r == f1 else None,
                bottom=_LADO if r == f2 else None,
            )


def _insertar_filas_seguras(ws, fila: int, cantidad: int, fila_estilo: int | None = None,
                            col_ini: int = 1, col_fin: int = 10, alto_nueva: float | None = None) -> None:
    """Inserta filas REUBICANDO manualmente celdas combinadas y alturas de fila
    (openpyxl mueve los valores pero NO los merges ni las alturas)."""
    # 1) Merges que empiezan en o después de `fila` → desmontar
    rangos = [(m.min_row, m.min_col, m.max_row, m.max_col)
              for m in list(ws.merged_cells.ranges) if m.min_row >= fila]
    for m in list(ws.merged_cells.ranges):
        if m.min_row >= fila:
            ws.unmerge_cells(str(m))
    # 2) Alturas personalizadas desde `fila` → guardar y limpiar
    alturas = {r: d.height for r, d in ws.row_dimensions.items()
               if r >= fila and d.height is not None}
    for r in alturas:
        ws.row_dimensions[r].height = None
    # 3) Insertar
    ws.insert_rows(fila, cantidad)
    # 4) Recomponer merges desplazados
    for r1, c1, r2, c2 in rangos:
        ws.merge_cells(start_row=r1 + cantidad, start_column=c1,
                       end_row=r2 + cantidad, end_column=c2)
    # 5) Recomponer alturas desplazadas
    for r, h in alturas.items():
        ws.row_dimensions[r + cantidad].height = h
    # 6) Estilo de las nuevas filas copiado de una fila de referencia
    if fila_estilo is not None:
        for i in range(cantidad):
            for col in range(col_ini, col_fin + 1):
                origen = ws.cell(row=fila_estilo, column=col)
                destino = ws.cell(row=fila + i, column=col)
                destino.font = copy(origen.font)
                destino.border = copy(origen.border)
                destino.fill = copy(origen.fill)
                destino.alignment = copy(origen.alignment)
                destino.number_format = origen.number_format
            ws.row_dimensions[fila + i].height = alto_nueva or ws.row_dimensions[fila_estilo].height


def _fila_de_etiqueta(ws, columna: str, prefijo: str, desde: int) -> int:
    """Devuelve la fila cuya celda `columna` empieza con `prefijo` (desde `desde`)."""
    idx = column_index_from_string(columna)
    for r in range(desde, ws.max_row + 2):
        valor = ws.cell(row=r, column=idx).value
        if valor is not None and str(valor).strip().upper().startswith(prefijo):
            return r
    raise RuntimeError(
        f"No se encontró la etiqueta '{prefijo}' en la columna {columna} de la plantilla. "
        f"Revise el MAPA correspondiente en src/services/excel.py."
    )


def _pct_texto(valor) -> str | None:
    """0.95 → '95%'; 0.85714 → '85.7%'; None → None."""
    if valor is None:
        return None
    n = float(valor) * 100
    return f"{n:.0f}%" if abs(n - round(n)) < 1e-9 else f"{n:.1f}%"


def _a_entero(texto) -> int | None:
    """Convierte '5', '5 ' o 5 → 5; None si no se puede."""
    if texto in (None, ""):
        return None
    try:
        return int(float(str(texto).strip()))
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Firmas
# ---------------------------------------------------------------------------
def _firma_activa(rol: str) -> sqlite3.Row | None:
    """Firma activa más reciente del rol indicado (o None)."""
    con = get_connection()
    try:
        return con.execute(
            "SELECT * FROM firmas WHERE rol = ? AND activa = 1 ORDER BY id DESC LIMIT 1",
            (rol,),
        ).fetchone()
    finally:
        con.close()


def _registrar_firma_aplicada(firma_id: int, tipo_documento: str, documento_id: int, notas: str = "") -> None:
    """Deja constancia en asignaciones_firma y auditoria_firmas."""
    usuario = getpass.getuser()
    with transaccion() as con:
        con.execute(
            "INSERT INTO asignaciones_firma (firma_id, tipo_documento, documento_id, notas) VALUES (?,?,?,?)",
            (firma_id, tipo_documento, documento_id, notas or None),
        )
        con.execute(
            "INSERT INTO auditoria_firmas (firma_id, accion, usuario, detalle) VALUES (?,?,?,?)",
            (firma_id, "aplicacion", usuario, f"{tipo_documento} #{documento_id} · {notas}"),
        )


def _insertar_imagen_firma(ws, firma: sqlite3.Row | None, coordenada: str,
                           tipo_documento: str | None = None, documento_id: int | None = None,
                           *, ancho_px: int = 160, alto_px: int = 60, notas: str = "") -> bool:
    """Inserta el PNG de la firma redimensionado a ~160×60 px anclado a `coordenada`.
    Devuelve True si se insertó; False si no hay firma activa para el rol."""
    if firma is None:
        log.warning("Documento %s #%s: sin firma activa para el rol indicado.", tipo_documento, documento_id)
        return False
    ruta = Path(firma["imagen_path"])
    if not ruta.exists():
        raise FileNotFoundError(
            f"La imagen de la firma de '{firma['persona_nombre']}' no está en:\n{ruta}\n"
            f"Vuelva a subir la firma desde la vista Firmas."
        )
    pil = PILImage.open(ruta).convert("RGBA")
    escala = min(ancho_px / pil.width, alto_px / pil.height, 1.0)
    pil = pil.resize((max(1, int(pil.width * escala)), max(1, int(pil.height * escala))), PILImage.LANCZOS)
    # openpyxl requiere un respaldo legible: se entrega el PNG en memoria
    bufer = io.BytesIO()
    pil.save(bufer, format="PNG")
    bufer.seek(0)
    imagen = XLImage(bufer)
    ws.add_image(imagen, coordenada)
    if tipo_documento and documento_id is not None:
        _registrar_firma_aplicada(firma["id"], tipo_documento, documento_id, notas)
    return True


def _guardar_libro(wb, nombre_archivo: str) -> str:
    """Guarda el libro en generados/ y devuelve la ruta absoluta."""
    ruta = config.GENERADOS_DIR / nombre_archivo
    wb.save(ruta)
    log.info("Documento generado: %s", ruta)
    return str(ruta)


# ---------------------------------------------------------------------------
# AT-F3 · Informe técnico mensual del deportista
# ---------------------------------------------------------------------------
def _escribir_horario(ws, mapa_horario: dict, horario: dict | None) -> None:
    """Limpia y escribe la matriz sesión × día del AT-F3."""
    col_ini = column_index_from_string(mapa_horario["col_inicio"])
    col_fin = column_index_from_string(mapa_horario["col_fin"])
    filas = {
        "MAÑANA": mapa_horario["fila_manana"],
        "TARDE": mapa_horario["fila_tarde"],
        "NOCHE": mapa_horario["fila_noche"],
    }
    for f in filas.values():
        for c in range(col_ini, col_fin + 1):
            ws.cell(row=f, column=c).value = None
    datos = horario or {}
    for sesion, f in filas.items():
        por_dia = datos.get(sesion, {}) or {}
        for i, dia in enumerate(config.DIAS):
            texto = str(por_dia.get(dia, "") or "").strip()
            if texto:
                ws.cell(row=f, column=col_ini + i).value = texto


def generar_at_f3(registro_id: int) -> str:
    """Genera el Excel oficial AT-F3 del registro mensual indicado."""
    con = get_connection()
    try:
        reg = con.execute(
            """
            SELECT r.*, d.nombres_apellidos, d.deporte AS deporte_dep,
                   d.region AS region_dep, d.entrenador AS entrenador_dep
            FROM registros_mensuales r JOIN deportistas d ON d.id = r.deportista_id
            WHERE r.id = ?
            """,
            (registro_id,),
        ).fetchone()
    finally:
        con.close()
    if reg is None:
        raise ValueError(f"No existe el registro AT-F3 con id={registro_id}.")

    wb = load_workbook(_ruta_plantilla("AT-F3"), keep_links=True)
    ws = wb.active
    # La plantilla AT-F3 no trae ajuste de impresión: se fuerza 1 página de
    # ancho para que el PDF salga íntegro (no altera el contenido oficial).
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    if ws.sheet_properties.pageSetUpPr is None:
        from openpyxl.worksheet.properties import PageSetupProperties
        ws.sheet_properties.pageSetUpPr = PageSetupProperties(fitToPage=True)
    else:
        ws.sheet_properties.pageSetUpPr.fitToPage = True
    m = MAPA_AT_F3
    periodo = reg["periodo"]

    _escribir(ws, m["nombre"], reg["nombres_apellidos"])
    _escribir(ws, m["deporte"], reg["deporte_dep"])
    _escribir(ws, m["mes"], config.mes_de_periodo(periodo))
    _escribir(ws, m["anio"], config.anio_de_periodo(periodo))
    _escribir(ws, m["entrenador"], reg["entrenador"] or reg["entrenador_dep"])
    _escribir(ws, m["region"], reg["region_dep"])
    _escribir_horario(ws, m["horario"], json.loads(reg["horario_json"]) if reg["horario_json"] else {})
    _texto_area(ws, m["objetivos"], reg["objetivos_metas"])
    _escribir(ws, m["pct_asist"], _pct_texto(reg["pct_asistencia"]))
    _escribir(ws, m["pct_cump"], _pct_texto(reg["pct_cumplimiento"]))
    _texto_area(ws, m["resultados"], reg["resultados_test"])
    _texto_area(ws, m["detalle"], reg["detalle_preparacion"])
    _texto_area(ws, m["participacion"], reg["participacion_competencias"])
    _texto_area(ws, m["cumplimiento_objetivos"], reg["cumplimiento_objetivos"])
    _texto_area(ws, m["evaluacion"], reg["evaluacion_general"])
    _crear_area_texto(ws, "B60:J63")                       # recuadro de observaciones
    _texto_area(ws, m["observaciones"], reg["observaciones"])

    # Firma: Entrenador o, en su defecto, Jefe de Unidad Técnica
    firma = _firma_activa("entrenador") or _firma_activa("jut")
    _insertar_imagen_firma(
        ws, firma, m["firma"], "AT-F3", registro_id,
        notas=f"{reg['nombres_apellidos']} · {periodo}",
    )
    return _guardar_libro(
        wb, f"AT-F3_{config.nombre_archivo_seguro(reg['nombres_apellidos'])}_{periodo}.xlsx"
    )


# ---------------------------------------------------------------------------
# AT-F1 · Consolidado del CAR
# ---------------------------------------------------------------------------
def generar_at_f1(consolidado_id: int) -> str:
    """Genera el Excel oficial AT-F1 (consolidado del CAR) del período indicado.

    La tabla II.I admite 20 deportistas con la plantilla entregada; si hay más,
    se insertan filas adicionales (reubicando merges y alturas de forma segura).
    """
    con = get_connection()
    try:
        consol = con.execute(
            "SELECT * FROM consolidados_at_f1 WHERE id = ?", (consolidado_id,)
        ).fetchone()
        atletas = []
        if consol is not None:
            atletas = con.execute(
                """
                SELECT d.nombres_apellidos, d.deporte, d.prueba_modalidad,
                       r.pct_asistencia, r.pct_cumplimiento,
                       r.participacion_competencias, r.detalle_preparacion
                FROM registros_mensuales r JOIN deportistas d ON d.id = r.deportista_id
                WHERE r.periodo = ?
                ORDER BY d.nombres_apellidos COLLATE NOCASE
                """,
                (consol["periodo"],),
            ).fetchall()
    finally:
        con.close()
    if consol is None:
        raise ValueError(f"No existe el consolidado AT-F1 con id={consolidado_id}.")

    wb = load_workbook(_ruta_plantilla("AT-F1"), keep_links=True)
    ws = wb.active
    m = MAPA_AT_F1
    periodo = consol["periodo"]

    # ---- Capacidad de la tabla II.I e inserción de filas si hace falta ----
    fila_ii_ii = _fila_de_etiqueta(ws, "A", "II-II", m["tabla"]["fila_inicio"])
    slots = fila_ii_ii - m["tabla"]["fila_inicio"]
    extra = max(0, len(atletas) - slots)
    if extra:
        _insertar_filas_seguras(
            ws, fila_ii_ii, extra,
            fila_estilo=fila_ii_ii - 1, col_ini=1, col_fin=10,
            alto_nueva=m["tabla"]["alto_fila_extra"],
        )
        log.info("AT-F1: %d deportista(s) adicionales → %d fila(s) insertadas.", len(atletas), extra)
    if len(atletas) > slots:
        log.warning("AT-F1: se escriben %d deportistas (capacidad ampliada).", len(atletas))

    # ---- Cabecera ----
    _escribir(ws, m["car"], consol["car"])
    _escribir(ws, m["mes"], config.mes_de_periodo(periodo))
    _escribir(ws, m["anio"], config.anio_de_periodo(periodo))

    # ---- Sección I: matrículas ----
    mm = m["matriculas"]
    matriculas = json.loads(consol["matriculas_json"]) if consol["matriculas_json"] else {}
    tot = {"retiros": 0, "ingresos": 0, "damas": 0, "varones": 0, "total": 0}
    for i, cat in enumerate(config.CATEGORIAS):
        fila = mm["fila_inicio"] + i
        d = matriculas.get(cat, {}) or {}
        retiros = _a_entero(d.get("retiros", 0)) or 0
        ingresos = _a_entero(d.get("ingresos", 0)) or 0
        damas = _a_entero(d.get("damas", 0)) or 0
        varones = _a_entero(d.get("varones", 0)) or 0
        total = damas + varones
        ws[f"{mm['col_retiros']}{fila}"] = retiros
        ws[f"{mm['col_ingresos']}{fila}"] = ingresos
        ws[f"{mm['col_damas']}{fila}"] = damas
        ws[f"{mm['col_varones']}{fila}"] = varones
        ws[f"{mm['col_total']}{fila}"] = total
        ws[f"{mm['col_sesiones']}{fila}"] = _a_entero(d.get("sesiones"))
        ws[f"{mm['col_manana']}{fila}"] = d.get("manana") or None
        ws[f"{mm['col_tarde']}{fila}"] = d.get("tarde") or None
        tot["retiros"] += retiros; tot["ingresos"] += ingresos
        tot["damas"] += damas; tot["varones"] += varones; tot["total"] += total
    fila = mm["fila_total"]
    for clave, col in (("retiros", "C"), ("ingresos", "D"), ("damas", "E"),
                       ("varones", "F"), ("total", "G")):
        ws[f"{col}{fila}"] = tot[clave]

    # ---- Sección II.I: tabla de deportistas (desde registros AT-F3) ----
    t = m["tabla"]
    for r in range(t["fila_inicio"], fila_ii_ii):
        for col in ("A", "B", "F", "G", "H", "I", "J"):
            ws[f"{col}{r}"] = None
    for i, a in enumerate(atletas):
        fila = t["fila_inicio"] + i
        ws[f"{t['col_n']}{fila}"] = i + 1
        ws[f"{t['col_nombre']}{fila}"] = a["nombres_apellidos"]
        ws[f"{t['col_deporte']}{fila}"] = a["deporte"]
        ws[f"{t['col_prueba']}{fila}"] = a["prueba_modalidad"]
        ws[f"{t['col_asist']}{fila}"] = a["pct_asistencia"]      # formato 0% ya aplicado
        ws[f"{t['col_cump']}{fila}"] = a["pct_cumplimiento"]
        resultado = (a["participacion_competencias"] or a["detalle_preparacion"] or "").strip()
        celda = f"{t['col_resultados']}{fila}"
        ws[celda] = resultado or None
        if resultado:
            al = ws[celda].alignment
            ws[celda].alignment = Alignment(
                horizontal=al.horizontal or "left", vertical=al.vertical or "top", wrap_text=True
            )

    # ---- Valoraciones cualitativas (coordenadas desplazadas si se insertaron filas) ----
    s = extra
    _texto_area(ws, _desplazar_entrada(m["valoracion_tecnica"], s), consol["valoracion_tecnica"])
    _texto_area(ws, _desplazar_entrada(m["dificultades"], s), consol["dificultades"])
    _texto_area(ws, _desplazar_entrada(m["valoracion_medica"], s), consol["valoracion_medica"])
    _texto_area(ws, _desplazar_entrada(m["plan_profilactico"], s), consol["plan_profilactico"])
    _texto_area(ws, _desplazar_entrada(m["balance_nutricional"], s), consol["balance_nutricional"])
    _texto_area(ws, _desplazar_entrada(m["valoracion_car"], s), consol["valoracion_car"])
    aspectos = "\n".join(x for x in (consol["aspectos_negativos"], consol["logros_car"]) if x)
    _texto_area(ws, _desplazar_entrada(m["aspectos_logros"], s), aspectos)
    rango_otros = f"A{67 + s}:J{67 + s}"
    _crear_area_texto(ws, rango_otros)                    # recuadro IV.II (fila libre)
    _texto_area(ws, _desplazar_entrada(m["otros_aspectos"], s), consol["otros_aspectos"])

    # ---- Firmas: JUT/DINADAF + Entrenador ----
    notas = f"{consol['car']} · {periodo}"
    firma_jut = _firma_activa("jut") or _firma_activa("dinadaf")
    _insertar_imagen_firma(ws, firma_jut, _desplazar(m["firma_jut"], s), "AT-F1", consolidado_id, notas=notas)
    firma_ent = _firma_activa("entrenador")
    _insertar_imagen_firma(ws, firma_ent, _desplazar(m["firma_entrenador"], s), "AT-F1", consolidado_id, notas=notas)
    return _guardar_libro(
        wb, f"AT-F1_{config.nombre_archivo_seguro(consol['car'])}_{periodo}.xlsx"
    )


# ---------------------------------------------------------------------------
# AT-F8 · Plan de trabajo mensual del JUT
# ---------------------------------------------------------------------------
def generar_at_f8(plan_id: int) -> str:
    """Genera el Excel oficial AT-F8 del plan de trabajo indicado."""
    con = get_connection()
    try:
        plan = con.execute("SELECT * FROM planes_jut WHERE id = ?", (plan_id,)).fetchone()
    finally:
        con.close()
    if plan is None:
        raise ValueError(f"No existe el plan AT-F8 con id={plan_id}.")

    wb = load_workbook(_ruta_plantilla("AT-F8"), keep_links=True)
    ws = wb.active
    m = MAPA_AT_F8
    periodo = plan["periodo"]

    # Cabecera (la plantilla lleva el valor en línea tras el rótulo)
    pref_fed, pref_nom = m["federacion"][1], m["nombres"][1]
    ws[m["federacion"][0]] = f"{pref_fed} {plan['federacion'] or ''}".rstrip()
    ws[m["nombres"][0]] = f"{pref_nom} {plan['jut_nombre'] or ''}".rstrip()
    ws[m["mes_anio"]] = f"MES: {config.mes_de_periodo(periodo)}          AÑO: {config.anio_de_periodo(periodo)}"

    # Tareas: limpiar y escribir (insertando filas si exceden la plantilla)
    t = m["tareas"]
    for r in range(t["fila_inicio"], t["fila_fin"] + 1):
        for col in (t["col_n"], t["col_actividad"], t["col_fecha"], t["col_hora"],
                    t["col_lugar"], t["col_obs"]):
            ws[f"{col}{r}"] = None
    tareas = json.loads(plan["tareas_json"]) if plan["tareas_json"] else []
    slots = t["fila_fin"] - t["fila_inicio"] + 1
    extra = max(0, len(tareas) - slots)
    if extra:
        _insertar_filas_seguras(
            ws, t["fila_fin"] + 1, extra,
            fila_estilo=t["fila_fin"], col_ini=1, col_fin=6, alto_nueva=t["alto_fila"],
        )
    for i, tarea in enumerate(tareas):
        fila = t["fila_inicio"] + i
        ws[f"{t['col_n']}{fila}"] = i + 1
        ws[f"{t['col_actividad']}{fila}"] = tarea.get("actividad") or None
        ws[f"{t['col_fecha']}{fila}"] = tarea.get("fecha") or None
        ws[f"{t['col_hora']}{fila}"] = tarea.get("hora") or None
        ws[f"{t['col_lugar']}{fila}"] = tarea.get("lugar") or None
        ws[f"{t['col_obs']}{fila}"] = tarea.get("observaciones") or None

    firma = _firma_activa("jut") or _firma_activa("dinadaf")
    _insertar_imagen_firma(
        ws, firma, _desplazar(m["firma"], extra), "AT-F8", plan_id,
        notas=f"{plan['jut_nombre']} · {periodo}",
    )
    return _guardar_libro(
        wb, f"AT-F8_{config.nombre_archivo_seguro(plan['jut_nombre'])}_{periodo}.xlsx"
    )


# ---------------------------------------------------------------------------
# AT-F9 · Informe de cumplimiento del JUT
# ---------------------------------------------------------------------------
def generar_at_f9(evaluacion_id: int) -> str:
    """Genera el Excel oficial AT-F9 de la evaluación indicada.

    La 'breve reseña de las reuniones de trabajo educativo' no tiene recuadro
    propio en la plantilla oficial: si trae texto, se inserta una fila dentro
    de la sección 2 (entre el encabezado y los porcentajes) usando la inserción
    segura de filas; el resto de coordenadas se desplaza automáticamente.
    """
    con = get_connection()
    try:
        # La federación de la cabecera proviene del plan AT-F8 evaluado
        ev = con.execute(
            """
            SELECT e.*, p.federacion AS federacion_plan
            FROM evaluaciones_jut e LEFT JOIN planes_jut p ON p.id = e.plan_id
            WHERE e.id = ?
            """,
            (evaluacion_id,),
        ).fetchone()
    finally:
        con.close()
    if ev is None:
        raise ValueError(f"No existe la evaluación AT-F9 con id={evaluacion_id}.")

    wb = load_workbook(_ruta_plantilla("AT-F9"), keep_links=True)
    ws = wb.active
    m = MAPA_AT_F9
    periodo = ev["periodo"]

    # ---- Cabecera ----
    _escribir(ws, m["nombres"], ev["jut_nombre"])
    _escribir(ws, m["federacion"], ev["federacion_plan"] or "")
    _escribir(ws, m["mes"], config.mes_de_periodo(periodo))
    _escribir(ws, m["anio"], config.anio_de_periodo(periodo))

    # ---- Sección 1: cumplimiento de tareas ----
    planificadas = ev["tareas_planificadas"] or 0
    cumplidas = ev["tareas_cumplidas"] or 0
    pct = ev["pct_cumplimiento"]
    _escribir(ws, m["tareas_planificadas"], planificadas)
    _escribir(ws, m["tareas_cumplidas"], cumplidas)
    _escribir(ws, m["pct"], _pct_texto(pct) or "0%")
    _crear_area_texto(ws, "B15:I15")                       # recuadro de la evaluación
    _texto_area(ws, m["evaluacion_cumplimiento"], ev["evaluacion_cumplimiento"])

    # ---- Sección 2: % promedios (informados al guardar) y dificultades ----
    _escribir(ws, m["pct_cumplimiento_prep"], _pct_texto(ev["pct_cumplimiento_promedio"]))
    _escribir(ws, m["pct_asistencia"], _pct_texto(ev["pct_asistencia_promedio"]))
    _texto_area(ws, m["dificultades_analizadas"], ev["resumen_dificultades_seccion2"])

    # ---- Secciones 3 a 7 ----
    _texto_area(ws, m["resumen_documentacion"], ev["resumen_documentacion"])
    _escribir(ws, m["cantidad_visitas"], ev["cantidad_visitas"])
    _escribir(ws, m["evaluacion_visitas"], ev["evaluacion_visitas"])
    _texto_area(ws, m["resumen_dificultades"], ev["resumen_dificultades"])
    _escribir(ws, m["actualizacion_bd"], ev["actualizacion_bd"])
    _escribir(ws, m["cumplimiento_calendario"], ev["cumplimiento_calendario"])
    _escribir(ws, m["capacitaciones"], ev["capacitaciones"])
    _texto_area(ws, m["analisis_poa"], ev["analisis_poa"])
    _texto_area(ws, m["otros_datos"], ev["otros_datos"])
    _texto_area(ws, m["opinion_presidente"], ev["opinion_presidente"])

    # ---- Sección 8: calificación (limpiar las 3 y marcar una) ----
    for coord in (m["calif_bueno"], m["calif_regular"], m["calif_malo"]):
        ws[coord] = None
    if ev["calificacion_final"] == "BUENO":
        ws[m["calif_bueno"]] = "X"
    elif ev["calificacion_final"] == "REGULAR":
        ws[m["calif_regular"]] = "X"
    elif ev["calificacion_final"] == "MALO":
        ws[m["calif_malo"]] = "X"

    # ---- Reseña de reuniones (fila insertada dentro de la sección 2) ----
    desplazamiento = 0
    if (ev["resumen_reuniones"] or "").strip():
        desplazamiento = 1
        _insertar_filas_seguras(ws, m["fila_reseña"], 1)
        _crear_area_texto(ws, f"B{m['fila_reseña']}:J{m['fila_reseña']}")
        _texto_area(ws, (f"B{m['fila_reseña']}", m["fila_reseña"], m["fila_reseña"], 110),
                    ev["resumen_reuniones"])

    # ---- Firmas ----
    firma_jut = _firma_activa("jut")
    _insertar_imagen_firma(
        ws, firma_jut, _desplazar(m["firma_jut"], desplazamiento), "AT-F9", evaluacion_id,
        notas=f"{ev['jut_nombre']} · {periodo}",
    )
    if (ev["opinion_presidente"] or "").strip():
        firma_pres = _firma_activa("presidente_fdn")
        _insertar_imagen_firma(
            ws, firma_pres, _desplazar(m["firma_presidente"], desplazamiento),
            "AT-F9", evaluacion_id, notas="Presidente FDN",
        )
    return _guardar_libro(
        wb, f"AT-F9_{config.nombre_archivo_seguro(ev['jut_nombre'])}_{periodo}.xlsx"
    )
