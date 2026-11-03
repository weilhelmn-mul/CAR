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
