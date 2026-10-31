"""
=============================================================
 Sistema AT · Instituto Peruano del Deporte (IPD - DINADAF)
 main.py — Punto de entrada de la aplicación de escritorio.
 Inicializa base de datos, registro de eventos y la ventana SPA.
=============================================================
"""
from __future__ import annotations

import logging
import sys
from types import TracebackType

from src import config


def _configurar_logging() -> None:
    """Envía los registros a DATA_DIR/sistema_at.log (o a la consola si falla)."""
    formato = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    try:
        config.DATA_DIR.mkdir(parents=True, exist_ok=True)
        logging.basicConfig(
            level=logging.INFO,
            format=formato,
            handlers=[logging.FileHandler(config.LOG_PATH, encoding="utf-8")],
        )
    except OSError:  # carpeta sin permisos: registrar en consola
        logging.basicConfig(level=logging.INFO, format=formato)
    logging.getLogger("sistema_at").info(
        "Inicio de %s v%s · portable=%s · datos=%s",
        config.APP_NAME, config.APP_VERSION, config.PORTABLE, config.DATA_DIR,
    )


def _excepcion_no_controlada(
    tipo: type[BaseException], valor: BaseException, traza: TracebackType | None
) -> None:
    """Última línea de defensa: registra y avisa al usuario con un diálogo."""
    logging.getLogger("sistema_at").critical("Error no controlado",
                                             exc_info=(tipo, valor, traza))
    try:
        from tkinter import messagebox

        messagebox.showerror(
            "Error inesperado",
            f"Ocurrió un error no controlado:\n{valor}\n\n"
            f"Detalle técnico en:\n{config.LOG_PATH}",
        )
    except Exception:  # pragma: no cover - entorno sin interfaz
        pass


def main() -> None:
    """Flujo principal de arranque de la aplicación."""
    sys.excepthook = _excepcion_no_controlada
    _configurar_logging()

    from src.database import init_db

    init_db()

    import customtkinter as ctk

    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")

    from src.main_window import MainWindow

    app = MainWindow()
    app.mainloop()


if __name__ == "__main__":
    main()
