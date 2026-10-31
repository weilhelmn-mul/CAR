# -*- coding: utf-8 -*-
"""
src/views/at_f1.py
==================
Vista AT-F1 · Informe mensual del área técnica (JUT) y/o entrenadores,
consolidado del CAR.

Automatismos (flujo 9.2 del pliego):
    * Sección I: las matrículas se agregan automáticamente desde los
      deportistas del período (activos por categoría y sexo; ingresos y
      retiros según fecha_ingreso / fecha_retiro dentro del mes).
    * Sección II.I: tabla autogenerada desde los registros AT-F3 del período.
El JUT completa las valoraciones cualitativas y genera Excel (con dos firmas:
JUT/DINADAF y Entrenador) y PDF.
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
from src.widgets import Card, FormField, PrimaryButton, SectionTitle, TablaFrame, TextboxCard
from src.widgets import abrir_ruta, confirmar_apertura

log = logging.getLogger(__name__)


def construir(parent, app) -> None:
    """Construye la vista y devuelve la instancia (útil para pruebas)."""
    return _Vista(parent, app)


def _acortar(texto: str | None, n: int = 90) -> str:
    texto = (texto or "").strip().replace("\n", " ")
    return texto if len(texto) <= n else texto[: n - 1] + "…"


class _Vista:
    def __init__(self, parent: ctk.CTkFrame, app):
        self.app = app
        self.consolidado_id: int | None = None
        self._cargando = False

        contenedor = ctk.CTkFrame(parent, fg_color="transparent")
        contenedor.pack(fill="both", expand=True, padx=24, pady=18)
        contenedor.grid_columnconfigure(0, weight=1)
        contenedor.grid_rowconfigure(1, weight=1)

        self._barra_superior(contenedor)

        formulario = ctk.CTkScrollableFrame(contenedor, fg_color="transparent")
        formulario.grid(row=1, column=0, sticky="nsew")
        self._seccion_matriculas(formulario)
        self._seccion_tabla_deportistas(formulario)
        self._seccion_textos(formulario)

        self._cargar()

    # ------------------------------------------------------------------ UI
    def _barra_superior(self, contenedor) -> None:
        barra = Card(contenedor)
        barra.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        self.f_car = FormField(barra, "CAR", "Ej. CUSCO", ancho=180)
        self.f_car.grid(row=0, column=0, sticky="w", padx=16, pady=12)
        ctk.CTkLabel(barra, text="Período", font=FONTS["small_bold"], anchor="w").grid(
            row=0, column=1, sticky="w", padx=8, pady=(12, 0)
        )
        self.o_periodo = ctk.CTkOptionMenu(
            barra, values=config.lista_periodos(24), width=140, height=32, font=FONTS["body"],
            command=lambda _v: self._cargar(),
        )
        self.o_periodo.set(config.periodo_actual())
        self.o_periodo.grid(row=1, column=1, sticky="w", padx=8, pady=(0, 10))
        PrimaryButton(
            barra, text="🔁 Recalcular matrículas", command=self._recalcular_matriculas
        ).grid(row=1, column=2, sticky="w", padx=8, pady=(0, 10))
        acciones = ctk.CTkFrame(barra, fg_color="transparent")
        acciones.grid(row=0, column=3, rowspan=2, sticky="e", padx=16)
        PrimaryButton(acciones, text="💾 Guardar", command=self._guardar).pack(side="left", padx=4, pady=12)
        PrimaryButton(acciones, text="📄 Generar Excel", command=self._generar_excel).pack(side="left", padx=4, pady=12)
        PrimaryButton(acciones, text="📕 Generar PDF", command=self._generar_pdf).pack(side="left", padx=4, pady=12)

    def _seccion_matriculas(self, formulario) -> None:
        """Sección I: tabla editable de matrículas por categoría."""
        tarjeta = Card(formulario)
        tarjeta.pack(fill="x", pady=8)
        SectionTitle(
            tarjeta, "Sección I · Comportamiento de las matrículas (automático desde Deportistas)"
        ).grid(row=0, column=0, columnspan=9, sticky="ew", padx=14, pady=(10, 6))
        rejilla = ctk.CTkFrame(tarjeta, fg_color="transparent")
        rejilla.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 12))
        encabezados = ["Categoría", "Retiros", "Ingresos", "Damas", "Varones", "Total",
                       "N° sesiones", "Horario mañana", "Horario tarde"]
        for j, texto in enumerate(encabezados):
            rejilla.grid_columnconfigure(j, weight=2 if j in (7, 8) else 1)
            ctk.CTkLabel(rejilla, text=texto, font=FONTS["small_bold"]).grid(row=0, column=j, padx=3, pady=(0, 4))
        self.m_entradas: dict[str, dict[str, ctk.CTkEntry]] = {}
        self.m_total: dict[str, ctk.CTkLabel] = {}
        for i, categoria in enumerate(config.CATEGORIAS, start=1):
            ctk.CTkLabel(rejilla, text=categoria, font=FONTS["small_bold"]).grid(row=i, column=0, padx=3)
            self.m_entradas[categoria] = {}
            for j, campo in enumerate(("retiros", "ingresos", "damas", "varones"), start=1):
                entrada = ctk.CTkEntry(rejilla, width=70, height=28, justify="center")
                entrada.grid(row=i, column=j, padx=3, pady=2)
                self.m_entradas[categoria][campo] = entrada
            self.m_total[categoria] = ctk.CTkLabel(
                rejilla, text="0", font=FONTS["small_bold"], text_color=COLORS["accent"]
            )
            self.m_total[categoria].grid(row=i, column=5, padx=3)
            for j, campo in enumerate(("sesiones", "manana", "tarde"), start=6):
                entrada = ctk.CTkEntry(rejilla, width=90 if campo == "sesiones" else 110, height=28)
                entrada.grid(row=i, column=j, padx=3, pady=2, sticky="ew")
                self.m_entradas[categoria][campo] = entrada

    def _seccion_tabla_deportistas(self, formulario) -> None:
        """Sección II.I: tabla autogenerada desde los AT-F3 del período."""
        tarjeta = Card(formulario)
        tarjeta.pack(fill="x", pady=8)
        tarjeta.grid_columnconfigure(0, weight=1)
        SectionTitle(
            tarjeta, "Sección II.I · Cumplimiento de los planes de entrenamiento (automático desde AT-F3)"
        ).grid(row=0, column=0, sticky="ew", padx=14, pady=(10, 4))
        PrimaryButton(
            tarjeta, text="🔄 Actualizar tabla", command=self._refrescar_tabla_atletas
        ).grid(row=0, column=1, sticky="e", padx=14, pady=(10, 4))
        self.tabla_atletas = TablaFrame(
            tarjeta,
            columnas=["N°", "Nombres y apellidos", "Deporte", "Prueba/Modalidad",
                      "% Asist.", "% Cumpl.", "Resultados competitivos y observaciones técnicas"],
            pesos=[0.5, 3, 1.8, 1.6, 1, 1, 5],
            altura=260,
        )
        self.tabla_atletas.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=14, pady=(0, 12))

    def _seccion_textos(self, formulario) -> None:
        self.t_valoracion_tecnica = TextboxCard(
            formulario, "Sección II-II · Valoración de la participación en test/controles/topes/competencias", 110
        )
        self.t_valoracion_tecnica.pack(fill="x", pady=8)
        self.t_dificultades = TextboxCard(
            formulario, "Sección II.III · Principales dificultades en el cumplimiento de los planes", 110
        )
        self.t_dificultades.pack(fill="x", pady=8)
        self.t_medica = TextboxCard(formulario, "Sección III · Valoración médica general", 100)
        self.t_medica.pack(fill="x", pady=8)
        self.t_profilactico = TextboxCard(
            formulario, "Sección III-I · Plan profiláctico / tratamientos / deportistas lesionados", 100
        )
        self.t_profilactico.pack(fill="x", pady=8)
        self.t_nutricional = TextboxCard(
            formulario, "Sección III-II · Comportamiento del balance nutricional en K/calorías", 100
        )
        self.t_nutricional.pack(fill="x", pady=8)
        self.t_car = TextboxCard(formulario, "Sección IV · Valoración del funcionamiento del CAR", 100)
        self.t_car.pack(fill="x", pady=8)
        self.t_negativos = TextboxCard(formulario, "Sección IV-I · Aspectos negativos del CAR", 90)
        self.t_negativos.pack(fill="x", pady=8)
        self.t_logros = TextboxCard(formulario, "Sección IV-I · Principales logros del CAR", 90)
        self.t_logros.pack(fill="x", pady=8)
        self.t_otros = TextboxCard(formulario, "Sección IV.II · Otros aspectos de interés", 90)
        self.t_otros.pack(fill="x", pady=8)

    # ------------------------------------------------------------------ datos
    def _car(self) -> str:
        return self.f_car.get().upper()

    def _recalcular_matriculas(self) -> None:
        """Agrega la Sección I desde la tabla deportistas (activos del período)."""
        periodo = self.o_periodo.get()
        con = get_connection()
        try:
            filas = con.execute(
                """
                SELECT categoria,
                       COALESCE(SUM(CASE WHEN sexo='D' AND activo=1 THEN 1 ELSE 0 END),0) AS damas,
                       COALESCE(SUM(CASE WHEN sexo='V' AND activo=1 THEN 1 ELSE 0 END),0) AS varones,
                       COALESCE(SUM(CASE WHEN activo=1 AND SUBSTR(COALESCE(fecha_ingreso,''),1,7)=:p
                                         THEN 1 ELSE 0 END),0) AS ingresos,
                       COALESCE(SUM(CASE WHEN SUBSTR(COALESCE(fecha_retiro,''),1,7)=:p
                                         THEN 1 ELSE 0 END),0) AS retiros
                FROM deportistas GROUP BY categoria
                """,
                {"p": periodo},
            ).fetchall()
        finally:
            con.close()
        agregado = {f["categoria"]: f for f in filas}
        for categoria in config.CATEGORIAS:
            f = agregado.get(categoria)
            e = self.m_entradas[categoria]
            e["retiros"].delete(0, "end"); e["retiros"].insert(0, str(f["retiros"] if f else 0))
            e["ingresos"].delete(0, "end"); e["ingresos"].insert(0, str(f["ingresos"] if f else 0))
            e["damas"].delete(0, "end"); e["damas"].insert(0, str(f["damas"] if f else 0))
            e["varones"].delete(0, "end"); e["varones"].insert(0, str(f["varones"] if f else 0))
            self._actualizar_total(categoria)

    def _actualizar_total(self, categoria: str) -> None:
        try:
            damas = int(self.m_entradas[categoria]["damas"].get() or 0)
            varones = int(self.m_entradas[categoria]["varones"].get() or 0)
        except ValueError:
            damas = varones = 0
        self.m_total[categoria].configure(text=str(damas + varones))

    def _refrescar_tabla_atletas(self) -> None:
        """Llena la Sección II.I con los registros AT-F3 del período."""
        periodo = self.o_periodo.get()
        con = get_connection()
        try:
            filas = con.execute(
                """
                SELECT d.nombres_apellidos, d.deporte, d.prueba_modalidad,
                       r.pct_asistencia, r.pct_cumplimiento,
                       r.participacion_competencias, r.detalle_preparacion
                FROM registros_mensuales r JOIN deportistas d ON d.id = r.deportista_id
                WHERE r.periodo = ?
                ORDER BY d.nombres_apellidos COLLATE NOCASE
                """,
                (periodo,),
            ).fetchall()
        finally:
            con.close()
        self.tabla_atletas.limpiar()
        if not filas:
            ctk.CTkLabel(
                self.tabla_atletas,
                text=f"No hay registros AT-F3 del período {periodo}. Regístrelos en la vista AT-F3.",
                font=FONTS["small"], text_color=COLORS["text_secondary"],
            ).grid(row=1, column=0, columnspan=7, pady=20)
            return
        for i, a in enumerate(filas):
            fila = self.tabla_atletas.nueva_fila(zebra=i % 2 == 1)
            resultado = a["participacion_competencias"] or a["detalle_preparacion"] or ""
            valores = [
                str(i + 1), a["nombres_apellidos"], a["deporte"] or "", a["prueba_modalidad"] or "",
                config.formatear_pct(a["pct_asistencia"]), config.formatear_pct(a["pct_cumplimiento"]),
                _acortar(resultado),
            ]
            for j, texto in enumerate(valores):
                ctk.CTkLabel(
                    fila, text=texto, font=FONTS["small"] if j else FONTS["small_bold"], anchor="w"
                ).grid(row=0, column=j, sticky="ew", padx=6)

    def _cargar(self) -> None:
        self._cargando = True
        try:
            self.consolidado_id = None
            for categoria in config.CATEGORIAS:
                for entrada in self.m_entradas[categoria].values():
                    entrada.delete(0, "end")
                self.m_total[categoria].configure(text="0")
            for tarjeta in (self.t_valoracion_tecnica, self.t_dificultades, self.t_medica,
                            self.t_profilactico, self.t_nutricional, self.t_car,
                            self.t_negativos, self.t_logros, self.t_otros):
                tarjeta.set("")
            self._refrescar_tabla_atletas()

            car = self._car()
            if not car:
                self._recalcular_matriculas()
                return
            periodo = self.o_periodo.get()
            con = get_connection()
            try:
                consol = con.execute(
                    "SELECT * FROM consolidados_at_f1 WHERE car = ? AND periodo = ?",
                    (car, periodo),
                ).fetchone()
            finally:
                con.close()
            if consol is None:
                self._recalcular_matriculas()
                return
            self.consolidado_id = consol["id"]
            matriculas = json.loads(consol["matriculas_json"]) if consol["matriculas_json"] else {}
            for categoria in config.CATEGORIAS:
                d = matriculas.get(categoria, {}) or {}
                e = self.m_entradas[categoria]
                for campo in ("retiros", "ingresos", "damas", "varones", "sesiones", "manana", "tarde"):
                    e[campo].insert(0, "" if d.get(campo) in (None, "") else str(d.get(campo)))
                self._actualizar_total(categoria)
            self.t_valoracion_tecnica.set(consol["valoracion_tecnica"])
            self.t_dificultades.set(consol["dificultades"])
            self.t_medica.set(consol["valoracion_medica"])
            self.t_profilactico.set(consol["plan_profilactico"])
            self.t_nutricional.set(consol["balance_nutricional"])
            self.t_car.set(consol["valoracion_car"])
            self.t_negativos.set(consol["aspectos_negativos"])
            self.t_logros.set(consol["logros_car"])
            self.t_otros.set(consol["otros_aspectos"])
        finally:
            self._cargando = False

    # ------------------------------------------------------------------ acciones
    def _guardar(self) -> None:
        if self._cargando:
            return
        car = self._car()
        if not car:
            messagebox.showwarning("Campo obligatorio", "Indique el CAR (ej. CUSCO).", parent=self)
            return
        matriculas = {}
        for categoria in config.CATEGORIAS:
            e = self.m_entradas[categoria]
            try:
                damas = int(e["damas"].get() or 0)
                varones = int(e["varones"].get() or 0)
            except ValueError:
                messagebox.showerror(
                    "Valores numéricos", f"Revisar damas/varones de {categoria}: deben ser números.",
                    parent=self,
                )
                return
            matriculas[categoria] = {
                "retiros": int(e["retiros"].get() or 0),
                "ingresos": int(e["ingresos"].get() or 0),
                "damas": damas, "varones": varones, "total": damas + varones,
                "sesiones": int(e["sesiones"].get()) if e["sesiones"].get().strip() else None,
                "manana": e["manana"].get().strip() or None,
                "tarde": e["tarde"].get().strip() or None,
            }
        periodo = self.o_periodo.get()
        try:
            with transaccion() as con:
                con.execute(
                    """
                    INSERT INTO consolidados_at_f1
                        (car, periodo, matriculas_json, valoracion_tecnica, dificultades,
                         valoracion_medica, plan_profilactico, balance_nutricional, valoracion_car,
                         aspectos_negativos, logros_car, otros_aspectos, estado)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?, 'borrador')
                    ON CONFLICT(car, periodo) DO UPDATE SET
                        matriculas_json=excluded.matriculas_json,
                        valoracion_tecnica=excluded.valoracion_tecnica,
                        dificultades=excluded.dificultades,
                        valoracion_medica=excluded.valoracion_medica,
                        plan_profilactico=excluded.plan_profilactico,
                        balance_nutricional=excluded.balance_nutricional,
                        valoracion_car=excluded.valoracion_car,
                        aspectos_negativos=excluded.aspectos_negativos,
                        logros_car=excluded.logros_car,
                        otros_aspectos=excluded.otros_aspectos
                    """,
                    (car, periodo, json.dumps(matriculas, ensure_ascii=False),
                     self.t_valoracion_tecnica.get() or None, self.t_dificultades.get() or None,
                     self.t_medica.get() or None, self.t_profilactico.get() or None,
                     self.t_nutricional.get() or None, self.t_car.get() or None,
                     self.t_negativos.get() or None, self.t_logros.get() or None,
                     self.t_otros.get() or None),
                )
                fila = con.execute(
                    "SELECT id FROM consolidados_at_f1 WHERE car = ? AND periodo = ?",
                    (car, periodo),
                ).fetchone()
                self.consolidado_id = fila["id"]
        except sqlite3.Error as e:
            log.exception("Error al guardar AT-F1")
            messagebox.showerror("Base de datos", f"No se pudo guardar el AT-F1:\n{e}", parent=self)
            return
        messagebox.showinfo("Registro guardado", f"AT-F1 · {car} · {periodo} guardado correctamente.")

    def _asegurar_guardado(self) -> bool:
        if self.consolidado_id is not None:
            return True
        if not messagebox.askyesno(
            "Guardar primero", "El consolidado aún no está guardado. ¿Desea guardarlo ahora?", parent=self
        ):
            return False
        self._guardar()
        return self.consolidado_id is not None

    def _generar_excel(self) -> None:
        if not self._asegurar_guardado():
            return
        try:
            ruta = svc_excel.generar_at_f1(self.consolidado_id)
        except FileNotFoundError as e:
            messagebox.showerror("Plantilla no encontrada", str(e), parent=self)
            return
        except Exception as e:
            log.exception("Error generando AT-F1 Excel")
            messagebox.showerror("Error al generar", f"No se pudo generar el Excel:\n{e}", parent=self)
            return
        confirmar_apertura(ruta)

    def _generar_pdf(self) -> None:
        if not self._asegurar_guardado():
            return
        try:
            ruta_xlsx = svc_excel.generar_at_f1(self.consolidado_id)
            ruta_pdf = svc_pdf.excel_a_pdf(ruta_xlsx)
        except FileNotFoundError as e:
            messagebox.showerror("Plantilla no encontrada", str(e), parent=self)
            return
        except RuntimeError as e:
            messagebox.showerror("PDF no generado", str(e), parent=self)
            return
        except Exception as e:
            log.exception("Error generando AT-F1 PDF")
            messagebox.showerror("Error al generar", f"No se pudo generar el PDF:\n{e}", parent=self)
            return
        confirmar_apertura(ruta_pdf)
