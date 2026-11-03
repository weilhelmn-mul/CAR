"""
Verificación EN FRÍO de SistemaAT_Portable_USB_v1.0.zip:
  Fase 1: extracción limpia + estructura (PE del exe, runtime Python, paquetes)
  Fase 2: prueba funcional del código embarcado con Python 3.12.16 (la misma
          versión que lleva dentro): config portable, BD de 8 tablas, cadena de
          imports completa, generación AT-F3 end-to-end con la plantilla real.
El ZIP NO se modifica.
"""
import hashlib
import shutil
import struct
import subprocess
import sys
import zipfile
from pathlib import Path

RAIZ = Path("/home/z/my-project/download")
ZIP = RAIZ / "SistemaAT_Portable_USB_v1.0.zip"
DEST = Path("/tmp/verificacion")
PY_TEST = "/tmp/venv_test/bin/python"

ok: list[str] = []
fallos: list[str] = []

def check(cond: bool, descripcion: str) -> None:
    (ok if cond else fallos).append(("✔ " if cond else "✘ ") + descripcion)

# ============================================================ FASE 1
if DEST.exists():
    shutil.rmtree(DEST)
DEST.mkdir(parents=True)
with zipfile.ZipFile(ZIP) as z:
    check(z.testzip() is None, "Integridad interna del ZIP (testzip)")
    z.extractall(DEST)

app = DEST / "SistemaAT_Portable"

# --- Ejecutable lanzador (PE x64, subsistema GUI) ---
raw = (app / "SistemaAT.exe").read_bytes()
e_lfanew = struct.unpack("<I", raw[0x3C:0x40])[0]
maquina = struct.unpack("<H", raw[e_lfanew + 4:e_lfanew + 6])[0]
subsys = struct.unpack("<H", raw[e_lfanew + 24 + 68:e_lfanew + 24 + 70])[0]
check(raw[:2] == b"MZ" and maquina == 0x8664, f"SistemaAT.exe es PE x64 válido (MZ, máquina=0x{maquina:X})")
check(subsys == 2, f"SistemaAT.exe es GUI sin ventana de consola (subsystem={subsys})")

# --- Runtime Python incluido ---
for rel in ("py/pythonw.exe", "py/python.exe", "py/python312.dll", "py/python3.dll",
            "py/vcruntime140.dll", "py/vcruntime140_1.dll",
            "py/DLLs/_tkinter.pyd", "py/DLLs/tcl86t.dll", "py/DLLs/tk86t.dll",
            "py/tcl/tcl8.6/init.tcl", "py/tcl/tk8.6/tk.tcl",
            "py/Lib/tkinter/__init__.py"):
    check((app / rel).exists(), f"Runtime: {rel}")

# --- Paquetes preinstalados (exactos a requirements.txt) ---
for rel in ("py/Lib/site-packages/customtkinter/__init__.py",
            "py/Lib/site-packages/customtkinter/assets/themes/blue.json",
            "py/Lib/site-packages/darkdetect/__init__.py",
            "py/Lib/site-packages/PIL/_imaging.cp312-win_amd64.pyd",
            "py/Lib/site-packages/openpyxl/__init__.py",
            "py/Lib/site-packages/et_xmlfile/__init__.py",
            "py/Lib/site-packages/pywin32.pth",
            "py/Lib/site-packages/pywin32_system32/pywintypes312.dll",
            "py/Lib/site-packages/win32/win32api.pyd"):
    check((app / rel).exists(), f"Dependencia: {rel}")

# --- Aplicación ---
plantillas = sorted(p.name for p in (app / "templates").glob("*.xlsx"))
esperadas = sorted(["PLANTILLA FORMATO AT-F3.xlsx", "PLANTILLA FORMATO AT-F1 CAR.xlsx",
                    "PLANTILLA FORMATO ATF8.xlsx", "PLANTILLA FORMATO AT -F9.xlsx"])
check(plantillas == esperadas, f"4 plantillas oficiales con nombres exactos: {plantillas}")
for rel in ("main.py", "PORTABLE", "LEEME_PORTABLE.txt", "CONSOLA_DEBUG.bat",
            "assets/icon.ico", "src/config.py", "src/main_window.py", "src/database.py",
            "src/theme.py", "src/widgets.py",
            "src/views/dashboard.py", "src/views/deportistas.py", "src/views/at_f3.py",
            "src/views/at_f1.py", "src/views/at_f8.py", "src/views/at_f9.py",
            "src/views/firmas.py",
            "src/services/excel.py", "src/services/pdf.py", "src/services/sisdena.py",
            "src/__init__.py", "src/views/__init__.py", "src/services/__init__.py"):
    check((app / rel).exists(), f"Aplicación: {rel}")
check('if (raiz / "PORTABLE").exists():' in (app / "src/config.py").read_text(encoding="utf-8"),
      "config.py con lógica de marcador PORTABLE (datos junto al exe)")

