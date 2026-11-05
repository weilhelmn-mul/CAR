"""
=============================================================
 Sistema AT · Instituto Peruano del Deporte (IPD - DINADAF)
 database.py — Capa de acceso a datos (SQLite 3).
 Esquema de 8 tablas, upserts mensuales (ON CONFLICT) y
 gestión/auditoría de firmas (SHA-256, solo desactivación).
=============================================================
"""
from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Iterator

from src.config import DATA_DIR, FIRMAS_DIR

log = logging.getLogger("sistema_at.db")

DB_PATH: sqlite3.PathLike | str = str(DATA_DIR / "sistema_at.db")

# ----------------------------------------------------------------------
# Esquema (CREATE TABLE IF NOT EXISTS — re-ejecutable sin perder datos)
# ----------------------------------------------------------------------
ESQUEMA: str = """
CREATE TABLE IF NOT EXISTS deportistas (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre        TEXT    NOT NULL,
    documento     TEXT    DEFAULT '',
    deporte       TEXT    NOT NULL,
    categoria     TEXT    NOT NULL CHECK (categoria IN ('U-18','U-20','U-23','MAY','JUV')),
    sexo          TEXT    NOT NULL CHECK (sexo IN ('D','V')),
    car           TEXT    DEFAULT '',
    region        TEXT    DEFAULT '',
    entrenador    TEXT    DEFAULT '',
    activo        INTEGER NOT NULL DEFAULT 1,
    creado_en     TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS registros_mensuales (           -- AT-F3
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    deportista_id        INTEGER NOT NULL REFERENCES deportistas(id),
    periodo              TEXT    NOT NULL,                  -- 'YYYY-MM'
    objetivos            TEXT    DEFAULT '',
    pct_asistencia       REAL    CHECK (pct_asistencia  IS NULL OR (pct_asistencia  BETWEEN 0 AND 1)),
    pct_cumplimiento     REAL    CHECK (pct_cumplimiento IS NULL OR (pct_cumplimiento BETWEEN 0 AND 1)),
    resultados           TEXT    DEFAULT '',
    pruebas_sisdena_json TEXT    NOT NULL DEFAULT '[]',
    horario_json         TEXT    NOT NULL DEFAULT '[]',
    evaluacion           TEXT    DEFAULT '',
    entrenador           TEXT    DEFAULT '',
    creado_en            TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
    actualizado_en       TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
    UNIQUE (deportista_id, periodo)
);

CREATE TABLE IF NOT EXISTS consolidados_at_f1 (            -- AT-F1
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    car            TEXT    NOT NULL,
    periodo        TEXT    NOT NULL,                        -- 'YYYY-MM'
    matriculas_json TEXT   NOT NULL DEFAULT '{}',           -- {"altas":{cat:n},"bajas":{cat:n}}
    eval_medica    TEXT    DEFAULT '',
    eval_nutricion TEXT    DEFAULT '',
    eval_car       TEXT    DEFAULT '',
    observaciones  TEXT    DEFAULT '',
    jut_nombre     TEXT    DEFAULT '',
    creado_en      TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
    actualizado_en TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
    UNIQUE (car, periodo)
);

CREATE TABLE IF NOT EXISTS planes_jut (                    -- AT-F8
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    jut_nombre TEXT    NOT NULL,
    car        TEXT    DEFAULT '',
    periodo    TEXT    NOT NULL,                             -- 'YYYY-MM' (mes planificado)
    tareas_json TEXT   NOT NULL DEFAULT '[]',                -- [{n,actividad,fecha,hora,lugar,obs}]
    creado_en  TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
    actualizado_en TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    UNIQUE (jut_nombre, periodo)
);

CREATE TABLE IF NOT EXISTS evaluaciones_jut (              -- AT-F9
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_id              INTEGER NOT NULL REFERENCES planes_jut(id),
    periodo_evaluado     TEXT    NOT NULL,                 -- 'YYYY-MM' (mes evaluado = plan)
    pct_asistencia_prom  REAL    CHECK (pct_asistencia_prom  IS NULL OR (pct_asistencia_prom  BETWEEN 0 AND 1)),
    pct_cumplimiento_prom REAL   CHECK (pct_cumplimiento_prom IS NULL OR (pct_cumplimiento_prom BETWEEN 0 AND 1)),
    tareas_programadas   INTEGER DEFAULT 0,
    tareas_cumplidas     INTEGER DEFAULT 0,
    pct_tareas           REAL    CHECK (pct_tareas IS NULL OR (pct_tareas BETWEEN 0 AND 1)),
    fecha_visita         TEXT    DEFAULT '',
    realizado_por        TEXT    DEFAULT '',
    obs_visita           TEXT    DEFAULT '',
    calificacion_final   TEXT    NOT NULL CHECK (calificacion_final IN ('BUENO','REGULAR','MALO')),
    opinion_presidente   TEXT    DEFAULT '',
    creado_en            TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
    UNIQUE (plan_id)
);

CREATE TABLE IF NOT EXISTS firmas (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    rol       TEXT    NOT NULL CHECK (rol IN ('entrenador','jut','dinadaf','presidente_fdn')),
    nombre    TEXT    NOT NULL,
    archivo   TEXT    NOT NULL,                             -- PNG dentro de FIRMAS_DIR
    sha256    TEXT    NOT NULL,
    activo    INTEGER NOT NULL DEFAULT 1,                   -- solo desactivación, jamás borrado
    creado_en TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS asignaciones_firma (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    firma_id  INTEGER NOT NULL REFERENCES firmas(id),
    ambito    TEXT    NOT NULL DEFAULT '*',                  -- 'AT-F3'|'AT-F1'|'AT-F8'|'AT-F9'|'*'
    activo    INTEGER NOT NULL DEFAULT 1,
    creado_en TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS auditoria_firmas (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    firma_id    INTEGER REFERENCES firmas(id),
    accion      TEXT    NOT NULL,                            -- 'registro'|'desactivacion'|'uso'
    detalle     TEXT    DEFAULT '',
    hash_sha256 TEXT    DEFAULT '',
    fecha       TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
);

-- Índices auxiliares de consulta (no alteran el esquema lógico)
CREATE INDEX IF NOT EXISTS idx_registros_periodo   ON registros_mensuales (periodo);
CREATE INDEX IF NOT EXISTS idx_consolidados_periodo ON consolidados_at_f1 (periodo);
CREATE INDEX IF NOT EXISTS idx_planes_periodo      ON planes_jut (periodo);

-- ----------------------------------------------------------------------
-- Tablas v3.0 — resultados deportivos, alimentación y seguros
-- ----------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS resultados_deportivos (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    deportista_id INTEGER NOT NULL REFERENCES deportistas(id),
    fecha         TEXT    NOT NULL,                          -- 'YYYY-MM-DD'
    competencia   TEXT    NOT NULL,
    lugar         TEXT    DEFAULT '',
    prueba        TEXT    DEFAULT '',                        -- prueba / estilo / categoría de la competencia
    marca         TEXT    DEFAULT '',                        -- tiempo, distancia, puntaje o resultado
    posicion      INTEGER CHECK (posicion IS NULL OR posicion > 0),
    medalla       TEXT    NOT NULL DEFAULT '' CHECK (medalla IN ('','ORO','PLATA','BRONCE')),
    puntos        REAL,
    observaciones TEXT    DEFAULT '',
    creado_en     TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS alimentacion (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    deportista_id     INTEGER NOT NULL REFERENCES deportistas(id),
    periodo           TEXT    NOT NULL,                     -- 'YYYY-MM'
    fecha_evaluacion  TEXT    DEFAULT '',                   -- 'YYYY-MM-DD'
    nutricionista     TEXT    DEFAULT '',
    peso_kg           REAL,
    estatura_m        REAL,
    imc               REAL,
    pct_grasa_corporal REAL,
    kcal_dia          REAL,
    objetivo          TEXT    NOT NULL DEFAULT 'RENDIMIENTO' CHECK (objetivo IN ('RENDIMIENTO','HIPERTROFIA','DESCENSO_PESO','ASCENSO_PESO','RECUPERACION')),
    plan_alimenticio  TEXT    DEFAULT '',
    observaciones     TEXT    DEFAULT '',
    creado_en         TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
    actualizado_en    TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
    UNIQUE (deportista_id, periodo)
);

CREATE TABLE IF NOT EXISTS seguros (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    deportista_id  INTEGER NOT NULL REFERENCES deportistas(id),
    aseguradora    TEXT    NOT NULL,
    tipo_seguro    TEXT    NOT NULL DEFAULT 'SALUD' CHECK (tipo_seguro IN ('SALUD','ACCIDENTES_DEPORTIVOS','VIDA','OTRO')),
    numero_poliza  TEXT    DEFAULT '',
    cobertura      TEXT    DEFAULT '',
    vigencia_inicio TEXT   DEFAULT '',                      -- 'YYYY-MM-DD'
    vigencia_fin   TEXT    DEFAULT '',                      -- 'YYYY-MM-DD'
    estado         TEXT    NOT NULL DEFAULT 'VIGENTE' CHECK (estado IN ('VIGENTE','VENCIDO','EN_TRAMITE','ANULADO')),
    observaciones  TEXT    DEFAULT '',
    creado_en      TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
    actualizado_en TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE INDEX IF NOT EXISTS idx_resultados_deportista ON resultados_deportivos (deportista_id, fecha);
CREATE INDEX IF NOT EXISTS idx_resultados_fecha      ON resultados_deportivos (fecha);
CREATE INDEX IF NOT EXISTS idx_alimentacion_periodo  ON alimentacion (periodo);
CREATE INDEX IF NOT EXISTS idx_seguros_estado        ON seguros (estado);
"""

