#!/usr/bin/env python3
"""Normaliza codificación y saltos de línea de los archivos v2.1 y reempaqueta el ZIP.

- .bat  -> ASCII estricto + CRLF (requisito para cmd.exe en Windows)
- .txt  -> UTF-8 con BOM + CRLF (Notepad y PowerShell 5 los leen bien)
- Actualiza versiones v1.1 -> v2.1 en archivos integrados.
- Crea el ZIP final en download/ y lo verifica.
"""
import sys
from pathlib import Path

STAGE = Path("/home/z/my-project/build_v21/stage/SistemaAT_Portable")
OUT_ZIP = Path("/home/z/my-project/download/SistemaAT_Portable_v2.1.zip")


def to_crlf(text: str) -> str:
    # Normaliza a LF primero para evitar mezclas, luego a CRLF.
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return text.replace("\n", "\r\n")


def normalize_bat(path: Path) -> None:
    raw = path.read_bytes()
    text = raw.decode("utf-8-sig")
    bad = {ch for ch in text if ord(ch) > 127}
    if bad:
        print(f"[BAT] {path.name}: caracteres no-ASCII {sorted(bad)} -> quitando acentos")
        trans = str.maketrans({
            "á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u",
            "Á": "A", "É": "E", "Í": "I", "Ó": "O", "Ú": "U",
            "ñ": "n", "Ñ": "N", "ü": "u", "Ü": "U",
            "«": '"', "»": '"', "“": '"', "”": '"', "’": "'",
            "—": "-", "–": "-", "·": "-",
        })
        text = text.translate(trans)
        bad2 = {ch for ch in text if ord(ch) > 127}
        if bad2:
            sys.exit(f"[FALLO] {path.name} sigue con no-ASCII: {bad2}")
    path.write_bytes(to_crlf(text).encode("ascii"))
    print(f"[BAT OK] {path.name}: ASCII + CRLF")


def normalize_txt(path: Path) -> None:
    text = path.read_text(encoding="utf-8-sig")
    path.write_bytes(b"\xef\xbb\xbf" + to_crlf(text).encode("utf-8"))
    print(f"[TXT OK] {path.name}: UTF-8 BOM + CRLF")


def main() -> None:
    # 1) Versiones v1.1 -> v2.1 en archivos integrados (manteniendo su codificación).
    for name, enc in (("CONSOLA_DEBUG.bat", "ascii"),
                      ("INICIAR_SISTEMA.bat", "ascii"),
                      ("LEEME_PORTABLE.txt", "utf-8")):
        p = STAGE / name
        raw = p.read_bytes()
        if raw.startswith(b"\xef\xbb\xbf"):
            body = raw[3:].decode("utf-8")
            bom = b"\xef\xbb\xbf"
        else:
            body = raw.decode(enc)
            bom = b""
        body = body.replace("v1.1", "v2.1")
        p.write_bytes(bom + to_crlf(body).encode(enc))
        print(f"[VER] {name}: version -> v2.1")

    # 2) Normalizar los archivos nuevos.
    for name in ("Instalar-SistemaAT.bat", "Desinstalar-SistemaAT.bat",
                 "Respaldar-Datos.bat"):
        normalize_bat(STAGE / name)
    normalize_txt(STAGE / "LEEME-INSTALACION.txt")
    normalize_txt(STAGE / "LEEME_PORTABLE.txt")

    # 3) Empaquetar (carpeta raiz SistemaAT_Portable, determinista).
    import zipfile
    OUT_ZIP.parent.mkdir(parents=True, exist_ok=True)
    if OUT_ZIP.exists():
        OUT_ZIP.unlink()
    files = sorted(p for p in STAGE.rglob("*") if p.is_file())
    with zipfile.ZipFile(OUT_ZIP, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for p in files:
            arcname = "SistemaAT_Portable/" + str(p.relative_to(STAGE))
            zi = zipfile.ZipInfo(arcname, date_time=(2026, 11, 5, 15, 0, 0))
            zi.external_attr = 0o755 << 16
            zi.compress_type = zipfile.ZIP_DEFLATED  # ZipInfo no hereda la compresion del ZipFile
            zf.writestr(zi, p.read_bytes(), compresslevel=9)
    print(f"\n[ZIP] creado: {OUT_ZIP} ({OUT_ZIP.stat().st_size:,} bytes, {len(files)} archivos)")


if __name__ == "__main__":
    main()