# ============================================================ FASE 2
PRUEBA = r'''
import sys, json
sys.path.insert(0, ".")
from src import config, database as db
from src.services import excel, pdf
from src.services.excel import parsear_porcentaje

assert config.PORTABLE is True, f"PORTABLE={config.PORTABLE}"
assert str(config.DATA_DIR).endswith("SistemaAT_Portable/Data"), config.DATA_DIR
print("RESULT config_portable: OK ·", "Data =", config.DATA_DIR.name)

db.init_db()
with db._conexion() as con:
    tablas = sorted(f[0] for f in con.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"))
esperadas = sorted(["deportistas", "registros_mensuales", "consolidados_at_f1",
                    "planes_jut", "evaluaciones_jut", "firmas",
                    "asignaciones_firma", "auditoria_firmas"])
assert tablas == esperadas, tablas
print("RESULT bd_8_tablas: OK")

# % reglas
for texto, esperado in (("95", 0.95), ("95%", 0.95), ("0.95", 0.95)):
    assert abs(parsear_porcentaje(texto) - esperado) < 1e-9, (texto, parsear_porcentaje(texto))
print("RESULT parseo_porcentajes: OK (95 / 95% / 0.95 -> 0.95)")

# Datos de prueba + generación AT-F3 end-to-end
with db._conexion() as con:
    cur = con.execute(
        "INSERT INTO deportistas (nombre, documento, deporte, categoria, sexo, car, region, entrenador)"
        " VALUES ('PEREZ QUISPE, Maria', 'DNI 70112233', 'Atletismo', 'U-20', 'D',"
        " 'CAR-Lima', 'Lima', 'Tec. J. ROJAS')")
    did = cur.lastrowid
    con.execute(
        "INSERT INTO registros_mensuales (deportista_id, periodo, objetivos, pct_asistencia,"
        " pct_cumplimiento, resultados, pruebas_sisdena_json, horario_json, evaluacion, entrenador)"
        " VALUES (?, '2026-10', 'Preparación física y técnica de salida', 0.92, 0.88,"
        " '1er puesto 100m llanos - Meet Nacional', ?, ?, 'Avance satisfactorio', 'Tec. J. ROJAS')",
        (did, json.dumps([{"fecha": "2026-10-18", "competencia": "Meet Nacional",
                           "prueba": "100m", "resultado": "12.31s", "puesto": "1"}]),
         json.dumps(["LUN-VIE 06:00-09:00 pista", "SAB 08:00-11:00 gimnasio"])))
    con.commit()

ruta = excel.generar_at_f3(1)
assert ruta, "generar_at_f3 no devolvió ruta"
print("RESULT generacion_at_f3: OK ->", ruta.split("/")[-1])

import openpyxl
wb = openpyxl.load_workbook(ruta)
ws = wb.active
celdas = {"C10": "PEREZ QUISPE, Maria", "C11": "Atletismo", "C12": "Octubre 2026",
          "C30": 0.92, "C35": 0.88}
for celda, esperado in celdas.items():
    valor = ws[celda].value
    assert valor == esperado, (celda, valor, esperado)
print("RESULT celdas_plantilla: OK (C10 nombre, C11 deporte, C12 mes, C30/C35 %)")

# Cadena completa de imports de la interfaz (sin abrir ventana)
import src.main_window, src.widgets, src.theme
import src.views.dashboard, src.views.deportistas, src.views.at_f3
import src.views.at_f1, src.views.at_f8, src.views.at_f9, src.views.firmas
print("RESULT imports_interfaz: OK (main_window + 7 vistas + widgets)")

# PDF (opcional): LibreOffice presente -> conversión real; ausente -> error controlado
try:
    ruta_pdf = pdf.excel_a_pdf(ruta)
    print("RESULT pdf:", "OK ->", Path(ruta_pdf).name)
except Exception as e:
    print("RESULT pdf: CONTROLADO ->", type(e).__name__)
'''

r = subprocess.run([PY_TEST, "-c", PRUEBA], cwd=app, capture_output=True,
                   text=True, timeout=420)
print("--- salida prueba funcional ---")
print(r.stdout)
if r.returncode != 0:
    fallos.append("✘ Prueba funcional del código embarcado (ver detalle abajo)")
    print(r.stderr)

# ============================================================ Resumen
sha = hashlib.sha256(ZIP.read_bytes()).hexdigest()
print("=" * 64)
for linea in ok:
    print(linea)
if fallos:
    print("---- FALLOS ----")
    for linea in fallos:
        print(linea)
print("=" * 64)
print(f"VERIFICACIÓN: {len(ok)} correctas · {len(fallos)} fallos")
print(f"SHA-256: {sha}")
print(f"Tamaño:  {ZIP.stat().st_size:,} bytes ({ZIP.stat().st_size/1e6:.1f} MB)")
