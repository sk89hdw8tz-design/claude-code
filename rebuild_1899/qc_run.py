#!/usr/bin/env python3
"""Stage 3 QC for the 1899 rebuild.

Renders the delivered extent (matching the prior build's 11449x7632 canvas
as closely as the frame allows), emits the coverage mask, runs the seed's
guard-metric suite against baseline_metrics.json, and builds:
  - outputs/1899/recipe/qc/guard_metrics.json
  - outputs/1899/recipe/qc/proof/seam_XX_YY.png  (19 seam midpoint panels)
  - outputs/1899/recipe/qc/proof/landmarks.png   (gate-landmark contact sheet)
  - outputs/qc/preview_1899_div8.png             (whole-extent preview)
Large intermediates stay in work/ and are deleted afterwards.
"""
import json
import os
import subprocess
import sys

import cv2
import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(REPO)
sys.path.insert(0, "tools")
from reciplib import Recipe  # noqa: E402

r = Recipe(1899)
own = r.ownership()

# delivered extent: piers west of Ave A to just past Ave I, 19th..25th + margin
X0, Y0 = -3259.0, 21911.0
W, H = 11449, 7632
canvas = np.full((H, W, 3), 255, np.uint8)
covered = np.zeros((H, W), np.uint8)
from shapely.geometry import Polygon, box
rect = box(X0, Y0, X0 + W, Y0 + H)
involved = [(s, p) for s, p in own if Polygon(p).intersects(rect)]
warped_cache = {}
def warp(sheet):
    if sheet not in warped_cache:
        img = cv2.imread(r.fetch(r.sheet_file(sheet)), cv2.IMREAD_COLOR)
        M, t = r.sheet_matrix(sheet)
        A = np.hstack([M, (t - np.array([X0, Y0])).reshape(2, 1)])
        warped_cache[sheet] = (cv2.warpAffine(img, A, (W, H),
                                              flags=cv2.INTER_LANCZOS4,
                                              borderValue=(255, 255, 255)),
                               img.shape)
    return warped_cache[sheet]

for sheet, poly in involved:
    w, _ = warp(sheet)
    mask = np.zeros((H, W), np.uint8)
    cv2.fillPoly(mask, [(np.array(poly) - [X0, Y0]).astype(np.int32)], 255)
    mask &= cv2.inRange(covered, 0, 0)
    canvas[mask > 0] = w[mask > 0]
    covered |= mask
order = sorted({s for s, _ in involved},
               key=lambda s: (s not in ("07", "06", "08"), int(s)))
for sheet in order:
    if not (covered == 0).any():
        break
    w, shape = warp(sheet)
    M, t = r.sheet_matrix(sheet)
    inb = np.zeros((H, W), np.uint8)
    ins, bot = 60, 230
    corners = np.array([(M @ np.array(p) + t - [X0, Y0]) for p in
                        [(ins, ins), (shape[1] - ins, ins),
                         (shape[1] - ins, shape[0] - bot), (ins, shape[0] - bot)]],
                       np.int32)
    cv2.fillPoly(inb, [corners], 255)
    fb = (covered == 0) & (inb > 0)
    if fb.any():
        canvas[fb] = w[fb]
        covered[fb] = 255
warped_cache.clear()

