#!/usr/bin/env python3
"""Combina las capturas de la auditoría visual en montajes etiquetados."""
from PIL import Image, ImageDraw
import os

SRC = '/tmp/render/aud'
OUT = '/tmp/render/aud'

def montage(files, cols, out, scale_w=340, bg='#0f172a', label_h=22):
    imgs = []
    for f in files:
        p = os.path.join(SRC, f)
        im = Image.open(p)
        r = scale_w / im.width
        im = im.resize((scale_w, int(im.height * r)), Image.LANCZOS)
        imgs.append((f, im))
    rows = (len(imgs) + cols - 1) // cols
    cell_h = max(im.height for _, im in imgs) + label_h
    W = cols * scale_w + (cols + 1) * 8
    H = rows * cell_h + (rows + 1) * 8
    canvas = Image.new('RGB', (W, H), bg)
    d = ImageDraw.Draw(canvas)
    for i, (name, im) in enumerate(imgs):
        r, c = divmod(i, cols)
        x = 8 + c * (scale_w + 8)
        y = 8 + r * (cell_h + 8)
        d.text((x + 2, y + 4), name, fill='#fbbf24')
        canvas.paste(im, (x, y + label_h))
    canvas.save(os.path.join(OUT, out), quality=80)
    print(f'{out}: {W}x{H}')

# Móvil: 11 capturas en montajes de 4
montage(['m-01-inicio.png', 'm-02-deportistas.png', 'm-03-formatos-alim.png', 'm-04-seguro.png'], 2, 'mont-m-a.jpg')
montage(['m-05-f3.png', 'm-06-f1.png', 'm-07-f8.png', 'm-08-f9.png'], 2, 'mont-m-b.jpg')
montage(['m-09-analisis.png', 'm-10-firmas.png', 'm-11-asistente.png'], 2, 'mont-m-c.jpg')
# Escritorio: 6 capturas
montage(['d-01-inicio.png', 'd-02-deportistas.png', 'd-03-f1.png', 'd-04-analisis.png', 'd-05-firmas.png', 'd-06-asistente.png'], 3, 'mont-d.jpg', scale_w=460)
