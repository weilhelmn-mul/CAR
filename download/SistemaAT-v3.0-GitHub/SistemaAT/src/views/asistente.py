"""
=============================================================
 Sistema AT · Instituto Peruano del Deporte (IPD - DINADAF)
 views/asistente.py — Vista central del Asistente IA: redacta
 los campos narrativos de los formatos y los aplica al registro.
=============================================================
"""
from __future__ import annotations

from typing import Any

import customtkinter as ctk
from tkinter import messagebox

from src import database as db
from src.services import asistente_ia
from src.theme import COLORS, FONTS
from src.widgets import Card, PrimaryButton, SecondaryButton, SectionTitle, etiqueta_datos

FORMATOS: list[str] = ["AT-F3", "AT-F1", "AT-F8", "AT-F9", "ALIMENTACION"]
TITULOS_CAMPOS: dict[str, dict[str, str]] = {
    "AT-F3": {"objetivos": "Objetivos del periodo", "resultados": "Resultados",
              "evaluacion": "Evaluación técnica"},
    "AT-F1": {"eval_car": "Evaluación del CAR", "observaciones": "Observaciones"},
    "AT-F8": {"criterio_plan": "Criterio técnico del plan"},
    "AT-F9": {"obs_visita": "Observaciones de la visita", "opinion_presidente": "Opinión presidencial"},
    "ALIMENTACION": {"plan_alimenticio": "Plan alimenticio", "observaciones": "Observaciones"},
}


