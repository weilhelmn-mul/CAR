"""
=============================================================
 Sistema AT · Instituto Peruano del Deporte (IPD - DINADAF)
 widgets.py — Componentes visuales reutilizables (Cards, botones,
 campos de formulario y títulos de sección) con el tema oficial.
=============================================================
"""
from __future__ import annotations

from typing import Any

import customtkinter as ctk

from src.theme import COLORS, FONTS


class Card(ctk.CTkFrame):
    """Tarjeta blanca con borde suave que agrupa contenido."""

    def __init__(self, master: Any, **kwargs: Any) -> None:
        super().__init__(
            master,
            fg_color=COLORS["card"],
            corner_radius=12,
            border_width=1,
            border_color=COLORS["border"],
            **kwargs,
        )


class StatCard(Card):
    """Tarjeta de indicador: valor grande + subtítulo descriptivo."""

    def __init__(self, master: Any, titulo: str, valor: str = "0", color: str | None = None) -> None:
        super().__init__(master)
        self.grid_columnconfigure(0, weight=1)
        self._etiqueta_valor = ctk.CTkLabel(
            self, text=valor, font=FONTS["h1"],
            text_color=color or COLORS["accent"], anchor="w",
        )
        self._etiqueta_valor.grid(row=0, column=0, sticky="ew", padx=18, pady=(16, 2))
        self._etiqueta_titulo = ctk.CTkLabel(
            self, text=titulo, font=FONTS["small"],
            text_color=COLORS["text_secondary"], anchor="w", justify="left",
        )
        self._etiqueta_titulo.grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 14))

    def set_valor(self, valor: str) -> None:
        """Actualiza el número mostrado por el indicador."""
        self._etiqueta_valor.configure(text=valor)


class PrimaryButton(ctk.CTkButton):
    """Botón principal con el acento indigo del sistema."""

    def __init__(self, master: Any, texto: str, comando: Any, color: str | None = None,
                 hover: str | None = None, **kwargs: Any) -> None:
        super().__init__(
            master,
            text=texto,
            command=comando,
            font=FONTS["button"],
            fg_color=color or COLORS["accent"],
            hover_color=hover or COLORS["accent_hover"],
            text_color=COLORS["text_light"],
            corner_radius=8,
            **kwargs,
        )


class SecondaryButton(ctk.CTkButton):
    """Botón secundario (borde gris, texto oscuro) para acciones menos frecuentes."""

    def __init__(self, master: Any, texto: str, comando: Any, **kwargs: Any) -> None:
        super().__init__(
            master,
            text=texto,
            command=comando,
            font=FONTS["small_bold"],
            fg_color=COLORS["card"],
            hover_color=COLORS["bg_main"],
            border_width=1,
            border_color=COLORS["border"],
            text_color=COLORS["text_primary"],
            corner_radius=8,
            **kwargs,
        )


class DangerButton(ctk.CTkButton):
    """Botón de acción destructiva (rojo)."""

    def __init__(self, master: Any, texto: str, comando: Any, **kwargs: Any) -> None:
        super().__init__(
            master,
            text=texto,
            command=comando,
            font=FONTS["small_bold"],
            fg_color=COLORS["danger"],
            hover_color="#dc2626",
            text_color=COLORS["text_light"],
            corner_radius=8,
            **kwargs,
        )


class FormField(ctk.CTkFrame):
    """Campo de formulario: etiqueta arriba + entrada de texto (con .get()/.set())."""

    def __init__(self, master: Any, etiqueta: str, placeholder: str = "", ancho: int = 220,
                 solo_lectura: bool = False) -> None:
        super().__init__(master, fg_color="transparent")
        self.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            self, text=etiqueta, font=FONTS["small_bold"],
            text_color=COLORS["text_secondary"], anchor="w",
        ).grid(row=0, column=0, sticky="ew", pady=(0, 3))
        self._entrada = ctk.CTkEntry(
            self, placeholder_text=placeholder, width=ancho, font=FONTS["body"],
            fg_color=COLORS["bg_main"], border_color=COLORS["border"],
        )
        self._entrada.grid(row=1, column=0, sticky="ew")
        if solo_lectura:
            self._entrada.configure(state="disabled")

    def get(self) -> str:
        """Devuelve el texto ingresado (sin espacios extremos)."""
        return self._entrada.get().strip()

    def set(self, valor: str) -> None:
        """Escribe texto en el campo (habilitándolo temporalmente si es solo lectura)."""
        estado = self._entrada.cget("state")
        if estado == "disabled":
            self._entrada.configure(state="normal")
        self._entrada.delete(0, "end")
        self._entrada.insert(0, valor)
        if estado == "disabled":
            self._entrada.configure(state="disabled")


class SectionTitle(ctk.CTkLabel):
    """Título de sección dentro de una vista."""

    def __init__(self, master: Any, texto: str, nivel: str = "h3") -> None:
        super().__init__(
            master, text=texto, font=FONTS.get(nivel, FONTS["h3"]),
            text_color=COLORS["text_primary"], anchor="w",
        )


def etiqueta_datos(master: Any, texto: str, color: str | None = None) -> ctk.CTkLabel:
    """Etiqueta pequeña para tablas/listados."""
    return ctk.CTkLabel(
        master, text=texto, font=FONTS["small"],
        text_color=color or COLORS["text_primary"], anchor="w",
    )
