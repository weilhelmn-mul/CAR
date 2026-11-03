"""
=============================================================
 Sistema AT · Instituto Peruano del Deporte (IPD - DINADAF)
 services/pdf.py — Conversión Excel → PDF.
 Orden de resolución: LibreOffice headless → Microsoft Excel (COM).
 Si no existe ninguno, lanza RuntimeError con instrucciones claras
 (el archivo Excel generado siempre queda disponible).
=============================================================
"""
from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path

log = logging.getLogger("sistema_at.pdf")

_TIMEOUT_SEGUNDOS = 180


def _localizar_libreoffice() -> str | None:
    """Busca el ejecutable de LibreOffice en PATH y rutas típicas de Windows."""
    for comando in ("soffice", "libreoffice"):
        ruta = shutil.which(comando)
        if ruta:
            return ruta
    candidatas = (
        r"C:\Program Files\LibreOffice\program\soffice.exe",
        r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
    )
    for ruta in candidatas:
        if Path(ruta).exists():
            return ruta
    return None


def _convertir_con_excel_com(xlsx: Path, pdf: Path) -> bool:
    """Convierte usando Microsoft Excel vía COM (solo Windows). Devuelve éxito."""
    try:
        import win32com.client  # type: ignore  # proviene de pywin32 (solo Windows)
    except ImportError:
        log.info("pywin32 no disponible; conversión COM omitida.")
        return False
    excel = None
    try:
        excel = win32com.client.DispatchEx("Excel.Application")
        excel.Visible = False
        excel.DisplayAlerts = False
        libro = excel.Workbooks.Open(str(xlsx))
        libro.ExportAsFixedFormat(0, str(pdf))  # 0 = xlTypePDF
        libro.Close(SaveChanges=False)
        return pdf.exists()
    except Exception as exc:  # pragma: no cover - depende del equipo del usuario
        log.warning("Conversión vía Excel COM falló: %s", exc)
        return False
    finally:
        if excel is not None:
            try:
                excel.Quit()
            except Exception:  # pragma: no cover
                pass


def excel_a_pdf(xlsx_path: str | Path) -> str:
    """Convierte un .xlsx a PDF junto al original y devuelve la ruta del PDF.

    Lanza RuntimeError si no hay LibreOffice ni Excel disponibles, indicando
    cómo instalar el conversor. El Excel original nunca se modifica.
    """
    xlsx = Path(xlsx_path).resolve()
    if not xlsx.exists():
        raise FileNotFoundError(f"No existe el archivo Excel: {xlsx}")
    pdf = xlsx.with_suffix(".pdf")

    soffice = _localizar_libreoffice()
    if soffice:
        try:
            subprocess.run(
                [soffice, "--headless", "--norestore", "--convert-to", "pdf",
                 "--outdir", str(xlsx.parent), str(xlsx)],
                capture_output=True, text=True, timeout=_TIMEOUT_SEGUNDOS, check=False,
            )
            if pdf.exists():
                log.info("PDF generado con LibreOffice: %s", pdf)
                return str(pdf)
            log.warning("LibreOffice no produjo salida PDF: revisar permisos/versión.")
        except (subprocess.TimeoutExpired, OSError) as exc:
            log.warning("Fallo la conversión con LibreOffice: %s", exc)

    if _convertir_con_excel_com(xlsx, pdf):
        log.info("PDF generado con Microsoft Excel (COM): %s", pdf)
        return str(pdf)

    raise RuntimeError(
        "No se pudo convertir a PDF. Instale LibreOffice (https://es.libreoffice.org) "
        "o Microsoft Excel y vuelva a intentarlo. El archivo Excel generado sigue "
        f"disponible en: {xlsx}"
    )