# ----------------------------------------------------------------------
# Conexión
# ----------------------------------------------------------------------
def get_connection() -> sqlite3.Connection:
    """Abre una conexión SQLite con filas tipo diccionario y claves foráneas activas."""
    conexion = sqlite3.connect(DB_PATH)
    conexion.row_factory = sqlite3.Row
    conexion.execute("PRAGMA foreign_keys = ON;")
    return conexion


@contextmanager
def _conexion() -> Iterator[sqlite3.Connection]:
    """Contexto transaccional: commit al salir, rollback ante error, siempre cierra."""
    con = get_connection()
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def _como_json(valor: Any) -> str:
    """Serializa a texto JSON legible (tildes conservadas)."""
    return json.dumps(valor, ensure_ascii=False)


def _desde_json(texto: str | None, por_defecto: Any) -> Any:
    """Deserializa JSON almacenado; devuelve `por_defecto` si está vacío/inválido."""
    if not texto:
        return por_defecto
    try:
        return json.loads(texto)
    except (TypeError, ValueError):
        return por_defecto


def init_db() -> None:
    """Crea carpetas de datos y el esquema completo si no existe."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    FIRMAS_DIR.mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "generados").mkdir(parents=True, exist_ok=True)
    with _conexion() as con:
        con.executescript(ESQUEMA)
    log.info("Base de datos inicializada en %s", DB_PATH)


# ----------------------------------------------------------------------
# Deportistas
# ----------------------------------------------------------------------
def crear_deportista(datos: dict[str, Any]) -> int:
    """Registra un deportista activo y devuelve su id."""
    with _conexion() as con:
        cursor = con.execute(
            "INSERT INTO deportistas (nombre, documento, deporte, categoria, sexo, car, region, entrenador) "
            "VALUES (:nombre, :documento, :deporte, :categoria, :sexo, :car, :region, :entrenador)",
            datos,
        )
        return int(cursor.lastrowid or 0)


def actualizar_deportista(deportista_id: int, datos: dict[str, Any]) -> None:
    """Actualiza los campos editables de un deportista."""
    consulta = (
        "UPDATE deportistas SET nombre=:nombre, documento=:documento, deporte=:deporte, "
        "categoria=:categoria, sexo=:sexo, car=:car, region=:region, entrenador=:entrenador "
        "WHERE id=:id"
    )
    with _conexion() as con:
        con.execute(consulta, {**datos, "id": deportista_id})


def cambiar_estado_deportista(deportista_id: int, activo: bool) -> None:
    """Da de baja (0) o reactiva (1) un deportista — nunca se borra."""
    with _conexion() as con:
        con.execute("UPDATE deportistas SET activo=? WHERE id=?", (1 if activo else 0, deportista_id))


def obtener_deportista(deportista_id: int) -> sqlite3.Row | None:
    with _conexion() as con:
        return con.execute("SELECT * FROM deportistas WHERE id=?", (deportista_id,)).fetchone()


def listar_deportistas(solo_activos: bool = True, categoria: str = "", texto: str = "") -> list[sqlite3.Row]:
    """Lista deportistas con filtros opcionales de categoría y búsqueda por nombre."""
    condiciones = ["1=1"]
    parametros: list[Any] = []
    if solo_activos:
        condiciones.append("activo=1")
    if categoria:
        condiciones.append("categoria=?")
        parametros.append(categoria)
    if texto:
        condiciones.append("LOWER(nombre) LIKE ?")
        parametros.append(f"%{texto.lower()}%")
    sql = "SELECT * FROM deportistas WHERE " + " AND ".join(condiciones) + " ORDER BY nombre"
    with _conexion() as con:
        return list(con.execute(sql, parametros).fetchall())


def opciones_deportistas() -> list[tuple[int, str]]:
    """Pares (id, etiqueta) de deportistas activos para menús desplegables."""
    return [(int(f["id"]), f"{f['nombre']} · {f['categoria']} · {f['deporte']}")
            for f in listar_deportistas(solo_activos=True)]


def buscar_deportista_por_nombre(nombre: str) -> sqlite3.Row | None:
    """Busca exacto (sin acentos de mayúsculas) un deportista activo por nombre."""
    with _conexion() as con:
        return con.execute(
            "SELECT * FROM deportistas WHERE activo=1 AND LOWER(TRIM(nombre))=LOWER(TRIM(?)) "
            "ORDER BY id LIMIT 1",
            (nombre,),
        ).fetchone()


# ----------------------------------------------------------------------
# Registros mensuales — AT-F3
# ----------------------------------------------------------------------
def upsert_registro(
    deportista_id: int,
    periodo: str,
    *,
    objetivos: str = "",
    pct_asistencia: float | None = None,
    pct_cumplimiento: float | None = None,
    resultados: str = "",
    horario: list[str] | None = None,
    evaluacion: str = "",
    entrenador: str = "",
) -> int:
    """Crea o actualiza el registro AT-F3 de (deportista, periodo). Devuelve el id."""
    parametros = (
        deportista_id, periodo, objetivos, pct_asistencia, pct_cumplimiento,
        resultados, _como_json(horario or []), evaluacion, entrenador,
    )
    with _conexion() as con:
        cursor = con.execute(
            """
            INSERT INTO registros_mensuales
                (deportista_id, periodo, objetivos, pct_asistencia, pct_cumplimiento,
                 resultados, horario_json, evaluacion, entrenador)
            VALUES (?,?,?,?,?,?,?,?,?)
            ON CONFLICT(deportista_id, periodo) DO UPDATE SET
                objetivos        = excluded.objetivos,
                pct_asistencia   = COALESCE(excluded.pct_asistencia, registros_mensuales.pct_asistencia),
                pct_cumplimiento = COALESCE(excluded.pct_cumplimiento, registros_mensuales.pct_cumplimiento),
                resultados       = excluded.resultados,
                horario_json     = excluded.horario_json,
                evaluacion       = excluded.evaluacion,
                entrenador       = excluded.entrenador,
                actualizado_en   = datetime('now','localtime')
            """,
            parametros,
        )
        fila = con.execute(
            "SELECT id FROM registros_mensuales WHERE deportista_id=? AND periodo=?",
            (deportista_id, periodo),
        ).fetchone()
        log.info("Registro AT-F3 upsert: deportista=%s periodo=%s", deportista_id, periodo)
        return int(fila["id"])


def obtener_registro(registro_id: int) -> sqlite3.Row | None:
    """Registro AT-F3 con datos del deportista (JOIN)."""
    with _conexion() as con:
        return con.execute(
            """
            SELECT r.*, d.nombre, d.deporte, d.categoria, d.sexo,
                   d.car AS car_dep, d.region AS region_dep, d.entrenador AS entrenador_dep
            FROM registros_mensuales r
            JOIN deportistas d ON d.id = r.deportista_id
            WHERE r.id=?
            """,
            (registro_id,),
        ).fetchone()


def listar_registros(periodo: str = "", deportista_id: int | None = None) -> list[sqlite3.Row]:
    """Lista registros AT-F3 (opcionalmente de un periodo o deportista)."""
    condiciones, parametros = ["1=1"], []
    if periodo:
        condiciones.append("r.periodo=?")
        parametros.append(periodo)
    if deportista_id is not None:
        condiciones.append("r.deportista_id=?")
        parametros.append(deportista_id)
    sql = (
        "SELECT r.*, d.nombre, d.categoria, d.deporte FROM registros_mensuales r "
        "JOIN deportistas d ON d.id=r.deportista_id WHERE "
        + " AND ".join(condiciones)
        + " ORDER BY r.periodo DESC, d.nombre"
    )
    with _conexion() as con:
        return list(con.execute(sql, parametros).fetchall())


def agregar_pruebas_sisdena(deportista_id: int, periodo: str, nuevas: list[dict[str, Any]]) -> int:
    """Fusiona participaciones SISDENA (sin duplicar) en el registro del periodo."""
    clave = lambda p: (str(p.get("fecha", "")), str(p.get("competencia", "")), str(p.get("prueba", "")))
    with _conexion() as con:
        fila = con.execute(
            "SELECT id, pruebas_sisdena_json FROM registros_mensuales WHERE deportista_id=? AND periodo=?",
            (deportista_id, periodo),
        ).fetchone()
        actuales: list[dict[str, Any]] = _desde_json(fila["pruebas_sisdena_json"] if fila else None, [])
        existentes = {clave(p) for p in actuales}
        for prueba in nuevas:
            if clave(prueba) not in existentes:
                actuales.append(prueba)
                existentes.add(clave(prueba))
        if fila:
            con.execute(
                "UPDATE registros_mensuales SET pruebas_sisdena_json=?, actualizado_en=datetime('now','localtime') "
                "WHERE id=?",
                (_como_json(actuales), fila["id"]),
            )
        else:
            con.execute(
                "INSERT INTO registros_mensuales (deportista_id, periodo, pruebas_sisdena_json) VALUES (?,?,?)",
                (deportista_id, periodo, _como_json(actuales)),
            )
        return len(actuales)


# ----------------------------------------------------------------------
# Consolidados CAR — AT-F1
# ----------------------------------------------------------------------
def upsert_consolidado(car: str, periodo: str, datos: dict[str, Any]) -> int:
    """Crea o actualiza el consolidado AT-F1 de (CAR, periodo). Devuelve el id."""
    with _conexion() as con:
        con.execute(
            """
            INSERT INTO consolidados_at_f1
                (car, periodo, matriculas_json, eval_medica, eval_nutricion, eval_car,
                 observaciones, jut_nombre)
            VALUES (:car, :periodo, :matriculas_json, :eval_medica, :eval_nutricion,
                    :eval_car, :observaciones, :jut_nombre)
            ON CONFLICT(car, periodo) DO UPDATE SET
                matriculas_json = excluded.matriculas_json,
                eval_medica     = excluded.eval_medica,
                eval_nutricion  = excluded.eval_nutricion,
                eval_car        = excluded.eval_car,
                observaciones   = excluded.observaciones,
                jut_nombre      = excluded.jut_nombre,
                actualizado_en  = datetime('now','localtime')
            """,
            {
                "car": car, "periodo": periodo,
                "matriculas_json": _como_json(datos.get("matriculas", {"altas": {}, "bajas": {}})),
                "eval_medica": datos.get("eval_medica", ""),
                "eval_nutricion": datos.get("eval_nutricion", ""),
                "eval_car": datos.get("eval_car", ""),
                "observaciones": datos.get("observaciones", ""),
                "jut_nombre": datos.get("jut_nombre", ""),
            },
        )
        fila = con.execute(
            "SELECT id FROM consolidados_at_f1 WHERE car=? AND periodo=?", (car, periodo)
        ).fetchone()
        return int(fila["id"])


def obtener_consolidado(consolidado_id: int) -> sqlite3.Row | None:
    with _conexion() as con:
        return con.execute("SELECT * FROM consolidados_at_f1 WHERE id=?", (consolidado_id,)).fetchone()


def listar_consolidados() -> list[sqlite3.Row]:
    with _conexion() as con:
        return list(
            con.execute("SELECT * FROM consolidados_at_f1 ORDER BY periodo DESC, car").fetchall()
        )


def registros_para_consolidado(car: str, periodo: str) -> list[sqlite3.Row]:
    """Registros AT-F3 del periodo para un CAR (o de todos si `car` viene vacío)."""
    with _conexion() as con:
        return list(
            con.execute(
                """
                SELECT r.*, d.nombre, d.categoria FROM registros_mensuales r
                JOIN deportistas d ON d.id = r.deportista_id
                WHERE r.periodo=? AND (?='' OR LOWER(TRIM(d.car))=LOWER(TRIM(?)))
                ORDER BY d.categoria, d.nombre
                """,
                (periodo, car.strip(), car.strip()),
            ).fetchall()
        )


def promedios_periodo(car: str, periodo: str) -> dict[str, Any]:
    """Promedios de % asistencia / cumplimiento (AT-F3) para AT-F9."""
    with _conexion() as con:
        fila = con.execute(
            """
            SELECT AVG(r.pct_asistencia) AS asistencia, AVG(r.pct_cumplimiento) AS cumplimiento,
                   COUNT(*) AS n
            FROM registros_mensuales r
            JOIN deportistas d ON d.id = r.deportista_id
            WHERE r.periodo=? AND (?='' OR LOWER(TRIM(d.car))=LOWER(TRIM(?)))
            """,
            (periodo, car.strip(), car.strip()),
        ).fetchone()
    return {
        "pct_asistencia": fila["asistencia"],
        "pct_cumplimiento": fila["cumplimiento"],
        "n": int(fila["n"] or 0),
    }


# ----------------------------------------------------------------------
# Planes JUT — AT-F8
# ----------------------------------------------------------------------
def upsert_plan(jut_nombre: str, periodo: str, car: str, tareas: list[dict[str, Any]]) -> int:
    """Crea o actualiza el plan mensual AT-F8 de (JUT, periodo). Devuelve el id."""
    with _conexion() as con:
        con.execute(
            """
            INSERT INTO planes_jut (jut_nombre, car, periodo, tareas_json)
            VALUES (?,?,?,?)
            ON CONFLICT(jut_nombre, periodo) DO UPDATE SET
                car        = excluded.car,
                tareas_json = excluded.tareas_json,
                actualizado_en = datetime('now','localtime')
            """,
            (jut_nombre.strip(), car.strip(), periodo, _como_json(tareas)),
        )
        fila = con.execute(
            "SELECT id FROM planes_jut WHERE jut_nombre=? AND periodo=?",
            (jut_nombre.strip(), periodo),
        ).fetchone()
        return int(fila["id"])


def obtener_plan(plan_id: int) -> sqlite3.Row | None:
    with _conexion() as con:
        return con.execute("SELECT * FROM planes_jut WHERE id=?", (plan_id,)).fetchone()


def listar_planes() -> list[sqlite3.Row]:
    with _conexion() as con:
        return list(con.execute("SELECT * FROM planes_jut ORDER BY periodo DESC, jut_nombre").fetchall())


def tareas_del_plan(plan_id: int) -> list[dict[str, Any]]:
    """Devuelve la lista de tareas {n, actividad, fecha, hora, lugar, obs} del plan."""
    plan = obtener_plan(plan_id)
    if plan is None:
        return []
    return list(_desde_json(plan["tareas_json"], []))


# ----------------------------------------------------------------------
# Evaluaciones JUT — AT-F9
# ----------------------------------------------------------------------
def upsert_evaluacion(plan_id: int, periodo_evaluado: str, datos: dict[str, Any]) -> int:
    """Crea o actualiza la evaluación AT-F9 de un plan (una por plan)."""
    with _conexion() as con:
        con.execute(
            """
            INSERT INTO evaluaciones_jut
                (plan_id, periodo_evaluado, pct_asistencia_prom, pct_cumplimiento_prom,
                 tareas_programadas, tareas_cumplidas, pct_tareas, fecha_visita,
                 realizado_por, obs_visita, calificacion_final, opinion_presidente)
            VALUES (:plan_id, :periodo_evaluado, :pct_asistencia_prom, :pct_cumplimiento_prom,
                    :tareas_programadas, :tareas_cumplidas, :pct_tareas, :fecha_visita,
                    :realizado_por, :obs_visita, :calificacion_final, :opinion_presidente)
            ON CONFLICT(plan_id) DO UPDATE SET
                periodo_evaluado      = excluded.periodo_evaluado,
                pct_asistencia_prom   = excluded.pct_asistencia_prom,
                pct_cumplimiento_prom = excluded.pct_cumplimiento_prom,
                tareas_programadas    = excluded.tareas_programadas,
                tareas_cumplidas      = excluded.tareas_cumplidas,
                pct_tareas            = excluded.pct_tareas,
                fecha_visita          = excluded.fecha_visita,
                realizado_por         = excluded.realizado_por,
                obs_visita            = excluded.obs_visita,
                calificacion_final    = excluded.calificacion_final,
                opinion_presidente    = excluded.opinion_presidente
            """,
            {
                "plan_id": plan_id, "periodo_evaluado": periodo_evaluado,
                "pct_asistencia_prom": datos.get("pct_asistencia_prom"),
                "pct_cumplimiento_prom": datos.get("pct_cumplimiento_prom"),
                "tareas_programadas": datos.get("tareas_programadas", 0),
                "tareas_cumplidas": datos.get("tareas_cumplidas", 0),
                "pct_tareas": datos.get("pct_tareas"),
                "fecha_visita": datos.get("fecha_visita", ""),
                "realizado_por": datos.get("realizado_por", ""),
                "obs_visita": datos.get("obs_visita", ""),
                "calificacion_final": datos.get("calificacion_final", "REGULAR"),
                "opinion_presidente": datos.get("opinion_presidente", ""),
            },
        )
        fila = con.execute("SELECT id FROM evaluaciones_jut WHERE plan_id=?", (plan_id,)).fetchone()
        return int(fila["id"])


def obtener_evaluacion(evaluacion_id: int) -> sqlite3.Row | None:
    with _conexion() as con:
        return con.execute("SELECT * FROM evaluaciones_jut WHERE id=?", (evaluacion_id,)).fetchone()


def obtener_evaluacion_por_plan(plan_id: int) -> sqlite3.Row | None:
    with _conexion() as con:
        return con.execute("SELECT * FROM evaluaciones_jut WHERE plan_id=?", (plan_id,)).fetchone()


def listar_evaluaciones() -> list[sqlite3.Row]:
    with _conexion() as con:
        return list(
            con.execute(
                """
                SELECT e.*, p.jut_nombre, p.car, p.periodo FROM evaluaciones_jut e
                JOIN planes_jut p ON p.id = e.plan_id
                ORDER BY e.id DESC
                """
            ).fetchall()
        )


# ----------------------------------------------------------------------
# Firmas (SHA-256 · solo desactivación · auditoría completa)
# ----------------------------------------------------------------------
def registrar_firma(rol: str, nombre: str, contenido_png: bytes) -> int:
    """Guarda el PNG de la rúbrica, su hash SHA-256 y deja constancia en auditoría."""
    FIRMAS_DIR.mkdir(parents=True, exist_ok=True)
    hash_sha = hashlib.sha256(contenido_png).hexdigest()
    archivo = FIRMAS_DIR / f"{rol}_{datetime.now():%Y%m%d_%H%M%S}.png"
    archivo.write_bytes(contenido_png)
    with _conexion() as con:
        cursor = con.execute(
            "INSERT INTO firmas (rol, nombre, archivo, sha256, activo) VALUES (?,?,?,?,1)",
            (rol, nombre, str(archivo), hash_sha),
        )
        firma_id = int(cursor.lastrowid or 0)
        con.execute("INSERT INTO asignaciones_firma (firma_id, ambito) VALUES (?, '*')", (firma_id,))
        con.execute(
            "INSERT INTO auditoria_firmas (firma_id, accion, detalle, hash_sha256) "
            "VALUES (?, 'registro', ?, ?)",
            (firma_id, f"Rol={rol} · Titular={nombre}", hash_sha),
        )
    log.info("Firma registrada: id=%s rol=%s sha256=%s", firma_id, rol, hash_sha[:12])
    return firma_id


def desactivar_firma(firma_id: int) -> None:
    """Desactiva una firma (nunca se elimina) y registra la acción en auditoría."""
    with _conexion() as con:
        con.execute("UPDATE firmas SET activo=0 WHERE id=?", (firma_id,))
        con.execute(
            "INSERT INTO auditoria_firmas (firma_id, accion, detalle) VALUES (?, 'desactivacion', ?)",
            (firma_id, f"Firma id={firma_id} desactivada"),
        )
    log.info("Firma desactivada: id=%s", firma_id)


def listar_firmas() -> list[sqlite3.Row]:
    with _conexion() as con:
        return list(con.execute("SELECT * FROM firmas ORDER BY id DESC").fetchall())


def firma_activa(rol: str) -> sqlite3.Row | None:
    """Última firma ACTIVA de un rol (o None)."""
    with _conexion() as con:
        return con.execute(
            "SELECT * FROM firmas WHERE rol=? AND activo=1 ORDER BY id DESC LIMIT 1", (rol,)
        ).fetchone()


def registrar_uso_firma(firma_id: int, detalle: str) -> None:
    """Anota en auditoría que una firma fue estampada en un documento generado."""
    with _conexion() as con:
        con.execute(
            "INSERT INTO auditoria_firmas (firma_id, accion, detalle) VALUES (?, 'uso', ?)",
            (firma_id, detalle),
        )


# ----------------------------------------------------------------------
# Contadores para el panel (dashboard)
# ----------------------------------------------------------------------
def contar_deportistas(solo_activos: bool = True) -> int:
    with _conexion() as con:
        fila = con.execute(
            f"SELECT COUNT(*) AS n FROM deportistas {'WHERE activo=1' if solo_activos else ''}"
        ).fetchone()
        return int(fila["n"])


def contar_registros(periodo: str) -> int:
    with _conexion() as con:
        fila = con.execute("SELECT COUNT(*) AS n FROM registros_mensuales WHERE periodo=?", (periodo,)).fetchone()
        return int(fila["n"])


def contar_planes(periodo: str = "") -> int:
    with _conexion() as con:
        if periodo:
            fila = con.execute("SELECT COUNT(*) AS n FROM planes_jut WHERE periodo=?", (periodo,)).fetchone()
        else:
            fila = con.execute("SELECT COUNT(*) AS n FROM planes_jut").fetchone()
        return int(fila["n"])


def contar_evaluaciones() -> int:
    with _conexion() as con:
        fila = con.execute("SELECT COUNT(*) AS n FROM evaluaciones_jut").fetchone()
        return int(fila["n"])


def ultimos_registros(limite: int = 8) -> list[sqlite3.Row]:
    with _conexion() as con:
        return list(
            con.execute(
                """
                SELECT r.periodo, r.pct_asistencia, r.pct_cumplimiento, r.actualizado_en,
                       d.nombre, d.categoria
                FROM registros_mensuales r JOIN deportistas d ON d.id=r.deportista_id
                ORDER BY r.actualizado_en DESC LIMIT ?
                """,
                (limite,),
            ).fetchall()
        )


# ======================================================================
# v3.0 — Resultados deportivos (mejores marcas por período)
# ======================================================================
def agregar_resultado(datos: dict[str, Any]) -> int:
    """Registra un resultado deportivo (fecha, competencia, marca, posición…)."""
    with _conexion() as con:
        cursor = con.execute(
            """
            INSERT INTO resultados_deportivos
                (deportista_id, fecha, competencia, lugar, prueba, marca,
                 posicion, medalla, puntos, observaciones)
            VALUES (:deportista_id, :fecha, :competencia, :lugar, :prueba, :marca,
                    :posicion, :medalla, :puntos, :observaciones)
            """,
            {
                "deportista_id": datos["deportista_id"],
                "fecha": datos["fecha"],
                "competencia": datos["competencia"],
                "lugar": datos.get("lugar", ""),
                "prueba": datos.get("prueba", ""),
                "marca": datos.get("marca", ""),
                "posicion": datos.get("posicion"),
                "medalla": datos.get("medalla", ""),
                "puntos": datos.get("puntos"),
                "observaciones": datos.get("observaciones", ""),
            },
        )
        return int(cursor.lastrowid or 0)


def eliminar_resultado(resultado_id: int) -> None:
    """Elimina un resultado mal ingresado (los resultados sí admiten borrado)."""
    with _conexion() as con:
        con.execute("DELETE FROM resultados_deportivos WHERE id=?", (resultado_id,))


def resultados_de(deportista_id: int, limite: int = 0) -> list[sqlite3.Row]:
    """Historial de resultados de un deportista (más recientes primero)."""
    sql = "SELECT * FROM resultados_deportivos WHERE deportista_id=? ORDER BY fecha DESC, id DESC"
    if limite:
        sql += f" LIMIT {int(limite)}"
    with _conexion() as con:
        return list(con.execute(sql, (deportista_id,)).fetchall())


def resultados_deporte_car(fecha_desde: str = "", fecha_hasta: str = "") -> list[sqlite3.Row]:
    """Resultados con datos del deportista, para análisis y top (opcional por rango)."""
    condiciones, parametros = ["1=1"], []
    if fecha_desde:
        condiciones.append("r.fecha >= ?")
        parametros.append(fecha_desde)
    if fecha_hasta:
        condiciones.append("r.fecha <= ?")
        parametros.append(fecha_hasta)
    sql = (
        "SELECT r.*, d.nombre, d.deporte, d.categoria, d.sexo, d.car "
        "FROM resultados_deportivos r JOIN deportistas d ON d.id = r.deportista_id "
        "WHERE " + " AND ".join(condiciones) +
        " ORDER BY r.fecha DESC, COALESCE(r.posicion, 99)"
    )
    with _conexion() as con:
        return list(con.execute(sql, parametros).fetchall())


def resumen_mejores_por_periodo(deportista_id: int) -> dict[str, dict[str, dict[str, Any]]]:
    """Mejor resultado por mes, bimestre, trimestre y año.

    Devuelve {"mes": {"2026-11": mejor}, "bimestre": {"2026 · B3": mejor},
              "trimestre": {"2026 · T3": mejor}, "anual": {"2026": mejor}}
    donde `mejor` es el registro con MENOR posición (1° lugar gana; los sin
    posición se ordenan al final). Las claves de mes usan 'YYYY-MM'; los
    bloques usan la etiqueta legible 'YYYY · B1…B6' / 'YYYY · T1…T4'.
    """
    from src.config import MESES_BIMESTRE, MESES_TRIMESTRE  # import local: evita ciclo

    filas = resultados_de(deportista_id)

    def _clave(fila: sqlite3.Row) -> tuple[int, int]:
        posicion = int(fila["posicion"]) if fila["posicion"] is not None else 999
        return (posicion, -int(fila["puntos"] or 0))

    bloques: dict[str, dict[str, dict[str, Any]]] = {
        "mes": {}, "bimestre": {}, "trimestre": {}, "anual": {},
    }
    for fila in filas:
        fecha = str(fila["fecha"])
        if len(fecha) < 7:
            continue
        anio, mes = fecha[:4], int(fecha[5:7])
        etiquetas = {
            "mes": f"{anio}-{mes:02d}",
            "bimestre": f"{anio} · {MESES_BIMESTRE.get(mes, '?')}",
            "trimestre": f"{anio} · {MESES_TRIMESTRE.get(mes, '?')}",
            "anual": anio,
        }
        for tipo, etiqueta in etiquetas.items():
            actual = bloques[tipo].get(etiqueta)
            if actual is None or _clave(fila) < _clave(actual):
                bloques[tipo][etiqueta] = fila
    return bloques


# ======================================================================
# v3.0 — Alimentación (evaluación nutricional mensual)
# ======================================================================
def upsert_alimentacion(deportista_id: int, periodo: str, datos: dict[str, Any]) -> int:
    """Crea o actualiza la evaluación nutricional de (deportista, periodo)."""
    with _conexion() as con:
        con.execute(
            """
            INSERT INTO alimentacion
                (deportista_id, periodo, fecha_evaluacion, nutricionista, peso_kg,
                 estatura_m, imc, pct_grasa_corporal, kcal_dia, objetivo,
                 plan_alimenticio, observaciones)
            VALUES (:deportista_id, :periodo, :fecha_evaluacion, :nutricionista, :peso_kg,
                    :estatura_m, :imc, :pct_grasa_corporal, :kcal_dia, :objetivo,
                    :plan_alimenticio, :observaciones)
            ON CONFLICT(deportista_id, periodo) DO UPDATE SET
                fecha_evaluacion   = excluded.fecha_evaluacion,
                nutricionista      = excluded.nutricionista,
                peso_kg            = excluded.peso_kg,
                estatura_m         = excluded.estatura_m,
                imc                = excluded.imc,
                pct_grasa_corporal = excluded.pct_grasa_corporal,
                kcal_dia           = excluded.kcal_dia,
                objetivo           = excluded.objetivo,
                plan_alimenticio   = excluded.plan_alimenticio,
                observaciones      = excluded.observaciones,
                actualizado_en     = datetime('now','localtime')
            """,
            {
                "deportista_id": deportista_id, "periodo": periodo,
                "fecha_evaluacion": datos.get("fecha_evaluacion", ""),
                "nutricionista": datos.get("nutricionista", ""),
                "peso_kg": datos.get("peso_kg"),
                "estatura_m": datos.get("estatura_m"),
                "imc": datos.get("imc"),
                "pct_grasa_corporal": datos.get("pct_grasa_corporal"),
                "kcal_dia": datos.get("kcal_dia"),
                "objetivo": datos.get("objetivo", "RENDIMIENTO"),
                "plan_alimenticio": datos.get("plan_alimenticio", ""),
                "observaciones": datos.get("observaciones", ""),
            },
        )
        fila = con.execute(
            "SELECT id FROM alimentacion WHERE deportista_id=? AND periodo=?",
            (deportista_id, periodo),
        ).fetchone()
        return int(fila["id"])


def obtener_alimentacion(registro_id: int) -> sqlite3.Row | None:
    """Evaluación nutricional con datos del deportista (JOIN)."""
    with _conexion() as con:
        return con.execute(
            """
            SELECT a.*, d.nombre, d.deporte, d.categoria, d.sexo, d.car, d.region
            FROM alimentacion a JOIN deportistas d ON d.id = a.deportista_id
            WHERE a.id=?
            """,
            (registro_id,),
        ).fetchone()


def listar_alimentacion(periodo: str = "") -> list[sqlite3.Row]:
    """Listado de evaluaciones nutricionales (opcionalmente de un periodo)."""
    condiciones, parametros = ["1=1"], []
    if periodo:
        condiciones.append("a.periodo=?")
        parametros.append(periodo)
    sql = (
        "SELECT a.*, d.nombre, d.categoria, d.deporte FROM alimentacion a "
        "JOIN deportistas d ON d.id=a.deportista_id WHERE "
        + " AND ".join(condiciones) + " ORDER BY a.periodo DESC, d.nombre"
    )
    with _conexion() as con:
        return list(con.execute(sql, parametros).fetchall())


def actualizar_plan_alimenticio(registro_id: int, texto: str) -> None:
    """Escribe el plan alimenticio (usado por el Asistente IA)."""
    with _conexion() as con:
        con.execute(
            "UPDATE alimentacion SET plan_alimenticio=?, actualizado_en=datetime('now','localtime') WHERE id=?",
            (texto, registro_id),
        )


# ----------------------------------------------------------------------
# v3.0 — Escritura de textos narrativos (Asistente IA → formatos)
# ----------------------------------------------------------------------
def actualizar_narrativa_f3(registro_id: int, *, objetivos: str | None = None,
                            resultados: str | None = None,
                            evaluacion: str | None = None) -> None:
    """Actualiza solo los campos narrativos de un registro AT-F3 (no toca cifras)."""
    asignaciones, valores = [], []
    for columna, texto in (("objetivos", objetivos), ("resultados", resultados),
                           ("evaluacion", evaluacion)):
        if texto is not None:
            asignaciones.append(f"{columna}=?")
            valores.append(texto)
    if not asignaciones:
        return
    valores.append(registro_id)
    with _conexion() as con:
        con.execute(
            f"UPDATE registros_mensuales SET {', '.join(asignaciones)}, "
            "actualizado_en=datetime('now','localtime') WHERE id=?",
            valores,
        )


def actualizar_narrativa_f1(consolidado_id: int, *, eval_car: str | None = None,
                            observaciones: str | None = None) -> None:
    """Actualiza los textos del consolidado AT-F1 (eval CAR y observaciones)."""
    asignaciones, valores = [], []
    for columna, texto in (("eval_car", eval_car), ("observaciones", observaciones)):
        if texto is not None:
            asignaciones.append(f"{columna}=?")
            valores.append(texto)
    if not asignaciones:
        return
    valores.append(consolidado_id)
    with _conexion() as con:
        con.execute(
            f"UPDATE consolidados_at_f1 SET {', '.join(asignaciones)}, "
            "actualizado_en=datetime('now','localtime') WHERE id=?",
            valores,
        )


def actualizar_narrativa_f9(evaluacion_id: int, *, obs_visita: str | None = None,
                            opinion_presidente: str | None = None) -> None:
    """Actualiza los textos de la evaluación AT-F9 (visita y opinión)."""
    asignaciones, valores = [], []
    for columna, texto in (("obs_visita", obs_visita),
                           ("opinion_presidente", opinion_presidente)):
        if texto is not None:
            asignaciones.append(f"{columna}=?")
            valores.append(texto)
    if not asignaciones:
        return
    valores.append(evaluacion_id)
    with _conexion() as con:
        con.execute(
            f"UPDATE evaluaciones_jut SET {', '.join(asignaciones)} WHERE id=?",
            valores,
        )


# ======================================================================
# v3.0 — Seguros deportivos
# ======================================================================
def upsert_seguro(deportista_id: int, datos: dict[str, Any]) -> int:
    """Registra o actualiza una póliza de seguro deportivo. Devuelve su id."""
    with _conexion() as con:
        if datos.get("id"):
            con.execute(
                """
                UPDATE seguros SET aseguradora=:aseguradora, tipo_seguro=:tipo_seguro,
                    numero_poliza=:numero_poliza, cobertura=:cobertura,
                    vigencia_inicio=:vigencia_inicio, vigencia_fin=:vigencia_fin,
                    estado=:estado, observaciones=:observaciones,
                    actualizado_en=datetime('now','localtime')
                WHERE id=:id
                """,
                {
                    "id": int(datos["id"]), "aseguradora": datos.get("aseguradora", ""),
                    "tipo_seguro": datos.get("tipo_seguro", "SALUD"),
                    "numero_poliza": datos.get("numero_poliza", ""),
                    "cobertura": datos.get("cobertura", ""),
                    "vigencia_inicio": datos.get("vigencia_inicio", ""),
                    "vigencia_fin": datos.get("vigencia_fin", ""),
                    "estado": datos.get("estado", "VIGENTE"),
                    "observaciones": datos.get("observaciones", ""),
                },
            )
            return int(datos["id"])
        cursor = con.execute(
            """
            INSERT INTO seguros (deportista_id, aseguradora, tipo_seguro, numero_poliza,
                                 cobertura, vigencia_inicio, vigencia_fin, estado, observaciones)
            VALUES (:deportista_id, :aseguradora, :tipo_seguro, :numero_poliza,
                    :cobertura, :vigencia_inicio, :vigencia_fin, :estado, :observaciones)
            """,
            {
                "deportista_id": deportista_id,
                "aseguradora": datos.get("aseguradora", ""),
                "tipo_seguro": datos.get("tipo_seguro", "SALUD"),
                "numero_poliza": datos.get("numero_poliza", ""),
                "cobertura": datos.get("cobertura", ""),
                "vigencia_inicio": datos.get("vigencia_inicio", ""),
                "vigencia_fin": datos.get("vigencia_fin", ""),
                "estado": datos.get("estado", "VIGENTE"),
                "observaciones": datos.get("observaciones", ""),
            },
        )
        return int(cursor.lastrowid or 0)


def obtener_seguro(seguro_id: int) -> sqlite3.Row | None:
    """Póliza con datos del deportista (JOIN)."""
    with _conexion() as con:
        return con.execute(
            """
            SELECT s.*, d.nombre, d.documento, d.deporte, d.categoria, d.sexo, d.car
            FROM seguros s JOIN deportistas d ON d.id = s.deportista_id
            WHERE s.id=?
            """,
            (seguro_id,),
        ).fetchone()


def listar_seguros(estado: str = "") -> list[sqlite3.Row]:
    """Listado de pólizas (opcionalmente filtradas por estado)."""
    condiciones, parametros = ["1=1"], []
    if estado:
        condiciones.append("s.estado=?")
        parametros.append(estado)
    sql = (
        "SELECT s.*, d.nombre, d.categoria, d.deporte FROM seguros s "
        "JOIN deportistas d ON d.id=s.deportista_id WHERE "
        + " AND ".join(condiciones) +
        " ORDER BY CASE s.estado WHEN 'VIGENTE' THEN 0 WHEN 'EN_TRAMITE' THEN 1 "
        "WHEN 'VENCIDO' THEN 2 ELSE 3 END, d.nombre"
    )
    with _conexion() as con:
        return list(con.execute(sql, parametros).fetchall())


def resumen_seguros() -> dict[str, int]:
    """Conteo de pólizas por estado (para análisis y panel)."""
    with _conexion() as con:
        filas = con.execute("SELECT estado, COUNT(*) AS n FROM seguros GROUP BY estado").fetchall()
    conteo = {estado: 0 for estado in ("VIGENTE", "VENCIDO", "EN_TRAMITE", "ANULADO")}
    for fila in filas:
        conteo[fila["estado"]] = int(fila["n"])
    return conteo


# ======================================================================
# v3.0 — Estadísticas para Análisis Deportivo y panel
# ======================================================================
def distribucion(columna: str, solo_activos: bool = True) -> list[sqlite3.Row]:
    """Cuenta deportistas agrupados por una columna ('sexo','categoria','deporte')."""
    if columna not in ("sexo", "categoria", "deporte", "car"):
        raise ValueError(f"Columna no permitida: {columna}")
    where = "WHERE activo=1" if solo_activos else ""
    with _conexion() as con:
        return list(
            con.execute(
                f"SELECT {columna} AS clave, COUNT(*) AS n FROM deportistas {where} "
                f"GROUP BY {columna} ORDER BY n DESC",
            ).fetchall()
        )


def matricula_por_categoria_sexo() -> list[sqlite3.Row]:
    """Matrícula activa cruzando categoría y sexo (D/V)."""
    with _conexion() as con:
        return list(
            con.execute(
                """
                SELECT categoria,
                       SUM(CASE WHEN sexo='D' THEN 1 ELSE 0 END) AS damas,
                       SUM(CASE WHEN sexo='V' THEN 1 ELSE 0 END) AS varones,
                       COUNT(*) AS total
                FROM deportistas WHERE activo=1
                GROUP BY categoria
                """
            ).fetchall()
        )


def promedios_por_periodo(limite: int = 6) -> list[sqlite3.Row]:
    """Promedios de asistencia/cumplimiento de los últimos N periodos con datos."""
    with _conexion() as con:
        return list(
            con.execute(
                """
                SELECT periodo, AVG(pct_asistencia) AS asistencia,
                       AVG(pct_cumplimiento) AS cumplimiento, COUNT(*) AS registros
                FROM registros_mensuales
                GROUP BY periodo ORDER BY periodo DESC LIMIT ?
                """,
                (int(limite),),
            ).fetchall()
        )


def imc_promedio_por_categoria() -> list[sqlite3.Row]:
    """IMC promedio de las evaluaciones de alimentación por categoría."""
    with _conexion() as con:
        return list(
            con.execute(
                """
                SELECT d.categoria AS clave, AVG(a.imc) AS imc_prom, COUNT(*) AS n
                FROM alimentacion a JOIN deportistas d ON d.id=a.deportista_id
                WHERE a.imc IS NOT NULL
                GROUP BY d.categoria ORDER BY d.categoria
                """
            ).fetchall()
        )
