#!/usr/bin/env python
"""Side-by-side crop of the same ground feature on two sheets, with source-pixel grid."""
import sys, os
from PIL import Image, ImageDraw, ImageFont
Image.MAX_IMAGE_PIXELS = None
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'data', 'original', 'txu-sanborn-galveston-1889-Sheet {}.jpg')
OUT = os.path.join(ROOT, 'output', 'qc', 'manual_crops')
_c = {}

def load(s):
    if s not in _c:
        _c[s] = Image.open(SRC.format(s))
    return _c[s]

def panel(sheet, cx, cy, halfw, halfh, zoom, grid, label_every):
    x0, y0 = int(cx - halfw), int(cy - halfh)
    x1, y1 = int(cx + halfw), int(cy + halfh)
    im = load(sheet).crop((x0, y0, x1, y1))
    big = im.resize((int((x1 - x0) * zoom), int((y1 - y0) * zoom)), Image.NEAREST)
    d = ImageDraw.Draw(big)
    try:
        font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', max(11, int(zoom * 1.4)))
    except Exception:
        font = ImageFont.load_default()
    gx = (x0 // grid) * grid
    while gx <= x1:
        if gx >= x0:
            px = int((gx - x0) * zoom)
            d.line([(px, 0), (px, big.size[1])], fill=(255, 0, 0), width=1)
            if gx % label_every == 0:
                d.text((px + 2, 2), str(gx), fill=(200, 0, 0), font=font)
        gx += grid
    gy = (y0 // grid) * grid
    while gy <= y1:
        if gy >= y0:
            py = int((gy - y0) * zoom)
            d.line([(0, py), (big.size[0], py)], fill=(255, 0, 0), width=1)
            if gy % label_every == 0:
                d.text((2, py + 2), str(gy), fill=(200, 0, 0), font=font)
        gy += grid
    d.text((6, big.size[1] - 26), 'SHEET %s' % sheet, fill=(0, 0, 255), font=font)
    return big

def pair(name, sa, ca, sb, cb, halfw=45, halfh=45, zoom=14, grid=10, label_every=20):
    A = panel(sa, ca[0], ca[1], halfw, halfh, zoom, grid, label_every)
    B = panel(sb, cb[0], cb[1], halfw, halfh, zoom, grid, label_every)
    W = A.size[0] + B.size[0] + 24
    H = max(A.size[1], B.size[1])
    out = Image.new('RGB', (W, H), (255, 255, 255))
    out.paste(A, (0, 0))
    out.paste(B, (A.size[0] + 24, 0))
    os.makedirs(OUT, exist_ok=True)
    p = os.path.join(OUT, name + '.png')
    out.save(p)
    print(p, out.size)

if __name__ == '__main__':
    import json
    spec = json.loads(sys.argv[1])
    for s in spec:
        pair(**s)
