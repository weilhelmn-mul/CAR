"""
=============================================================
 Sistema AT · Instituto Peruano del Deporte (IPD - DINADAF)
 views/analisis.py — Módulo de análisis deportivo: datos
 personales agregados, categoría, cuadros estadísticos y
 mejores resultados, con exportación a Excel y PDF.
=============================================================
"""
from __future__ import annotations

from typing import Any

import customtkinter as ctk
from tkinter import messagebox

from src import database as db
from src.services import excel as servicio_excel
from src.services import pdf as servicio_pdf
from src.theme import COLORS, FONTS
from src.widgets import Card, PrimaryButton, SecondaryButton, SectionTitle, StatCard, etiqueta_datos


class AnalisisView(ctk.CTkFrame):
    """Panel de cuadros estadísticos con exportación directa."""

    def __init__(self, master: Any, app: Any) -> None:
        super().__init__(master, fg_color="transparent")
        self.app = app
        self._construir()
        self._refrescar()

    # ------------------------------------------------------------------
    def _construir(self) -> None:
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        cabecera = ctk.CTkFrame(self, fg_color="transparent")
        cabecera.grid(row=0, column=0, sticky="ew", padx=28, pady=(24, 6))
        ctk.CTkLabel(cabecera, text="Análisis deportivo", font=FONTS["h2"],
                     text_color=COLORS["text_primary"]).pack(side="left")
        acciones = ctk.CTkFrame(cabecera, fg_color="transparent")
        acciones.pack(side="right")
        PrimaryButton(acciones, "📊 Exportar Excel", self._exportar_excel, width=170).pack(side="left", padx=4)
        SecondaryButton(acciones, "📄 Exportar PDF", self._exportar_pdf, width=150).pack(side="left", padx=4)
        SecondaryButton(acciones, "🔄 Refrescar", self._refrescar, width=130).pack(side="left", padx=4)

        filtros = ctk.CTkFrame(self, fg_color="transparent")
        filtros.grid(row=1, column=0, sticky="ew", padx=28, pady=(0, 10))
        ctk.CTkLabel(filtros, text="Periodo (YYYY-MM):", font=FONTS["small_bold"],
                     text_color=COLORS["text_secondary"]).pack(side="left")
        self.campo_periodo = ctk.CTkEntry(filtros, placeholder_text="vacío = todos", width=140,
                                          font=FONTS["body"], fg_color=COLORS["bg_main"],
                                          border_color=COLORS["border"])
        self.campo_periodo.pack(side="left", padx=6)
        ctk.CTkLabel(filtros, text="Año de resultados:", font=FONTS["small_bold"],
                     text_color=COLORS["text_secondary"]).pack(side="left", padx=(16, 0))
        self.campo_anio = ctk.CTkEntry(filtros, placeholder_text="vacío = todos", width=140,
                                       font=FONTS["body"], fg_color=COLORS["bg_main"],
                                       border_color=COLORS["border"])
        self.campo_anio.pack(side="left", padx=6)
        ctk.CTkLabel(filtros, text="Los cuadros y la exportación usan estos filtros.",
                     font=FONTS["small"], text_color=COLORS["text_secondary"]).pack(side="left", padx=16)

        self.cuerpo = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.cuerpo.grid(row=2, column=0, sticky="nsew", padx=28, pady=(0, 24))
        self.cuerpo.grid_columnconfigure(0, weight=1)
        self.cuerpo.grid_columnconfigure(1, weight=1)

    # ------------------------------------------------------------------
    def _refrescar(self) -> None:
        """Redibuja todos los cuadros estadísticos."""
        for widget in self.cuerpo.winfo_children():
            widget.destroy()

        # --- Indicadores ----------------------------------------------------
        fila_indicadores = ctk.CTkFrame(self.cuerpo, fg_color="transparent")
        fila_indicadores.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 12))
        for columna in range(4):
            fila_indicadores.grid_columnconfigure(columna, weight=1)
        conteo_seguros = db.resumen_seguros()
        damas = next((int(f["n"]) for f in db.distribucion("sexo") if f["clave"] == "D"), 0)
        varones = next((int(f["n"]) for f in db.distribucion("sexo") if f["clave"] == "V"), 0)
        indicadores = [
            ("Deportistas activos", str(db.contar_deportistas(True)), COLORS["accent"]),
            ("Damas", str(damas), COLORS["accent"]),
            ("Varones", str(varones), COLORS["accent"]),
            ("Pólizas vigentes", str(conteo_seguros.get("VIGENTE", 0)), COLORS["success"]),
        ]
        for columna, (titulo, valor, color) in enumerate(indicadores):
            StatCard(fila_indicadores, titulo, valor, color).grid(
                row=0, column=columna, sticky="ew", padx=5)
        if conteo_seguros.get("VENCIDO", 0):
            tarjeta_alerta = Card(fila_indicadores)
            tarjeta_alerta.grid(row=1, column=0, columnspan=4, sticky="ew", padx=5, pady=(10, 0))
            etiqueta_datos(tarjeta_alerta,
                           f"⚠ {conteo_seguros['VENCIDO']} póliza(s) de seguro VENCIDA(S): "
                           "gestione su renovación en el módulo de Seguros.",
                           COLORS["danger"]).pack(anchor="w", padx=16, pady=10)

        self._cuadro_matricula(0, 0)
        self._cuadro_deportes(0, 1)
        self._cuadro_rendimiento(1, 0)
        self._cuadro_top_resultados(1, 1)
        self._cuadro_alimentacion(2, 0)
        self._cuadro_categorias_sexo(2, 1)

    # ------------------------------------------------------------------
    def _tarjeta(self, fila: int, columna: int, titulo: str) -> ctk.CTkFrame:
        tarjeta = Card(self.cuerpo)
        tarjeta.grid(row=fila, column=columna, sticky="nsew", padx=5, pady=6)
        SectionTitle(tarjeta, titulo).pack(anchor="w", padx=18, pady=(14, 6))
        contenedor = ctk.CTkFrame(tarjeta, fg_color="transparent")
        contenedor.pack(fill="both", expand=True, padx=18, pady=(0, 12))
        return contenedor

    @staticmethod
    def _tabla(contenedor: ctk.CTkFrame, cabeceras: tuple[str, ...], pesos: tuple[int, ...],
               filas: list[tuple], color_columna: dict[int, Any] | None = None) -> None:
        """Tabla simple de etiquetas dentro de un contenedor."""
        for columna, peso in enumerate(pesos):
            contenedor.grid_columnconfigure(columna, weight=peso)
        for columna, texto in enumerate(cabeceras):
            etiqueta_datos(contenedor, texto, COLORS["text_secondary"]).grid(
                row=0, column=columna, sticky="ew", padx=6, pady=2)
        for numero, valores in enumerate(filas, start=1):
            for columna, valor in enumerate(valores):
                color = None
                if color_columna and columna in color_columna:
                    color = color_columna[columna](valores[columna])
                etiqueta_datos(contenedor, str(valor), color).grid(
                    row=numero, column=columna, sticky="ew", padx=6, pady=2)
        if not filas:
            etiqueta_datos(contenedor, "Sin datos registrados.",
                           COLORS["text_secondary"]).grid(row=1, column=0, sticky="w", pady=4)

    # ------------------------------------------------------------------
    def _cuadro_matricula(self, fila: int, columna: int) -> None:
        contenedor = self._tarjeta(fila, columna, "Matrícula por categoría y sexo")
        filas = [(m["categoria"], int(m["damas"]), int(m["varones"]), int(m["total"]))
                 for m in db.matricula_por_categoria_sexo()]
        self._tabla(contenedor, ("Categoría", "Damas", "Varones", "Total"),
                    (3, 2, 2, 2), filas)

    def _cuadro_deportes(self, fila: int, columna: int) -> None:
        contenedor = self._tarjeta(fila, columna, "Distribución por deporte")
        filas = [(d["clave"], int(d["n"])) for d in db.distribucion("deporte")]
        self._tabla(contenedor, ("Deporte", "Deportistas"), (4, 2), filas)

    def _cuadro_rendimiento(self, fila: int, columna: int) -> None:
        contenedor = self._tarjeta(fila, columna, "Asistencia y cumplimiento promedio")
        filas = []
        for promedio in db.promedios_por_periodo(8):
            filas.append((
                promedio["periodo"],
                f"{promedio['asistencia'] * 100:.1f} %" if promedio["asistencia"] is not None else "—",
                f"{promedio['cumplimiento'] * 100:.1f} %" if promedio["cumplimiento"] is not None else "—",
                int(promedio["registros"]),
            ))
        self._tabla(contenedor, ("Periodo", "% Asistencia", "% Cumplimiento", "Informes"),
                    (2, 2, 2, 2), filas)

    def _cuadro_top_resultados(self, fila: int, columna: int) -> None:
        anio = self.campo_anio.get().strip()
        contenedor = self._tarjeta(fila, columna, f"Mejores resultados {'del año ' + anio if anio else '(todos)'}")
        desde = f"{anio}-01-01" if anio else ""
        hasta = f"{anio}-12-31" if anio else ""
        podio = [r for r in db.resultados_deporte_car(desde, hasta)
                 if r["posicion"] is not None and int(r["posicion"]) <= 3][:12]
        filas = [(r["fecha"], r["nombre"], r["competencia"],
                  f"{r['posicion']}.°", r["marca"] or "—") for r in podio]
        color_puesto = {3: lambda v: COLORS["success"] if str(v).startswith("1") else None}
        self._tabla(contenedor, ("Fecha", "Deportista", "Competencia", "Puesto", "Marca"),
                    (2, 3, 4, 1, 2), filas, color_puesto)

    def _cuadro_alimentacion(self, fila: int, columna: int) -> None:
        contenedor = self._tarjeta(fila, columna, "IMC promedio por categoría (nutrición)")
        filas = []
        for fila_imc in db.imc_promedio_por_categoria():
            imc_prom = float(fila_imc["imc_prom"])
            lectura = ("Bajo peso" if imc_prom < 18.5 else
                       "Saludable" if imc_prom < 25 else
                       "Sobrepeso" if imc_prom < 30 else "Obesidad")
            filas.append((fila_imc["clave"], f"{imc_prom:.1f}", int(fila_imc["n"]), lectura))
        color_lectura = {3: lambda v: {"Bajo peso": COLORS["warning"],
                                       "Obesidad": COLORS["danger"],
                                       "Sobrepeso": COLORS["warning"]}.get(str(v))}
        self._tabla(contenedor, ("Categoría", "IMC prom.", "Eval.", "Lectura"),
                    (2, 2, 1, 2), filas, color_lectura)

    def _cuadro_categorias_sexo(self, fila: int, columna: int) -> None:
        contenedor = self._tarjeta(fila, columna, "Distribución por sexo")
        filas = [({"D": "Damas", "V": "Varones"}.get(d["clave"], d["clave"]), int(d["n"]))
                 for d in db.distribucion("sexo")]
        self._tabla(contenedor, ("Sexo", "Deportistas"), (4, 2), filas)

    # ------------------------------------------------------------------
    def _filtros_actuales(self) -> tuple[str, str]:
        return self.campo_periodo.get().strip(), self.campo_anio.get().strip()

    def _exportar_excel(self) -> None:
        periodo, anio = self._filtros_actuales()
        try:
            ruta = servicio_excel.generar_analisis(periodo=periodo, anio=anio)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Exportar", f"No se pudo generar el análisis:\n{exc}")
            return
        messagebox.showinfo("Excel generado", f"Análisis deportivo generado en:\n{ruta}")

    def _exportar_pdf(self) -> None:
        periodo, anio = self._filtros_actuales()
        try:
            ruta = servicio_excel.generar_analisis(periodo=periodo, anio=anio)
            pdf = servicio_pdf.excel_a_pdf(ruta)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Exportar", f"No se pudo generar el PDF:\n{exc}")
            return
        messagebox.showinfo("PDF generado", f"PDF disponible en:\n{pdf}")
