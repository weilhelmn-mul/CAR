# -*- coding: utf-8 -*-
"""
src/views/deportistas.py
========================
Gestión de deportistas: búsqueda en vivo, tabla con nombre, deporte, categoría,
sexo y entrenador, y diálogo de alta/edición (DeportistaDialog).

Campos auxiliares documentados (existen en el esquema de BD y son necesarios
para el consolidado AT-F1): fecha_ingreso, fecha_retiro y el interruptor
"activo" (para marcar retiros).
"""
from __future__ import annotations

import datetime as dt
import logging
import sqlite3

import customtkinter as ctk
from tkinter import messagebox

from src import config
from src.database import get_connection, transaccion
from src.theme import COLORS, FONTS
from src.widgets import Card, FormField, PrimaryButton, TablaFrame, centrar_ventana

log = logging.getLogger(__name__)

_MAPA_SEXO = {"Damas (D)": "D", "Varones (V)": "V"}
_MAPA_SEXO_INV = {v: k for k, v in _MAPA_SEXO.items()}


def construir(parent, app) -> None:
    """Construye la vista y devuelve la instancia (útil para pruebas)."""
    return _Vista(parent, app)


class _Vista:
    def __init__(self, parent: ctk.CTkFrame, app):
        self.app = app
        contenedor = ctk.CTkFrame(parent, fg_color="transparent")
        contenedor.pack(fill="both", expand=True, padx=28, pady=24)
        contenedor.grid_columnconfigure(0, weight=1)
        contenedor.grid_rowconfigure(1, weight=1)

        # ---- Barra superior: búsqueda + nuevo --------------------------
        barra = Card(contenedor)
        barra.grid(row=0, column=0, sticky="ew", pady=(0, 14))
        barra.grid_columnconfigure(0, weight=1)
        self.busqueda = FormField(
            barra, "Buscar deportista", placeholder="Nombre, deporte o entrenador…", ancho=420
        )
        self.busqueda.grid(row=0, column=0, sticky="w", padx=16, pady=14)
        self.busqueda.entry.bind("<KeyRelease>", lambda _e: self.refrescar())
        PrimaryButton(barra, text="＋ Nuevo deportista", command=self._nuevo).grid(
            row=0, column=1, sticky="e", padx=16, pady=14
        )
        self.ver_retirados = ctk.CTkSwitch(
            barra, text="Mostrar retirados", font=FONTS["small"],
            command=self.refrescar, progress_color=COLORS["accent"],
        )
        self.ver_retirados.grid(row=0, column=2, sticky="e", padx=(0, 16))

        # ---- Tabla ------------------------------------------------------
        marco = Card(contenedor)
        marco.grid(row=1, column=0, sticky="nsew")
        marco.grid_columnconfigure(0, weight=1)
        marco.grid_rowconfigure(0, weight=1)
        self.tabla = TablaFrame(
            marco,
            columnas=["Nombres y apellidos", "Deporte", "Categoría", "Sexo", "Entrenador", "Acción"],
            pesos=[4.2, 2.2, 1.4, 1.2, 2.6, 1.2],
            altura=420,
        )
        self.tabla.grid(row=0, column=0, sticky="nsew", padx=14, pady=14)

        # Petición pendiente desde el Dashboard ("Nuevo deportista")
        if getattr(app, "pendiente", None) == "nuevo_deportista":
            app.pendiente = None
            self.abrir_dialogo(None)
        self.refrescar()

    # ---------------------------------------------------------------- datos
    def refrescar(self) -> None:
        """Vuelve a llenar la tabla aplicando el filtro de búsqueda en vivo."""
        texto = self.busqueda.get()
        like = f"%{texto}%"
        incluir_retirados = bool(self.ver_retirados.get())
        con = get_connection()
        try:
            if incluir_retirados:
                filas = con.execute(
                    """
                    SELECT * FROM deportistas
                    WHERE nombres_apellidos LIKE ? OR deporte LIKE ? OR entrenador LIKE ?
                    ORDER BY activo DESC, nombres_apellidos COLLATE NOCASE
                    """,
                    (like, like, like),
                ).fetchall()
            else:
                filas = con.execute(
                    """
                    SELECT * FROM deportistas
                    WHERE activo = 1 AND (nombres_apellidos LIKE ? OR deporte LIKE ? OR entrenador LIKE ?)
                    ORDER BY nombres_apellidos COLLATE NOCASE
                    """,
                    (like, like, like),
                ).fetchall()
        finally:
            con.close()

        self.tabla.limpiar()
        if not filas:
            ctk.CTkLabel(
                self.tabla, text="No hay deportistas que coincidan con la búsqueda.",
                font=FONTS["small"], text_color=COLORS["text_secondary"],
            ).grid(row=1, column=0, columnspan=6, pady=24)
            return
        for i, d in enumerate(filas):
            fila = self.tabla.nueva_fila(zebra=i % 2 == 1)
            nombre = d["nombres_apellidos"] + ("" if d["activo"] else "  (retirado)")
            ctk.CTkLabel(fila, text=nombre, font=FONTS["small_bold"], anchor="w").grid(row=0, column=0, sticky="ew", padx=10)
            ctk.CTkLabel(fila, text=d["deporte"] or "", font=FONTS["small"], anchor="w").grid(row=0, column=1, sticky="ew", padx=6)
            ctk.CTkLabel(fila, text=d["categoria"], font=FONTS["small"], anchor="w").grid(row=0, column=2, sticky="ew", padx=6)
            ctk.CTkLabel(fila, text=d["sexo"], font=FONTS["small"], anchor="w").grid(row=0, column=3, sticky="ew", padx=6)
            ctk.CTkLabel(fila, text=d["entrenador"] or "", font=FONTS["small"], anchor="w").grid(row=0, column=4, sticky="ew", padx=6)
            ctk.CTkButton(
                fila, text="Editar", width=76, height=26, font=FONTS["small_bold"],
                fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"],
                command=lambda id_=d["id"]: self.abrir_dialogo(id_),
            ).grid(row=0, column=5, sticky="e", padx=8)

    def _nuevo(self) -> None:
        self.abrir_dialogo(None)

    def abrir_dialogo(self, deportista_id: int | None) -> None:
        """Abre el diálogo de alta (id=None) o edición (id) de un deportista."""
        datos = None
        if deportista_id is not None:
            con = get_connection()
            try:
                datos = con.execute(
                    "SELECT * FROM deportistas WHERE id = ?", (deportista_id,)
                ).fetchone()
            finally:
                con.close()
            if datos is None:
                messagebox.showerror("No encontrado", "El deportista ya no existe.", parent=self)
                return
        DeportistaDialog(self, datos=datos, al_guardar=self.refrescar)


