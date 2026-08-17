#!/usr/bin/env python
"""build_masks.py — per-sheet ownership polygons in SHEET pixel coordinates.

Each solved sheet owns its page content (the detected paper quad) clipped by the
half-planes of the pooled cut polylines of its bounding streets (from
50_seams/cuts.json); on outer edges the ownership runs to the page quad — outer
trimming to the target extent happens at render time via the canvas rect.

Regions are stored as a LIST of features, each with a unique region_id (a
duplicate id raises; nothing is ever silently overwritten). Honors
50_seams/manual_exclusions.json (verified exclusions survive regeneration
because they live in that separate input file and are re-applied on every run).

Idempotent: canonical JSON (sorted keys, 3-dp floats); reruns without input
changes are byte-identical.
"""

import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import seamlib as sl  # noqa: E402

from shapely.geometry import Polygon  # noqa: E402


EXCLUSIONS_SCAFFOLD = {
    "_doc": ("Manually verified ownership exclusions, applied by build_masks.py as "
             "polygon subtractions from the named sheet's region. Coordinates are "
             "SHEET pixels (raster, origin top-left). Entries survive mask "
             "regeneration because this file is an input, never rewritten by the "
             "pipeline. Schema per entry: {exclusion_id, sheet, polygon_sheet_px "
             "[[x,y],...], reason, verified_by, date}."),
    "version": 1,
    "exclusions": [],
}


def ensure_exclusions_scaffold(path=sl.MANUAL_EXCLUSIONS_JSON):
    if not os.path.exists(path):
        sl.write_canonical_json(path, EXCLUSIONS_SCAFFOLD)
    with open(path) as f:
        return json.load(f)


def street_lookup(cuts):
    return {s["street_id"]: s for s in cuts["streets"]}


def bounding_cuts_for_sheet(adjacency, sheet, streets):
    """[(street_id, side)] of the cut streets bounding this sheet."""
    out = []
    edges = adjacency["edges"][str(sheet)]
    for side in ("top", "bottom", "left", "right"):
        val = edges.get(side)
        if not val or val[0] is None or val[1] is None:
            continue
        sid = sl.slug(val[1])
        if sid in streets:
            out.append((sid, side))
    return out


def sheet_ownership_mosaic(sheet, raw_T, page_quad, streets, cut_ids):
    """Shapely polygon of the sheet's ownership region in the mosaic frame."""
    poly = Polygon(sl.apply_raw(raw_T, page_quad))
    centre = sl.apply_raw(raw_T, page_quad.mean(axis=0))
    used = []
    for sid, side in cut_ids:
        st = streets[sid]
        line = st["line_fit"]
        sgn = 1.0 if sl.line_offset(line, centre) >= 0 else -1.0
        half = sl.halfplane_polygon(line, st["polyline_tn"], sgn)
        poly = poly.intersection(half)
        used.append({"street_id": sid, "sheet_edge": side, "side_sign": sgn})
    return poly, used


def coverage_margin_px(poly_page_mosaic, streets, sid, sgn):
    """How far the page extends PAST the cut toward the neighbour (positive =
    covered; negative = the page does not reach the cut -> potential gap)."""
    st = streets[sid]
    line = st["line_fit"]
    offs = sl.line_offset(line, np.asarray(poly_page_mosaic.exterior.coords))
    return float(np.max(-sgn * offs))


def polys_of(geom):
    if geom.is_empty:
        return []
    if geom.geom_type == "Polygon":
        return [geom]
    if geom.geom_type in ("MultiPolygon", "GeometryCollection"):
        return [g for g in geom.geoms if g.geom_type == "Polygon"]
    return []


def ring_to_sheet(ring_coords, inv_T):
    return [[float(x), float(y)] for x, y in sl.apply_raw(inv_T, np.asarray(ring_coords))]


