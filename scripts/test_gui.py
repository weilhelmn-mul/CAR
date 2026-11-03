# -*- coding: utf-8 -*-
"""Prueba de arranque de la GUI del Sistema AT bajo Xvfb (sin interacción).

Verifica que la ventana principal se construye, que las 7 vistas se crean sin
errores, que el diálogo de deportista abre/cierra y que el selector de
deportistas del AT-F3 carga registros.
"""
import sys
import tempfile
from pathlib import Path

RAIZ = Path("/home/z/my-project/download/atletas_system")
sys.path.insert(0, str(RAIZ))

TMP = Path(tempfile.mkdtemp(prefix="sistema_at_gui_"))
import src.config as config  # noqa: E402

config.DATA_DIR = TMP / "data"; config.DATA_DIR.mkdir(parents=True, exist_ok=True)
config.FIRMAS_DIR = TMP / "firmas"; config.FIRMAS_DIR.mkdir(parents=True, exist_ok=True)
config.GENERADOS_DIR = TMP / "generados"; config.GENERADOS_DIR.mkdir(parents=True, exist_ok=True)
config.DB_PATH = config.DATA_DIR / "sistema_at.db"

from src import theme  # noqa: E402
from src.database import init_db, get_connection, transaccion  # noqa: E402

theme.aplicar_tema()
init_db()

# --- datos mínimos ----------------------------------------------------------
with transaccion() as con:
    con.execute(
        "INSERT INTO deportistas (nombres_apellidos, deporte, prueba_modalidad, categoria, sexo, region, entrenador, activo)"
        " VALUES ('DEPORTISTA PRUEBA GUI','ATLETISMO','DC','U-20','V','CUSCO','ENTRENADOR PRUEBA',1)")
    con.execute(
        "INSERT INTO registros_mensuales (deportista_id, periodo, pct_asistencia, pct_cumplimiento)"
        " VALUES (1, ?, 0.9, 0.95)", (config.periodo_actual(),))
    con.execute(
        "INSERT INTO planes_jut (jut_nombre, federacion, periodo, tareas_json)"
        " VALUES ('JUT PRUEBA', 'FEDERACIÓN PRUEBA', ?, ?)",
        (config.periodo_anterior(config.periodo_actual(), 1),
         '[{"n":1,"actividad":"Visita técnica","fecha":"05","hora":"9:00","lugar":"CAR","observaciones":""}]'))

from src.main_window import MainWindow  # noqa: E402

errores: list[str] = []
app = MainWindow()
app.update()

# --- navegar por las 7 vistas ------------------------------------------------
for clave in ("dashboard", "deportistas", "at_f3", "at_f1", "at_f8", "at_f9", "firmas"):
    try:
        app.show_view(clave)
        app.update()
        print(f"  ✓ vista construida: {clave}")
    except Exception as e:
        errores.append(f"vista {clave}: {e!r}")
        print(f"  ✗ vista {clave}: {e!r}")

# --- diálogo de deportista ----------------------------------------------------
app.show_view("deportistas")
app.update()
from src.views.deportistas import DeportistaDialog  # noqa: E402
dialogo = DeportistaDialog(app, datos=None, al_guardar=lambda: None)
app.update()
print("  ✓ diálogo DeportistaDialog abre")
dialogo.destroy()

# --- AT-F9 carga plan del período anterior -----------------------------------
app.show_view("at_f9")
app.update()
vista = app.vista
# escribir JUT y recargar
try:
    vista.f_jut.set("JUT PRUEBA")
    vista._cargar()
    app.update()
    print(f"  ✓ AT-F9 carga plan: {vista.lbl_plan.cget('text')[:60]!r}")
except Exception as e:
    errores.append(f"at_f9 carga: {e!r}")
    print(f"  ✗ AT-F9 carga plan: {e!r}")

# --- AT-F3 carga registro ------------------------------------------------------
app.show_view("at_f3")
app.update()
try:
    vista = app.vista
    app.update()
    print(f"  ✓ AT-F3 cargado: registro_id={vista.registro_id}, %asist={vista.f_asistencia.get()!r}")
except Exception as e:
    errores.append(f"at_f3 carga: {e!r}")
    print(f"  ✗ AT-F3: {e!r}")

app.destroy()
if errores:
    print(f"\n✗ {len(errores)} fallo(s) de GUI")
    sys.exit(1)
print("\n✓ GUI OK bajo Xvfb")
