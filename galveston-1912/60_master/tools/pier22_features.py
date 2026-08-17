"""Locate, per row and per plate, every drafted feature across the disputed band.

The repair hinges on three questions that must be answered in numbers, not by
eye on a downscaled preview:
  1. where each plate draws the slip's east bulkhead,
  2. where each plate's westernmost rail-fan track begins,
  3. whether a jointly-blank corridor separates (1) from (2) wide enough to
     carry a hard source boundary.

Prints ink-run tables so the corridor can be read directly off the plates.
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
X0, Y0, X1, Y1 = 7700, 6600, 8900, 9600
W, H = X1 - X0, Y1 - Y0

tf = json.load(open(f"{G}/40_solve/output_sheet5_joint/"
                    "transforms_sheet5_joint_shared.json"))["panels"]
geo = json.load(open(f"{G}/fable_review/sheet05_candidate_regions.geojson"))
feats = {f["properties"].get("region_id"): f for f in geo["features"]}
scan = cv2.imread(SCAN, cv2.IMREAD_COLOR)
SH, SW = scan.shape[:2]
DIV_HALF = 40
EDGE_INSET = {"top": 80, "bottom": 96, "left": 250, "right": 70}
div_x = 3789.0 + 0.0099 * np.arange(SH, dtype=np.float64)


def region_mask(rid):
    poly = np.array(feats[rid]["geometry"]["coordinates"][0], np.float64)
    m = np.zeros((SH, SW), np.uint8)
    cv2.fillPoly(m, [np.round(poly).astype(np.int32)], 255)
    cols = np.arange(SW)[None, :]
    xi = div_x[:, None]
    if rid == "A":
        m[cols >= (xi - DIV_HALF)] = 0
    else:
        m[cols <= (xi + DIV_HALF)] = 0
    m[:EDGE_INSET["top"], :] = 0
    m[SH - EDGE_INSET["bottom"]:, :] = 0
    m[:, :EDGE_INSET["left"]] = 0
    m[:, SW - EDGE_INSET["right"]:] = 0
    return m


def panel_layer(rid):
    key = "5A" if "A" in rid else "5B"
    r = tf[key]["raw"]
    M = np.array([[r["a"], -r["b"], r["tx"] - CX0 - X0],
                  [r["b"], r["a"], r["ty"] - CY0 - Y0]], np.float64)
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
# pool over +-12 rows so a single row's gaps in a dashed/thin line do not read
# as blank ground
kern = np.ones((25, 1), np.uint8)
p9 = cv2.dilate(ink9.astype(np.uint8), kern) > 0
pB = cv2.dilate(inkB.astype(np.uint8), kern) > 0


def runs(row, min_len=3):
    d = np.diff(np.concatenate([[0], row.view(np.int8), [0]]))
    s = np.where(d == 1)[0]
    e = np.where(d == -1)[0]
    return [(int(a + X0), int(b + X0)) for a, b in zip(s, e) if b - a >= min_len]


print(f"ink runs across canvas x{X0}-{X1}  (pooled +-12 rows)")
print(f"{'row':>6}  {'panel B (sheet 5)':<44} {'sheet 9':<44}")
for y in range(6800, 9601, 200):
    i = y - Y0
    if i < 0 or i >= H:
        continue
    rb = runs(pB[i])
    r9 = runs(p9[i])
    fb = " ".join(f"{a}-{b}" for a, b in rb[:5])
    f9 = " ".join(f"{a}-{b}" for a, b in r9[:5])
    print(f"{y:>6}  {fb:<44} {f9:<44}")

# jointly-blank corridor between panel B's bulkhead and sheet 9's first track
print("\njointly-blank runs (neither plate draws), canvas x, with 12 px clearance")
kk = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (25, 25))
busy = cv2.dilate((p9 | pB).astype(np.uint8), kk) > 0
recs = {}
for y in range(Y0, Y1):
    fr = runs(~busy[y - Y0], min_len=1)
    recs[y] = fr
for y in range(6800, 9601, 200):
    print(f"{y:>6}  " + " ".join(f"{a}-{b}({b-a})" for a, b in recs[y][:6]))
np.save(f"{OUT}/busy.npy", busy)
print(f"\nsaved {OUT}/busy.npy  window x{X0}-{X1} y{Y0}-{Y1}")
