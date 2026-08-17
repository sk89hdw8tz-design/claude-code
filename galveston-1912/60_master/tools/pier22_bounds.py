"""Compute the feasible band for the repaired Pier 22 ownership boundary.

Three curves decide where a hard source boundary may legally sit, row by row:

  LO(y)  east edge of SHEET 9's own slip bulkhead.  The boundary must sit east
         of it, otherwise sheet 9's bulkhead is revealed alongside panel B's and
         the slip edge prints as a doubled line (the two drafts disagree by
         30-90 px here, a genuine historical disagreement, not an error).

  HI(y)  west edge of the westernmost SHEET 9 yard ink -- track, tick or
         numeral.  The boundary must sit west of it, otherwise sheet 9's own
         drawn track work is deleted.  This is exactly what the present
         boundary violates.

  BLANK  the boundary must also fall where NEITHER plate carries ink, so the
         cut crosses no drawn line on either drawing.

Prints LO/HI per row and reports any row where the band is empty.
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
X0, Y0, X1, Y1 = 7700, 6500, 8900, 9800
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
np.save(f"{OUT}/ink9.npy", ink9)
np.save(f"{OUT}/inkB.npy", inkB)
np.save(f"{OUT}/bounds_window.npy", np.array([X0, Y0, X1, Y1]))

pool = cv2.dilate(ink9.astype(np.uint8), np.ones((21, 1), np.uint8)) > 0
poolB = cv2.dilate(inkB.astype(np.uint8), np.ones((21, 1), np.uint8)) > 0

LO = np.full(H, np.nan)
HI = np.full(H, np.nan)
for i in range(H):
    row = pool[i]
    idx = np.where(row)[0]
    if len(idx) == 0:
        continue
    # sheet 9's bulkhead = first ink group; walk to its east edge
    a = idx[0]
    e = a
    while e + 1 < W and (row[e + 1] or row[e + 1:e + 26].any()):
        e += 1
    LO[i] = e + X0
    # next ink group after a >=40 px gap = start of the yard
    j = e
    while j + 1 < W and not row[j + 1]:
        j += 1
    HI[i] = (j + 1 + X0) if j + 1 < W else np.nan

# widest jointly blank run strictly between LO and HI
kk = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (21, 21))
busy = cv2.dilate((pool | poolB).astype(np.uint8), kk) > 0
np.save(f"{OUT}/busy_bounds.npy", busy)

print(f"window canvas x{X0}-{X1} y{Y0}-{Y1}")
print(f"{'row':>6} {'LO(s9 bulkhead E)':>18} {'HI(s9 yard W)':>14} {'band':>6}  blank-mid")
empty = 0
mids = np.full(H, np.nan)
for i in range(H):
    lo, hi = LO[i], HI[i]
    if np.isnan(lo) or np.isnan(hi) or hi - lo < 20:
        empty += 1
        continue
    a = int(lo - X0) + 6
    b = int(hi - X0) - 6
    if b <= a:
        empty += 1
        continue
    seg = ~busy[i, a:b]
    if not seg.any():
        empty += 1
        continue
    d = np.diff(np.concatenate([[0], seg.view(np.int8), [0]]))
    s = np.where(d == 1)[0]
    e2 = np.where(d == -1)[0]
    k = int(np.argmax(e2 - s))
    mids[i] = a + X0 + (s[k] + e2[k]) / 2.0
for y in range(6600, 9800, 100):
    i = y - Y0
    lo, hi, m = LO[i], HI[i], mids[i]
    print(f"{y:>6} {lo:18.0f} {hi:14.0f} {hi-lo:6.0f}  {m:9.1f}")
print(f"\nrows with no feasible boundary position: {empty} of {H}")
np.save(f"{OUT}/bounds_LO.npy", LO)
np.save(f"{OUT}/bounds_HI.npy", HI)
np.save(f"{OUT}/bounds_mid.npy", mids)
print(f"saved LO/HI/mid to {OUT}")
