#!/usr/bin/env python3
"""Stage 4 gate: does the ownership tiling cover the city without gaps?

    python3 tools/tiling.py --year 1912

Every output pixel must come from exactly one sheet. This checks the ways
that can fail — ground inside the mosaic that no sheet claims, and two sheets
claiming the same pixel — using the ownership polygons themselves, so the
answer is exact geometry rather than a sampled image statistic.

Unclaimed ground comes in two shapes. A HOLE is an interior ring of the
union. An INLET is a channel of unclaimed ground that reaches the outside of
the union, so it is not a ring: the 57|63 white band (HQ-19) was one, and the
first version of this gate never saw it. Inlets are found by closing the
union with a CLOSE_PX buffer -- which seals a channel narrower than 2*CLOSE_PX
at its mouth -- and reporting what the closed union contains that the real
union does not, provided some sheet's paper actually covers it.

Writes outputs/{year}/qc/tiling_audit.json and gaps.geojson.
"""
import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from reciplib import Recipe                      # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MIN_GAP_AREA = 50.0 * 50.0     # mosaic px^2 (~8.6 x 8.6 ft at 1912 scale)
HOLE_WIDTH = 30.0              # px; narrower is a cut-line hairline
CLOSE_PX = 700.0               # seals inlet mouths up to ~1400 px (240 ft)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", required=True, choices=["1899", "1912"])
    a = ap.parse_args()

    from shapely.geometry import Polygon
    from shapely.ops import unary_union

    r = Recipe(int(a.year))
    regions = [(u, Polygon(p).buffer(0)) for u, p in r.ownership()]
    print(f"{len(regions)} ownership regions", flush=True)

    union = unary_union([p for _, p in regions])
    sum_area = sum(p.area for _, p in regions)
    overlap_area = sum_area - union.area

    overlaps = []
    for i in range(len(regions)):
        for j in range(i + 1, len(regions)):
            ua, pa = regions[i]
            ub, pb = regions[j]
            if not pa.intersects(pb):
                continue
            inter = pa.intersection(pb)
            if inter.area > MIN_GAP_AREA:
                overlaps.append({"pair": f"{ua}|{ub}",
                                 "area_px2": round(inter.area, 1)})
    overlaps.sort(key=lambda o: -o["area_px2"])

    def describe(hp, kind):
        c = hp.centroid
        width = 2.0 * hp.area / hp.length if hp.length else 0.0
        return {"area_px2": round(hp.area, 1), "width_px": round(width, 1),
                "kind": kind if width > HOLE_WIDTH else "hairline",
                "centroid": [round(c.x, 1), round(c.y, 1)]}

    # holes: interior rings of the union
    polys = list(getattr(union, "geoms", [union]))
    gaps, gap_geoms = [], []
    for poly in polys:
        for ring in poly.interiors:
            hp = Polygon(ring)
            if hp.area > MIN_GAP_AREA:
                gaps.append(describe(hp, "hole"))
                gap_geoms.append((hp.area, hp))

    # inlets: unclaimed channels open to the outside, found by closing
    paper = []
    for u, info in r.units.items():
        e = info.get("extent")
        if not e:
            continue
        M, t = r.sheet_matrix(u)
        paper.append(Polygon([tuple(M @ np.array(c, float) + t) for c in
                              ((e[0], e[1]), (e[2], e[1]), (e[2], e[3]), (e[0], e[3]))]))
    paper = unary_union(paper) if paper else union
    closed = union.buffer(CLOSE_PX).buffer(-CLOSE_PX)
    extra = closed.difference(union).intersection(paper)
    for g in getattr(extra, "geoms", [extra]):
        if g.is_empty or g.area <= MIN_GAP_AREA:
            continue
        # skip anything that is really an interior hole already listed
        if any(h.intersects(g) and h.intersection(g).area > 0.5 * g.area
               for _, h in gap_geoms):
            continue
        gaps.append(describe(g, "inlet"))
        gap_geoms.append((g.area, g))
    gaps.sort(key=lambda h: -h["area_px2"])
    gap_geoms.sort(key=lambda h: -h[0])

    res = {
        "year": int(a.year),
        "regions": len(regions),
        "union_area_px2": round(union.area, 1),
        "sum_of_regions_px2": round(sum_area, 1),
        "overlap_area_px2": round(overlap_area, 1),
        "overlap_fraction": round(overlap_area / union.area, 6),
        "disjoint_pieces": len(polys),
        "interior_gaps": gaps,
        "unclaimed_area_px2": round(sum(g.area for _, g in gap_geoms), 1),
        "pairwise_overlaps": overlaps[:25],
        "min_reported_area_px2": MIN_GAP_AREA,
        "inlet_close_px": CLOSE_PX,
    }

    qc = os.path.join(REPO, "outputs", a.year, "qc")
    os.makedirs(qc, exist_ok=True)
    json.dump(res, open(os.path.join(qc, "tiling_audit.json"), "w"), indent=1)
    json.dump({"type": "FeatureCollection", "features": [
        {"type": "Feature",
         "properties": {"area_px2": round(area, 1), "rank": i + 1},
         "geometry": {"type": "Polygon",
                      "coordinates": [list(g.exterior.coords)]}}
        for i, (area, g) in enumerate(gap_geoms) if g.geom_type == "Polygon"]},
        open(os.path.join(qc, "gaps.geojson"), "w"))

    print(f"union area        : {union.area:,.0f} px^2")
    print(f"overlap area      : {overlap_area:,.0f} px^2 "
          f"({overlap_area / union.area * 100:.4f}% of the union)")
    print(f"disjoint pieces   : {len(polys)}"
          + ("  <- the city should be ONE piece" if len(polys) > 1 else ""))
    real = [h for h in gaps if h["kind"] == "hole"]
    inl = [h for h in gaps if h["kind"] == "inlet"]
    hair = [h for h in gaps if h["kind"] == "hairline"]
    print(f"unclaimed ground  : {len(gaps)}  ({len(real)} holes, {len(inl)} inlets, "
          f"{len(hair)} cut-line hairlines); "
          f"{res['unclaimed_area_px2'] / union.area * 100:.3f}% of the union")
    for h in real + inl:
        print(f"    {h['kind']:<6} {h['area_px2']:>12,.0f} px^2  {h['width_px']:>7.0f} px wide"
              f"   at {h['centroid']}")
    print(f"overlapping pairs : {len(overlaps)}"
          + (f"  worst {overlaps[0]['pair']} {overlaps[0]['area_px2']:,.0f} px^2"
             if overlaps else "  (none)"))
    print(f"\nwrote {qc}/tiling_audit.json")

    return 0 if not gaps and len(polys) == 1 else 1


if __name__ == "__main__":
    sys.exit(main())
