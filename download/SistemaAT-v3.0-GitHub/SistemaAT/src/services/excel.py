"""
=============================================================
 Sistema AT · Instituto Peruano del Deporte (IPD - DINADAF)
 services/excel.py — Generadores de los formatos oficiales
 AT-F3 / AT-F1 / AT-F8 / AT-F9 a partir de las plantillas
 Excel del IPD, incluyendo estampado de firmas verificadas.
=============================================================
"""
from __future__ import annotations

import json
import logging
import re
import unicodedata
from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.worksheet.worksheet import Worksheet

from src import database as db
from src.config import (
    CATEGORIAS,
    GENERADOS_DIR,
    MAPA_AT_F1,
    MAPA_AT_F3,
    MAPA_AT_F8,
    MAPA_AT_F9,
    MESES,
    PLANTILLAS,
    ruta_recurso,
)

log = logging.getLogger("sistema_at.excel")

FORMATO_PORCENTAJE = "0%"


# ----------------------------------------------------------------------
# Utilidades públicas
# ----------------------------------------------------------------------
def parsear_porcentaje(texto: str | None) -> float | None:
    """Convierte '95', '95%' u '0.95' a una fracción 0.0–1.0.

    Regla oficial: los números "pelados" se interpretan como puntos porcentuales
    (95 → 0.95); con punto/coma decimal se toma la fracción (0.95 → 0.95).
    Devuelve None si el texto está vacío. Lanza ValueError si es inválido.
    """
    if texto is None:
        return None
    limpio = texto.strip().replace("%", "").replace(",", ".")
    if not limpio:
        return None
    valor = float(limpio)  # ValueError si no es número
    if valor < 0:
        raise ValueError("El porcentaje no puede ser negativo.")
    if "." in limpio and valor <= 1:
        return valor
    if valor <= 100:
        return valor / 100.0
    raise ValueError("El porcentaje debe estar entre 0 y 100 (acepta 95, 95% o 0.95).")


def _nombre_seguro(texto: str) -> str:
    """Normaliza un nombre para usarlo en nombre de archivo (ASCII, mayúsculas)."""
    normalizado = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    limpio = re.sub(r"[^A-Za-z0-9]+", "_", normalizado).strip("_").upper()
    return limpio or "SIN_NOMBRE"


def _desde_json(texto: str | None, por_defecto: object) -> object:
    """Deserializa un campo JSON de la base de datos con tolerancia a fallos."""
    if not texto:
        return por_defecto
    try:
        return json.loads(texto)
    except (TypeError, ValueError):
        return por_defecto


# ----------------------------------------------------------------------
# Infraestructura de plantillas y firmas
# ----------------------------------------------------------------------
def _cargar_libro(clave: str) -> Workbook:
    """Abre la plantilla oficial `clave` (p. ej. 'AT-F3'). Falla con mensaje claro."""
    nombre = PLANTILLAS[clave]
    plantilla = ruta_recurso("templates", nombre)
    if not plantilla.exists():
        raise FileNotFoundError(
            f"Falta la plantilla oficial '{nombre}'. Cópiala en la carpeta: {ruta_recurso('templates')}"
        )
    return load_workbook(plantilla, keep_links=True)


def _colocar(ws: Worksheet, mapa: dict[str, str], clave: str, valor: object) -> None:
    """Escribe `valor` en la celda mapeada `clave` (sin romper si el mapa no la trae)."""
    celda = mapa.get(clave)
    if not celda:
        log.debug("Clave '%s' sin celda en el mapa; se omite.", clave)
        return
    ws[celda] = valor if valor is not None else ""


def _numero_fila(coordenada: str) -> int:
    """Devuelve la fila numérica de una coordenada tipo 'B17' → 17."""
    coincidencia = re.match(r"[A-Za-z]+(\d+)", coordenada)
    if not coincidencia:
        raise ValueError(f"Coordenada inválida: {coordenada}")
    return int(coincidencia.group(1))


def _firma_activa(rol: str) -> Path | None:
    """Ruta del PNG de la firma ACTIVA de un rol, verificando su hash SHA-256.

    Si el archivo falta o fue alterado (hash distinto al registrado) se omite
    la firma y se deja evidencia en el log — el documento se genera igual.
    """
    fila = db.firma_activa(rol)
    if fila is None:
        return None
    ruta = Path(fila["archivo"])
    if not ruta.exists():
        log.warning("Firma activa de rol '%s' no existe en disco: %s", rol, ruta)
        return None
    import hashlib

    if hashlib.sha256(ruta.read_bytes()).hexdigest() != fila["sha256"]:
        log.warning("Firma de rol '%s' modificada (hash SHA-256 distinto); se omite.", rol)
        return None
    return ruta


def _insertar_firma(ws: Worksheet, celda: str, ruta_png: Path) -> None:
    """Inserta la imagen de la firma anclada en `celda`, escalada a ~160×60 px."""
    from openpyxl.drawing.image import Image as ImagenExcel

    imagen = ImagenExcel(str(ruta_png))
    ancho, alto = int(imagen.width or 400), int(imagen.height or 150)
    escala = min(160 / max(ancho, 1), 60 / max(alto, 1), 1.0)
    imagen.width = max(int(ancho * escala), 10)
    imagen.height = max(int(alto * escala), 5)
    ws.add_image(imagen, celda)


