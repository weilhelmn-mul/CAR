# -*- coding: utf-8 -*-
"""
src/services/pdf.py
===================
Conversión de los Excel generados a PDF con la máxima fidelidad al formato
oficial del IPD (se convierte el propio .xlsx, no una recreación).

Estrategia (en orden):
    1. LibreOffice en modo headless (multiplataforma, búsqueda en PATH y en
       las rutas típicas de Windows).
    2. Excel COM vía pywin32 (solo Windows, requiere Microsoft Excel).
    3. Si no hay ninguna opción → RuntimeError con instrucciones claras de
       instalación (el Excel sí queda guardado y puede exportarse a mano).
"""
from __future__ import annotations

import logging
import shutil
import subprocess
import sys
from pathlib import Path

log = logging.getLogger(__name__)

_RUTAS_SOFFICE_WINDOWS = (
    r"C:\Program Files\LibreOffice\program\soffice.exe",
    r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
)
_TIEMPO_LIMITE_S = 180


def _mensaje_instalacion() -> str:
    return (
        "No se encontró LibreOffice ni Microsoft Excel para convertir a PDF.\n\n"
        "Para generar PDF instale una de estas opciones:\n"
        "  • LibreOffice (gratuito): https://es.libreoffice.org\n"
        "  • Microsoft Excel (solo Windows, con pywin32 instalado).\n\n"
        "El archivo Excel SÍ se generó correctamente; también puede abrirlo y "
        "exportarlo a PDF manualmente."
    )


def _buscar_soffice() -> str | None:
    """Localiza el ejecutable de LibreOffice (PATH o rutas típicas de Windows)."""
    encontrado = shutil.which("soffice") or shutil.which("soffice.exe")
    if encontrado:
        return encontrado
    for ruta in _RUTAS_SOFFICE_WINDOWS:
        if Path(ruta).exists():
            return ruta
    return None


def excel_a_pdf(ruta_xlsx: str | Path) -> str:
    """Convierte un .xlsx a .pdf en la misma carpeta y devuelve la ruta del PDF."""
    xlsx = Path(ruta_xlsx)
    if not xlsx.exists():
        raise FileNotFoundError(f"No existe el archivo Excel a convertir: {xlsx}")
    pdf = xlsx.with_suffix(".pdf")

    soffice = _buscar_soffice()
    if soffice:
        try:
            resultado = subprocess.run(  # noqa: S603
                [
                    soffice, "--headless", "--norestore",
                    "--convert-to", "pdf", "--outdir", str(xlsx.parent), str(xlsx),
                ],
                capture_output=True, text=True, timeout=_TIEMPO_LIMITE_S,
            )
            if pdf.exists():
                log.info("PDF generado con LibreOffice: %s", pdf)
                return str(pdf)
            detalle = (resultado.stderr or resultado.stdout or "").strip()
            raise RuntimeError(f"LibreOffice no generó el PDF. Detalle: {detalle}")
        except subprocess.TimeoutExpired as e:
            raise RuntimeError(
                f"La conversión a PDF con LibreOffice superó los {_TIEMPO_LIMITE_S} s de espera."
            ) from e

    if sys.platform == "win32":
        return _convertir_con_excel_com(xlsx, pdf)

    raise RuntimeError(_mensaje_instalacion())


def _convertir_con_excel_com(xlsx: Path, pdf: Path) -> str:
    """Conversión usando Microsoft Excel vía COM (Windows + pywin32)."""
    try:
        import win32com.client  # type: ignore  # pywin32 (solo Windows)
    except ImportError as e:
        raise RuntimeError(_mensaje_instalacion()) from e

    excel = None
    try:
        excel = win32com.client.DispatchEx("Excel.Application")
        excel.Visible = False
        excel.DisplayAlerts = False
        libro = excel.Workbooks.Open(str(xlsx), ReadOnly=True)
        try:
            libro.ExportAsFixedFormat(0, str(pdf))  # 0 = xlTypePDF
        finally:
            libro.Close(SaveChanges=False)
        if pdf.exists():
            log.info("PDF generado con Excel COM: %s", pdf)
            return str(pdf)
        raise RuntimeError("Excel no generó el PDF; revise que el archivo no esté protegido.")
    except RuntimeError:
        raise
    except Exception as e:
        raise RuntimeError(f"Fallo la conversión con Excel COM: {e}") from e
    finally:
        if excel is not None:
            excel.Quit()
