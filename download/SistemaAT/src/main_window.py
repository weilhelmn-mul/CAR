"""
=============================================================
 Sistema AT · Instituto Peruano del Deporte (IPD - DINADAF)
 main_window.py — Ventana principal (1400×850) con navegación
 SPA: la vista activa se destruye y reconstruye en el cuerpo,
 sin abrir ventanas adicionales.
=============================================================
"""
from __future__ import annotations

import logging
from typing import Any, Callable

import customtkinter as ctk

from src.config import APP_NAME, APP_ORG, APP_VERSION, ruta_recurso
from src.theme import COLORS, FONTS
from src.views.alimentacion import AlimentacionView
from src.views.analisis import AnalisisView
from src.views.asistente import AsistenteView
from src.views.at_f1 import AtF1View
from src.views.at_f3 import AtF3View
from src.views.at_f8 import AtF8View
from src.views.at_f9 import AtF9View
from src.views.dashboard import DashboardView
from src.views.deportistas import DeportistasView
from src.views.expediente import ExpedienteView
from src.views.firmas import FirmasView
from src.views.seguro import SeguroView

log = logging.getLogger("sistema_at.ventana")

# Claves de navegación admitidas por show_view()
VISTAS: dict[str, Callable[[Any, Any], Any]] = {
    "dashboard": DashboardView,
    "deportistas": DeportistasView,
    "asistente": AsistenteView,
    "at_f3": AtF3View,
    "at_f1": AtF1View,
    "at_f8": AtF8View,
    "at_f9": AtF9View,
    "expediente": ExpedienteView,
    "alimentacion": AlimentacionView,
    "seguro": SeguroView,
    "analisis": AnalisisView,
    "firmas": FirmasView,
}

NAVEGACION: list[tuple[str, str]] = [
    ("dashboard", "🏠  Panel"),
    ("deportistas", "🧍  Deportistas"),
    ("asistente", "✨  Asistente IA"),
    ("at_f3", "📋  AT-F3 · Informe"),
    ("at_f1", "🗂️  AT-F1 · CAR"),
    ("at_f8", "🗓️  AT-F8 · Plan JUT"),
    ("at_f9", "✅  AT-F9 · Evaluación"),
    ("expediente", "🥇  Expediente del atleta"),
    ("alimentacion", "🥗  Alimentación"),
    ("seguro", "🛡️  Seguros"),
    ("analisis", "📊  Análisis deportivo"),
    ("firmas", "✍️  Firmas"),
]


class MainWindow(ctk.CTk):
    """Ventana raíz de la aplicación: sidebar fijo + cuerpo con vistas SPA."""

    def __init__(self) -> None:
        super().__init__(fg_color=COLORS["bg_main"])
        self.title(f"{APP_NAME} · {APP_ORG}")
        self.geometry("1400x850")
        self.minsize(1200, 700)
        self._vista_actual: str = ""
        self._botones_nav: dict[str, ctk.CTkButton] = {}

        try:  # Icono opcional (solo existe en el paquete compilado/plantillas)
            self.iconbitmap(str(ruta_recurso("assets", "icon.ico")))
        except Exception:  # pragma: no cover - decorativo
            log.debug("Icono de ventana no disponible")

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self._construir_sidebar()

        self.cuerpo = ctk.CTkFrame(self, fg_color=COLORS["bg_main"], corner_radius=0)
        self.cuerpo.grid(row=0, column=1, sticky="nsew")

        self.show_view("dashboard")

    # ------------------------------------------------------------------
    def _construir_sidebar(self) -> None:
        """Construye la barra lateral oscura de 240 px con la navegación."""
        barra = ctk.CTkFrame(self, width=240, corner_radius=0, fg_color=COLORS["sidebar"])
        barra.grid(row=0, column=0, sticky="nsew")
        barra.grid_propagate(False)
        barra.grid_columnconfigure(0, weight=1)

        marca = ctk.CTkLabel(barra, text="🏅 Sistema AT", font=FONTS["h3"],
                             text_color=COLORS["text_light"])
        marca.grid(row=0, column=0, sticky="ew", padx=20, pady=(24, 2))
        ctk.CTkLabel(barra, text="Gestión de formatos · DINADAF", font=FONTS["small"],
                     text_color="#94a3b8").grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 18))

        for clave, texto in NAVEGACION:
            boton = ctk.CTkButton(
                barra, text=texto, command=lambda k=clave: self.show_view(k),
                font=FONTS["body"], anchor="w", height=42, corner_radius=8,
                fg_color=COLORS["sidebar"], hover_color=COLORS["sidebar_active"],
                text_color=COLORS["text_light"],
            )
            boton.grid(row=2 + NAVEGACION.index((clave, texto)), column=0, sticky="ew",
                       padx=12, pady=3)
            self._botones_nav[clave] = boton

        pie = ctk.CTkLabel(barra, text=f"v{APP_VERSION} · DINADAF 2026", font=FONTS["small"],
                           text_color="#94a3b8")
        pie.grid(row=20, column=0, sticky="ew", padx=20, pady=16)

    # ------------------------------------------------------------------
    def show_view(self, key: str) -> None:
        """Reemplaza la vista del cuerpo (SPA: destruye y reconstruye)."""
        if key not in VISTAS:
            raise ValueError(f"Vista desconocida: {key}")
        for widget in self.cuerpo.winfo_children():
            widget.destroy()
        vista = VISTAS[key](self.cuerpo, self)
        vista.pack(fill="both", expand=True)
        self._vista_actual = key
        self._resaltar_navegacion(key)
        log.info("Vista activa: %s", key)

    def _resaltar_navegacion(self, key: str) -> None:
        """Marca en color acento el botón de la vista activa."""
        for clave, boton in self._botones_nav.items():
            activo = clave == key
            boton.configure(
                fg_color=COLORS["sidebar_active"] if activo else COLORS["sidebar"],
                hover_color=COLORS["sidebar_active"] if activo else COLORS["sidebar_hover"],
            )

    @property
    def vista_actual(self) -> str:
        """Clave de la vista actualmente mostrada."""
        return self._vista_actual