def _aplicar_firma(ws: Worksheet, celda: str, roles: tuple[str, ...], detalle: str) -> bool:
    """Estampa la primera firma activa disponible entre `roles` y audita el uso."""
    for rol in roles:
        fila = db.firma_activa(rol)
        if fila is None:
            continue
        ruta = _firma_activa(rol)
        if ruta is None:
            continue
        try:
            _insertar_firma(ws, celda, ruta)
        except Exception:  # pragma: no cover - imagen corrupta no debe frenar el formato
            log.exception("No se pudo insertar la firma de rol '%s'", rol)
            return False
        db.registrar_uso_firma(int(fila["id"]), detalle)
        log.info("Firma estampada (%s) en %s · %s", rol, celda, detalle)
        return True
    log.info("Sin firma activa para roles %s; el formato se genera sin firma.", roles)
    return False


# ----------------------------------------------------------------------
# Generador AT-F3 — Informe técnico mensual del deportista
# ----------------------------------------------------------------------
def generar_at_f3(registro_id: int) -> str:
    """Genera el Excel AT-F3 de un registro mensual. Devuelve la ruta generada."""
    registro = db.obtener_registro(registro_id)
    if registro is None:
        raise ValueError(f"No existe el registro mensual con id={registro_id}.")

    ws = _cargar_libro("AT-F3").active
    m = MAPA_AT_F3
    periodo = registro["periodo"]
    anio, mes_num = periodo.split("-")

    _colocar(ws, m, "nombre", registro["nombre"])
    _colocar(ws, m, "deporte", registro["deporte"])
    _colocar(ws, m, "mes", f"{MESES.get(mes_num, mes_num)} {anio}")
    _colocar(ws, m, "anio", anio)
    _colocar(ws, m, "region", registro["region_dep"] or "")
    _colocar(ws, m, "entrenador", registro["entrenador"] or registro["entrenador_dep"] or "")
    _colocar(ws, m, "objetivos", registro["objetivos"] or "")

    horario = _desde_json(registro["horario_json"], [])
    _colocar(ws, m, "horario", "\n".join(str(linea) for linea in horario))

    if registro["pct_asistencia"] is not None:
        ws[m["pct_asist"]] = float(registro["pct_asistencia"])
        ws[m["pct_asist"]].number_format = FORMATO_PORCENTAJE
    if registro["pct_cumplimiento"] is not None:
        ws[m["pct_cump"]] = float(registro["pct_cumplimiento"])
        ws[m["pct_cump"]].number_format = FORMATO_PORCENTAJE

    _colocar(ws, m, "resultados", registro["resultados"] or "")

    pruebas = _desde_json(registro["pruebas_sisdena_json"], [])
    lineas = [
        f"• {p.get('fecha', '')} · {p.get('competencia', '')} · {p.get('prueba', '')} · "
        f"{p.get('resultado', '')} · puesto {p.get('puesto', '')}".strip(" ·")
        for p in pruebas
    ]
    _colocar(ws, m, "sisdena", "\n".join(lineas) if lineas else "Sin participaciones SISDENA registradas.")

    _colocar(ws, m, "evaluacion", registro["evaluacion"] or "")
    _aplicar_firma(ws, m["firma"], ("entrenador", "jut"), f"AT-F3 · {registro['nombre']} · {periodo}")

    GENERADOS_DIR.mkdir(parents=True, exist_ok=True)
    destino = GENERADOS_DIR / f"AT-F3_{_nombre_seguro(registro['nombre'])}_{periodo}.xlsx"
    ws.parent.save(destino)
    log.info("AT-F3 generado: %s", destino)
    return str(destino)


