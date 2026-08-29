#!/usr/bin/env python3
"""Measure the 1912 street/avenue corridor grid in the mosaic frame.

Per sheet: brightness-profile peaks locate each corridor the sheet carries;
the sheet's solved transform maps them to the mosaic frame; per-corridor
medians across sheets give the grid, with spread reported as QC.

Writes outputs/1912/recipe/grid.json.
"""
import hashlib
import json
import os
import subprocess

import cv2
import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(REPO)

inv = json.load(open("outputs/1912/recipe/inventory.json"))
tr = json.load(open("outputs/1912/recipe/transforms.json"))["sheets"]
plates = {str(p["sheet"]): p for p in
          json.load(open("outputs/1912/recipe/plates/plate_structure.json"))["plates"]}

SHEET_IMG = {"7": 11, "8": 13, "9": 15, "10": 17, "11": 19, "12": 21,
             "39": 49, "40": 50, "43": 53, "44": 54, "49": 59, "50": 60}
# corridors per sheet: (avenue slots, street indices); A=0..K=10
COLS = {"7": [0, 1, 2], "9": [0, 1, 2], "11": [0, 1, 2],
        "8": [2, 3, 4, 5], "10": [2, 3, 4, 5], "12": [2, 3, 4, 5],
        "39": [5, 6, 7, 8], "43": [5, 6, 7, 8], "49": [5, 6, 7, 8],
        "40": [8, 9, 10], "44": [8, 9, 10], "50": [8, 9, 10]}
ROWS = {"7": [18, 19, 20, 21], "8": [18, 19, 20, 21], "39": [18, 19, 20, 21],
        "40": [18, 19, 20, 21],
        "9": [21, 22, 23, 24], "10": [21, 22, 23, 24], "43": [21, 22, 23, 24],
        "44": [21, 22, 23, 24],
        "11": [24, 25, 26, 27], "12": [24, 25, 26, 27], "49": [24, 25, 26, 27],
        "50": [24, 25, 26, 27]}

def materialize(sheet):
    f = f"sanborn08539_004_img{SHEET_IMG[sheet]:03d}_archival.jp2"
    p = f"work/sheets/1912/sheet{sheet}.jp2"
    if not os.path.exists(p):
        it = next(i for i in inv["items"] if i["file"] == f)
        data = subprocess.run(["git", "show",
                               f"origin/claude/galveston-1912-source-data:{it['mirror']['path']}"],
                              capture_output=True, check=True).stdout
        assert hashlib.sha256(data).hexdigest() == it["sha256"], f
        open(p, "wb").write(data)
    return cv2.imread(p, 0)

def profile_peaks(frac, n, lo_lim, hi_lim, spacing, min_dist=800, min_val=0.08):
    """Corridor centres: all candidate peaks inside [lo_lim, hi_lim], then the
    size-n subset that best matches the expected spacing."""
    from itertools import combinations
    k = np.ones(61) / 61
    s = np.convolve(frac, k, mode="same")
    s[:int(lo_lim)] = 0
    s[int(hi_lim):] = 0
    cands = []
    for i in np.argsort(s)[::-1]:
        if s[i] < min_val or len(cands) >= 9:
            break
        if all(abs(int(i) - c) >= min_dist for c in cands):
            cands.append(int(i))
    if len(cands) < n:
        return [], []
    best, best_cost = None, None
    for combo in combinations(sorted(cands), n):
        gaps = np.diff(combo)
        if len(gaps) and (gaps.min() < spacing * 0.6 or gaps.max() > spacing * 1.45):
            continue
        cost = float(np.abs(gaps - spacing).sum()) - 4000 * sum(s[c] for c in combo)
        if best_cost is None or cost < best_cost:
            best, best_cost = combo, cost
    if best is None:
        return [], []
    def refine(p):
        thr = s[p] * 0.6
        lo = p
        while lo > 0 and s[lo] >= thr:
            lo -= 1
        hi = p
        while hi < len(s) - 1 and s[hi] >= thr:
            hi += 1
        return (lo + hi) / 2.0
    return [refine(p) for p in best], [float(s[p]) for p in best]

def to_mosaic(sheet, xy):
    t = tr[sheet]["raw"]
    M = np.array([[t["a"], -t["b"]], [t["b"], t["a"]]])
    return M @ np.array(xy) + np.array([t["tx"], t["ty"]])

ave_obs = {}   # slot -> [mosaic x]
st_obs = {}    # street -> [mosaic y]
for sheet in SHEET_IMG:
    img = materialize(sheet)
    # paper tone varies per scan: bright = above the 75th percentile shifted
    # slightly down, which selects clean paper against washes and ink
    thr = np.percentile(img, 75) - 4
    H, W = img.shape
    q = np.array(plates[sheet]["page_quad_fullres"])
    x0, x1 = q[:, 0].min() + 320, q[:, 0].max() - 320
    y0, y1 = q[:, 1].min() + 320, q[:, 1].max() - 320
    inset = img[int(y0):int(y1), int(x0):int(x1)]
    bright = (inset > thr).astype(np.float32)
    cx, vals = profile_peaks(bright.mean(axis=0), len(COLS[sheet]),
                             0, inset.shape[1], 1900)
    cy, valsy = profile_peaks(bright.mean(axis=1), len(ROWS[sheet]),
                              0, inset.shape[0], 2150)
    cx = [c + x0 for c in cx]
    cy = [c + y0 for c in cy]
    got_c = len(cx) == len(COLS[sheet])
    got_r = len(cy) == len(ROWS[sheet])
    center = np.array([W / 2, H / 2])
    if got_c:
        for slot, x in zip(COLS[sheet], cx):
            mx = to_mosaic(sheet, [x, center[1]])[0]
            ave_obs.setdefault(slot, []).append(float(mx))
    if got_r:
        for st, y in zip(ROWS[sheet], cy):
            my = to_mosaic(sheet, [center[0], y])[1]
            st_obs.setdefault(st, []).append(float(my))
    print(f"sheet {sheet}: aves {'ok' if got_c else f'{len(cx)}/{len(COLS[sheet])}'} "
          f"streets {'ok' if got_r else f'{len(cy)}/{len(ROWS[sheet])}'}")

grid = {
 "frame": "1912 mosaic frame (sheet 10 raw pixels minus [3326, 3898])",
 "avenue_slots": "A=0 B=1 C=2 D=3 E=4 F=5 G=6 H=7 I=8 J=9(Broadway) K=10",
 "avenues": {}, "streets": {},
}
print("\navenue x (mosaic):")
for slot in sorted(ave_obs):
    xs = ave_obs[slot]
    med = float(np.median(xs)); spread = float(np.max(xs) - np.min(xs)) if len(xs) > 1 else 0.0
    grid["avenues"][str(slot)] = {"x": round(med, 1), "n": len(xs), "spread": round(spread, 1)}
    print(f"  slot {slot}: {med:8.1f}  n={len(xs)} spread={spread:.1f}")
print("street y (mosaic):")
for st in sorted(st_obs):
    ys = st_obs[st]
    med = float(np.median(ys)); spread = float(np.max(ys) - np.min(ys)) if len(ys) > 1 else 0.0
    grid["streets"][str(st)] = {"y": round(med, 1), "n": len(ys), "spread": round(spread, 1)}
    print(f"  {st}th: {med:8.1f}  n={len(ys)} spread={spread:.1f}")
json.dump(grid, open("outputs/1912/recipe/grid.json", "w"), indent=1)
print("wrote outputs/1912/recipe/grid.json")
