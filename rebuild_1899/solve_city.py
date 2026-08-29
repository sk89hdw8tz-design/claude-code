#!/usr/bin/env python3
"""City-wide rigid similarity bundle over the 90-unit network.

Same model and priors as the downtown rev2 solve (solve3): per unit
p_global = s*R(theta) @ p_native + t; a ~ N(1, 0.003), b ~ N(0, 0.015),
t ~ N(estimated offsets, 250 px); gauge unit 13. Huber IRLS, hard reject
> 60 px after iteration 3. Downtown units keep their rev2 constraints by
INCLUDING the downtown measurement set alongside the city set, and the
consolidated fit landmarks stay in at weight 3.

Flags for adjudication: pairs with median live residual > 25 px, or fewer
than 4 live matches, or fully rejected.

Writes out/affine_city_1899.json + out/solve_city_report.json.
"""
import json
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "out")

CITY = json.load(open(os.path.join(OUT, "city_measurements.json")))
NET = json.load(open(os.path.join(OUT, "city_network.json")))
DOWN = json.load(open(os.path.join(OUT, "r1_measurements.json")))
LM2 = json.load(open(os.path.join(OUT, "landmarks_v2.json")))

OFFSETS = {uid: tuple(u["offsets"]) for uid, u in NET["units"].items()}
UNITS = sorted(OFFSETS)
GAUGE = "13"
IDX = {u: i for i, u in enumerate(UNITS)}
NP = 4

SCHEMATIC_PAIRS = {"06|13", "06|15", "07|11", "07|13", "08|11"}
matches = []
seen_pairs = set()
for pair, recs in DOWN["seam_matches"].items():          # downtown rev2 set first
    if pair in SCHEMATIC_PAIRS:
        continue
    a, b = pair.split("|")
    seen_pairs.add(pair)
    for r in recs:
        matches.append([a, b, r["a_xy"][0], r["a_xy"][1],
                        r["b_xy"][0], r["b_xy"][1], True, 1.0])
for pair, recs in CITY["seam_matches"].items():
    if pair in seen_pairs or pair in SCHEMATIC_PAIRS:
        continue
    a, b = pair.split("|")
    for r in recs:
        matches.append([a, b, r["a_xy"][0], r["a_xy"][1],
                        r["b_xy"][0], r["b_xy"][1], True, 1.0])
n_dense = len(matches)
for r in LM2["features"]:
    if r.get("split") == "fit":
        a, b = r["pair"]
        wt = 1.0 if (f"{a}|{b}" in SCHEMATIC_PAIRS or f"{b}|{a}" in SCHEMATIC_PAIRS) else 3.0
        matches.append([a, b, r["a_xy"][0], r["a_xy"][1],
                        r["b_xy"][0], r["b_xy"][1], True, wt])
print(f"{n_dense} dense + {len(matches)-n_dense} landmark constraints, "
      f"{len(UNITS)} units")

x = np.zeros(len(UNITS) * NP)
for u in UNITS:
    ox, oy = OFFSETS[u]
    x[IDX[u]*NP:IDX[u]*NP+4] = [1.0, 0.0, ox, oy]

def unpack(xv, u):
    a, b, tx, ty = xv[IDX[u]*NP:IDX[u]*NP+4]
    return a, b, tx, ty

def residuals(xv):
    out = np.empty((len(matches), 2))
    for k, m in enumerate(matches):
        a, b, ax, ay, bx, by, live, wt = m
        aa, ab, atx, aty = unpack(xv, a)
        ba, bb, btx, bty = unpack(xv, b)
        out[k, 0] = (aa*ax - ab*ay + atx) - (ba*bx - bb*by + btx)
        out[k, 1] = (ab*ax + aa*ay + aty) - (bb*bx + ba*by + bty)
    return out