def build_regions(raw, adjacency, page_quads, cuts, exclusions):
    """Build the feature list + stats. Raises RegionIdError on duplicate ids."""
    streets = street_lookup(cuts)
    registry = sl.RegionRegistry()
    stats = []
    excl_by_sheet = {}
    for e in exclusions.get("exclusions", []):
        excl_by_sheet.setdefault(int(e["sheet"]), []).append(e)

    for sheet in sorted(raw):
        T = raw[sheet]
        inv_T = sl.invert_raw(T)
        quad = page_quads[sheet]
        cut_ids = bounding_cuts_for_sheet(adjacency, sheet, streets)
        poly, used = sheet_ownership_mosaic(sheet, T, quad, streets, cut_ids)

        page_poly = Polygon(sl.apply_raw(T, quad))
        coverage = [{"street_id": u["street_id"],
                     "margin_px": coverage_margin_px(page_poly, streets,
                                                     u["street_id"], u["side_sign"])}
                    for u in used]

        applied = []
        for e in sorted(excl_by_sheet.get(sheet, []), key=lambda e: e["exclusion_id"]):
            ex_poly = Polygon(sl.apply_raw(T, np.asarray(e["polygon_sheet_px"], float)))
            poly = poly.difference(ex_poly)
            applied.append(e["exclusion_id"])

        parts = sorted(polys_of(poly),
                       key=lambda g: (-g.area, g.bounds[0], g.bounds[1]))
        for i, part in enumerate(parts):
            rid = "s%02d_r%d" % (sheet, i)
            registry.add({
                "region_id": rid,
                "sheet": sheet,
                "polygon_sheet_px": {
                    "exterior": ring_to_sheet(part.exterior.coords, inv_T),
                    "interiors": [ring_to_sheet(r.coords, inv_T) for r in part.interiors],
                },
                "polygon_mosaic": {
                    "exterior": [[float(x), float(y)] for x, y in part.exterior.coords],
                    "interiors": [[[float(x), float(y)] for x, y in r.coords]
                                  for r in part.interiors],
                },
                "bounding_cuts": used,
                "exclusions_applied": applied,
                "area_mosaic_px2": float(part.area),
            })
        stats.append({
            "sheet": sheet,
            "n_regions": len(parts),
            "area_mosaic_px2": float(sum(p.area for p in parts)),
            "page_area_mosaic_px2": float(page_poly.area),
            "owned_fraction_of_page": float(sum(p.area for p in parts) / page_poly.area),
            "cut_coverage_margins_px": coverage,
        })
    return registry.features, stats


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--transforms", default=sl.TRANSFORMS_JSON)
    ap.add_argument("--cuts", default=sl.CUTS_JSON)
    ap.add_argument("--out", default=sl.MASKS_JSON)
    args = ap.parse_args(argv)

    raw, tdoc = sl.load_transforms(args.transforms)
    adjacency = sl.load_adjacency()
    page_quads = sl.load_page_quads()
    with open(args.cuts) as f:
        cuts = json.load(f)
    t_sha = sl.sha256_file(args.transforms)
    cuts_t_sha = cuts["inputs"]["transforms_json"]["sha256"]
    if cuts_t_sha != t_sha:
        raise SystemExit(
            "cuts.json was built from a different transforms.json (%s... vs now %s...)"
            " — the solve output changed; re-run build_cuts.py first" %
            (cuts_t_sha[:12], t_sha[:12]))
    exclusions = ensure_exclusions_scaffold()

    features, stats = build_regions(raw, adjacency, page_quads, cuts, exclusions)

    gaps = [(st["sheet"], c) for st in stats
            for c in st["cut_coverage_margins_px"] if c["margin_px"] < 0]

    out = {
        "generated_by": "50_seams/build_masks.py",
        "convention": {
            "polygon_sheet_px": "SHEET raster pixels (origin top-left) of the archival "
                                "scan; ownership region = page quad clipped by bounding "
                                "cut half-planes, minus manual exclusions",
            "mosaic": tdoc["convention"],
        },
        "inputs": {
            "transforms_json": {"sha256": sl.sha256_file(args.transforms)},
            "cuts_json": {"sha256": sl.sha256_file(args.cuts)},
            "adjacency_json": {"sha256": sl.sha256_file(sl.ADJACENCY_JSON)},
            "plate_structure_json": {"sha256": sl.sha256_file(sl.PLATE_STRUCTURE_JSON)},
            "manual_exclusions_json": {"sha256": sl.sha256_file(sl.MANUAL_EXCLUSIONS_JSON)},
        },
        "regions": features,
        "stats": stats,
        "seam_gaps": [{"sheet": s, "street_id": c["street_id"],
                       "margin_px": c["margin_px"]} for s, c in gaps],
        "reserved": {
            "sheet5_bay_band": cuts["target_extent"]["reserved_bay_band"],
            "note": "sheet-5 panels not masked/rendered at this stage (D-006/D-008); "
                    "band kept empty by the render canvas",
        },
    }
    text = sl.write_canonical_json(args.out, out)
    print("wrote %s (%d regions on %d sheets, sha256 %s)" % (
        args.out, len(features), len(stats), sl.sha256_text(text)[:12]))
    for st in stats:
        margins = ", ".join("%s:%+.0f" % (c["street_id"].split("_")[1], c["margin_px"])
                            for c in st["cut_coverage_margins_px"])
        print("  sheet %2d: %d region(s), owns %5.1f%% of page, past-cut margins px [%s]"
              % (st["sheet"], st["n_regions"],
                 100 * st["owned_fraction_of_page"], margins))
    if gaps:
        print("  WARNING: %d seam gap(s) — page does not reach the cut:" % len(gaps))
        for s, c in gaps:
            print("    sheet %s @ %s margin %.1f px" % (s, c["street_id"], c["margin_px"]))
    else:
        print("  no seam gaps: every page reaches past every bounding cut")
    return 0


if __name__ == "__main__":
    sys.exit(main())
