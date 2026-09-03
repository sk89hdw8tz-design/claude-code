#!/usr/bin/env python3
"""Close tiling gaps that a neighbouring sheet can actually supply.

    python3 tools/fillgaps.py --year 1912 [--apply]

A gap in the ownership tiling renders as a white gash. Some gaps are real
source gaps — no sheet maps that ground, and nothing can fix that here. The
rest are bookkeeping: a neighbour's scan does cover the ground, but no region
claims it. This assigns such ground to adjoining units whose paper covers it.

Two cases (HQ-19 defect 2):
  * one sheet covers essentially the whole gap: it takes the whole gap;
  * no single sheet does, but a union of adjoining sheets does: the gap is
    split between them, each taking the part its own paper covers, in order
    of how much of the gap each covers. The boundary between the parts is
    then a paper edge, not a bisector, which is still not a building.

Gaps are both interior holes and inlets (channels open to the exterior), as
tools/tiling.py finds them. This changes only WHICH sheet writes a pixel. It
does not touch pixels, and it cannot invent coverage: ground no sheet covers
is left alone and reported. Dry-run by default; --apply rewrites
seams/ownership_city.json.
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
CLOSE_PX = 700.0        # same inlet closing as tiling.py
FULL = 0.98             # one sheet covering this much takes the whole gap
PART_MIN = 0.02         # a split part smaller than this share is ignored


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", required=True, choices=["1899", "1912"])
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    from shapely.geometry import Polygon
    from shapely.ops import unary_union

    r = Recipe(int(a.year))
    regions = {u: P.buffer(0) for u, P in r.ownership_shapes()}

    supply = {}
    for u, info in r.units.items():
        if not info.get("extent") or u not in regions:
            continue
        supply[u] = r.footprint(u).buffer(0)     # trimmed extent minus inset frames
    paper = unary_union(list(supply.values()))

    union = unary_union(list(regions.values()))
    gaps = []
    for poly in getattr(union, "geoms", [union]):
        for ring in poly.interiors:
            hp = Polygon(ring)
            if hp.area > MIN_AREA:
                gaps.append(("hole", hp))
    closed = union.buffer(CLOSE_PX).buffer(-CLOSE_PX)
    extra = closed.difference(union).intersection(paper)
    for g in getattr(extra, "geoms", [extra]):
        if g.is_empty or g.area <= MIN_AREA or g.geom_type != "Polygon":
            continue
        if any(h.intersects(g) and h.intersection(g).area > 0.5 * g.area for _, h in gaps):
            continue
        gaps.append(("inlet", g))
    gaps.sort(key=lambda h: -h[1].area)
    print(f"{len(gaps)} gaps over {MIN_AREA:.0f} px^2 "
          f"({sum(1 for k, _ in gaps if k == 'hole')} holes, "
          f"{sum(1 for k, _ in gaps if k == 'inlet')} inlets)", flush=True)

    filled, unfixable, assign = [], [], {}
    for kind, hp in gaps:
        cands = []
        for u, poly in regions.items():
            sup = supply.get(u)
            if sup is None:
                continue
            cov = sup.intersection(hp)
            if cov.area > PART_MIN * hp.area:
                # a unit that already touches the hole is preferred: its paper
                # continues across the join. A unit that merely maps the ground
                # is still allowed -- the furniture boxes (a plate's own scale
                # bar) cut holes that only a non-adjacent neighbour covers, and
                # a hole is worse than that neighbour's own scan of the ground.
                cands.append((poly.buffer(1.0).intersects(hp), cov.area, u, cov))
        cands.sort(key=lambda c: (not c[0], -c[1]))
        cands = [(a, u, cov) for _, a, u, cov in cands]
        c = hp.centroid
        rec = {"kind": kind, "area_px2": round(hp.area, 1),
               "centroid": [round(c.x, 1), round(c.y, 1)]}
        if not cands:
            unfixable.append(dict(rec, covered_fraction=0.0))
            continue
        if cands[0][0] >= FULL * hp.area:
            u = cands[0][1]
            assign.setdefault(u, []).append(hp)
            filled.append(dict(rec, to=[[u, 1.0]]))
            continue
        # split: each candidate takes what its paper covers of what is left
        left, parts = hp, []
        for area, u, cov in cands:
            piece = left.intersection(cov)
            if piece.is_empty or piece.area < PART_MIN * hp.area:
                continue
            pieces = [p for p in getattr(piece, "geoms", [piece])
                      if p.geom_type == "Polygon" and p.area > MIN_AREA / 4]
            if not pieces:
                continue
            for p in pieces:
                assign.setdefault(u, []).append(p)
            got = sum(p.area for p in pieces)
            parts.append([u, round(got / hp.area, 3)])
            left = left.difference(piece)
            if left.area < PART_MIN * hp.area:
                break
        covered = 1.0 - left.area / hp.area
        if parts:
            filled.append(dict(rec, to=parts, covered_fraction=round(covered, 3)))
        if left.area > MIN_AREA:
            unfixable.append(dict(rec, area_px2=round(left.area, 1),
                                  covered_fraction=round(covered, 3),
                                  note="remainder after split" if parts else None))

    print(f"\nassigned to neighbours : {len(filled)}")
    for f in filled:
        print(f"    {f['kind']:<5} {f['area_px2']:>11,.0f} px^2 at {f['centroid']} -> "
              + ", ".join(f"unit {u} ({s:.0%})" for u, s in f["to"]))
    print(f"\ntrue source gaps       : {len(unfixable)} "
          f"(no sheet maps this ground; nothing to assign)")
    for f in unfixable:
        print(f"    {f['kind']:<5} {f['area_px2']:>11,.0f} px^2 at {f['centroid']}"
              f"  (covered {f['covered_fraction']:.0%})")

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
        merged = unary_union([regions[u]] + [h.buffer(0.01) for h in hs]).buffer(0)
        if merged.geom_type != "Polygon":       # keep the largest part
            merged = max(merged.geoms, key=lambda g: g.area)
        by_unit[u]["polygon_mosaic"]["exterior"] = [
            [round(x, 3), round(y, 3)] for x, y in merged.exterior.coords]
        by_unit[u]["polygon_mosaic"]["interiors"] = [
            [[round(x, 3), round(y, 3)] for x, y in r_.coords] for r_ in merged.interiors]
        by_unit[u]["gap_filled"] = [f["area_px2"] for f in filled
                                    if any(t[0] == u for t in f["to"])]
    doc["gap_fill"] = {
        "tool": "tools/fillgaps.py",
        "note": ("gaps in the tiling assigned to adjoining units whose paper "
                 "covers that ground, split between several where no single "
                 "one does; ownership only, no pixel change"),
        "filled": filled, "left_as_source_gaps": unfixable,
    }
    json.dump(doc, open(path, "w"), indent=1)
    print(f"\nwrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
