"""Find, per canvas row, ground that is blank on BOTH plates near Pier 22.

The repair brief requires the ownership boundary to be moved into low-information
ground rather than fabricating continuity. "Low-information" has to be measured,
not assumed, so for every row in the defect neighbourhood this scans a corridor
and reports the widest run of columns where neither Sheet 5 panel B nor Sheet 9
carries drafted ink. The centre of that run is the only defensible place to put
a hard source boundary: a cut there crosses no drawn line on either plate.

Also renders a wide context view of the current master with the *present*
boundary drawn on it, so the defect can be seen entering and leaving the zone.
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
os.makedirs(OUT, exist_ok=True)
CX0, CY0 = -16734, -8279

# wide context window: tracks enter at the top and leave to the south-west
X0, Y0, X1, Y1 = 6900, 6400, 10200, 11200
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
    """Identical to composite_wharf.region_mask, so the corridor is measured on
    exactly the pixels the compositor would be allowed to place."""
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
master = np.ascontiguousarray(
    tifffile.imread(f"{G}/60_master/final/master_full.tif")[Y0:Y1, X0:X1][:, :, ::-1])
imgB, mB = panel_layer("B")

ink9 = flat_ink(s9)
inkB = flat_ink(imgB) & mB
# dilate so a boundary is not merely between two adjacent ink pixels but has
# genuine clearance from drawn line work on both plates
k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (25, 25))
busy = (cv2.dilate((ink9 | inkB).astype(np.uint8), k) > 0)

frontier = np.load(f"{OUT}/frontier_final.npy")

CORR_X0, CORR_X1 = 7500, 8600          # search corridor (canvas x)
rows, cent, width = [], [], []
for y in range(Y0, Y1):
    seg = busy[y - Y0, CORR_X0 - X0:CORR_X1 - X0]
    free = ~seg
    if not free.any():
        rows.append(y); cent.append(np.nan); width.append(0); continue
    # longest run of free columns
    d = np.diff(np.concatenate([[0], free.view(np.int8), [0]]))
    starts = np.where(d == 1)[0]
    ends = np.where(d == -1)[0]
    i = int(np.argmax(ends - starts))
    rows.append(y)
    cent.append(CORR_X0 + (starts[i] + ends[i]) / 2.0)
    width.append(int(ends[i] - starts[i]))

rows = np.array(rows); cent = np.array(cent); width = np.array(width, float)
np.save(f"{OUT}/corridor_rows.npy", rows)
np.save(f"{OUT}/corridor_centre.npy", cent)
np.save(f"{OUT}/corridor_width.npy", width)

print(f"corridor search canvas x{CORR_X0}-{CORR_X1}, rows {Y0}-{Y1}")
print("  row   widest-blank-run  centre   current-boundary")
for y in range(6400, 11200, 200):
    i = y - Y0
    c = cent[i]
    print(f" {y:6d}   {width[i]:8.0f} px      {c:7.1f}   {frontier[y]:8d}")
bad = int((width < 40).sum())
print(f"\nrows with < 40 px of jointly-blank corridor: {bad} of {len(rows)}")

# context view with the CURRENT boundary drawn
vis = master.copy()
for y in range(H):
    fx = int(frontier[Y0 + y]) - X0
    if 0 <= fx < W:
        vis[y, max(fx - 2, 0):fx + 3] = (0, 0, 255)
sc = 0.42
cv2.imwrite(f"{OUT}/ctx_current_boundary.jpg",
            cv2.resize(vis, None, fx=sc, fy=sc, interpolation=cv2.INTER_AREA),
            [cv2.IMWRITE_JPEG_QUALITY, 92])
print(f"wrote {OUT}/ctx_current_boundary.jpg  (window x{X0}-{X1} y{Y0}-{Y1}, {sc:.2f}x)")
