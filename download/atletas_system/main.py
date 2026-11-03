# -*- coding: utf-8 -*-
"""
main.py
=======
Punto de entrada del Sistema AT · DINADAF (Instituto Peruano del Deporte).

Responsabilidad:
    1. Configurar el logging en archivo (data/sistema_at.log; en producción
       los mensajes NO van a consola — la app es windowed).
    2. Aplicar el tema institucional y crear el esquema de base de datos.
    3. Abrir la ventana principal (shell SPA con navegación lateral).

Ejecución:  python main.py        (desarrollo)
            SistemaAT.exe         (empaquetado con PyInstaller + Inno Setup)
"""
from __future__ import annotations

import logging
import sys
import traceback

from src import config, theme
from src.database import init_db


def configurar_logging() -> None:
    """Log en archivo dentro de la carpeta de datos del usuario."""
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        filename=str(config.DATA_DIR / "sistema_at.log"),
        level=logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        encoding="utf-8",
    )


def main() -> None:
    configurar_logging()
    log = logging.getLogger("sistema_at")
    theme.aplicar_tema()
    init_db()

    # Importación tardía: garantiza BD y tema listos antes de construir la UI
    from src.main_window import MainWindow

    app = MainWindow()
    log.info(
        "Sistema AT v%s iniciado (congelado=%s, datos=%s, plantillas=%s)",
        config.VERSION, config.CONGELADO, config.DATA_DIR, config.TEMPLATES_DIR,
    )
    app.mainloop()
    log.info("Sistema AT finalizado.")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        detalle = traceback.format_exc()
        logging.getLogger("sistema_at").exception("Error fatal al iniciar la aplicación")
        try:
            from tkinter import messagebox

            messagebox.showerror(
                "Sistema AT — error fatal",
                "No se pudo iniciar la aplicación:\n\n" + detalle[-1200:],
            )
        except Exception:
            # sin entorno gráfico disponible: solo queda el log
            pass
        sys.exit(1)
