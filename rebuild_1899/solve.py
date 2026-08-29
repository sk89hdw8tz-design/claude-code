#!/usr/bin/env python3
"""Bundle adjustment over the 19 seams' dense matches.

Model per sheet: axis-aligned affine  x' = sx*x + tx,  y' = sy*y + ty.
No rotation term — the gate's knot format is axis-separable, and holding the
model to what the gate can represent exactly keeps the check honest. If the
per-pair residuals show a rotation signature (dy varying linearly with x
along a horizontal seam), that is reported, not hidden.

Gauge: sheet 13 fixed at scale 1, translation = its anchor offset, so the
global frame stays the anchor ground frame (x = slot*1006, y = street*1169).

Soft priors: scale ~ N(1, 0.004); translation ~ N(anchor_offset, 120 px).
Robust loss: Huber (delta 6 px) via IRLS.

Inputs:  out/r1_measurements.json   (dense matches; landmarks NOT used here)
Outputs: out/registration.json      (landmark_check.py format)
         out/transforms_1899.json   (recipe format, 1912-style convention)
         out/solve_report.json
"""
import json
import os

import numpy as np

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "out")
M = json.load(open(os.path.join(OUT, "r1_measurements.json")))

SHEETS = sorted(M["anchor_offsets"])
GAUGE = "13"
IDX = {s: i for i, s in enumerate(SHEETS)}
NP = 4  # sx, sy, tx, ty per sheet

matches = []
for pair, recs in M["seam_matches"].items():
    a, b = pair.split("|")
    for r in recs:
        matches.append((a, b, r["a_xy"][0], r["a_xy"][1],
                        r["b_xy"][0], r["b_xy"][1], r["score"]))
print(f"{len(matches)} matches over {len(M['seam_matches'])} pairs")

x0 = np.zeros(len(SHEETS) * NP)
for s in SHEETS:
    ox, oy = M["anchor_offsets"][s]
    x0[IDX[s]*NP:IDX[s]*NP+4] = [1.0, 1.0, ox, oy]

def unpack(x, s):
    sx, sy, tx, ty = x[IDX[s]*NP:IDX[s]*NP+4]
    return sx, sy, tx, ty

def residuals(x):
    res, rows = [], []
    for (a, b, ax, ay, bx, by, sc) in matches:
        sxa, sya, txa, tya = unpack(x, a)
        sxb, syb, txb, tyb = unpack(x, b)
        rx = (sxa*ax + txa) - (sxb*bx + txb)
        ry = (sya*ay + tya) - (syb*by + tyb)
        res.append((rx, ry))
        rows.append((a, b, ax, ay, bx, by))
    return np.array(res), rows

def solve():
    x = x0.copy()
    n = len(x)
    for it in range(8):
        # linear system: unknown deltas around current x (model is linear in
        # params, so this converges in one step per reweighting)
        A, bvec, w = [], [], []
        res, _ = residuals(x)
        stepn = np.hypot(res[:, 0], res[:, 1])
        huber = np.where(stepn <= 6.0, 1.0, np.sqrt(6.0 / np.maximum(stepn, 1e-9)))
        for k, (a, b, ax, ay, bx, by, sc) in enumerate(matches):
            for axis in (0, 1):
                row = np.zeros(n)
                ia, ib = IDX[a]*NP, IDX[b]*NP
                if axis == 0:
                    row[ia+0] = ax; row[ia+2] = 1.0
                    row[ib+0] = -bx; row[ib+2] = -1.0
                else:
                    row[ia+1] = ay; row[ia+3] = 1.0
                    row[ib+1] = -by; row[ib+3] = -1.0
                A.append(row); bvec.append(0.0); w.append(huber[k])
        # priors
        for s in SHEETS:
            i = IDX[s]*NP
            ox, oy = M["anchor_offsets"][s]
            for (j, target, sigma) in ((0, 1.0, 0.004), (1, 1.0, 0.004),
                                       (2, ox, 120.0), (3, oy, 120.0)):
                row = np.zeros(n); row[i+j] = 1.0
                A.append(row); bvec.append(target); w.append(1.0/sigma)
        # gauge: sheet 13 pinned hard
        i = IDX[GAUGE]*NP
        ox, oy = M["anchor_offsets"][GAUGE]
        for (j, target) in ((0, 1.0), (1, 1.0), (2, ox), (3, oy)):
            row = np.zeros(n); row[i+j] = 1.0
            A.append(row); bvec.append(target); w.append(1e6)
        A = np.array(A); bvec = np.array(bvec); w = np.array(w)
        Aw = A * w[:, None]; bw = bvec * w
        x_new, *_ = np.linalg.lstsq(Aw, bw, rcond=None)
        if np.max(np.abs(x_new - x)) < 1e-9:
            x = x_new
            break
        x = x_new
    return x

