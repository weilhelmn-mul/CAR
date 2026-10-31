# -*- coding: utf-8 -*-
"""
src/views/at_f9.py
==================
Vista AT-F9 · Informe de cumplimiento del Jefe de Unidad Técnica (evalúa el
plan de trabajo mensual, integrando evidencia de AT-F1 y AT-F3).

Automatismos (flujo 9.3 y sección 7.12 del pliego):
    * Al elegir JUT + período se carga automáticamente el plan AT-F8 a evaluar
      (por defecto, el del PERÍODO ANTERIOR; ver DESFASE_PLAN más abajo).
    * Tareas planificadas / cumplidas / % se calculan con las casillas.
    * % de cumplimiento promedio y % de asistencia promedio se traen de los
      registros AT-F3 del período y se congelan al guardar (campos auxiliares
      de la BD, documentados).

Nota sobre la reseña: la plantilla oficial no tiene recuadro para la reseña
de reuniones; al generar el Excel se inserta una fila dentro de la sección 2.
"""
from __future__ import annotations

import json
import logging
import sqlite3

import customtkinter as ctk
from tkinter import messagebox

from src import config
from src.database import get_connection, transaccion
from src.services import excel as svc_excel
from src.services import pdf as svc_pdf
from src.theme import COLORS, FONTS
from src.widgets import Card, FormField, PrimaryButton, SectionTitle, TextboxCard, confirmar_apertura

log = logging.getLogger(__name__)

# El AT-F9 evalúa el plan AT-F8 del período ANTERIOR (sección 7.12 del pliego).
# Si su práctica es evaluar el plan del MISMO período (cabecera del AT-F8 con
# el mes planificado), cambie este valor a 0.
DESFASE_PLAN = 1


def construir(parent, app) -> None:
    """Construye la vista y devuelve la instancia (útil para pruebas)."""
    return _Vista(parent, app)


