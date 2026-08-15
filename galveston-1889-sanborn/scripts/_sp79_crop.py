#!/usr/bin/env python3
"""Gridded crop helper for the S7|S9 second-pass manual measurement. Local only."""
import sys, os
from PIL import Image, ImageDraw
Image.MAX_IMAGE_PIXELS = None
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'output', 'qc', 'manual_crops', 'secondpass_S7_S9')
os.makedirs(OUT, exist_ok=True)
SHEETS = {
    '7': os.path.join(ROOT, 'data/original/txu-sanborn-galveston-1889-Sheet 7.jpg'),
    '9': os.path.join(ROOT, 'data/original/txu-sanborn-galveston-1889-Sheet 9.jpg'),
}
_cache = {}
def sheet(n):
    if n not in _cache:
        _cache[n] = Image.open(SHEETS[n]).convert('RGB')
    return _cache[n]

def gridcrop(n, x0, y0, x1, y1, zoom, name, label=10, grid=True):
    im = sheet(n).crop((x0, y0, x1, y1))
    w, h = im.size
    big = im.resize((w*zoom, h*zoom), Image.NEAREST)
    if grid:
        d = ImageDraw.Draw(big, 'RGBA')
        for sx in range(x0, x1+1):
            px = (sx - x0)*zoom
            if sx % label == 0: col=(255,0,0,200); wdt=2
            elif sx % 5 == 0:   col=(0,120,255,130); wdt=1
            else:               col=(0,0,0,45); wdt=1
            d.line([(px,0),(px,h*zoom)], fill=col, width=wdt)
        for sy in range(y0, y1+1):
            py = (sy - y0)*zoom
            if sy % label == 0: col=(255,0,0,200); wdt=2
            elif sy % 5 == 0:   col=(0,120,255,130); wdt=1
            else:               col=(0,0,0,45); wdt=1
            d.line([(0,py),(w*zoom,py)], fill=col, width=wdt)
        for sx in range(x0, x1+1):
            if sx % label == 0: d.text(((sx-x0)*zoom+2, 2), str(sx), fill=(200,0,0,255))
        for sy in range(y0, y1+1):
            if sy % label == 0: d.text((2, (sy-y0)*zoom+2), str(sy), fill=(200,0,0,255))
    p = os.path.join(OUT, name + '.png')
    big.save(p)
    print(p, big.size)
    return p

def plain(n, x0, y0, x1, y1, zoom, name):
    return gridcrop(n, x0, y0, x1, y1, zoom, name, grid=False)

if __name__ == '__main__':
    a = sys.argv[1:]
    if a[0] == 'plain':
        plain(a[1], int(a[2]), int(a[3]), int(a[4]), int(a[5]), int(a[6]), a[7])
    else:
        gridcrop(a[0], int(a[1]), int(a[2]), int(a[3]), int(a[4]), int(a[5]), a[6],
                 label=int(a[7]) if len(a) > 7 else 10)