# ----------------------------------------------------------------------
# Generador AT-F1 — Consolidado mensual del CAR
# ----------------------------------------------------------------------
def generar_at_f1(consolidado_id: int) -> str:
    """Genera el Excel AT-F1 (consolidado CAR) con agregación automática."""
    consolidado = db.obtener_consolidado(consolidado_id)
    if consolidado is None:
        raise ValueError(f"No existe el consolidado AT-F1 con id={consolidado_id}.")

    ws = _cargar_libro("AT-F1").active
    m = MAPA_AT_F1
    periodo = consolidado["periodo"]
    anio, mes_num = periodo.split("-")

    _colocar(ws, m, "car", consolidado["car"])
    _colocar(ws, m, "mes", f"{MESES.get(mes_num, mes_num)} {anio}")
    _colocar(ws, m, "anio", anio)
    _colocar(ws, m, "jut_nombre", consolidado["jut_nombre"] or "")

    matriculas: dict = _desde_json(consolidado["matriculas_json"], {"altas": {}, "bajas": {}})
    altas = matriculas.get("altas", {}) if isinstance(matriculas, dict) else {}
    bajas = matriculas.get("bajas", {}) if isinstance(matriculas, dict) else {}
    for categoria in CATEGORIAS:
        n_altas = int(altas.get(categoria, 0) or 0)
        n_bajas = int(bajas.get(categoria, 0) or 0)
        _colocar(ws, m, f"altas_{categoria}", n_altas)
        _colocar(ws, m, f"bajas_{categoria}", n_bajas)
        _colocar(ws, m, f"saldo_{categoria}", n_altas - n_bajas)

    # Tabla de % por deportista — agregación automática de AT-F3
    registros = db.registros_para_consolidado(consolidado["car"], periodo)
    fila = _numero_fila(m["tabla_pct_inicio"])
    if registros:
        for registro in registros:
            ws.cell(row=fila, column=2, value=registro["nombre"])
            ws.cell(row=fila, column=3, value=registro["categoria"])
            celda_asist = ws.cell(row=fila, column=4, value=registro["pct_asistencia"])
            celda_asist.number_format = FORMATO_PORCENTAJE
            celda_cump = ws.cell(row=fila, column=5, value=registro["pct_cumplimiento"])
            celda_cump.number_format = FORMATO_PORCENTAJE
            fila += 1
    else:
        ws.cell(row=fila, column=2,
                value="Sin registros AT-F3 del periodo para este CAR.")

    _colocar(ws, m, "eval_medica", consolidado["eval_medica"] or "")
    _colocar(ws, m, "eval_nutricion", consolidado["eval_nutricion"] or "")
    _colocar(ws, m, "eval_car", consolidado["eval_car"] or "")
    _colocar(ws, m, "observaciones", consolidado["observaciones"] or "")

    _aplicar_firma(ws, m["firma_jut"], ("jut", "dinadaf"), f"AT-F1 · {consolidado['car']} · {periodo}")
    _aplicar_firma(ws, m["firma_entrenador"], ("entrenador",), f"AT-F1 · {consolidado['car']} · {periodo}")

    GENERADOS_DIR.mkdir(parents=True, exist_ok=True)
    destino = GENERADOS_DIR / f"AT-F1_{_nombre_seguro(consolidado['car'])}_{periodo}.xlsx"
    ws.parent.save(destino)
    log.info("AT-F1 generado: %s", destino)
    return str(destino)


# ----------------------------------------------------------------------
# Generador AT-F8 — Plan mensual de trabajo del JUT
# ----------------------------------------------------------------------
def generar_at_f8(plan_id: int) -> str:
    """Genera el Excel AT-F8 (plan del JUT) con su tabla de tareas."""
    plan = db.obtener_plan(plan_id)
    if plan is None:
        raise ValueError(f"No existe el plan AT-F8 con id={plan_id}.")

    ws = _cargar_libro("AT-F8").active
    m = MAPA_AT_F8
    periodo = plan["periodo"]
    anio, mes_num = periodo.split("-")

    _colocar(ws, m, "jut_nombre", plan["jut_nombre"])
    _colocar(ws, m, "car", plan["car"] or "")
    _colocar(ws, m, "mes", f"{MESES.get(mes_num, mes_num)} {anio}")
    _colocar(ws, m, "anio", anio)

    tareas = _desde_json(plan["tareas_json"], [])
    fila = _numero_fila(m["tabla_inicio"])
    for tarea in tareas:
        ws.cell(row=fila, column=2, value=tarea.get("n", fila - _numero_fila(m["tabla_inicio"]) + 1))
        ws.cell(row=fila, column=3, value=tarea.get("actividad", ""))
        ws.cell(row=fila, column=4, value=tarea.get("fecha", ""))
        ws.cell(row=fila, column=5, value=tarea.get("hora", ""))
        ws.cell(row=fila, column=6, value=tarea.get("lugar", ""))
        ws.cell(row=fila, column=7, value=tarea.get("obs", ""))
        fila += 1
    if not tareas:
        ws.cell(row=fila, column=3, value="Sin tareas registradas en el plan.")

    _aplicar_firma(ws, m["firma"], ("jut",), f"AT-F8 · {plan['jut_nombre']} · {periodo}")

    GENERADOS_DIR.mkdir(parents=True, exist_ok=True)
    destino = GENERADOS_DIR / f"AT-F8_{_nombre_seguro(plan['jut_nombre'])}_{periodo}.xlsx"
    ws.parent.save(destino)
    log.info("AT-F8 generado: %s", destino)
    return str(destino)