class _Vista:
    def __init__(self, parent: ctk.CTkFrame, app):
        self.app = app
        self.evaluacion_id: int | None = None
        self.plan: sqlite3.Row | None = None
        self._tareas_plan: list[dict] = []
        self._vars_cumplida: list[ctk.BooleanVar] = []
        self._var_calif = ctk.StringVar(value="")
        self._cargando = False

        contenedor = ctk.CTkFrame(parent, fg_color="transparent")
        contenedor.pack(fill="both", expand=True, padx=24, pady=18)
        contenedor.grid_columnconfigure(0, weight=1)
        contenedor.grid_rowconfigure(1, weight=1)

        self._barra_superior(contenedor)
        formulario = ctk.CTkScrollableFrame(contenedor, fg_color="transparent")
        formulario.grid(row=1, column=0, sticky="nsew")
        self._secciones(formulario)
        self._cargar()

    # ------------------------------------------------------------------ UI
    def _barra_superior(self, contenedor) -> None:
        barra = Card(contenedor)
        barra.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        barra.grid_columnconfigure(0, weight=1)
        self.f_jut = FormField(barra, "Nombres y apellidos del JUT *", "Ej. JHON CUSI HUAMÁN", ancho=420)
        self.f_jut.grid(row=0, column=0, sticky="w", padx=16, pady=(12, 4))

        ctk.CTkLabel(barra, text="Período evaluado", font=FONTS["small_bold"], anchor="w").grid(
            row=0, column=1, sticky="w", padx=8, pady=(12, 0)
        )
        self.o_periodo = ctk.CTkOptionMenu(
            barra, values=config.lista_periodos(24), width=140, height=32, font=FONTS["body"],
            command=lambda _v: self._cargar(),
        )
        self.o_periodo.set(config.periodo_actual())
        self.o_periodo.grid(row=1, column=1, sticky="w", padx=8, pady=(0, 10))

        acciones = ctk.CTkFrame(barra, fg_color="transparent")
        acciones.grid(row=0, column=2, rowspan=2, sticky="e", padx=16)
        PrimaryButton(acciones, text="💾 Guardar", command=self._guardar).pack(side="left", padx=4, pady=12)
        PrimaryButton(acciones, text="📄 Generar Excel", command=self._generar_excel).pack(side="left", padx=4, pady=12)
        PrimaryButton(acciones, text="📕 Generar PDF", command=self._generar_pdf).pack(side="left", padx=4, pady=12)

        self.lbl_plan = ctk.CTkLabel(
            barra, text="", font=FONTS["small"], text_color=COLORS["text_secondary"], anchor="w"
        )
        self.lbl_plan.grid(row=2, column=0, columnspan=3, sticky="ew", padx=16, pady=(0, 12))

    def _secciones(self, formulario) -> None:
        # ---- Sección 1 · Cumplimiento de tareas ------------------------
        s1 = Card(formulario)
        s1.pack(fill="x", pady=8)
        s1.grid_columnconfigure(0, weight=1)
        SectionTitle(s1, "Sección 1 · Cumplimiento de las tareas/actividades (plan AT-F8 del período anterior)").grid(
            row=0, column=0, sticky="ew", padx=14, pady=(10, 4)
        )
        resumen = ctk.CTkFrame(s1, fg_color="transparent")
        resumen.grid(row=1, column=0, sticky="ew", padx=14)
        self.lbl_planificadas = ctk.CTkLabel(resumen, text="Planificadas: 0", font=FONTS["small_bold"])
        self.lbl_planificadas.pack(side="left", padx=(0, 18))
        self.lbl_cumplidas = ctk.CTkLabel(resumen, text="Cumplidas: 0", font=FONTS["small_bold"], text_color=COLORS["success"])
        self.lbl_cumplidas.pack(side="left", padx=(0, 18))
        self.lbl_pct = ctk.CTkLabel(resumen, text="%: —", font=FONTS["small_bold"], text_color=COLORS["accent"])
        self.lbl_pct.pack(side="left")
        self.marco_tareas = ctk.CTkFrame(s1, fg_color="transparent")
        self.marco_tareas.grid(row=2, column=0, sticky="ew", padx=14, pady=(6, 4))
        self.t_eval_cumplimiento = TextboxCard(s1, "Evaluación del cumplimiento", 90)
        self.t_eval_cumplimiento.grid(row=3, column=0, sticky="ew", padx=14, pady=(4, 12))

        # ---- Sección 2 · Reuniones ------------------------------------
        self.t_reuniones = TextboxCard(formulario, "Sección 2 · Breve reseña de las reuniones de trabajo educativo", 100)
        self.t_reuniones.pack(fill="x", pady=8)
        promedios = Card(formulario)
        promedios.pack(fill="x", pady=8)
        SectionTitle(promedios, "Sección 2 · Promedios automáticos desde los AT-F3 del período").grid(
            row=0, column=0, columnspan=2, sticky="ew", padx=14, pady=(10, 4)
        )
        self.lbl_pct_preparacion = ctk.CTkLabel(
            promedios, text="% cumplimiento de la preparación: —", font=FONTS["body"], anchor="w"
        )
        self.lbl_pct_preparacion.grid(row=1, column=0, sticky="w", padx=14, pady=(0, 8))
        self.lbl_pct_asistencia = ctk.CTkLabel(
            promedios, text="% de asistencia a los entrenamientos: —", font=FONTS["body"], anchor="w"
        )
        self.lbl_pct_asistencia.grid(row=1, column=1, sticky="w", padx=14, pady=(0, 8))
        self.t_dif_analizadas = TextboxCard(formulario, "Sección 2 · Dificultades analizadas", 100)
        self.t_dif_analizadas.pack(fill="x", pady=8)

        # ---- Sección 3 · Documentación --------------------------------
        self.t_documentacion = TextboxCard(
            formulario,
            "Sección 3 · Evaluación / revisión y control de la documentación técnico-metodológica de los entrenadores",
            100,
        )
        self.t_documentacion.pack(fill="x", pady=8)

        # ---- Sección 4 · Visitas técnicas -----------------------------
        s4 = Card(formulario)
        s4.pack(fill="x", pady=8)
        SectionTitle(s4, "Sección 4 · Informe de resumen de las visitas técnicas realizadas").grid(
            row=0, column=0, columnspan=2, sticky="ew", padx=14, pady=(10, 4)
        )
        self.f_cantidad_visitas = FormField(s4, "Cantidad de visitas", "Ej. 10", ancho=160)
        self.f_cantidad_visitas.grid(row=1, column=0, sticky="w", padx=14, pady=(0, 10))
        self.f_eval_visitas = FormField(s4, "Evaluación", "Ej. 18/20", ancho=160)
        self.f_eval_visitas.grid(row=1, column=1, sticky="w", padx=14, pady=(0, 10))
        self.t_resumen_visitas = TextboxCard(s4, "Resumen de dificultades de las visitas", 90)
        self.t_resumen_visitas.grid(row=2, column=0, columnspan=2, sticky="ew", padx=14, pady=(0, 12))

        # ---- Sección 5 · Trabajo integral -----------------------------
        s5 = Card(formulario)
        s5.pack(fill="x", pady=8)
        SectionTitle(s5, "Sección 5 · Evaluación del trabajo integral realizado durante el mes").grid(
            row=0, column=0, columnspan=2, sticky="ew", padx=14, pady=(10, 6)
        )
        self.seg_bd = self._fila_si_no(s5, 1, "Actualización de la base de datos")
        self.seg_calendario = self._fila_si_no(s5, 2, "Cumplimiento del calendario de actividades")
        self.seg_capacitaciones = self._fila_si_no(s5, 3, "Capacitaciones realizados")
        self.t_analisis_poa = TextboxCard(
            s5, "Análisis del cumplimiento de los objetivos permanentes del plan operativo", 90
        )
        self.t_analisis_poa.grid(row=4, column=0, columnspan=2, sticky="ew", padx=14, pady=(4, 12))

        # ---- Secciones 6 y 7 -------------------------------------------
        self.t_otros = TextboxCard(formulario, "Sección 6 · Otros datos de interés", 90)
        self.t_otros.pack(fill="x", pady=8)
        self.t_opinion = TextboxCard(
            formulario, "Sección 7 · Opinión del Presidente de la FDN (opcional)", 90,
            nota="Si añade opinión, el Excel incluirá también la firma del Presidente de la FDN (si está registrada).",
        )
        self.t_opinion.pack(fill="x", pady=8)

        # ---- Sección 8 · Calificación final ----------------------------
        s8 = Card(formulario)
        s8.pack(fill="x", pady=8)
        SectionTitle(s8, "Sección 8 · Evaluación del cumplimiento del plan de trabajo").grid(
            row=0, column=0, sticky="ew", padx=14, pady=(10, 6)
        )
        fila_calif = ctk.CTkFrame(s8, fg_color="transparent")
        fila_calif.grid(row=1, column=0, sticky="w", padx=14, pady=(0, 12))
        for valor in config.CALIFICACIONES:
            ctk.CTkRadioButton(
                fila_calif, text=valor, variable=self._var_calif, value=valor,
                font=FONTS["body"], fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"],
            ).pack(side="left", padx=(0, 22))

    @staticmethod
    def _fila_si_no(padre, fila: int, etiqueta: str) -> ctk.CTkSegmentedButton:
        ctk.CTkLabel(padre, text=etiqueta, font=FONTS["body"], anchor="w").grid(
            row=fila, column=0, sticky="w", padx=14, pady=3
        )
        seg = ctk.CTkSegmentedButton(padre, values=["SÍ", "NO"], font=FONTS["small_bold"])
        seg.set("NO")
        seg.grid(row=fila, column=1, sticky="w", padx=14, pady=3)
        return seg

    # ------------------------------------------------------------------ datos
    def _jut(self) -> str:
        return self.f_jut.get().upper()

    def _construir_lista_tareas(self) -> None:
        """Reconstruye la lista de tareas del plan con sus casillas."""
        for hijo in self.marco_tareas.winfo_children():
            hijo.destroy()
        self._vars_cumplida = []
        if not self._tareas_plan:
            ctk.CTkLabel(
                self.marco_tareas, text="Sin plan AT-F8 del período anterior para este JUT.",
                font=FONTS["small"], text_color=COLORS["text_secondary"], anchor="w",
            ).pack(fill="x", pady=4)
        for tarea in self._tareas_plan:
            fila = ctk.CTkFrame(self.marco_tareas, fg_color="transparent")
            fila.pack(fill="x", pady=2)
            detalle = f"{tarea.get('fecha', '')} {tarea.get('hora', '')}".strip()
            texto = tarea.get("actividad") or "(tarea sin descripción)"
            ctk.CTkLabel(
                fila, text=f"{tarea.get('n', '')}. {texto}" + (f"   · {detalle}" if detalle else ""),
                font=FONTS["small"], anchor="w", justify="left", wraplength=760,
            ).pack(side="left", fill="x", expand=True)
            var = ctk.BooleanVar(value=False)
            ctk.CTkCheckBox(
                fila, text="Cumplida", variable=var, font=FONTS["small"],
                fg_color=COLORS["success"], hover_color=COLORS["success"],
                command=self._actualizar_resumen,
            ).pack(side="right", padx=(8, 0))
            self._vars_cumplida.append(var)
        self._actualizar_resumen()

    def _actualizar_resumen(self) -> None:
        planificadas = len(self._tareas_plan)
        cumplidas = sum(1 for v in self._vars_cumplida if v.get())
        pct = (cumplidas / planificadas) if planificadas else None
        self.lbl_planificadas.configure(text=f"Planificadas: {planificadas}")
        self.lbl_cumplidas.configure(text=f"Cumplidas: {cumplidas}")
        self.lbl_pct.configure(text=f"%: {config.formatear_pct(pct) or '—'}")

    def _calcular_promedios(self) -> tuple[float | None, float | None]:
        """% promedio de cumplimiento y asistencia de los AT-F3 del período."""
        con = get_connection()
        try:
            fila = con.execute(
                "SELECT AVG(pct_cumplimiento) AS cump, AVG(pct_asistencia) AS asis "
                "FROM registros_mensuales WHERE periodo = ?",
                (self.o_periodo.get(),),
            ).fetchone()
        finally:
            con.close()
        return fila["cump"], fila["asis"]

    def _cargar(self) -> None:
        self._cargando = True
        try:
            self.evaluacion_id = None
            self.plan = None
            self._tareas_plan = []
            self.lbl_plan.configure(text="")
            for tarjeta in (self.t_eval_cumplimiento, self.t_reuniones, self.t_dif_analizadas,
                            self.t_documentacion, self.t_resumen_visitas, self.t_analisis_poa,
                            self.t_otros, self.t_opinion):
                tarjeta.set("")
            self.f_cantidad_visitas.set(""); self.f_eval_visitas.set("")
            self._var_calif.set("")
            for seg in (self.seg_bd, self.seg_calendario, self.seg_capacitaciones):
                seg.set("NO")

            pct_cump, pct_asis = self._calcular_promedios()
            self.lbl_pct_preparacion.configure(
                text=f"% cumplimiento de la preparación: {config.formatear_pct(pct_cump) or '—'}"
            )
            self.lbl_pct_asistencia.configure(
                text=f"% de asistencia a los entrenamientos: {config.formatear_pct(pct_asis) or '—'}"
            )

            jut = self._jut()
            periodo = self.o_periodo.get()
            if not jut:
                self._construir_lista_tareas()
                return

            periodo_plan = config.periodo_anterior(periodo, DESFASE_PLAN)
            con = get_connection()
            try:
                self.plan = con.execute(
                    "SELECT * FROM planes_jut WHERE jut_nombre = ? AND periodo = ?",
                    (jut, periodo_plan),
                ).fetchone()
                evaluacion = con.execute(
                    "SELECT * FROM evaluaciones_jut WHERE jut_nombre = ? AND periodo = ?",
                    (jut, periodo),
                ).fetchone()
            finally:
                con.close()

            if self.plan is not None:
                self._tareas_plan = json.loads(self.plan["tareas_json"]) if self.plan["tareas_json"] else []
                self.lbl_plan.configure(
                    text=f"Plan AT-F8 de {config.mes_de_periodo(periodo_plan)} cargado: "
                         f"{len(self._tareas_plan)} tarea(s) del JUT {jut}."
                )
            else:
                self.lbl_plan.configure(
                    text=f"No hay plan AT-F8 de {config.mes_de_periodo(periodo_plan)} para {jut}. "
                         f"Créelo en la vista AT-F8."
                )
            self._construir_lista_tareas()

            if evaluacion is not None:
                self.evaluacion_id = evaluacion["id"]
                self.t_eval_cumplimiento.set(evaluacion["evaluacion_cumplimiento"])
                self.t_reuniones.set(evaluacion["resumen_reuniones"])
                self.t_dif_analizadas.set(evaluacion["resumen_dificultades_seccion2"])
                self.t_documentacion.set(evaluacion["resumen_documentacion"])
                self.f_cantidad_visitas.set(evaluacion["cantidad_visitas"])
                self.f_eval_visitas.set(evaluacion["evaluacion_visitas"])
                self.t_resumen_visitas.set(evaluacion["resumen_dificultades"])
                self.seg_bd.set(evaluacion["actualizacion_bd"] or "NO")
                self.seg_calendario.set(evaluacion["cumplimiento_calendario"] or "NO")
                self.seg_capacitaciones.set(evaluacion["capacitaciones"] or "NO")
                self.t_analisis_poa.set(evaluacion["analisis_poa"])
                self.t_otros.set(evaluacion["otros_datos"])
                self.t_opinion.set(evaluacion["opinion_presidente"])
                if evaluacion["calificacion_final"]:
                    self._var_calif.set(evaluacion["calificacion_final"])
        finally:
            self._cargando = False

    # ------------------------------------------------------------------ acciones
    def _guardar(self) -> None:
        if self._cargando:
            return
        jut = self._jut()
        if not jut:
            messagebox.showwarning("Campo obligatorio", "Indique los nombres y apellidos del JUT.", parent=self)
            return
        calificacion = self._var_calif.get()
        if calificacion not in config.CALIFICACIONES:
            messagebox.showwarning(
                "Calificación obligatoria", "Seleccione la calificación final (BUENO / REGULAR / MALO).",
                parent=self,
            )
            return
        cantidad = self.f_cantidad_visitas.get()
        if cantidad and not cantidad.isdigit():
            messagebox.showerror("Valor numérico", "La cantidad de visitas debe ser un número entero.", parent=self)
            return

        planificadas = len(self._tareas_plan)
        cumplidas = sum(1 for v in self._vars_cumplida if v.get())
        pct = (cumplidas / planificadas) if planificadas else None
        pct_cump, pct_asis = self._calcular_promedios()
        periodo = self.o_periodo.get()
        try:
            with transaccion() as con:
                con.execute(
                    """
                    INSERT INTO evaluaciones_jut
                        (plan_id, jut_nombre, periodo, tareas_planificadas, tareas_cumplidas,
                         pct_cumplimiento, evaluacion_cumplimiento, resumen_reuniones,
                         resumen_documentacion, cantidad_visitas, evaluacion_visitas,
                         resumen_dificultades, actualizacion_bd, cumplimiento_calendario,
                         capacitaciones, analisis_poa, otros_datos, opinion_presidente,
                         calificacion_final, resumen_dificultades_seccion2,
                         pct_cumplimiento_promedio, pct_asistencia_promedio, estado)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?, 'borrador')
                    ON CONFLICT(jut_nombre, periodo) DO UPDATE SET
                        plan_id=excluded.plan_id,
                        tareas_planificadas=excluded.tareas_planificadas,
                        tareas_cumplidas=excluded.tareas_cumplidas,
                        pct_cumplimiento=excluded.pct_cumplimiento,
                        evaluacion_cumplimiento=excluded.evaluacion_cumplimiento,
                        resumen_reuniones=excluded.resumen_reuniones,
                        resumen_documentacion=excluded.resumen_documentacion,
                        cantidad_visitas=excluded.cantidad_visitas,
                        evaluacion_visitas=excluded.evaluacion_visitas,
                        resumen_dificultades=excluded.resumen_dificultades,
                        actualizacion_bd=excluded.actualizacion_bd,
                        cumplimiento_calendario=excluded.cumplimiento_calendario,
                        capacitaciones=excluded.capacitaciones,
                        analisis_poa=excluded.analisis_poa,
                        otros_datos=excluded.otros_datos,
                        opinion_presidente=excluded.opinion_presidente,
                        calificacion_final=excluded.calificacion_final,
                        resumen_dificultades_seccion2=excluded.resumen_dificultades_seccion2,
                        pct_cumplimiento_promedio=excluded.pct_cumplimiento_promedio,
                        pct_asistencia_promedio=excluded.pct_asistencia_promedio
                    """,
                    (self.plan["id"] if self.plan else None, jut, periodo, planificadas,
                     cumplidas, pct, self.t_eval_cumplimiento.get() or None,
                     self.t_reuniones.get() or None, self.t_documentacion.get() or None,
                     int(cantidad) if cantidad else None, self.f_eval_visitas.get() or None,
                     self.t_resumen_visitas.get() or None, self.seg_bd.get(),
                     self.seg_calendario.get(), self.seg_capacitaciones.get(),
                     self.t_analisis_poa.get() or None, self.t_otros.get() or None,
                     self.t_opinion.get() or None, calificacion,
                     self.t_dif_analizadas.get() or None, pct_cump, pct_asis),
                )
                fila = con.execute(
                    "SELECT id FROM evaluaciones_jut WHERE jut_nombre = ? AND periodo = ?",
                    (jut, periodo),
                ).fetchone()
                self.evaluacion_id = fila["id"]
        except sqlite3.Error as e:
            log.exception("Error al guardar AT-F9")
            messagebox.showerror("Base de datos", f"No se pudo guardar el AT-F9:\n{e}", parent=self)
            return
        messagebox.showinfo(
            "Registro guardado",
            f"AT-F9 · {jut} · {periodo} guardado ({cumplidas}/{planificadas} tareas).",
        )

    def _asegurar_guardado(self) -> bool:
        if self.evaluacion_id is not None:
            return True
        if not messagebox.askyesno(
            "Guardar primero", "La evaluación aún no está guardada. ¿Desea guardarla ahora?", parent=self
        ):
            return False
        self._guardar()
        return self.evaluacion_id is not None

    def _generar_excel(self) -> None:
        if not self._asegurar_guardado():
            return
        try:
            ruta = svc_excel.generar_at_f9(self.evaluacion_id)
        except FileNotFoundError as e:
            messagebox.showerror("Plantilla no encontrada", str(e), parent=self)
            return
        except Exception as e:
            log.exception("Error generando AT-F9 Excel")
            messagebox.showerror("Error al generar", f"No se pudo generar el Excel:\n{e}", parent=self)
            return
        confirmar_apertura(ruta)

    def _generar_pdf(self) -> None:
        if not self._asegurar_guardado():
            return
        try:
            ruta_xlsx = svc_excel.generar_at_f9(self.evaluacion_id)
            ruta_pdf = svc_pdf.excel_a_pdf(ruta_xlsx)
        except FileNotFoundError as e:
            messagebox.showerror("Plantilla no encontrada", str(e), parent=self)
            return
        except RuntimeError as e:
            messagebox.showerror("PDF no generado", str(e), parent=self)
            return
        except Exception as e:
            log.exception("Error generando AT-F9 PDF")
            messagebox.showerror("Error al generar", f"No se pudo generar el PDF:\n{e}", parent=self)
            return
        confirmar_apertura(ruta_pdf)
