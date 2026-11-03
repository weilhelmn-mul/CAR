"""
=============================================================
 Sistema AT · Instituto Peruano del Deporte (IPD - DINADAF)
 views/at_f3.py — Informe técnico mensual del deportista
 (fuente primaria de datos): objetivos, % asistencia y
 cumplimiento, resultados, horario, SISDENA y firma.
=============================================================
"""
from __future__ import annotations

import re
from typing import Any

import customtkinter as ctk
from tkinter import messagebox, filedialog

from src import database as db
from src.services import excel as servicio_excel
from src.services import pdf as servicio_pdf
from src.services import sisdena as servicio_sisdena
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


class AtF3View(ctk.CTkFrame):
    """Formulario AT-F3 + tabla del periodo con generación Excel/PDF."""

    def __init__(self, master: Any, app: Any) -> None:
        super().__init__(master, fg_color="transparent")
        self.app = app
        self._ids_deportistas: list[tuple[int, str]] = []
        self._construir()
        self._refrescar_deportistas()
        self._refrescar_tabla()

    # ------------------------------------------------------------------
    def _construir(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(self, text="AT-F3 · Informe técnico mensual del deportista",
                     font=FONTS["h2"], text_color=COLORS["text_primary"]).grid(
            row=0, column=0, sticky="w", padx=28, pady=(24, 10))

        contenido = ctk.CTkScrollableFrame(self, fg_color="transparent")
        contenido.grid(row=1, column=0, sticky="nsew", padx=28, pady=(0, 24))
        contenido.grid_columnconfigure(0, weight=1)

        # --- Formulario -------------------------------------------------
        formulario = Card(contenido)
        formulario.pack(fill="x", pady=(0, 12))
        SectionTitle(formulario, "Datos del informe").pack(anchor="w", padx=18, pady=(16, 6))

        fila1 = ctk.CTkFrame(formulario, fg_color="transparent")
        fila1.pack(fill="x", padx=18, pady=4)
        ctk.CTkLabel(fila1, text="Deportista *", font=FONTS["small_bold"],
                     text_color=COLORS["text_secondary"]).pack(anchor="w")
        self.menu_deportista = ctk.CTkOptionMenu(
            fila1, values=["— Sin deportistas —"], font=FONTS["body"], width=460,
            fg_color=COLORS["bg_main"], button_color=COLORS["accent"],
            button_hover_color=COLORS["accent_hover"], command=self._al_elegir_deportista)
        self.menu_deportista.pack(anchor="w", pady=2)

        fila2 = ctk.CTkFrame(formulario, fg_color="transparent")
        fila2.pack(fill="x", padx=18, pady=4)
        self.campo_periodo = FormField(fila2, "Periodo (AAAA-MM) *", "2026-01", 160)
        self.campo_entrenador = FormField(fila2, "Entrenador", "", 260)
        self.campo_region = FormField(fila2, "Región", "", 160)
        self.campo_periodo.pack(side="left", padx=(0, 10))
        self.campo_entrenador.pack(side="left", padx=(0, 10))
        self.campo_region.pack(side="left")

        self.txt_objetivos = self._textbox(formulario, "Objetivos del mes", 70)
        fila_pct = ctk.CTkFrame(formulario, fg_color="transparent")
        fila_pct.pack(fill="x", padx=18, pady=4)
        self.campo_asistencia = FormField(fila_pct, "% Asistencia * (95 / 95% / 0.95)", "95", 220)
        self.campo_cumplimiento = FormField(fila_pct, "% Plan cumplido * (95 / 95% / 0.95)", "90", 220)
        self.campo_asistencia.pack(side="left", padx=(0, 10))
        self.campo_cumplimiento.pack(side="left")

        self.txt_horario = self._textbox(formulario, "Horario semanal (una línea por día)", 70)
        self.txt_resultados = self._textbox(formulario, "Resultados / logros del mes", 70)
        self.txt_evaluacion = self._textbox(formulario, "Evaluación técnica", 60)

        botones = ctk.CTkFrame(formulario, fg_color="transparent")
        botones.pack(fill="x", padx=18, pady=(10, 16))
        PrimaryButton(botones, "💾 Guardar registro", self._guardar).pack(side="left", padx=(0, 8))
        PrimaryButton(botones, "📄 Generar Excel", self._generar_excel, color=COLORS["success"],
                      hover="#059669").pack(side="left", padx=(0, 8))
        PrimaryButton(botones, "🖨️ Exportar PDF", self._exportar_pdf, color=COLORS["warning"],
                      hover="#d97706").pack(side="left", padx=(0, 8))
        SecondaryButton(botones, "🥇 Importar SISDENA (Excel)", self._importar_sisdena).pack(
            side="left", padx=(0, 8))
        SecondaryButton(botones, "🧹 Limpiar", self._limpiar).pack(side="left")

        # --- Tabla del periodo ------------------------------------------
        tabla_card = Card(contenido)
        tabla_card.pack(fill="x")
        SectionTitle(tabla_card, "Registros del periodo").pack(anchor="w", padx=18, pady=(16, 6))
        filtros = ctk.CTkFrame(tabla_card, fg_color="transparent")
        filtros.pack(fill="x", padx=18, pady=(0, 8))
        self.campo_filtro_periodo = FormField(filtros, "Periodo a listar", "2026-01", 140)
        self.campo_filtro_periodo.pack(side="left")
        SecondaryButton(filtros, "Actualizar", self._refrescar_tabla).pack(side="left", padx=10, pady=12)

        self.tabla = ctk.CTkScrollableFrame(tabla_card, fg_color="transparent", height=220)
        self.tabla.pack(fill="x", padx=18, pady=(0, 16))

    def _textbox(self, padre: Any, titulo: str, alto: int) -> ctk.CTkTextbox:
        """Crea un bloque etiqueta + CTkTextbox dentro de una tarjeta."""
        ctk.CTkLabel(padre, text=titulo, font=FONTS["small_bold"],
                     text_color=COLORS["text_secondary"], anchor="w").pack(
            fill="x", padx=18, pady=(6, 2))
        caja = ctk.CTkTextbox(padre, height=alto, font=FONTS["body"],
                              fg_color=COLORS["bg_main"], border_width=1,
                              border_color=COLORS["border"])
        caja.pack(fill="x", padx=18, pady=2)
        return caja

    # ------------------------------------------------------------------
    def _refrescar_deportistas(self) -> None:
        self._ids_deportistas = db.opciones_deportistas()
        valores = [etiqueta for _id, etiqueta in self._ids_deportistas] or ["— Sin deportistas —"]
        self.menu_deportista.configure(values=valores)
        self.menu_deportista.set(valores[0])

    def _deportista_id(self) -> int | None:
        seleccion = self.menu_deportista.get()
        for id_deportista, etiqueta in self._ids_deportistas:
            if etiqueta == seleccion:
                return id_deportista
        return None

    def _al_elegir_deportista(self, etiqueta: str) -> None:
        id_deportista = self._deportista_id()
        if id_deportista is None:
            return
        deportista = db.obtener_deportista(id_deportista)
        if deportista is not None:
            if not self.campo_entrenador.get():
                self.campo_entrenador.set(deportista["entrenador"] or "")
            if not self.campo_region.get():
                self.campo_region.set(deportista["region"] or "")

    # ------------------------------------------------------------------
    def _leer_formulario(self) -> tuple[int, str, dict[str, Any]] | None:
        """Valida y empaqueta el formulario. Devuelve (id, periodo, campos) o None."""
        id_deportista = self._deportista_id()
        if id_deportista is None:
            messagebox.showwarning("Falta deportista", "Seleccione un deportista de la lista.")
            return None
        periodo = self.campo_periodo.get()
        if not PATRON_PERIODO.match(periodo):
            messagebox.showerror("Periodo inválido", "Use el formato AAAA-MM (p. ej. 2026-01).")
            return None
        try:
            pct_asistencia = servicio_excel.parsear_porcentaje(self.campo_asistencia.get())
            pct_cumplimiento = servicio_excel.parsear_porcentaje(self.campo_cumplimiento.get())
        except ValueError as error:
            messagebox.showerror("Porcentaje inválido", str(error))
            return None
        if pct_asistencia is None:
            messagebox.showerror("Falta % de asistencia", "El % de asistencia es obligatorio en AT-F3.")
            return None
        campos = {
            "objetivos": self.txt_objetivos.get("1.0", "end-1c").strip(),
            "pct_asistencia": pct_asistencia,
            "pct_cumplimiento": pct_cumplimiento,
            "resultados": self.txt_resultados.get("1.0", "end-1c").strip(),
            "horario": [l.strip() for l in self.txt_horario.get("1.0", "end-1c").splitlines() if l.strip()],
            "evaluacion": self.txt_evaluacion.get("1.0", "end-1c").strip(),
            "entrenador": self.campo_entrenador.get(),
        }
        return id_deportista, periodo, campos

    def _guardar(self) -> None:
        leido = self._leer_formulario()
        if leido is None:
            return
        id_deportista, periodo, campos = leido
        db.upsert_registro(id_deportista, periodo, **campos)
        messagebox.showinfo("Registro guardado", f"AT-F3 de {periodo} guardado correctamente.")
        self._refrescar_tabla()

    def _generar_excel(self) -> str | None:
        leido = self._leer_formulario()
        if leido is None:
            return None
        id_deportista, periodo, campos = leido
        registro_id = db.upsert_registro(id_deportista, periodo, **campos)
        try:
            ruta = servicio_excel.generar_at_f3(registro_id)
        except (FileNotFoundError, ValueError) as error:
            messagebox.showerror("No se pudo generar", str(error))
            return None
        messagebox.showinfo("Excel generado", f"AT-F3 generado en:\n{ruta}")
        self._refrescar_tabla()
        return ruta

    def _exportar_pdf(self) -> None:
        ruta = self._generar_excel()
        if ruta is None:
            return
        try:
            pdf = servicio_pdf.excel_a_pdf(ruta)
            messagebox.showinfo("PDF generado", f"PDF disponible en:\n{pdf}")
        except RuntimeError as error:
            messagebox.showwarning("PDF no generado", str(error))

    def _importar_sisdena(self) -> None:
        """Importa competencias del Excel SISDENA al deportista+periodo elegidos."""
        id_deportista = self._deportista_id()
        if id_deportista is None:
            messagebox.showwarning("Falta deportista", "Seleccione un deportista primero.")
            return
        periodo = self.campo_periodo.get()
        if not PATRON_PERIODO.match(periodo):
            messagebox.showerror("Periodo inválido", "Use el formato AAAA-MM (p. ej. 2026-01).")
            return
        ruta = filedialog.askopenfilename(
            title="Seleccionar reporte SISDENA",
            filetypes=[("Archivos Excel", "*.xlsx *.xlsm"), ("Todos", "*.*")])
        if not ruta:
            return
        try:
            competencias = servicio_sisdena.importar_competencias_desde_excel(ruta)
        except (ValueError, FileNotFoundError) as error:
            messagebox.showerror("Importación SISDENA", str(error))
            return
        aplicadas, no_encontrados = 0, []
        for competencia in competencias:
            objetivo = db.buscar_deportista_por_nombre(competencia["deportista"])
            if objetivo is not None and int(objetivo["id"]) == id_deportista:
                db.agregar_pruebas_sisdena(id_deportista, periodo, [competencia])
                aplicadas += 1
            else:
                no_encontrados.append(competencia["deportista"] or "(vacío)")
        mensaje = f"Se aplicaron {aplicadas} competencia(s) a este deportista en {periodo}."
        if no_encontrados:
            mensaje += "\n\nNombres sin coincidencia (revíselos):\n" + "\n".join(sorted(set(no_encontrados)))
        messagebox.showinfo("Importación SISDENA", mensaje)

    def _limpiar(self) -> None:
        for campo in (self.campo_periodo, self.campo_entrenador, self.campo_region,
                      self.campo_asistencia, self.campo_cumplimiento):
            campo.set("")
        for caja in (self.txt_objetivos, self.txt_horario, self.txt_resultados, self.txt_evaluacion):
            caja.delete("1.0", "end")

    # ------------------------------------------------------------------
    def _refrescar_tabla(self) -> None:
        for widget in self.tabla.winfo_children():
            widget.destroy()
        periodo = self.campo_filtro_periodo.get()
        registros = db.listar_registros(periodo=periodo if PATRON_PERIODO.match(periodo) else "")
        cabecera = ctk.CTkFrame(self.tabla, fg_color=COLORS["bg_main"], corner_radius=6)
        cabecera.pack(fill="x", pady=(0, 4))
        anchos = (4, 2, 2, 2, 2)
        for columna, peso in enumerate(anchos):
            cabecera.grid_columnconfigure(columna, weight=peso)
        for columna, texto in enumerate(("Deportista", "Cat.", "Periodo", "% Asist.", "% Cumpl.")):
            etiqueta_datos(cabecera, texto, COLORS["text_secondary"]).grid(
                row=0, column=columna, sticky="ew", padx=8, pady=4)
        if not registros:
            etiqueta_datos(self.tabla, "Sin registros para el periodo indicado.",
                           COLORS["text_secondary"]).pack(anchor="w", pady=8)
        for registro in registros:
            linea = ctk.CTkFrame(self.tabla, fg_color="transparent")
            linea.pack(fill="x", pady=1)
            for columna, peso in enumerate(anchos):
                linea.grid_columnconfigure(columna, weight=peso)
            asist = f"{registro['pct_asistencia']:.0%}" if registro["pct_asistencia"] is not None else "—"
            cump = f"{registro['pct_cumplimiento']:.0%}" if registro["pct_cumplimiento"] is not None else "—"
            valores = (registro["nombre"], registro["categoria"], registro["periodo"], asist, cump)
            for columna, valor in enumerate(valores):
                etiqueta_datos(linea, str(valor)).grid(row=0, column=columna, sticky="ew", padx=8, pady=3)
            SecondaryButton(linea, "Excel",
                            lambda r=int(registro["id"]): self._generar_de_tabla(r)).grid(
                row=0, column=5, sticky="e", padx=8, pady=2)

    def _generar_de_tabla(self, registro_id: int) -> None:
        try:
            ruta = servicio_excel.generar_at_f3(registro_id)
            messagebox.showinfo("Excel generado", f"AT-F3 generado en:\n{ruta}")
        except (FileNotFoundError, ValueError) as error:
            messagebox.showerror("No se pudo generar", str(error))
