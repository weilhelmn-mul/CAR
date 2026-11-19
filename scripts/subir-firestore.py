#!/usr/bin/env python3
"""Sube la base SQLite (db/custom.db) a Firestore (proyecto car-cusco).
Diseñado para Cloud Shell (no necesita claves de cuenta de servicio):

    git clone --depth 1 https://github.com/weilhelmn-mul/CAR.git car-mig && cd car-mig && python3 scripts/subir-firestore.py

Variables opcionales: FIREBASE_PROJECT (default: car-cusco), DB_PATH (default: db/custom.db)
Prueba local sin subir: python3 scripts/subir-firestore.py --dry-run
"""
import json, os, sqlite3, subprocess, sys, urllib.request, urllib.error

DB_PATH = os.environ.get("DB_PATH", "db/custom.db")
PROJECT = os.environ.get("FIREBASE_PROJECT", "car-cusco")
DRY = "--dry-run" in sys.argv

TABLAS = {
    "Deportista":   "deportistas",
    "Resultado":    "resultados",
    "Alimentacion": "alimentaciones",
    "Firma":        "firmas",
    "FormatoF1":    "formatos_f1",
    "FormatoF3":    "formatos_f3",
    "FormatoF8":    "formatos_f8",
    "FormatoF9":    "formatos_f9",
}
BOOL = {
    "Deportista":   {"pad", "activo", "retirado"},
    "Alimentacion": {"incluido"},
    "Firma":        {"activo"},
    "FormatoF9":    {"baseDatos", "calendario", "capacitaciones"},
}
JSONF = {
    "FormatoF8": {"actividades"},
    "FormatoF1": {"matriculas", "textos", "filas"},
    "FormatoF3": {"horario"},
}

def typed(tabla, nombre, v):
    """Convierte un valor SQLite en typed value de Firestore REST."""
    if v is None:
        return {"nullValue": None}
    if nombre in BOOL.get(tabla, set()):
        return {"booleanValue": bool(v)}
    if nombre in JSONF.get(tabla, set()) and isinstance(v, str):
        try:
            v = json.loads(v)
        except Exception:
            pass
    if isinstance(v, bool):
        return {"booleanValue": v}
    if isinstance(v, int):
        return {"integerValue": str(v)}
    if isinstance(v, float):
        return {"doubleValue": v}
    if isinstance(v, str):
        return {"stringValue": v}
    if isinstance(v, dict):
        return {"mapValue": {"fields": {k: typed(tabla, k, x) for k, x in v.items()}}}
    if isinstance(v, list):
        return {"arrayValue": {"values": [typed(tabla, nombre, x) for x in v]} if v else {}}
    return {"stringValue": str(v)}

def main():
    if not os.path.exists(DB_PATH):
        sys.exit(f"No encuentro la base en {DB_PATH}")
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    docs = {}
    total = 0
    for tabla, col in TABLAS.items():
        filas = [dict(r) for r in con.execute(f'SELECT * FROM "{tabla}"')]
        for f in filas:
            iddoc = str(f.pop("id"))
            fields = {k: typed(tabla, k, v) for k, v in f.items()}
            docs.setdefault(col, []).append((iddoc, fields))
        total += len(filas)
        print(f"{tabla}: {len(filas)} filas -> coleccion '{col}'")

    if DRY:
        print(f"DRY-RUN OK: {total} documentos listos (sin subir)")
        return

    tok = subprocess.run(["gcloud", "auth", "print-access-token"],
                         capture_output=True, text=True)
    token = tok.stdout.strip()
    if not token:
        sys.exit("No obtuve token de gcloud. Abre Cloud Shell con tu cuenta de Google.")

    ok = 0
    for col, items in docs.items():
        fallos = 0
        for iddoc, fields in items:
            url = (f"https://firestore.googleapis.com/v1/projects/{PROJECT}"
                   f"/databases/(default)/documents/{col}/{iddoc}")
            req = urllib.request.Request(url, method="PATCH",
                data=json.dumps({"fields": fields}).encode("utf-8"),
                headers={"Authorization": f"Bearer {token}",
                         "Content-Type": "application/json"})
            try:
                urllib.request.urlopen(req, timeout=30)
                ok += 1
            except urllib.error.HTTPError as e:
                fallos += 1
                print(f"  ERROR {col}/{iddoc}: {e.code} {e.read().decode()[:200]}")
        print(f"  coleccion '{col}': {len(items) - fallos} subidos"
              + (f", {fallos} con error" if fallos else ""))
    print(f"LISTO: {ok}/{total} documentos en el proyecto '{PROJECT}'")

if __name__ == "__main__":
    main()
