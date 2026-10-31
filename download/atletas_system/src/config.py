# -*- coding: utf-8 -*-
"""
src/config.py
=============
Configuración global del Sistema AT (DINADAF · Instituto Peruano del Deporte).

Responsabilidad:
    * Detectar si la aplicación corre como .exe congelado (PyInstaller) o en
      modo desarrollo, y resolver en consecuencia las rutas de plantillas,
      base de datos, firmas y documentos generados.
    * Centralizar las constantes de dominio: categorías, roles de firma,
      nombres EXACTOS de las plantillas oficiales, meses, sesiones y días.
    * Crear las carpetas de trabajo al importar el módulo.

Reglas de rutas:
    * Modo desarrollo → todo vive dentro de la carpeta del proyecto
      (./templates, ./data, ./firmas, ./generados).
    * .exe congelado  → las plantillas viajan dentro del bundle
      (sys._MEIPASS/templates) y los datos del usuario persisten en
      %LOCALAPPDATA%\\SistemaAT\\ incluso al reinstalar o desinstalar.
    * Como comodidad documentada: si junto al .exe existe una carpeta
      "templates/", tiene prioridad sobre la del bundle (permite actualizar
      plantillas oficiales sin recompilar).
"""
from __future__ import annotations

import datetime as dt
import os
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# 1. Detección del entorno de ejecución
# ---------------------------------------------------------------------------
CONGELADO: bool = getattr(sys, "frozen", False)

if CONGELADO:
    # Recursos empaquetados por PyInstaller (plantillas, assets)
    _BASE_RECURSOS = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    # Carpeta donde vive el .exe (permite sobrescribir plantillas sin recompilar)
    _DIR_EXE = Path(sys.executable).parent
    # Datos del usuario en %LOCALAPPDATA%\SistemaAT\
    _DIR_USUARIO = (
        Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "SistemaAT"
    )
    DATA_DIR = _DIR_USUARIO / "data"
    FIRMAS_DIR = _DIR_USUARIO / "firmas"
    GENERADOS_DIR = _DIR_USUARIO / "generados"
    _TEMPLATES_EXE = _DIR_EXE / "templates"
    TEMPLATES_DIR: Path = _TEMPLATES_EXE if _TEMPLATES_EXE.exists() else _BASE_RECURSOS / "templates"
else:
    _BASE_RECURSOS = Path(__file__).resolve().parent.parent  # raíz del proyecto
    DATA_DIR = _BASE_RECURSOS / "data"
    FIRMAS_DIR = _BASE_RECURSOS / "firmas"
    GENERADOS_DIR = _BASE_RECURSOS / "generados"
    TEMPLATES_DIR = _BASE_RECURSOS / "templates"

ASSETS_DIR: Path = _BASE_RECURSOS / "assets"
DB_PATH: Path = DATA_DIR / "sistema_at.db"

VERSION = "1.0.0"

# ---------------------------------------------------------------------------
# 2. Creación de carpetas al importar el módulo
# ---------------------------------------------------------------------------
for _carpeta in (TEMPLATES_DIR, DATA_DIR, FIRMAS_DIR, GENERADOS_DIR):
    _carpeta.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# 3. Constantes de dominio
# ---------------------------------------------------------------------------
CATEGORIAS = ("U-18", "U-20", "U-23", "MAY", "JUV")
SEXOS = ("D", "V")  # D = Damas · V = Varones
SESIONES = ("MAÑANA", "TARDE", "NOCHE")
DIAS = ("LUNES", "MARTES", "MIERCOLES", "JUEVES", "VIERNES", "SABADO", "DOMINGO")
CALIFICACIONES = ("BUENO", "REGULAR", "MALO")
TIPOS_DOCUMENTO = ("AT-F1", "AT-F3", "AT-F8", "AT-F9")

ROLES_FIRMA = {
    "entrenador": "Entrenador",
    "jut": "Jefe de Unidad Técnica",
    "dinadaf": "Representante DINADAF",
    "presidente_fdn": "Presidente de la FDN",
}

# Nombres EXACTOS de las plantillas oficiales dentro de templates/
PLANTILLAS = {
    "AT-F1": "PLANTILLA FORMATO AT-F1 CAR.xlsx",
    "AT-F3": "PLANTILLA FORMATO AT-F3.xlsx",
    "AT-F8": "PLANTILLA FORMATO ATF8.xlsx",
    "AT-F9": "PLANTILLA FORMATO AT -F9.xlsx",
}

MESES = {
    1: "ENERO", 2: "FEBRERO", 3: "MARZO", 4: "ABRIL", 5: "MAYO", 6: "JUNIO",
    7: "JULIO", 8: "AGOSTO", 9: "SETIEMBRE", 10: "OCTUBRE", 11: "NOVIEMBRE", 12: "DICIEMBRE",
}

# ---------------------------------------------------------------------------
# 4. Utilidades de dominio
# ---------------------------------------------------------------------------


def nombre_archivo_seguro(texto: str) -> str:
    """Convierte un texto en un nombre de archivo seguro (sin espacios ni símbolos)."""
    limpio = re.sub(r"[^\w\s-]", "", str(texto), flags=re.UNICODE).strip()
    limpio = re.sub(r"[\s]+", "_", limpio)
    return limpio or "documento"


def parse_porcentaje(texto: str | None) -> float | None:
    """Convierte entradas como ``'95'``, ``'95%'``, ``'0.95'`` o ``'95,5'`` a fracción 0.0–1.0.

    Regla documentada: valores ≤ 1 se interpretan como fracción (0.95 = 95 %) y
    valores > 1 como porcentaje (95 → 0.95). Devuelve ``None`` si el texto está
    vacío, no es numérico o el resultado queda fuera del rango 0–100 %.
    """
    if texto is None:
        return None
    t = str(texto).strip().replace("%", "").replace(",", ".")
    if not t:
        return None
    try:
        n = float(t)
    except ValueError:
        return None
    if n > 1:
        n = n / 100.0
    if n < 0 or n > 1:
        return None
    return n


def formatear_pct(valor: float | None) -> str:
    """Formatea una fracción 0.0–1.0 como texto de porcentaje ('95%'). Vacío si es None."""
    if valor is None:
        return ""
    n = float(valor) * 100
    return f"{n:.0f}%" if abs(n - round(n)) < 1e-9 else f"{n:.2f}%"


def periodo_actual() -> str:
    """Período (mes) actual en formato 'YYYY-MM'."""
    return dt.date.today().strftime("%Y-%m")


def periodo_anterior(periodo: str, meses: int = 1) -> str:
    """Devuelve el período 'YYYY-MM' desplazado `meses` hacia atrás."""
    anio, mes = (int(x) for x in periodo.split("-"))
    total = anio * 12 + (mes - 1) - meses
    return f"{total // 12:04d}-{total % 12 + 1:02d}"


def lista_periodos(cantidad: int = 24) -> list[str]:
    """Lista de los últimos `cantidad` períodos 'YYYY-MM' (el actual primero)."""
    p = periodo_actual()
    salida = []
    for i in range(cantidad):
        salida.append(periodo_anterior(p, i))
    return salida


def mes_de_periodo(periodo: str) -> str:
    """'2026-10' → 'OCTUBRE' (nombre tal como lo usa la plantilla oficial)."""
    return MESES[int(periodo.split("-")[1])]


def anio_de_periodo(periodo: str) -> str:
    """'2026-10' → '2026'."""
    return periodo.split("-")[0]
