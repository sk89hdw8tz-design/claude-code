#!/usr/bin/env python
"""Crop + upscale + grid-overlay helper for manual seam GCP work.

Usage:
  python manual_crop_helper.py SHEET X0 Y0 X1 Y1 ZOOM OUTNAME [GRIDSTEP]

Writes output/qc/manual_crops/OUTNAME.png with a 1-source-pixel-wide grid
drawn every GRIDSTEP source pixels, labelled with SOURCE coordinates.
"""
import sys, os
from PIL import Image, ImageDraw, ImageFont
Image.MAX_IMAGE_PIXELS = None

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'data', 'original', 'txu-sanborn-galveston-1889-Sheet {}.jpg')
OUT = os.path.join(ROOT, 'output', 'qc', 'manual_crops')

_cache = {}

def load(sheet):
    if sheet not in _cache:
        _cache[sheet] = Image.open(SRC.format(sheet))
    return _cache[sheet]


def crop(sheet, x0, y0, x1, y1, zoom, name, grid=None, resample='nearest',
         label_every=None, color=(255, 0, 0)):
    im = load(sheet)
    x0, y0, x1, y1 = int(x0), int(y0), int(x1), int(y1)
    c = im.crop((x0, y0, x1, y1))
    r = Image.NEAREST if resample == 'nearest' else Image.LANCZOS
    w, h = c.size
    big = c.resize((int(w * zoom), int(h * zoom)), r)
    d = ImageDraw.Draw(big)
    try:
        font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', max(10, int(zoom * 1.6)))
    except Exception:
        font = ImageFont.load_default()
    if grid:
        if label_every is None:
            label_every = grid * 2
        gx = (x0 // grid) * grid
        while gx <= x1:
            if gx >= x0:
                px = int((gx - x0) * zoom)
                d.line([(px, 0), (px, big.size[1])], fill=color, width=1)
                if gx % label_every == 0:
                    d.text((px + 2, 2), str(gx), fill=color, font=font)
            gx += grid
        gy = (y0 // grid) * grid
        while gy <= y1:
            if gy >= y0:
                py = int((gy - y0) * zoom)
                d.line([(0, py), (big.size[0], py)], fill=color, width=1)
                if gy % label_every == 0:
                    d.text((2, py + 2), str(gy), fill=color, font=font)
            gy += grid
    os.makedirs(OUT, exist_ok=True)
    p = os.path.join(OUT, name + '.png')
    big.save(p)
    print(p, big.size, 'src=(%d,%d)-(%d,%d) zoom=%s' % (x0, y0, x1, y1, zoom))
    return p


if __name__ == '__main__':
    a = sys.argv[1:]
    sheet = a[0]
    x0, y0, x1, y1 = [float(v) for v in a[1:5]]
    zoom = float(a[5])
    name = a[6]
    grid = int(a[7]) if len(a) > 7 else None
    lab = int(a[8]) if len(a) > 8 else None
    crop(sheet, x0, y0, x1, y1, zoom, name, grid, label_every=lab)