class DeportistaDialog(ctk.CTkToplevel):
    """Ventana modal de alta/edición de deportista."""

    def __init__(self, master, datos: sqlite3.Row | None, al_guardar):
        super().__init__(master)
        self.datos = datos
        self.al_guardar = al_guardar
        self.title("Editar deportista" if datos else "Nuevo deportista")
        self.configure(fg_color=COLORS["bg_main"])
        centrar_ventana(self, 560, 720)
        self.transient(master.winfo_toplevel())
        self.after(120, self.grab_set)

        cuerpo = ctk.CTkScrollableFrame(self, fg_color="transparent")
        cuerpo.pack(fill="both", expand=True, padx=20, pady=(18, 0))

        self.c_nombre = FormField(cuerpo, "Nombres y apellidos *", "Ej. HUAMAN MATAMOROS LUIS GUSTAVO")
        self.c_nombre.pack(fill="x", pady=5)
        self.c_deporte = FormField(cuerpo, "Deporte *", "Ej. ATLETISMO")
        self.c_deporte.pack(fill="x", pady=5)
        self.c_prueba = FormField(cuerpo, "Prueba / modalidad", "Ej. DC, DP, DECAN, 3000 m…")
        self.c_prueba.pack(fill="x", pady=5)

        ctk.CTkLabel(cuerpo, text="Categoría *", font=FONTS["small_bold"], anchor="w").pack(fill="x", pady=(8, 0))
        self.o_categoria = ctk.CTkOptionMenu(cuerpo, values=list(config.CATEGORIAS), font=FONTS["body"], height=32)
        self.o_categoria.pack(fill="x", pady=(2, 5))

        ctk.CTkLabel(cuerpo, text="Sexo *", font=FONTS["small_bold"], anchor="w").pack(fill="x", pady=(8, 0))
        self.s_sexo = ctk.CTkSegmentedButton(cuerpo, values=list(_MAPA_SEXO), font=FONTS["body"])
        self.s_sexo.set("Varones (V)")
        self.s_sexo.pack(fill="x", pady=(2, 5))

        self.c_region = FormField(cuerpo, "Región", "Ej. CUSCO")
        self.c_region.pack(fill="x", pady=5)
        self.c_entrenador = FormField(cuerpo, "Entrenador", "Ej. JHON CUSI HUAMÁN")
        self.c_entrenador.pack(fill="x", pady=5)
        self.c_ingreso = FormField(cuerpo, "Fecha de ingreso (opcional)", "AAAA-MM-DD")
        self.c_ingreso.pack(fill="x", pady=5)
        self.c_retiro = FormField(cuerpo, "Fecha de retiro (opcional)", "AAAA-MM-DD")
        self.c_retiro.pack(fill="x", pady=5)

        self.sw_activo = ctk.CTkSwitch(
            cuerpo, text="Deportista activo (albergado en el CAR)",
            font=FONTS["body"], progress_color=COLORS["accent"], onvalue=1, offvalue=0,
        )
        self.sw_activo.pack(anchor="w", pady=(8, 4))
        self.sw_activo.select()

        botones = ctk.CTkFrame(self, fg_color="transparent")
        botones.pack(fill="x", padx=20, pady=16)
        botones.grid_columnconfigure((0, 1), weight=1)
        PrimaryButton(botones, text="💾 Guardar", command=self._guardar).grid(row=0, column=0, sticky="e", padx=(0, 8))
        ctk.CTkButton(
            botones, text="Cancelar", width=120, font=FONTS["button"],
            fg_color=COLORS["border"], text_color=COLORS["text_primary"],
            hover_color="#cbd5e1", command=self.destroy,
        ).grid(row=0, column=1, sticky="w")

        if datos:
            self.c_nombre.set(datos["nombres_apellidos"])
            self.c_deporte.set(datos["deporte"])
            self.c_prueba.set(datos["prueba_modalidad"])
            self.o_categoria.set(datos["categoria"])
            self.s_sexo.set(_MAPA_SEXO_INV.get(datos["sexo"], "Varones (V)"))
            self.c_region.set(datos["region"])
            self.c_entrenador.set(datos["entrenador"])
            self.c_ingreso.set(datos["fecha_ingreso"])
            self.c_retiro.set(datos["fecha_retiro"])
            if datos["activo"]:
                self.sw_activo.select()
            else:
                self.sw_activo.deselect()

    # ---------------------------------------------------------------- guardar
    def _fecha_valida(self, texto: str, campo: str) -> str | None:
        """Valida una fecha opcional AAAA-MM-DD; devuelve None si está vacía."""
        if not texto:
            return None
        try:
            dt.datetime.strptime(texto, "%Y-%m-%d")
        except ValueError:
            messagebox.showerror(
                "Fecha no válida", f"La {campo} debe tener el formato AAAA-MM-DD.", parent=self
            )
            raise ValueError(campo)
        return texto

    def _guardar(self) -> None:
        nombre = self.c_nombre.get()
        if not nombre:
            messagebox.showwarning("Campo obligatorio", "El nombre del deportista es obligatorio.", parent=self)
            return
        deporte = self.c_deporte.get()
        if not deporte:
            messagebox.showwarning("Campo obligatorio", "El deporte es obligatorio.", parent=self)
            return
        try:
            ingreso = self._fecha_valida(self.c_ingreso.get(), "fecha de ingreso")
            retiro = self._fecha_valida(self.c_retiro.get(), "fecha de retiro")
        except ValueError:
            return

        valores = (
            nombre.upper(),
            deporte.upper(),
            self.c_prueba.get().upper() or None,
            self.o_categoria.get(),
            _MAPA_SEXO.get(self.s_sexo.get(), "V"),
            self.c_region.get().upper() or None,
            self.c_entrenador.get().upper() or None,
            int(self.sw_activo.get()),
            ingreso,
            retiro,
        )
        try:
            with transaccion() as con:
                if self.datos is None:
                    con.execute(
                        """
                        INSERT INTO deportistas
                            (nombres_apellidos, deporte, prueba_modalidad, categoria, sexo,
                             region, entrenador, activo, fecha_ingreso, fecha_retiro)
                        VALUES (?,?,?,?,?,?,?,?,?,?)
                        """,
                        valores,
                    )
                else:
                    con.execute(
                        """
                        UPDATE deportistas SET nombres_apellidos=?, deporte=?, prueba_modalidad=?,
                            categoria=?, sexo=?, region=?, entrenador=?, activo=?,
                            fecha_ingreso=?, fecha_retiro=?
                        WHERE id=?
                        """,
                        valores + (self.datos["id"],),
                    )
        except sqlite3.Error as e:
            log.exception("Error al guardar deportista")
            messagebox.showerror("Base de datos", f"No se pudo guardar el deportista:\n{e}", parent=self)
            return
        messagebox.showinfo("Guardado", "Deportista guardado correctamente.", parent=self)
        self.al_guardar()
        self.destroy()
