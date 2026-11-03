"""
=============================================================
 Sistema AT · Instituto Peruano del Deporte (IPD - DINADAF)
 views/deportistas.py — ABM de deportistas con filtros, baja/
 reactivación lógica (nunca se borran registros).
=============================================================
"""
from __future__ import annotations

from typing import Any

import customtkinter as ctk
from tkinter import messagebox

from src import database as db
from src.config import CATEGORIAS, SEXOS
from src.theme import COLORS, FONTS
from src.widgets import (
    Card,
    DangerButton,
    FormField,
    PrimaryButton,
    SecondaryButton,
    SectionTitle,
    etiqueta_datos,
)


class DeportistasView(ctk.CTkFrame):
    """Formulario + tabla de deportistas del CAR."""

    def __init__(self, master: Any, app: Any) -> None:
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.seleccion_id: int | None = None
        self._construir()
        self._refrescar_tabla()

    # ------------------------------------------------------------------
    def _construir(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(self, text="Deportistas", font=FONTS["h2"],
                     text_color=COLORS["text_primary"]).grid(
            row=0, column=0, sticky="w", padx=28, pady=(24, 10))

        contenido = ctk.CTkFrame(self, fg_color="transparent")
        contenido.grid(row=1, column=0, sticky="nsew", padx=28, pady=(0, 24))
        contenido.grid_columnconfigure(0, weight=0)
        contenido.grid_columnconfigure(1, weight=1)
        contenido.grid_rowconfigure(0, weight=1)

        # --- Formulario -------------------------------------------------
        formulario = Card(contenido, width=320)
        formulario.grid(row=0, column=0, sticky="ns", padx=(0, 10))
        formulario.pack_propagate(False)
        SectionTitle(formulario, "Datos del deportista").pack(anchor="w", padx=18, pady=(16, 6))

        self.campo_nombre = FormField(formulario, "Apellidos y nombres *", "Ej.: QUISPE, María", 260)
        self.campo_documento = FormField(formulario, "DNI / Carné", "8 dígitos", 260)
        self.campo_deporte = FormField(formulario, "Deporte *", "Ej.: Atletismo", 260)
        self.campo_nombre.pack(fill="x", padx=18, pady=4)
        self.campo_documento.pack(fill="x", padx=18, pady=4)
        self.campo_deporte.pack(fill="x", padx=18, pady=4)

        ctk.CTkLabel(formulario, text="Categoría *", font=FONTS["small_bold"],
                     text_color=COLORS["text_secondary"], anchor="w").pack(fill="x", padx=18, pady=(6, 2))
        self.menu_categoria = ctk.CTkOptionMenu(
            formulario, values=list(CATEGORIAS), font=FONTS["body"],
            fg_color=COLORS["bg_main"], button_color=COLORS["accent"],
            button_hover_color=COLORS["accent_hover"])
        self.menu_categoria.pack(fill="x", padx=18, pady=2)

        ctk.CTkLabel(formulario, text="Sexo *", font=FONTS["small_bold"],
                     text_color=COLORS["text_secondary"], anchor="w").pack(fill="x", padx=18, pady=(6, 2))
        self.menu_sexo = ctk.CTkOptionMenu(
            formulario, values=["D · Damas", "V · Varones"], font=FONTS["body"],
            fg_color=COLORS["bg_main"], button_color=COLORS["accent"],
            button_hover_color=COLORS["accent_hover"])
        self.menu_sexo.set("D · Damas")
        self.menu_sexo.pack(fill="x", padx=18, pady=2)

        self.campo_car = FormField(formulario, "CAR", "Ej.: CAR Lima", 260)
        self.campo_region = FormField(formulario, "Región", "Ej.: Lima", 260)
        self.campo_entrenador = FormField(formulario, "Entrenador", "Nombre completo", 260)
        self.campo_car.pack(fill="x", padx=18, pady=4)
        self.campo_region.pack(fill="x", padx=18, pady=4)
        self.campo_entrenador.pack(fill="x", padx=18, pady=4)

        botones = ctk.CTkFrame(formulario, fg_color="transparent")
        botones.pack(fill="x", padx=18, pady=(12, 16))
        PrimaryButton(botones, "💾 Guardar", self._guardar).pack(fill="x", pady=3)
        SecondaryButton(botones, "🧹 Limpiar formulario", self._limpiar).pack(fill="x", pady=3)
        SecondaryButton(botones, "⬇️ Dar baja (desactivar)", self._dar_baja).pack(fill="x", pady=3)
        SecondaryButton(botones, "⬆️ Reactivar", self._reactivar).pack(fill="x", pady=3)
        DangerButton(botones, "🗑️ Eliminar selección", self._recordar_baja_logica).pack(fill="x", pady=3)

        # --- Tabla ------------------------------------------------------
        tabla_card = Card(contenido)
        tabla_card.grid(row=0, column=1, sticky="nsew")
        SectionTitle(tabla_card, "Listado").pack(anchor="w", padx=18, pady=(16, 6))

        filtros = ctk.CTkFrame(tabla_card, fg_color="transparent")
        filtros.pack(fill="x", padx=18, pady=(0, 8))
        self.busqueda = FormField(filtros, "Buscar por nombre", "", 240)
        self.busqueda.pack(side="left", padx=(0, 8))
        self.menu_filtro_categoria = ctk.CTkOptionMenu(
            filtros, values=["Todas", *CATEGORIAS], font=FONTS["body"],
            fg_color=COLORS["bg_main"], button_color=COLORS["accent"],
            button_hover_color=COLORS["accent_hover"], command=lambda _v: self._refrescar_tabla())
        self.menu_filtro_categoria.set("Todas")
        self.menu_filtro_categoria.pack(side="left", padx=(0, 8))
        self._boton_inactivos = SecondaryButton(filtros, "Mostrar inactivos", self._alternar_inactivos)
        self._boton_inactivos.pack(side="left")
        self.ver_inactivos = False

        self.tabla = ctk.CTkScrollableFrame(tabla_card, fg_color="transparent")
        self.tabla.pack(fill="both", expand=True, padx=18, pady=(0, 16))

    # ------------------------------------------------------------------
    def _alternar_inactivos(self) -> None:
        """Alterna entre mostrar solo activos o incluir también los inactivos."""
        self.ver_inactivos = not self.ver_inactivos
        texto = "Mostrar solo activos" if self.ver_inactivos else "Mostrar inactivos"
        self._boton_inactivos.configure(text=texto)
        self._refrescar_tabla()

    def _refrescar_tabla(self) -> None:
        """Vuelve a dibujar la tabla aplicando los filtros vigentes."""
        for widget in self.tabla.winfo_children():
            widget.destroy()
        categoria = "" if self.menu_filtro_categoria.get() == "Todas" else self.menu_filtro_categoria.get()
        filas = db.listar_deportistas(solo_activos=not self.ver_inactivos,
                                      categoria=categoria, texto=self.busqueda.get())
        cabecera = ctk.CTkFrame(self.tabla, fg_color=COLORS["bg_main"], corner_radius=6)
        cabecera.pack(fill="x", pady=(0, 4))
        anchos = (4, 2, 2, 3, 3, 2)
        for columna, peso in enumerate(anchos):
            cabecera.grid_columnconfigure(columna, weight=peso)
        for columna, texto in enumerate(("Nombre", "Cat.", "Sexo", "Deporte", "CAR", "Estado")):
            etiqueta_datos(cabecera, texto, COLORS["text_secondary"]).grid(
                row=0, column=columna, sticky="ew", padx=8, pady=4)
        if not filas:
            etiqueta_datos(self.tabla, "Sin resultados.", COLORS["text_secondary"]).pack(anchor="w", pady=8)
        for fila in filas:
            linea = ctk.CTkFrame(self.tabla, fg_color="transparent",
                                 corner_radius=6)
            linea.pack(fill="x", pady=1)
            for columna, peso in enumerate(anchos):
                linea.grid_columnconfigure(columna, weight=peso)
            estado = "Activo" if fila["activo"] else "Inactivo"
            color_estado = COLORS["success"] if fila["activo"] else COLORS["danger"]
            valores = (fila["nombre"], fila["categoria"],
                       SEXOS.get(fila["sexo"], fila["sexo"]), fila["deporte"],
                       fila["car"] or "—", estado)
            for columna, valor in enumerate(valores):
                color = color_estado if columna == 5 else None
                etiqueta_datos(linea, str(valor), color).grid(row=0, column=columna, sticky="ew", padx=8, pady=3)
            linea.bind("<Button-1>", lambda _e, f=fila: self._cargar_formulario(int(f["id"])))
            for hijo in linea.winfo_children():
                hijo.bind("<Button-1>", lambda _e, f=fila: self._cargar_formulario(int(f["id"])))

    def _cargar_formulario(self, deportista_id: int) -> None:
        """Carga el deportista seleccionado en el formulario para editar."""
        fila = db.obtener_deportista(deportista_id)
        if fila is None:
            return
        self.seleccion_id = deportista_id
        self.campo_nombre.set(fila["nombre"])
        self.campo_documento.set(fila["documento"] or "")
        self.campo_deporte.set(fila["deporte"])
        self.menu_categoria.set(fila["categoria"])
        self.menu_sexo.set(f"D · Damas" if fila["sexo"] == "D" else "V · Varones")
        self.campo_car.set(fila["car"] or "")
        self.campo_region.set(fila["region"] or "")
        self.campo_entrenador.set(fila["entrenador"] or "")

    def _datos_formulario(self) -> dict[str, str] | None:
        """Valida y empaqueta los campos; devuelve None mostrando el error."""
        datos = {
            "nombre": self.campo_nombre.get(),
            "documento": self.campo_documento.get(),
            "deporte": self.campo_deporte.get(),
            "categoria": self.menu_categoria.get(),
            "sexo": "D" if self.menu_sexo.get().startswith("D") else "V",
            "car": self.campo_car.get(),
            "region": self.campo_region.get(),
            "entrenador": self.campo_entrenador.get(),
        }
        if not datos["nombre"] or not datos["deporte"]:
            messagebox.showwarning("Campos obligatorios",
                                   "Complete al menos 'Apellidos y nombres' y 'Deporte'.")
            return None
        return datos

    def _guardar(self) -> None:
        """Crea o actualiza el deportista según haya selección previa."""
        datos = self._datos_formulario()
        if datos is None:
            return
        if self.seleccion_id is None:
            db.crear_deportista(datos)
            messagebox.showinfo("Deportista registrado", f"«{datos['nombre']}» se registró correctamente.")
        else:
            db.actualizar_deportista(self.seleccion_id, datos)
            messagebox.showinfo("Deportista actualizado", "Los cambios se guardaron correctamente.")
        self._limpiar()
        self._refrescar_tabla()

    def _limpiar(self) -> None:
        self.seleccion_id = None
        for campo in (self.campo_nombre, self.campo_documento, self.campo_deporte,
                      self.campo_car, self.campo_region, self.campo_entrenador):
            campo.set("")
        self.menu_categoria.set(CATEGORIAS[0])
        self.menu_sexo.set("D · Damas")

    def _dar_baja(self) -> None:
        if self.seleccion_id is None:
            messagebox.showinfo("Seleccione un deportista", "Haga clic en una fila de la tabla primero.")
            return
        db.cambiar_estado_deportista(self.seleccion_id, activo=False)
        messagebox.showinfo("Baja registrada", "El deportista quedó inactivo (sus registros se conservan).")
        self._limpiar()
        self._refrescar_tabla()

    def _reactivar(self) -> None:
        if self.seleccion_id is None:
            messagebox.showinfo("Seleccione un deportista", "Haga clic en una fila de la tabla primero.")
            return
        db.cambiar_estado_deportista(self.seleccion_id, activo=True)
        self._limpiar()
        self._refrescar_tabla()

    def _recordar_baja_logica(self) -> None:
        """El botón rojo no borra: recuerda que la baja es lógica (política de datos)."""
        messagebox.showinfo("Eliminación no permitida",
                            "Los deportistas nunca se eliminan: use «Dar baja (desactivar)» "
                            "para conservar el historial de formatos.")
