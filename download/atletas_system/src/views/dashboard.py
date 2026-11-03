# -*- coding: utf-8 -*-
"""
src/views/dashboard.py
======================
Panel principal del Sistema AT: cuatro tarjetas de indicadores (deportistas
activos, registros mensuales AT-F3, firmas activas y documentos firmados),
tarjeta de acciones rápidas y tarjeta de actividad reciente con las últimas
10 firmas aplicadas a documentos.
"""
from __future__ import annotations

import customtkinter as ctk

from src.database import get_connection
from src.theme import COLORS, FONTS
from src.widgets import Card, PrimaryButton, SectionTitle, StatCard, TablaFrame


def construir(parent, app) -> None:
    """Construye la vista y devuelve la instancia (útil para pruebas)."""
    return _Vista(parent, app)


class _Vista:
    def __init__(self, parent: ctk.CTkFrame, app):
        self.app = app
        contenedor = ctk.CTkFrame(parent, fg_color="transparent")
        contenedor.pack(fill="both", expand=True, padx=28, pady=24)
        contenedor.grid_columnconfigure(0, weight=1)
        contenedor.grid_rowconfigure(2, weight=1)

        # ---- Fila 1: indicadores ---------------------------------------
        fila_stats = ctk.CTkFrame(contenedor, fg_color="transparent")
        fila_stats.grid(row=0, column=0, sticky="ew")
        for i in range(4):
            fila_stats.grid_columnconfigure(i, weight=1, uniform="stat")
        con = get_connection()
        try:
            n_deportistas = con.execute(
                "SELECT COUNT(*) FROM deportistas WHERE activo = 1"
            ).fetchone()[0]
            n_registros = con.execute("SELECT COUNT(*) FROM registros_mensuales").fetchone()[0]
            n_firmas = con.execute("SELECT COUNT(*) FROM firmas WHERE activa = 1").fetchone()[0]
            n_firmados = con.execute(
                "SELECT COUNT(*) FROM (SELECT DISTINCT tipo_documento, documento_id FROM asignaciones_firma)"
            ).fetchone()[0]
        finally:
            con.close()

        StatCard(fila_stats, "🏃", "Deportistas activos", n_deportistas, COLORS["accent"]).grid(
            row=0, column=0, sticky="ew", padx=(0, 12)
        )
        StatCard(fila_stats, "📋", "Registros mensuales (AT-F3)", n_registros, COLORS["success"]).grid(
            row=0, column=1, sticky="ew", padx=12
        )
        StatCard(fila_stats, "✒️", "Firmas activas", n_firmas, COLORS["warning"]).grid(
            row=0, column=2, sticky="ew", padx=12
        )
        StatCard(fila_stats, "📄", "Documentos firmados", n_firmados, COLORS["accent_hover"]).grid(
            row=0, column=3, sticky="ew", padx=(12, 0)
        )

        # ---- Fila 2: acciones rápidas ----------------------------------
        acciones = Card(contenedor)
        acciones.grid(row=1, column=0, sticky="ew", pady=16)
        acciones.grid_columnconfigure((0, 1, 2), weight=1)
        SectionTitle(acciones, "Acciones rápidas").grid(
            row=0, column=0, columnspan=3, sticky="ew", padx=16, pady=(14, 8)
        )
        PrimaryButton(acciones, text="＋ Nuevo deportista", command=self._nuevo_deportista).grid(
            row=1, column=0, sticky="ew", padx=16, pady=(0, 16)
        )
        PrimaryButton(acciones, text="📋 Registrar AT-F3", command=self._ir_at_f3).grid(
            row=1, column=1, sticky="ew", padx=12, pady=(0, 16)
        )
        PrimaryButton(acciones, text="✒️ Subir firma", command=self._ir_firmas).grid(
            row=1, column=2, sticky="ew", padx=16, pady=(0, 16)
        )

        # ---- Fila 3: actividad reciente --------------------------------
        actividad = Card(contenedor)
        actividad.grid(row=2, column=0, sticky="nsew")
        actividad.grid_columnconfigure(0, weight=1)
        actividad.grid_rowconfigure(1, weight=1)
        SectionTitle(actividad, "Actividad reciente · últimas 10 firmas aplicadas").grid(
            row=0, column=0, sticky="ew", padx=16, pady=(14, 8)
        )
        tabla = TablaFrame(
            actividad,
            columnas=["Documento", "Firmado por", "Rol", "Fecha y hora"],
            pesos=[2, 4, 3, 3],
            altura=260,
        )
        tabla.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 16))

        con = get_connection()
        try:
            filas = con.execute(
                """
                SELECT a.tipo_documento, a.documento_id, a.firmado_en, a.notas,
                       f.persona_nombre, f.rol
                FROM asignaciones_firma a JOIN firmas f ON f.id = a.firma_id
                ORDER BY a.id DESC LIMIT 10
                """
            ).fetchall()
        finally:
            con.close()

        if not filas:
            ctk.CTkLabel(
                tabla, text="Aún no se han aplicado firmas a documentos generados.",
                font=FONTS["small"], text_color=COLORS["text_secondary"],
            ).grid(row=1, column=0, columnspan=4, pady=24)
        else:
            for i, f in enumerate(filas):
                zebra = i % 2 == 1
                fila = tabla.nueva_fila(zebra=zebra)
                ctk.CTkLabel(fila, text=f"{f['tipo_documento']} · #{f['documento_id']}", font=FONTS["small_bold"], anchor="w").grid(row=0, column=0, sticky="ew", padx=8)
                ctk.CTkLabel(fila, text=f["persona_nombre"], font=FONTS["small"], anchor="w").grid(row=0, column=1, sticky="ew", padx=8)
                ctk.CTkLabel(fila, text=f["rol"], font=FONTS["small"], anchor="w").grid(row=0, column=2, sticky="ew", padx=8)
                ctk.CTkLabel(fila, text=str(f["firmado_en"] or ""), font=FONTS["small"], anchor="w").grid(row=0, column=3, sticky="ew", padx=8)

    # ------------------------------------------------------------- acciones
    def _nuevo_deportista(self) -> None:
        self.app.pendiente = "nuevo_deportista"
        self.app.show_view("deportistas")

    def _ir_at_f3(self) -> None:
        self.app.show_view("at_f3")

    def _ir_firmas(self) -> None:
        self.app.show_view("firmas")
