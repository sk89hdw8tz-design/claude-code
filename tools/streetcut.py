#!/usr/bin/env python3
"""Cut sheet ownership along street centrelines, as the brief requires.

    python3 tools/streetcut.py --year 1912 [--apply]

Non-negotiable §2.5: "cut seams down street centrelines so no building
footprint is ever split across a seam". The Voronoi re-cut that followed the
control solve does not do that — its boundaries are bisectors between sheet
centres and can run straight through a building.

The controls already say where to cut. Each one names the corridor two
adjacent sheets share and gives its position on both, so the seam between
that pair IS that corridor's centreline. So a sheet's region is simply the
intersection of the half-planes its controls put it on, clipped to the ground
it actually covers:

    region(u) = footprint(u)  ∩  { half-plane from each control on u }
                              ∩  { bisector for neighbours with no control }

That is convex, so every region is one clean ring, every boundary between two
controlled neighbours lies on a street or avenue centreline, and buildings —
which sit inside blocks, between corridors — are never split.

A single straight line per named street is deliberately NOT used: Galveston's
grid bends about 2 degrees to the south, so one street's mosaic coordinate
varies along its length. Each pair's own reading is used instead.

Geometry only; no pixel is altered.
"""
import argparse
import json
import os
import re
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from reciplib import Recipe, px_per_ft          # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIG = 1e7


def load_cuts(r):
    """{(a,b): (axis, mosaic_coord)} from every accepted control."""
    out = {}
    cdir = os.path.join(r.dir, "controls")
    for f in sorted(os.listdir(cdir)):
        m = re.match(r"pair_(\w+)_(\w+)\.json$", f)
        if not m:
            continue
        try:
            d = json.load(open(os.path.join(cdir, f)))
        except Exception:
            continue
        if "a_native" not in d or str(d.get("status", "")).upper() != "ACCEPTED":
            continue
        ua, ub = m.group(1).lstrip("0"), m.group(2).lstrip("0")
        if ua not in r.units or ub not in r.units:
            continue
        vert = str(d.get("axis", "")).lower().startswith("av")
        pos = []
        for uid, nat in ((ua, d["a_native"]), (ub, d["b_native"])):
            M, t = r.sheet_matrix(uid)
            e = r.units[uid]["extent"]
            p = M @ (np.array([float(nat), (e[1] + e[3]) / 2]) if vert
                     else np.array([(e[0] + e[2]) / 2, float(nat)])) + t
            pos.append(float(p[0] if vert else p[1]))
        out[(ua, ub)] = ("x" if vert else "y", float(np.mean(pos)),
                         d.get("corridor", "?"))
    return out


def half_plane(axis, coord, keep_low):
    from shapely.geometry import box
    if axis == "x":
        return box(-BIG, -BIG, coord, BIG) if keep_low else box(coord, -BIG, BIG, BIG)
    return box(-BIG, -BIG, BIG, coord) if keep_low else box(-BIG, coord, BIG, BIG)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", required=True, choices=["1912", "1899"])
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    from shapely.geometry import Polygon
    from shapely.ops import unary_union

    r = Recipe(int(a.year))
    ppf = px_per_ft(r)
    cuts = load_cuts(r)
    print(f"{len(cuts)} control cuts "
          f"({sum(1 for v in cuts.values() if v[0]=='x')} avenue, "
          f"{sum(1 for v in cuts.values() if v[0]=='y')} street)", flush=True)

    def foot(u):
        e = r.units[u]["extent"]
        M, t = r.sheet_matrix(u)
        return Polygon([tuple(M @ np.array(c, float) + t) for c in
                        ((e[0], e[1]), (e[2], e[1]), (e[2], e[3]), (e[0], e[3]))])

    feet = {u: foot(u) for u in r.units}
    cen = {u: np.array([feet[u].centroid.x, feet[u].centroid.y]) for u in feet}

    regions, stats = {}, {"control": 0, "bisector": 0}
    for u in feet:
        g = feet[u]
        for v in feet:
            if v == u or not feet[u].intersects(feet[v]):
                continue
            key = (u, v) if (u, v) in cuts else ((v, u) if (v, u) in cuts else None)
            if key:
                axis, coord, _ = cuts[key]
                k = 0 if axis == "x" else 1
                # sides must be assigned by which sheet lies lower on this axis,
                # NOT by comparing each centre to the line: a corridor at the far
                # edge of one sheet can leave both centres on the same side, and
                # both would then keep the same half-plane and overlap
                g = g.intersection(half_plane(axis, coord, cen[u][k] < cen[v][k]))
                stats["control"] += 1
            else:
                # no control for this neighbour: fall back to the bisector so
                # the tiling still closes, and count it
                d = cen[v] - cen[u]
                mid = (cen[u] + cen[v]) / 2
                axis = "x" if abs(d[0]) >= abs(d[1]) else "y"
                k = 0 if axis == "x" else 1
                g = g.intersection(half_plane(axis, mid[k], cen[u][k] < mid[k]))
                stats["bisector"] += 1
            if g.is_empty:
                break
        if not g.is_empty:
            if g.geom_type != "Polygon":
                g = max(g.geoms, key=lambda p: p.area)
            regions[u] = g
    print(f"boundaries: {stats['control']//2} from controls, "
          f"{stats['bisector']//2} from bisectors (no control for that pair)",
          flush=True)

    un = unary_union(list(regions.values()))
    s = sum(g.area for g in regions.values())
    holes = sum(1 for p in getattr(un, "geoms", [un]) for _ in p.interiors)
    print(f"{len(regions)} regions; union {un.area:,.0f} px2, "
          f"overlap {s-un.area:,.0f} px2 ({(s-un.area)/un.area*100:.4f}%), "
          f"pieces {len(getattr(un,'geoms',[un]))}, interior rings {holes}")

    doc = {"convention": "polygon_mosaic.exterior in mosaic pixels",
           "generated_by": "tools/streetcut.py",
           "note": ("seams cut on the shared street/avenue centreline named by "
                    "each pair's control (§2.5); bisector only where a pair has "
                    "no control"),
           "regions": [{"unit": u,
                        "source": "street-centreline cut",
                        "polygon_mosaic": {"exterior":
                            [[round(x, 3), round(y, 3)] for x, y in g.exterior.coords]}}
                       for u, g in sorted(regions.items(), key=lambda kv: int(kv[0]))]}
    p = os.path.join(r.dir, "seams", "ownership_streetcut.json")
    json.dump(doc, open(p, "w"), indent=1)
    print(f"wrote {p}")
    if a.apply:
        import shutil
        tgt = os.path.join(r.dir, "seams", "ownership_city.json")
        if not os.path.exists(tgt + ".pre_streetcut"):
            shutil.copyfile(tgt, tgt + ".pre_streetcut")
        json.dump(doc, open(tgt, "w"), indent=1)
        print(f"applied to {tgt}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
