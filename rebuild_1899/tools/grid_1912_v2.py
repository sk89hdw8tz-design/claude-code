#!/usr/bin/env python3
"""1912 corridor grid from the verified control files (not detection).

Each control anchor carries the two frontage-line segments (face1/face2) of a
named street or avenue corridor, in native px, on both sheets of a pair,
sigma ~3 px, with the one-block-off argument recorded. The corridor
centreline is the midpoint of the two faces. Mapping every measurement
through the solved transforms gives corridor positions in the mosaic frame.

Writes outputs/1912/recipe/grid.json (replacing the detection attempt).
"""
import glob
import json
import os
import re

import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(REPO)
tr = json.load(open("outputs/1912/recipe/transforms.json"))["sheets"]

def to_mosaic(sheet, xy):
    t = tr[str(sheet)]["raw"]
    M = np.array([[t["a"], -t["b"]], [t["b"], t["a"]]])
    return M @ np.array(xy, float) + np.array([t["tx"], t["ty"]])

AVE = {"a": 0, "b": 1, "c": 2, "d": 3, "e": 4, "f": 5, "g": 6, "h": 7,
       "i": 8, "j": 9, "broadway": 9, "k": 10}

def parse_anchor(s):
    t = s.lower()
    m = re.search(r"(\d+)(st|nd|rd|th)", t)
    if m and ("st" in t or "street" in t or True):
        # street anchor like "22nd St"
        if "ave" not in t:
            return ("street", int(m.group(1)))
    m = re.search(r"ave\.?\s*([a-k])\b", t)
    if m:
        return ("avenue", AVE[m.group(1)])
    if "broadway" in t:
        return ("avenue", 9)
    return (None, None)

streets, avenues = {}, {}
boundary_obs = {}
n_used = n_skip = 0

def parse_boundary(s):
    t = s.lower()
    m = re.search(r"ave\.?\s*([a-k])\b", t)
    if m:
        return ("avenue", AVE[m.group(1)])
    if "broadway" in t:
        return ("avenue", 9)
    m = re.search(r"(\d+)(st|nd|rd|th)", t)
    if m:
        return ("street", int(m.group(1)))
    return (None, None)
for path in sorted(glob.glob("outputs/1912/recipe/controls/*.json")):
    d = json.load(open(path))
    for c in d.get("controls", []):
        if c.get("status") not in ("ACCEPTED", "accepted"):
            n_skip += 1
            continue
        kind, idx = parse_anchor(c.get("anchor", ""))
        if kind is None:
            n_skip += 1
            continue
        for side in ("A", "B"):
            m = c.get(side)
            if not m or "face1_seg" not in m or "face2_seg" not in m:
                continue
            sheet = str(m["sheet"])
            if sheet not in tr:
                continue
            try:
                f1 = np.atleast_2d(np.array(m["face1_seg"], float))
                f2 = np.atleast_2d(np.array(m["face2_seg"], float))
                if f1.shape[-1] != 2 or f2.shape[-1] != 2:
                    raise ValueError
            except Exception:
                n_skip += 1
                continue
            mid = (f1.mean(axis=0) + f2.mean(axis=0)) / 2.0
            g = to_mosaic(sheet, mid)
            if kind == "street":
                streets.setdefault(idx, []).append((float(g[1]), float(g[0]), sheet))
            else:
                avenues.setdefault(idx, []).append((float(g[0]), float(g[1]), sheet))
            n_used += 1
            # The segment ends nearest the pair's BOUNDARY corridor stop at
            # that corridor's frontage line: A-side far ends and B-side near
            # ends bracket the boundary corridor. Collect them to recover the
            # boundary corridors (Aves C/F/I, 21st/24th) that never appear as
            # anchors themselves.
            bkind, bidx = parse_boundary(d.get("boundary", ""))
            if bkind:
                axis_i = 0 if bkind == "avenue" else 1
                ends = np.vstack([f1, f2])
                pick = ends[:, axis_i].max() if side == "A" else ends[:, axis_i].min()
                pt = ends[np.argmax(ends[:, axis_i])] if side == "A" else ends[np.argmin(ends[:, axis_i])]
                gb = to_mosaic(sheet, pt)
                store = boundary_obs.setdefault((bkind, bidx), {"A": [], "B": []})
                store["A" if side == "A" else "B"].append(float(gb[axis_i]))

grid = {
 "frame": "1912 mosaic frame (sheet 10 raw pixels minus [3326, 3898])",
 "avenue_slots": "A=0 B=1 C=2 D=3 E=4 F=5 G=6 H=7 I=8 J=9(Broadway) K=10",
 "source": "verified control files (frontage midlines), mapped through solved transforms",
 "streets": {}, "avenues": {},
}
print(f"controls used: {n_used} measurements, skipped {n_skip}")
print("street y (mosaic):")
for idx in sorted(streets):
    v = np.array([p[0] for p in streets[idx]])
    grid["streets"][str(idx)] = {
        "y": round(float(np.median(v)), 1), "n": len(v),
        "spread": round(float(v.max() - v.min()), 1),
        "samples": [[round(p[1], 1), round(p[0], 1), p[2]] for p in streets[idx]],
    }
    print(f"  {idx}: {np.median(v):8.1f} n={len(v)} spread={v.max()-v.min():6.1f}")
print("avenue x (mosaic):")
for idx in sorted(avenues):
    v = np.array([p[0] for p in avenues[idx]])
    grid["avenues"][str(idx)] = {
        "x": round(float(np.median(v)), 1), "n": len(v),
        "spread": round(float(v.max() - v.min()), 1),
        "samples": [[round(p[0], 1), round(p[1], 1), p[2]] for p in avenues[idx]],
    }
    print(f"  {idx}: {np.median(v):8.1f} n={len(v)} spread={v.max()-v.min():6.1f}")
print("boundary corridors from segment ends (frontage-to-frontage midpoints):")
for (bkind, bidx), obs in sorted(boundary_obs.items()):
    if not obs["A"] or not obs["B"]:
        continue
    a = float(np.median(obs["A"])); b = float(np.median(obs["B"]))
    centre = (a + b) / 2.0
    tgt = grid["avenues"] if bkind == "avenue" else grid["streets"]
    key = str(bidx)
    rec = {"x" if bkind == "avenue" else "y": round(centre, 1),
           "n": len(obs["A"]) + len(obs["B"]),
           "spread": round(abs(a - b), 1),
           "method": "boundary-bracket (A-side frontage to B-side frontage)"}
    if key not in tgt or tgt[key]["n"] <= 1:
        tgt[key] = rec
    print(f"  {bkind} {bidx}: centre {centre:8.1f}  bracket width {abs(a-b):6.1f} "
          f"nA={len(obs['A'])} nB={len(obs['B'])}{' (adopted)' if tgt[key] is rec else ''}")
json.dump(grid, open("outputs/1912/recipe/grid.json", "w"), indent=1)
print("wrote outputs/1912/recipe/grid.json")
