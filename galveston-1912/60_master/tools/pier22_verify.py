"""Verify the Candidate S ownership boundary against both plates.

Two things must be true for the repair to be honest:

  1. The boundary must cross essentially no drawn ink on EITHER plate, so no
     drafted line is severed and nothing has to be faked across the join.
  2. It must lie west of sheet 9's westernmost yard ink, so sheet 9's own track
     work -- the thing the present boundary deletes -- is fully restored.

Reports ink crossings per plate for the frozen boundary and for Candidate S,
so the two are compared on identical terms.
"""

import json
import os

import cv2
import numpy as np
import tifffile
from PIL import Image

Image.MAX_IMAGE_PIXELS = None

G = "/home/user/claude-code/galveston-1912"
SCAN = ("/home/user/g1912/data-branch/galveston_1912_sources/"
        "sanborn08539_004_img009_archival.jp2")
OUT = "/home/user/g1912/work/pier22"
CX0, CY0 = -16734, -8279
X0, Y0, X1, Y1 = 7700, 6400, 8900, 9600
W, H = X1 - X0, Y1 - Y0

from pier22_candidates import (CAND_S, region_mask, raw_matrix, frontier0,  # noqa: E402
                               make_frontier)

scan = cv2.imread(SCAN, cv2.IMREAD_COLOR)


def panel_layer(rid):
    key = "5A" if "A" in rid else "5B"
    M = raw_matrix(key).copy()
    M[0, 2] += -CX0 - X0
    M[1, 2] += -CY0 - Y0
    ms = region_mask(rid)
    img = cv2.warpAffine(scan, M, (W, H), flags=cv2.INTER_LANCZOS4,
                         borderMode=cv2.BORDER_CONSTANT, borderValue=(255, 255, 255))
    msk = cv2.warpAffine(ms, M, (W, H), flags=cv2.INTER_NEAREST,
                         borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    img[msk == 0] = 255
    return img, msk > 0


def flat_ink(bgr, drop=0.14):
    g = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY).astype(np.float32)
    bg = cv2.morphologyEx(g, cv2.MORPH_CLOSE,
                          cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (61, 61)))
    bg = cv2.blur(bg, (121, 121))
    return (g / np.maximum(bg, 1.0)) < (1.0 - drop)


s9 = np.ascontiguousarray(
    tifffile.imread(f"{G}/60_master/final/candidate_master.tif")[Y0:Y1, X0:X1][:, :, ::-1])
imgB, mB = panel_layer("B")
ink9 = flat_ink(s9)
inkB = flat_ink(imgB) & mB

rows = np.arange(Y0, Y1)
# use the renderer's own frontier builder, so the boundary verified here is
# byte-for-byte the boundary that would be composited (including reverting to
# the frozen frontier outside the repair neighbourhood)
bS = make_frontier(CAND_S)[Y0:Y1]
bF = frontier0[Y0:Y1]


def crossings(b, half=3):
    """Rows where the boundary column sits on drawn ink, per plate."""
    n9 = nB = 0
    for i, y in enumerate(rows):
        c = b[i] - X0
        if c < half or c >= W - half:
            continue
        if ink9[i, c - half:c + half + 1].any():
            n9 += 1
        if inkB[i, c - half:c + half + 1].any():
            nB += 1
    return n9, nB


f9, fB = crossings(bF)
s9c, sBc = crossings(bS)
print(f"rows examined: {H}   (canvas y{Y0}-{Y1})")
print(f"{'boundary':<22} {'crosses sheet-9 ink':>20} {'crosses panel-B ink':>20}")
print(f"{'frozen (delivered)':<22} {f9:>17} rows {fB:>17} rows")
print(f"{'Candidate S':<22} {s9c:>17} rows {sBc:>17} rows")

# how much sheet-9 yard ink each boundary suppresses (ink lying WEST of it,
# inside the block-owned area = ink the boundary throws away)
def suppressed(b):
    m = np.zeros((H, W), bool)
    for i in range(H):
        c = max(min(b[i] - X0, W), 0)
        m[i, :c] = True
    return int((ink9 & m).sum())


tot9 = int(ink9.sum())
print(f"\nsheet-9 drawn ink in window: {tot9:,} px")
print(f"  suppressed by frozen boundary : {suppressed(bF):,} "
      f"({100*suppressed(bF)/tot9:.1f}%)")
print(f"  suppressed by Candidate S     : {suppressed(bS):,} "
      f"({100*suppressed(bS)/tot9:.1f}%)")

totB = int(inkB.sum())
def suppressedB(b):
    m = np.zeros((H, W), bool)
    for i in range(H):
        c = max(min(b[i] - X0, W), 0)
        m[i, c:] = True
    return int((inkB & m).sum())


print(f"panel-B drawn ink in window: {totB:,} px")
print(f"  suppressed by frozen boundary : {suppressedB(bF):,} "
      f"({100*suppressedB(bF)/totB:.1f}%)")
print(f"  suppressed by Candidate S     : {suppressedB(bS):,} "
      f"({100*suppressedB(bS)/totB:.1f}%)")

print("\nper-row detail (every 200 rows)")
print(f"{'row':>6} {'frozen':>8} {'cand S':>8} {'shift':>7}  {'S on ink?':>10}")
for y in range(Y0, Y1, 200):
    i = y - Y0
    c = bS[i] - X0
    on = []
    if 0 <= c < W:
        if ink9[i, max(c-3,0):c+4].any():
            on.append("s9")
        if inkB[i, max(c-3,0):c+4].any():
            on.append("B")
    print(f"{y:>6} {bF[i]:>8} {bS[i]:>8} {bS[i]-bF[i]:>+7}  {','.join(on) or '-':>10}")
