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
import traceback
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


def _mostrar_error(titulo: str, mensaje: str) -> None:
    """Muestra un diálogo de error aunque Tk aún no exista; nunca lanza."""
    try:
        from tkinter import messagebox

        messagebox.showerror(titulo, mensaje)
    except Exception:  # pragma: no cover - entorno sin interfaz
        logging.getLogger("sistema_at").error("No se pudo mostrar el diálogo: %s", mensaje)


def _excepcion_no_controlada(
    tipo: type[BaseException], valor: BaseException, traza: TracebackType | None
) -> None:
    """Última línea de defensa: registra y avisa al usuario con un diálogo."""
    logging.getLogger("sistema_at").critical("Error no controlado",
                                             exc_info=(tipo, valor, traza))
    detalle = "".join(traceback.format_exception_only(tipo, valor)).strip()
    _mostrar_error(
        "Error inesperado",
        f"Ocurrió un error no controlado:\n{detalle}\n\n"
        f"Detalle técnico en:\n{config.LOG_PATH}",
    )


def _error_en_interfaz(tipo: type, valor: BaseException, traza: TracebackType | None) -> None:
    """Captura errores de callbacks de Tk (que no pasan por sys.excepthook)."""
    _excepcion_no_controlada(tipo, valor, traza)


def main() -> None:
    """Flujo principal de arranque de la aplicación.

    Todo el cuerpo está protegido: cualquier fallo (incluido el propio
    arranque de la interfaz) genera un diálogo visible y queda registrado
    en el log, incluso cuando se ejecuta con pythonw (sin consola).
    """
    sys.excepthook = _excepcion_no_controlada
    _configurar_logging()
    try:
        from src.database import init_db

        init_db()

        import customtkinter as ctk

        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")

        from src.main_window import MainWindow

        app = MainWindow()
        app.report_callback_exception = _error_en_interfaz  # errores de callbacks
        app.mainloop()
    except Exception:  # noqa: BLE001 - el arranque nunca debe morir en silencio
        logging.getLogger("sistema_at").critical("Fallo durante el arranque",
                                                  exc_info=True)
        detalle = traceback.format_exc().strip().splitlines()[-1]
        _mostrar_error(
            "El sistema no pudo iniciarse",
            f"{detalle}\n\n"
            "Revise el registro técnico en:\n"
            f"{config.LOG_PATH}\n\n"
            "Si esta carpeta viene de un ZIP, asegúrese de haberla extraído"
            " completa y de que su antivirus no esté bloqueando el sistema.",
        )
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
