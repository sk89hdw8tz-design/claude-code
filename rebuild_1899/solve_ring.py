#!/usr/bin/env python3
"""Incremental ring solve for the 1899 city.

The gated downtown rev2 transforms are FROZEN (they passed a held-out
landmark gate; nothing the outer city says should move them). Every other
unit is placed by a robust per-unit similarity fit against its already-
placed neighbours, breadth-first outward from downtown. Placed units never
move, so a bad lock in a vacant outlot stays local and gets flagged instead
of bending the whole network.

Per-unit sanity: scale within 2.5% of its matched neighbours' mean, theta
within 1.8 deg of their median; a unit failing sanity or lacking 3 usable
correspondences is placed by the seam-line prior (translation only,
neighbour's rotation/scale) and FLAGGED for adjudication.

Writes out/affine_city_1899.json + out/ring_report.json.
"""
import json
import os
from collections import deque

import numpy as np

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "out")

NET = json.load(open(os.path.join(OUT, "city_network.json")))
CITY = json.load(open(os.path.join(OUT, "city_measurements.json")))
DOWN = json.load(open(os.path.join(OUT, "r1_measurements.json")))
CORE = json.load(open(os.path.join(REPO_TRANSFORMS := os.path.join(
    os.path.dirname(ROOT), "outputs", "1899", "recipe", "transforms.json"))))["sheets"]

UNITS = NET["units"]
matches_by_pair = {}
for src in (CITY["seam_matches"], DOWN["seam_matches"]):
    for pair, recs in src.items():
        if recs:
            matches_by_pair.setdefault(pair, []).extend(
                [(r["a_xy"], r["b_xy"]) for r in recs])

nbr_pairs = {}
for p in NET["pairs"]:
    nbr_pairs.setdefault(p["owner"], []).append(p)
    nbr_pairs.setdefault(p["nbr"], []).append(p)

placed = {}
flags = {}
for uid, s in CORE.items():
    if uid in UNITS:
        placed[uid] = {"m": np.array(s["m"], float), "t": np.array(s["t"], float),
                       "how": "frozen-downtown"}
print(f"frozen core: {sorted(placed)}")

def correspondences(uid):
    """[(native_xy_on_uid, global_xy)] via placed neighbours."""
    out = []
    used_pairs = []
    for p in nbr_pairs.get(uid, []):
        other = p["nbr"] if p["owner"] == uid else p["owner"]
        if other not in placed:
            continue
        key = f"{p['owner']}|{p['nbr']}"
        recs = matches_by_pair.get(key, [])
        if not recs:
            continue
        Mo, to = placed[other]["m"], placed[other]["t"]
        n_used = 0
        for a_xy, b_xy in recs:
            if p["owner"] == uid:
                mine, theirs = a_xy, b_xy
            else:
                mine, theirs = b_xy, a_xy
            g = Mo @ np.array(theirs, float) + to
            out.append((np.array(mine, float), g))
            n_used += 1
        used_pairs.append((key, n_used))
    return out, used_pairs

def fit_similarity(cor):
    A = np.array([c[0] for c in cor])
    B = np.array([c[1] for c in cor])
    w = np.ones(len(A))
    res = np.full(len(A), 1e9)
    for _ in range(6):
        if w.sum() < 1e-6:
            return np.eye(2), np.zeros(2), 1e9, 0
        ca = (A * w[:, None]).sum(0) / w.sum()
        cb = (B * w[:, None]).sum(0) / w.sum()
        A0, B0 = A - ca, B - cb
        H = (A0 * w[:, None]).T @ B0
        den = ((A0 ** 2) * w[:, None]).sum()
        if not np.isfinite(H).all() or den < 1e-6:
            return np.eye(2), np.zeros(2), 1e9, 0
        try:
            U, S, Vt = np.linalg.svd(H)
        except np.linalg.LinAlgError:
            return np.eye(2), np.zeros(2), 1e9, 0
        R = Vt.T @ U.T
        if np.linalg.det(R) < 0:
            Vt[-1] *= -1
            R = Vt.T @ U.T
        s = S.sum() / den
        t = cb - s * R @ ca
        res = np.hypot(*(((s * (R @ A0.T)).T + cb) - B).T)
        w = np.where(res <= 6, 1.0, np.sqrt(6 / np.maximum(res, 1e-9)))
        w = np.where(res > 60, 0.0, w)
    keep = w > 0
    if not keep.any():
        return np.eye(2), np.zeros(2), 1e9, 0
    return s * R, t, float(np.median(res[keep])), int(keep.sum())

