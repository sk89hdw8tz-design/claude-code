#!/usr/bin/env python3
"""Move a seam locally, by declaration, after the cut pipeline has run.

    python3 tools/seamnudge.py --year 1912 [--apply]

Reads seams/nudges.json: a list of
  {"pair": ["50","56"], "axis": "y", "along": [13480, 14740], "coord": 10600,
   "why": "..."}
For each entry, inside the window (along-range x coord+-ACROSS), the ground
the two units own between them is re-partitioned by a straight line at
`coord` on the seam's across-axis: the unit whose centre is on the low side
takes the low side, the other the high side, each clipped to its own paper
(footprint with furniture cut). No other unit is touched. Re-run after every
streetcut/fillgaps pass; the declarations are the durable record.
"""
import argparse, json, os, sys, copy
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from reciplib import Recipe
from shapely.geometry import Polygon, box
from shapely.ops import unary_union

ACROSS = 1500.0

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", required=True, choices=["1912"])
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    r = Recipe(int(a.year))
    op = os.path.join(r.dir, "seams", "ownership_city.json")
    own = json.load(open(op))
    nudges = json.load(open(os.path.join(r.dir, "seams", "nudges.json")))
    R = {}
    for reg in own["regions"]:
        R.setdefault(str(reg.get("unit", reg.get("sheet"))), []).append(reg)
    def poly(reg):
        pm = reg["polygon_mosaic"]; return Polygon(pm["exterior"], pm.get("interiors") or None).buffer(0)
    U = {u: unary_union([poly(x) for x in v]) for u, v in R.items()}
    touched = set()
    for n in nudges:
        ua, ub = n["pair"]; ax = n["axis"]; lo, hi = n["along"]; c = float(n["coord"])
        win = box(lo, c - ACROSS, hi, c + ACROSS) if ax == "y" else box(c - ACROSS, lo, c + ACROSS, hi)
        low_half = box(lo, c - ACROSS, hi, c) if ax == "y" else box(c - ACROSS, lo, c, hi)
        high_half = box(lo, c, hi, c + ACROSS) if ax == "y" else box(c, lo, c + ACROSS, hi)
        both = unary_union([U[ua], U[ub]]).intersection(win)
        ca, cb = U[ua].centroid, U[ub].centroid
        k = 1 if ax == "y" else 0
        low_u, high_u = (ua, ub) if (ca.coords[0][k] < cb.coords[0][k]) else (ub, ua)
        fl, fh = r.footprint(low_u, furniture=True), r.footprint(high_u, furniture=True)
        low_take = both.intersection(low_half).intersection(fl)
        high_take = both.intersection(high_half).intersection(fh)
        rest = both.difference(unary_union([low_take, high_take]))
        # ground only one plate's paper covers stays with that plate
        low_take = unary_union([low_take, rest.intersection(fl)])
        high_take = unary_union([high_take, rest.intersection(fh).difference(fl)])
        before = {low_u: round(U[low_u].intersection(win).area), high_u: round(U[high_u].intersection(win).area)}
        U[low_u] = unary_union([U[low_u].difference(win), low_take])
        U[high_u] = unary_union([U[high_u].difference(win), high_take])
        touched |= {ua, ub}
        print(f"{ua}|{ub} {ax}={c:.0f} along {lo}-{hi}: {before} -> {low_u} {round(U[low_u].intersection(win).area)}, {high_u} {round(U[high_u].intersection(win).area)}  ({n.get('why','')[:70]})")
    if not a.apply:
        return
    regs = [reg for reg in own["regions"] if str(reg.get("unit", reg.get("sheet"))) not in touched]
    for u in sorted(touched):
        g = U[u]
        for piece in (g.geoms if g.geom_type != "Polygon" else [g]):
            if piece.is_empty or piece.area < 300:
                continue
            proto = copy.deepcopy(R[u][0]); proto["unit"] = u
            proto["polygon_mosaic"] = {"exterior": [[round(x, 1), round(y, 1)] for x, y in piece.exterior.coords],
                                       "interiors": [[[round(x, 1), round(y, 1)] for x, y in i.coords] for i in piece.interiors]}
            regs.append(proto)
    own["regions"] = regs
    own["nudges"] = {"tool": "tools/seamnudge.py", "n": len(nudges), "note": "declared local seam moves (seams/nudges.json) applied after streetcut+fillgaps"}
    json.dump(own, open(op, "w"), indent=1)
    print("applied:", len(regs), "regions")

if __name__ == "__main__":
    main()
