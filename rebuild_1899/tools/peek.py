#!/usr/bin/env python3
"""Render a zoomed crop of a sheet with a native-coordinate grid, so a
feature's pixel position can be read off visually.

  python3 rebuild_1899/tools/peek.py SHEET CX CY [--r 250] [--zoom 2] \
      [--grid 50] [--out /path.png]

SHEET like 07 (loads work/sheets/1899/Galveston_1899_sheet_07.jpg).
Grid lines every --grid native px; labels are NATIVE sheet coordinates.
Default output: rebuild_1899/out/peek/<sheet>_<cx>_<cy>.png
"""
import argparse
import os

import cv2
import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sheet")
    ap.add_argument("cx", type=int)
    ap.add_argument("cy", type=int)
    ap.add_argument("--r", type=int, default=250)
    ap.add_argument("--zoom", type=float, default=2.0)
    ap.add_argument("--grid", type=int, default=50)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    img = cv2.imread(os.path.join(REPO, "work", "sheets", "1899",
                                  f"Galveston_1899_sheet_{a.sheet}.jpg"))
    assert img is not None, "sheet not found"
    H, W = img.shape[:2]
    x0, y0 = max(0, a.cx - a.r), max(0, a.cy - a.r)
    x1, y1 = min(W, a.cx + a.r), min(H, a.cy + a.r)
    crop = img[y0:y1, x0:x1]
    z = a.zoom
    crop = cv2.resize(crop, None, fx=z, fy=z, interpolation=cv2.INTER_CUBIC)
    # grid at native multiples of a.grid
    gx = ((x0 // a.grid) + 1) * a.grid
    while gx < x1:
        px = int((gx - x0) * z)
        major = (gx % (a.grid * 5) == 0)
        cv2.line(crop, (px, 0), (px, crop.shape[0]), (0, 140, 255), 2 if major else 1)
        cv2.putText(crop, str(gx), (px + 3, 22), cv2.FONT_HERSHEY_SIMPLEX,
                    0.55, (0, 90, 255), 2)
        gx += a.grid
    gy = ((y0 // a.grid) + 1) * a.grid
    while gy < y1:
        py = int((gy - y0) * z)
        major = (gy % (a.grid * 5) == 0)
        cv2.line(crop, (0, py), (crop.shape[1], py), (0, 140, 255), 2 if major else 1)
        cv2.putText(crop, str(gy), (4, py - 4), cv2.FONT_HERSHEY_SIMPLEX,
                    0.55, (0, 90, 255), 2)
        gy += a.grid
    out = a.out or os.path.join(REPO, "rebuild_1899", "out", "peek",
                                f"{a.sheet}_{a.cx}_{a.cy}.png")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    cv2.imwrite(out, crop)
    print(out)

if __name__ == "__main__":
    main()
