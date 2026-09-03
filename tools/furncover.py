#!/usr/bin/env python3
"""Decide which furniture boxes may be cut from a unit's footprint.

    python3 tools/furncover.py --year 1912 [--apply]

A furniture box (a plate's title, its numeral, its 'Scale of Feet' legend)
is cut out so that a neighbour mapping the same ground owns it and the
marking never prints inside the city. That only works if a neighbour maps
essentially ALL of the box: where it maps part, the rest falls back to the
plate's own scan and the result is a patch of neighbour paper beside half a
legend -- worse than either alternative. So each box is marked
`cut: true` only when other units' trimmed footprints cover at least
COVER of it; otherwise `cut: false` and the plate keeps its own paper, as
the accepted 27x40 master does with its scale bars and compass roses.
"""
import argparse
import json
import os
import sys

COVER = 0.98


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", type=int, default=1912)
    ap.add_argument("--cover", type=float, default=COVER)
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from reciplib import Recipe
    from shapely.geometry import box as sbox
    from shapely.ops import unary_union
    from shapely.affinity import affine_transform
    import numpy as np
    r = Recipe(a.year)
    doc = json.load(open(os.path.join(r.dir, "units.json")))
    # every unit's footprint with furniture kept (what it could supply)
    foot = {}
    for u in r.units:
        try:
            foot[u] = r.footprint(u, furniture=False).buffer(0)
        except Exception:
            pass
    stats = {"cut": 0, "kept": 0}
    for u, ud in doc["units"].items():
        fs = ud.get("furniture_native") or []
        if not fs:
            continue
        M, t = r.sheet_matrix(u)
        others = [f for v, f in foot.items() if v != u and not
                  (r.units[v].get("panel_of") == u or r.units[u].get("panel_of") == v)]
        for f in fs:
            b = f["box"]
            g = affine_transform(sbox(b[0], b[1], b[2], b[3]),
                                 [M[0, 0], M[0, 1], M[1, 0], M[1, 1], t[0], t[1]])
            near = [o for o in others if o.intersects(g)]
            cov = unary_union([o.intersection(g) for o in near]).area / g.area if near else 0.0
            f["cut"] = bool(cov >= a.cover)
            f["covered_fraction"] = round(cov, 3)
            stats["cut" if f["cut"] else "kept"] += 1
    print(f"{stats['cut']} boxes a neighbour can supply in full (cut), "
          f"{stats['kept']} kept on the plate's own paper")
    if a.apply:
        json.dump(doc, open(os.path.join(r.dir, "units.json"), "w"), indent=1)
        print("applied to units.json")


if __name__ == "__main__":
    main()