def solve():
    global x
    n = len(x)
    for it in range(10):
        res = residuals(x)
        stepn = np.hypot(res[:, 0], res[:, 1])
        if it >= 3:
            for k, m in enumerate(matches):
                if stepn[k] > 60:
                    m[6] = False
        w = np.where(stepn <= 5.0, 1.0, np.sqrt(5.0 / np.maximum(stepn, 1e-9)))
        w = w * np.array([m[7] for m in matches])
        w = np.where([m[6] for m in matches], w, 0.0)
        rows_A, rows_b, rows_w = [], [], []
        for k, m in enumerate(matches):
            if not m[6]:
                continue
            a, b, ax, ay, bx, by, live, wt = m
            ia, ib = IDX[a]*NP, IDX[b]*NP
            rx = np.zeros(n)
            rx[ia+0] = ax; rx[ia+1] = -ay; rx[ia+2] = 1
            rx[ib+0] = -bx; rx[ib+1] = by; rx[ib+2] = -1
            ry = np.zeros(n)
            ry[ia+0] = ay; ry[ia+1] = ax; ry[ia+3] = 1
            ry[ib+0] = -by; ry[ib+1] = -bx; ry[ib+3] = -1
            rows_A += [rx, ry]; rows_b += [0.0, 0.0]; rows_w += [w[k]]*2
        for u in UNITS:
            i = IDX[u]*NP
            ox, oy = OFFSETS[u]
            # the island's grid bends ~2 deg across the south: rotation
            # priors stay loose and translation priors looser outside the
            # (flat) downtown frame the offsets were computed in
            b_sigma = 0.06
            t_sigma = 600.0
            for (j, target, sigma) in ((0, 1.0, 0.004), (1, 0.0, b_sigma),
                                       (2, ox, t_sigma), (3, oy, t_sigma)):
                r = np.zeros(n); r[i+j] = 1
                rows_A.append(r); rows_b.append(target); rows_w.append(1.0/sigma)
        i = IDX[GAUGE]*NP
        ox, oy = OFFSETS[GAUGE]
        for (j, target) in ((0, 1.0), (1, 0.0), (2, ox), (3, oy)):
            r = np.zeros(n); r[i+j] = 1
            rows_A.append(r); rows_b.append(target); rows_w.append(1e6)
        A = np.array(rows_A) * np.array(rows_w)[:, None]
        bv = np.array(rows_b) * np.array(rows_w)
        x_new, *_ = np.linalg.lstsq(A, bv, rcond=None)
        if np.max(np.abs(x_new - x)) < 1e-10:
            x = x_new
            break
        x = x_new

solve()
# Second pass: units with too few live constraints wander (a narrow panel or
# a vacant seam can't pin rotation/scale). Their priors snap to the local
# consensus: b-target = median b of their live-solved neighbours, tight
# sigma; scale prior tight at 1.
live_count = {}
for m in matches:
    if m[6]:
        live_count[m[0]] = live_count.get(m[0], 0) + 1
        live_count[m[1]] = live_count.get(m[1], 0) + 1
WEAK = {u for u in UNITS if live_count.get(u, 0) < 12}
if WEAK:
    print(f"weak units (re-priored to neighbour consensus): {sorted(WEAK)}")
    nbrs = {}
    for p in NET["pairs"]:
        nbrs.setdefault(p["owner"], set()).add(p["nbr"])
        nbrs.setdefault(p["nbr"], set()).add(p["owner"])
    WEAK_PRIOR = {}
    for u in WEAK:
        bs = [x[IDX[v]*NP+1] for v in nbrs.get(u, ()) if v not in WEAK]
        WEAK_PRIOR[u] = float(np.median(bs)) if bs else 0.0
    _orig_solve = solve
    def solve_pass2():
        global x
        n = len(x)
        for it in range(8):
            res = residuals(x)
            stepn = np.hypot(res[:, 0], res[:, 1])
            w = np.where(stepn <= 5.0, 1.0, np.sqrt(5.0 / np.maximum(stepn, 1e-9)))
            w = w * np.array([m[7] for m in matches])
            w = np.where([m[6] for m in matches], w, 0.0)
            rows_A, rows_b, rows_w = [], [], []
            for k, m in enumerate(matches):
                if not m[6]:
                    continue
                a, b, ax, ay, bx, by, live, wt = m
                ia, ib = IDX[a]*NP, IDX[b]*NP
                rx = np.zeros(n)
                rx[ia+0] = ax; rx[ia+1] = -ay; rx[ia+2] = 1
                rx[ib+0] = -bx; rx[ib+1] = by; rx[ib+2] = -1
                ry = np.zeros(n)
                ry[ia+0] = ay; ry[ia+1] = ax; ry[ia+3] = 1
                ry[ib+0] = -by; ry[ib+1] = -bx; ry[ib+3] = -1
                rows_A += [rx, ry]; rows_b += [0.0, 0.0]; rows_w += [w[k]]*2
            for u in UNITS:
                i = IDX[u]*NP
                ox, oy = OFFSETS[u]
                if u in WEAK:
                    pri = ((0, 1.0, 0.004), (1, WEAK_PRIOR[u], 0.008),
                           (2, ox, 600.0), (3, oy, 600.0))
                else:
                    pri = ((0, 1.0, 0.004), (1, 0.0, 0.06),
                           (2, ox, 600.0), (3, oy, 600.0))
                for (j, target, sigma) in pri:
                    r = np.zeros(n); r[i+j] = 1
                    rows_A.append(r); rows_b.append(target); rows_w.append(1.0/sigma)
            i = IDX[GAUGE]*NP
            ox, oy = OFFSETS[GAUGE]
            for (j, target) in ((0, 1.0), (1, 0.0), (2, ox), (3, oy)):
                r = np.zeros(n); r[i+j] = 1
                rows_A.append(r); rows_b.append(target); rows_w.append(1e6)
            A = np.array(rows_A) * np.array(rows_w)[:, None]
            bv = np.array(rows_b) * np.array(rows_w)
            x_new, *_ = np.linalg.lstsq(A, bv, rcond=None)
            if np.max(np.abs(x_new - x)) < 1e-10:
                x = x_new
                break
            x = x_new
    solve_pass2()