# ----------------------------------------------------------------------
# Generador AT-F9 — Evaluación del plan (mes anterior)
# ----------------------------------------------------------------------
def generar_at_f9(evaluacion_id: int) -> str:
    """Genera el Excel AT-F9 (evaluación del plan AT-F8 del mes anterior)."""
    evaluacion = db.obtener_evaluacion(evaluacion_id)
    if evaluacion is None:
        raise ValueError(f"No existe la evaluación AT-F9 con id={evaluacion_id}.")
    plan = db.obtener_plan(int(evaluacion["plan_id"]))
    if plan is None:
        raise ValueError(f"El plan AT-F8 (id={evaluacion['plan_id']}) ya no existe.")

    ws = _cargar_libro("AT-F9").active
    m = MAPA_AT_F9
    periodo_evaluado = evaluacion["periodo_evaluado"]
    anio, mes_num = periodo_evaluado.split("-")

    _colocar(ws, m, "jut_nombre", plan["jut_nombre"])
    _colocar(ws, m, "car", plan["car"] or "")
    _colocar(ws, m, "mes_evaluado", f"{MESES.get(mes_num, mes_num)} {anio}")
    _colocar(ws, m, "anio", anio)
    _colocar(ws, m, "periodo_plan", f"AT-F8 · {plan['periodo']}")

    if evaluacion["pct_asistencia_prom"] is not None:
        ws[m["pct_asist_prom"]] = float(evaluacion["pct_asistencia_prom"])
        ws[m["pct_asist_prom"]].number_format = FORMATO_PORCENTAJE
    if evaluacion["pct_cumplimiento_prom"] is not None:
        ws[m["pct_cump_prom"]] = float(evaluacion["pct_cumplimiento_prom"])
        ws[m["pct_cump_prom"]].number_format = FORMATO_PORCENTAJE
    _colocar(ws, m, "tareas_programadas", evaluacion["tareas_programadas"])
    _colocar(ws, m, "tareas_cumplidas", evaluacion["tareas_cumplidas"])
    if evaluacion["pct_tareas"] is not None:
        ws[m["pct_tareas"]] = float(evaluacion["pct_tareas"])
        ws[m["pct_tareas"]].number_format = FORMATO_PORCENTAJE

    _colocar(ws, m, "fecha_visita", evaluacion["fecha_visita"] or "")
    _colocar(ws, m, "realizado_por", evaluacion["realizado_por"] or "")
    _colocar(ws, m, "obs_visita", evaluacion["obs_visita"] or "")
    _colocar(ws, m, "calificacion_final", evaluacion["calificacion_final"])
    _colocar(ws, m, "opinion_presidente", evaluacion["opinion_presidente"] or "")

    _aplicar_firma(ws, m["firma_jut"], ("jut",), f"AT-F9 · {plan['jut_nombre']} · {periodo_evaluado}")
    if (evaluacion["opinion_presidente"] or "").strip():
        _aplicar_firma(ws, m["firma_presidente"], ("presidente_fdn",),
                       f"AT-F9 · Opinión presidida · {periodo_evaluado}")

    GENERADOS_DIR.mkdir(parents=True, exist_ok=True)
    destino = GENERADOS_DIR / f"AT-F9_{_nombre_seguro(plan['jut_nombre'])}_{periodo_evaluado}.xlsx"
    ws.parent.save(destino)
    log.info("AT-F9 generado: %s", destino)
    return str(destino)


# ======================================================================
# v3.0 — Estilos para los libros generados sin plantilla IPD
# ======================================================================
def _estilos():
    """Devuelve los estilos base (fill, fuentes, bordes) del tema institucional."""
    relleno_titulo = PatternFill("solid", fgColor="0F172A")
    relleno_cabecera = PatternFill("solid", fgColor="6366F1")
    relleno_seccion = PatternFill("solid", fgColor="EEF2FF")
    fuente_titulo = Font(color="FFFFFF", bold=True, size=14)
    fuente_cabecera = Font(color="FFFFFF", bold=True, size=10)
    fuente_seccion = Font(color="0F172A", bold=True, size=10)
    borde_fino = Border(*[Side(style="thin", color="D8DEE9")] * 4)
    alineacion = Alignment(vertical="center", wrap_text=True)
    return {
        "relleno_titulo": relleno_titulo, "relleno_cabecera": relleno_cabecera,
        "relleno_seccion": relleno_seccion, "fuente_titulo": fuente_titulo,
        "fuente_cabecera": fuente_cabecera, "fuente_seccion": fuente_seccion,
        "borde": borde_fino, "alineacion": alineacion,
    }


def _fila_cabecera(ws: Worksheet, fila: int, textos: list[str], estilos: dict) -> None:
    """Escribe una fila de cabecera con el estilo del sistema."""
    for columna, texto in enumerate(textos, start=1):
        celda = ws.cell(row=fila, column=columna, value=texto)
        celda.fill = estilos["relleno_cabecera"]
        celda.font = estilos["fuente_cabecera"]
        celda.border = estilos["borde"]
        celda.alignment = estilos["alineacion"]


def _titulo_hoja(ws: Worksheet, texto: str, ancho: int, estilos: dict, fila: int = 1) -> None:
    """Banda de título oscura en la primera fila de la hoja."""
    ws.cell(row=fila, column=1, value=texto)
    ws.merge_cells(start_row=fila, start_column=1, end_row=fila, end_column=ancho)
    celda = ws.cell(row=fila, column=1)
    celda.fill = estilos["relleno_titulo"]
    celda.font = estilos["fuente_titulo"]
    celda.alignment = Alignment(vertical="center", horizontal="left", indent=1)
    ws.row_dimensions[fila].height = 30


def _ajustar_columnas(ws: Worksheet, anchos: list[int]) -> None:
    from openpyxl.utils import get_column_letter

    for indice, ancho in enumerate(anchos, start=1):
        ws.column_dimensions[get_column_letter(indice)].width = ancho


def _seccion(ws: Worksheet, fila: int, texto: str, ancho: int, estilos: dict) -> None:
    ws.cell(row=fila, column=1, value=texto)
    ws.merge_cells(start_row=fila, start_column=1, end_row=fila, end_column=ancho)
    celda = ws.cell(row=fila, column=1)
    celda.fill = estilos["relleno_seccion"]
    celda.font = estilos["fuente_seccion"]
    celda.alignment = Alignment(vertical="center", horizontal="left", indent=1)


