"""
=============================================================
 Sistema AT · Instituto Peruano del Deporte (IPD - DINADAF)
 views/at_f8.py — Plan mensual de trabajo del JUT (mes
 siguiente): editor de tareas (N°, actividad, fecha, hora,
 lugar, observaciones) + generación Excel con firma JUT.
=============================================================
"""
from __future__ import annotations

import re
from typing import Any

import customtkinter as ctk
from tkinter import messagebox

from src import database as db
from src.services import excel as servicio_excel
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

PATRON_PERIODO = re.compile(r"\d{4}-(0[1-9]|1[0-2])$")


class AtF8View(ctk.CTkFrame):
    """Editor de plan AT-F8 + listado de planes con generación Excel."""

    def __init__(self, master: Any, app: Any) -> None:
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.plan_id: int | None = None
        self._construir()
        self._refrescar_tabla()

    # ------------------------------------------------------------------
    def _construir(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(self, text="AT-F8 · Plan mensual de trabajo del JUT",
                     font=FONTS["h2"], text_color=COLORS["text_primary"]).grid(
            row=0, column=0, sticky="w", padx=28, pady=(24, 10))

        contenido = ctk.CTkScrollableFrame(self, fg_color="transparent")
        contenido.grid(row=1, column=0, sticky="nsew", padx=28, pady=(0, 24))
        contenido.grid_columnconfigure(0, weight=1)

        formulario = Card(contenido)
        formulario.pack(fill="x", pady=(0, 12))
        SectionTitle(formulario, "Datos del plan").pack(anchor="w", padx=18, pady=(16, 6))

        fila1 = ctk.CTkFrame(formulario, fg_color="transparent")
        fila1.pack(fill="x", padx=18, pady=4)
        self.campo_jut = FormField(fila1, "JUT (Jefe de Unidad Técnica) *", "Nombre completo", 260)
        self.campo_car = FormField(fila1, "CAR", "Ej.: CAR Lima", 200)
        self.campo_periodo = FormField(fila1, "Periodo planificado (AAAA-MM) *", "2026-02", 200)
        self.campo_jut.pack(side="left", padx=(0, 10))
        self.campo_car.pack(side="left", padx=(0, 10))
        self.campo_periodo.pack(side="left")

        SectionTitle(formulario, "Tareas planificadas").pack(anchor="w", padx=18, pady=(10, 2))
        cabecera = ctk.CTkFrame(formulario, fg_color="transparent")
        cabecera.pack(fill="x", padx=18)
        anchos = ((2, "N°"), (5, "Actividad"), (2, "Fecha"), (1, "Hora"), (2, "Lugar"), (3, "Observaciones"))
        for columna, (peso, texto) in enumerate(anchos):
            cabecera.grid_columnconfigure(columna, weight=peso)
            etiqueta_datos(cabecera, texto, COLORS["text_secondary"]).grid(
                row=0, column=columna, sticky="ew", padx=4)
        self.contenedor_tareas = ctk.CTkFrame(formulario, fg_color="transparent")
        self.contenedor_tareas.pack(fill="x", padx=18, pady=2)
        SecondaryButton(formulario, "➕ Añadir tarea", self._agregar_fila).pack(
            anchor="w", padx=18, pady=6)

        botones = ctk.CTkFrame(formulario, fg_color="transparent")
        botones.pack(fill="x", padx=18, pady=(8, 16))
        PrimaryButton(botones, "💾 Guardar plan", self._guardar).pack(side="left", padx=(0, 8))
        PrimaryButton(botones, "📄 Generar Excel", self._generar_excel, color=COLORS["success"],
                      hover="#059669").pack(side="left", padx=(0, 8))
        SecondaryButton(botones, "🧹 Nuevo plan", self._limpiar).pack(side="left")

        tabla_card = Card(contenido)
        tabla_card.pack(fill="x")
        SectionTitle(tabla_card, "Planes registrados (clic en una fila para editar)").pack(
            anchor="w", padx=18, pady=(16, 6))
        self.tabla = ctk.CTkScrollableFrame(tabla_card, fg_color="transparent", height=200)
        self.tabla.pack(fill="x", padx=18, pady=(0, 16))

        for _ in range(3):  # filas iniciales por comodidad
            self._agregar_fila()

    # ------------------------------------------------------------------
    def _agregar_fila(self, datos: dict[str, Any] | None = None) -> None:
        """Añade una fila editable de tarea al editor (opcionalmente precargada)."""
        numero = len(self.filas_tareas) + 1
        linea = ctk.CTkFrame(self.contenedor_tareas, fg_color="transparent")
        linea.pack(fill="x", pady=1)
        pesos = [2, 5, 2, 1, 2, 3]
        for columna, peso in enumerate(pesos):
            linea.grid_columnconfigure(columna, weight=peso)
        etiqueta_numero = etiqueta_datos(linea, str(datos.get("n", numero)) if datos else str(numero))
        etiqueta_numero.grid(row=0, column=0, sticky="ew", padx=4)

        def campo(ancho_placeholder: str = "") -> ctk.CTkEntry:
            entrada = ctk.CTkEntry(linea, placeholder_text=ancho_placeholder, font=FONTS["small"],
                                   fg_color=COLORS["bg_main"], border_color=COLORS["border"])
            return entrada

        entradas = {
            "actividad": campo("Actividad"),
            "fecha": campo("dd/mm"),
            "hora": campo("hh:mm"),
            "lugar": campo("Lugar"),
            "obs": campo("Observaciones"),
        }
        posiciones = {"actividad": 1, "fecha": 2, "hora": 3, "lugar": 4, "obs": 5}
        for clave, entrada in entradas.items():
            entrada.grid(row=0, column=posiciones[clave], sticky="ew", padx=4, pady=2)
            if datos:
                entrada.insert(0, str(datos.get(clave, "")))
        DangerButton(linea, "✕", lambda: self._quitar_fila(linea, marco)).grid(
            row=0, column=6, sticky="e", padx=4, pady=2)
        marco = {"linea": linea, "entradas": entradas, "numero": etiqueta_numero}
        self.filas_tareas.append(marco)
        self._renumerar()

    def _quitar_fila(self, linea: ctk.CTkFrame, marco: dict[str, Any]) -> None:
        if marco in self.filas_tareas:
            self.filas_tareas.remove(marco)
        linea.destroy()
        self._renumerar()

    def _renumerar(self) -> None:
        for indice, marco in enumerate(self.filas_tareas, start=1):
            marco["numero"].configure(text=str(indice))

    @property
    def filas_tareas(self) -> list[dict[str, Any]]:
        """Filas actuales del editor (inicializadas de forma perezosa)."""
        if not hasattr(self, "_filas_tareas"):
            self._filas_tareas: list[dict[str, Any]] = []
        return self._filas_tareas

    # ------------------------------------------------------------------
    def _leer_tareas(self) -> list[dict[str, Any]]:
        tareas: list[dict[str, Any]] = []
        for indice, marco in enumerate(self.filas_tareas, start=1):
            valores = {clave: entrada.get().strip() for clave, entrada in marco["entradas"].items()}
            if not valores["actividad"]:
                continue  # filas sin actividad se descartan
            tareas.append({"n": len(tareas) + 1, **valores})
        return tareas

    def _guardar(self) -> str | None:
        jut = self.campo_jut.get()
        periodo = self.campo_periodo.get()
        if not jut:
            messagebox.showwarning("Falta JUT", "Indique el nombre del JUT.")
            return None
        if not PATRON_PERIODO.match(periodo):
            messagebox.showerror("Periodo inválido", "Use el formato AAAA-MM (p. ej. 2026-02).")
            return None
        tareas = self._leer_tareas()
        if not tareas:
            messagebox.showwarning("Sin tareas", "Añada al menos una tarea con actividad.")
            return None
        plan_id = db.upsert_plan(jut, periodo, self.campo_car.get(), tareas)
        messagebox.showinfo("Plan guardado", f"AT-F8 de {jut} · {periodo} guardado ({len(tareas)} tareas).")
        self.plan_id = plan_id
        self._refrescar_tabla()
        return str(plan_id)

    def _generar_excel(self) -> None:
        if self._guardar() is None:
            return
        try:
            ruta = servicio_excel.generar_at_f8(int(self.plan_id or 0))
        except (FileNotFoundError, ValueError) as error:
            messagebox.showerror("No se pudo generar", str(error))
            return
        messagebox.showinfo("Excel generado", f"AT-F8 generado en:\n{ruta}")

    def _limpiar(self) -> None:
        self.plan_id = None
        for campo in (self.campo_jut, self.campo_car, self.campo_periodo):
            campo.set("")
        for marco in list(self.filas_tareas):
            marco["linea"].destroy()
        self.filas_tareas.clear()
        for _ in range(3):
            self._agregar_fila()

    # ------------------------------------------------------------------
    def _refrescar_tabla(self) -> None:
        for widget in self.tabla.winfo_children():
            widget.destroy()
        planes = db.listar_planes()
        cabecera = ctk.CTkFrame(self.tabla, fg_color=COLORS["bg_main"], corner_radius=6)
        cabecera.pack(fill="x", pady=(0, 4))
        anchos = (3, 2, 2, 2)
        for columna, peso in enumerate(anchos):
            cabecera.grid_columnconfigure(columna, weight=peso)
        for columna, texto in enumerate(("JUT", "CAR", "Periodo", "Acción")):
            etiqueta_datos(cabecera, texto, COLORS["text_secondary"]).grid(
                row=0, column=columna, sticky="ew", padx=8, pady=4)
        if not planes:
            etiqueta_datos(self.tabla, "Sin planes registrados.",
                           COLORS["text_secondary"]).pack(anchor="w", pady=8)
        for plan in planes:
            linea = ctk.CTkFrame(self.tabla, fg_color="transparent")
            linea.pack(fill="x", pady=1)
            for columna, peso in enumerate(anchos):
                linea.grid_columnconfigure(columna, weight=peso)
            valores = (plan["jut_nombre"], plan["car"] or "—", plan["periodo"])
            for columna, valor in enumerate(valores):
                etiqueta_datos(linea, str(valor)).grid(row=0, column=columna, sticky="ew", padx=8, pady=3)
            SecondaryButton(linea, "Excel",
                            lambda p=int(plan["id"]): self._generar_de_tabla(p)).grid(
                row=0, column=3, sticky="e", padx=4, pady=2)
            SecondaryButton(linea, "Editar",
                            lambda p=int(plan["id"]): self._cargar_plan(p)).grid(
                row=0, column=4, sticky="e", padx=4, pady=2)

    def _cargar_plan(self, plan_id: int) -> None:
        plan = db.obtener_plan(plan_id)
        if plan is None:
            return
        self.plan_id = plan_id
        self.campo_jut.set(plan["jut_nombre"])
        self.campo_car.set(plan["car"] or "")
        self.campo_periodo.set(plan["periodo"])
        for marco in list(self.filas_tareas):
            marco["linea"].destroy()
        self.filas_tareas.clear()
        for tarea in db.tareas_del_plan(plan_id):
            self._agregar_fila(tarea)

    def _generar_de_tabla(self, plan_id: int) -> None:
        try:
            ruta = servicio_excel.generar_at_f8(plan_id)
            messagebox.showinfo("Excel generado", f"AT-F8 generado en:\n{ruta}")
        except (FileNotFoundError, ValueError) as error:
            messagebox.showerror("No se pudo generar", str(error))
