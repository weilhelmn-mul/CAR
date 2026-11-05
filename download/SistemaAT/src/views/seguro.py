"""
=============================================================
 Sistema AT · Instituto Peruano del Deporte (IPD - DINADAF)
 views/seguro.py — Formato de seguro: pólizas por deportista
 con alerta de vencimiento y exportación a Excel/PDF.
=============================================================
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any

import customtkinter as ctk
from tkinter import messagebox

from src import database as db
from src.config import ESTADOS_SEGURO, TIPOS_SEGURO
from src.services import excel as servicio_excel
from src.services import pdf as servicio_pdf
from src.theme import COLORS, FONTS
from src.widgets import Card, PrimaryButton, SecondaryButton, SectionTitle, etiqueta_datos

DIAS_ALERTA = 30


class SeguroView(ctk.CTkFrame):
    """Formulario + listado de pólizas de seguro deportivo."""

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

        formulario = Card(self, width=400)
        formulario.grid(row=0, column=0, sticky="ns", padx=(28, 10), pady=(24, 24))
        formulario.pack_propagate(False)
        SectionTitle(formulario, "🛡️ Póliza de seguro deportivo").pack(anchor="w", padx=18, pady=(14, 6))

        ctk.CTkLabel(formulario, text="Deportista *", font=FONTS["small_bold"],
                     text_color=COLORS["text_secondary"], anchor="w").pack(fill="x", padx=18, pady=(2, 2))
        self.menu_deportista = ctk.CTkOptionMenu(
            formulario, values=["— sin deportistas —"], font=FONTS["body"],
            fg_color=COLORS["bg_main"], button_color=COLORS["accent"],
            button_hover_color=COLORS["accent_hover"])
        self.menu_deportista.pack(fill="x", padx=18, pady=2)

        self.campo_aseguradora = self._campo(formulario, "Aseguradora *", "Ej.: Pacífico Seguros")
        self.campo_poliza = self._campo(formulario, "N.° de póliza", "Ej.: POL-2026-001487")

        fila_tipo = ctk.CTkFrame(formulario, fg_color="transparent")
        fila_tipo.pack(fill="x", padx=18, pady=4)
        fila_tipo.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkLabel(fila_tipo, text="Tipo de seguro", font=FONTS["small_bold"],
                     text_color=COLORS["text_secondary"], anchor="w").grid(row=0, column=0, sticky="ew")
        ctk.CTkLabel(fila_tipo, text="Estado", font=FONTS["small_bold"],
                     text_color=COLORS["text_secondary"], anchor="w").grid(row=0, column=1, sticky="ew")
        self.menu_tipo = ctk.CTkOptionMenu(fila_tipo, values=list(TIPOS_SEGURO), font=FONTS["body"],
                                           fg_color=COLORS["bg_main"], button_color=COLORS["accent"],
                                           button_hover_color=COLORS["accent_hover"])
        self.menu_tipo.set("SALUD")
        self.menu_tipo.grid(row=1, column=0, sticky="ew", padx=(0, 6))
        self.menu_estado = ctk.CTkOptionMenu(fila_tipo, values=list(ESTADOS_SEGURO), font=FONTS["body"],
                                             fg_color=COLORS["bg_main"], button_color=COLORS["accent"],
                                             button_hover_color=COLORS["accent_hover"])
        self.menu_estado.set("VIGENTE")
        self.menu_estado.grid(row=1, column=1, sticky="ew")

        fila_vigencia = ctk.CTkFrame(formulario, fg_color="transparent")
        fila_vigencia.pack(fill="x", padx=18, pady=4)
        fila_vigencia.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkLabel(fila_vigencia, text="Vigencia desde (YYYY-MM-DD)", font=FONTS["small_bold"],
                     text_color=COLORS["text_secondary"], anchor="w").grid(row=0, column=0, sticky="ew")
        ctk.CTkLabel(fila_vigencia, text="Vigencia hasta (YYYY-MM-DD)", font=FONTS["small_bold"],
                     text_color=COLORS["text_secondary"], anchor="w").grid(row=0, column=1, sticky="ew")
        self.campo_inicio = ctk.CTkEntry(fila_vigencia, placeholder_text="2026-01-01", font=FONTS["body"],
                                         fg_color=COLORS["bg_main"], border_color=COLORS["border"])
        self.campo_inicio.grid(row=1, column=0, sticky="ew", padx=(0, 6))
        self.campo_fin = ctk.CTkEntry(fila_vigencia, placeholder_text="2026-12-31", font=FONTS["body"],
                                      fg_color=COLORS["bg_main"], border_color=COLORS["border"])
        self.campo_fin.grid(row=1, column=1, sticky="ew")

        self.campo_cobertura = self._campo(formulario, "Cobertura", "Ej.: Accidentes deportivos y gastos médicos")
        ctk.CTkLabel(formulario, text="Observaciones", font=FONTS["small_bold"],
                     text_color=COLORS["text_secondary"], anchor="w").pack(fill="x", padx=18, pady=(6, 2))
        self.texto_observaciones = ctk.CTkTextbox(formulario, height=70, font=FONTS["body"], wrap="word")
        self.texto_observaciones.pack(fill="x", padx=18, pady=2)

        botones = ctk.CTkFrame(formulario, fg_color="transparent")
        botones.pack(fill="x", padx=18, pady=(10, 16))
        PrimaryButton(botones, "💾 Guardar póliza", self._guardar).pack(fill="x", pady=3)
        SecondaryButton(botones, "📊 Exportar listado (Excel)", self._exportar_excel).pack(fill="x", pady=3)
        SecondaryButton(botones, "📄 Exportar listado (PDF)", self._exportar_pdf).pack(fill="x", pady=3)
        SecondaryButton(botones, "🧹 Limpiar formulario", self._limpiar).pack(fill="x", pady=3)

        tabla_card = Card(self)
        tabla_card.grid(row=0, column=1, sticky="nsew", padx=(0, 28), pady=(24, 24))
        SectionTitle(tabla_card, "Pólizas registradas").pack(anchor="w", padx=18, pady=(14, 6))
        filtros = ctk.CTkFrame(tabla_card, fg_color="transparent")
        filtros.pack(fill="x", padx=18, pady=(0, 6))
        ctk.CTkLabel(filtros, text="Estado:", font=FONTS["small_bold"],
                     text_color=COLORS["text_secondary"]).pack(side="left")
        self.menu_filtro = ctk.CTkOptionMenu(filtros, values=["Todos", *ESTADOS_SEGURO], font=FONTS["body"],
                                             fg_color=COLORS["bg_main"], button_color=COLORS["accent"],
                                             button_hover_color=COLORS["accent_hover"],
                                             command=lambda _v: self._refrescar_tabla())
        self.menu_filtro.set("Todos")
        self.menu_filtro.pack(side="left", padx=8)
        self.tabla = ctk.CTkScrollableFrame(tabla_card, fg_color="transparent")
        self.tabla.pack(fill="both", expand=True, padx=18, pady=(0, 16))

    # ------------------------------------------------------------------
    def _campo(self, contenedor: Any, titulo: str, placeholder: str) -> ctk.CTkEntry:
        ctk.CTkLabel(contenedor, text=titulo, font=FONTS["small_bold"],
                     text_color=COLORS["text_secondary"], anchor="w").pack(fill="x", padx=18, pady=(6, 2))
        entrada = ctk.CTkEntry(contenedor, placeholder_text=placeholder, font=FONTS["body"],
                               fg_color=COLORS["bg_main"], border_color=COLORS["border"])
        entrada.pack(fill="x", padx=18, pady=2)
        return entrada

    def _refrescar_selector(self) -> None:
        opciones = db.opciones_deportistas()
        self._opciones_deportistas = opciones
        valores = [texto for _i, texto in opciones] or ["— sin deportistas —"]
        self.menu_deportista.configure(values=valores)
        self.menu_deportista.set(valores[0])

    # ------------------------------------------------------------------
    @staticmethod
    def _dias_para_vencer(fecha_fin: str) -> int | None:
        try:
            limite = datetime.strptime(fecha_fin, "%Y-%m-%d").date()
        except ValueError:
            return None
        return (limite - date.today()).days

    def _refrescar_tabla(self) -> None:
        for widget in self.tabla.winfo_children():
            widget.destroy()
        estado = "" if self.menu_filtro.get() == "Todos" else self.menu_filtro.get()
        filas = db.listar_seguros(estado)
        cabecera = ctk.CTkFrame(self.tabla, fg_color=COLORS["bg_main"], corner_radius=6)
        cabecera.pack(fill="x", pady=(0, 4))
        for columna, peso in enumerate((4, 2, 3, 3, 3, 2)):
            cabecera.grid_columnconfigure(columna, weight=peso)
        for columna, texto in enumerate(("Deportista", "Cat.", "Aseguradora", "Póliza", "Vigencia", "Estado")):
            etiqueta_datos(cabecera, texto, COLORS["text_secondary"]).grid(
                row=0, column=columna, sticky="ew", padx=8, pady=4)
        if not filas:
            etiqueta_datos(self.tabla, "Sin pólizas registradas.",
                           COLORS["text_secondary"]).pack(anchor="w", pady=8)
        for fila in filas:
            linea = ctk.CTkFrame(self.tabla, fg_color="transparent", corner_radius=6)
            linea.pack(fill="x", pady=1)
            for columna, peso in enumerate((4, 2, 3, 3, 3, 2)):
                linea.grid_columnconfigure(columna, weight=peso)
            estado_fila = fila["estado"]
            dias = self._dias_para_vencer(str(fila["vigencia_fin"] or ""))
            if estado_fila == "VENCIDO" or (dias is not None and dias < 0):
                color_estado, texto_estado = COLORS["danger"], "VENCIDO"
            elif dias is not None and 0 <= dias <= DIAS_ALERTA:
                color_estado, texto_estado = COLORS["warning"], f"Vence en {dias} días"
            else:
                color_estado = COLORS["success"] if estado_fila == "VIGENTE" else None
                texto_estado = estado_fila
            vigencia = f"{fila['vigencia_inicio'] or '—'} → {fila['vigencia_fin'] or '—'}"
            valores = (fila["nombre"], fila["categoria"], fila["aseguradora"],
                       fila["numero_poliza"] or "—", vigencia, texto_estado)
            for columna, valor in enumerate(valores):
                color = color_estado if columna == 5 else None
                etiqueta_datos(linea, str(valor), color).grid(row=0, column=columna, sticky="ew", padx=8, pady=3)
            linea.bind("<Button-1>", lambda _e, f=fila: self._cargar(int(f["id"])))
            for hijo in linea.winfo_children():
                hijo.bind("<Button-1>", lambda _e, f=fila: self._cargar(int(f["id"])))

    def _cargar(self, seguro_id: int) -> None:
        fila = db.obtener_seguro(seguro_id)
        if fila is None:
            return
        self.seleccion_id = seguro_id
        self.menu_deportista.set(f"{fila['nombre']} · {fila['categoria']} · {fila['deporte']}")
        self.campo_aseguradora.delete(0, "end"); self.campo_aseguradora.insert(0, fila["aseguradora"])
        self.campo_poliza.delete(0, "end"); self.campo_poliza.insert(0, fila["numero_poliza"] or "")
        self.menu_tipo.set(fila["tipo_seguro"])
        self.menu_estado.set(fila["estado"])
        self.campo_inicio.delete(0, "end"); self.campo_inicio.insert(0, fila["vigencia_inicio"] or "")
        self.campo_fin.delete(0, "end"); self.campo_fin.insert(0, fila["vigencia_fin"] or "")
        self.campo_cobertura.delete(0, "end"); self.campo_cobertura.insert(0, fila["cobertura"] or "")
        self.texto_observaciones.delete("1.0", "end")
        self.texto_observaciones.insert("1.0", fila["observaciones"] or "")

    def _limpiar(self) -> None:
        self.seleccion_id = None
        self.campo_aseguradora.delete(0, "end")
        self.campo_poliza.delete(0, "end")
        self.menu_tipo.set("SALUD")
        self.menu_estado.set("VIGENTE")
        self.campo_inicio.delete(0, "end")
        self.campo_fin.delete(0, "end")
        self.campo_cobertura.delete(0, "end")
        self.texto_observaciones.delete("1.0", "end")

    # ------------------------------------------------------------------
    def _guardar(self) -> None:
        etiqueta = self.menu_deportista.get()
        deportista_id = next((i for i, t in self._opciones_deportistas if t == etiqueta), None)
        aseguradora = self.campo_aseguradora.get().strip()
        if deportista_id is None or not aseguradora:
            messagebox.showwarning("Campos obligatorios",
                                   "Seleccione el deportista e indique la aseguradora.")
            return
        datos = {
            "id": self.seleccion_id,
            "aseguradora": aseguradora,
            "tipo_seguro": self.menu_tipo.get(),
            "numero_poliza": self.campo_poliza.get().strip(),
            "cobertura": self.campo_cobertura.get().strip(),
            "vigencia_inicio": self.campo_inicio.get().strip(),
            "vigencia_fin": self.campo_fin.get().strip(),
            "estado": self.menu_estado.get(),
            "observaciones": self.texto_observaciones.get("1.0", "end").strip(),
        }
        db.upsert_seguro(deportista_id, datos)
        messagebox.showinfo("Póliza guardada",
                            f"La póliza de {aseguradora} quedó registrada correctamente.")
        self._limpiar()
        self._refrescar_tabla()

    def _exportar_excel(self) -> None:
        try:
            ruta = servicio_excel.generar_listado_seguros()
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Exportar", f"No se pudo generar el Excel:\n{exc}")
            return
        messagebox.showinfo("Excel generado", f"Listado de seguros generado en:\n{ruta}")

    def _exportar_pdf(self) -> None:
        try:
            ruta = servicio_excel.generar_listado_seguros()
            pdf = servicio_pdf.excel_a_pdf(ruta)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Exportar", f"No se pudo generar el PDF:\n{exc}")
            return
        messagebox.showinfo("PDF generado", f"PDF disponible en:\n{pdf}")
