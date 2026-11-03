# -*- coding: utf-8 -*-
"""Prueba integral de lógica del Sistema AT (sin GUI).

Cubre: esquema de BD, seed de deportistas/registros, generación de los 4
formatos Excel a partir de las plantillas reales, verificación del contenido
escrito en celdas clave, conversión a PDF (LibreOffice del sandbox) e
importación SISDENA (xlsx + csv).

Se ejecuta con la BD apuntando a un directorio temporal para no ensuciar
el proyecto entregado.
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

RAIZ = Path("/home/z/my-project/download/atletas_system")
sys.path.insert(0, str(RAIZ))

# --- redirigir BD/ firmas/ generados/ a un directorio temporal ---------------
TMP = Path(tempfile.mkdtemp(prefix="sistema_at_test_"))
import src.config as config  # noqa: E402

config.DATA_DIR = TMP / "data"; config.DATA_DIR.mkdir(parents=True, exist_ok=True)
config.FIRMAS_DIR = TMP / "firmas"; config.FIRMAS_DIR.mkdir(parents=True, exist_ok=True)
config.GENERADOS_DIR = TMP / "generados"; config.GENERADOS_DIR.mkdir(parents=True, exist_ok=True)
config.DB_PATH = config.DATA_DIR / "sistema_at.db"
config.FIRMAS_DIR.mkdir(exist_ok=True)

from src.database import init_db, get_connection, transaccion  # noqa: E402
from src.services import excel as excel  # noqa: E402
from src.services import pdf as pdf  # noqa: E402
from src.services import sisdena  # noqa: E402
from PIL import Image  # noqa: E402

import openpyxl  # noqa: E402

ERRORES: list[str] = []


def verificar(condicion: bool, mensaje: str) -> None:
    if condicion:
        print(f"  ✓ {mensaje}")
    else:
        ERRORES.append(mensaje)
        print(f"  ✗ FALLO: {mensaje}")


# ---------------------------------------------------------------------------
print("== 1. Esquema de base de datos ==")
init_db()
con = get_connection()
tablas = {f["name"] for f in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
con.close()
esperadas = {"deportistas", "registros_mensuales", "consolidados_at_f1", "planes_jut",
             "evaluaciones_jut", "firmas", "asignaciones_firma", "auditoria_firmas"}
verificar(esperadas <= tablas, f"tablas creadas: {sorted(esperadas & tablas)}")

# ---------------------------------------------------------------------------
print("== 2. Seed de datos (basado en entrenador.xlsx / AT-F1 de ejemplo) ==")
DEPORTISTAS = [
    ("COMPANOCCA CHECCO ELVIS EMERSON", "ATLETISMO", "DP", "U-20", "V", "CUSCO", "OMAR MOLINA CRESPO", "2026-10-05"),
    ("CUITO TACUSI NANCY", "ATLETISMO", "DP", "U-20", "D", "CUSCO", "JHON CUSI HUAMÁN", "2026-10-05"),
    ("FLORES LOPINTA KIMBERLY LISSETTE", "ATLETISMO", "DC", "U-18", "D", "CUSCO", "OMAR MOLINA CRESPO", "2026-10-05"),
    ("HUAMAN MATAMOROS LUIS GUSTAVO", "ATLETISMO", "DECAN", "MAY", "V", "CUSCO", "OMAR MOLINA CRESPO", "2026-10-05"),
    ("HUAMANI CHEQQUERA LIZARDO", "ATLETISMO", "DC", "U-20", "V", "CUSCO", "JHON CUSI HUAMÁN", "2026-10-05"),
    ("VELASQUEZ ROJAS DINA", "ATLETISMO", "DC", "U-20", "D", "CUSCO", "JHON CUSI HUAMÁN", "2025-01-10"),
    ("ROJAS HUILLCA JHONS FILDER", "ATLETISMO", "DP", "U-18", "V", "CUSCO", "PABLO MORALES ORTELANO", "2025-01-10"),
    ("DAZA QUISPE DEMETRIO", "PARA ATLETISMO", "DC", "MAY", "V", "CUSCO", "JHON CUSI HUAMÁN", "2025-01-10"),
]
with transaccion() as con:
    for d in DEPORTISTAS:
        con.execute(
            "INSERT INTO deportistas (nombres_apellidos, deporte, prueba_modalidad, categoria, sexo, region, entrenador, activo, fecha_ingreso) "
            "VALUES (?,?,?,?,?,?,?,1,?)", d)
    # un retirado en octubre (para la columna RETIROS de AT-F1)
    con.execute(
        "INSERT INTO deportistas (nombres_apellidos, deporte, prueba_modalidad, categoria, sexo, region, entrenador, activo, fecha_ingreso, fecha_retiro) "
        "VALUES ('RETIRADO PRUEBA UNO','ATLETISMO','DC','U-23','V','CUSCO','JHON CUSI HUAMÁN',0,'2024-05-01','2026-10-15')")

horario = {
    "MAÑANA": {d: "7:00-10:00" for d in ("LUNES", "MARTES", "MIERCOLES", "JUEVES", "VIERNES")} | {"SABADO": "6:00-11:00", "DOMINGO": "DESCANSO"},
    "TARDE": {d: "16:00-18:00" for d in ("LUNES", "MARTES", "MIERCOLES", "JUEVES", "VIERNES")} | {"SABADO": "DESCANSO", "DOMINGO": "DESCANSO"},
    "NOCHE": {d: "DESCANSO" for d in __import__("src").config.DIAS},
}
with transaccion() as con:
    for i, d in enumerate(DEPORTISTAS):
        dep_id = con.execute("SELECT id FROM deportistas WHERE nombres_apellidos=?", (d[0],)).fetchone()["id"]
        con.execute(
            """INSERT INTO registros_mensuales
               (deportista_id, periodo, entrenador, objetivos_metas, horario_json,
                pct_asistencia, pct_cumplimiento, resultados_test, detalle_preparacion,
                participacion_competencias, cumplimiento_objetivos, evaluacion_general, observaciones, estado)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?, 'borrador')""",
            (dep_id, "2026-10", d[6],
             f"Objetivos del mes para {d[0].title()}: consolidar la preparación específica.",
             json.dumps(horario, ensure_ascii=False),
             [0.99, 0.95, 0.98, 1.0, 0.94, 1.0, 0.95, 0.95][i],
             [0.99, 0.97, 0.98, 0.98, 0.94, 1.0, 0.97, 0.99][i],
             "Test de control: mejora de 2% en resistencia aeróbica.",
             "Etapa de preparación específica con miras al Campeonato Nacional de Mayores.",
             "Participó en el control interno del 15/10 (marca: 00:08:33.32).",
             "Se cumplieron los objetivos planteados.",
             "", "borrador"))

with transaccion() as con:
    con.execute(
        """INSERT INTO consolidados_at_f1
           (car, periodo, matriculas_json, valoracion_tecnica, dificultades, valoracion_medica,
            plan_profilactico, balance_nutricional, valoracion_car, aspectos_negativos, logros_car,
            otros_aspectos, estado)
           VALUES ('CUSCO','2026-10',?,?,?,?,?,?,?,?,?,?, 'borrador')""",
        (json.dumps({"U-18": {"retiros": 0, "ingresos": 1, "damas": 1, "varones": 1, "total": 2,
                              "sesiones": 20, "manana": "7:00 - 9:00", "tarde": "16:00 - 18:00"}}),
         "Alto nivel de cumplimiento (90–100%).", "Molestias físicas puntuales.",
         "Buen estado de salud general.", "Plan profiláctico cumplido.",
         "Balance energético adecuado.", "Funcionamiento adecuado y eficiente.",
         "Episodios puntuales de desabastecimiento de agua.",
         "Medallas en eventos internacionales.", "Gestión de la plaza de conductor.",))

with transaccion() as con:
    con.execute(
        """INSERT INTO planes_jut (jut_nombre, federacion, periodo, tareas_json, estado)
           VALUES ('JHON CUSI HUAMÁN','FEDERACIÓN DEPORTIVA PERUANA DE ATLETISMO','2026-09',?, 'borrador')""",
        (json.dumps([{"n": i + 1, "actividad": f"Tarea de planificación {i + 1}",
                      "fecha": f"{i + 2}/09", "hora": "8:00-10:00",
                      "lugar": "CAR Cusco", "observaciones": ""} for i in range(14)]),))
    con.execute(
        "INSERT INTO evaluaciones_jut (jut_nombre, periodo, estado) VALUES ('JHON CUSI HUAMÁN','2026-10','borrador')")

print("  ✓ datos sembrados (8 deportistas AT-F3, consolidado, plan con 14 tareas)")

# ---------------------------------------------------------------------------
print("== 3. Firmas (PNG con SHA-256) ==")
png = TMP / "firma_prueba.png"
Image.new("RGBA", (300, 100), (99, 102, 241, 255)).save(png)
import hashlib  # noqa: E402
with transaccion() as con:
    c1 = con.execute("INSERT INTO firmas (persona_nombre, rol, imagen_path, imagen_hash, activa, vigente_desde) VALUES (?,?,?,?,1,'2026-10-01')",
                     ("JHON CUSI HUAMÁN", "jut", str(png), hashlib.sha256(png.read_bytes()).hexdigest()))
    c2 = con.execute("INSERT INTO firmas (persona_nombre, rol, imagen_path, imagen_hash, activa, vigente_desde) VALUES (?,?,?,?,1,'2026-10-01')",
                     ("OMAR MOLINA CRESPO", "entrenador", str(png), hashlib.sha256(png.read_bytes()).hexdigest()))
    con.execute("INSERT INTO firmas (persona_nombre, rol, imagen_path, imagen_hash, activa, vigente_desde) VALUES (?,?,?,?,1,'2026-10-01')",
                ("PRESIDENTE PRUEBA", "presidente_fdn", str(png), hashlib.sha256(png.read_bytes()).hexdigest()))
print("  ✓ 3 firmas registradas")

# ---------------------------------------------------------------------------
print("== 4. Generación AT-F3 y verificación de celdas ==")
con = get_connection()
reg_id = con.execute("SELECT id FROM registros_mensuales LIMIT 1").fetchone()["id"]
con.close()
ruta_f3 = excel.generar_at_f3(reg_id)
wb = openpyxl.load_workbook(ruta_f3)
ws = wb.active
verificar(str(ws["D8"].value or "").startswith("COMPANOCCA"), f"AT-F3 D8 nombre = {ws['D8'].value!r}")
verificar(ws["D10"].value == "OCTUBRE", f"AT-F3 D10 mes = {ws['D10'].value!r}")
verificar(ws["J9"].value == "2026", f"AT-F3 J9 año = {ws['J9'].value!r}")
verificar(ws["B24"].value == "99%", f"AT-F3 B24 % asist = {ws['B24'].value!r}")
verificar(ws["B28"].value == "99%", f"AT-F3 B28 % cump = {ws['B28'].value!r}")
verificar(str(ws["B14"].value).startswith("Objetivos"), "AT-F3 B14 objetivos escritos")
verificar(ws["D19"].value == "7:00-10:00" and ws["J21"].value == "DESCANSO",
          f"AT-F3 horario D19={ws['D19'].value!r} J21={ws['J21'].value!r}")
verificar(len(ws._images) == 2, f"AT-F3 imágenes (logo+firma) = {len(ws._images)}")

print("== 5. Generación AT-F1 (agregado de AT-F3) ==")
con = get_connection()
cons_id = con.execute("SELECT id FROM consolidados_at_f1 LIMIT 1").fetchone()["id"]
con.close()
ruta_f1 = excel.generar_at_f1(cons_id)
wb = openpyxl.load_workbook(ruta_f1)
ws = wb.active
verificar(ws["C7"].value == "CUSCO", f"AT-F1 C7 car = {ws['C7'].value!r}")
verificar(ws["D13"].value == 1, f"AT-F1 D13 ingresos U-18 (desde matriculas_json) = {ws['D13'].value!r}")   # json sembrado: 1 ingreso
verificar(ws["C17"].value == 0, f"AT-F1 C17 retiros U-23 (sin datos en json) = {ws['C17'].value!r}")
verificar(ws["H24"].value == 0.99, f"AT-F1 H24 %asist = {ws['H24'].value!r}")
verificar(str(ws["B24"].value or "").startswith("COMPANOCCA"), f"AT-F1 B24 nombre = {ws['B24'].value!r}")
verificar(str(ws["A45"].value or "").startswith("Alto nivel"), "AT-F1 A45 valoración técnica")
verificar(len(ws._images) == 3, f"AT-F1 imágenes (logo + 2 firmas) = {len(ws._images)}")
# merges reubicados correctamente tras insertar? (no se insertó: 8 ≤ 20 cupos)
verificar("A45:J45" in {str(m) for m in ws.merged_cells.ranges}, "AT-F1 merge A45:J45 intacto")

print("== 6. Generación AT-F8 (14 tareas → supera las 10 filas, inserta filas) ==")
con = get_connection()
plan_id = con.execute("SELECT id FROM planes_jut LIMIT 1").fetchone()["id"]
con.close()
ruta_f8 = excel.generar_at_f8(plan_id)
wb = openpyxl.load_workbook(ruta_f8)
ws = wb.active
verificar(str(ws["A7"].value).replace("  ", " ").startswith("FEDERACION: FEDERACIÓN"), f"AT-F8 A7 = {ws['A7'].value!r}")
verificar("JHON CUSI" in str(ws["A8"].value), f"AT-F8 A8 = {ws['A8'].value!r}")
verificar("SETIEMBRE" in str(ws["A9"].value) and "2026" in str(ws["A9"].value), f"AT-F8 A9 = {ws['A9'].value!r}")
verificar(ws["A12"].value == 1 and ws["B12"].value == "Tarea de planificación 1", f"AT-F8 B12 = {ws['B12'].value!r}")
verificar(ws["B25"].value == "Tarea de planificación 14", f"AT-F8 B25 (fila insertada) = {ws['B25'].value!r}")
merges_f8 = {str(m) for m in ws.merged_cells.ranges}
verificar("C30:D30" in merges_f8 and "C31:D31" in merges_f8,
          f"AT-F8 firma reubicada: {sorted(m for m in merges_f8 if m.startswith('C3'))}")
verificar(len(ws._images) == 2, f"AT-F8 imágenes (logo+firma) = {len(ws._images)}")

print("== 7. Generación AT-F9 (reseña → inserta fila; promedios; calificación) ==")
with transaccion() as con:
    con.execute(
        """UPDATE evaluaciones_jut SET
             plan_id=(SELECT id FROM planes_jut WHERE id=?),
             tareas_planificadas=14, tareas_cumplidas=12, pct_cumplimiento=12.0/14,
             evaluacion_cumplimiento='Se cumplió la mayor parte de la programación; dos actividades se reprogramaron por actividades de campo.',
             resumen_reuniones='Se realizaron dos reuniones de trabajo educativo con los entrenadores sobre periodización y control de cargas.',
             resumen_dificultades_seccion2='Alimentación: optimizar horarios. Infraestructura: pista desgastada.',
             resumen_documentacion='Se revisó la documentación técnico-metodológica; falta estandarizar planes escritos.',
             cantidad_visitas=10, evaluacion_visitas='18/20',
             resumen_dificultades='Necesidades de mantenimiento y equipamiento tecnológico.',
             actualizacion_bd='SÍ', cumplimiento_calendario='SÍ', capacitaciones='SÍ',
             analisis_poa='Cumplimiento del 95% de los objetivos operativos.',
             otros_datos='Se requiere cubrir la plaza de conductor.',
             opinion_presidente='Se valora positivamente el trabajo del JUT.',
             calificacion_final='BUENO',
             pct_cumplimiento_promedio=(SELECT AVG(pct_cumplimiento) FROM registros_mensuales WHERE periodo='2026-10'),
             pct_asistencia_promedio=(SELECT AVG(pct_asistencia) FROM registros_mensuales WHERE periodo='2026-10')
           WHERE id=(SELECT id FROM evaluaciones_jut LIMIT 1)""",
        (plan_id,))
ev_id = get_connection().execute("SELECT id FROM evaluaciones_jut LIMIT 1").fetchone()["id"]
ruta_f9 = excel.generar_at_f9(ev_id)
wb = openpyxl.load_workbook(ruta_f9)
ws = wb.active
verificar(str(ws["D7"].value or "").startswith("JHON"), f"AT-F9 D7 nombres = {ws['D7'].value!r}")
verificar(ws["H9"].value == "OCTUBRE", f"AT-F9 H9 mes = {ws['H9'].value!r}")
verificar(ws["D12"].value == 14 and ws["F12"].value == 12, f"AT-F9 D12/F12 = {ws['D12'].value}/{ws['F12'].value}")
verificar(ws["H12"].value == "85.7%", f"AT-F9 H12 % = {ws['H12'].value!r}")
verificar(str(ws["B17"].value or "").startswith("Se realizaron dos reuniones"), f"AT-F9 B17 reseña insertada = {str(ws['B17'].value)[:40]!r}")
verificar(str(ws["B21"].value or "").startswith("Alimentación"), f"AT-F9 B21 dificultades secc.2 (desplazada) = {str(ws['B21'].value)[:30]!r}")
verificar(str(ws["B24"].value or "").startswith("Se revisó la documentación"), f"AT-F9 B24 documentación (desplazada) = {str(ws['B24'].value)[:30]!r}")
verificar(ws["G18"].value is not None and str(ws["G18"].value).endswith("%"), f"AT-F9 G18 %cumpl prom = {ws['G18'].value!r}")
verificar(ws["C49"].value == "X" and ws["C48"].value is None, f"AT-F9 BUENO marcado en C49 (desplazado) = {ws['C49'].value!r}")
merges_f9 = {str(m) for m in ws.merged_cells.ranges}
verificar("B17:J17" in merges_f9, f"AT-F9 merge reseña B17:J17 presente")
verificar(len(ws._images) == 3, f"AT-F9 imágenes (logo + 2 firmas) = {len(ws._images)}")

print("== 8. Conversión a PDF con LibreOffice ==")
for ruta in (ruta_f3, ruta_f1, ruta_f8, ruta_f9):
    ruta_pdf = pdf.excel_a_pdf(ruta)
    verificar(Path(ruta_pdf).exists() and Path(ruta_pdf).stat().st_size > 5000, f"PDF generado: {Path(ruta_pdf).name}")

print("== 9. Importación SISDENA (xlsx y csv) ==")
wb = openpyxl.Workbook(); wsx = wb.active
wsx.append(["Nombre del deportista", "Nombre de la competencia", "Fecha", "Prueba / Modalidad", "Resultado", "Puesto"])
wsx.append(["HUAMAN MATAMOROS LUIS GUSTAVO", "Campeonato Sudamericano Indoor 2026", "2026-02-28", "3000 m", "00:08:33.32", "1°"])
xlsx_sis = TMP / "sisdena.xlsx"; wb.save(xlsx_sis)
regs = sisdena.importar_competencias_desde_excel(xlsx_sis)
verificar(len(regs) == 1 and regs[0]["deportista"].startswith("HUAMAN") and regs[0]["puesto"] == "1°", f"SISDENA xlsx: {regs}")
csv_sis = TMP / "sisdena.csv"
csv_sis.write_text("Atleta;Evento;Fecha;Prueba;Marca;Posicion\nCUITO TACUSI NANCY;Copa Nacional;2026-03-15;5000 m;16:20.5;3°\n", encoding="utf-8")
regs = sisdena.importar_competencias_desde_excel(csv_sis)
verificar(len(regs) == 1 and regs[0]["competencia"] == "Copa Nacional" and regs[0]["resultado"] == "16:20.5", f"SISDENA csv: {regs}")

print("== 10. Registro de firmas aplicadas ==")
con = get_connection()
n = con.execute("SELECT COUNT(*) FROM asignaciones_firma").fetchone()[0]
a = con.execute("SELECT COUNT(*) FROM auditoria_firmas WHERE accion='aplicacion'").fetchone()[0]
con.close()
verificar(n >= 5, f"asignaciones_firma registradas = {n}")
verificar(a >= 5, f"auditoria_firmas (aplicacion) = {a}")

print()
print("GENERADOS EN:", config.GENERADOS_DIR)
if ERRORES:
    print(f"\n✗ {len(ERRORES)} FALLO(S):")
    for e in ERRORES:
        print("   -", e)
    sys.exit(1)
print("\n✓ TODAS LAS PRUEBAS DE LÓGICA PASARON")
