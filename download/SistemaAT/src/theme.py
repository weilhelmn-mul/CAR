"""
=============================================================
 Sistema AT · Instituto Peruano del Deporte (IPD - DINADAF)
 theme.py — Paleta de colores y tipografías oficiales.
 CONSTANTES NO MODIFICABLES (definidas por el PROMPT MAESTRO).
=============================================================
"""

COLORS: dict[str, str] = {
    "sidebar": "#0f172a",
    "sidebar_hover": "#1e293b",
    "sidebar_active": "#6366f1",
    "bg_main": "#f1f5f9",
    "card": "#ffffff",
    "border": "#e2e8f0",
    "text_primary": "#0f172a",
    "text_secondary": "#64748b",
    "text_light": "#f8fafc",
    "accent": "#6366f1",
    "accent_hover": "#4f46e5",
    "success": "#10b981",
    "warning": "#f59e0b",
    "danger": "#ef4444",
}

FONTS: dict[str, tuple] = {
    "h1": ("Segoe UI", 26, "bold"),
    "h2": ("Segoe UI", 20, "bold"),
    "h3": ("Segoe UI", 15, "bold"),
    "body": ("Segoe UI", 12),
    "small": ("Segoe UI", 10),
    "small_bold": ("Segoe UI", 10, "bold"),
    "button": ("Segoe UI", 12, "bold"),
}


def fuente(clave: str) -> tuple:
    """Devuelve la tupla de fuente `clave` lista para pasar a los widgets CTk."""
    return FONTS[clave]
