"""Visual check of the sheet-5 A|B panel registration in the mosaic frame.

Warps BOTH panels' overlap ground into the mosaic and renders them as a
red/cyan anaglyph: where the two drafts agree the ink prints neutral dark;
where they disagree it splits into a red ghost and a cyan ghost, and the
split distance IS the disagreement. This is the direct visual test of whether
the tracks and the Pier 22 shed carry through the join.

Usage: check_panel_join.py <transforms_json> <tag>
"""

import json
import os
import sys

import cv2
import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
G = ROOT if os.path.basename(ROOT) == "galveston-1912" else os.path.join(ROOT, "galveston-1912")
SCAN = ("/home/user/g1912/data-branch/galveston_1912_sources/"
        "sanborn08539_004_img009_archival.jp2")
OUT = "/home/user/g1912/work"

tf_path = sys.argv[1]
tag = sys.argv[2] if len(sys.argv) > 2 else "join"

panels = {k: v["raw"] for k, v in json.load(open(tf_path))["panels"].items()}
xp = json.load(open(os.path.join(
    G, "30_controls/verified/cross_panel_05_v2.json")))["correspondences"]

scan = cv2.imread(SCAN, cv2.IMREAD_COLOR)
if scan is None:
    raise SystemExit(f"cannot read {SCAN}")
H, W = scan.shape[:2]
divider = lambda y: 3797.6 + 0.01015 * y          # measured thick-rule centreline

# Panel masks in sheet space: A = left of the divider, B = right of it.
yy, xx = np.mgrid[0:H, 0:W]
dv = divider(yy)
maskA = (xx < dv - 14).astype(np.uint8)           # keep clear of the 22 px rule
maskB = (xx > dv + 14).astype(np.uint8)

# Mosaic window: centred on the duplicated ground (mean of mapped correspondences)
def M(r):
    return (np.array([[r["a"], -r["b"], r["tx"]],
                      [r["b"],  r["a"], r["ty"]]], dtype=np.float64))

MA, MB = M(panels["5A"]), M(panels["5B"])
pts = []
for c in xp:
    a = np.array([c["A"][0], c["A"][1], 1.0])
    b = np.array([c["B"][0], c["B"][1], 1.0])
    pts.append(MA @ a)
    pts.append(MB @ b)
pts = np.array(pts)
cx, cy = pts[:, 0].mean(), pts[:, 1].mean()
half_w, half_h = 2400, 1500
x0, y0 = int(cx - half_w), int(cy - half_h)

def warp(mask):
    T = MA.copy() if mask is maskA else MB.copy()
    T[0, 2] -= x0
    T[1, 2] -= y0
    img = cv2.warpAffine(scan, T, (2 * half_w, 2 * half_h),
                         flags=cv2.INTER_LANCZOS4,
                         borderMode=cv2.BORDER_CONSTANT, borderValue=(255, 255, 255))
    m = cv2.warpAffine(mask * 255, T, (2 * half_w, 2 * half_h),
                       flags=cv2.INTER_NEAREST, borderMode=cv2.BORDER_CONSTANT,
                       borderValue=0)
    img[m == 0] = 255
    return img

A = warp(maskA)
B = warp(maskB)
gA = cv2.cvtColor(A, cv2.COLOR_BGR2GRAY)
gB = cv2.cvtColor(B, cv2.COLOR_BGR2GRAY)

# anaglyph: A -> red channel, B -> cyan (green+blue)
ana = np.dstack([np.minimum(gA, 255), np.minimum(gB, 255), np.minimum(gB, 255)])
both = (gA < 200) & (gB < 200)
cv2.imwrite(f"{OUT}/{tag}_anaglyph.jpg", ana[:, :, ::-1],
            [cv2.IMWRITE_JPEG_QUALITY, 93])
cv2.imwrite(f"{OUT}/{tag}_A.jpg", A, [cv2.IMWRITE_JPEG_QUALITY, 90])
cv2.imwrite(f"{OUT}/{tag}_B.jpg", B, [cv2.IMWRITE_JPEG_QUALITY, 90])
print(f"{tag}: window mosaic ({x0},{y0}) size {2*half_w}x{2*half_h}; "
      f"ink overlap {both.sum():,} px; wrote {tag}_anaglyph.jpg")
