#!/usr/bin/env python
"""build_cuts.py — derive ONE pooled ownership-cut polyline per shared street.

Method (per 30_controls/SEAM_STRUCTURE.md):
  every seam abuts; each plate draws only its own frontage of the boundary
  street, so the natural cut is the shared street's centreline. For each
  measured anchor we take the two plates' frontage corners (the seam-ward
  endpoints of the verified face segments), transform them with the SOLVED raw
  transforms (read at run time from 40_solve/output/transforms.json — the solve
  will be re-run, transforms are an input, never baked in), and put the cut at
  the midline between the plates' drawn extents. The streets are platted
  straight, so the pooled cut is a total-least-squares line through the
  per-anchor midpoints, extended straight along the street.

  Where a plate's measured drawn extent crosses the nominal midline, the cut
  deviates locally to keep the drawn cartography on its own side, and the span
  is FLAGGED in the output (never silently clipped). Ink-level validation is
  the job of 60_master/tools/content_extent_check.py.

Outputs 50_seams/cuts.json: per street, polyline vertices + full provenance
(which anchors/faces determined it), plus the block outer boundary, the target
extent used for the render canvas, and the reserved sheet-5 bay band.
"""

import argparse
import json
import os
import re
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import seamlib as sl  # noqa: E402


# ---------------------------------------------------------------------------

