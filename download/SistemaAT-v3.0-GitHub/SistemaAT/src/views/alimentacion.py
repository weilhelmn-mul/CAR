"""
=============================================================
 Sistema AT · Instituto Peruano del Deporte (IPD - DINADAF)
 views/alimentacion.py — Formato de alimentación: evaluación
 nutricional mensual por deportista con plan alimenticio
 (asistido por IA) y exportación a Excel/PDF.
=============================================================
"""
from __future__ import annotations

from typing import Any

import customtkinter as ctk
from tkinter import messagebox

from src import database as db
from src.config import OBJETIVOS_NUTRICION
from src.services import asistente_ia
from src.services import excel as servicio_excel
from src.services import pdf as servicio_pdf
from src.theme import COLORS, FONTS
from src.widgets import Card, PrimaryButton, SecondaryButton, SectionTitle, etiqueta_datos


class AlimentacionView(ctk.CTkFrame):
    """Formulario + listado de evaluaciones nutricionales mensuales."""

    def __init__(self, master: Any, app: Any) -> None:
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.seleccion_id: int | None = None
        self._opciones_deportistas: list[tuple[int, str]] = []
        self._construir()
        self._refrescar_selector()
        self._refrescar_tabla()

    # ------------------------------------------------------------------
    def _construir(self) -> None:
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- Formulario ----------------------------------------------------
        formulario = Card(self, width=420)
        formulario.grid(row=0, column=0, sticky="ns", padx=(28, 10), pady=(24, 24))
        formulario.pack_propagate(False)
        SectionTitle(formulario, "🥗 Evaluación nutricional").pack(anchor="w", padx=18, pady=(14, 6))

        ctk.CTkLabel(formulario, text="Deportista *", font=FONTS["small_bold"],
                     text_color=COLORS["text_secondary"], anchor="w").pack(fill="x", padx=18, pady=(2, 2))
        self.menu_deportista = ctk.CTkOptionMenu(
            formulario, values=["— sin deportistas —"], font=FONTS["body"],
            fg_color=COLORS["bg_main"], button_color=COLORS["accent"],
            button_hover_color=COLORS["accent_hover"])
        self.menu_deportista.pack(fill="x", padx=18, pady=2)

        fila_periodo = ctk.CTkFrame(formulario, fg_color="transparent")
        fila_periodo.pack(fill="x", padx=18, pady=4)
        fila_periodo.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkLabel(fila_periodo, text="Periodo (YYYY-MM) *", font=FONTS["small_bold"],
                     text_color=COLORS["text_secondary"], anchor="w").grid(row=0, column=0, sticky="ew")
        ctk.CTkLabel(fila_periodo, text="Fecha de evaluación", font=FONTS["small_bold"],
                     text_color=COLORS["text_secondary"], anchor="w").grid(row=0, column=1, sticky="ew")
        self.campo_periodo = ctk.CTkEntry(fila_periodo, placeholder_text="2026-11", font=FONTS["body"],
                                          fg_color=COLORS["bg_main"], border_color=COLORS["border"])
        self.campo_periodo.grid(row=1, column=0, sticky="ew", padx=(0, 6))
        self.campo_fecha = ctk.CTkEntry(fila_periodo, placeholder_text="2026-11-15", font=FONTS["body"],
                                        fg_color=COLORS["bg_main"], border_color=COLORS["border"])
        self.campo_fecha.grid(row=1, column=1, sticky="ew")

        fila_metricas = ctk.CTkFrame(formulario, fg_color="transparent")
        fila_metricas.pack(fill="x", padx=18, pady=4)
        for columna in range(4):
            fila_metricas.grid_columnconfigure(columna, weight=1)
        campos = (("Peso (kg)", "72.5"), ("Estatura (m)", "1.78"),
                  ("IMC (auto)", ""), ("% grasa", "14.0"))
        self.campos_metricas: dict[str, ctk.CTkEntry] = {}
        for columna, (titulo, placeholder) in enumerate(campos):
            ctk.CTkLabel(fila_metricas, text=titulo, font=FONTS["small_bold"],
                         text_color=COLORS["text_secondary"], anchor="w").grid(row=0, column=columna, sticky="ew")
            entrada = ctk.CTkEntry(fila_metricas, placeholder_text=placeholder, font=FONTS["body"],
                                   fg_color=COLORS["bg_main"], border_color=COLORS["border"])
            entrada.grid(row=1, column=columna, sticky="ew", padx=(0 if columna == 0 else 3, 0))
            self.campos_metricas[titulo] = entrada
        self.campos_metricas["IMC (auto)"].configure(state="disabled")

        fila_mas = ctk.CTkFrame(formulario, fg_color="transparent")
        fila_mas.pack(fill="x", padx=18, pady=4)
        fila_mas.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkLabel(fila_mas, text="kcal/día objetivo", font=FONTS["small_bold"],
                     text_color=COLORS["text_secondary"], anchor="w").grid(row=0, column=0, sticky="ew")
        ctk.CTkLabel(fila_mas, text="Nutricionista", font=FONTS["small_bold"],
                     text_color=COLORS["text_secondary"], anchor="w").grid(row=0, column=1, sticky="ew")
        self.campo_kcal = ctk.CTkEntry(fila_mas, placeholder_text="2800", font=FONTS["body"],
                                       fg_color=COLORS["bg_main"], border_color=COLORS["border"])
        self.campo_kcal.grid(row=1, column=0, sticky="ew", padx=(0, 6))
        self.campo_nutricionista = ctk.CTkEntry(fila_mas, placeholder_text="Nombre completo", font=FONTS["body"],
                                                fg_color=COLORS["bg_main"], border_color=COLORS["border"])
        self.campo_nutricionista.grid(row=1, column=1, sticky="ew")

        ctk.CTkLabel(formulario, text="Objetivo nutricional", font=FONTS["small_bold"],
                     text_color=COLORS["text_secondary"], anchor="w").pack(fill="x", padx=18, pady=(6, 2))
        self.menu_objetivo = ctk.CTkOptionMenu(
            formulario, values=list(OBJETIVOS_NUTRICION), font=FONTS["body"],
            fg_color=COLORS["bg_main"], button_color=COLORS["accent"],
            button_hover_color=COLORS["accent_hover"])
        self.menu_objetivo.set("RENDIMIENTO")
        self.menu_objetivo.pack(fill="x", padx=18, pady=2)

        ctk.CTkLabel(formulario, text="Plan alimenticio", font=FONTS["small_bold"],
                     text_color=COLORS["text_secondary"], anchor="w").pack(fill="x", padx=18, pady=(6, 2))
        self.texto_plan = ctk.CTkTextbox(formulario, height=110, font=FONTS["body"], wrap="word")
        self.texto_plan.pack(fill="x", padx=18, pady=2)

        ctk.CTkLabel(formulario, text="Observaciones", font=FONTS["small_bold"],
                     text_color=COLORS["text_secondary"], anchor="w").pack(fill="x", padx=18, pady=(6, 2))
        self.texto_observaciones = ctk.CTkTextbox(formulario, height=60, font=FONTS["body"], wrap="word")
        self.texto_observaciones.pack(fill="x", padx=18, pady=2)

        botones = ctk.CTkFrame(formulario, fg_color="transparent")
        botones.pack(fill="x", padx=18, pady=(10, 16))
        PrimaryButton(botones, "💾 Guardar evaluación", self._guardar).pack(fill="x", pady=3)
        SecondaryButton(botones, "✨ Generar plan con IA", self._plan_con_ia).pack(fill="x", pady=3)
        SecondaryButton(botones, "📊 Generar Excel", self._exportar_excel).pack(fill="x", pady=3)
        SecondaryButton(botones, "📄 Generar PDF", self._exportar_pdf).pack(fill="x", pady=3)
        SecondaryButton(botones, "🧹 Limpiar formulario", self._limpiar).pack(fill="x", pady=3)
        for clave in ("Peso (kg)", "Estatura (m)"):
            self.campos_metricas[clave].bind("<KeyRelease>", lambda _e: self._recalcular_imc())

        # --- Listado --------------------------------------------------------
        tabla_card = Card(self)
        tabla_card.grid(row=0, column=1, sticky="nsew", padx=(0, 28), pady=(24, 24))
        SectionTitle(tabla_card, "Evaluaciones registradas").pack(anchor="w", padx=18, pady=(14, 6))
        filtros = ctk.CTkFrame(tabla_card, fg_color="transparent")
        filtros.pack(fill="x", padx=18, pady=(0, 6))
        self.campo_filtro = ctk.CTkEntry(filtros, placeholder_text="Filtrar por periodo (2026-11)",
                                         width=220, font=FONTS["body"],
                                         fg_color=COLORS["bg_main"], border_color=COLORS["border"])
        self.campo_filtro.pack(side="left")
        SecondaryButton(filtros, "Filtrar", self._refrescar_tabla, width=110).pack(side="left", padx=8)
        self.tabla = ctk.CTkScrollableFrame(tabla_card, fg_color="transparent")
        self.tabla.pack(fill="both", expand=True, padx=18, pady=(0, 16))

    # ------------------------------------------------------------------
    def _recalcular_imc(self) -> None:
        """Recalcula el IMC a partir de peso y estatura."""
        campo_imc = self.campos_metricas["IMC (auto)"]
        try:
            peso = float((self.campos_metricas["Peso (kg)"].get() or "").replace(",", "."))
            estatura = float((self.campos_metricas["Estatura (m)"].get() or "").replace(",", "."))
        except ValueError:
            return
        if peso <= 0 or estatura <= 0:
            return
        imc = peso / (estatura ** 2)
        campo_imc.configure(state="normal")
        campo_imc.delete(0, "end")
        campo_imc.insert(0, f"{imc:.1f}")
        campo_imc.configure(state="disabled")

    def _numero(self, texto: str) -> float | None:
        texto = (texto or "").strip().replace(",", ".")
        if not texto:
            return None
        return float(texto)  # ValueError lo captura _guardar

    def _refrescar_tabla(self) -> None:
        for widget in self.tabla.winfo_children():
            widget.destroy()
        filas = db.listar_alimentacion(self.campo_filtro.get().strip())
        cabecera = ctk.CTkFrame(self.tabla, fg_color=COLORS["bg_main"], corner_radius=6)
        cabecera.pack(fill="x", pady=(0, 4))
        for columna, peso in enumerate((4, 2, 2, 2, 3, 3)):
            cabecera.grid_columnconfigure(columna, weight=peso)
        for columna, texto in enumerate(("Deportista", "Cat.", "Periodo", "IMC", "Objetivo", "kcal/día")):
            etiqueta_datos(cabecera, texto, COLORS["text_secondary"]).grid(
                row=0, column=columna, sticky="ew", padx=8, pady=4)
        if not filas:
            etiqueta_datos(self.tabla, "Sin evaluaciones registradas.",
                           COLORS["text_secondary"]).pack(anchor="w", pady=8)
        for fila in filas:
            linea = ctk.CTkFrame(self.tabla, fg_color="transparent", corner_radius=6)
            linea.pack(fill="x", pady=1)
            for columna, peso in enumerate((4, 2, 2, 2, 3, 3)):
                linea.grid_columnconfigure(columna, weight=peso)
            valores = (fila["nombre"], fila["categoria"], fila["periodo"],
                       f"{fila['imc']:.1f}" if fila["imc"] else "—",
                       str(fila["objetivo"]).replace("_", " "),
                       f"{fila['kcal_dia']:.0f}" if fila["kcal_dia"] else "—")
            for columna, valor in enumerate(valores):
                etiqueta_datos(linea, str(valor)).grid(row=0, column=columna, sticky="ew", padx=8, pady=3)
            linea.bind("<Button-1>", lambda _e, f=fila: self._cargar(int(f["id"])))
            for hijo in linea.winfo_children():
                hijo.bind("<Button-1>", lambda _e, f=fila: self._cargar(int(f["id"])))

    def _cargar(self, registro_id: int) -> None:
        fila = db.obtener_alimentacion(registro_id)
        if fila is None:
            return
        self.seleccion_id = registro_id
        self.menu_deportista.set(f"{fila['nombre']} · {fila['categoria']} · {fila['deporte']}")
        self.campo_periodo.delete(0, "end"); self.campo_periodo.insert(0, fila["periodo"])
        self.campo_fecha.delete(0, "end"); self.campo_fecha.insert(0, fila["fecha_evaluacion"] or "")
        valores = {"Peso (kg)": fila["peso_kg"], "Estatura (m)": fila["estatura_m"],
                   "% grasa": fila["pct_grasa_corporal"]}
        for titulo, valor in valores.items():
            entrada = self.campos_metricas[titulo]
            entrada.delete(0, "end")
            entrada.insert(0, f"{valor:g}" if valor is not None else "")
        campo_imc = self.campos_metricas["IMC (auto)"]
        campo_imc.configure(state="normal")
        campo_imc.delete(0, "end")
        campo_imc.insert(0, f"{fila['imc']:.1f}" if fila["imc"] else "")
        campo_imc.configure(state="disabled")
        self.campo_kcal.delete(0, "end")
        self.campo_kcal.insert(0, f"{fila['kcal_dia']:g}" if fila["kcal_dia"] else "")
        self.campo_nutricionista.delete(0, "end")
        self.campo_nutricionista.insert(0, fila["nutricionista"] or "")
        self.menu_objetivo.set(fila["objetivo"])
        self.texto_plan.delete("1.0", "end")
        self.texto_plan.insert("1.0", fila["plan_alimenticio"] or "")
        self.texto_observaciones.delete("1.0", "end")
        self.texto_observaciones.insert("1.0", fila["observaciones"] or "")

    def _limpiar(self) -> None:
        self.seleccion_id = None
        self.campo_periodo.delete(0, "end")
        self.campo_fecha.delete(0, "end")
        for titulo, entrada in self.campos_metricas.items():
            entrada.configure(state="normal")
            entrada.delete(0, "end")
            if titulo == "IMC (auto)":
                entrada.configure(state="disabled")
        self.campo_kcal.delete(0, "end")
        self.campo_nutricionista.delete(0, "end")
        self.menu_objetivo.set("RENDIMIENTO")
        self.texto_plan.delete("1.0", "end")
        self.texto_observaciones.delete("1.0", "end")

    # ------------------------------------------------------------------
    def _guardar(self) -> None:
        """Valida y guarda (o actualiza) la evaluación nutricional."""
        etiqueta = self.menu_deportista.get()
        deportista_id = next((i for i, t in getattr(self, "_opciones_deportistas", []) if t == etiqueta), None)
        periodo = self.campo_periodo.get().strip()
        if deportista_id is None or not periodo:
            messagebox.showwarning("Campos obligatorios",
                                   "Seleccione un deportista e indique el periodo (YYYY-MM).")
            return
        try:
            datos = {
                "fecha_evaluacion": self.campo_fecha.get().strip(),
                "nutricionista": self.campo_nutricionista.get().strip(),
                "peso_kg": self._numero(self.campos_metricas["Peso (kg)"].get()),
                "estatura_m": self._numero(self.campos_metricas["Estatura (m)"].get()),
                "imc": self._numero(self.campos_metricas["IMC (auto)"].get()),
                "pct_grasa_corporal": self._numero(self.campos_metricas["% grasa"].get()),
                "kcal_dia": self._numero(self.campo_kcal.get()),
                "objetivo": self.menu_objetivo.get(),
                "plan_alimenticio": self.texto_plan.get("1.0", "end").strip(),
                "observaciones": self.texto_observaciones.get("1.0", "end").strip(),
            }
        except ValueError:
            messagebox.showwarning("Valores numéricos", "Peso, estatura, IMC, grasa y kcal deben ser números.")
            return
        registro_id = db.upsert_alimentacion(deportista_id, periodo, datos)
        messagebox.showinfo("Evaluación guardada",
                            f"La evaluación nutricional de {periodo} quedó registrada (id {registro_id}).")
        self._limpiar()
        self._refrescar_tabla()

    def _registro_listo(self) -> int | None:
        """Garantiza que exista un registro guardado para usar IA/exportar."""
        if self.seleccion_id is not None:
            return self.seleccion_id
        messagebox.showinfo("Guarde primero",
                            "Guarde la evaluación (💾) antes de usar el asistente o exportar.")
        return None

    def _plan_con_ia(self) -> None:
        registro_id = self._registro_listo()
        if registro_id is None:
            return
        try:
            textos = asistente_ia.redactar("ALIMENTACION", registro_id)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Asistente IA", f"No se pudo redactar:\n{exc}")
            return
        if messagebox.askyesno("Plan con IA",
                               "Se reemplazará el contenido del plan alimenticio y de las "
                               "observaciones por la redacción del asistente. ¿Continuar?"):
            self.texto_plan.delete("1.0", "end")
            self.texto_plan.insert("1.0", textos.get("plan_alimenticio", ""))
            self.texto_observaciones.delete("1.0", "end")
            self.texto_observaciones.insert("1.0", textos.get("observaciones", ""))

    def _exportar_excel(self) -> None:
        registro_id = self._registro_listo()
        if registro_id is None:
            return
        try:
            ruta = servicio_excel.generar_alimentacion(registro_id)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Exportar", f"No se pudo generar el Excel:\n{exc}")
            return
        messagebox.showinfo("Excel generado", f"Ficha de alimentación generada en:\n{ruta}")

    def _exportar_pdf(self) -> None:
        registro_id = self._registro_listo()
        if registro_id is None:
            return
        try:
            ruta = servicio_excel.generar_alimentacion(registro_id)
            pdf = servicio_pdf.excel_a_pdf(ruta)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Exportar", f"No se pudo generar el PDF:\n{exc}")
            return
        messagebox.showinfo("PDF generado", f"PDF disponible en:\n{pdf}")

    # ------------------------------------------------------------------
    def _refrescar_selector(self) -> None:
        """Carga las opciones de deportistas en el menú."""
        opciones = db.opciones_deportistas()
        self._opciones_deportistas = opciones
        valores = [texto for _i, texto in opciones] or ["— sin deportistas —"]
        self.menu_deportista.configure(values=valores)
        self.menu_deportista.set(valores[0])