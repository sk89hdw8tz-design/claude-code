#!/usr/bin/env python3
"""Bundle adjustment, full-affine model.

Per sheet: p_global = M @ p_native + t, M = [[m00,m01],[m10,m11]] — absorbs
scan rotation and anisotropic paper stretch, both real on these scans (the
axis-aligned fit left 20-90 px/sheet rotation signatures).

Gauge: sheet 13 = identity matrix at its anchor offset.
Priors: diag ~ N(1, 0.012), off-diag ~ N(0, 0.02 ~= 1.1 deg), t ~ N(anchor,
150) — per-pair similarity fits show real relative rotations up to ~1 deg
and scales to +-1%, so the priors must leave room for them.
Huber IRLS (delta 5) + hard rejection of matches > 80 px after iteration 3.

Reads the match set from out/r1_measurements.json (overwritten by each
refine pass). Writes out/affine_1899.json + out/solve_report.json and an
axis-separable knots file out/registration.json for the UNMODIFIED seed gate
(disclosed approximation: knots drop the off-diagonal terms).
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
NP = 6  # m00 m01 m10 m11 tx ty

matches = []
for pair, recs in M["seam_matches"].items():
    a, b = pair.split("|")
    for r in recs:
        matches.append([a, b, r["a_xy"][0], r["a_xy"][1],
                        r["b_xy"][0], r["b_xy"][1], True, 1.0])
n_dense = len(matches)
# Landmark constraints come from the consolidated three-source set
# (landmarks_v2.json): only its FIT half; the GATE half never enters the
# solver, keeping gate.py an honest hold-out.
FIT_LM_IDS = []
LM2 = json.load(open(os.path.join(OUT, "landmarks_v2.json")))
for r in LM2["features"]:
    if r.get("split") == "fit":
        a, b = r["pair"]
        matches.append([a, b, r["a_xy"][0], r["a_xy"][1],
                        r["b_xy"][0], r["b_xy"][1], True, 3.0])
        FIT_LM_IDS.append(r["id"])
print(f"{n_dense} dense + {len(FIT_LM_IDS)} fit-landmark constraints "
      f"over {len(M['seam_matches'])} pairs")

x0 = np.zeros(len(SHEETS) * NP)
for s in SHEETS:
    ox, oy = M["anchor_offsets"][s]
    x0[IDX[s]*NP:IDX[s]*NP+6] = [1, 0, 0, 1, ox, oy]

def unpack(x, s):
    v = x[IDX[s]*NP:IDX[s]*NP+6]
    return v[0], v[1], v[2], v[3], v[4], v[5]

def residuals(x):
    out = []
    for m in matches:
        a, b, ax, ay, bx, by, live, wt = m
        A = unpack(x, a); B = unpack(x, b)
        rx = (A[0]*ax + A[1]*ay + A[4]) - (B[0]*bx + B[1]*by + B[4])
        ry = (A[2]*ax + A[3]*ay + A[5]) - (B[2]*bx + B[3]*by + B[5])
        out.append((rx, ry))
    return np.array(out)

def build_system(x, weights):
    n = len(x)
    rows_A, rows_b, rows_w = [], [], []
    for k, m in enumerate(matches):
        a, b, ax, ay, bx, by, live, wt = m
        if not live:
            continue
        ia, ib = IDX[a]*NP, IDX[b]*NP
        rx = np.zeros(n)
        rx[ia+0] = ax; rx[ia+1] = ay; rx[ia+4] = 1
        rx[ib+0] = -bx; rx[ib+1] = -by; rx[ib+4] = -1
        ry = np.zeros(n)
        ry[ia+2] = ax; ry[ia+3] = ay; ry[ia+5] = 1
        ry[ib+2] = -bx; ry[ib+3] = -by; ry[ib+5] = -1
        rows_A += [rx, ry]; rows_b += [0.0, 0.0]; rows_w += [weights[k]]*2
    for s in SHEETS:
        i = IDX[s]*NP
        ox, oy = M["anchor_offsets"][s]
        for (j, target, sigma) in ((0, 1.0, 0.012), (1, 0.0, 0.02),
                                   (2, 0.0, 0.02), (3, 1.0, 0.012),
                                   (4, ox, 150.0), (5, oy, 150.0)):
            r = np.zeros(len(x)); r[i+j] = 1
            rows_A.append(r); rows_b.append(target); rows_w.append(1.0/sigma)
    i = IDX[GAUGE]*NP
    ox, oy = M["anchor_offsets"][GAUGE]
    for (j, target) in ((0, 1.0), (1, 0.0), (2, 0.0), (3, 1.0), (4, ox), (5, oy)):
        r = np.zeros(len(x)); r[i+j] = 1
        rows_A.append(r); rows_b.append(target); rows_w.append(1e6)
    A = np.array(rows_A); bv = np.array(rows_b); w = np.array(rows_w)
    return A * w[:, None], bv * w

x = x0.copy()
for it in range(10):
    res = residuals(x)
    stepn = np.hypot(res[:, 0], res[:, 1])
    if it >= 3:
        for k, m in enumerate(matches):
            if stepn[k] > 80:
                m[6] = False
    w = np.where(stepn <= 5.0, 1.0, np.sqrt(5.0 / np.maximum(stepn, 1e-9)))
    w = w * np.array([m[7] for m in matches])
    w = np.where([m[6] for m in matches], w, 0.0)
    Aw, bw = build_system(x, w)
    x_new, *_ = np.linalg.lstsq(Aw, bw, rcond=None)
    delta = float(np.max(np.abs(x_new - x)))
    x = x_new
    if delta < 1e-10:
        break

res = residuals(x)
live = np.array([m[6] for m in matches])
stepn = np.hypot(res[:, 0], res[:, 1])
print(f"live matches {live.sum()}/{len(matches)}; residuals (live): "
      f"median {np.median(stepn[live]):.1f}, p90 {np.percentile(stepn[live], 90):.1f}, "
      f"max {stepn[live].max():.1f}")

pair_stats = {}
for k, m in enumerate(matches):
    a, b = m[0], m[1]
    pair_stats.setdefault(f"{a}|{b}", []).append((stepn[k], m[6]))
report_pairs = {}
for pair, rows in sorted(pair_stats.items()):
    lv = [s for s, ok in rows if ok]
    report_pairs[pair] = {
        "n_total": len(rows), "n_live": len(lv),
        "median_step": float(np.median(lv)) if lv else None,
        "max_step": float(max(lv)) if lv else None,
    }
    print(f"  {pair:7} n={len(lv):3d}/{len(rows):3d} "
          f"med={report_pairs[pair]['median_step'] and round(report_pairs[pair]['median_step'],1)} "
          f"max={report_pairs[pair]['max_step'] and round(report_pairs[pair]['max_step'],1)}")

aff = {s: {"m": [[float(v) for v in unpack(x, s)[0:2]],
                 [float(v) for v in unpack(x, s)[2:4]]],
           "t": [float(unpack(x, s)[4]), float(unpack(x, s)[5])]}
       for s in SHEETS}
json.dump({
 "convention": {
  "model": "p_global = m @ p_native + t; raster px, origin top-left",
  "frame": "ground grid: x = avenue_slot*1006, y = street_index*1169; gauge sheet 13 identity at anchor offset",
 },
 "sheets": aff,
}, open(os.path.join(OUT, "affine_1899.json"), "w"), indent=1)

# axis-separable knots for the unmodified seed gate (drops off-diagonals)
units = {}
for s in SHEETS:
    m00, m01, m10, m11, tx, ty = unpack(x, s)
    units[s] = {"knots": {"xkn": [0.0, 3400.0], "xkg": [tx, m00*3400 + tx],
                          "ykn": [0.0, 4100.0], "ykg": [ty, m11*4100 + ty]},
                "fit": {"sx": float(m00), "sy": float(m11)}}
json.dump({"units": units}, open(os.path.join(OUT, "registration.json"), "w"), indent=1)
json.dump({"matches_total": len(matches), "matches_live": int(live.sum()),
           "fit_landmark_ids": FIT_LM_IDS,
           "residuals_live": {"median": float(np.median(stepn[live])),
                              "p90": float(np.percentile(stepn[live], 90)),
                              "max": float(stepn[live].max())},
           "pairs": report_pairs},
          open(os.path.join(OUT, "solve_report.json"), "w"), indent=1)
print("wrote affine_1899.json, registration.json, solve_report.json")
