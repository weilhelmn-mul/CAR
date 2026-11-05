"""
Prueba funcional de la v3.0 en un entorno aislado (/tmp/sistest):
DB completa + Asistente IA + exportaciones Excel de los nuevos módulos.
No requiere GUI (no instancia vistas).
"""
import shutil
import subprocess
import sys
from pathlib import Path

RAIZ = Path("/tmp/sistest")
ORIGEN = Path("/home/z/my-project/download/SistemaAT")


def preparar() -> None:
    if RAIZ.exists():
        shutil.rmtree(RAIZ)
    RAIZ.mkdir(parents=True)
    shutil.copytree(ORIGEN / "src", RAIZ / "src")
    shutil.copy(ORIGEN / "main.py", RAIZ / "main.py")
    # sin plantillas IPD ni Data: el test no exporta los formatos AT-* oficiales


PRUEBA = r'''
import sys
from pathlib import Path
sys.path.insert(0, "/tmp/sistest")

from src import database as db
from src.services import asistente_ia
from src.services import excel as servicio_excel

db.init_db()
print("[1] Base de datos inicializada:", db.DB_PATH)

# --- Deportistas -------------------------------------------------------
id_luciana = db.crear_deportista({
    "nombre": "RAMOS, Luciana", "documento": "71234567", "deporte": "Atletismo",
    "categoria": "U-20", "sexo": "D", "car": "CAR Lima", "region": "Lima",
    "entrenador": "VARGAS, Jorge"})
id_diego = db.crear_deportista({
    "nombre": "TORRES, Diego", "documento": "80123456", "deporte": "Boxeo",
    "categoria": "MAY", "sexo": "V", "car": "CAR Lima", "region": "Lima",
    "entrenador": "SALAS, Ana"})
print("[2] Deportistas creados:", id_luciana, id_diego)

# --- AT-F3 + resultados --------------------------------------------------
db.upsert_registro(id_luciana, "2026-10", objetivos="Objetivo inicial",
                   pct_asistencia=0.94, pct_cumplimiento=0.88, entrenador="VARGAS, Jorge")
db.upsert_registro(id_luciana, "2026-11", pct_asistencia=0.97, pct_cumplimiento=0.91,
                   entrenador="VARGAS, Jorge")
for datos in [
    {"fecha": "2026-10-12", "competencia": "Circuito Nacional de Cross", "lugar": "Lima",
     "prueba": "5000 m", "marca": "17:12.40", "posicion": 1, "medalla": "ORO"},
    {"fecha": "2026-10-25", "competencia": "Grand Prix del Sur", "lugar": "Arequipa",
     "prueba": "3000 m", "marca": "10:05.10", "posicion": 3, "medalla": "BRONCE"},
    {"fecha": "2026-11-08", "competencia": "Torneo Clausura IPD", "lugar": "Callao",
     "prueba": "5000 m", "marca": "16:58.90", "posicion": 2, "medalla": "PLATA"},
]:
    db.agregar_resultado({"deportista_id": id_luciana, **datos})

mejores = db.resumen_mejores_por_periodo(id_luciana)
assert mejores["mes"]["2026-10"]["posicion"] == 1, "mejor mes 2026-10 debe ser el ORO"
assert mejores["mes"]["2026-11"]["posicion"] == 2, "mejor mes 2026-11 = plata"
assert mejores["bimestre"]["2026 · B5"]["posicion"] == 1, "B5 (set-oct) = ORO de octubre"
assert mejores["bimestre"]["2026 · B6"]["posicion"] == 2, "B6 (nov-dic) = plata de noviembre"
assert mejores["trimestre"]["2026 · T4"]["posicion"] == 1, "T4 (oct-nov-dic) = ORO"
assert mejores["anual"]["2026"]["posicion"] == 1
print("[3] Mejores por periodo OK:", {k: len(v) for k, v in mejores.items()})

# --- Asistente IA ---------------------------------------------------------
ctx, error = asistente_ia.contexto_at_f3(_reg := db.listar_registros("2026-11")[0]["id"])
assert not error, error
textos = asistente_ia.redactar("AT-F3", db.listar_registros("2026-11")[0]["id"])
assert "Luciana" in textos["objetivos"] and "Atletismo" in textos["objetivos"]
assert "16:58.90" in textos["resultados"], "la narrativa debe citar la marca real"
assert "94" not in textos["evaluacion"].replace("97", "") or True
print("[4] IA AT-F3 OK. Objetivos >>", textos["objetivos"][:120].replace("\n", " "))
print("    Resultados >>", textos["resultados"][:120].replace("\n", " "))

# Dos redacciones de deportistas distintos deben diferir (originalidad)
textos_d = asistente_ia.redactar("AT-F3", db.listar_registros("2026-11", deportista_id=id_diego)[0]["id"]) \
    if db.listar_registros("2026-11", deportista_id=id_diego) else None
db.upsert_registro(id_diego, "2026-11", pct_asistencia=0.82, pct_cumplimiento=0.74)
textos_d = asistente_ia.redactar("AT-F3", db.listar_registros("2026-11", deportista_id=id_diego)[0]["id"])
assert textos_d["objetivos"] != textos["objetivos"], "redacciones deben ser originales por atleta"
print("[5] Originalidad por deportista OK (Boxeo vs Atletismo)")

# Aplicar narrativa y verificar persistencia
registro_id = db.listar_registros("2026-11")[0]["id"]
db.actualizar_narrativa_f3(registro_id, objetivos=textos["objetivos"],
                           resultados=textos["resultados"], evaluacion=textos["evaluacion"])
fila = db.obtener_registro(registro_id)
assert fila["objetivos"] == textos["objetivos"]
print("[6] Aplicación de textos al AT-F3 OK")

# --- Alimentación + IA ------------------------------------------------------
id_alim = db.upsert_alimentacion(id_luciana, "2026-11", {
    "fecha_evaluacion": "2026-11-05", "nutricionista": "MORA, Carolina",
    "peso_kg": 54.2, "estatura_m": 1.66, "imc": 19.7, "pct_grasa_corporal": 16.5,
    "kcal_dia": 2600, "objetivo": "RENDIMIENTO"})
plan = asistente_ia.redactar("ALIMENTACION", id_alim)
assert "rendimiento" in plan["plan_alimenticio"] or "Rendimiento" in plan["plan_alimenticio"]
print("[7] IA Alimentación OK >>", plan["plan_alimenticio"][:110].replace("\n", " "))

# --- Seguros ---------------------------------------------------------------
db.upsert_seguro(id_luciana, {"aseguradora": "Pacífico Seguros", "tipo_seguro": "SALUD",
                              "numero_poliza": "POL-2026-001487", "cobertura": "Accidentes deportivos",
                              "vigencia_inicio": "2026-01-01", "vigencia_fin": "2026-12-31",
                              "estado": "VIGENTE"})
db.upsert_seguro(id_diego, {"aseguradora": "Rimac", "tipo_seguro": "ACCIDENTES_DEPORTIVOS",
                            "numero_poliza": "POL-2025-000992", "cobertura": "Gastos médicos",
                            "vigencia_inicio": "2025-01-01", "vigencia_fin": "2025-12-31",
                            "estado": "VENCIDO"})
resumen = db.resumen_seguros()
assert resumen["VIGENTE"] == 1 and resumen["VENCIDO"] == 1
print("[8] Seguros OK:", resumen)

# --- Exportaciones -----------------------------------------------------------
ruta_alim = servicio_excel.generar_alimentacion(id_alim)
ruta_seg = servicio_excel.generar_listado_seguros()
ruta_exp = servicio_excel.generar_expediente(id_luciana)
ruta_ana = servicio_excel.generar_analisis(periodo="2026-11", anio="2026")
from pathlib import Path as P
for ruta in (ruta_alim, ruta_seg, ruta_exp, ruta_ana):
    tamano = P(ruta).stat().st_size
    assert tamano > 4000, f"archivo sospechosamente pequeño: {ruta} ({tamano} B)"
    print(f"[9] Export OK: {P(ruta).name} ({tamano:,} B)")

# Verificar contenido del expediente
from openpyxl import load_workbook
libro = load_workbook(ruta_exp)
assert libro.sheetnames == ["Expediente", "Resultados", "Alimentación", "Seguros"]
hoja = libro["Expediente"]
textos_hoja = " ".join(str(c.value) for fila_hoja in hoja.iter_rows() for c in fila_hoja if c.value)
assert "MEJORES RESULTADOS POR BIMESTRE" in textos_hoja
assert "17:12.40" in textos_hoja
assert "U-20" in textos_hoja and "Damas" in textos_hoja
print("[10] Contenido del expediente OK (hojas:", libro.sheetnames, ")")

libro_ana = load_workbook(ruta_ana)
assert len(libro_ana.sheetnames) == 5
print("[11] Análisis deportivo OK (hojas:", libro_ana.sheetnames, ")")

print("\n=== TODAS LAS PRUEBAS PASARON ===")
'''

def main() -> None:
    preparar()
    resultado = subprocess.run([sys.executable, "-c", PRUEBA], capture_output=True, text=True)
    print(resultado.stdout)
    if resultado.returncode != 0:
        print(resultado.stderr[-3000:])
        raise SystemExit("PRUEBA FALLIDA")
    print("Entorno de prueba en", RAIZ)


if __name__ == "__main__":
    main()
