"""
=============================================================
 Sistema AT · Instituto Peruano del Deporte (IPD - DINADAF)
 views/expediente.py — Expediente completo del atleta: datos
 personales, categoría, sexo, historial y mejores resultados
 por mes, bimestre, trimestre y año. Exportable a Excel/PDF.
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
from src.widgets import Card, PrimaryButton, SecondaryButton, SectionTitle, etiqueta_datos

MESES_NOMBRE = {"01": "Enero", "02": "Febrero", "03": "Marzo", "04": "Abril",
                "05": "Mayo", "06": "Junio", "07": "Julio", "08": "Agosto",
                "09": "Setiembre", "10": "Octubre", "11": "Noviembre", "12": "Diciembre"}


class ExpedienteView(ctk.CTkFrame):
    """Ficha integral del deportista con su historial competitivo."""

    def __init__(self, master: Any, app: Any) -> None:
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.deportista_id: int | None = None
        self._construir()
        self._refrescar_selector()

    # ------------------------------------------------------------------
    def _construir(self) -> None:
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # --- Cabecera con selector y exportación --------------------------
        cabecera = ctk.CTkFrame(self, fg_color="transparent")
        cabecera.grid(row=0, column=0, sticky="ew", padx=28, pady=(24, 6))
        ctk.CTkLabel(cabecera, text="Expediente del atleta", font=FONTS["h2"],
                     text_color=COLORS["text_primary"]).pack(side="left")
        acciones = ctk.CTkFrame(cabecera, fg_color="transparent")
        acciones.pack(side="right")
        PrimaryButton(acciones, "📊 Exportar Excel", self._exportar_excel, width=170).pack(side="left", padx=4)
        SecondaryButton(acciones, "📄 Exportar PDF", self._exportar_pdf, width=150).pack(side="left", padx=4)

        selector = ctk.CTkFrame(self, fg_color="transparent")
        selector.grid(row=1, column=0, sticky="ew", padx=28, pady=(0, 8))
        ctk.CTkLabel(selector, text="Deportista:", font=FONTS["small_bold"],
                     text_color=COLORS["text_secondary"]).pack(side="left", padx=(0, 8))
        self.menu_deportista = ctk.CTkOptionMenu(
            selector, values=["— sin deportistas —"], width=420, font=FONTS["body"],
            fg_color=COLORS["bg_main"], button_color=COLORS["accent"],
            button_hover_color=COLORS["accent_hover"], command=lambda _v: self._mostrar())
        self.menu_deportista.pack(side="left")

        # --- Cuerpo con scroll --------------------------------------------
        self.cuerpo = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.cuerpo.grid(row=2, column=0, sticky="nsew", padx=28, pady=(0, 24))
        self.cuerpo.grid_columnconfigure(0, weight=1)

    # ------------------------------------------------------------------
    def _refrescar_selector(self) -> None:
        opciones = db.opciones_deportistas()
        valores = [texto for _i, texto in opciones] or ["— sin deportistas —"]
        self._opciones = opciones
        self.menu_deportista.configure(values=valores)
        self.menu_deportista.set(valores[0])
        self._mostrar()

    def _id_seleccionado(self) -> int | None:
        etiqueta = self.menu_deportista.get()
        for identificador, texto in getattr(self, "_opciones", []):
            if texto == etiqueta:
                return identificador
        return None

    # ------------------------------------------------------------------
    def _mostrar(self) -> None:
        """Redibuja el expediente del deportista seleccionado."""
        for widget in self.cuerpo.winfo_children():
            widget.destroy()
        self.deportista_id = self._id_seleccionado()
        if self.deportista_id is None:
            etiqueta_datos(self.cuerpo, "Registra deportistas para ver su expediente.",
                           COLORS["text_secondary"]).pack(anchor="w", pady=20)
            return
        deportista = db.obtener_deportista(self.deportista_id)
        if deportista is None:
            return

        # --- Datos personales ----------------------------------------------
        tarjeta_datos = Card(self.cuerpo)
        tarjeta_datos.pack(fill="x", pady=(0, 12))
        SectionTitle(tarjeta_datos, "Datos personales y deportivos").pack(anchor="w", padx=18, pady=(14, 6))
        cuadricula = ctk.CTkFrame(tarjeta_datos, fg_color="transparent")
        cuadricula.pack(fill="x", padx=18, pady=(0, 14))
        for columna in range(4):
            cuadricula.grid_columnconfigure(columna, weight=1 if columna % 2 else 0, uniform="datos")
        datos = [
            ("Documento", deportista["documento"] or "—"),
            ("Categoría que compite", deportista["categoria"]),
            ("Sexo", {"D": "Damas", "V": "Varones"}.get(deportista["sexo"], "—")),
            ("Deporte", deportista["deporte"]),
            ("CAR", deportista["car"] or "—"),
            ("Región", deportista["region"] or "—"),
            ("Entrenador", deportista["entrenador"] or "—"),
            ("Estado", "Activo" if deportista["activo"] else "Inactivo"),
        ]
        for indice, (titulo, valor) in enumerate(datos):
            fila, columna = divmod(indice, 4)
            bloque = ctk.CTkFrame(cuadricula, fg_color="transparent")
            bloque.grid(row=fila, column=columna, sticky="ew", padx=6, pady=4)
            etiqueta_datos(bloque, titulo.upper(), COLORS["text_secondary"]).pack(anchor="w")
            color = COLORS["success"] if titulo == "Estado" and deportista["activo"] else (
                COLORS["danger"] if titulo == "Estado" else COLORS["text_primary"])
            etiqueta_datos(bloque, str(valor), color).pack(anchor="w")

        # --- Registro rápido de resultado ---------------------------------
        tarjeta_form = Card(self.cuerpo)
        tarjeta_form.pack(fill="x", pady=(0, 12))
        SectionTitle(tarjeta_form, "Registrar resultado deportivo").pack(anchor="w", padx=18, pady=(14, 6))
        formulario = ctk.CTkFrame(tarjeta_form, fg_color="transparent")
        formulario.pack(fill="x", padx=18, pady=(0, 8))
        for columna in range(4):
            formulario.grid_columnconfigure(columna, weight=1)
        campos = (("Fecha (YYYY-MM-DD) *", "2026-11-20"), ("Competencia *", "Campeonato Nacional"),
                  ("Lugar", "Lima"), ("Prueba", "5000 m planos"))
        self._entradas_resultado: dict[str, ctk.CTkEntry] = {}
        for indice, (titulo, placeholder) in enumerate(campos):
            ctk.CTkLabel(formulario, text=titulo, font=FONTS["small_bold"],
                         text_color=COLORS["text_secondary"], anchor="w").grid(
                row=0, column=indice, sticky="ew", padx=3)
            entrada = ctk.CTkEntry(formulario, placeholder_text=placeholder, font=FONTS["body"],
                                   fg_color=COLORS["bg_main"], border_color=COLORS["border"])
            entrada.grid(row=1, column=indice, sticky="ew", padx=3)
            self._entradas_resultado[titulo.split(" ")[0]] = entrada
        fila_baja = ctk.CTkFrame(formulario, fg_color="transparent")
        fila_baja.grid(row=2, column=0, columnspan=4, sticky="ew", pady=(6, 0))
        for columna in range(4):
            fila_baja.grid_columnconfigure(columna, weight=1)
        ctk.CTkLabel(fila_baja, text="Marca", font=FONTS["small_bold"],
                     text_color=COLORS["text_secondary"], anchor="w").grid(row=0, column=0, sticky="ew", padx=3)
        entrada_marca = ctk.CTkEntry(fila_baja, placeholder_text="15:42.30", font=FONTS["body"],
                                     fg_color=COLORS["bg_main"], border_color=COLORS["border"])
        entrada_marca.grid(row=1, column=0, sticky="ew", padx=3)
        self._entradas_resultado["Marca"] = entrada_marca
        ctk.CTkLabel(fila_baja, text="Puesto (1-8)", font=FONTS["small_bold"],
                     text_color=COLORS["text_secondary"], anchor="w").grid(row=0, column=1, sticky="ew", padx=3)
        entrada_puesto = ctk.CTkEntry(fila_baja, placeholder_text="1", font=FONTS["body"],
                                      fg_color=COLORS["bg_main"], border_color=COLORS["border"])
        entrada_puesto.grid(row=1, column=1, sticky="ew", padx=3)
        self._entradas_resultado["Puesto"] = entrada_puesto
        ctk.CTkLabel(fila_baja, text="Medalla", font=FONTS["small_bold"],
                     text_color=COLORS["text_secondary"], anchor="w").grid(row=0, column=2, sticky="ew", padx=3)
        menu_medalla = ctk.CTkOptionMenu(fila_baja, values=["—", "ORO", "PLATA", "BRONCE"],
                                         font=FONTS["body"], fg_color=COLORS["bg_main"],
                                         button_color=COLORS["accent"],
                                         button_hover_color=COLORS["accent_hover"])
        menu_medalla.set("—")
        menu_medalla.grid(row=1, column=2, sticky="ew", padx=3)
        self._menu_medalla = menu_medalla
        PrimaryButton(fila_baja, "➕ Agregar", self._agregar_resultado, height=28).grid(
            row=1, column=3, sticky="ew", padx=3, pady=(14, 0))

        # --- Mejores resultados por período ---------------------------------
        mejores = db.resumen_mejores_por_periodo(self.deportista_id)
        secciones = [
            ("mes", "Mejores resultados por MES"),
            ("bimestre", "Mejores resultados por BIMESTRE"),
            ("trimestre", "Mejores resultados por TRIMESTRE"),
            ("anual", "Mejores resultados por AÑO"),
        ]
        for tipo, titulo in secciones:
            tarjeta = Card(self.cuerpo)
            tarjeta.pack(fill="x", pady=(0, 12))
            SectionTitle(tarjeta, titulo).pack(anchor="w", padx=18, pady=(14, 6))
            bloque = mejores.get(tipo, {})
            contenedor = ctk.CTkFrame(tarjeta, fg_color="transparent")
            contenedor.pack(fill="x", padx=18, pady=(0, 12))
            for columna, peso in enumerate((3, 4, 4, 2, 2, 2)):
                contenedor.grid_columnconfigure(columna, weight=peso)
            if not bloque:
                etiqueta_datos(contenedor, "Sin resultados registrados en este nivel.",
                               COLORS["text_secondary"]).grid(row=0, column=0, sticky="w", pady=4)
                continue
            for columna, texto in enumerate((titulo.split("por ")[1].capitalize(), "Competencia",
                                             "Prueba", "Marca", "Puesto", "Medalla")):
                etiqueta_datos(contenedor, texto, COLORS["text_secondary"]).grid(
                    row=0, column=columna, sticky="ew", padx=6, pady=2)
            for numero, (etiqueta, mejor) in enumerate(sorted(bloque.items()), start=1):
                puesto = f"{mejor['posicion']}.°" if mejor["posicion"] else "—"
                color_puesto = COLORS["success"] if mejor["posicion"] and int(mejor["posicion"]) <= 3 else None
                valores = (self._etiqueta_legible(tipo, etiqueta), mejor["competencia"],
                           mejor["prueba"] or "—", mejor["marca"] or "—", puesto,
                           mejor["medalla"] or "—")
                for columna, valor in enumerate(valores):
                    color = color_puesto if columna == 4 else None
                    etiqueta_datos(contenedor, str(valor), color).grid(
                        row=numero, column=columna, sticky="ew", padx=6, pady=2)

        # --- Historial completo ----------------------------------------------
        tarjeta_historial = Card(self.cuerpo)
        tarjeta_historial.pack(fill="x", pady=(0, 12))
        SectionTitle(tarjeta_historial, "Historial completo de resultados").pack(anchor="w", padx=18, pady=(14, 6))
        historial = db.resultados_de(self.deportista_id)
        contenedor_h = ctk.CTkFrame(tarjeta_historial, fg_color="transparent")
        contenedor_h.pack(fill="x", padx=18, pady=(0, 12))
        for columna, peso in enumerate((2, 4, 3, 3, 2, 1, 0)):
            contenedor_h.grid_columnconfigure(columna, weight=peso)
        for columna, texto in enumerate(("Fecha", "Competencia", "Lugar", "Prueba", "Marca", "Puesto", "")):
            etiqueta_datos(contenedor_h, texto, COLORS["text_secondary"]).grid(
                row=0, column=columna, sticky="ew", padx=6, pady=2)
        if not historial:
            etiqueta_datos(contenedor_h, "Sin resultados registrados.",
                           COLORS["text_secondary"]).grid(row=1, column=0, sticky="w", pady=4)
        for numero, resultado in enumerate(historial, start=1):
            valores = (resultado["fecha"], resultado["competencia"], resultado["lugar"] or "—",
                       resultado["prueba"] or "—", resultado["marca"] or "—",
                       f"{resultado['posicion']}.°" if resultado["posicion"] else "—")
            for columna, valor in enumerate(valores):
                etiqueta_datos(contenedor_h, str(valor)).grid(
                    row=numero, column=columna, sticky="ew", padx=6, pady=2)
            ctk.CTkButton(contenedor_h, text="✕", width=28, height=22,
                          font=FONTS["small_bold"], fg_color=COLORS["card"],
                          hover_color=COLORS["bg_main"], border_width=1,
                          border_color=COLORS["border"], text_color=COLORS["danger"],
                          command=lambda r=int(resultado["id"]): self._eliminar_resultado(r)).grid(
                row=numero, column=6, sticky="e", padx=6, pady=2)

    # ------------------------------------------------------------------
    def _agregar_resultado(self) -> None:
        """Valida y registra el resultado ingresado en el formulario."""
        if self.deportista_id is None:
            messagebox.showinfo("Seleccione un deportista", "Elige un deportista del menú superior.")
            return
        fecha = self._entradas_resultado["Fecha"].get().strip()
        competencia = self._entradas_resultado["Competencia"].get().strip()
        if not fecha or not competencia:
            messagebox.showwarning("Campos obligatorios", "La fecha y la competencia son obligatorias.")
            return
        puesto = self._entradas_resultado["Puesto"].get().strip()
        try:
            posicion = int(puesto) if puesto else None
            if posicion is not None and posicion <= 0:
                raise ValueError
        except ValueError:
            messagebox.showwarning("Puesto inválido", "El puesto debe ser un número entero mayor a 0.")
            return
        medalla = self._menu_medalla.get()
        db.agregar_resultado({
            "deportista_id": self.deportista_id,
            "fecha": fecha,
            "competencia": competencia,
            "lugar": self._entradas_resultado["Lugar"].get().strip(),
            "prueba": self._entradas_resultado["Prueba"].get().strip(),
            "marca": self._entradas_resultado["Marca"].get().strip(),
            "posicion": posicion,
            "medalla": "" if medalla == "—" else medalla,
        })
        for entrada in self._entradas_resultado.values():
            entrada.delete(0, "end")
        self._menu_medalla.set("—")
        self._mostrar()

    def _eliminar_resultado(self, resultado_id: int) -> None:
        """Elimina un resultado mal ingresado tras confirmación."""
        if messagebox.askyesno("Eliminar resultado",
                               "¿Eliminar este resultado del historial? Esta acción no se puede deshacer."):
            db.eliminar_resultado(resultado_id)
            self._mostrar()

    # ------------------------------------------------------------------
    @staticmethod
    def _etiqueta_legible(tipo: str, etiqueta: str) -> str:
        """Convierte '2026-11' / '2026 · B3' / '2026' en texto legible."""
        if tipo == "mes":
            anio, mes = etiqueta.split("-")
            return f"{MESES_NOMBRE.get(mes, mes)} {anio}"
        if tipo in ("bimestre", "trimestre"):
            anio, bloque = etiqueta.split("·")
            return f"{bloque.strip()} {anio.strip()}"
        return etiqueta

    # ------------------------------------------------------------------
    def _exportar_excel(self) -> None:
        if self.deportista_id is None:
            messagebox.showinfo("Seleccione un deportista", "Elige un deportista del menú superior.")
            return
        try:
            ruta = servicio_excel.generar_expediente(self.deportista_id)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Exportar", f"No se pudo generar el expediente:\n{exc}")
            return
        messagebox.showinfo("Excel generado", f"Expediente generado en:\n{ruta}")

    def _exportar_pdf(self) -> None:
        if self.deportista_id is None:
            messagebox.showinfo("Seleccione un deportista", "Elige un deportista del menú superior.")
            return
        try:
            ruta = servicio_excel.generar_expediente(self.deportista_id)
            pdf = servicio_pdf.excel_a_pdf(ruta)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Exportar", f"No se pudo generar el PDF:\n{exc}")
            return
        messagebox.showinfo("PDF generado", f"PDF disponible en:\n{pdf}")
