"""
=============================================================
 Sistema AT · Instituto Peruano del Deporte (IPD - DINADAF)
 views/firmas.py — Captura de rúbricas en pantalla (canvas),
 registro con hash SHA-256, listado y desactivación (jamás
 borrado físico) con auditoría completa.
=============================================================
"""
from __future__ import annotations

from typing import Any

import customtkinter as ctk
from tkinter import messagebox

from src import database as db
from src.config import ROLES_FIRMA, ROLES_FIRMA_ETIQUETAS
from src.theme import COLORS, FONTS
from src.widgets import Card, DangerButton, PrimaryButton, SecondaryButton, SectionTitle, etiqueta_datos

ANCHO_LIENZO = 420
ALTO_LIENZO = 160
GROSOR_TINTA = 2


class FirmasView(ctk.CTkFrame):
    """Gestión de firmas: capturar, listar y desactivar."""

    def __init__(self, master: Any, app: Any) -> None:
        super().__init__(master, fg_color="transparent")
        self.app = app
        self._ultimo_punto: tuple[float, float] | None = None
        self._construir()
        self._refrescar_tabla()

    # ------------------------------------------------------------------
    def _construir(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(self, text="Firmas autorizadas", font=FONTS["h2"],
                     text_color=COLORS["text_primary"]).grid(row=0, column=0, sticky="w",
                                                             padx=28, pady=(24, 10))
        contenido = ctk.CTkFrame(self, fg_color="transparent")
        contenido.grid(row=1, column=0, sticky="nsew", padx=28, pady=(0, 24))
        contenido.grid_columnconfigure(0, weight=0)
        contenido.grid_columnconfigure(1, weight=1)
        contenido.grid_rowconfigure(0, weight=1)

        # --- Captura ----------------------------------------------------
        captura = Card(contenido, width=480)
        captura.grid(row=0, column=0, sticky="ns", padx=(0, 10))
        captura.pack_propagate(False)
        SectionTitle(captura, "Registrar nueva firma").pack(anchor="w", padx=18, pady=(16, 6))

        ctk.CTkLabel(captura, text="Rol", font=FONTS["small_bold"],
                     text_color=COLORS["text_secondary"], anchor="w").pack(fill="x", padx=18)
        self.menu_rol = ctk.CTkOptionMenu(
            captura, values=[ROLES_FIRMA_ETIQUETAS[r] for r in ROLES_FIRMA],
            font=FONTS["body"], fg_color=COLORS["bg_main"],
            button_color=COLORS["accent"], button_hover_color=COLORS["accent_hover"])
        self.menu_rol.pack(fill="x", padx=18, pady=4)

        ctk.CTkLabel(captura, text="Nombre del titular", font=FONTS["small_bold"],
                     text_color=COLORS["text_secondary"], anchor="w").pack(fill="x", padx=18)
        self.campo_nombre = ctk.CTkEntry(captura, placeholder_text="Nombre completo",
                                         font=FONTS["body"], fg_color=COLORS["bg_main"],
                                         border_color=COLORS["border"])
        self.campo_nombre.pack(fill="x", padx=18, pady=4)

        ctk.CTkLabel(captura, text="Dibuje la rúbrica con el mouse:",
                     font=FONTS["small"], text_color=COLORS["text_secondary"],
                     anchor="w").pack(fill="x", padx=18, pady=(8, 2))
        self.lienzo = ctk.CTkCanvas(captura, width=ANCHO_LIENZO, height=ALTO_LIENZO,
                                    bg="white", highlightthickness=1,
                                    highlightbackground=COLORS["border"], cursor="pencil")
        self.lienzo.pack(padx=18, pady=4)
        self.lienzo.bind("<Button-1>", self._inicio_trazo)
        self.lienzo.bind("<B1-Motion>", self._trazar)
        self.lienzo.bind("<ButtonRelease-1>", lambda _e: setattr(self, "_ultimo_punto", None))

        botones = ctk.CTkFrame(captura, fg_color="transparent")
        botones.pack(fill="x", padx=18, pady=(8, 16))
        PrimaryButton(botones, "💾 Guardar firma", self._guardar).pack(fill="x", pady=3)
        SecondaryButton(botones, "🧽 Limpiar rúbrica", self._limpiar_lienzo).pack(fill="x", pady=3)
        ctk.CTkLabel(
            captura,
            text="Las firmas se guardan con hash SHA-256 y solo pueden "
                 "desactivarse, nunca eliminarse (auditoría DINADAF).",
            font=FONTS["small"], text_color=COLORS["text_secondary"],
            wraplength=420, justify="left", anchor="w",
        ).pack(fill="x", padx=18, pady=(4, 12))

        # --- Listado ----------------------------------------------------
        listado = Card(contenido)
        listado.grid(row=0, column=1, sticky="nsew")
        SectionTitle(listado, "Firmas registradas").pack(anchor="w", padx=18, pady=(16, 6))
        self.tabla = ctk.CTkScrollableFrame(listado, fg_color="transparent")
        self.tabla.pack(fill="both", expand=True, padx=18, pady=(0, 16))

    # ------------------------------------------------------------------
    # Captura en el lienzo
    # ------------------------------------------------------------------
    def _inicio_trazo(self, evento: Any) -> None:
        self._ultimo_punto = (evento.x, evento.y)
        self.lienzo.create_oval(evento.x - 1, evento.y - 1, evento.x + 1, evento.y + 1,
                                fill="black", outline="black")

    def _trazar(self, evento: Any) -> None:
        if self._ultimo_punto is not None:
            self.lienzo.create_line(*self._ultimo_punto, evento.x, evento.y,
                                    width=GROSOR_TINTA, fill="black",
                                    capstyle="round", smooth=True)
        self._ultimo_punto = (evento.x, evento.y)

    def _limpiar_lienzo(self) -> None:
        self.lienzo.delete("all")
        self._ultimo_punto = None

    # ------------------------------------------------------------------
    def _guardar(self) -> None:
        """Valida, rasteriza el lienzo a PNG transparente y lo registra con SHA-256."""
        nombre = self.campo_nombre.get().strip()
        if not nombre:
            messagebox.showwarning("Falta el titular", "Ingrese el nombre del titular de la firma.")
            return
        trazos = self.lienzo.find_all()
        if not trazos:
            messagebox.showwarning("Rúbrica vacía", "Dibuje la firma en el recuadro blanco.")
            return
        rol_inverso = {etiqueta: rol for rol, etiqueta in ROLES_FIRMA_ETIQUETAS.items()}
        rol = rol_inverso[self.menu_rol.get()]

        try:
            from PIL import Image, ImageDraw

            imagen = Image.new("RGBA", (ANCHO_LIENZO, ALTO_LIENZO), (0, 0, 0, 0))
            dibujo = ImageDraw.Draw(imagen)
            for item in trazos:
                coordenadas = self.lienzo.coords(item)
                if len(coordenadas) >= 4 and self.lienzo.type(item) == "line":
                    dibujo.line(coordenadas, fill=(15, 23, 42, 255), width=GROSOR_TINTA + 1,
                                joint="curve")
                elif len(coordenadas) == 4:  # punto inicial
                    dibujo.ellipse([coordenadas[0] - 1, coordenadas[1] - 1,
                                    coordenadas[2] + 1, coordenadas[3] + 1],
                                   fill=(15, 23, 42, 255))
            import io

            buffer = io.BytesIO()
            imagen.save(buffer, format="PNG")
            db.registrar_firma(rol, nombre, buffer.getvalue())
        except Exception:
            messagebox.showerror("Error al guardar",
                                 "No se pudo guardar la firma. Revise el archivo de registro.")
            raise
        messagebox.showinfo("Firma registrada", f"La firma de {nombre} quedó activa para el rol {rol}.")
        self.campo_nombre.delete(0, "end")
        self._limpiar_lienzo()
        self._refrescar_tabla()

    # ------------------------------------------------------------------
    def _refrescar_tabla(self) -> None:
        for widget in self.tabla.winfo_children():
            widget.destroy()
        firmas = db.listar_firmas()
        if not firmas:
            etiqueta_datos(self.tabla, "Aún no hay firmas registradas.",
                           COLORS["text_secondary"]).pack(anchor="w", pady=8)
            return
        cabecera = ctk.CTkFrame(self.tabla, fg_color=COLORS["bg_main"], corner_radius=6)
        cabecera.pack(fill="x", pady=(0, 4))
        anchos = (3, 3, 2, 2, 2)
        for columna, peso in enumerate(anchos):
            cabecera.grid_columnconfigure(columna, weight=peso)
        for columna, texto in enumerate(("Titular", "Rol", "Hash (12)", "Estado", "Acción")):
            etiqueta_datos(cabecera, texto, COLORS["text_secondary"]).grid(
                row=0, column=columna, sticky="ew", padx=8, pady=4)
        for firma in firmas:
            linea = ctk.CTkFrame(self.tabla, fg_color="transparent")
            linea.pack(fill="x", pady=1)
            for columna, peso in enumerate(anchos):
                linea.grid_columnconfigure(columna, weight=peso)
            activo = bool(firma["activo"])
            valores = (
                firma["nombre"], ROLES_FIRMA_ETIQUETAS.get(firma["rol"], firma["rol"]),
                firma["sha256"][:12],
                "Activa" if activo else "Desactivada",
            )
            for columna, valor in enumerate(valores):
                color = COLORS["success"] if (columna == 3 and activo) else (
                    COLORS["danger"] if columna == 3 else None)
                etiqueta_datos(linea, str(valor), color).grid(row=0, column=columna,
                                                              sticky="ew", padx=8, pady=3)
            if activo:
                DangerButton(linea, "Desactivar",
                             lambda f=int(firma["id"]): self._desactivar(f)).grid(
                    row=0, column=4, sticky="ew", padx=8, pady=2)
            else:
                etiqueta_datos(linea, "—", COLORS["text_secondary"]).grid(
                    row=0, column=4, sticky="ew", padx=8)

    def _desactivar(self, firma_id: int) -> None:
        if not messagebox.askyesno("Desactivar firma",
                                   "La firma dejará de estamparse en nuevos formatos. ¿Continuar?"):
            return
        db.desactivar_firma(firma_id)
        self._refrescar_tabla()