def derive_street_cut(street_id, street_name, records, raw, page_quads,
                      clearance_px=4.0, deviation_halfspan_px=150.0,
                      deviation_clearance_px=12.0):
    """Derive the pooled cut for one street from its anchor records.

    records: anchor records from seamlib.load_pair_anchors (this street only).
    raw: {sheet: raw transform}. page_quads: {sheet: (4,2) sheet-px corners}.
    Returns the street's cuts.json entry (dict).
    """
    anchors = []
    midpoints = []
    sheets_involved = set()
    for rec in records:
        plates_m = {}
        for sheet, pl in rec["plates"].items():
            corners_m = sl.apply_raw(raw[sheet], np.asarray(pl["corners_sheet"]))
            plates_m[sheet] = {
                "side": pl["side"],
                "corners_sheet": pl["corners_sheet"],
                "corners_mosaic": corners_m,
                "frontage_mosaic": corners_m.mean(axis=0),
                "source_sha256": pl["source_sha256"],
            }
            sheets_involved.add(sheet)
        fronts = [plates_m[s]["frontage_mosaic"] for s in sorted(plates_m)]
        mid = np.mean(np.stack(fronts, axis=0), axis=0)
        midpoints.append(mid)
        anchors.append({"rec": rec, "plates_m": plates_m, "midpoint": mid})

    line = sl.fit_tls_line(np.asarray(midpoints))

    # along-extent: cover every participating page footprint, extended a bit
    ts = []
    for sheet in sorted(sheets_involved):
        quad_m = sl.apply_raw(raw[sheet], page_quads[sheet])
        ts.extend(sl.line_along(line, quad_m))
    t_min, t_max = float(min(ts)) - 200.0, float(max(ts)) + 200.0

    # side sign per sheet (from transformed page centre)
    side_sign = {}
    for sheet in sorted(sheets_involved):
        centre_m = sl.apply_raw(raw[sheet], page_quads[sheet].mean(axis=0))
        side_sign[sheet] = 1.0 if sl.line_offset(line, centre_m) >= 0 else -1.0

    # per-anchor diagnostics + content-crossing detection against the fitted line
    anchor_out = []
    flags = []
    deviations = []  # (t_corner, needed_offset, flag_index)
    for a in anchors:
        rec, plates_m = a["rec"], a["plates_m"]
        entry = {
            "pair": rec["pair"],
            "anchor": rec["anchor"],
            "file": rec["file"],
            "midpoint_mosaic": [float(v) for v in a["midpoint"]],
            "midline_residual_px": float(sl.line_offset(line, a["midpoint"])),
            "plates": {},
        }
        fronts_off = {}
        for sheet, pl in sorted(plates_m.items()):
            sgn = side_sign[sheet]
            offs = sl.line_offset(line, pl["corners_mosaic"])
            fronts_off[sheet] = float(sl.line_offset(line, pl["frontage_mosaic"]))
            entry["plates"][str(sheet)] = {
                "side": pl["side"],
                "side_sign": sgn,
                "corners_sheet_px": pl["corners_sheet"],
                "corners_mosaic": [[float(x) for x in p] for p in pl["corners_mosaic"]],
                "frontage_offset_px": fronts_off[sheet],
                "corner_offsets_px": [float(o) for o in offs],
                "source_sha256": pl["source_sha256"],
            }
            # crossing check: every measured corner must sit on its own side
            # of the cut by at least clearance_px
            for ci, o in enumerate(offs):
                margin = sgn * float(o)
                if margin < clearance_px:
                    t_c = float(sl.line_along(line, pl["corners_mosaic"][ci]))
                    need = float(o) - sgn * deviation_clearance_px
                    flags.append({
                        "street_id": street_id,
                        "pair": rec["pair"],
                        "anchor": rec["anchor"],
                        "sheet": sheet,
                        "corner_index": ci,
                        "corner_mosaic": [float(x) for x in pl["corners_mosaic"][ci]],
                        "margin_px": margin,
                        "cut_local_offset_px": need,
                        "along_t": t_c,
                        "note": "measured drawn extent crosses (or grazes) the nominal "
                                "midline; cut deviated locally, span flagged",
                    })
                    deviations.append((t_c, need))
        # solved street width at this anchor (separation of the two frontages)
        offs_sorted = sorted(fronts_off.values())
        entry["solved_street_width_px"] = float(offs_sorted[-1] - offs_sorted[0])
        anchor_out.append(entry)

    # build the cut polyline in (t, offset) coordinates
    tn = [(t_min, 0.0), (t_max, 0.0)]
    for t_c, need in deviations:
        h = deviation_halfspan_px
        tn.extend([(t_c - h, 0.0), (t_c - h / 2.0, need),
                   (t_c + h / 2.0, need), (t_c + h, 0.0)])
    manual_devs_applied = []
    for md in load_manual_deviations():
        if md.get("street_match", "").lower() not in street_name.lower():
            continue
        t0, t1 = md["t_range_mosaic"]
        off = float(md["offset_px"])
        ramp = float(md.get("ramp_px", 120.0))
        tn.extend([(t0 - ramp, 0.0), (t0, off), (t1, off), (t1 + ramp, 0.0)])
        manual_devs_applied.append(md)
    tn = sorted(set(tn))
    polyline = sl.polyline_from_tn(line, tn)

    halfwidths = [e["solved_street_width_px"] / 2.0 for e in anchor_out]
    residuals = [e["midline_residual_px"] for e in anchor_out]
    return {
        "street_id": street_id,
        "street_name": street_name,
        "orientation": "vertical" if abs(line["dir"][1]) > abs(line["dir"][0]) else "horizontal",
        "line_fit": line,
        "polyline_mosaic": polyline,
        "polyline_tn": [[float(t), float(o)] for t, o in tn],
        "along_range": [t_min, t_max],
        "sheet_side_sign": {str(s): side_sign[s] for s in sorted(side_sign)},
        "mean_half_street_width_px": float(np.mean(halfwidths)),
        "anchor_midline_residuals_px": {
            "rms": float(np.sqrt(np.mean(np.square(residuals)))),
            "max_abs": float(np.max(np.abs(residuals))),
        },
        "n_anchors": len(anchor_out),
        "anchors": anchor_out,
        "flagged_spans": [f for f in flags],
        "manual_deviations": manual_devs_applied,
        "provenance": ("cut = TLS midline through per-anchor midpoints of the two "
                       "plates' solved frontage corners (seam-ward endpoints of the "
                       "verified face segments); extended straight along the platted "
                       "street; sides fixed by adjacency"),
    }


# ---------------------------------------------------------------------------
# target extent helpers

