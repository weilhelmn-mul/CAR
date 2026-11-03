# -*- coding: utf-8 -*-
"""
src/widgets.py
==============
Componentes visuales reutilizables del Sistema AT:

    * Card           → tarjeta blanca con borde y corner_radius (diseño oficial).
    * StatCard       → tarjeta de indicador con icono, título y valor grande.
    * PrimaryButton  → botón primario índigo con hover institucional.
    * FormField      → etiqueta + campo de entrada con .get() y .set().
    * SectionTitle   → título de sección con tipografía h3.
    * TextboxCard    → tarjeta con título y cuadro de texto multilínea.
    * TablaFrame     → tabla sencilla con encabezado fijo y filas agregables.
    * abrir_ruta()   → abre un archivo/carpeta con la app predeterminada.
    * centrar_ventana() → centra un Toplevel en pantalla.
"""
from __future__ import annotations

import logging
import os
import subprocess
import sys
from tkinter import messagebox

import customtkinter as ctk

from src.theme import COLORS, FONTS

log = logging.getLogger(__name__)


def peso_entero(peso: float) -> int:
    """Convierte un peso relativo (puede ser decimal) a entero para Tk grid."""
    return max(1, int(round(float(peso) * 10)))


def confirmar_apertura(ruta) -> None:
    """Informa que un documento se generó y ofrece abrir la carpeta que lo contiene."""
    if messagebox.askyesno(
        "Documento generado", f"Documento generado en:\n{ruta}\n\n¿Desea abrir la carpeta?"
    ):
        abrir_ruta(ruta)


# ---------------------------------------------------------------------------
# Contenedores
# ---------------------------------------------------------------------------
class Card(ctk.CTkFrame):
    """Tarjeta blanca con esquinas redondeadas y borde claro (diseño institucional)."""

    def __init__(self, master, **kwargs):
        super().__init__(
            master,
            fg_color=COLORS["card"],
            corner_radius=14,
            border_width=1,
            border_color=COLORS["border"],
            **kwargs,
        )


class StatCard(Card):
    """Tarjeta de indicador: icono + valor grande + título."""

    def __init__(self, master, icono: str, titulo: str, valor, color: str | None = None):
        super().__init__(master)
        self.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self, text=icono, font=FONTS["h2"]).grid(
            row=0, column=0, sticky="w", padx=18, pady=(14, 0)
        )
        self.valor_lbl = ctk.CTkLabel(
            self, text=str(valor), font=FONTS["h1"],
            text_color=color or COLORS["text_primary"], anchor="w",
        )
        self.valor_lbl.grid(row=1, column=0, sticky="ew", padx=18)
        ctk.CTkLabel(
            self, text=titulo, font=FONTS["small"], text_color=COLORS["text_secondary"], anchor="w"
        ).grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 14))

    def set_valor(self, valor) -> None:
        self.valor_lbl.configure(text=str(valor))


class SectionTitle(ctk.CTkLabel):
    """Título de sección con tipografía h3 alineado a la izquierda."""

    def __init__(self, master, texto: str):
        super().__init__(
            master, text=texto, font=FONTS["h3"], text_color=COLORS["text_primary"], anchor="w"
        )


# ---------------------------------------------------------------------------
# Botones
# ---------------------------------------------------------------------------
class PrimaryButton(ctk.CTkButton):
    """Botón primario índigo con hover institucional."""

    def __init__(self, master, **kwargs):
        kwargs.setdefault("fg_color", COLORS["accent"])
        kwargs.setdefault("hover_color", COLORS["accent_hover"])
        kwargs.setdefault("text_color", COLORS["text_light"])
        kwargs.setdefault("font", FONTS["button"])
        kwargs.setdefault("corner_radius", 8)
        kwargs.setdefault("height", 34)
        super().__init__(master, **kwargs)


# ---------------------------------------------------------------------------
# Formularios
# ---------------------------------------------------------------------------
class FormField(ctk.CTkFrame):
    """Etiqueta + campo de entrada con métodos .get() y .set(valor)."""

    def __init__(self, master, etiqueta: str, placeholder: str = "", ancho: int = 260):
        super().__init__(master, fg_color="transparent")
        ctk.CTkLabel(self, text=etiqueta, font=FONTS["small_bold"], anchor="w").pack(fill="x")
        self.entry = ctk.CTkEntry(
            self, width=ancho, placeholder_text=placeholder, font=FONTS["body"], height=32
        )
        self.entry.pack(fill="x", pady=(2, 0))

    def get(self) -> str:
        return self.entry.get().strip()

    def set(self, valor) -> None:
        self.entry.delete(0, "end")
        if valor not in (None, ""):
            self.entry.insert(0, str(valor))


