"""
=============================================================
 Sistema AT · Instituto Peruano del Deporte (IPD - DINADAF)
 services/sisdena.py — Importación manual de competencias
 SISDENA desde Excel/CSV (v1 sin API pública).

 PUNTO DE EXTENSIÓN: cuando el IPD publique una API de SISDENA,
 reemplazar `importar_competencias_desde_excel` por el cliente
 HTTP correspondiente (misma estructura de dict de salida) sin
 tocar vistas ni base de datos.
=============================================================
"""
from __future__ import annotations

import logging
from datetime import date, datetime
from pathlib import Path
from typing import Any

from openpyxl import load_workbook

log = logging.getLogger("sistema_at.sisdena")

# Columnas esperadas en la fila 1 de la hoja (tolerante a mayúsculas/acentos)
COLUMNAS_ESPERADAS: tuple[str, ...] = ("deportista", "competencia", "fecha", "prueba", "resultado", "puesto")


def _normalizar(texto: object) -> str:
    """Minúsculas, sin espacios ni tildes para comparar encabezados."""
    replacements = str(texto or "").strip().lower()
    for a, b in (("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"), ("ú", "u")):
        replacements = replacements.replace(a, b)
    return replacements


def _a_fecha(valor: object) -> str:
    """Normaliza la celda de fecha a texto ISO AAAA-MM-DD (o cadena tal cual)."""
    if isinstance(valor, datetime):
        return valor.date().isoformat()
    if isinstance(valor, date):
        return valor.isoformat()
    texto = str(valor or "").strip()
    if not texto:
        return ""
    for formato in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d/%m/%y"):
        try:
            return datetime.strptime(texto, formato).date().isoformat()
        except ValueError:
            continue
    return texto  # se conserva tal cual si no es parseable


def importar_competencias_desde_excel(xlsx_path: str | Path) -> list[dict[str, Any]]:
    """Lee competencias SISDENA de un Excel y devuelve lista de diccionarios.

    Estructura de salida (una entrada por fila de datos):
        {"deportista": str, "competencia": str, "fecha": "AAAA-MM-DD",
         "prueba": str, "resultado": str, "puesto": str|int}

    Lanza ValueError si faltan columnas obligatorias o el archivo no tiene datos.
    """
    ruta = Path(xlsx_path)
    if not ruta.exists():
        raise FileNotFoundError(f"No existe el archivo de importación: {ruta}")
    libro = load_workbook(ruta, data_only=True, read_only=True)
    hoja = libro.active
    if hoja is None:
        raise ValueError("El archivo no contiene hojas legibles.")

    filas = list(hoja.iter_rows(values_only=True))
    libro.close()
    if not filas:
        raise ValueError("El archivo está vacío (sin encabezados ni datos).")

    encabezados = [_normalizar(c) for c in (filas[0] or ())]
    faltantes = [col for col in COLUMNAS_ESPERADAS if col not in encabezados]
    if faltantes:
        raise ValueError(
            "Columnas faltantes en el archivo SISDENA: "
            + ", ".join(faltantes)
            + f". Encabezados detectados: {', '.join(h or '?' for h in encabezados)}"
        )

    indice = {col: encabezados.index(col) for col in COLUMNAS_ESPERADAS}
    competencias: list[dict[str, Any]] = []
    for fila in filas[1:]:
        if fila is None or all(c in (None, "") for c in fila):
            continue  # fila vacía
        registro = {
            "deportista": str(fila[indice["deportista"]] or "").strip(),
            "competencia": str(fila[indice["competencia"]] or "").strip(),
            "fecha": _a_fecha(fila[indice["fecha"]]),
            "prueba": str(fila[indice["prueba"]] or "").strip(),
            "resultado": str(fila[indice["resultado"]] or "").strip(),
            "puesto": fila[indice["puesto"]] if fila[indice["puesto"]] not in (None, "") else "",
        }
        if not registro["deportista"] and not registro["competencia"]:
            continue  # fila sin contenido útil
        competencias.append(registro)

    if not competencias:
        raise ValueError("El archivo no contiene filas de competencias válidas.")
    log.info("SISDENA: %d competencias importadas desde %s", len(competencias), ruta.name)
    return competencias


def sincronizar_sisdena_api(*args: object, **kwargs: object) -> list[dict[str, Any]]:
    """Reservado para la futura API oficial de SISDENA (no implementado en v1).

    Debe devolver la MISMA estructura de `importar_competencias_desde_excel`.
    """
    raise NotImplementedError(
        "La API pública de SISDENA aún no está disponible; use la importación manual desde Excel."
    )
