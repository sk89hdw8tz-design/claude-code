#!/usr/bin/env python3
"""Close tiling holes that a neighbouring sheet can actually supply.

    python3 tools/fillgaps.py --year 1912 [--apply]

A hole in the ownership tiling renders as a white gash. Some holes are real
source gaps — no sheet maps that ground, and nothing can fix that here. The
rest are bookkeeping: a neighbour's scan does cover the ground, but no region
claims it. This assigns each such hole to the adjoining unit that (a) can
supply the pixels and (b) shares the most boundary with it.

This changes only WHICH sheet writes a pixel. It does not touch pixels, and
it cannot invent coverage: a hole no sheet covers is left alone and reported.
Dry-run by default; --apply rewrites seams/ownership_city.json.
"""
import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from reciplib import Recipe                      # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MIN_AREA = 50.0 * 50.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", required=True, choices=["1899", "1912"])
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    from shapely.geometry import Polygon, Point
    from shapely.ops import unary_union

    r = Recipe(int(a.year))
    regions = {u: Polygon(p).buffer(0) for u, p in r.ownership()}

    # what ground each sheet can actually supply
    supply = {}
    for u, info in r.units.items():
        e = info.get("extent")
        if not e or u not in regions:
            continue
        M, t = r.sheet_matrix(u)
        supply[u] = Polygon([tuple(M @ np.array(c, float) + t) for c in
                             ((e[0], e[1]), (e[2], e[1]),
                              (e[2], e[3]), (e[0], e[3]))]).buffer(0)

    union = unary_union(list(regions.values()))
    holes = []
    for poly in getattr(union, "geoms", [union]):
        for ring in poly.interiors:
            hp = Polygon(ring)
            if hp.area > MIN_AREA:
                holes.append(hp)
    holes.sort(key=lambda h: -h.area)
    print(f"{len(holes)} holes over {MIN_AREA:.0f} px^2", flush=True)

    filled, unfixable, assign = [], [], {}
    for hp in holes:
        cands = []
        for u, poly in regions.items():
            if not poly.buffer(1.0).intersects(hp):
                continue
            sup = supply.get(u)
            # the sheet must cover essentially all of the hole to fill it
            if sup is None or sup.intersection(hp).area < 0.98 * hp.area:
                continue
            shared = poly.buffer(1.0).intersection(hp.boundary).length
            cands.append((shared, u))
        if not cands:
            c = hp.centroid
            unfixable.append({"area_px2": round(hp.area, 1),
                              "centroid": [round(c.x, 1), round(c.y, 1)]})
            continue
        cands.sort(reverse=True)
        u = cands[0][1]
        assign.setdefault(u, []).append(hp)
        c = hp.centroid
        filled.append({"area_px2": round(hp.area, 1), "to_unit": u,
                       "centroid": [round(c.x, 1), round(c.y, 1)]})

    print(f"\nfillable by a neighbour : {len(filled)}")
    for f in filled:
        print(f"    {f['area_px2']:>11,.0f} px^2 -> unit {f['to_unit']:<4} "
              f"at {f['centroid']}")
    print(f"\ntrue source gaps        : {len(unfixable)} "
          f"(no sheet maps this ground; nothing to assign)")
    for f in unfixable:
        print(f"    {f['area_px2']:>11,.0f} px^2 at {f['centroid']}")

    if not a.apply:
        print("\ndry run — pass --apply to write the ownership file")
        return 0
    if not assign:
        print("\nnothing to apply")
        return 0

    path = os.path.join(REPO, "outputs", a.year, "recipe", "seams",
                        "ownership_city.json")
    doc = json.load(open(path))
    by_unit = {str(reg.get("unit", reg.get("sheet"))): reg
               for reg in doc["regions"]}
    for u, hs in assign.items():
        merged = unary_union([regions[u]] + hs)
        if merged.geom_type != "Polygon":       # keep the largest part
            merged = max(merged.geoms, key=lambda g: g.area)
        by_unit[u]["polygon_mosaic"]["exterior"] = [
            [round(x, 3), round(y, 3)] for x, y in merged.exterior.coords]
        by_unit[u]["gap_filled"] = [f["area_px2"] for f in filled
                                    if f["to_unit"] == u]
    doc["gap_fill"] = {
        "tool": "tools/fillgaps.py",
        "note": ("holes in the tiling assigned to an adjoining unit whose scan "
                 "covers that ground; ownership only, no pixel change"),
        "filled": filled, "left_as_source_gaps": unfixable,
    }
    json.dump(doc, open(path, "w"), indent=1)
    print(f"\nwrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
