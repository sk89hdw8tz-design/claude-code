#!/usr/bin/env python3
"""Render a boundary-band strip of a sheet with native-coordinate grid.

  strip.py SHEET h|v COORD [--half 280] [--lo 0] [--hi 3400] [--zoom 1] [--out P]
h: horizontal boundary at y=COORD -> band y in [COORD-half, COORD+half], x in [lo,hi]
v: vertical   boundary at x=COORD -> band x in [COORD-half, COORD+half], y in [lo,hi]
"""
import argparse, os, cv2
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ap = argparse.ArgumentParser()
ap.add_argument("sheet"); ap.add_argument("axis"); ap.add_argument("coord", type=int)
ap.add_argument("--half", type=int, default=280)
ap.add_argument("--lo", type=int, default=0); ap.add_argument("--hi", type=int, default=99999)
ap.add_argument("--zoom", type=float, default=1.0); ap.add_argument("--grid", type=int, default=100)
ap.add_argument("--out", default=None)
a = ap.parse_args()
img = cv2.imread(os.path.join(REPO, "work", "sheets", "1899", f"Galveston_1899_sheet_{a.sheet}.jpg"))
H, W = img.shape[:2]
if a.axis == "h":
    x0, x1 = max(0, a.lo), min(W, a.hi); y0, y1 = max(0, a.coord-a.half), min(H, a.coord+a.half)
else:
    y0, y1 = max(0, a.lo), min(H, a.hi); x0, x1 = max(0, a.coord-a.half), min(W, a.coord+a.half)
crop = img[y0:y1, x0:x1]
z = a.zoom
crop = cv2.resize(crop, None, fx=z, fy=z, interpolation=cv2.INTER_CUBIC)
g = a.grid
gx = ((x0//g)+1)*g
while gx < x1:
    px = int((gx-x0)*z); major = (gx % (g*5) == 0)
    cv2.line(crop, (px,0),(px,crop.shape[0]),(0,140,255), 2 if major else 1)
    if major: cv2.putText(crop, str(gx), (px+3,20), cv2.FONT_HERSHEY_SIMPLEX, .55,(0,90,255),2)
    gx += g
gy = ((y0//g)+1)*g
while gy < y1:
    py = int((gy-y0)*z); major = (gy % (g*5) == 0)
    cv2.line(crop, (0,py),(crop.shape[1],py),(0,140,255), 2 if major else 1)
    if major: cv2.putText(crop, str(gy), (4,py-4), cv2.FONT_HERSHEY_SIMPLEX, .55,(0,90,255),2)
    gy += g
out = a.out or os.path.join("/tmp/claude-0/-home-user-claude-code/ce2e7a9c-d756-5c87-a2a8-b95d8c16cea2/scratchpad", f"strip_{a.sheet}_{a.axis}{a.coord}_{a.lo}.png")
os.makedirs(os.path.dirname(out), exist_ok=True)
cv2.imwrite(out, crop); print(out, crop.shape)