# ----------------------------------------------------------------------
# v3.0 — Ficha de alimentación (AT-NUT)
# ----------------------------------------------------------------------
def generar_alimentacion(registro_id: int) -> str:
    """Genera el Excel de la evaluación nutricional mensual. Devuelve la ruta."""
    registro = db.obtener_alimentacion(registro_id)
    if registro is None:
        raise ValueError(f"No existe la evaluación nutricional con id={registro_id}.")
    est = _estilos()
    libro = Workbook()
    ws = libro.active
    ws.title = "AT-NUT"

    _titulo_hoja(ws, "FORMATO DE ALIMENTACIÓN · IPD - DINADAF", 4, est)
    _ajustar_columnas(ws, [26, 30, 22, 42])

    fila = 3
    _seccion(ws, fila, "DATOS DEL DEPORTISTA", 4, est)
    fila += 1
    datos = [
        ("Apellidos y nombres", registro["nombre"], "Categoría", registro["categoria"]),
        ("Deporte", registro["deporte"], "Sexo", {"D": "Damas", "V": "Varones"}.get(registro["sexo"], "")),
        ("CAR", registro["car"], "Periodo", registro["periodo"]),
    ]
    for izq_i, izq_v, der_i, der_v in datos:
        ws.cell(row=fila, column=1, value=izq_i).font = Font(bold=True)
        ws.cell(row=fila, column=2, value=izq_v)
        ws.cell(row=fila, column=3, value=der_i).font = Font(bold=True)
        ws.cell(row=fila, column=4, value=der_v)
        fila += 1

    fila += 1
    _seccion(ws, fila, "EVALUACIÓN ANTROPOMÉTRICA Y NUTRICIONAL", 4, est)
    fila += 1
    _fila_cabecera(ws, fila, ["Indicador", "Valor", "Nutricionista", "Fecha de evaluación"], est)
    fila += 1
    metricas = [
        ("Peso (kg)", registro["peso_kg"], "0.0"),
        ("Estatura (m)", registro["estatura_m"], "0.00"),
        ("IMC", registro["imc"], "0.0"),
        ("% grasa corporal", registro["pct_grasa_corporal"], "0.0"),
        ("Consumo objetivo (kcal/día)", registro["kcal_dia"], "#,##0"),
    ]
    for nombre, valor, formato in metricas:
        ws.cell(row=fila, column=1, value=nombre)
        celda = ws.cell(row=fila, column=2, value=valor)
        celda.number_format = formato
        ws.cell(row=fila, column=3, value=registro["nutricionista"])
        ws.cell(row=fila, column=4, value=registro["fecha_evaluacion"])
        fila += 1
    ws.cell(row=fila, column=1, value="Objetivo nutricional").font = Font(bold=True)
    ws.cell(row=fila, column=2, value=str(registro["objetivo"]).replace("_", " "))
    fila += 2

    _seccion(ws, fila, "PLAN ALIMENTICIO DEL PERIODO", 4, est)
    fila += 1
    ws.merge_cells(start_row=fila, start_column=1, end_row=fila + 6, end_column=4)
    celda_plan = ws.cell(row=fila, column=1, value=registro["plan_alimenticio"] or "Sin plan registrado.")
    celda_plan.alignment = Alignment(vertical="top", wrap_text=True)
    fila += 8
    _seccion(ws, fila, "OBSERVACIONES", 4, est)
    fila += 1
    ws.merge_cells(start_row=fila, start_column=1, end_row=fila + 2, end_column=4)
    celda_obs = ws.cell(row=fila, column=1, value=registro["observaciones"] or "—")
    celda_obs.alignment = Alignment(vertical="top", wrap_text=True)

    GENERADOS_DIR.mkdir(parents=True, exist_ok=True)
    destino = GENERADOS_DIR / f"AT-NUT_{_nombre_seguro(registro['nombre'])}_{registro['periodo']}.xlsx"
    libro.save(destino)
    log.info("Ficha de alimentación generada: %s", destino)
    return str(destino)


# ----------------------------------------------------------------------
# v3.0 — Listado de seguros deportivos
# ----------------------------------------------------------------------
def generar_listado_seguros() -> str:
    """Genera el Excel consolidado de pólizas de seguro deportivo."""
    est = _estilos()
    libro = Workbook()
    ws = libro.active
    ws.title = "Seguros"

    _titulo_hoja(ws, "REGISTRO DE SEGUROS DEPORTIVOS · IPD - DINADAF", 9, est)
    _ajustar_columnas(ws, [30, 12, 20, 18, 16, 26, 13, 14, 12])

    _fila_cabecera(ws, 3, [
        "Deportista", "Categoría", "Deporte", "Aseguradora", "Tipo",
        "N.° de póliza", "Vigencia", "Estado", "Cobertura",
    ], est)
    fila = 4
    for seguro in db.listar_seguros():
        vigencia = f"{seguro['vigencia_inicio'] or '—'} → {seguro['vigencia_fin'] or '—'}"
        valores = [
            seguro["nombre"], seguro["categoria"], seguro["deporte"],
            seguro["aseguradora"], str(seguro["tipo_seguro"]).replace("_", " "),
            seguro["numero_poliza"], vigencia, seguro["estado"],
            seguro["cobertura"] or "—",
        ]
        for columna, valor in enumerate(valores, start=1):
            celda = ws.cell(row=fila, column=columna, value=valor)
            celda.border = est["borde"]
            celda.alignment = est["alineacion"]
        if seguro["estado"] == "VENCIDO":
            ws.cell(row=fila, column=8).font = Font(bold=True, color="DC2626")
        elif seguro["estado"] == "VIGENTE":
            ws.cell(row=fila, column=8).font = Font(bold=True, color="059669")
        fila += 1
    if fila == 4:
        ws.cell(row=4, column=1, value="Sin pólizas registradas.")
    ws.freeze_panes = "A4"

    GENERADOS_DIR.mkdir(parents=True, exist_ok=True)
    destino = GENERADOS_DIR / "SEGUROS_listado.xlsx"
    libro.save(destino)
    log.info("Listado de seguros generado: %s", destino)
    return str(destino)


