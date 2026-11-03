# -*- coding: utf-8 -*-
"""
src/main_window.py
==================
Ventana principal del Sistema AT: shell tipo SPA con barra lateral oscura
(marca, navegación de 7 vistas y versión al pie) y panel de contenido claro
(cabecera con título dinámico + body donde se destruye/recrea la vista activa).

Tamaño: 1400×850 (mínimo 1200×700). Navegación: show_view(key) actualiza el
botón activo, el título y reconstruye la vista dentro del body.
"""
from __future__ import annotations

import importlib
import logging

import customtkinter as ctk

from src import config
from src.theme import COLORS, FONTS
from src.widgets import abrir_ruta  # noqa: F401  (reexportado para comodidad de las vistas)

log = logging.getLogger(__name__)

TITULOS = {
    "dashboard": "Panel principal",
    "deportistas": "Gestión de deportistas",
    "at_f3": "AT-F3 · Informe técnico mensual del deportista albergado",
    "at_f1": "AT-F1 · Informe mensual del área técnica (JUT) y/o entrenadores",
    "at_f8": "AT-F8 · Plan de trabajo mensual del Jefe de Unidad Técnica",
    "at_f9": "AT-F9 · Informe de cumplimiento del Jefe de Unidad Técnica",
    "firmas": "Gestión de firmas",
}

NAVEGACION = [
    ("dashboard", "🏠   Panel principal"),
    ("deportistas", "🏃   Deportistas"),
    ("at_f3", "📋   AT-F3 · Deportista"),
    ("at_f1", "📊   AT-F1 · CAR"),
    ("at_f8", "🗓️   AT-F8 · Plan JUT"),
    ("at_f9", "✅   AT-F9 · Cumplimiento"),
    ("firmas", "✒️   Firmas"),
]


class MainWindow(ctk.CTk):
    """Ventana raíz de la aplicación."""

    def __init__(self):
        super().__init__()
        self.title("Sistema AT · DINADAF — Instituto Peruano del Deporte")
        self.geometry("1400x850")
        self.minsize(1200, 700)
        self.configure(fg_color=COLORS["bg_main"])

        self._vista_actual: str | None = None
        self.vista = None  # instancia de la vista activa (testabilidad)
        self._nav_botones: dict[str, ctk.CTkButton] = {}
        # Bandera de comunicación entre vistas (ej. Dashboard → Deportistas:
        # abrir el diálogo de nuevo deportista tras navegar).
        self.pendiente: str | None = None

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self._construir_sidebar()
        self._construir_panel()
        self.show_view("dashboard")

    # ------------------------------------------------------------------ UI
    def _construir_sidebar(self) -> None:
        barra = ctk.CTkFrame(self, width=240, corner_radius=0, fg_color=COLORS["sidebar"])
        barra.grid(row=0, column=0, sticky="nsw")
        barra.grid_propagate(False)
        barra.grid_rowconfigure(2, weight=1)

        # Marca
        marca = ctk.CTkFrame(barra, fg_color="transparent")
        marca.grid(row=0, column=0, sticky="ew", padx=18, pady=(22, 4))
        ctk.CTkLabel(marca, text="🏅", font=FONTS["h2"]).pack(anchor="w")
        ctk.CTkLabel(marca, text="Sistema AT", font=FONTS["h3"], text_color=COLORS["text_light"]).pack(anchor="w")
        ctk.CTkLabel(
            marca, text="DINADAF · IPD", font=FONTS["small"],
            text_color=COLORS["text_light"], fg_color=COLORS["sidebar_hover"], corner_radius=6,
        ).pack(anchor="w", pady=(4, 0), ipadx=6, ipady=2)

        # Navegación
        nav = ctk.CTkFrame(barra, fg_color="transparent")
        nav.grid(row=1, column=0, sticky="ew", padx=12, pady=(16, 0))
        for clave, texto in NAVEGACION:
            boton = ctk.CTkButton(
                nav, text=texto, anchor="w", height=42, corner_radius=8,
                font=FONTS["body"], text_color=COLORS["text_light"],
                fg_color="transparent", hover_color=COLORS["sidebar_hover"],
                command=lambda k=clave: self.show_view(k),
            )
            boton.pack(fill="x", pady=2)
            self._nav_botones[clave] = boton

        # Pie con versión
        ctk.CTkLabel(
            barra, text=f"v{config.VERSION} · DINADAF 2026",
            font=FONTS["small"], text_color=COLORS["text_light"],
        ).grid(row=3, column=0, sticky="ew", padx=18, pady=16)

    def _construir_panel(self) -> None:
        panel = ctk.CTkFrame(self, fg_color="transparent")
        panel.grid(row=0, column=1, sticky="nsew")
        panel.grid_rowconfigure(1, weight=1)
        panel.grid_columnconfigure(0, weight=1)

        # Cabecera con título dinámico
        cabecera = ctk.CTkFrame(panel, height=68, corner_radius=0, fg_color=COLORS["card"])
        cabecera.grid(row=0, column=0, sticky="ew")
        cabecera.grid_columnconfigure(0, weight=1)
        self.title_label = ctk.CTkLabel(
            cabecera, text=TITULOS["dashboard"], font=FONTS["h2"], text_color=COLORS["text_primary"], anchor="w"
        )
        self.title_label.grid(row=0, column=0, sticky="ew", padx=28, pady=16)
        ctk.CTkFrame(cabecera, height=1, fg_color=COLORS["border"]).grid(row=1, column=0, sticky="ew")

        # Body: aquí se destruye y recrea cada vista
        self.body = ctk.CTkFrame(panel, fg_color=COLORS["bg_main"])
        self.body.grid(row=1, column=0, sticky="nsew")

    # ------------------------------------------------------------- Navegación
    def _limpiar(self, frame: ctk.CTkFrame) -> None:
        """Destruye todos los hijos del frame (navegación tipo SPA)."""
        for hijo in frame.winfo_children():
            hijo.destroy()

    def show_view(self, clave: str) -> None:
        """Muestra la vista indicada actualizando nav activa, título y body."""
        if clave not in TITULOS:
            clave = "dashboard"
        self._vista_actual = clave
        for k, boton in self._nav_botones.items():
            boton.configure(
                fg_color=COLORS["sidebar_active"] if k == clave else "transparent",
                hover_color=COLORS["sidebar_hover"],
            )
        self.title_label.configure(text=TITULOS[clave])
        self._limpiar(self.body)
        try:
            modulo = importlib.import_module(f"src.views.{clave}")
            self.vista = modulo.construir(self.body, self)  # referencia a la vista activa
        except Exception:
            log.exception("Error al construir la vista '%s'", clave)
            raise
