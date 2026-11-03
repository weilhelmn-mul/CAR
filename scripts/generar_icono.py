"""generar_icono.py — Crea assets/icon.ico del Sistema AT (Pillow)."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

RAIZ = Path("/home/z/my-project/download/SistemaAT")
TAMANO = 256


def principal() -> None:
    imagen = Image.new("RGBA", (TAMANO, TAMANO), (0, 0, 0, 0))
    dibujo = ImageDraw.Draw(imagen)
    # Fondo redondeado azul oscuro
    dibujo.rounded_rectangle([8, 8, TAMANO - 8, TAMANO - 8], radius=48, fill=(15, 23, 42, 255))
    # Círculo indigo
    dibujo.ellipse([52, 44, TAMANO - 52, TAMANO - 84], fill=(99, 102, 241, 255))
    # Texto AT
    try:
        fuente = ImageFont.load_default(size=104)
    except TypeError:  # Pillow < 10.1
        fuente = ImageFont.load_default()
    texto = "AT"
    caja = dibujo.textbbox((0, 0), texto, font=fuente)
    ancho_texto = caja[2] - caja[0]
    dibujo.text(((TAMANO - ancho_texto) / 2 - caja[0], 58), texto, font=fuente, fill=(255, 255, 255, 255))
    # Medalla inferior
    dibujo.rounded_rectangle([88, 168, TAMANO - 88, 216], radius=18, fill=(16, 185, 129, 255))

    destino = RAIZ / "assets" / "icon.ico"
    destino.parent.mkdir(parents=True, exist_ok=True)
    imagen.save(destino, sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
    imagen.convert("RGB").save(RAIZ / "assets" / "icon.png")
    print(f"[OK] {destino}")


if __name__ == "__main__":
    principal()
