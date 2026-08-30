#!/usr/bin/env python3
"""Stage 4 gate: does the ownership tiling cover the city without gaps?

    python3 tools/tiling.py --year 1912

Every output pixel must come from exactly one sheet. This checks the two ways
that can fail — a hole inside the mosaic that no sheet claims (a gap), and two
sheets claiming the same pixel (an overlap, which would mean the single-writer
rule was not enforced) — using the ownership polygons themselves, so the answer
is exact geometry rather than a sampled image statistic.

Writes outputs/{year}/qc/tiling_audit.json.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from reciplib import Recipe                      # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# a sliver narrower than this is a polygon-arithmetic artefact, not a real gap
MIN_GAP_AREA = 50.0 * 50.0     # mosaic px^2 (~8.6 x 8.6 ft at 1912 scale)
HOLE_WIDTH = 30.0              # px; narrower than this is a cut-line hairline,
                               # not ground that no sheet maps


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

    # pairwise overlaps, worst first
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

    # holes: interior rings of the union are areas no sheet claims
    polys = list(getattr(union, "geoms", [union]))
    holes, hole_geoms = [], []
    for poly in polys:
        for ring in poly.interiors:
            hp = Polygon(ring)
            if hp.area > MIN_GAP_AREA:
                c = hp.centroid
                # 2*area/perimeter ~ the width of a long thin shape: it
                # separates hairline slivers between abutting cuts from
                # genuinely unmapped ground
                width = 2.0 * hp.area / hp.length if hp.length else 0.0
                holes.append({"area_px2": round(hp.area, 1),
                              "width_px": round(width, 1),
                              "kind": "hole" if width > HOLE_WIDTH else "hairline",
                              "centroid": [round(c.x, 1), round(c.y, 1)]})
                hole_geoms.append((hp.area, list(ring.coords)))
    holes.sort(key=lambda h: -h["area_px2"])
    hole_geoms.sort(key=lambda h: -h[0])

    res = {
        "year": int(a.year),
        "regions": len(regions),
        "union_area_px2": round(union.area, 1),
        "sum_of_regions_px2": round(sum_area, 1),
        "overlap_area_px2": round(overlap_area, 1),
        "overlap_fraction": round(overlap_area / union.area, 6),
        "disjoint_pieces": len(polys),
        "interior_gaps": holes,
        "pairwise_overlaps": overlaps[:25],
        "min_reported_area_px2": MIN_GAP_AREA,
    }

    qc = os.path.join(REPO, "outputs", a.year, "qc")
    os.makedirs(qc, exist_ok=True)
    json.dump(res, open(os.path.join(qc, "tiling_audit.json"), "w"), indent=1)
    json.dump({"type": "FeatureCollection", "features": [
        {"type": "Feature",
         "properties": {"area_px2": round(area, 1), "rank": i + 1},
         "geometry": {"type": "Polygon", "coordinates": [coords]}}
        for i, (area, coords) in enumerate(hole_geoms)]},
        open(os.path.join(qc, "gaps.geojson"), "w"))

    print(f"union area        : {union.area:,.0f} px^2")
    print(f"overlap area      : {overlap_area:,.0f} px^2 "
          f"({overlap_area / union.area * 100:.4f}% of the union)")
    print(f"disjoint pieces   : {len(polys)}"
          + ("  <- the city should be ONE piece" if len(polys) > 1 else ""))
    real = [h for h in holes if h["kind"] == "hole"]
    hair = [h for h in holes if h["kind"] == "hairline"]
    print(f"interior gaps     : {len(holes)}  "
          f"({len(real)} unmapped holes, {len(hair)} cut-line hairlines)")
    for h in real:
        print(f"    hole {h['area_px2']:>12,.0f} px^2  {h['width_px']:>7.0f} px wide"
              f"   at {h['centroid']}")
    print(f"overlapping pairs : {len(overlaps)}"
          + (f"  worst {overlaps[0]['pair']} {overlaps[0]['area_px2']:,.0f} px^2"
             if overlaps else "  (none)"))
    print(f"\nwrote {qc}/tiling_audit.json")

    return 0 if not holes and len(polys) == 1 else 1


if __name__ == "__main__":
    sys.exit(main())