def _face_line_from_anchors(records, raw, name_substr, pick):
    """TLS line through transformed face-segment endpoints of anchors whose name
    contains name_substr. pick: 'min_y'|'max_y' chooses, per plate, the face
    whose transformed mean y is smaller/larger (outer face of the extent)."""
    pts = []
    used = []
    for rec in records:
        if name_substr not in str(rec["anchor"]).lower():
            continue
        for sheet, pl in sorted(rec["plates"].items()):
            segs_m = [sl.apply_raw(raw[sheet], np.asarray(s)) for s in pl["segs_sheet"]]
            means = [s.mean(axis=0)[1] for s in segs_m]
            idx = int(np.argmin(means)) if pick == "min_y" else int(np.argmax(means))
            pts.extend(segs_m[idx])
            used.append({"file": rec["file"], "anchor": rec["anchor"], "sheet": sheet,
                         "face_index": idx})
    if len(pts) < 2:
        return None, used
    return sl.fit_tls_line(np.asarray(pts)), used


def _frontage_line_side(records, raw, want_max_x):
    """TLS line through the frontage corners of the plates on one side of a
    street (used for the Sealy east frontage = target right edge)."""
    pts = []
    used = []
    for rec in records:
        fronts = {}
        for sheet, pl in rec["plates"].items():
            fronts[sheet] = sl.apply_raw(raw[sheet], np.asarray(pl["corners_sheet"]))
        # plate with larger mean x = east plate
        items = sorted(fronts.items(), key=lambda kv: kv[1].mean(axis=0)[0])
        sheet, corners = items[-1] if want_max_x else items[0]
        pts.extend(corners)
        used.append({"file": rec["file"], "anchor": rec["anchor"], "sheet": sheet})
    if len(pts) < 2:
        return None, used
    return sl.fit_tls_line(np.asarray(pts)), used


