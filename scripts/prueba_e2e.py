"""prueba_e2e.py — Prueba de extremo a extremo de los servicios del Sistema AT
(sin interfaz gráfica): base de datos, 4 generadores Excel, SISDENA y firmas."""
from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path("/home/z/my-project/download/SistemaAT")
sys.path.insert(0, str(RAIZ))

from src import database as db  # noqa: E402
from src.services import excel as sx  # noqa: E402
from src.services import sisdena as ss  # noqa: E402
from openpyxl import load_workbook  # noqa: E402


def verificar(ruta: str, celdas: dict[str, object]) -> None:
    ws = load_workbook(ruta).active
    for celda, esperado in celdas.items():
        valor = ws[celda].value
        if esperado is None:
            continue
        if isinstance(esperado, float):
            ok = valor is not None and abs(float(valor) - esperado) < 1e-6
        else:
            ok = str(valor or "").strip() == str(esperado).strip() or str(esperado) in str(valor or "")
        estado = "OK " if ok else "FAIL"
        print(f"   [{estado}] {Path(ruta).name} {celda} = {valor!r} (esperado: {esperado!r})")
        assert ok, f"Celda {celda} incorrecta en {ruta}"


def main() -> None:
    # 1) Base de datos limpia -------------------------------------------------
    db.DB_PATH = str(RAIZ / "data" / "sistema_at.db")
    Path(db.DB_PATH).unlink(missing_ok=True)
    db.init_db()
    print("== init_db OK ==")

    # 2) Firmas ---------------------------------------------------------------
    png = bytes.fromhex("89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
                        "0000000d49444154789c626001000000ffff03000006000557bfabd4000000004945"
                        "4e44ae426082")
    id_firma_entrenador = db.registrar_firma("entrenador", "Carlos Ríos (Entrenador)", png)
    id_firma_jut = db.registrar_firma("jut", "Ana Torres (JUT)", png)
    db.registrar_firma("presidente_fdn", "Luis Vega (Presidente FDN)", png)
    assert db.firma_activa("entrenador") is not None
    print("== firmas registradas con SHA-256 OK ==")

    # 3) Deportistas ----------------------------------------------------------
    id_dep1 = db.crear_deportista({
        "nombre": "QUISPE FLORES, María", "documento": "71234567", "deporte": "Atletismo",
        "categoria": "U-20", "sexo": "D", "car": "CAR Lima", "region": "Lima",
        "entrenador": "Carlos Ríos"})
    id_dep2 = db.crear_deportista({
        "nombre": "SALAS DIAZ, Jorge", "documento": "71234568", "deporte": "Natación",
        "categoria": "U-23", "sexo": "V", "car": "CAR Lima", "region": "Lima",
        "entrenador": "Carlos Ríos"})
    print("== deportistas OK ==")

    # 4) Registros AT-F3 ------------------------------------------------------
    assert sx.parsear_porcentaje("95") == 0.95
    assert sx.parsear_porcentaje("95%") == 0.95
    assert sx.parsear_porcentaje("0.95") == 0.95
    assert sx.parsear_porcentaje("0,5") == 0.5
    assert sx.parsear_porcentaje("") is None
    print("== parsear_porcentaje OK ==")

    r1 = db.upsert_registro(id_dep1, "2026-01", objetivos="Bajar marca 100m a 12.4s",
                            pct_asistencia=0.92, pct_cumplimiento=0.88,
                            resultados="2º lugar nacional sub-20",
                            horario=["Lun 06:00-08:00 Pista", "Mié 06:00-08:00 Gimnasio",
                                     "Vie 16:00-18:00 Pista"],
                            evaluacion="Buena progresión técnica", entrenador="Carlos Ríos")
    db.upsert_registro(id_dep2, "2026-01", objetivos="Mejorar tiempo 200m",
                       pct_asistencia=0.85, pct_cumplimiento=0.80,
                       resultados="Clasificado regional", entrenador="Carlos Ríos")
    # Upsert (mismo periodo) debe actualizar y NO duplicar:
    r1_duplicado = db.upsert_registro(id_dep1, "2026-01", pct_asistencia=0.95,
                                      pct_cumplimiento=0.90, objetivos="Objetivo actualizado")
    assert r1 == r1_duplicado, "El upsert debe conservar el mismo id"
    reg = db.obtener_registro(r1)
    assert abs(reg["pct_asistencia"] - 0.95) < 1e-6
    assert reg["objetivos"] == "Objetivo actualizado"
    print("== upsert AT-F3 (ON CONFLICT) OK ==")

    # 5) SISDENA ---------------------------------------------------------------
    from openpyxl import Workbook

    ruta_sisdena = RAIZ / "data" / "reporte_sisdena_prueba.xlsx"
    libro = Workbook()
    hoja = libro.active
    hoja.append(["Deportista", "Competencia", "Fecha", "Prueba", "Resultado", "Puesto"])
    hoja.append(["QUISPE FLORES, María", "Campeonato Nacional Sub-20", "18/01/2026",
                 "100 m planos", "Finalista", 2])
    hoja.append(["OTRO DEPORTISTA", "Otra competencia", "20/01/2026", "Salto largo", "—", 5])
    libro.save(ruta_sisdena)
    competencias = ss.importar_competencias_desde_excel(ruta_sisdena)
    assert len(competencias) == 2
    db.agregar_pruebas_sisdena(id_dep1, "2026-01", [competencias[0]])
    db.agregar_pruebas_sisdena(id_dep1, "2026-01", [competencias[0]])  # sin duplicar
    reg = db.obtener_registro(r1)
    pruebas = __import__("json").loads(reg["pruebas_sisdena_json"])
    assert len(pruebas) == 1, "No debe duplicar la misma competencia"
    print("== importación SISDENA OK ==")

    # 6) Generar AT-F3 ----------------------------------------------------------
    ruta_f3 = sx.generar_at_f3(r1)
    verificar(ruta_f3, {"C10": "QUISPE FLORES, María", "C11": "Atletismo", "J11": "2026",
                        "C30": 0.95, "C35": 0.90})
    print("== AT-F3 generado:", Path(ruta_f3).name)

    # 7) Consolidado AT-F1 ------------------------------------------------------
    id_f1 = db.upsert_consolidado("CAR Lima", "2026-01", {
        "matriculas": {"altas": {"U-20": 2, "U-23": 1}, "bajas": {"JUV": 1}},
        "eval_medica": "Sin lesiones activas", "eval_nutricion": "Plan alimentario al día",
        "eval_car": "Cumplimiento general satisfactorio", "jut_nombre": "Ana Torres"})
    ruta_f1 = sx.generar_at_f1(id_f1)
    ws_f1 = load_workbook(ruta_f1).active
    assert ws_f1["C15"].value == 2 and ws_f1["D15"].value == 0 and ws_f1["E15"].value == 2  # U-20
    assert ws_f1["C16"].value == 1 and ws_f1["E16"].value == 1  # U-23
    assert ws_f1["B22"].value == "QUISPE FLORES, María" and abs(ws_f1["D22"].value - 0.95) < 1e-6
    print("== AT-F1 generado con agregación automática:", Path(ruta_f1).name)

    # 8) Plan AT-F8 -------------------------------------------------------------
    tareas = [
        {"n": 1, "actividad": "Control técnico de atletismo", "fecha": "05/02", "hora": "09:00",
         "lugar": "Pista CAR", "obs": "Con entrenadores"},
        {"n": 2, "actividad": "Reunión con DINADAF", "fecha": "12/02", "hora": "15:00",
         "lugar": "Sede IPD", "obs": ""},
        {"n": 3, "actividad": "Visita a filial Callao", "fecha": "25/02", "hora": "10:00",
         "lugar": "Callao", "obs": "Evaluar altas"},
    ]
    id_plan = db.upsert_plan("Ana Torres", "2026-02", "CAR Lima", tareas)
    ruta_f8 = sx.generar_at_f8(id_plan)
    ws_f8 = load_workbook(ruta_f8).active
    assert ws_f8["C17"].value == "Control técnico de atletismo"
    assert ws_f8["F19"].value == "Callao"
    print("== AT-F8 generado:", Path(ruta_f8).name)

    # 9) Evaluación AT-F9 --------------------------------------------------------
    promedios = db.promedios_periodo("CAR Lima", "2026-01")
    assert promedios["n"] == 2
    id_eval = db.upsert_evaluacion(id_plan, "2026-02", {
        "pct_asistencia_prom": promedios["pct_asistencia"],
        "pct_cumplimiento_prom": promedios["pct_cumplimiento"],
        "tareas_programadas": 3, "tareas_cumplidas": 2, "pct_tareas": 2 / 3,
        "fecha_visita": "25/02/2026", "realizado_por": "Ana Torres",
        "obs_visita": "Se verificaron 2 de 3 tareas; la visita a Callao se reprogramó.",
        "calificacion_final": "BUENO", "opinion_presidente": "Continuar con el esquema actual."})
    ruta_f9 = sx.generar_at_f9(id_eval)
    verificar(ruta_f9, {"C30": "BUENO", "C20": 3, "C21": 2})
    print("== AT-F9 generado:", Path(ruta_f9).name)

    # 10) Auditoría de firmas ------------------------------------------------------
    with db._conexion() as con:
        usos = con.execute("SELECT COUNT(*) AS n FROM auditoria_firmas WHERE accion='uso'").fetchone()["n"]
    assert usos >= 5, f"Se esperaban usos de firma auditados, hay {usos}"
    print(f"== auditoría de firmas OK ({usos} usos registrados) ==")

    print("\n** E2E COMPLETO: TODAS LAS PRUEBAS PASARON **")


if __name__ == "__main__":
    main()
