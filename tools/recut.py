#!/usr/bin/env python3
"""Re-cut sheet ownership after the sheets have moved.

    python3 tools/recut.py --year 1912 [--apply]

Ownership says which sheet writes each pixel. It was cut for the old
placement, so once netsolve moves sheets it no longer matches where they
actually are. This rebuilds it the way the city recipe already described:
the frozen downtown core keeps its hand-cut regions exactly, and every other
sheet takes the Voronoi cell of its centre, clipped to the ground that sheet
actually covers.

Geometry only — which sheet supplies a pixel, never the pixel itself.
"""
import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from reciplib import Recipe                        # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", required=True, choices=["1912", "1899"])
    ap.add_argument("--transforms", default="transforms_controls.json")
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    from shapely.geometry import Polygon, MultiPoint, box
    from shapely.ops import unary_union
    from shapely import voronoi_polygons

    r = Recipe(int(a.year))
    T = json.load(open(os.path.join(r.dir, a.transforms)))["sheets"]
    gj = json.load(open(os.path.join(r.dir, "sheets_city.geojson")))
    core = {str(f["properties"]["unit"]) for f in gj["features"]
            if f["properties"].get("tier") == "core"}
    own_old = dict(r.ownership())

    def foot(u):
        e = r.units[u]["extent"]
        M = np.array(T[u]["m"], float)
        t = np.array(T[u]["t"], float)
        return Polygon([tuple(M @ np.array(c, float) + t) for c in
                        ((e[0], e[1]), (e[2], e[1]), (e[2], e[3]), (e[0], e[3]))])

    feet = {u: foot(u) for u in r.units if u in T}
    core_poly = unary_union([Polygon(own_old[u]).buffer(0)
                             for u in core if u in own_old])
    others = [u for u in feet if u not in core]
    pts = {u: feet[u].centroid for u in others}

    allf = unary_union(list(feet.values()))
    env = box(*allf.buffer(2000).bounds)
    mp = MultiPoint([pts[u] for u in others])
    cells = list(voronoi_polygons(mp, extend_to=env).geoms)
    # match each cell back to its generating point
    cell_for = {}
    for c in cells:
        for u in others:
            if c.contains(pts[u]):
                cell_for[u] = c
                break

    regions, dropped = [], []
    for u in others:
        c = cell_for.get(u)
        if c is None:
            dropped.append(u)
            continue
        g = feet[u].intersection(c).difference(core_poly).buffer(0)
        if g.is_empty:
            dropped.append(u)
            continue
        if g.geom_type != "Polygon":
            g = max(g.geoms, key=lambda p: p.area)
        regions.append({"unit": u, "source": "voronoi(re-cut after control solve)",
                        "polygon_mosaic": {"exterior":
                            [[round(x, 3), round(y, 3)] for x, y in g.exterior.coords]}})
    for u in sorted(core):
        if u in own_old:
            regions.append({"unit": u, "source": "dp-cut(frozen downtown)",
                            "polygon_mosaic": {"exterior":
                                [[round(x, 3), round(y, 3)]
                                 for x, y in Polygon(own_old[u]).exterior.coords]}})

    print(f"{len(regions)} regions ({len(core)} frozen core, "
          f"{len(regions)-len(core)} re-cut)"
          + (f"; dropped {dropped}" if dropped else ""))
    tot = unary_union([Polygon(g["polygon_mosaic"]["exterior"]).buffer(0)
                       for g in regions])
    s = sum(Polygon(g["polygon_mosaic"]["exterior"]).area for g in regions)
    print(f"union {tot.area:,.0f} px2, overlap {s-tot.area:,.0f} px2 "
          f"({(s-tot.area)/tot.area*100:.4f}%), pieces "
          f"{len(getattr(tot,'geoms',[tot]))}")

    doc = {"convention": "polygon_mosaic.exterior in mosaic pixels",
           "generated_by": "tools/recut.py", "regions": regions}
    p = os.path.join(r.dir, "seams", "ownership_recut.json")
    json.dump(doc, open(p, "w"), indent=1)
    print(f"wrote {p}")
    if a.apply:
        import shutil
        tgt = os.path.join(r.dir, "seams", "ownership_city.json")
        shutil.copyfile(tgt, tgt + ".pre_recut")
        json.dump(doc, open(tgt, "w"), indent=1)
        print(f"applied to {tgt} (previous kept as .pre_recut)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
