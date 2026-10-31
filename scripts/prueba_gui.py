"""prueba_gui.py — Prueba de humo de la interfaz: crea la ventana SPA, recorre
las 7 vistas y cierra. Requiere pantalla (usar xvfb-run en Linux)."""
from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path("/home/z/my-project/download/SistemaAT")
sys.path.insert(0, str(RAIZ))

import customtkinter as ctk  # noqa: E402

from src.database import init_db  # noqa: E402
from src.main_window import MainWindow, VISTAS  # noqa: E402


def main() -> None:
    init_db()
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")
    app = MainWindow()
    orden = ["dashboard", "deportistas", "at_f3", "at_f1", "at_f8", "at_f9", "firmas", "dashboard"]
    paso = [0]

    def recorrer() -> None:
        if paso[0] >= len(orden):
            geometria = app.geometry()
            print(f"[GUI OK] Ventana {geometria} · vistas recorridas: {len(orden)}")
            app.destroy()
            return
        clave = orden[paso[0]]
        app.show_view(clave)
        app.update_idletasks()
        assert app.vista_actual == clave
        print(f"[vista OK] {clave}")
        paso[0] += 1
        app.after(120, recorrer)

    app.after(300, recorrer)
    app.after(20000, app.destroy)  # red de seguridad
    app.mainloop()


if __name__ == "__main__":
    main()
