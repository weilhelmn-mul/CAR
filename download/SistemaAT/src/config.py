"""
=============================================================
 Sistema AT · Instituto Peruano del Deporte (IPD - DINADAF)
 config.py — Configuración global: detección del modo PORTABLE,
 rutas de datos, constantes de dominio y mapas de celdas de
 las plantillas Excel oficiales (AT-F3 / AT-F1 / AT-F8 / AT-F9).
=============================================================
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# ----------------------------------------------------------------------
# Identidad de la aplicación
# ----------------------------------------------------------------------
APP_NAME: str = "Sistema AT"
APP_VERSION: str = "1.0"
APP_ORG: str = "IPD · DINADAF"

# ----------------------------------------------------------------------
# Utilidades de rutas
# ----------------------------------------------------------------------
def _directorio_escribible(ruta: Path) -> bool:
    """Devuelve True si `ruta` puede crearse/escribirse (prueba real de escritura)."""
    try:
        ruta.mkdir(parents=True, exist_ok=True)
        prueba = ruta / ".prueba_escritura"
        prueba.write_text("ok", encoding="utf-8")
        prueba.unlink(missing_ok=True)
        return True
    except OSError:
        return False


def _base_recursos() -> Path:
    """Carpeta de recursos empaquetados (plantillas / assets).

    - Congelado (PyInstaller): carpeta temporal _MEIPASS (onefile) o _internal (onedir).
    - Desarrollo: raíz del proyecto (carpeta padre de src/).
    """
    if getattr(sys, "frozen", False):  # exe compilado
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    return Path(__file__).resolve().parent.parent


def _directorio_datos() -> tuple[Path, bool]:
    """Decide dónde viven los datos según el modo de ejecución.

    1. PORTABLE congelado: exe compilado + archivo marcador ``PORTABLE`` junto
       al ejecutable → los datos viven en ``<carpeta del exe>/Data`` (USB).
    2. PORTABLE con Python incluido: carpeta con marcador ``PORTABLE`` en la
       raíz del proyecto, ejecutada con un Python no congelado (p. ej. el
       intérprete portátil de ``py\\``) → ``<raíz del proyecto>/Data``.
    3. INSTALADO: exe congelado sin marcador → ``%LOCALAPPDATA%\\SistemaAT``.
    4. DESARROLLO: ``<proyecto>/data``.
    """
    raiz = Path(__file__).resolve().parent.parent
    if getattr(sys, "frozen", False):
        carpeta_exe = Path(sys.executable).resolve().parent
        if (carpeta_exe / "PORTABLE").exists():
            datos = carpeta_exe / "Data"
            if _directorio_escribible(datos):
                return datos, True
            # USB/destino sin permisos: cae a LOCALAPPDATA sin perder datos
        base = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local")))
        return base / "SistemaAT", False
    if (raiz / "PORTABLE").exists():
        datos = raiz / "Data"
        if _directorio_escribible(datos):
            return datos, True
    return raiz / "data", False


DATA_DIR: Path
PORTABLE: bool
DATA_DIR, PORTABLE = _directorio_datos()
BASE_RECURSOS: Path = _base_recursos()

FIRMAS_DIR: Path = DATA_DIR / "firmas"
GENERADOS_DIR: Path = DATA_DIR / "generados"
DB_PATH: Path = DATA_DIR / "sistema_at.db"
LOG_PATH: Path = DATA_DIR / "sistema_at.log"


def ruta_recurso(*partes: str) -> Path:
    """Resuelve un recurso empaquetado (p. ej. ``ruta_recurso("templates", "x.xlsx")``)."""
    return BASE_RECURSOS.joinpath(*partes)


# ----------------------------------------------------------------------
# Plantillas oficiales (nombres EXACTOS — no modificar)
# ----------------------------------------------------------------------
PLANTILLAS: dict[str, str] = {
    "AT-F3": "PLANTILLA FORMATO AT-F3.xlsx",
    "AT-F1": "PLANTILLA FORMATO AT-F1 CAR.xlsx",
    "AT-F8": "PLANTILLA FORMATO ATF8.xlsx",
    "AT-F9": "PLANTILLA FORMATO AT -F9.xlsx",
}

# ----------------------------------------------------------------------
# Constantes de dominio
# ----------------------------------------------------------------------
CATEGORIAS: tuple[str, ...] = ("U-18", "U-20", "U-23", "MAY", "JUV")
SEXOS: dict[str, str] = {"D": "Damas", "V": "Varones"}
ROLES_FIRMA: tuple[str, ...] = ("entrenador", "jut", "dinadaf", "presidente_fdn")
ROLES_FIRMA_ETIQUETAS: dict[str, str] = {
    "entrenador": "Entrenador",
    "jut": "JUT (Jefe de Unidad Técnica)",
    "dinadaf": "Representante DINADAF",
    "presidente_fdn": "Presidente FDN",
}
CALIFICACIONES: tuple[str, ...] = ("BUENO", "REGULAR", "MALO")
MESES: dict[str, str] = {
    "01": "Enero", "02": "Febrero", "03": "Marzo", "04": "Abril",
    "05": "Mayo", "06": "Junio", "07": "Julio", "08": "Agosto",
    "09": "Setiembre", "10": "Octubre", "11": "Noviembre", "12": "Diciembre",
}

# ----------------------------------------------------------------------
# Mapas de celdas de las plantillas
# ----------------------------------------------------------------------
# ATENCIÓN: coordenadas calibradas contra las plantillas incluidas en /templates.
# Si el IPD entrega versiones oficiales con otra disposición, ajuste SOLO aquí
# (o el generador escribirá en celdas incorrectas).
MAPA_AT_F3: dict[str, str] = {
    "nombre": "C10", "deporte": "C11", "mes": "C12", "entrenador": "C13",
    "region": "J10", "anio": "J11", "objetivos": "C15", "pct_asist": "C30",
    "pct_cump": "C35", "resultados": "C40", "evaluacion": "C50", "firma": "E55",
    # --- Campos auxiliares documentados (bloques adicionales de la plantilla) ---
    "horario": "C20",   # Horario semanal: celdas combinadas C20:C26 (1 línea por día)
    "sisdena": "C45",   # Participaciones SISDENA: celdas combinadas C45:C49
}

MAPA_AT_F1: dict[str, str] = {
    "car": "C8", "mes": "C9", "anio": "J9", "jut_nombre": "C10",
    # Tabla de matrículas por categoría (filas 14–18: Altas / Bajas / Saldo)
    "altas_U-18": "C14", "bajas_U-18": "D14", "saldo_U-18": "E14",
    "altas_U-20": "C15", "bajas_U-20": "D15", "saldo_U-20": "E15",
    "altas_U-23": "C16", "bajas_U-23": "D16", "saldo_U-23": "E16",
    "altas_MAY": "C17", "bajas_MAY": "D17", "saldo_MAY": "E17",
    "altas_JUV": "C18", "bajas_JUV": "D18", "saldo_JUV": "E18",
    "tabla_pct_inicio": "B22",   # Primera fila libre de la tabla de % por deportista
    "eval_medica": "C35", "eval_nutricion": "C36", "eval_car": "C37",
    "observaciones": "C40",
    "firma_jut": "E58", "firma_entrenador": "H58",
}

MAPA_AT_F8: dict[str, str] = {
    "jut_nombre": "C10", "car": "C11", "mes": "C12", "anio": "J12",
    "tabla_inicio": "B17",   # Tabla de tareas (filas 17–36: N°|Actividad|Fecha|Hora|Lugar|Obs.)
    "firma": "E40",
}

MAPA_AT_F9: dict[str, str] = {
    "jut_nombre": "C10", "car": "C11", "mes_evaluado": "C12", "anio": "J12",
    "periodo_plan": "C15",
    "pct_asist_prom": "C18", "pct_cump_prom": "C19",
    "tareas_programadas": "C20", "tareas_cumplidas": "C21", "pct_tareas": "C22",
    "fecha_visita": "C25", "realizado_por": "C26", "obs_visita": "C27",
    "calificacion_final": "C30",
    "opinion_presidente": "C33",
    "firma_jut": "E38", "firma_presidente": "H38",
}