def derive_target_extent(all_records, streets, raw, page_quads, adjacency,
                         kappa_mosaic, sheet5_geojson_path):
    """Target extent (INVENTORY: Ave A/Water to Ave I/Sealy; 19th to 25th St)
    intersected with the solved footprints, plus the reserved sheet-5 bay band."""
    notes = []
    fp_pts = np.vstack([sl.apply_raw(raw[s], page_quads[s]) for s in sorted(raw)])
    fp_bbox = [float(fp_pts[:, 0].min()), float(fp_pts[:, 1].min()),
               float(fp_pts[:, 0].max()), float(fp_pts[:, 1].max())]

    vertical_recs = [r for r in all_records
                     if streets.get(r["street_id"], {}).get("orientation") == "vertical"]

    line19, used19 = _face_line_from_anchors(vertical_recs, raw, "19th", "min_y")
    line25, used25 = _face_line_from_anchors(vertical_recs, raw, "25th", "max_y")

    sealy_recs = [r for r in all_records if r["street_id"] == "ave_i_or_sealy"]
    line_sealy_e, used_se = _frontage_line_side(sealy_recs, raw, True) \
        if sealy_recs else (None, [])

    # bay-side sheets = solved sheets whose left neighbour is unsolved sheet 5
    bay_sheets = [s for s in sorted(raw)
                  if adjacency["edges"][str(s)]["left"][0] == 5]
    bay_x = min(float(sl.apply_raw(raw[s], page_quads[s])[:, 0].min())
                for s in bay_sheets) if bay_sheets else fp_bbox[0]

    # reserved band width from the sheet-5 panel regions
    with open(sheet5_geojson_path) as f:
        gj = json.load(f)
    m = re.search(r"100\s*ft\s*=\s*~?(\d+)\s*px", gj.get("description", ""))
    kappa5 = (float(m.group(1)) / 100.0) if m else 3.09
    if not m:
        notes.append("sheet-5 scale not parsed from geojson description; fallback 3.09 px/ft")
    panel_w = 0.0
    panels = []
    for feat in gj["features"]:
        rid = feat["properties"].get("region_id")
        if rid not in ("A", "B"):
            continue
        xs = [p[0] for p in feat["geometry"]["coordinates"][0]]
        w = max(xs) - min(xs)
        panel_w = max(panel_w, w)
        panels.append({"region_id": rid, "width_sheet5_px": float(w)})
    scale5 = kappa_mosaic / kappa5
    band_w = int(np.ceil(panel_w * scale5 / 10.0) * 10) + 200
    notes.append("band width = widest sheet-5 panel (%.0f px) x kappa ratio %.3f "
                 "(kappa_mosaic %.3f / sheet5 %.2f px/ft) + 200 px margin; "
                 "kappa is prior-dominated (see transforms.json kappa_note) so the "
                 "band is a RESERVATION, not solved geometry" %
                 (panel_w, scale5, kappa_mosaic, kappa5))

    # evaluate extent lines over the footprint ranges
    def line_y_range(line, x0, x1):
        ys = []
        for x in (x0, x1):
            d, p0 = line["dir"], line["p0"]
            if abs(d[0]) < 1e-9:
                continue
            t = (x - p0[0]) / d[0]
            ys.append(p0[1] + t * d[1])
        return (min(ys), max(ys)) if ys else (None, None)

    def line_x_range(line, y0, y1):
        xs = []
        for y in (y0, y1):
            d, p0 = line["dir"], line["p0"]
            if abs(d[1]) > abs(d[0]):  # near-vertical: param by y
                t = (y - p0[1]) / d[1]
                xs.append(p0[0] + t * d[0])
            else:
                t = (y - p0[1]) / d[1] if abs(d[1]) > 1e-9 else 0.0
                xs.append(p0[0] + t * d[0])
        return (min(xs), max(xs)) if xs else (None, None)

    x_right = fp_bbox[2]
    if line_sealy_e is not None:
        xr = line_x_range(line_sealy_e, fp_bbox[1], fp_bbox[3])
        x_right = xr[1]
        notes.append("right edge = Sealy east frontage line (target ends at Ave I)")
    else:
        notes.append("right edge fallback = footprint bbox (no Sealy anchors)")

    y_top = fp_bbox[1]
    if line19 is not None:
        y_top = line_y_range(line19, bay_x, x_right)[0]
        notes.append("top edge = 19th St outer (north) face line from boundary-row anchors")
    else:
        notes.append("top edge fallback = footprint bbox (no 19th St anchors)")

    y_bot = fp_bbox[3]
    if line25 is not None:
        y_bot = line_y_range(line25, bay_x, x_right)[1]
        notes.append("bottom edge = 25th St (Rosenberg) outer (south) face line")
    else:
        notes.append("bottom edge fallback = footprint bbox (no 25th St anchors)")

    canvas_rect = [int(np.floor(bay_x)) - band_w, int(np.floor(y_top)),
                   int(np.ceil(x_right)), int(np.ceil(y_bot))]
    return {
        "description": "canvas = bbox of the 12 solved footprints intersected with the "
                       "target extent (Ave A/Water to Ave I/Sealy; 19th to 25th St) "
                       "+ reserved blank bay-side band for the sheet-5 panels",
        "footprint_bbox_mosaic": fp_bbox,
        "canvas_rect_mosaic": canvas_rect,
        "reserved_bay_band": {
            "mosaic_rect": [canvas_rect[0], canvas_rect[1],
                            int(np.floor(bay_x)), canvas_rect[3]],
            "width_px": band_w,
            "panels": panels,
            "sheet5_scale_px_per_ft": kappa5,
            "status": "reserved-empty: sheet-5 attachments out of scope for this stage",
        },
        "lines": {
            "st_19th_north_face": line19, "st_25th_south_face": line25,
            "ave_i_east_frontage": line_sealy_e,
        },
        "line_sources": {"19th": used19, "25th": used25, "sealy_east": used_se},
        "bay_sheets": bay_sheets,
        "notes": notes,
    }


def outer_boundary_ring(raw, page_quads):
    from shapely.ops import unary_union
    from shapely.geometry import Polygon
    polys = [Polygon(sl.apply_raw(raw[s], page_quads[s])) for s in sorted(raw)]
    u = unary_union(polys)
    if u.geom_type == "MultiPolygon":
        u = max(u.geoms, key=lambda g: g.area)
    ring = [list(map(float, p)) for p in u.exterior.coords]
    return ring


# ---------------------------------------------------------------------------


MANUAL_DEVIATIONS_JSON = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                      "manual_deviations.json")