class AsistenteView(ctk.CTkFrame):
    """Generador de redacciones técnicas para los formatos del sistema."""

    def __init__(self, master: Any, app: Any) -> None:
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.formato_actual = "AT-F3"
        self.opciones: list[tuple[int, str]] = []   # (id, etiqueta)
        self.redaccion: dict[str, str] = {}
        self._construir()
        self._recargar_opciones()

    # ------------------------------------------------------------------
    def _construir(self) -> None:
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- Panel de selección ------------------------------------------
        panel = Card(self, width=360)
        panel.grid(row=0, column=0, sticky="ns", padx=(28, 10), pady=(24, 24))
        panel.pack_propagate(False)
        SectionTitle(panel, "✨ Asistente IA").pack(anchor="w", padx=18, pady=(16, 4))
        etiqueta_datos(panel,
                       "Redacta textos técnicos de las ciencias del deporte para "
                       "los formatos. Motor local sin internet (opcionalmente "
                       "conecta tu API en Data/config_ia.json).",
                       COLORS["text_secondary"]).pack(anchor="w", padx=18, pady=(0, 10))

        ctk.CTkLabel(panel, text="Formato", font=FONTS["small_bold"],
                     text_color=COLORS["text_secondary"], anchor="w").pack(fill="x", padx=18, pady=(4, 2))
        self.menu_formato = ctk.CTkOptionMenu(
            panel, values=FORMATOS, font=FONTS["body"],
            fg_color=COLORS["bg_main"], button_color=COLORS["accent"],
            button_hover_color=COLORS["accent_hover"], command=lambda _v: self._recargar_opciones())
        self.menu_formato.set("AT-F3")
        self.menu_formato.pack(fill="x", padx=18, pady=2)

        ctk.CTkLabel(panel, text="Registro a redactar", font=FONTS["small_bold"],
                     text_color=COLORS["text_secondary"], anchor="w").pack(fill="x", padx=18, pady=(8, 2))
        self.menu_registro = ctk.CTkOptionMenu(
            panel, values=["— sin registros —"], font=FONTS["body"],
            fg_color=COLORS["bg_main"], button_color=COLORS["accent"],
            button_hover_color=COLORS["accent_hover"])
        self.menu_registro.pack(fill="x", padx=18, pady=2)

        PrimaryButton(panel, "✨ Redactar con IA", self._redactar).pack(fill="x", padx=18, pady=(14, 4))
        SecondaryButton(panel, "🔄 Recargar registros", self._recargar_opciones).pack(fill="x", padx=18, pady=4)
        SecondaryButton(panel, "✅ Aplicar al formato", self._aplicar).pack(fill="x", padx=18, pady=4)
        SecondaryButton(panel, "📋 Copiar todo", self._copiar_todo).pack(fill="x", padx=18, pady=(4, 16))

        # --- Área de resultados ------------------------------------------
        self.resultado = ctk.CTkScrollableFrame(self, fg_color=COLORS["card"],
                                                corner_radius=12)
        self.resultado.grid(row=0, column=1, sticky="nsew", padx=(0, 28), pady=(24, 24))
        self._mensaje_bienvenida()

    # ------------------------------------------------------------------
    def _mensaje_bienvenida(self) -> None:
        for widget in self.resultado.winfo_children():
            widget.destroy()
        etiqueta_datos(
            self.resultado,
            "1) Elige el formato y el registro.\n"
            "2) Pulsa «Redactar con IA» para generar los textos técnicos.\n"
            "3) Revisa, copia o aplica los textos al formato.\n\n"
            "La redacción usa datos reales del sistema (deporte, categoría, "
            "porcentajes, resultados y SISDENA) y nunca inventa cifras.",
            COLORS["text_secondary"],
        ).pack(anchor="w", padx=20, pady=20)

    def _recargar_opciones(self) -> None:
        """Carga las opciones del formato elegido (registro → etiqueta)."""
        self.formato_actual = self.menu_formato.get()
        if self.formato_actual == "AT-F3":
            self.opciones = [(int(r["id"]), f"{r['nombre']} · {r['periodo']}")
                             for r in db.listar_registros()]
        elif self.formato_actual == "AT-F1":
            self.opciones = [(int(c["id"]), f"{c['car'] or 'CAR'} · {c['periodo']}")
                             for c in db.listar_consolidados()]
        elif self.formato_actual == "AT-F8":
            self.opciones = [(int(p["id"]), f"{p['jut_nombre']} · {p['periodo']}")
                             for p in db.listar_planes()]
        elif self.formato_actual == "AT-F9":
            self.opciones = [(int(e["id"]), f"{e['jut_nombre']} · {e['periodo']}")
                             for e in db.listar_evaluaciones()]
        else:
            self.opciones = [(int(a["id"]), f"{a['nombre']} · {a['periodo']}")
                             for a in db.listar_alimentacion()]

        valores = [etiqueta for _i, etiqueta in self.opciones] or ["— sin registros —"]
        self.menu_registro.configure(values=valores)
        self.menu_registro.set(valores[0])

    def _id_seleccionado(self) -> int | None:
        etiqueta = self.menu_registro.get()
        for identificador, texto in self.opciones:
            if texto == etiqueta:
                return identificador
        return None

    # ------------------------------------------------------------------
    def _redactar(self) -> None:
        """Genera la redacción técnica del registro seleccionado."""
        registro_id = self._id_seleccionado()
        if registro_id is None:
            messagebox.showinfo(
                "Sin registros",
                f"Aún no hay registros de {self.formato_actual}. Crea primero el "
                "registro en su módulo y vuelve al asistente.")
            return
        try:
            self.redaccion = asistente_ia.redactar(self.formato_actual, registro_id)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Asistente IA", f"No se pudo redactar:\n{exc}")
            return
        self._mostrar_redaccion()

    def _mostrar_redaccion(self) -> None:
        for widget in self.resultado.winfo_children():
            widget.destroy()
        titulos = TITULOS_CAMPOS[self.formato_actual]
        for campo, titulo in titulos.items():
            texto = self.redaccion.get(campo, "")
            tarjeta = ctk.CTkFrame(self.resultado, fg_color=COLORS["bg_main"], corner_radius=8)
            tarjeta.pack(fill="x", padx=16, pady=(14, 6))
            cabecera = ctk.CTkFrame(tarjeta, fg_color="transparent")
            cabecera.pack(fill="x", padx=12, pady=(8, 2))
            etiqueta_datos(cabecera, titulo, COLORS["accent"]).pack(side="left")
            ctk.CTkButton(cabecera, text="📋 Copiar", width=90, height=24,
                          font=FONTS["small_bold"], fg_color=COLORS["accent"],
                          hover_color=COLORS["accent_hover"],
                          command=lambda t=texto: self._copiar(t)).pack(side="right")
            cuadro = ctk.CTkTextbox(tarjeta, height=150, font=FONTS["body"], wrap="word")
            cuadro.pack(fill="x", padx=12, pady=(0, 10))
            cuadro.insert("1.0", texto)
            cuadro.configure(state="disabled")

    # ------------------------------------------------------------------
    def _copiar(self, texto: str) -> None:
        self.clipboard_clear()
        self.clipboard_append(texto)
        etiqueta_datos(self.resultado, "✓ Copiado al portapapeles",
                       COLORS["success"]).pack(anchor="w", padx=20, pady=(0, 6))

    def _copiar_todo(self) -> None:
        if not self.redaccion:
            messagebox.showinfo("Nada que copiar", "Primero redacta con el asistente.")
            return
        titulos = TITULOS_CAMPOS[self.formato_actual]
        bloques = [f"== {titulos[campo]} ==\n{texto}"
                   for campo, texto in self.redaccion.items() if campo in titulos]
        self._copiar("\n\n".join(bloques))

    def _aplicar(self) -> None:
        """Escribe los textos generados en los campos del formato."""
        if not self.redaccion:
            messagebox.showinfo("Sin redacción", "Primero pulsa «Redactar con IA».")
            return
        registro_id = self._id_seleccionado()
        if registro_id is None:
            return
        if not messagebox.askyesno(
                "Aplicar textos",
                "Se escribirán los textos generados en el registro seleccionado "
                "(no se tocan las cifras). ¿Continuar?"):
            return
        try:
            if self.formato_actual == "AT-F3":
                db.actualizar_narrativa_f3(registro_id, **self.redaccion)
            elif self.formato_actual == "AT-F1":
                db.actualizar_narrativa_f1(registro_id, **self.redaccion)
            elif self.formato_actual == "AT-F9":
                db.actualizar_narrativa_f9(registro_id, **self.redaccion)
            elif self.formato_actual == "ALIMENTACION":
                if "plan_alimenticio" in self.redaccion:
                    db.actualizar_plan_alimenticio(registro_id, self.redaccion["plan_alimenticio"])
            else:  # AT-F8: criterio orientativo, solo copiable
                messagebox.showinfo(
                    "Criterio del plan",
                    "El criterio técnico es orientativo: cópialo en las "
                    "observaciones o en la reunión de planificación del JUT.")
                return
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Asistente IA", f"No se pudo aplicar:\n{exc}")
            return
        messagebox.showinfo("Textos aplicados",
                            "Los textos del asistente quedaron guardados en el registro.")
