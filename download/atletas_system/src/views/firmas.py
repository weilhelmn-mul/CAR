# -*- coding: utf-8 -*-
"""
src/views/firmas.py
===================
Gestión de firmas digitales (imágenes PNG): registro con hash SHA-256,
listado con estado y desactivación (no se permite borrar firmas para
preservar la trazabilidad de auditoría).

Al subir una firma:
    1. Se valida que sea un PNG real (PIL).
    2. Se copia a la carpeta FIRMAS_DIR con nombre único
       {nombre}_{rol}_{estampa}.png.
    3. Se inserta en la tabla `firmas` (con SHA-256 y vigente_desde=hoy) y se
       registra la acción en `auditoria_firmas`.
"""
from __future__ import annotations

import datetime as dt
import getpass
import hashlib
import logging
import shutil
import sqlite3
from pathlib import Path

import customtkinter as ctk
from PIL import Image as PILImage
from tkinter import filedialog, messagebox

from src import config
from src.database import get_connection, transaccion
from src.theme import COLORS, FONTS
from src.widgets import Card, FormField, PrimaryButton, SectionTitle, TablaFrame

log = logging.getLogger(__name__)

_ROL_INVERSO = {v: k for k, v in config.ROLES_FIRMA.items()}


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

        # ---- Formulario de registro ------------------------------------
        formulario = Card(contenedor)
        formulario.grid(row=0, column=0, sticky="ew", pady=(0, 14))
        formulario.grid_columnconfigure((0, 1), weight=1)
        SectionTitle(formulario, "Registrar una nueva firma").grid(
            row=0, column=0, columnspan=3, sticky="ew", padx=16, pady=(14, 4)
        )
        ctk.CTkLabel(
            formulario,
            text="Las firmas no se eliminan (solo se desactivan) para preservar la auditoría. "
                 "Al generar un documento se usa la firma activa más reciente del rol correspondiente.",
            font=FONTS["small"], text_color=COLORS["text_secondary"], anchor="w", justify="left",
        ).grid(row=1, column=0, columnspan=3, sticky="ew", padx=16)

        self.c_nombre = FormField(formulario, "Nombre de la persona", "Ej. JHON CUSI HUAMÁN", ancho=340)
        self.c_nombre.grid(row=2, column=0, sticky="ew", padx=16, pady=(10, 4))

        marco_rol = ctk.CTkFrame(formulario, fg_color="transparent")
        marco_rol.grid(row=2, column=1, sticky="w", padx=12, pady=(10, 4))
        ctk.CTkLabel(marco_rol, text="Rol", font=FONTS["small_bold"], anchor="w").pack(fill="x")
        self.o_rol = ctk.CTkOptionMenu(
            marco_rol, values=list(config.ROLES_FIRMA.values()), font=FONTS["body"], height=32, width=260
        )
        self.o_rol.pack(fill="x", pady=(2, 0))

        PrimaryButton(
            formulario, text="🖼️ Seleccionar PNG y guardar", command=self._subir_firma
        ).grid(row=2, column=2, sticky="e", padx=16, pady=(14, 6))

        # ---- Listado -----------------------------------------------------
        marco = Card(contenedor)
        marco.grid(row=1, column=0, sticky="nsew")
        marco.grid_columnconfigure(0, weight=1)
        marco.grid_rowconfigure(0, weight=1)
        self.tabla = TablaFrame(
            marco,
            columnas=["Nombre", "Rol", "SHA-256", "Registrada", "Estado", "Acción"],
            pesos=[3.4, 2.6, 2.4, 2, 1.4, 1.4],
            altura=380,
        )
        self.tabla.grid(row=0, column=0, sticky="nsew", padx=14, pady=14)
        self.refrescar()

    # ---------------------------------------------------------------- datos
    def refrescar(self) -> None:
        con = get_connection()
        try:
            filas = con.execute(
                "SELECT * FROM firmas ORDER BY activa DESC, id DESC"
            ).fetchall()
        finally:
            con.close()
        self.tabla.limpiar()
        if not filas:
            ctk.CTkLabel(
                self.tabla, text="Todavía no hay firmas registradas.",
                font=FONTS["small"], text_color=COLORS["text_secondary"],
            ).grid(row=1, column=0, columnspan=6, pady=24)
            return
        for i, f in enumerate(filas):
            fila = self.tabla.nueva_fila(zebra=i % 2 == 1)
            ctk.CTkLabel(fila, text=f["persona_nombre"], font=FONTS["small_bold"], anchor="w").grid(row=0, column=0, sticky="ew", padx=10)
            ctk.CTkLabel(fila, text=config.ROLES_FIRMA.get(f["rol"], f["rol"]), font=FONTS["small"], anchor="w").grid(row=0, column=1, sticky="ew", padx=6)
            hash_corto = (f["imagen_hash"] or "")[:14] + "…"
            ctk.CTkLabel(fila, text=hash_corto, font=FONTS["small"], text_color=COLORS["text_secondary"], anchor="w").grid(row=0, column=2, sticky="ew", padx=6)
            ctk.CTkLabel(fila, text=str(f["vigente_desde"] or ""), font=FONTS["small"], anchor="w").grid(row=0, column=3, sticky="ew", padx=6)
            ctk.CTkLabel(
                fila, text="Activa" if f["activa"] else "Inactiva", font=FONTS["small_bold"],
                text_color=COLORS["success"] if f["activa"] else COLORS["text_secondary"], anchor="w",
            ).grid(row=0, column=4, sticky="ew", padx=6)
            if f["activa"]:
                ctk.CTkButton(
                    fila, text="Desactivar", width=90, height=26, font=FONTS["small_bold"],
                    fg_color=COLORS["warning"], hover_color=COLORS["danger"],
                    command=lambda id_=f["id"]: self._desactivar(id_),
                ).grid(row=0, column=5, sticky="e", padx=8)
            else:
                ctk.CTkLabel(fila, text="—", font=FONTS["small"], text_color=COLORS["text_secondary"]).grid(row=0, column=5, sticky="e", padx=8)

    # ---------------------------------------------------------------- acciones
    def _subir_firma(self) -> None:
        nombre = self.c_nombre.get()
        if not nombre:
            messagebox.showwarning("Campo obligatorio", "Ingrese el nombre de la persona.", parent=self)
            return
        rol_mostrado = self.o_rol.get()
        rol = _ROL_INVERSO.get(rol_mostrado, "entrenador")

        ruta_origen = filedialog.askopenfilename(
            parent=self, title="Seleccionar firma PNG",
            filetypes=[("Imagen PNG", "*.png")],
        )
        if not ruta_origen:
            return

        # Validar que realmente sea una imagen PNG
        try:
            with PILImage.open(ruta_origen) as imagen:
                imagen.verify()
        except Exception:
            messagebox.showerror("Archivo no válido", "El archivo seleccionado no es una imagen PNG válida.", parent=self)
            return

        estampa = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        destino = config.FIRMAS_DIR / f"{config.nombre_archivo_seguro(nombre)}_{rol}_{estampa}.png"
        try:
            shutil.copyfile(ruta_origen, destino)
        except OSError as e:
            messagebox.showerror("Copia fallida", f"No se pudo copiar la imagen:\n{e}", parent=self)
            return
        hash_sha = hashlib.sha256(destino.read_bytes()).hexdigest()
        hoy = dt.date.today().isoformat()
        try:
            with transaccion() as con:
                cursor = con.execute(
                    """
                    INSERT INTO firmas (persona_nombre, rol, imagen_path, imagen_hash, activa, vigente_desde)
                    VALUES (?, ?, ?, ?, 1, ?)
                    """,
                    (nombre.upper(), rol, str(destino), hash_sha, hoy),
                )
                con.execute(
                    """
                    INSERT INTO auditoria_firmas (firma_id, accion, usuario, detalle)
                    VALUES (?, 'registro', ?, ?)
                    """,
                    (cursor.lastrowid, getpass.getuser(),
                     f"Archivo: {destino.name} · SHA-256: {hash_sha}"),
                )
        except sqlite3.Error as e:
            log.exception("Error al registrar firma")
            messagebox.showerror("Base de datos", f"No se pudo registrar la firma:\n{e}", parent=self)
            return
        messagebox.showinfo("Firma registrada", f"Firma de {nombre} registrada con SHA-256:\n{hash_sha[:32]}…")
        self.c_nombre.set("")
        self.refrescar()

    def _desactivar(self, firma_id: int) -> None:
        if not messagebox.askyesno(
            "Desactivar firma",
            "La firma quedará inactiva y NO podrá eliminarse (trazabilidad).\n¿Desea continuar?",
            parent=self,
        ):
            return
        try:
            with transaccion() as con:
                con.execute("UPDATE firmas SET activa = 0 WHERE id = ?", (firma_id,))
                con.execute(
                    """
                    INSERT INTO auditoria_firmas (firma_id, accion, usuario, detalle)
                    VALUES (?, 'desactivacion', ?, 'Desactivada desde la vista Firmas')
                    """,
                    (firma_id, getpass.getuser()),
                )
        except sqlite3.Error as e:
            log.exception("Error al desactivar firma")
            messagebox.showerror("Base de datos", f"No se pudo desactivar la firma:\n{e}", parent=self)
            return
        self.refrescar()