def load_manual_deviations():
    """Owner-verified local cut deviations. Schema per entry:
    {street_match, t_range_mosaic [t0,t1], offset_px (signed, in the street's
    (t,n) normal frame), ramp_px, reason, verified_by, date}.  Input file, never
    rewritten by the pipeline, so deviations survive regeneration."""
    if not os.path.exists(MANUAL_DEVIATIONS_JSON):
        return []
    with open(MANUAL_DEVIATIONS_JSON) as fh:
        return json.load(fh).get("deviations", [])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--transforms", default=sl.TRANSFORMS_JSON)
    ap.add_argument("--out", default=sl.CUTS_JSON)
    ap.add_argument("--clearance-px", type=float, default=4.0)
    args = ap.parse_args(argv)

    raw, tdoc = sl.load_transforms(args.transforms)
    adjacency = sl.load_adjacency()
    page_quads = sl.load_page_quads()
    records, pair_hashes, skipped = sl.load_pair_anchors(
        sl.VERIFIED_DIR, adjacency, set(raw))

    by_street = {}
    for rec in records:
        by_street.setdefault((rec["street_id"], rec["street_name"]), []).append(rec)

    streets = {}
    for (sid, name), recs in sorted(by_street.items()):
        streets[sid] = derive_street_cut(sid, name, recs, raw, page_quads,
                                         clearance_px=args.clearance_px)

    kappa = float(tdoc.get("kappa_px_per_ft", 5.826))
    target = derive_target_extent(records, streets, raw, page_quads, adjacency,
                                  kappa, sl.SHEET5_REGIONS_GEOJSON)

    out = {
        "generated_by": "50_seams/build_cuts.py",
        "convention": tdoc["convention"],
        "kappa_px_per_ft": kappa,
        "kappa_caveat": tdoc.get("kappa_note"),
        "inputs": {
            "transforms_json": {"path": os.path.relpath(args.transforms, sl.PROJECT),
                                "sha256": sl.sha256_file(args.transforms)},
            "adjacency_json": {"sha256": sl.sha256_file(sl.ADJACENCY_JSON)},
            "plate_structure_json": {"sha256": sl.sha256_file(sl.PLATE_STRUCTURE_JSON)},
            "pair_files": {k: v for k, v in sorted(pair_hashes.items())},
        },
        "skipped_inputs": [{"item": a, "reason": b} for a, b in skipped],
        "streets": [streets[sid] for sid in sorted(streets)],
        "outer_boundary": {
            "ring_mosaic": outer_boundary_ring(raw, page_quads),
            "provenance": "union boundary of the 12 solved page quads "
                          "(20_plates/plate_structure.json, Otsu paper detection); "
                          "NOT a drawn-content boundary — outer trimming is done by "
                          "the target extent at render time",
        },
        "target_extent": target,
    }
    text = sl.write_canonical_json(args.out, out)
    print("wrote %s (%d streets, %d anchors, %d flagged spans, sha256 %s)" % (
        args.out, len(streets), len(records),
        sum(len(s["flagged_spans"]) for s in streets.values()),
        sl.sha256_text(text)[:12]))

    for sid in sorted(streets):
        s = streets[sid]
        widths = [a["solved_street_width_px"] for a in s["anchors"]]
        print("  %-22s %-10s anchors=%d width_px %.1f..%.1f (mean %.1f = %.1f ft) "
              "midline-resid rms %.2f max %.2f flags=%d" % (
                  sid, s["orientation"], s["n_anchors"],
                  min(widths), max(widths), float(np.mean(widths)),
                  float(np.mean(widths)) / kappa,
                  s["anchor_midline_residuals_px"]["rms"],
                  s["anchor_midline_residuals_px"]["max_abs"],
                  len(s["flagged_spans"])))
        for f in s["flagged_spans"]:
            print("    FLAG %s %s sheet %s corner %d margin %.1f px" % (
                f["pair"], f["anchor"], f["sheet"], f["corner_index"], f["margin_px"]))
    cr = target["canvas_rect_mosaic"]
    print("  canvas mosaic rect: x %d..%d  y %d..%d  (%d x %d), bay band %d px" % (
        cr[0], cr[2], cr[1], cr[3], cr[2] - cr[0], cr[3] - cr[1],
        target["reserved_bay_band"]["width_px"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