x = solve()
res, _ = residuals(x)
stepn = np.hypot(res[:, 0], res[:, 1])
print(f"seam-match residuals: median {np.median(stepn):.1f} px, "
      f"p90 {np.percentile(stepn, 90):.1f}, max {stepn.max():.1f}")

# per-pair residual summary + rotation signature check
pair_stats = {}
for k, (a, b, ax, ay, bx, by, sc) in enumerate(matches):
    pair_stats.setdefault(f"{a}|{b}", []).append((ax, ay, res[k][0], res[k][1]))
report_pairs = {}
for pair, rows in sorted(pair_stats.items()):
    arr = np.array(rows)
    rx, ry = arr[:, 2], arr[:, 3]
    # rotation signature: correlate cross-residual with along-seam coordinate
    along = arr[:, 0] if abs(arr[:, 0].std()) > abs(arr[:, 1].std()) else arr[:, 1]
    sig = 0.0
    if along.std() > 1:
        cross = ry if along is arr[:, 0] else rx
        sig = float(np.polyfit(along, cross, 1)[0] * 3400)  # px across a sheet
    report_pairs[pair] = {
        "n": len(rows),
        "median_step": float(np.median(np.hypot(rx, ry))),
        "max_step": float(np.hypot(rx, ry).max()),
        "rotation_signature_px_per_sheet": round(sig, 1),
    }
    print(f"  {pair:7} n={len(rows):3d} med={report_pairs[pair]['median_step']:5.1f} "
          f"max={report_pairs[pair]['max_step']:5.1f} rot_sig={sig:+6.1f}px/sheet")

# ---- emit landmark_check registration.json (2 knots per axis, exact) ----
units = {}
for s in SHEETS:
    sx, sy, tx, ty = unpack(x, s)
    units[s] = {
        "knots": {
            "xkn": [0.0, 3400.0], "xkg": [tx, sx*3400 + tx],
            "ykn": [0.0, 4100.0], "ykg": [ty, sy*4100 + ty],
        },
        "fit": {"sx": float(sx), "sy": float(sy)},
    }
json.dump({"units": units}, open(os.path.join(OUT, "registration.json"), "w"), indent=1)

# ---- recipe transforms (1912-style but axis-aligned) ----
tr = {
 "convention": {
  "model": "axis-aligned affine per sheet: p_global = (sx*x + tx, sy*y + ty), raster px, origin top-left",
  "frame": "ground grid frame: x = avenue_slot * 1006, y = street_index * 1169 (SEED_1899 constants); gauge sheet 13 = scale 1 at its anchor offset",
  "no_rotation": "rotation withheld from the model so the landmark gate's axis-separable knots represent the build exactly; per-pair rotation signatures are reported in solve_report.json"
 },
 "sheets": {s: dict(zip(("sx", "sy", "tx", "ty"), map(float, unpack(x, s)))) for s in SHEETS},
}
json.dump(tr, open(os.path.join(OUT, "transforms_1899.json"), "w"), indent=1)
json.dump({
 "matches_used": len(matches),
 "residuals": {"median": float(np.median(stepn)), "p90": float(np.percentile(stepn, 90)), "max": float(stepn.max())},
 "pairs": report_pairs,
}, open(os.path.join(OUT, "solve_report.json"), "w"), indent=1)
print("wrote registration.json, transforms_1899.json, solve_report.json")
