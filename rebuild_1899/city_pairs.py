#!/usr/bin/env python3
"""City-wide unit network for 1899: estimated anchors + pair contexts.

Anchors are ESTIMATES ONLY (seed values where the seed has them, otherwise
printed-extent margins + grid pitch): they seed the wide first matching
pass; the dense matches and the loop-closure audit carry the real geometry.
Adjacency is derived from the coverage spans and cross-checked against the
survey's printed edge references.

Writes out/city_network.json:
  units[uid] = {file, region, extent, offsets: [ox, oy], est_v, est_h}
  pairs = [{owner, nbr, axis, idx, owner_native, nbr_native, boundary}]
  edge_ref_mismatches = [...]
"""
import glob
import json
import os

import cv2
import numpy as np

ROOT = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(ROOT)
os.chdir(REPO)
SEED = "work/seed_pipeline/SEED_1899"
COV = json.load(open(f"{SEED}/coverage_1899.json"))
AV_PITCH, ST_PITCH = 1006.0, 1169.0
M_TOP, M_WEST = 230.0, 170.0     # typical printed-edge to first-corridor pads

def printed_extent(g, region):
    H, W = g.shape
    x0r, y0r, x1r, y1r = region if region else (0, 0, W, min(H, 4100))
    core = g[y0r:min(y1r, H - 155), x0r:x1r]
    def first_last(v, thr=0.008, max_gap=500):
        idx = np.where(v > thr)[0]
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

units = {}
for uid, u in sorted(COV["units"].items()):
    g = cv2.imread(f"work/sheets/1899/Galveston_1899_sheet_{u['file']:02d}.jpg", 0)
    if g is None:
        continue
    ext = printed_extent(g, u.get("region"))
    slots = u.get("av_slots") or []
    sts = u.get("st")
    est_v, est_h = {}, {}
    if u.get("v_anchors"):
        for k, v in u["v_anchors"].items():
            est_v[str(k)] = float(v)
    elif slots:
        for i, slot in enumerate(slots):
            est_v[str(slot)] = ext[0] + M_WEST + i * AV_PITCH
    if u.get("h_anchors"):
        for k, v in u["h_anchors"].items():
            est_h[str(k)] = float(v)
    elif sts:
        for i, stn in enumerate(range(sts[0], sts[1] + 1)):
            est_h[str(stn)] = ext[1] + M_TOP + i * ST_PITCH
    for ax, table in (("x", est_v), ("y", est_h)):
        for k, v in (u.get("line_overrides", {}).get(ax, {}) or {}).items():
            table[str(k)] = float(v)
    # translation offsets: ground = native + offset (mean over anchors)
    oxs = [int(k) * AV_PITCH - v for k, v in est_v.items()]
    oys = [int(k) * ST_PITCH - v for k, v in est_h.items()]
    units[uid] = {"file": u["file"], "region": u.get("region"),
                  "extent": list(ext), "slots": slots, "st": sts,
                  "est_v": est_v, "est_h": est_h,
                  "offsets": [float(np.mean(oxs)) if oxs else None,
                              float(np.mean(oys)) if oys else None]}

# survey edge refs, keyed by printed sheet number
edge_refs = {}
for p in sorted(glob.glob(f"{SEED}/survey/survey_batch_*.json")):
    for rec in json.load(open(p)):
        num = rec.get("sheet", rec.get("printed_number"))
        if num is None:
            continue
        edge_refs[int(num)] = rec.get("edge_refs", {})

pairs = []
mismatches = []
uids = sorted(units)
for i, a in enumerate(uids):
    ua = units[a]
    for b in uids[i + 1:]:
        ub = units[b]
        if ua["st"] is None or ub["st"] is None:
            continue
        st_a, st_b = ua["st"], ub["st"]
        sl_a, sl_b = ua["slots"], ub["slots"]
        sl_overlap = set(sl_a) & set(sl_b)
        st_overlap = min(st_a[1], st_b[1]) - max(st_a[0], st_b[0])
        # vertical boundary (shared avenue slot), same street row
        if sl_a and sl_b and st_overlap > 0:
            if sl_a[-1] == sl_b[0]:
                idx = sl_a[-1]
                pairs.append({"owner": a, "nbr": b, "axis": "v", "idx": idx,
                              "boundary": f"avenue slot {idx}",
                              "owner_native": ua["est_v"].get(str(idx)),
                              "nbr_native": ub["est_v"].get(str(idx))})
            elif sl_b[-1] == sl_a[0]:
                idx = sl_b[-1]
                pairs.append({"owner": b, "nbr": a, "axis": "v", "idx": idx,
                              "boundary": f"avenue slot {idx}",
                              "owner_native": ub["est_v"].get(str(idx)),
                              "nbr_native": ua["est_v"].get(str(idx))})
        # horizontal boundary (shared street), same column; corner-touching
        # units (interval overlap 0) are NOT neighbours
        iv_overlap = (min(sl_a[-1], sl_b[-1]) - max(sl_a[0], sl_b[0])) if (sl_a and sl_b) else 0
        single_col = bool(sl_overlap) and (len(sl_a) == 1 or len(sl_b) == 1)
        if iv_overlap >= 1 or single_col or (not sl_a) or (not sl_b):
            slot_gap_ok = iv_overlap >= 1 or single_col or not (sl_a and sl_b)
            if slot_gap_ok and st_a[1] == st_b[0]:
                idx = st_a[1]
                pairs.append({"owner": a, "nbr": b, "axis": "h", "idx": idx,
                              "boundary": f"street {idx}",
                              "owner_native": ua["est_h"].get(str(idx)),
                              "nbr_native": ub["est_h"].get(str(idx))})
            elif slot_gap_ok and st_b[1] == st_a[0]:
                idx = st_b[1]
                pairs.append({"owner": b, "nbr": a, "axis": "h", "idx": idx,
                              "boundary": f"street {idx}",
                              "owner_native": ub["est_h"].get(str(idx)),
                              "nbr_native": ua["est_h"].get(str(idx))})

# drop pairs missing a native estimate on either side
good = [p for p in pairs if p["owner_native"] is not None and p["nbr_native"] is not None]
dropped = len(pairs) - len(good)

# cross-check against survey edge refs (file-number level)
byfile = {}
for uid, u in units.items():
    byfile.setdefault(u["file"], []).append(uid)
for p in good:
    fa = units[p["owner"]]["file"]; fb = units[p["nbr"]]["file"]
    if fa == fb:
        continue
    refs = edge_refs.get(fa, {})
    allrefs = set(sum((v for v in refs.values()), []))
    if allrefs and fb not in allrefs:
        mismatches.append({"pair": [p["owner"], p["nbr"]],
                           "boundary": p["boundary"],
                           "note": f"survey edge refs of sheet {fa} do not list {fb}"})

json.dump({"units": units, "pairs": good,
           "edge_ref_mismatches": mismatches},
          open(os.path.join(ROOT, "out", "city_network.json"), "w"), indent=1)
print(f"units {len(units)}  pairs {len(good)} (dropped {dropped} without natives)  "
      f"edge-ref mismatches {len(mismatches)}")
deg = {}
for p in good:
    deg[p["owner"]] = deg.get(p["owner"], 0) + 1
    deg[p["nbr"]] = deg.get(p["nbr"], 0) + 1
isolated = [u for u in units if deg.get(u, 0) == 0]
print("isolated units:", isolated)
low = sorted((d, u) for u, d in deg.items())[:8]
print("lowest-degree:", low)