# ----------------------------------------------------------------------
# v3.0 — Expediente completo del atleta
# ----------------------------------------------------------------------
def generar_expediente(deportista_id: int) -> str:
    """Genera el Excel del expediente completo del deportista (4 hojas)."""
    deportista = db.obtener_deportista(deportista_id)
    if deportista is None:
        raise ValueError(f"No existe el deportista con id={deportista_id}.")
    est = _estilos()
    libro = Workbook()

    # --- Hoja 1: datos personales y mejores resultados -----------------
    ws = libro.active
    ws.title = "Expediente"
    _titulo_hoja(ws, f"EXPEDIENTE DEL ATLETA · {deportista['nombre']}", 6, est)
    _ajustar_columnas(ws, [24, 26, 24, 26, 18, 18])
    fila = 3
    _seccion(ws, fila, "DATOS PERSONALES Y DEPORTIVOS", 6, est)
    fila += 1
    datos = [
        ("Apellidos y nombres", deportista["nombre"], "Documento", deportista["documento"] or "—"),
        ("Deporte", deportista["deporte"], "Categoría que compite", deportista["categoria"]),
        ("Sexo", {"D": "Damas", "V": "Varones"}.get(deportista["sexo"], ""), "CAR", deportista["car"] or "—"),
        ("Región", deportista["region"] or "—", "Entrenador", deportista["entrenador"] or "—"),
        ("Estado", "Activo" if deportista["activo"] else "Inactivo", "Registrado el", deportista["creado_en"]),
    ]
    for izq_i, izq_v, der_i, der_v in datos:
        ws.cell(row=fila, column=1, value=izq_i).font = Font(bold=True)
        ws.cell(row=fila, column=2, value=izq_v)
        ws.cell(row=fila, column=3, value=der_i).font = Font(bold=True)
        ws.cell(row=fila, column=4, value=der_v)
        fila += 1

    mejores = db.resumen_mejores_por_periodo(deportista_id)
    titulos = {
        "mes": ("MEJORES RESULTADOS POR MES", "Mes"),
        "bimestre": ("MEJORES RESULTADOS POR BIMESTRE", "Bimestre"),
        "trimestre": ("MEJORES RESULTADOS POR TRIMESTRE", "Trimestre"),
        "anual": ("MEJORES RESULTADOS POR AÑO", "Año"),
    }
    for tipo, (seccion_texto, etiqueta_col) in titulos.items():
        fila += 1
        _seccion(ws, fila, seccion_texto, 6, est)
        fila += 1
        _fila_cabecera(ws, fila, [etiqueta_col, "Competencia", "Prueba", "Marca", "Puesto", "Medalla"], est)
        fila += 1
        bloque = mejores.get(tipo, {})
        if not bloque:
            ws.cell(row=fila, column=1, value="Sin resultados registrados aún.")
            fila += 1
        for etiqueta, mejor in sorted(bloque.items()):
            puesto = f"{mejor['posicion']}.°" if mejor["posicion"] else "—"
            valores = [etiqueta, mejor["competencia"], mejor["prueba"] or "—",
                       mejor["marca"] or "—", puesto, mejor["medalla"] or "—"]
            for columna, valor in enumerate(valores, start=1):
                celda = ws.cell(row=fila, column=columna, value=valor)
                celda.border = est["borde"]
                celda.alignment = est["alineacion"]
            fila += 1

    # --- Hoja 2: historial completo de resultados ----------------------
    ws2 = libro.create_sheet("Resultados")
    _titulo_hoja(ws2, "HISTORIAL COMPLETO DE RESULTADOS", 8, est)
    _ajustar_columnas(ws2, [12, 32, 20, 20, 14, 10, 10, 30])
    _fila_cabecera(ws2, 3, ["Fecha", "Competencia", "Lugar", "Prueba", "Marca",
                            "Puesto", "Medalla", "Observaciones"], est)
    fila = 4
    historial = db.resultados_de(deportista_id)
    for resultado in historial:
        valores = [resultado["fecha"], resultado["competencia"], resultado["lugar"] or "—",
                   resultado["prueba"] or "—", resultado["marca"] or "—",
                   resultado["posicion"] or "—", resultado["medalla"] or "—",
                   resultado["observaciones"] or ""]
        for columna, valor in enumerate(valores, start=1):
            celda = ws2.cell(row=fila, column=columna, value=valor)
            celda.border = est["borde"]
            celda.alignment = est["alineacion"]
        fila += 1
    if not historial:
        ws2.cell(row=4, column=1, value="Sin resultados registrados.")
    ws2.freeze_panes = "A4"

    # --- Hoja 3: alimentación ------------------------------------------
    ws3 = libro.create_sheet("Alimentación")
    _titulo_hoja(ws3, "HISTORIAL DE EVALUACIONES NUTRICIONALES", 8, est)
    _ajustar_columnas(ws3, [10, 12, 10, 8, 8, 10, 10, 30])
    _fila_cabecera(ws3, 3, ["Periodo", "Fecha eval.", "Peso (kg)", "Estatura (m)",
                            "IMC", "% grasa", "kcal/día", "Objetivo"], est)
    fila = 4
    for evaluacion in db.listar_alimentacion():
        valores = [evaluacion["periodo"], evaluacion["fecha_evaluacion"] or "—",
                   evaluacion["peso_kg"] or "—", evaluacion["estatura_m"] or "—",
                   evaluacion["imc"] or "—", evaluacion["pct_grasa_corporal"] or "—",
                   evaluacion["kcal_dia"] or "—",
                   str(evaluacion["objetivo"]).replace("_", " ")]
        for columna, valor in enumerate(valores, start=1):
            celda = ws3.cell(row=fila, column=columna, value=valor)
            celda.border = est["borde"]
            celda.alignment = est["alineacion"]
        fila += 1
    ws3.freeze_panes = "A4"

    # --- Hoja 4: seguros ------------------------------------------------
    ws4 = libro.create_sheet("Seguros")
    _titulo_hoja(ws4, "PÓLIZAS DE SEGURO DEL DEPORTISTA", 6, est)
    _ajustar_columnas(ws4, [20, 22, 16, 22, 14, 14])
    _fila_cabecera(ws4, 3, ["Aseguradora", "Tipo", "N.° póliza", "Cobertura",
                            "Vigencia", "Estado"], est)
    fila = 4
    for seguro in db.listar_seguros():
        if int(seguro["deportista_id"]) != int(deportista_id):
            continue
        valores = [seguro["aseguradora"], str(seguro["tipo_seguro"]).replace("_", " "),
                   seguro["numero_poliza"] or "—", seguro["cobertura"] or "—",
                   f"{seguro['vigencia_inicio'] or '—'} → {seguro['vigencia_fin'] or '—'}",
                   seguro["estado"]]
        for columna, valor in enumerate(valores, start=1):
            celda = ws4.cell(row=fila, column=columna, value=valor)
            celda.border = est["borde"]
            celda.alignment = est["alineacion"]
        fila += 1
    ws4.freeze_panes = "A4"

    GENERADOS_DIR.mkdir(parents=True, exist_ok=True)
    destino = GENERADOS_DIR / f"EXPEDIENTE_{_nombre_seguro(deportista['nombre'])}.xlsx"
    libro.save(destino)
    log.info("Expediente generado: %s", destino)
    return str(destino)


