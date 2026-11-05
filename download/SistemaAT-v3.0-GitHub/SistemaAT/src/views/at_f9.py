"""
=============================================================
 Sistema AT · Instituto Peruano del Deporte (IPD - DINADAF)
 views/at_f9.py — Evaluación del plan AT-F8 del mes anterior:
 carga automática del plan, promedios AT-F3, marcado de tareas
 cumplidas, visita técnica y calificación BUENO/REGULAR/MALO.
=============================================================
"""
from __future__ import annotations

from typing import Any

import customtkinter as ctk
from tkinter import messagebox

from src import database as db
from src.config import CALIFICACIONES
from src.services import excel as servicio_excel
from src.services import pdf as servicio_pdf
from src.theme import COLORS, FONTS
from src.widgets import (
    Card,
    FormField,
    PrimaryButton,
    SecondaryButton,
    SectionTitle,
    etiqueta_datos,
)


class AtF9View(ctk.CTkFrame):
    """Formulario AT-F9 con precarga automática del plan seleccionado."""

    def __init__(self, master: Any, app: Any) -> None:
        super().__init__(master, fg_color="transparent")
        self.app = app
        self._planes: dict[str, Any] = {}  # etiqueta -> fila plan
        self._checks: list[tuple[int, ctk.BooleanVar]] = []  # (n tarea, cumplida?)
        self._construir()
        self._refrescar_planes()

    # ------------------------------------------------------------------
    def _construir(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(self, text="AT-F9 · Evaluación del plan del mes anterior",
                     font=FONTS["h2"], text_color=COLORS["text_primary"]).grid(
            row=0, column=0, sticky="w", padx=28, pady=(24, 10))

        contenido = ctk.CTkScrollableFrame(self, fg_color="transparent")
        contenido.grid(row=1, column=0, sticky="nsew", padx=28, pady=(0, 24))
        contenido.grid_columnconfigure(0, weight=1)

        formulario = Card(contenido)
        formulario.pack(fill="x", pady=(0, 12))
        SectionTitle(formulario, "Plan a evaluar (AT-F8 del mes anterior)").pack(
            anchor="w", padx=18, pady=(16, 6))
        ctk.CTkLabel(formulario, text="Plan AT-F8", font=FONTS["small_bold"],
                     text_color=COLORS["text_secondary"], anchor="w").pack(fill="x", padx=18)
        self.menu_planes = ctk.CTkOptionMenu(
            formulario, values=["— Sin planes —"], font=FONTS["body"], width=480,
            fg_color=COLORS["bg_main"], button_color=COLORS["accent"],
            button_hover_color=COLORS["accent_hover"], command=lambda _v: self._cargar_plan())
        self.menu_planes.pack(anchor="w", pady=(2, 8))
        self.etiqueta_auto = ctk.CTkLabel(formulario, text="", font=FONTS["small"],
                                          text_color=COLORS["text_secondary"], anchor="w",
                                          justify="left", wraplength=760)
        self.etiqueta_auto.pack(fill="x", padx=18, pady=(0, 8))

        SectionTitle(formulario, "Tareas del plan — marque las CUMPLIDAS").pack(
            anchor="w", padx=18, pady=(6, 2))
        self.contenedor_tareas = ctk.CTkFrame(formulario, fg_color="transparent")
        self.contenedor_tareas.pack(fill="x", padx=18, pady=(0, 8))

        SectionTitle(formulario, "Indicadores (AT-F3 promedio — automático)").pack(
            anchor="w", padx=18, pady=(6, 2))
        self.etiqueta_promedios = ctk.CTkLabel(formulario, text="—", font=FONTS["body"],
                                               text_color=COLORS["text_primary"], anchor="w",
                                               justify="left")
        self.etiqueta_promedios.pack(fill="x", padx=18, pady=(0, 6))

        fila_visita = ctk.CTkFrame(formulario, fg_color="transparent")
        fila_visita.pack(fill="x", padx=18, pady=4)
        self.campo_fecha_visita = FormField(fila_visita, "Fecha de visita técnica (dd/mm/aaaa)", "", 220)
        self.campo_realizado_por = FormField(fila_visita, "Visita realizada por", "", 240)
        self.campo_fecha_visita.pack(side="left", padx=(0, 10))
        self.campo_realizado_por.pack(side="left")
        self.txt_obs_visita = self._textbox(formulario, "Observaciones de la visita técnica", 60)

        fila_calif = ctk.CTkFrame(formulario, fg_color="transparent")
        fila_calif.pack(fill="x", padx=18, pady=4)
        ctk.CTkLabel(fila_calif, text="Calificación final *", font=FONTS["small_bold"],
                     text_color=COLORS["text_secondary"]).pack(anchor="w")
        self.menu_calificacion = ctk.CTkOptionMenu(
            fila_calif, values=list(CALIFICACIONES), font=FONTS["body"], width=220,
            fg_color=COLORS["bg_main"], button_color=COLORS["accent"],
            button_hover_color=COLORS["accent_hover"])
        self.menu_calificacion.set("REGULAR")
        self.menu_calificacion.pack(anchor="w", pady=2)
        self.txt_opinion = self._textbox(
            formulario, "Opinión del Presidente FDN (opcional — habilita su firma)", 60)

        botones = ctk.CTkFrame(formulario, fg_color="transparent")
        botones.pack(fill="x", padx=18, pady=(10, 16))
        PrimaryButton(botones, "💾 Guardar evaluación", self._guardar).pack(side="left", padx=(0, 8))
        PrimaryButton(botones, "📄 Generar Excel", self._generar_excel, color=COLORS["success"],
                      hover="#059669").pack(side="left", padx=(0, 8))
        PrimaryButton(botones, "🖨️ Exportar PDF", self._exportar_pdf, color=COLORS["warning"],
                      hover="#d97706").pack(side="left", padx=(0, 8))

        tabla_card = Card(contenido)
        tabla_card.pack(fill="x")
        SectionTitle(tabla_card, "Evaluaciones registradas").pack(anchor="w", padx=18, pady=(16, 6))
        self.tabla = ctk.CTkScrollableFrame(tabla_card, fg_color="transparent", height=180)
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
    def _refrescar_planes(self) -> None:
        self._planes = {}
        for plan in db.listar_planes():
            etiqueta = f"{plan['jut_nombre']} · {plan['periodo']}"
            self._planes[etiqueta] = plan
        valores = list(self._planes.keys()) or ["— Sin planes —"]
        self.menu_planes.configure(values=valores)
        self.menu_planes.set(valores[0])
        self._cargar_plan()

    def _plan_actual(self) -> Any:
        return self._planes.get(self.menu_planes.get())

    def _cargar_plan(self) -> None:
        """Precarga tareas (checkboxes), promedios AT-F3 y evaluación previa."""
        for widget in self.contenedor_tareas.winfo_children():
            widget.destroy()
        self._checks = []
        plan = self._plan_actual()
        if plan is None:
            self.etiqueta_auto.configure(text="Registre primero un plan AT-F8.")
            self.etiqueta_promedios.configure(text="—")
            return
        tareas = db.tareas_del_plan(int(plan["id"]))
        self.etiqueta_auto.configure(
            text=f"Plan: {plan['jut_nombre']} · CAR {plan['car'] or '—'} · periodo {plan['periodo']} · "
                 f"{len(tareas)} tarea(s)")
        for tarea in tareas:
            variable = ctk.BooleanVar(value=False)
            casilla = ctk.CTkCheckBox(
                self.contenedor_tareas, text=f"{tarea.get('n', '')}. {tarea.get('actividad', '')}"
                                            f" ({tarea.get('fecha', '')})", variable=variable,
                font=FONTS["small"], text_color=COLORS["text_primary"])
            casilla.pack(anchor="w", padx=8, pady=2)
            self._checks.append((int(tarea.get("n", 0)), variable))

        promedios = db.promedios_periodo(plan["car"] or "", plan["periodo"])
        if promedios["n"]:
            texto_asist = f"{promedios['pct_asistencia']:.0%}" if promedios["pct_asistencia"] is not None else "—"
            texto_cump = f"{promedios['pct_cumplimiento']:.0%}" if promedios["pct_cumplimiento"] is not None else "—"
            self.etiqueta_promedios.configure(
                text=f"% Asistencia promedio: {texto_asist}    ·    % Cumplimiento promedio: {texto_cump}    "
                     f"·    Registros considerados: {promedios['n']}")
        else:
            self.etiqueta_promedios.configure(
                text="Sin registros AT-F3 del periodo; los promedios quedarán vacíos.")

        previa = db.obtener_evaluacion_por_plan(int(plan["id"]))
        if previa is not None:
            self.campo_fecha_visita.set(previa["fecha_visita"] or "")
            self.campo_realizado_por.set(previa["realizado_por"] or "")
            self.txt_obs_visita.delete("1.0", "end")
            self.txt_obs_visita.insert("1.0", previa["obs_visita"] or "")
            self.menu_calificacion.set(previa["calificacion_final"])
            self.txt_opinion.delete("1.0", "end")
            self.txt_opinion.insert("1.0", previa["opinion_presidente"] or "")
            cumplidas_previas = int(previa["tareas_cumplidas"] or 0)
            for indice, (_n, variable) in enumerate(self._checks):
                if indice < cumplidas_previas:
                    variable.set(True)
        else:
            for campo in (self.campo_fecha_visita, self.campo_realizado_por):
                campo.set("")
            for caja in (self.txt_obs_visita, self.txt_opinion):
                caja.delete("1.0", "end")
            self.menu_calificacion.set("REGULAR")
            for _n, variable in self._checks:
                variable.set(False)
        self._refrescar_tabla()

    # ------------------------------------------------------------------
    def _guardar(self) -> int | None:
        plan = self._plan_actual()
        if plan is None:
            messagebox.showwarning("Sin plan", "Seleccione un plan AT-F8 para evaluar.")
            return None
        programadas = len(self._checks)
        cumplidas = sum(1 for _n, variable in self._checks if variable.get())
        pct_tareas = (cumplidas / programadas) if programadas else None
        promedios = db.promedios_periodo(plan["car"] or "", plan["periodo"])
        evaluacion_id = db.upsert_evaluacion(int(plan["id"]), plan["periodo"], {
            "pct_asistencia_prom": promedios["pct_asistencia"],
            "pct_cumplimiento_prom": promedios["pct_cumplimiento"],
            "tareas_programadas": programadas,
            "tareas_cumplidas": cumplidas,
            "pct_tareas": pct_tareas,
            "fecha_visita": self.campo_fecha_visita.get(),
            "realizado_por": self.campo_realizado_por.get(),
            "obs_visita": self.txt_obs_visita.get("1.0", "end-1c").strip(),
            "calificacion_final": self.menu_calificacion.get(),
            "opinion_presidente": self.txt_opinion.get("1.0", "end-1c").strip(),
        })
        messagebox.showinfo("Evaluación guardada", f"AT-F9 de {plan['periodo']} guardado.")
        self._refrescar_tabla()
        return evaluacion_id

    def _generar_excel(self) -> str | None:
        evaluacion_id = self._guardar()
        if evaluacion_id is None:
            return None
        try:
            ruta = servicio_excel.generar_at_f9(evaluacion_id)
        except (FileNotFoundError, ValueError) as error:
            messagebox.showerror("No se pudo generar", str(error))
            return None
        messagebox.showinfo("Excel generado", f"AT-F9 generado en:\n{ruta}")
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

    # ------------------------------------------------------------------
    def _refrescar_tabla(self) -> None:
        for widget in self.tabla.winfo_children():
            widget.destroy()
        evaluaciones = db.listar_evaluaciones()
        cabecera = ctk.CTkFrame(self.tabla, fg_color=COLORS["bg_main"], corner_radius=6)
        cabecera.pack(fill="x", pady=(0, 4))
        anchos = (3, 2, 2, 2, 2, 2)
        for columna, peso in enumerate(anchos):
            cabecera.grid_columnconfigure(columna, weight=peso)
        for columna, texto in enumerate(("JUT", "Periodo", "Programadas", "Cumplidas", "Calif.", "Acción")):
            etiqueta_datos(cabecera, texto, COLORS["text_secondary"]).grid(
                row=0, column=columna, sticky="ew", padx=8, pady=4)
        if not evaluaciones:
            etiqueta_datos(self.tabla, "Sin evaluaciones registradas.",
                           COLORS["text_secondary"]).pack(anchor="w", pady=8)
        for evaluacion in evaluaciones:
            linea = ctk.CTkFrame(self.tabla, fg_color="transparent")
            linea.pack(fill="x", pady=1)
            for columna, peso in enumerate(anchos):
                linea.grid_columnconfigure(columna, weight=peso)
            valores = (evaluacion["jut_nombre"], evaluacion["periodo"],
                       evaluacion["tareas_programadas"], evaluacion["tareas_cumplidas"],
                       evaluacion["calificacion_final"])
            for columna, valor in enumerate(valores):
                etiqueta_datos(linea, str(valor)).grid(row=0, column=columna, sticky="ew", padx=8, pady=3)
            SecondaryButton(linea, "Excel",
                            lambda e=int(evaluacion["id"]): self._generar_de_tabla(e)).grid(
                row=0, column=5, sticky="e", padx=8, pady=2)

    def _generar_de_tabla(self, evaluacion_id: int) -> None:
        try:
            ruta = servicio_excel.generar_at_f9(evaluacion_id)
            messagebox.showinfo("Excel generado", f"AT-F9 generado en:\n{ruta}")
        except (FileNotFoundError, ValueError) as error:
            messagebox.showerror("No se pudo generar", str(error))
