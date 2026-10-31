# -*- coding: utf-8 -*-
"""Genera assets/icon.ico del Sistema AT (medalla con 'AT' en la paleta institucional)."""
from PIL import Image, ImageDraw, ImageFont

S = 256
img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
d = ImageDraw.Draw(img)

# Fondo índigo redondeado (accent #6366f1)
d.rounded_rectangle([8, 8, S - 8, S - 8], radius=56, fill=(99, 102, 241, 255))

# Cintas de la medalla
d.polygon([(S // 2 - 40, 140), (S // 2 - 78, 238), (S // 2 - 16, 216)], fill=(79, 70, 229, 255))
d.polygon([(S // 2 + 40, 140), (S // 2 + 78, 238), (S // 2 + 16, 216)], fill=(79, 70, 229, 255))

# Medalla
d.ellipse([S // 2 - 54, 30, S // 2 + 54, 138], fill=(245, 158, 11, 255))
d.ellipse([S // 2 - 54, 30, S // 2 + 54, 138], outline=(248, 250, 252, 255), width=8)

fuente = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 58)
d.text((S // 2, 84), "AT", font=fuente, fill=(15, 23, 42, 255), anchor="mm")

salida = "/home/z/my-project/download/atletas_system/assets/icon.ico"
img.save(salida, format="ICO", sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
print("Icono generado:", salida)