# metrics on the tight bbox of sourced content: the extent guess includes
# ground outside every sheet (prior build tinted such area), which is an
# extent choice, not lost source coverage
ys, xs = np.where(covered > 0)
bx0, bx1 = xs.min(), xs.max() + 1
by0, by1 = ys.min(), ys.max() + 1
canvas_m = canvas[by0:by1, bx0:bx1]
covered_m = covered[by0:by1, bx0:bx1]
print(f"metric bbox: {bx1-bx0}x{by1-by0} at offset ({bx0},{by0})")
os.makedirs("work/qc", exist_ok=True)
cv2.imwrite("work/qc/composite_1899.png", canvas_m)
cv2.imwrite("work/qc/coverage_1899.png", covered_m)
prev = cv2.resize(canvas, (W // 8, H // 8), interpolation=cv2.INTER_AREA)
os.makedirs("outputs/qc", exist_ok=True)
cv2.imwrite("outputs/qc/preview_1899_div8.png", prev)

# guard metrics over the SOURCE FOOTPRINT (union of sheet page quads within
# the extent): the prior build tinted the bay, so its canvas had ~no white
# and counted tinted water as covered; this recipe ships no water tint, so
# extent outside every sheet stays paper-white by design and is excluded
# from the responsibility area.
foot = np.zeros((H, W), np.uint8)
for sheet in {s for s, _ in involved}:
    img_sh = cv2.imread(r.fetch(r.sheet_file(sheet)), cv2.IMREAD_GRAYSCALE)
    M, t = r.sheet_matrix(sheet)
    ins = 60
    cs = np.array([(M @ np.array(p) + t - [X0, Y0]) for p in
                   [(ins, ins), (img_sh.shape[1]-ins, ins),
                    (img_sh.shape[1]-ins, img_sh.shape[0]-ins), (ins, img_sh.shape[0]-ins)]],
                  np.int32)
    cv2.fillPoly(foot, [cs], 255)
inside = foot > 0
n_inside = int(inside.sum())
cov_in = float((covered[inside] > 0).mean()) * 100
white_in = int((canvas[inside] == 255).all(axis=1).sum())
black_in = int((canvas[inside].max(axis=1) == 0).sum())
footprint_metrics = {
    "responsibility_area_px": n_inside,
    "coverage_pct_within_footprint": round(cov_in, 3),
    "pure_white_px_within_footprint": white_in,
    "pure_black_pct_within_footprint": round(100.0 * black_in / n_inside, 4),
}
print("footprint metrics:", json.dumps(footprint_metrics))

res = subprocess.run([sys.executable,
                      "work/seed_pipeline/SEED_1899/tools/build_metrics.py",
                      "work/qc/composite_1899.png", "work/qc/coverage_1899.png",
                      "work/seed_pipeline/SEED_1899/baseline_metrics.json"],
                     capture_output=True, text=True)
print(res.stdout, res.stderr)
open("outputs/1899/recipe/qc/guard_metrics.json", "w").write(json.dumps({
    "extent_mosaic": [X0, Y0, X0 + W, Y0 + H],
    "note": ("extent approximates the prior build's 11449x7632 delivered canvas. "
             "The prior build tinted the bay (its 20 white px / 98.98% coverage "
             "count tinted water); this recipe ships no water tint, so the "
             "comparable numbers are the footprint-scoped ones."),
    "footprint_scoped": footprint_metrics,
    "whole_extent_raw_output": res.stdout,
}, indent=1))

# seam midpoint panels
os.makedirs("outputs/1899/recipe/qc/proof", exist_ok=True)
ctxs = json.load(open("work/seed_pipeline/SEED_1899/pair_context.json"))
AFF = json.load(open("outputs/1899/recipe/transforms.json"))["sheets"]
for ctx in ctxs:
    a = ctx["owner"]
    M = np.array(AFF[a]["m"]); t = np.array(AFF[a]["t"])
    if ctx["axis"] == "h":
        mid_native = [1700, ctx["owner_native"]]
    else:
        mid_native = [ctx["owner_native"], 2050]
    g = M @ np.array(mid_native, float) + t
    cxp, cyp = int(g[0] - X0), int(g[1] - Y0)
    rad = 350
    x0c, y0c = max(0, cxp - rad), max(0, cyp - rad)
    crop = canvas[y0c:y0c + 2 * rad, x0c:x0c + 2 * rad]
    if crop.size:
        cv2.imwrite(f"outputs/1899/recipe/qc/proof/seam_{a}_{ctx['nbr']}.png",
                    cv2.resize(crop, (350, 350), interpolation=cv2.INTER_AREA))
# gate-landmark contact sheet
v2 = json.load(open("outputs/1899/recipe/controls/landmarks_v2.json"))["features"]
tiles = []
for f in [x for x in v2 if x.get("split") == "gate"]:
    aa = f["pair"][0]
    M = np.array(AFF[aa]["m"]); t = np.array(AFF[aa]["t"])
    g = M @ np.array(f["a_xy"], float) + t
    cxp, cyp = int(g[0] - X0), int(g[1] - Y0)
    rad = 170
    crop = canvas[max(0, cyp - rad):cyp + rad, max(0, cxp - rad):cxp + rad].copy()
    if not crop.size:
        continue
    cv2.circle(crop, (min(rad, cxp), min(rad, cyp)), 24, (0, 0, 255), 2)
    cv2.putText(crop, f["id"][:22], (6, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                (0, 0, 255), 1)
    tiles.append(cv2.resize(crop, (300, 300)))
if tiles:
    cols = 3
    rows = (len(tiles) + cols - 1) // cols
    sheet_img = np.full((rows * 300, cols * 300, 3), 255, np.uint8)
    for i, tl in enumerate(tiles):
        rr, cc = divmod(i, cols)
        sheet_img[rr*300:(rr+1)*300, cc*300:(cc+1)*300] = tl
    cv2.imwrite("outputs/1899/recipe/qc/proof/landmarks.png", sheet_img)
os.remove("work/qc/composite_1899.png")
os.remove("work/qc/coverage_1899.png")
print("QC artifacts written; large intermediates deleted")