def neighbour_stats(uid):
    ths, scs, ref = [], [], None
    for p in nbr_pairs.get(uid, []):
        other = p["nbr"] if p["owner"] == uid else p["owner"]
        if other in placed:
            M = placed[other]["m"]
            ths.append(np.degrees(np.arctan2(M[1, 0], M[0, 0])))
            scs.append(np.hypot(M[0, 0], M[1, 0]))
            ref = ref or (other, p)
    return (float(np.median(ths)) if ths else 0.0,
            float(np.mean(scs)) if scs else 1.0, ref)

def prior_place(uid):
    """Translation from the seam-line estimate against one placed neighbour;
    rotation/scale = that neighbour's."""
    nth, nsc, ref = neighbour_stats(uid)
    other, p = ref
    Mo, to = placed[other]["m"], placed[other]["t"]
    th = np.radians(nth)
    M = nsc * np.array([[np.cos(th), -np.sin(th)], [np.sin(th), np.cos(th)]])
    # align the shared line estimate: owner_native on uid maps where
    # nbr_native maps on the neighbour; complete translation from unit offsets
    est = np.array(UNITS[uid]["offsets"], float)
    est_o = np.array(UNITS[other]["offsets"], float)
    delta = (Mo @ np.zeros(2) + to) - (est_o)          # neighbour's frame shift
    t = est + delta
    return M, t

order_pool = set(UNITS) - set(placed)
report = {}
while order_pool:
    # frontier: most correspondences to placed first
    frontier = []
    for uid in order_pool:
        cor, used = correspondences(uid)
        frontier.append((len(cor), uid, cor, used))
    frontier.sort(key=lambda f: -f[0])
    n_cor, uid, cor, used = frontier[0]
    order_pool.discard(uid)
    nth, nsc, ref = neighbour_stats(uid)
    if ref is None:
        # no placed neighbour yet: defer unless nothing else remains
        if any(f[0] > 0 for f in frontier[1:]):
            order_pool.add(uid)
            # rotate: place the best-connected other unit first
            n2, uid2, cor2, used2 = next(f for f in frontier[1:] if f[0] > 0)
            order_pool.discard(uid2)
            n_cor, uid, cor, used = n2, uid2, cor2, used2
            nth, nsc, ref = neighbour_stats(uid)
        else:
            report[uid] = {"how": "isolated-prior", "n": 0}
            M, t = np.eye(2), np.array(UNITS[uid]["offsets"], float)
            placed[uid] = {"m": M, "t": t, "how": "isolated-prior"}
            flags[uid] = "no placed neighbour"
            continue
    if n_cor >= 3:
        M, t, med, kept = fit_similarity(cor)
        th = float(np.degrees(np.arctan2(M[1, 0], M[0, 0])))
        sc = float(np.hypot(M[0, 0], M[1, 0]))
        ok = (abs(sc - nsc) <= 0.025 * nsc and abs(th - nth) <= 1.8
              and med <= 20 and kept >= 3)
        if ok:
            placed[uid] = {"m": M, "t": t, "how": f"fit(n={kept},med={med:.1f})"}
            report[uid] = {"how": "fit", "n": kept, "med": round(med, 1),
                           "theta": round(th, 2), "scale": round(sc, 4),
                           "pairs": used}
            continue
        flags[uid] = (f"fit rejected: med={med:.1f} kept={kept} "
                      f"theta={th:.2f} (nbr {nth:.2f}) scale={sc:.4f} (nbr {nsc:.4f})")
    else:
        flags[uid] = f"only {n_cor} correspondences"
    M, t = prior_place(uid)
    placed[uid] = {"m": M, "t": t, "how": "prior"}
    report[uid] = {"how": "prior", "n": n_cor, "flag": flags[uid]}

n_fit = sum(1 for r in report.values() if r["how"] == "fit")
print(f"placed {len(placed)} units: {len(CORE)} frozen, {n_fit} fitted, "
      f"{len(flags)} flagged/prior")
for uid, f in sorted(flags.items()):
    print(f"  FLAG {uid}: {f}")

aff = {uid: {"m": [[float(v) for v in row] for row in p["m"]],
             "t": [float(v) for v in p["t"]],
             "how": p["how"]} for uid, p in placed.items()}
json.dump({
 "convention": {
  "model": "similarity per unit; frozen gated downtown core + incremental ring placement",
  "frame": "ground grid: x = avenue_slot*1006, y = street_index*1169 (downtown-flat; the island grid bends south, absolute rotations drift legitimately)",
 },
 "sheets": aff,
}, open(os.path.join(OUT, "affine_city_1899.json"), "w"), indent=1)
json.dump({"report": report, "flags": flags},
          open(os.path.join(OUT, "ring_report.json"), "w"), indent=1)
print("wrote affine_city_1899.json (ring) + ring_report.json")
