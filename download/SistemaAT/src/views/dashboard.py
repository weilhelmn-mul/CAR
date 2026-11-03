"""
=============================================================
 Sistema AT · Instituto Peruano del Deporte (IPD - DINADAF)
 views/dashboard.py — Panel general: indicadores clave, accesos
 rápidos y últimos registros AT-F3 ingresados.
=============================================================
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

import customtkinter as ctk

from src import database as db
from src.theme import COLORS, FONTS
from src.widgets import Card, PrimaryButton, SectionTitle, StatCard, etiqueta_datos


class DashboardView(ctk.CTkFrame):
    """Panel de inicio con métricas del mes y navegación rápida."""

    def __init__(self, master: Any, app: Any) -> None:
        super().__init__(master, fg_color="transparent")
        self.app = app
        self._construir()

    # ------------------------------------------------------------------
    def _construir(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        periodo_actual = datetime.now().strftime("%Y-%m")

        encabezado = ctk.CTkFrame(self, fg_color="transparent")
        encabezado.grid(row=0, column=0, sticky="ew", padx=28, pady=(24, 4))
        ctk.CTkLabel(encabezado, text="Panel general", font=FONTS["h2"],
                     text_color=COLORS["text_primary"]).pack(anchor="w")
        ctk.CTkLabel(
            encabezado,
            text=f"{datetime.now().strftime('%d/%m/%Y')} · Periodo en curso: {periodo_actual}",
            font=FONTS["small"], text_color=COLORS["text_secondary"],
        ).pack(anchor="w")

        indicadores = ctk.CTkFrame(self, fg_color="transparent")
        indicadores.grid(row=1, column=0, sticky="ew", padx=28, pady=12)
        for columna in range(4):
            indicadores.grid_columnconfigure(columna, weight=1, uniform="stats")
        tarjetas = [
            ("Deportistas activos", str(db.contar_deportistas()), COLORS["accent"]),
            (f"Registros AT-F3 · {periodo_actual}", str(db.contar_registros(periodo_actual)), COLORS["success"]),
            ("Planes JUT registrados", str(db.contar_planes()), COLORS["warning"]),
            ("Evaluaciones AT-F9", str(db.contar_evaluaciones()), COLORS["text_primary"]),
        ]
        for columna, (titulo, valor, color) in enumerate(tarjetas):
            StatCard(indicadores, titulo, valor, color).grid(row=0, column=columna, sticky="nsew", padx=6)

        contenido = ctk.CTkFrame(self, fg_color="transparent")
        contenido.grid(row=2, column=0, sticky="nsew", padx=28, pady=(4, 24))
        contenido.grid_columnconfigure(0, weight=1)
        contenido.grid_columnconfigure(1, weight=1)
        contenido.grid_rowconfigure(0, weight=1)

        # --- Accesos rápidos -------------------------------------------
        acciones = Card(contenido)
        acciones.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        SectionTitle(acciones, "Accesos rápidos").pack(anchor="w", padx=18, pady=(16, 8))
        atajos = [
            ("➕  Registrar deportista", "deportistas"),
            ("📋  Nuevo informe AT-F3", "at_f3"),
            ("🗂️  Consolidado AT-F1 del CAR", "at_f1"),
            ("🗓️  Plan AT-F8 del JUT", "at_f8"),
            ("✅  Evaluación AT-F9", "at_f9"),
            ("✍️  Gestionar firmas", "firmas"),
        ]
        for texto, clave in atajos:
            PrimaryButton(acciones, texto, lambda k=clave: self.app.show_view(k)).pack(
                fill="x", padx=18, pady=5
            )

        # --- Últimos registros -----------------------------------------
        ultimos = Card(contenido)
        ultimos.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        SectionTitle(ultimos, "Últimos registros AT-F3").pack(anchor="w", padx=18, pady=(16, 8))

        cabecera = ctk.CTkFrame(ultimos, fg_color=COLORS["bg_main"], corner_radius=6)
        cabecera.pack(fill="x", padx=18)
        for columna, peso in enumerate((4, 2, 3)):
            cabecera.grid_columnconfigure(columna, weight=peso)
        for columna, texto in enumerate(("Deportista", "Cat.", "Periodo")):
            etiqueta_datos(cabecera, texto, COLORS["text_secondary"]).grid(
                row=0, column=columna, sticky="ew", padx=8, pady=4
            )

        registros = db.ultimos_registros(9)
        contenedor = ctk.CTkFrame(ultimos, fg_color="transparent")
        contenedor.pack(fill="both", expand=True, padx=18, pady=(2, 16))
        if not registros:
            etiqueta_datos(contenedor, "Aún no hay registros. Empiece por AT-F3.",
                           COLORS["text_secondary"]).pack(anchor="w", pady=10)
        for fila, registro in enumerate(registros):
            linea = ctk.CTkFrame(contenedor, fg_color="transparent")
            linea.pack(fill="x", pady=2)
            for columna, peso in enumerate((4, 2, 3)):
                linea.grid_columnconfigure(columna, weight=peso)
            etiqueta_datos(linea, registro["nombre"]).grid(row=0, column=0, sticky="ew")
            etiqueta_datos(linea, registro["categoria"]).grid(row=0, column=1, sticky="ew")
            etiqueta_datos(linea, registro["periodo"], COLORS["text_secondary"]).grid(
                row=0, column=2, sticky="ew"
            )