class TextboxCard(Card):
    """Tarjeta con título de sección y cuadro de texto multilínea (.get/.set)."""

    def __init__(self, master, titulo: str, altura: int = 140, nota: str | None = None):
        super().__init__(master)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1 if nota is None else 2, weight=1)
        SectionTitle(self, titulo).grid(row=0, column=0, sticky="ew", padx=14, pady=(10, 4))
        if nota is not None:
            ctk.CTkLabel(
                self, text=nota, font=FONTS["small"], text_color=COLORS["text_secondary"],
                anchor="w", justify="left", wraplength=900,
            ).grid(row=1, column=0, sticky="ew", padx=14)
        self.textbox = ctk.CTkTextbox(self, height=altura, font=FONTS["body"], wrap="word")
        self.textbox.grid(
            row=1 if nota is None else 2, column=0, sticky="nsew", padx=14, pady=(0, 12)
        )

    def get(self) -> str:
        return self.textbox.get("1.0", "end").strip()

    def set(self, texto) -> None:
        self.textbox.delete("1.0", "end")
        if texto:
            self.textbox.insert("1.0", str(texto))


# ---------------------------------------------------------------------------
# Tablas
# ---------------------------------------------------------------------------
class TablaFrame(ctk.CTkScrollableFrame):
    """Tabla sencilla: encabezado fijo + filas agregables con grid interno.

    `pesos` define el peso relativo de cada columna (como grid_columnconfigure).
    `nueva_fila()` devuelve un frame con las columnas ya configuradas; la vista
    coloca en él sus labels/entradas/botones con .grid(row=0, column=i).
    """

    def __init__(self, master, columnas: list[str], pesos: list[float], altura: int = 320):
        super().__init__(master, height=altura, fg_color=COLORS["card"], corner_radius=10)
        self.pesos = list(pesos)
        self._fila_actual = 1
        for i, _ in enumerate(self.pesos):
            self.grid_columnconfigure(i, weight=peso_entero(self.pesos[i]))
        for i, texto in enumerate(columnas):
            ctk.CTkLabel(
                self, text=texto, font=FONTS["small_bold"], text_color=COLORS["text_light"],
                fg_color=COLORS["sidebar"], corner_radius=6, height=30, anchor="w",
            ).grid(row=0, column=i, sticky="ew", padx=2, pady=(2, 6))

    def nueva_fila(self, zebra: bool = False) -> ctk.CTkFrame:
        """Agrega y devuelve el contenedor de una fila de datos."""
        fila = ctk.CTkFrame(
            self, fg_color="#f8fafc" if zebra else "transparent", corner_radius=6
        )
        fila.grid(row=self._fila_actual, column=0, columnspan=len(self.pesos), sticky="ew", pady=1)
        for i, _ in enumerate(self.pesos):
            fila.grid_columnconfigure(i, weight=peso_entero(self.pesos[i]))
        self._fila_actual += 1
        return fila

    def limpiar(self) -> None:
        """Elimina las filas de datos conservando el encabezado."""
        for hijo in self.winfo_children():
            if isinstance(hijo, ctk.CTkFrame):
                hijo.destroy()
        self._fila_actual = 1


# ---------------------------------------------------------------------------
# Utilidades de sistema
# ---------------------------------------------------------------------------
def abrir_ruta(ruta) -> None:
    """Abre un archivo o carpeta con la aplicación predeterminada del sistema."""
    destino = str(ruta)
    try:
        if sys.platform == "win32":
            os.startfile(destino)  # type: ignore[attr-defined]  # noqa: S606
        elif sys.platform == "darwin":
            subprocess.Popen(["open", destino])  # noqa: S603
        else:
            subprocess.Popen(["xdg-open", destino])  # noqa: S603
    except Exception:
        log.exception("No se pudo abrir la ruta: %s", destino)


def centrar_ventana(ventana: ctk.CTkToplevel, ancho: int, alto: int) -> None:
    """Centra una ventana emergente en la pantalla y fija su tamaño."""
    ventana.update_idletasks()
    x = max(0, (ventana.winfo_screenwidth() - ancho) // 2)
    y = max(0, (ventana.winfo_screenheight() - alto) // 3)
    ventana.geometry(f"{ancho}x{alto}+{x}+{y}")
