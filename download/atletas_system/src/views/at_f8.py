# -*- coding: utf-8 -*-
"""
src/views/at_f8.py
==================
Vista AT-F8 · Plan de trabajo mensual del Jefe de Unidad Técnica (planifica el
mes: tareas con fecha, hora, lugar y observaciones).

Las tareas se guardan como lista de diccionarios en planes_jut.tareas_json:
    [{"n": 1, "actividad": …, "fecha": …, "hora": …, "lugar": …, "observaciones": …}]
Este plan es el que luego evalúa el AT-F9 (cadena de gestión AT-F8 → AT-F9).
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
from src.widgets import Card, FormField, PrimaryButton, SectionTitle, confirmar_apertura, peso_entero

log = logging.getLogger(__name__)


def construir(parent, app) -> None:
    """Construye la vista y devuelve la instancia (útil para pruebas)."""
    return _Vista(parent, app)


class _Vista:
    def __init__(self, parent: ctk.CTkFrame, app):
        self.app = app
        self.plan_id: int | None = None
        self._filas: list[dict] = []
        self._cargando = False

        contenedor = ctk.CTkFrame(parent, fg_color="transparent")
        contenedor.pack(fill="both", expand=True, padx=24, pady=18)
        contenedor.grid_columnconfigure(0, weight=1)
        contenedor.grid_rowconfigure(1, weight=1)

        self._barra_superior(contenedor)
        self._seccion_tareas(contenedor)
        self._cargar()

    # ------------------------------------------------------------------ UI
    def _barra_superior(self, contenedor) -> None:
        barra = Card(contenedor)
        barra.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        barra.grid_columnconfigure(0, weight=1)
        self.f_federacion = FormField(barra, "Federación", "Ej. FEDERACIÓN DEPORTIVA PERUANA DE ATLETISMO", ancho=420)
        self.f_federacion.grid(row=0, column=0, sticky="w", padx=16, pady=(12, 4))
        self.f_jut = FormField(barra, "Nombres y apellidos del Jefe de Unidad Técnica *", "Ej. JHON CUSI HUAMÁN", ancho=420)
        self.f_jut.grid(row=1, column=0, sticky="w", padx=16, pady=4)

        ctk.CTkLabel(barra, text="Período (mes planificado)", font=FONTS["small_bold"], anchor="w").grid(
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

    def _seccion_tareas(self, contenedor) -> None:
        tarjeta = Card(contenedor)
        tarjeta.grid(row=1, column=0, sticky="nsew")
        tarjeta.grid_columnconfigure(0, weight=1)
        tarjeta.grid_rowconfigure(1, weight=1)
        SectionTitle(tarjeta, "Tareas / actividades del mes").grid(
            row=0, column=0, sticky="w", padx=14, pady=(10, 6)
        )
        self.marco_tabla = ctk.CTkScrollableFrame(tarjeta, height=380, fg_color="transparent")
        self.marco_tabla.grid(row=1, column=0, sticky="nsew", padx=14)

        anchos = [0.5, 4, 1.4, 1.1, 1.8, 2.4, 0.9]
        for j, peso in enumerate(anchos):
            self.marco_tabla.grid_columnconfigure(j, weight=peso_entero(peso))
        for j, texto in enumerate(["N°", "Actividad / Tarea", "Fecha", "Hora", "Lugar", "Observaciones", ""]):
            ctk.CTkLabel(
                self.marco_tabla, text=texto, font=FONTS["small_bold"],
                text_color=COLORS["text_light"], fg_color=COLORS["sidebar"], corner_radius=6, height=30,
            ).grid(row=0, column=j, sticky="ew", padx=2, pady=(2, 6))

        PrimaryButton(tarjeta, text="➕ Añadir tarea", command=self._anadir_tarea).grid(
            row=2, column=0, sticky="w", padx=14, pady=(6, 12)
        )

    # ------------------------------------------------------------------ filas
    def _anadir_tarea(self, valores: dict | None = None) -> None:
        """Agrega una fila editable a la tabla de tareas."""
        valores = valores or {}
        fila = ctk.CTkFrame(self.marco_tabla, fg_color="transparent")
        # la fila se coloca al final de las existentes
        fila.grid(row=len(self._filas) + 1, column=0, columnspan=7, sticky="ew", pady=2)
        for j, peso in enumerate([0.5, 4, 1.4, 1.1, 1.8, 2.4, 0.9]):
            fila.grid_columnconfigure(j, weight=peso_entero(peso))
        num = ctk.CTkLabel(fila, text=str(len(self._filas) + 1), font=FONTS["small_bold"])
        num.grid(row=0, column=0, padx=4)
        e_actividad = ctk.CTkEntry(fila, height=30, placeholder_text="Actividad o tarea…")
        e_actividad.grid(row=0, column=1, sticky="ew", padx=3)
        e_fecha = ctk.CTkEntry(fila, height=30, width=110, placeholder_text="dd/mm")
        e_fecha.grid(row=0, column=2, sticky="ew", padx=3)
        e_hora = ctk.CTkEntry(fila, height=30, width=90, placeholder_text="8:00-10:00")
        e_hora.grid(row=0, column=3, sticky="ew", padx=3)
        e_lugar = ctk.CTkEntry(fila, height=30, placeholder_text="Lugar…")
        e_lugar.grid(row=0, column=4, sticky="ew", padx=3)
        e_obs = ctk.CTkEntry(fila, height=30, placeholder_text="Observaciones…")
        e_obs.grid(row=0, column=5, sticky="ew", padx=3)
        boton = ctk.CTkButton(
            fila, text="✕", width=32, height=30, font=FONTS["small_bold"],
            fg_color=COLORS["danger"], hover_color="#dc2626",
            command=lambda: self._eliminar_tarea(registro),
        )
        boton.grid(row=0, column=6, padx=4)
        registro = {"frame": fila, "num": num, "actividad": e_actividad, "fecha": e_fecha,
                    "hora": e_hora, "lugar": e_lugar, "obs": e_obs, "boton": boton}
        if valores:
            for clave in ("actividad", "fecha", "hora", "lugar", "observaciones"):
                destino = {"observaciones": "obs"}.get(clave, clave)
                if valores.get(clave):
                    registro[destino].insert(0, str(valores[clave]))
        self._filas.append(registro)

    def _eliminar_tarea(self, registro: dict) -> None:
        registro["frame"].destroy()
        if registro in self._filas:
            self._filas.remove(registro)
        # renumerar y reubicar las filas restantes
        for i, r in enumerate(self._filas, start=1):
            r["num"].configure(text=str(i))
            r["frame"].grid(row=i, column=0, columnspan=7, sticky="ew", pady=2)

    # ------------------------------------------------------------------ datos
    def _cargar(self) -> None:
        self._cargando = True
        try:
            self.plan_id = None
            for registro in list(self._filas):
                registro["frame"].destroy()
            self._filas.clear()
            jut = self.f_jut.get().upper()
            if jut:
                con = get_connection()
                try:
                    plan = con.execute(
                        "SELECT * FROM planes_jut WHERE jut_nombre = ? AND periodo = ?",
                        (jut, self.o_periodo.get()),
                    ).fetchone()
                finally:
                    con.close()
                if plan is not None:
                    self.plan_id = plan["id"]
                    self.f_federacion.set(plan["federacion"])
                    for tarea in json.loads(plan["tareas_json"]) if plan["tareas_json"] else []:
                        self._anadir_tarea(tarea)
            if not self._filas:
                self._anadir_tarea()
        finally:
            self._cargando = False

    def _guardar(self) -> None:
        if self._cargando:
            return
        jut = self.f_jut.get().upper()
        if not jut:
            messagebox.showwarning("Campo obligatorio", "Indique los nombres y apellidos del JUT.", parent=self)
            return
        tareas = []
        for r in self._filas:
            actividad = r["actividad"].get().strip()
            if not actividad and not (r["fecha"].get().strip() or r["hora"].get().strip()
                                      or r["lugar"].get().strip() or r["obs"].get().strip()):
                continue  # filas completamente vacías se descartan
            tareas.append({
                "n": len(tareas) + 1,
                "actividad": actividad,
                "fecha": r["fecha"].get().strip(),
                "hora": r["hora"].get().strip(),
                "lugar": r["lugar"].get().strip(),
                "observaciones": r["obs"].get().strip(),
            })
        periodo = self.o_periodo.get()
        try:
            with transaccion() as con:
                con.execute(
                    """
                    INSERT INTO planes_jut (jut_nombre, federacion, periodo, tareas_json, estado)
                    VALUES (?,?,?,?, 'borrador')
                    ON CONFLICT(jut_nombre, periodo) DO UPDATE SET
                        federacion=excluded.federacion,
                        tareas_json=excluded.tareas_json
                    """,
                    (jut, self.f_federacion.get().upper() or None, periodo,
                     json.dumps(tareas, ensure_ascii=False)),
                )
                fila = con.execute(
                    "SELECT id FROM planes_jut WHERE jut_nombre = ? AND periodo = ?",
                    (jut, periodo),
                ).fetchone()
                self.plan_id = fila["id"]
        except sqlite3.Error as e:
            log.exception("Error al guardar AT-F8")
            messagebox.showerror("Base de datos", f"No se pudo guardar el AT-F8:\n{e}", parent=self)
            return
        messagebox.showinfo(
            "Plan guardado",
            f"AT-F8 · {jut} · {periodo} guardado con {len(tareas)} tarea(s).",
        )

    def _asegurar_guardado(self) -> bool:
        if self.plan_id is not None:
            return True
        if not messagebox.askyesno(
            "Guardar primero", "El plan aún no está guardado. ¿Desea guardarlo ahora?", parent=self
        ):
            return False
        self._guardar()
        return self.plan_id is not None

    def _generar_excel(self) -> None:
        if not self._asegurar_guardado():
            return
        try:
            ruta = svc_excel.generar_at_f8(self.plan_id)
        except FileNotFoundError as e:
            messagebox.showerror("Plantilla no encontrada", str(e), parent=self)
            return
        except Exception as e:
            log.exception("Error generando AT-F8 Excel")
            messagebox.showerror("Error al generar", f"No se pudo generar el Excel:\n{e}", parent=self)
            return
        confirmar_apertura(ruta)

    def _generar_pdf(self) -> None:
        if not self._asegurar_guardado():
            return
        try:
            ruta_xlsx = svc_excel.generar_at_f8(self.plan_id)
            ruta_pdf = svc_pdf.excel_a_pdf(ruta_xlsx)
        except FileNotFoundError as e:
            messagebox.showerror("Plantilla no encontrada", str(e), parent=self)
            return
        except RuntimeError as e:
            messagebox.showerror("PDF no generado", str(e), parent=self)
            return
        except Exception as e:
            log.exception("Error generando AT-F8 PDF")
            messagebox.showerror("Error al generar", f"No se pudo generar el PDF:\n{e}", parent=self)
            return
        confirmar_apertura(ruta_pdf)
