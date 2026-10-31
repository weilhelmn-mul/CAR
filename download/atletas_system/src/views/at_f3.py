# -*- coding: utf-8 -*-
"""
src/views/at_f3.py
==================
Vista AT-F3 · Informe técnico mensual del deportista albergado (fuente
primaria de datos). Flujo del pliego (9.1): elegir deportista y período →
completar secciones → Guardar (INSERT … ON CONFLICT … DO UPDATE) → Generar
Excel (rellena la plantilla oficial) → Generar PDF.

Notas documentadas:
    * Además de las secciones 1, 3, 4, 5 y 9 exigidas por el pliego, se
      editan aquí la 2 (horario), 6, 7, 8 y observaciones, porque forman
      parte de la plantilla oficial AT-F3 y del esquema de BD
      (horario_json, detalle_preparacion, participacion_competencias,
      cumplimiento_objetivos, observaciones).
    * La sección 7 permite importación manual desde un Excel/CSV exportado
      de SISDENA (services/sisdena.py); preparado para API futura.
    * El % se acepta como "95", "95%" o "0.95" y se guarda 0.0–1.0.
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
from src.services import sisdena
from src.theme import COLORS, FONTS
from src.widgets import (
    Card, FormField, PrimaryButton, SectionTitle, TextboxCard, abrir_ruta,
)

log = logging.getLogger(__name__)

_SIN_DEPORTISTAS = "— sin deportistas registrados —"


def construir(parent, app) -> None:
    """Construye la vista y devuelve la instancia (útil para pruebas)."""
    return _Vista(parent, app)


def _tokens(texto: str) -> set[str]:
    return set("".join(ch if ch.isalnum() else " " for ch in str(texto).upper()).split())


class _Vista:
    def __init__(self, parent: ctk.CTkFrame, app):
        self.app = app
        self.registro_id: int | None = None
        self._ids_deportistas: list[int] = []
        self._cargando = False  # evita dobles cargas al refrescar selectores

        contenedor = ctk.CTkFrame(parent, fg_color="transparent")
        contenedor.pack(fill="both", expand=True, padx=24, pady=18)
        contenedor.grid_columnconfigure(0, weight=1)
        contenedor.grid_rowconfigure(1, weight=1)

        self._barra_superior(contenedor)
        self._formulario(contenedor)
        self._cargar()

    # ------------------------------------------------------------------ UI
    def _barra_superior(self, contenedor) -> None:
        barra = Card(contenedor)
        barra.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        barra.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(barra, text="Deportista", font=FONTS["small_bold"], anchor="w").grid(
            row=0, column=0, sticky="w", padx=16, pady=(12, 0)
        )
        self.o_deportista = ctk.CTkOptionMenu(
            barra, values=[_SIN_DEPORTISTAS], width=420, height=32, font=FONTS["body"],
            command=lambda _v: self._cargar(),
        )
        self.o_deportista.grid(row=1, column=0, sticky="w", padx=16)

        ctk.CTkLabel(barra, text="Período (mes del informe)", font=FONTS["small_bold"], anchor="w").grid(
            row=0, column=1, sticky="w", padx=12, pady=(12, 0)
        )
        self.o_periodo = ctk.CTkOptionMenu(
            barra, values=config.lista_periodos(24), width=140, height=32, font=FONTS["body"],
            command=lambda _v: self._cargar(),
        )
        self.o_periodo.set(config.periodo_actual())
        self.o_periodo.grid(row=1, column=1, sticky="w", padx=12, pady=(0, 4))

        ctk.CTkLabel(barra, text="Entrenador", font=FONTS["small_bold"], anchor="w").grid(
            row=0, column=2, sticky="w", padx=12, pady=(12, 0)
        )
        self.c_entrenador = ctk.CTkEntry(barra, width=220, height=32, font=FONTS["body"])
        self.c_entrenador.grid(row=1, column=2, sticky="w", padx=12, pady=(0, 4))

        acciones = ctk.CTkFrame(barra, fg_color="transparent")
        acciones.grid(row=1, column=3, sticky="e", padx=16, pady=(0, 6))
        PrimaryButton(acciones, text="💾 Guardar", command=self._guardar).pack(side="left", padx=4)
        PrimaryButton(acciones, text="📄 Generar Excel", command=self._generar_excel).pack(side="left", padx=4)
        PrimaryButton(acciones, text="📕 Generar PDF", command=self._generar_pdf).pack(side="left", padx=4)

        self._refrescar_deportistas()

    def _formulario(self, contenedor) -> None:
        formulario = ctk.CTkScrollableFrame(contenedor, fg_color="transparent")
        formulario.grid(row=1, column=0, sticky="nsew")

        # Sección 1 · Objetivos y metas
        self.t_objetivos = TextboxCard(formulario, "Sección 1 · Objetivos y metas de la preparación", 120)
        self.t_objetivos.pack(fill="x", pady=8)

        # Sección 2 · Horario de entrenamiento (matriz sesión × día)
        self.horario_entradas: dict[tuple[str, str], ctk.CTkEntry] = {}
        tarjeta_horario = Card(formulario)
        tarjeta_horario.pack(fill="x", pady=8)
        SectionTitle(tarjeta_horario, "Sección 2 · Horario de entrenamiento").grid(
            row=0, column=0, columnspan=8, sticky="ew", padx=14, pady=(10, 4)
        )
        rejilla = ctk.CTkFrame(tarjeta_horario, fg_color="transparent")
        rejilla.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 12))
        rejilla.grid_columnconfigure(0, weight=1)
        for j, dia in enumerate(config.DIAS, start=1):
            rejilla.grid_columnconfigure(j, weight=1)
            ctk.CTkLabel(rejilla, text=dia.title(), font=FONTS["small_bold"]).grid(row=0, column=j, padx=3, pady=(0, 4))
        for i, sesion in enumerate(config.SESIONES, start=1):
            ctk.CTkLabel(rejilla, text=sesion.title(), font=FONTS["small_bold"]).grid(row=i, column=0, sticky="w", padx=3)
            for j, dia in enumerate(config.DIAS, start=1):
                entrada = ctk.CTkEntry(rejilla, height=28, font=FONTS["small"], placeholder_text="…")
                entrada.grid(row=i, column=j, padx=3, pady=2, sticky="ew")
                self.horario_entradas[(sesion, dia)] = entrada

        # Secciones 3 y 4 · Porcentajes
        tarjeta_pct = Card(formulario)
        tarjeta_pct.pack(fill="x", pady=8)
        SectionTitle(tarjeta_pct, "Secciones 3 y 4 · Porcentajes del mes").grid(
            row=0, column=0, columnspan=2, sticky="ew", padx=14, pady=(10, 4)
        )
        self.f_asistencia = FormField(
            tarjeta_pct, "% de asistencia a los entrenamientos",
            "Acepta 95, 95% o 0.95", ancho=260,
        )
        self.f_asistencia.grid(row=1, column=0, sticky="w", padx=14, pady=(0, 10))
        self.f_cumplimiento = FormField(
            tarjeta_pct, "% de cumplimiento del plan de entrenamiento",
            "Acepta 95, 95% o 0.95", ancho=260,
        )
        self.f_cumplimiento.grid(row=1, column=1, sticky="w", padx=14, pady=(0, 10))

        # Sección 5 · Resultados de test
        self.t_test = TextboxCard(
            formulario, "Sección 5 · Resultados de los test pedagógicos, controles internos y avances", 110
        )
        self.t_test.pack(fill="x", pady=8)

        # Sección 6 · Detalle de la preparación
        self.t_detalle = TextboxCard(formulario, "Sección 6 · Detalle de la preparación en la etapa actual", 110)
        self.t_detalle.pack(fill="x", pady=8)

        # Sección 7 · Participación en competencias (SISDENA)
        tarjeta_sisdena = Card(formulario)
        tarjeta_sisdena.pack(fill="x", pady=8)
        tarjeta_sisdena.grid_columnconfigure(0, weight=1)
        SectionTitle(
            tarjeta_sisdena, "Sección 7 · Participación en competencias nacionales e internacionales"
        ).grid(row=0, column=0, sticky="ew", padx=14, pady=(10, 2))
        ctk.CTkLabel(
            tarjeta_sisdena,
            text="El detalle oficial proviene de SISDENA (https://sisdena.ipd.gob.pe). "
                 "Importe aquí el Excel/CSV exportado del portal; el código está preparado "
                 "para una futura integración vía API.",
            font=FONTS["small"], text_color=COLORS["text_secondary"], anchor="w", justify="left",
        ).grid(row=1, column=0, sticky="ew", padx=14)
        self.t_competencias = ctk.CTkTextbox(tarjeta_sisdena, height=120, font=FONTS["body"], wrap="word")
        self.t_competencias.grid(row=2, column=0, sticky="ew", padx=14, pady=(6, 6))
        PrimaryButton(
            tarjeta_sisdena, text="⬆ Importar competencias desde SISDENA (Excel/CSV)",
            command=self._importar_sisdena,
        ).grid(row=3, column=0, sticky="w", padx=14, pady=(0, 12))

        # Sección 8 · Cumplimiento de objetivos
        self.t_cumplimiento = TextboxCard(
            formulario, "Sección 8 · Cumplimiento de los objetivos del entrenamiento y/o competencias", 110
        )
        self.t_cumplimiento.pack(fill="x", pady=8)

        # Sección 9 · Evaluación general
        self.t_evaluacion = TextboxCard(
            formulario, "Sección 9 · Evaluación general de la preparación y progresos deportivos", 110
        )
        self.t_evaluacion.pack(fill="x", pady=8)

        # Observaciones
        self.t_observaciones = TextboxCard(
            formulario, "Observaciones", 110,
            nota="* Si el deportista no cumple los porcentajes de asistencia y de preparación, "
                 "indique aquí los motivos (la plantilla oficial exige anexar documentación).",
        )
        self.t_observaciones.pack(fill="x", pady=8)

    # ------------------------------------------------------------------ datos
    def _refrescar_deportistas(self) -> None:
        con = get_connection()
        try:
            filas = con.execute(
                "SELECT id, nombres_apellidos FROM deportistas WHERE activo = 1 "
                "ORDER BY nombres_apellidos COLLATE NOCASE"
            ).fetchall()
        finally:
            con.close()
        self._ids_deportistas = [f["id"] for f in filas]
        nombres = [f["nombres_apellidos"] for f in filas] or [_SIN_DEPORTISTAS]
        actual = self.o_deportista.get()
        self.o_deportista.configure(values=nombres)
        if nombres and (actual in nombres):
            self.o_deportista.set(actual)
        else:
            self.o_deportista.set(nombres[0])

    def _deportista_sel(self) -> int | None:
        nombre = self.o_deportista.get()
        if nombre == _SIN_DEPORTISTAS or nombre not in self.o_deportista.cget("values"):
            return None
        indice = list(self.o_deportista.cget("values")).index(nombre)
        if 0 <= indice < len(self._ids_deportistas):
            return self._ids_deportistas[indice]
        return None

    def _limpiar_campos(self) -> None:
        self.registro_id = None
        self.c_entrenador.delete(0, "end")
        self.t_objetivos.set(""); self.t_test.set(""); self.t_detalle.set("")
        self.t_competencias.delete("1.0", "end")
        self.t_cumplimiento.set(""); self.t_evaluacion.set(""); self.t_observaciones.set("")
        self.f_asistencia.set(""); self.f_cumplimiento.set("")
        for entrada in self.horario_entradas.values():
            entrada.delete(0, "end")

    def _cargar(self) -> None:
        """Carga el registro AT-F3 del deportista/período elegidos (o limpia)."""
        self._cargando = True
        try:
            self._limpiar_campos()
            deportista_id = self._deportista_sel()
            if deportista_id is None:
                return
            periodo = self.o_periodo.get()
            con = get_connection()
            try:
                reg = con.execute(
                    "SELECT * FROM registros_mensuales WHERE deportista_id = ? AND periodo = ?",
                    (deportista_id, periodo),
                ).fetchone()
                dep = con.execute(
                    "SELECT entrenador FROM deportistas WHERE id = ?", (deportista_id,)
                ).fetchone()
            finally:
                con.close()
            self.c_entrenador.insert(
                0, (reg["entrenador"] if reg and reg["entrenador"] else (dep["entrenador"] if dep else "")) or ""
            )
            if reg is None:
                return
            self.registro_id = reg["id"]
            self.t_objetivos.set(reg["objetivos_metas"])
            self.f_asistencia.set(config.formatear_pct(reg["pct_asistencia"]))
            self.f_cumplimiento.set(config.formatear_pct(reg["pct_cumplimiento"]))
            self.t_test.set(reg["resultados_test"])
            self.t_detalle.set(reg["detalle_preparacion"])
            self.t_competencias.insert("1.0", reg["participacion_competencias"] or "")
            self.t_cumplimiento.set(reg["cumplimiento_objetivos"])
            self.t_evaluacion.set(reg["evaluacion_general"])
            self.t_observaciones.set(reg["observaciones"])
            horario = json.loads(reg["horario_json"]) if reg["horario_json"] else {}
            for (sesion, dia), entrada in self.horario_entradas.items():
                texto = (horario.get(sesion, {}) or {}).get(dia, "") or ""
                if texto:
                    entrada.insert(0, texto)
        finally:
            self._cargando = False

    # ------------------------------------------------------------------ acciones
    def _importar_sisdena(self) -> None:
        deportista_id = self._deportista_sel()
        if deportista_id is None:
            messagebox.showwarning("Sin deportista", "Seleccione primero un deportista.", parent=self)
            return
        con = get_connection()
        try:
            nombre = con.execute(
                "SELECT nombres_apellidos FROM deportistas WHERE id = ?", (deportista_id,)
            ).fetchone()["nombres_apellidos"]
        finally:
            con.close()
        ruta = filedialog_askopen()
        if not ruta:
            return
        try:
            registros = sisdena.importar_competencias_desde_excel(ruta)
        except (ValueError, FileNotFoundError) as e:
            messagebox.showerror("Importación SISDENA", str(e), parent=self)
            return
        except Exception as e:  # archivo corrupto u otro error de lectura
            log.exception("Error importando SISDENA")
            messagebox.showerror("Importación SISDENA", f"No se pudo leer el archivo:\n{e}", parent=self)
            return
        if not registros:
            messagebox.showinfo("Importación SISDENA", "El archivo no contiene registros de competencias.", parent=self)
            return
        del_deportista = _tokens(nombre)
        propias = [
            r for r in registros
            if len(del_deportista & _tokens(r["deportista"])) >= 2
        ]
        seleccion = propias or registros
        if not propias:
            if not messagebox.askyesno(
                "Importación SISDENA",
                f"No se encontraron filas cuyo 'Deportista' coincida claramente con {nombre}.\n"
                f"¿Desea volcar las {len(registros)} fila(s) importadas de todos modos?",
                parent=self,
            ):
                return
        lineas = "\n".join(
            f"• {r['fecha'] or 's/f'} · {r['competencia']} · {r['prueba']}"
            f" · Resultado: {r['resultado'] or '—'} · Puesto: {r['puesto'] or '—'}"
            for r in seleccion
        )
        actual = self.t_competencias.get("1.0", "end").strip()
        self.t_competencias.insert("end", ("\n" if actual else "") + lineas + "\n")
        messagebox.showinfo(
            "Importación SISDENA", f"Se agregaron {len(seleccion)} competencia(s) a la sección 7.", parent=self
        )

    def _guardar(self) -> None:
        if self._cargando:
            return
        deportista_id = self._deportista_sel()
        if deportista_id is None:
            messagebox.showwarning("Sin deportista", "Seleccione un deportista.", parent=self)
            return
        pct_asist = config.parse_porcentaje(self.f_asistencia.get())
        if self.f_asistencia.get() and pct_asist is None:
            messagebox.showerror(
                "Porcentaje no válido",
                "El % de asistencia no se entiende. Use 95, 95% o 0.95.", parent=self,
            )
            return
        pct_cump = config.parse_porcentaje(self.f_cumplimiento.get())
        if self.f_cumplimiento.get() and pct_cump is None:
            messagebox.showerror(
                "Porcentaje no válido",
                "El % de cumplimiento no se entiende. Use 95, 95% o 0.95.", parent=self,
            )
            return
        horario = {
            sesion: {dia: self.horario_entradas[(sesion, dia)].get().strip()
                     for dia in config.DIAS}
            for sesion in config.SESIONES
        }
        periodo = self.o_periodo.get()
        parametros = (
            deportista_id, periodo, self.c_entrenador.get().upper() or None,
            self.t_objetivos.get() or None,
            json.dumps(horario, ensure_ascii=False),
            pct_asist, pct_cump,
            self.t_test.get() or None, self.t_detalle.get() or None,
            self.t_competencias.get("1.0", "end").strip() or None,
            self.t_cumplimiento.get() or None, self.t_evaluacion.get() or None,
            self.t_observaciones.get() or None,
        )
        try:
            with transaccion() as con:
                con.execute(
                    """
                    INSERT INTO registros_mensuales
                        (deportista_id, periodo, entrenador, objetivos_metas, horario_json,
                         pct_asistencia, pct_cumplimiento, resultados_test, detalle_preparacion,
                         participacion_competencias, cumplimiento_objetivos, evaluacion_general,
                         observaciones, estado, updated_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,'borrador', CURRENT_TIMESTAMP)
                    ON CONFLICT(deportista_id, periodo) DO UPDATE SET
                        entrenador=excluded.entrenador,
                        objetivos_metas=excluded.objetivos_metas,
                        horario_json=excluded.horario_json,
                        pct_asistencia=excluded.pct_asistencia,
                        pct_cumplimiento=excluded.pct_cumplimiento,
                        resultados_test=excluded.resultados_test,
                        detalle_preparacion=excluded.detalle_preparacion,
                        participacion_competencias=excluded.participacion_competencias,
                        cumplimiento_objetivos=excluded.cumplimiento_objetivos,
                        evaluacion_general=excluded.evaluacion_general,
                        observaciones=excluded.observaciones,
                        updated_at=CURRENT_TIMESTAMP
                    """,
                    parametros,
                )
                fila = con.execute(
                    "SELECT id FROM registros_mensuales WHERE deportista_id = ? AND periodo = ?",
                    (deportista_id, periodo),
                ).fetchone()
                self.registro_id = fila["id"]
        except sqlite3.Error as e:
            log.exception("Error al guardar AT-F3")
            messagebox.showerror("Base de datos", f"No se pudo guardar el AT-F3:\n{e}", parent=self)
            return
        messagebox.showinfo(
            "Registro guardado", f"AT-F3 · {self.o_deportista.get()} · {periodo} guardado correctamente."
        )

    def _asegurar_guardado(self) -> bool:
        """Guarda si hay cambios pendientes; devuelve False si no se puede generar."""
        if self.registro_id is not None:
            return True
        if not messagebox.askyesno(
            "Guardar primero", "El registro aún no está guardado. ¿Desea guardarlo ahora?", parent=self
        ):
            return False
        self._guardar()
        return self.registro_id is not None

    def _generar_excel(self) -> None:
        if not self._asegurar_guardado():
            return
        try:
            ruta = svc_excel.generar_at_f3(self.registro_id)
        except FileNotFoundError as e:
            messagebox.showerror("Plantilla no encontrada", str(e), parent=self)
            return
        except Exception as e:
            log.exception("Error generando AT-F3 Excel")
            messagebox.showerror("Error al generar", f"No se pudo generar el Excel:\n{e}", parent=self)
            return
        abrir_ruta_dialogo(ruta)

    def _generar_pdf(self) -> None:
        if not self._asegurar_guardado():
            return
        try:
            ruta_xlsx = svc_excel.generar_at_f3(self.registro_id)
            ruta_pdf = svc_pdf.excel_a_pdf(ruta_xlsx)
        except FileNotFoundError as e:
            messagebox.showerror("Plantilla no encontrada", str(e), parent=self)
            return
        except RuntimeError as e:
            messagebox.showerror("PDF no generado", str(e), parent=self)
            return
        except Exception as e:
            log.exception("Error generando AT-F3 PDF")
            messagebox.showerror("Error al generar", f"No se pudo generar el PDF:\n{e}", parent=self)
            return
        abrir_ruta_dialogo(ruta_pdf)


# --- utilidades locales -----------------------------------------------------
def filedialog_askopen() -> str:
    """Selector de Excel/CSV (función separada para facilitar pruebas)."""
    from tkinter import filedialog
    return filedialog.askopenfilename(
        title="Seleccionar archivo exportado de SISDENA",
        filetypes=[("Excel o CSV", "*.xlsx *.xls *.csv"), ("Todos los archivos", "*.*")],
    )


def abrir_ruta_dialogo(ruta: str) -> None:
    """Mensaje de éxito + opción de abrir la carpeta del documento."""
    from src.widgets import confirmar_apertura
    confirmar_apertura(ruta)
