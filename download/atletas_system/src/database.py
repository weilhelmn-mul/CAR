# -*- coding: utf-8 -*-
"""
src/database.py
===============
Capa de acceso a SQLite del Sistema AT.

Responsabilidad:
    * Entregar conexiones configuradas (filas como diccionario, llaves
      foráneas activas).
    * Crear el esquema completo (8 tablas) con CREATE TABLE IF NOT EXISTS.

El esquema reproduce exactamente el definido en el pliego del sistema:
deportistas, registros_mensuales (AT-F3), consolidados_at_f1 (AT-F1),
planes_jut (AT-F8), evaluaciones_jut (AT-F9), firmas, asignaciones_firma y
auditoria_firmas.
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from typing import Iterator

from src import config

_ESQUEMA = """
CREATE TABLE IF NOT EXISTS deportistas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombres_apellidos TEXT NOT NULL,
    deporte TEXT NOT NULL,
    prueba_modalidad TEXT,
    categoria TEXT NOT NULL CHECK(categoria IN ('U-18','U-20','U-23','MAY','JUV')),
    sexo TEXT NOT NULL CHECK(sexo IN ('D','V')),
    region TEXT,
    entrenador TEXT,
    activo INTEGER DEFAULT 1,
    fecha_ingreso DATE,
    fecha_retiro DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS registros_mensuales (       -- AT-F3
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    deportista_id INTEGER NOT NULL,
    periodo TEXT NOT NULL,               -- formato 'YYYY-MM'
    entrenador TEXT,
    objetivos_metas TEXT,
    horario_json TEXT,                   -- matriz sesión×día en JSON
    pct_asistencia REAL,                 -- 0.0 – 1.0
    pct_cumplimiento REAL,               -- 0.0 – 1.0
    resultados_test TEXT,
    detalle_preparacion TEXT,
    participacion_competencias TEXT,     -- importado de SISDENA
    cumplimiento_objetivos TEXT,
    evaluacion_general TEXT,
    observaciones TEXT,
    estado TEXT DEFAULT 'borrador',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP,
    UNIQUE(deportista_id, periodo),
    FOREIGN KEY (deportista_id) REFERENCES deportistas(id)
);

CREATE TABLE IF NOT EXISTS consolidados_at_f1 (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    car TEXT NOT NULL,
    periodo TEXT NOT NULL,
    matriculas_json TEXT,                -- {categoria: {retiros, ingresos, damas, varones, total, sesiones, horarios}}
    valoracion_tecnica TEXT,
    dificultades TEXT,
    valoracion_medica TEXT,
    plan_profilactico TEXT,
    balance_nutricional TEXT,
    valoracion_car TEXT,
    aspectos_negativos TEXT,
    logros_car TEXT,
    otros_aspectos TEXT,
    estado TEXT DEFAULT 'borrador',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(car, periodo)
);

CREATE TABLE IF NOT EXISTS planes_jut (                -- AT-F8
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    jut_nombre TEXT NOT NULL,
    federacion TEXT,
    periodo TEXT NOT NULL,
    tareas_json TEXT,                    -- lista [{n, actividad, fecha, hora, lugar, observaciones}]
    estado TEXT DEFAULT 'borrador',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(jut_nombre, periodo)
);

CREATE TABLE IF NOT EXISTS evaluaciones_jut (          -- AT-F9
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_id INTEGER,
    jut_nombre TEXT NOT NULL,
    periodo TEXT NOT NULL,
    tareas_planificadas INTEGER,
    tareas_cumplidas INTEGER,
    pct_cumplimiento REAL,
    evaluacion_cumplimiento TEXT,
    resumen_reuniones TEXT,
    resumen_documentacion TEXT,
    cantidad_visitas INTEGER,
    evaluacion_visitas TEXT,
    resumen_dificultades TEXT,
    actualizacion_bd TEXT,
    cumplimiento_calendario TEXT,
    capacitaciones TEXT,
    analisis_poa TEXT,
    otros_datos TEXT,
    opinion_presidente TEXT,
    calificacion_final TEXT CHECK(calificacion_final IN ('BUENO','REGULAR','MALO')),
    -- Campos auxiliares (documentados en RESUMEN_EJECUTIVO.md / INSTALL.md):
    --   * resumen_dificultades_seccion2 → 'dificultades analizadas' de la sección 2
    --     (la tabla original solo contempla el resumen de la sección 4).
    --   * pct_cumplimiento_promedio / pct_asistencia_promedio → % promedio de los
    --     AT-F3 del período, calculado al guardar para que el informe quede
    --     congelado aunque los registros se editen después.
    resumen_dificultades_seccion2 TEXT,
    pct_cumplimiento_promedio REAL,
    pct_asistencia_promedio REAL,
    estado TEXT DEFAULT 'borrador',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (plan_id) REFERENCES planes_jut(id)
);

CREATE TABLE IF NOT EXISTS firmas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    persona_nombre TEXT NOT NULL,
    rol TEXT NOT NULL CHECK(rol IN ('entrenador','jut','dinadaf','presidente_fdn')),
    imagen_path TEXT NOT NULL,
    imagen_hash TEXT,
    activa INTEGER DEFAULT 1,
    vigente_desde DATE,
    vigente_hasta DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS asignaciones_firma (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    firma_id INTEGER NOT NULL,
    tipo_documento TEXT NOT NULL CHECK(tipo_documento IN ('AT-F1','AT-F3','AT-F8','AT-F9')),
    documento_id INTEGER NOT NULL,
    firmado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notas TEXT,
    FOREIGN KEY (firma_id) REFERENCES firmas(id)
);

CREATE TABLE IF NOT EXISTS auditoria_firmas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    firma_id INTEGER,
    accion TEXT NOT NULL,
    usuario TEXT,
    detalle TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


def get_connection() -> sqlite3.Connection:
    """Devuelve una conexión SQLite configurada para toda la aplicación.

    * row_factory = sqlite3.Row  → las filas se leen como diccionarios.
    * PRAGMA foreign_keys = ON   → se respetan las llaves foráneas.
    """
    con = sqlite3.connect(str(config.DB_PATH), timeout=15)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


@contextmanager
def transaccion() -> Iterator[sqlite3.Connection]:
    """Contexto que entrega una conexión, hace commit al salir y rollback ante error."""
    con = get_connection()
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def init_db() -> None:
    """Crea el esquema completo si aún no existe (idempotente)."""
    con = get_connection()
    try:
        con.executescript(_ESQUEMA)
        con.commit()
    finally:
        con.close()
