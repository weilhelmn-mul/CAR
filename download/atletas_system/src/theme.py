# -*- coding: utf-8 -*-
"""
src/theme.py
============
Paleta institucional y tipografía del Sistema AT (parte del diseño oficial,
NO modificar sin autorización de la DINADAF). También aplica el modo de
apariencia y el tema base de CustomTkinter.
"""
from __future__ import annotations

import customtkinter as ctk

COLORS = {
    "sidebar":        "#0f172a",   # slate-900
    "sidebar_hover":  "#1e293b",   # slate-800
    "sidebar_active": "#6366f1",   # indigo-500
    "bg_main":        "#f1f5f9",   # slate-100
    "card":           "#ffffff",
    "border":         "#e2e8f0",
    "text_primary":   "#0f172a",
    "text_secondary": "#64748b",
    "text_light":     "#f8fafc",
    "accent":         "#6366f1",
    "accent_hover":   "#4f46e5",
    "success":        "#10b981",
    "warning":        "#f59e0b",
    "danger":         "#ef4444",
}

FONTS = {
    "h1": ("Segoe UI", 26, "bold"),
    "h2": ("Segoe UI", 20, "bold"),
    "h3": ("Segoe UI", 15, "bold"),
    "body": ("Segoe UI", 12),
    "small": ("Segoe UI", 10),
    "small_bold": ("Segoe UI", 10, "bold"),
    "button": ("Segoe UI", 12, "bold"),
}


def aplicar_tema() -> None:
    """Aplica el modo de apariencia claro y el tema base de CustomTkinter."""
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")
