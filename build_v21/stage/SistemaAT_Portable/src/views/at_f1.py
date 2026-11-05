"""
=============================================================
 Sistema AT · Instituto Peruano del Deporte (IPD - DINADAF)
 views/at_f1.py — Consolidado mensual del CAR: matrículas por
 categoría, tabla de % (auto desde AT-F3) y evaluaciones
 médica / nutrición / CAR, con doble firma.
=============================================================
"""
from __future__ import annotations

import re
from typing import Any

import customtkinter as ctk
from tkinter import messagebox

from src import database as db
from src.config import CATEGORIAS
from src.services import excel as servicio_excel
from src.theme import COLORS, FONTS
from src.widgets import (
    Card,
    FormField,
    PrimaryButton,
    SecondaryButton,
    SectionTitle,
    etiqueta_datos,
)

PATRON_PERIODO = re.compile(r"\d{4}-(0[1-9]|1[0-2])$")


class AtF1View(ctk.CTkFrame):
    """Formulario AT-F1 + listado de consolidados con generación Excel."""

    def __init__(self, master: Any, app: Any) -> None:
        super().__init__(master, fg_color="transparent")
        self.app = app
        self._construir()
        self._refrescar_tabla()

    # ------------------------------------------------------------------
    def _construir(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(self, text="AT-F1 · Consolidado mensual del CAR",
                     font=FONTS["h2"], text_color=COLORS["text_primary"]).grid(
            row=0, column=0, sticky="w", padx=28, pady=(24, 10))

        contenido = ctk.CTkScrollableFrame(self, fg_color="transparent")
        contenido.grid(row=1, column=0, sticky="nsew", padx=28, pady=(0, 24))
        contenido.grid_columnconfigure(0, weight=1)

        formulario = Card(contenido)
        formulario.pack(fill="x", pady=(0, 12))
        SectionTitle(formulario, "Datos del consolidado").pack(anchor="w", padx=18, pady=(16, 6))

        fila1 = ctk.CTkFrame(formulario, fg_color="transparent")
        fila1.pack(fill="x", padx=18, pady=4)
        self.campo_car = FormField(fila1, "CAR *", "Ej.: CAR Lima", 220)
        self.campo_periodo = FormField(fila1, "Periodo (AAAA-MM) *", "2026-01", 160)
        self.campo_jut = FormField(fila1, "JUT / Representante DINADAF", "", 260)
        self.campo_car.pack(side="left", padx=(0, 10))
        self.campo_periodo.pack(side="left", padx=(0, 10))
        self.campo_jut.pack(side="left")

        SectionTitle(formulario, "Movimiento de matrículas por categoría").pack(
            anchor="w", padx=18, pady=(10, 2))
        cabecera = ctk.CTkFrame(formulario, fg_color="transparent")
        cabecera.pack(fill="x", padx=18)
        for columna, (texto, peso) in enumerate((("Categoría", 3), ("Altas", 1), ("Bajas", 1), ("Saldo auto", 1))):
            cabecera.grid_columnconfigure(columna, weight=peso)
            etiqueta_datos(cabecera, texto, COLORS["text_secondary"]).grid(
                row=0, column=columna, sticky="ew", padx=6)
        self.campos_altas: dict[str, FormField] = {}
        self.campos_bajas: dict[str, FormField] = {}
        for categoria in CATEGORIAS:
            linea = ctk.CTkFrame(formulario, fg_color="transparent")
            linea.pack(fill="x", padx=18, pady=1)
            for columna, peso in enumerate((3, 1, 1, 1)):
                linea.grid_columnconfigure(columna, weight=peso)
            etiqueta_datos(linea, categoria).grid(row=0, column=0, sticky="ew", padx=6)
            altas = FormField(linea, "", "0", 90)
            bajas = FormField(linea, "", "0", 90)
            altas.grid(row=0, column=1, sticky="ew", padx=6)
            bajas.grid(row=0, column=2, sticky="ew", padx=6)
            saldo = FormField(linea, "", "—", 90, solo_lectura=True)
            saldo.grid(row=0, column=3, sticky="ew", padx=6)
            self.campos_altas[categoria] = altas
            self.campos_bajas[categoria] = bajas
            saldo.set("(auto)")

        self.txt_medica = self._textbox(formulario, "Evaluación médica (resumen)", 50)
        self.txt_nutricion = self._textbox(formulario, "Evaluación nutricional (resumen)", 50)
        self.txt_car = self._textbox(formulario, "Evaluación del CAR", 50)
        self.txt_observaciones = self._textbox(formulario, "Observaciones generales", 50)

        botones = ctk.CTkFrame(formulario, fg_color="transparent")
        botones.pack(fill="x", padx=18, pady=(10, 16))
        PrimaryButton(botones, "💾 Guardar consolidado", self._guardar).pack(side="left", padx=(0, 8))
        PrimaryButton(botones, "📄 Generar Excel (con firma doble)", self._generar_excel,
                      color=COLORS["success"], hover="#059669").pack(side="left", padx=(0, 8))
        SecondaryButton(botones, "🧹 Limpiar", self._limpiar).pack(side="left")

        # --- Tabla ------------------------------------------------------
        tabla_card = Card(contenido)
        tabla_card.pack(fill="x")
        SectionTitle(tabla_card, "Consolidados registrados").pack(anchor="w", padx=18, pady=(16, 6))
        self.tabla = ctk.CTkScrollableFrame(tabla_card, fg_color="transparent", height=200)
        self.tabla.pack(fill="x", padx=18, pady=(0, 16))

    def _textbox(self, padre: Any, titulo: str, alto: int) -> ctk.CTkTextbox:
        ctk.CTkLabel(padre, text=titulo, font=FONTS["small_bold"],
                     text_color=COLORS["text_secondary"], anchor="w").pack(
            fill="x", padx=18, pady=(6, 2))
        caja = ctk.CTkTextbox(padre, height=alto, font=FONTS["body"],
                              fg_color=COLORS["bg_main"], border_width=1,
                              border_color=COLORS["border"])
        caja.pack(fill="x", padx=18, pady=2)
        return caja

    # ------------------------------------------------------------------
    def _guardar(self) -> None:
        car = self.campo_car.get()
        periodo = self.campo_periodo.get()
        if not car:
            messagebox.showwarning("Falta CAR", "Indique el nombre del CAR.")
            return
        if not PATRON_PERIODO.match(periodo):
            messagebox.showerror("Periodo inválido", "Use el formato AAAA-MM (p. ej. 2026-01).")
            return
        altas: dict[str, int] = {}
        bajas: dict[str, int] = {}
        try:
            for categoria in CATEGORIAS:
                texto_altas = self.campos_altas[categoria].get() or "0"
                texto_bajas = self.campos_bajas[categoria].get() or "0"
                altas[categoria] = int(float(texto_altas))
                bajas[categoria] = int(float(texto_bajas))
        except ValueError:
            messagebox.showerror("Valores de matrícula", "Altas/Bajas deben ser números enteros.")
            return
        db.upsert_consolidado(car, periodo, {
            "matriculas": {"altas": altas, "bajas": bajas},
            "eval_medica": self.txt_medica.get("1.0", "end-1c").strip(),
            "eval_nutricion": self.txt_nutricion.get("1.0", "end-1c").strip(),
            "eval_car": self.txt_car.get("1.0", "end-1c").strip(),
            "observaciones": self.txt_observaciones.get("1.0", "end-1c").strip(),
            "jut_nombre": self.campo_jut.get(),
        })
        messagebox.showinfo("Consolidado guardado", f"AT-F1 de {car} · {periodo} guardado.")
        self._refrescar_tabla()

    def _generar_excel(self) -> None:
        car = self.campo_car.get()
        periodo = self.campo_periodo.get()
        if not car or not PATRON_PERIODO.match(periodo):
            messagebox.showwarning("Datos incompletos",
                                   "Complete CAR y periodo (o guarde primero el consolidado).")
            return
        self._guardar()
        consolidados = [c for c in db.listar_consolidados()
                        if c["car"].lower() == car.lower() and c["periodo"] == periodo]
        if not consolidados:
            messagebox.showerror("No guardado", "No se encontró el consolidado recién guardado.")
            return
        try:
            ruta = servicio_excel.generar_at_f1(int(consolidados[0]["id"]))
        except (FileNotFoundError, ValueError) as error:
            messagebox.showerror("No se pudo generar", str(error))
            return
        messagebox.showinfo("Excel generado", f"AT-F1 generado en:\n{ruta}")

    def _limpiar(self) -> None:
        for campo in (self.campo_car, self.campo_periodo, self.campo_jut):
            campo.set("")
        for categoria in CATEGORIAS:
            self.campos_altas[categoria].set("")
            self.campos_bajas[categoria].set("")
        for caja in (self.txt_medica, self.txt_nutricion, self.txt_car, self.txt_observaciones):
            caja.delete("1.0", "end")

    # ------------------------------------------------------------------
    def _refrescar_tabla(self) -> None:
        for widget in self.tabla.winfo_children():
            widget.destroy()
        consolidados = db.listar_consolidados()
        cabecera = ctk.CTkFrame(self.tabla, fg_color=COLORS["bg_main"], corner_radius=6)
        cabecera.pack(fill="x", pady=(0, 4))
        anchos = (3, 2, 3, 2)
        for columna, peso in enumerate(anchos):
            cabecera.grid_columnconfigure(columna, weight=peso)
        for columna, texto in enumerate(("CAR", "Periodo", "JUT / Representante", "Acción")):
            etiqueta_datos(cabecera, texto, COLORS["text_secondary"]).grid(
                row=0, column=columna, sticky="ew", padx=8, pady=4)
        if not consolidados:
            etiqueta_datos(self.tabla, "Sin consolidados registrados.",
                           COLORS["text_secondary"]).pack(anchor="w", pady=8)
        for consolidado in consolidados:
            linea = ctk.CTkFrame(self.tabla, fg_color="transparent")
            linea.pack(fill="x", pady=1)
            for columna, peso in enumerate(anchos):
                linea.grid_columnconfigure(columna, weight=peso)
            valores = (consolidado["car"], consolidado["periodo"], consolidado["jut_nombre"] or "—")
            for columna, valor in enumerate(valores):
                etiqueta_datos(linea, str(valor)).grid(row=0, column=columna, sticky="ew", padx=8, pady=3)
            SecondaryButton(linea, "Excel",
                            lambda c=int(consolidado["id"]): self._generar_de_tabla(c)).grid(
                row=0, column=3, sticky="e", padx=8, pady=2)

    def _generar_de_tabla(self, consolidado_id: int) -> None:
        try:
            ruta = servicio_excel.generar_at_f1(consolidado_id)
            messagebox.showinfo("Excel generado", f"AT-F1 generado en:\n{ruta}")
        except (FileNotFoundError, ValueError) as error:
            messagebox.showerror("No se pudo generar", str(error))
