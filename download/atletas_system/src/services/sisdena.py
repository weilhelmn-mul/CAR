# -*- coding: utf-8 -*-
"""
src/services/sisdena.py
=======================
Importación del detalle de participación en competencias (sección 7 del AT-F3).

SISDENA (https://sisdena.ipd.gob.pe/) NO expone una API pública en la versión
actual del sistema, por lo que la importación es MANUAL: el usuario descarga
o exporta el listado de competencias a Excel/CSV y la aplicación lo interpreta
reconociendo automáticamente las columnas (con sinónimos habituales).

La estructura queda preparada para sustituir esto por una llamada HTTP cuando
el IPD publique una API: ver `importar_desde_api()` al final del módulo.
"""
from __future__ import annotations

import csv
import datetime as dt
import logging
import unicodedata
from pathlib import Path

from openpyxl import load_workbook

log = logging.getLogger(__name__)

CAMPOS = ("deportista", "competencia", "fecha", "prueba", "resultado", "puesto")

# Sinónimos aceptados para cada columna (normalizados sin tildes ni mayúsculas)
SINONIMOS = {
    "deportista": ("deportista", "atleta", "nombres y apellidos", "nombres", "nombre del deportista"),
    "competencia": ("competencia", "evento", "campeonato", "torneo", "nombre de la competencia"),
    "fecha": ("fecha", "fecha de la competencia", "fecha competencia", "fecha de realizacion"),
    "prueba": ("prueba", "modalidad", "prueba / modalidad", "prueba-modalidad"),
    "resultado": ("resultado", "marca", "tiempo", "registro"),
    "puesto": ("puesto", "posicion", "lugar obtenido", "ubicacion"),
}


def _normalizar(texto) -> str:
    """Minúsculas, sin tildes y con espacios colapsados (para comparar cabeceras)."""
    if texto is None:
        return ""
    t = unicodedata.normalize("NFD", str(texto))
    t = "".join(ch for ch in t if unicodedata.category(ch) != "Mn")
    return " ".join(t.lower().split())


def _a_texto(valor) -> str:
    """Celda → texto legible (fechas en formato AAAA-MM-DD)."""
    if valor is None:
        return ""
    if isinstance(valor, dt.datetime):
        return valor.date().isoformat()
    if isinstance(valor, dt.date):
        return valor.isoformat()
    return str(valor).strip()


def _leer_filas(ruta: Path) -> list[list]:
    """Lee todas las filas del archivo (primera hoja si es Excel; CSV con , o ;)."""
    sufijo = ruta.suffix.lower()
    if sufijo == ".csv":
        for codificacion in ("utf-8-sig", "latin-1"):
            try:
                texto = ruta.read_text(encoding=codificacion)
                break
            except UnicodeDecodeError:
                continue
        else:
            raise ValueError("No se pudo leer el CSV (codificación no reconocida).")
        delimitador = ";" if texto.split("\n", 1)[0].count(";") > texto.split("\n", 1)[0].count(",") else ","
        return [list(fila) for fila in csv.reader(texto.splitlines(), delimiter=delimitador)]

    wb = load_workbook(ruta, data_only=True)
    for hoja in wb.worksheets:
        filas = [
            [celda for celda in fila] for fila in hoja.iter_rows(values_only=True)
        ]
        if any(celda not in (None, "") for fila in filas for celda in fila):
            return filas
    return []


def _detectar_encabezado(filas: list[list]) -> tuple[int, dict[str, int]] | None:
    """Busca la fila de cabeceras con más coincidencias de sinónimos (mínimo 2)."""
    mejor: tuple[int, dict[str, int]] | None = None
    mejores_coincidencias = 0
    for i, fila in enumerate(filas[:50]):          # la cabecera suele estar al inicio
        normalizadas = [_normalizar(c) for c in fila]
        mapa: dict[str, int] = {}
        coincidencias = 0
        for campo, sinonimos in SINONIMOS.items():
            for j, texto in enumerate(normalizadas):
                if texto and texto in sinonimos and campo not in mapa:
                    mapa[campo] = j
                    coincidencias += 1
                    break
        if coincidencias > mejores_coincidencias:
            mejores_coincidencias = coincidencias
            mejor = (i, mapa)
    if mejor is not None and mejores_coincidencias >= 2:
        return mejor
    return None


def importar_competencias_desde_excel(ruta_xlsx: str | Path) -> list[dict]:
    """Lee un Excel/CSV exportado de SISDENA y devuelve una lista de competencias.

    Cada elemento es un diccionario con las claves: deportista, competencia,
    fecha, prueba, resultado, puesto. Lanza ValueError si no reconoce el formato.
    """
    ruta = Path(ruta_xlsx)
    if not ruta.exists():
        raise FileNotFoundError(f"No existe el archivo a importar: {ruta}")
    filas = _leer_filas(ruta)
    deteccion = _detectar_encabezado(filas)
    if deteccion is None:
        raise ValueError(
            "No se reconoció el formato del archivo de SISDENA.\n"
            "Debe incluir columnas como: Deportista, Competencia, Fecha, Prueba, "
            "Resultado y Puesto (los nombres pueden variar ligeramente)."
        )
    fila_cabecera, mapa = deteccion
    registros: list[dict] = []
    for fila in filas[fila_cabecera + 1:]:
        if not any(celda not in (None, "") for celda in fila):
            continue
        registro = {campo: "" for campo in CAMPOS}
        for campo in CAMPOS:
            indice = mapa.get(campo)
            if indice is not None and indice < len(fila):
                registro[campo] = _a_texto(fila[indice])
        if registro["deportista"] or registro["competencia"]:
            registros.append(registro)
    log.info("SISDENA: %d competencia(s) importada(s) desde %s", len(registros), ruta.name)
    return registros


def importar_desde_api() -> list[dict]:
    """Punto de extensión para una futura API pública de SISDENA.

    Cuando el IPD publique el servicio REST, reemplazar este cuerpo por la
    llamada HTTP correspondiente (mismo formato de retorno que la importación
    manual) y enlazar la vista AT-F3 a esta función.
    """
    raise NotImplementedError(
        "SISDENA aún no expone una API pública. Use la importación manual "
        "desde Excel/CSV (exportado del propio portal SISDENA)."
    )
