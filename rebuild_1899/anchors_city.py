#!/usr/bin/env python3
"""City-wide per-unit corridor anchors for the 1899 edition.

For each of the 90 coverage units: whiteness-profile corridor detection
inside the (gap-bridged) printed extent, with the EXPECTED corridor counts
and grid pitches from the unit's coverage span constraining the peak
assignment. Detected anchors are validated against every anchor the seed
already carries (wharf v/h anchors, line_overrides) and against the pitch.

Output: out/city_anchors.json
  units[uid] = {file, region, v: {slot: x}, h: {street: y}, extent,
                status: full|partial|failed, checks: [...]}
"""
import json
import os
from itertools import combinations

import cv2
import numpy as np

ROOT = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(ROOT)
os.chdir(REPO)
SEED = "work/seed_pipeline/SEED_1899"
COV = json.load(open(f"{SEED}/coverage_1899.json"))
AV_PITCH, ST_PITCH = 1006.0, 1169.0

def sheet_gray(fileno):
    return cv2.imread(f"work/sheets/1899/Galveston_1899_sheet_{fileno:02d}.jpg", 0)

def printed_extent(g, region):
    H, W = g.shape
    x0r, y0r, x1r, y1r = region if region else (0, 0, W, min(H, 4100))
    core = g[y0r:min(y1r, H - 155), x0r:x1r]
    def first_last(v, thr=0.008, max_gap=500):
        on = v > thr
        idx = np.where(on)[0]
        if len(idx) == 0:
            return (0, len(v) - 1)
        runs = []
        start = prev = idx[0]
        for i in idx[1:]:
            if i - prev > max_gap:
                runs.append((start, prev)); start = i
            prev = i
        runs.append((start, prev))
        lo, hi = max(runs, key=lambda r: r[1] - r[0])
        for r in runs:
            if 0 < lo - r[1] <= max_gap:
                lo = r[0]
            if 0 < r[0] - hi <= max_gap:
                hi = r[1]
        return int(lo), int(hi)
    colink = (core < 200).mean(axis=0)
    rowink = (core < 200).mean(axis=1)
    x0, x1 = first_last(colink)
    y0, y1 = first_last(rowink)
    return x0 + x0r, y0 + y0r, x1 + x0r, y1 + y0r

def corridor_peaks(frac, n, spacing, lo_lim, hi_lim, min_val=0.30):
    """n corridor centres with ~spacing between them inside [lo_lim, hi_lim].
    frac = fraction of bright (paper) pixels per row/col inside the extent."""
    k = np.ones(81) / 81
    s = np.convolve(frac, k, mode="same")
    s[:int(max(0, lo_lim))] = 0
    s[int(hi_lim):] = 0
    cands = []
    for i in np.argsort(s)[::-1]:
        if s[i] < min_val or len(cands) >= n + 5:
            break
        if all(abs(int(i) - c) >= spacing * 0.55 for c in cands):
            cands.append(int(i))
    if len(cands) < n:
        return None
    best, best_cost = None, None
    for combo in combinations(sorted(cands), n):
        gaps = np.diff(combo)
        if len(gaps) and (gaps.min() < spacing * 0.75 or gaps.max() > spacing * 1.3):
            continue
        cost = float(np.abs(np.array(gaps) - spacing).sum()) - 3000 * sum(s[c] for c in combo)
        if best_cost is None or cost < best_cost:
            best, best_cost = combo, cost
    if best is None:
        return None
    def refine(p):
        thr = s[p] * 0.6
        lo = p
        while lo > 0 and s[lo] >= thr:
            lo -= 1
        hi = p
        while hi < len(s) - 1 and s[hi] >= thr:
            hi += 1
        return (lo + hi) / 2.0
    return [refine(p) for p in best]

out = {}
n_full = n_partial = n_failed = 0
for uid, u in sorted(COV["units"].items()):
    g = sheet_gray(u["file"])
    if g is None:
        out[uid] = {"status": "failed", "why": "sheet missing"}
        n_failed += 1
        continue
    region = u.get("region")
    x0, y0, x1, y1 = printed_extent(g, region)
    ins = 140
    sub = g[y0:y1, x0:x1]
    thr = np.percentile(sub, 70) - 6
    bright = (sub > thr).astype(np.float32)
    rec = {"file": u["file"], "region": region, "extent": [x0, y0, x1, y1],
           "v": {}, "h": {}, "checks": []}

    slots = u.get("av_slots") or []
    sts = u.get("st") or None
    # verticals
    if len(slots) >= 2:
        vx = corridor_peaks(bright.mean(axis=0), len(slots), AV_PITCH,
                            ins, (x1 - x0) - ins)
        if vx:
            for slot, x in zip(slots, vx):
                rec["v"][str(slot)] = round(x + x0, 1)
    elif len(slots) == 1 and u.get("v_anchors"):
        for slot, x in u["v_anchors"].items():
            rec["v"][str(slot)] = float(x)
    # horizontals
    if sts:
        n_st = sts[1] - sts[0] + 1
        hy = corridor_peaks(bright.mean(axis=1), n_st, ST_PITCH,
                            ins, (y1 - y0) - ins)
        if hy:
            for stn, y in zip(range(sts[0], sts[1] + 1), hy):
                rec["h"][str(stn)] = round(y + y0, 1)
    if u.get("h_anchors"):
        for stn, y in u["h_anchors"].items():
            det = rec["h"].get(str(stn))
            if det is not None:
                rec["checks"].append({"h": stn, "seed": y, "detected": det,
                                      "diff": round(det - y, 1)})
            rec["h"][str(stn)] = float(y)          # seed wins
    for ax, table in (("x", "v"), ("y", "h")):
        for key, val in (u.get("line_overrides", {}).get(ax, {}) or {}).items():
            det = rec[table].get(str(key))
            if det is not None:
                rec["checks"].append({ax: key, "seed": val, "detected": det,
                                      "diff": round(det - val, 1)})
            rec[table][str(key)] = float(val)
    got_v, got_h = len(rec["v"]), len(rec["h"])
    want_v = max(1, len(slots))
    want_h = (sts[1] - sts[0] + 1) if sts else 0
    if got_v >= want_v and got_h >= max(2, want_h - 0):
        rec["status"] = "full"
        n_full += 1
    elif got_v and got_h >= 2:
        rec["status"] = "partial"
        n_partial += 1
    else:
        rec["status"] = "failed"
        n_failed += 1
    out[uid] = rec

json.dump({"pitches": {"avenue": AV_PITCH, "street": ST_PITCH},
           "excluded": COV["excluded"], "units": out},
          open(os.path.join(ROOT, "out", "city_anchors.json"), "w"), indent=1)
print(f"full {n_full}  partial {n_partial}  failed {n_failed}")
bad_checks = []
for uid, r in out.items():
    for c in r.get("checks", []):
        if abs(c["diff"]) > 40:
            bad_checks.append((uid, c))
print("validation checks with |diff|>40px:", bad_checks if bad_checks else "none")
for uid, r in sorted(out.items()):
    if r.get("status") != "full":
        print(" ", uid, r.get("status"), "v", len(r.get("v", {})), "h", len(r.get("h", {})),
              (COV["units"][uid].get("note") or "")[:50])
EOF_MARKER_NOT_USED = None