# ----------------------------------------------------------------------
# v3.0 — Cuadros estadísticos del análisis deportivo
# ----------------------------------------------------------------------
def generar_analisis(periodo: str = "", anio: str = "") -> str:
    """Genera el Excel multi-hoja del análisis deportivo (cuadros estadísticos)."""
    est = _estilos()
    libro = Workbook()

    # --- Hoja 1: resumen -------------------------------------------------
    ws = libro.active
    ws.title = "Resumen"
    _titulo_hoja(ws, "ANÁLISIS DEPORTIVO · IPD - DINADAF", 5, est)
    _ajustar_columnas(ws, [34, 14, 14, 14, 14])
    fila = 3
    _seccion(ws, fila, "INDICADORES GENERALES", 5, est)
    fila += 1
    conteo_seguros = db.resumen_seguros()
    indicadores = [
        ("Deportistas activos", db.contar_deportistas(True), None),
        ("Deportistas inactivos", db.contar_deportistas(False), None),
        ("Informes AT-F3 registrados", db.contar_registros(periodo) if periodo else "", None),
        ("Planes AT-F8 registrados", db.contar_planes(), None),
        ("Evaluaciones AT-F9", db.contar_evaluaciones(), None),
        ("Pólizas de seguro vigentes", conteo_seguros.get("VIGENTE", 0), None),
        ("Pólizas vencidas (requieren acción)", conteo_seguros.get("VENCIDO", 0), None),
    ]
    for nombre, valor, _f in indicadores:
        ws.cell(row=fila, column=1, value=nombre).border = est["borde"]
        celda = ws.cell(row=fila, column=2, value=valor if valor != "" else "Todos los periodos")
        celda.border = est["borde"]
        fila += 1

    fila += 1
    _seccion(ws, fila, "DISTRIBUCIÓN POR SEXO", 5, est)
    fila += 1
    for distribucion_fila in db.distribucion("sexo"):
        ws.cell(row=fila, column=1, value={"D": "Damas", "V": "Varones"}.get(distribucion_fila["clave"], distribucion_fila["clave"]))
        ws.cell(row=fila, column=2, value=int(distribucion_fila["n"])).border = est["borde"]
        fila += 1

    # --- Hoja 2: matrícula -----------------------------------------------
    ws2 = libro.create_sheet("Matrícula")
    _titulo_hoja(ws2, "MATRÍCULA POR CATEGORÍA Y SEXO", 5, est)
    _ajustar_columnas(ws2, [16, 12, 12, 12, 16])
    _fila_cabecera(ws2, 3, ["Categoría", "Damas", "Varones", "Total", "% del total"], est)
    fila = 4
    matriculas = db.matricula_por_categoria_sexo()
    total_general = sum(int(m["total"]) for m in matriculas) or 1
    for m in matriculas:
        valores = [m["categoria"], int(m["damas"]), int(m["varones"]), int(m["total"])]
        for columna, valor in enumerate(valores, start=1):
            celda = ws2.cell(row=fila, column=columna, value=valor)
            celda.border = est["borde"]
        celda_pct = ws2.cell(row=fila, column=5, value=int(m["total"]) / total_general)
        celda_pct.number_format = FORMATO_PORCENTAJE
        celda_pct.border = est["borde"]
        fila += 1
    ws2.cell(row=fila, column=1, value="TOTAL").font = Font(bold=True)
    ws2.cell(row=fila, column=4, value=total_general).font = Font(bold=True)

    # --- Hoja 3: rendimiento mensual -------------------------------------
    ws3 = libro.create_sheet("Rendimiento")
    _titulo_hoja(ws3, "ASISTENCIA Y CUMPLIMIENTO PROMEDIO POR PERIODO", 5, est)
    _ajustar_columnas(ws3, [14, 16, 16, 14, 30])
    _fila_cabecera(ws3, 3, ["Periodo", "% Asistencia", "% Cumplimiento", "Informes", "Periodo legible"], est)
    fila = 4
    for promedio in db.promedios_por_periodo(12):
        anio_p, mes_p = promedio["periodo"].split("-")
        valores = [
            promedio["periodo"],
            promedio["asistencia"], promedio["cumplimiento"], int(promedio["registros"]),
            f"{MESES.get(mes_p, mes_p)} {anio_p}",
        ]
        for columna, valor in enumerate(valores, start=1):
            celda = ws3.cell(row=fila, column=columna, value=valor)
            celda.border = est["borde"]
            if columna in (2, 3):
                celda.number_format = FORMATO_PORCENTAJE
        fila += 1
    ws3.freeze_panes = "A4"

    # --- Hoja 4: mejores resultados del año -------------------------------
    ws4 = libro.create_sheet("Top resultados")
    _titulo_hoja(ws4, f"MEJORES RESULTADOS {'AÑO ' + anio if anio else 'TODOS LOS AÑOS'} (puesto 1-3)", 8, est)
    _ajustar_columnas(ws4, [12, 28, 24, 20, 16, 10, 10, 16])
    _fila_cabecera(ws4, 3, ["Fecha", "Deportista", "Competencia", "Prueba", "Marca",
                            "Puesto", "Medalla", "Categoría"], est)
    fila = 4
    desde = f"{anio}-01-01" if anio else ""
    hasta = f"{anio}-12-31" if anio else ""
    candidatos = [r for r in db.resultados_deporte_car(desde, hasta)
                  if r["posicion"] is not None and int(r["posicion"]) <= 3]
    for resultado in candidatos[:60]:
        valores = [resultado["fecha"], resultado["nombre"], resultado["competencia"],
                   resultado["prueba"] or "—", resultado["marca"] or "—",
                   int(resultado["posicion"]), resultado["medalla"] or "—",
                   resultado["categoria"]]
        for columna, valor in enumerate(valores, start=1):
            celda = ws4.cell(row=fila, column=columna, value=valor)
            celda.border = est["borde"]
            celda.alignment = est["alineacion"]
        fila += 1
    if not candidatos:
        ws4.cell(row=4, column=1, value="Sin resultados en podio registrados para el rango.")
    ws4.freeze_panes = "A4"

    # --- Hoja 5: alimentación por categoría -------------------------------
    ws5 = libro.create_sheet("Alimentación")
    _titulo_hoja(ws5, "IMC PROMEDIO POR CATEGORÍA (EVALUACIONES NUTRICIONALES)", 4, est)
    _ajustar_columnas(ws5, [16, 14, 14, 20])
    _fila_cabecera(ws5, 3, ["Categoría", "IMC promedio", "Evaluaciones", "Lectura"], est)
    fila = 4
    for fila_imc in db.imc_promedio_por_categoria():
        imc_prom = float(fila_imc["imc_prom"])
        if imc_prom < 18.5:
            lectura = "Bajo peso — revisar disponibilidad energética"
        elif imc_prom < 25:
            lectura = "Rango saludable"
        elif imc_prom < 30:
            lectura = "Sobrepeso — ajustar plan"
        else:
            lectura = "Obesidad — intervención prioritaria"
        valores = [fila_imc["clave"], round(imc_prom, 1), int(fila_imc["n"]), lectura]
        for columna, valor in enumerate(valores, start=1):
            celda = ws5.cell(row=fila, column=columna, value=valor)
            celda.border = est["borde"]
        fila += 1
    if fila == 4:
        ws5.cell(row=4, column=1, value="Sin evaluaciones nutricionales registradas.")

    GENERADOS_DIR.mkdir(parents=True, exist_ok=True)
    sufijo = f"_{periodo}" if periodo else (f"_{anio}" if anio else "_general")
    destino = GENERADOS_DIR / f"ANALISIS_DEPORTIVO{sufijo}.xlsx"
    libro.save(destino)
    log.info("Análisis deportivo generado: %s", destino)
    return str(destino)
