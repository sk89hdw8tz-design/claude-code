#!/usr/bin/env python3
"""Crop helper for manual S8|S10 seam work.

Usage:
  python manual_crop_s8_s10.py SHEET X0 Y0 X1 Y1 ZOOM [GRIDSTEP] [OUTNAME]

Writes an upscaled crop with a grid overlay labelled in SOURCE pixel
coordinates, so coordinates can be read straight off the picture.
"""
import sys
import os
from PIL import Image, ImageDraw, ImageFont

Image.MAX_IMAGE_PIXELS = None

BASE = "/home/user/claude-code/galveston-1889-sanborn"
ORIG = os.path.join(BASE, "data/original")
OUT = os.path.join(BASE, "output/qc/manual_crops")


def sheet_path(n):
    return os.path.join(ORIG, f"txu-sanborn-galveston-1889-Sheet {n}.jpg")


def load_font(size):
    for p in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationMono-Bold.ttf",
    ):
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def crop(sheet, x0, y0, x1, y1, zoom, grid=None, name=None, resample="nearest"):
    im = Image.open(sheet_path(sheet)).convert("RGB")
    W, H = im.size
    x0, y0 = max(0, int(x0)), max(0, int(y0))
    x1, y1 = min(W, int(x1)), min(H, int(y1))
    sub = im.crop((x0, y0, x1, y1))
    rs = Image.NEAREST if resample == "nearest" else Image.LANCZOS
    big = sub.resize(((x1 - x0) * zoom, (y1 - y0) * zoom), rs)
    d = ImageDraw.Draw(big)
    if grid:
        fs = max(11, min(26, zoom * 2))
        font = load_font(fs)
        # vertical lines
        gx = ((x0 + grid - 1) // grid) * grid
        while gx < x1:
            px = (gx - x0) * zoom
            major = (gx % (grid * 5) == 0)
            d.line([(px, 0), (px, big.height)],
                   fill=(255, 0, 0) if major else (0, 160, 255), width=1)
            if major:
                d.text((px + 2, 2), str(gx), fill=(255, 0, 0), font=font)
                d.text((px + 2, big.height - fs - 3), str(gx),
                       fill=(255, 0, 0), font=font)
            gx += grid
        gy = ((y0 + grid - 1) // grid) * grid
        while gy < y1:
            py = (gy - y0) * zoom
            major = (gy % (grid * 5) == 0)
            d.line([(0, py), (big.width, py)],
                   fill=(255, 0, 0) if major else (0, 160, 255), width=1)
            if major:
                d.text((2, py + 2), str(gy), fill=(255, 0, 0), font=font)
                d.text((big.width - 70, py + 2), str(gy),
                       fill=(255, 0, 0), font=font)
            gy += grid
    if name is None:
        name = f"s{sheet}_{x0}_{y0}_{x1}_{y1}_z{zoom}.png"
    p = os.path.join(OUT, name)
    big.save(p)
    print(p, big.size, "src", (x0, y0, x1, y1))
    return p


if __name__ == "__main__":
    a = sys.argv[1:]
    sheet = a[0]
    x0, y0, x1, y1, zoom = (int(v) for v in a[1:6])
    grid = int(a[6]) if len(a) > 6 and a[6] != "-" else None
    name = a[7] if len(a) > 7 else None
    rs = a[8] if len(a) > 8 else "nearest"
    crop(sheet, x0, y0, x1, y1, zoom, grid, name, rs)