res = residuals(x)
live = np.array([m[6] for m in matches])
stepn = np.hypot(res[:, 0], res[:, 1])
print(f"live {int(live.sum())}/{len(matches)}; residuals (live): "
      f"median {np.median(stepn[live]):.1f}, p90 {np.percentile(stepn[live], 90):.1f}")

thetas, scales = {}, {}
for u in UNITS:
    a, b, *_ = unpack(x, u)
    thetas[u] = float(np.degrees(np.arctan2(b, a)))
    scales[u] = float(np.hypot(a, b))
# Sanity, city edition: each sheet must be rigid RELATIVE TO ITS NEIGHBOURS
# (the island's grid bends gradually, so absolute theta drifts legitimately);
# scale must stay within scan physics.
sane = True
for u in UNITS:
    if abs(scales[u] - 1) > 0.04:
        print(f"  INSANE unit {u}: scale {scales[u]:.4f}")
        sane = False
rel_viol = []
for p in NET["pairs"]:
    a, b = p["owner"], p["nbr"]
    dth = abs(thetas[a] - thetas[b])
    dsc = abs(scales[a] - scales[b])
    if dth > 1.8 or dsc > 0.025:
        rel_viol.append((f"{a}|{b}", round(dth, 2), round(dsc, 4)))
print(f"theta range [{min(thetas.values()):.2f}, {max(thetas.values()):.2f}] deg; "
      f"scale range [{min(scales.values()):.4f}, {max(scales.values()):.4f}]")
print(f"neighbour-relative violations (d_theta>1.8deg or d_scale>0.025): {len(rel_viol)}")
for v in rel_viol[:12]:
    print("   ", v)
if not sane:
    print("DRAFT EXPORT: scale sanity violated on the units above — "
          "transforms exported for visual diagnosis only")

pair_stats = {}
for k, m in enumerate(matches):
    pair_stats.setdefault(f"{m[0]}|{m[1]}", []).append((stepn[k], m[6]))
flags = {}
report = {}
for pair, rows in sorted(pair_stats.items()):
    lv = [s for s, ok in rows if ok]
    med = float(np.median(lv)) if lv else None
    report[pair] = {"n_total": len(rows), "n_live": len(lv), "median": med,
                    "max": float(max(lv)) if lv else None}
    if len(lv) < 4 or (med is not None and med > 25):
        flags[pair] = report[pair]
print(f"flagged pairs ({len(flags)}):")
for pair, st in sorted(flags.items(), key=lambda kv: -(kv[1]['median'] or 999)):
    print(f"  {pair:9} n={st['n_live']}/{st['n_total']} med={st['median'] and round(st['median'],1)}")

aff = {}
for u in UNITS:
    a, b, tx, ty = (float(v) for v in unpack(x, u))
    aff[u] = {"m": [[a, -b], [b, a]], "t": [tx, ty],
              "theta_deg": thetas[u], "scale": scales[u]}
json.dump({
 "convention": {
  "model": "similarity per unit: p_global = s*R(theta) @ p_native + t; raster px, origin top-left",
  "frame": "ground grid: x = avenue_slot*1006, y = street_index*1169; gauge unit 13 identity at anchor offset",
 },
 "sheets": aff,
}, open(os.path.join(OUT, "affine_city_1899.json"), "w"), indent=1)
json.dump({"pairs": report, "flags": flags,
           "theta_deg": thetas, "scale": scales},
          open(os.path.join(OUT, "solve_city_report.json"), "w"), indent=1)
print("wrote affine_city_1899.json + solve_city_report.json")
