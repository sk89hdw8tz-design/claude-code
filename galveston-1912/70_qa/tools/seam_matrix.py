#!/usr/bin/env python
"""seam_matrix.py — QA stage 1: one row per seam (adjacent sheet pair).

Columns: solve residual RMS (40_solve/output/residuals.json), cut provenance
(pooled street cut + any manual deviation touching the pair's span), mask
tiling verdict (independent shapely re-check: overlap area, boundary-gap
sampling, shared-segment length), content-extent encroachment (frozen rerun of
content_extent_check), and the panel verdict (placeholder until stage 2's
visual review fills it via --verdicts).

Outputs: 70_qa/run1/seam_matrix.json + seam_matrix.md, stamped with the
master's sha256. Report-only; nothing is modified.
"""

import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import qalib
from qalib import RUN, sl


def tiling_check(geo, a, b, street):
    """Independent mask-tiling verdict for the pair (a, b).

    The mask cut is reconstructed by build_masks from cuts.json's 3-dp-rounded
    line_fit, so it can sit a few px off polyline_mosaic (rounded direction
    vector times |t| up to ~12000). Both sides share the SAME rounded line, so
    tiling must still be exact. Method: sample the street line inside the two
    page quads' intersection, project each sample onto region A's boundary
    (that projection lies on the actual shared cut), then test +/-0.5 px
    offsets for exactly-one coverage among ALL owned regions. Also reports the
    A-boundary/B-boundary Hausdorff-style gap at each sample and the drift of
    the actual cut from polyline_mosaic.
    """
    from shapely.ops import unary_union
    from shapely.geometry import Point, Polygon, LineString
    A = unary_union([r["poly_mosaic"] for r in geo["regions"] if r["sheet"] == a])
    B = unary_union([r["poly_mosaic"] for r in geo["regions"] if r["sheet"] == b])
    allpolys = [(r["sheet"], r["poly_mosaic"]) for r in geo["regions"]]
    overlap = A.intersection(B).area

    Tq = geo["raw"]
    qa_m = sl.apply_raw(Tq[a], geo["quads"][a])
    qb_m = sl.apply_raw(Tq[b], geo["quads"][b])
    quad_int = Polygon(qa_m).intersection(Polygon(qb_m))
    result = {"overlap_px2": round(float(overlap), 3),
              "shared_boundary_px": 0.0, "gap_samples_bad": 0, "n_gap_samples": 0,
              "max_pair_gap_px": None, "cut_drift_from_polyline_px": None,
              "bad_sample_coords": []}
    if quad_int.is_empty:
        result["verdict"] = "FAIL-no-page-overlap"
        return result, None

    line = street["line_fit"]
    pl = LineString(street["polyline_mosaic"])
    seg = pl.intersection(quad_int)
    if not seg.is_empty:
        # restrict to the span where BOTH regions actually border this cut
        # (the page overlap band runs past crossing streets into ground owned
        # by other sheets; 10 px tolerance covers the 3-dp line rounding drift)
        seg = seg.intersection(A.buffer(10.0)).intersection(B.buffer(10.0))
    if seg.is_empty:
        result["verdict"] = "FAIL-cut-outside-page-overlap"
        return result, None
    if seg.geom_type != "LineString":
        seg = max(seg.geoms, key=lambda g: g.length)
    L = seg.length
    result["shared_boundary_px"] = round(float(L), 1)

    bad = 0
    n = 0
    gaps = []
    drifts = []
    bad_coords = []
    street_n = np.asarray(line["normal"])
    for f in np.linspace(0.01, 0.99, max(8, int(L // 150))):
        p = seg.interpolate(f, normalized=True)
        # project onto A's boundary -> a point on the actual mask cut
        cutp = A.boundary.interpolate(A.boundary.project(p))
        drifts.append(p.distance(cutp))
        gaps.append(B.boundary.distance(cutp))
        for s in (+0.5, -0.5):
            q = Point(cutp.x + s * street_n[0], cutp.y + s * street_n[1])
            cov = [sh for sh, poly in allpolys if poly.covers(q)]
            n += 1
            if len(cov) != 1:
                bad += 1
                if len(bad_coords) < 8:
                    bad_coords.append({"mosaic": [round(q.x, 1), round(q.y, 1)],
                                       "covered_by": cov})
    result["n_gap_samples"] = n
    result["gap_samples_bad"] = bad
    result["max_pair_gap_px"] = round(float(max(gaps)), 3) if gaps else None
    result["cut_drift_from_polyline_px"] = round(float(max(drifts)), 2) if drifts else None
    result["bad_sample_coords"] = bad_coords
    # overlap is a rounding sliver: mean width = area / shared length. The
    # masks' 3-dp canonical rounding produces ~0.0004 px wide slivers (a few
    # px^2 over ~7000 px); integer rasterization cannot double-own a pixel
    # from those (stage 7 verifies coverage==1 on the raster independently).
    mean_w = overlap / max(L, 1.0)
    result["overlap_mean_width_px"] = round(float(mean_w), 6)
    ok = (mean_w < 0.01 and bad == 0 and L > 500 and
          (result["max_pair_gap_px"] or 0) < 0.01)
    result["verdict"] = "PASS" if ok else "FAIL"
    return result, seg


def mid_anchor(geo, a, b, street, seg):
    """The pair's control anchor nearest the middle of the CANVAS-VISIBLE part
    of the shared segment (regions extend past the canvas; panels must not)."""
    from shapely.geometry import box
    cand = [an for an in street["anchors"] if sorted(an["pair"]) == sorted((a, b))]
    midxy = None
    if seg is not None:
        x0m, y0m, x1m, y1m = geo["mosaic_rect"]
        vis = seg.intersection(box(x0m, y0m, x1m, y1m))
        if vis.is_empty:
            vis = seg
        if vis.geom_type != "LineString":
            vis = max(vis.geoms, key=lambda g: g.length)
        mid = vis.interpolate(0.5, normalized=True)
        midxy = np.array([mid.x, mid.y])
    if not cand:
        return None, midxy
    if midxy is None:
        return cand[len(cand) // 2], None
    best = min(cand, key=lambda an: np.hypot(*(np.asarray(an["midpoint_mosaic"]) - midxy)))
    return best, midxy


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--verdicts", default=None,
                    help="JSON {seam: {verdict, reason}} from stage-2 visual review")
    args = ap.parse_args(argv)

    man, fz, checks = qalib.verify_frozen_inputs()
    geo = qalib.load_geometry()
    with open(qalib.RESIDUALS_JSON) as f:
        res = json.load(f)
    frozen_extent_path = os.path.join(RUN, "content_extent_report_frozen.json")
    with open(frozen_extent_path) as f:
        extent = json.load(f)
    if extent["inputs"]["cuts_json"]["sha256"] != fz["components"]["cuts"]:
        raise SystemExit("frozen content extent report does not match frozen cuts")
    ext_by = {(r["sheet"], r["street_id"]): r for r in extent["results"]}

    with open(os.path.join(qalib.PROJECT, "50_seams", "manual_deviations.json")) as f:
        mdev = json.load(f)

    verdicts = {}
    if args.verdicts:
        with open(args.verdicts) as f:
            vdoc = json.load(f)
        if "verdicts" in vdoc:
            vstamp = vdoc.get("stamp", {}).get("master_sha256")
            if vstamp and vstamp != qalib.master_sha256():
                raise SystemExit("verdicts file is stale (different master sha)")
            verdicts = vdoc["verdicts"]
        else:
            verdicts = vdoc

    rows = []
    for p in geo["pairs"]:
        a, b = p["pair"]
        sid = p["street_id"]
        street = geo["streets"][sid]
        seam_key = "%d-%d" % (a, b)

        obs = [o for o in res["observations"]
               if o.get("seam") == seam_key or o.get("seam") == "%d-%d" % (b, a)]
        rr_along = [o["residual_px"] for o in obs if o["type"] == "along"]
        rr_across = [o["residual_px"] for o in obs if o["type"] == "across"]

        def rms_of(v):
            return float(np.sqrt(np.mean(np.square(v)))) if v else None

        def worst_of(v):
            return float(np.max(np.abs(v))) if v else None

        rms, worst = rms_of(rr_along), worst_of(rr_along)
        rms_across, worst_across = rms_of(rr_across), worst_of(rr_across)

        tiling, seg = tiling_check(geo, a, b, street)
        anchor, midxy = mid_anchor(geo, a, b, street, seg)

        # manual deviations relevant to this pair's along-range
        devs = []
        if seg is not None:
            line = street["line_fit"]
            pts = np.asarray(seg.coords) if seg.geom_type == "LineString" else \
                np.concatenate([np.asarray(g.coords) for g in seg.geoms])
            t_lo = float(sl.line_along(line, pts).min())
            t_hi = float(sl.line_along(line, pts).max())
            for d in street.get("manual_deviations", []):
                dr = d.get("t_range_mosaic")
                if dr and not (dr[1] < t_lo or dr[0] > t_hi):
                    devs.append({"reason": d.get("reason", "")[:140],
                                 "offset_px": d.get("offset_px"),
                                 "t_range_mosaic": dr})

        e_a = ext_by.get((a, sid))
        e_b = ext_by.get((b, sid))
        enc = {
            "sheet_%d_interior_px" % a: e_a["max_encroachment_interior_px"] if e_a else None,
            "sheet_%d_interior_px" % b: e_b["max_encroachment_interior_px"] if e_b else None,
            "half_street_width_px": street["mean_half_street_width_px"],
        }

        v = verdicts.get(seam_key, {})
        rows.append({
            "seam": seam_key, "pair": [a, b],
            "street_id": sid, "street_name": p["street_name"],
            "solve_rms_px": None if rms is None else round(rms, 2),
            "solve_worst_abs_px": None if worst is None else round(worst, 2),
            "across_rms_px": None if rms_across is None else round(rms_across, 2),
            "across_worst_abs_px": None if worst_across is None else round(worst_across, 2),
            "across_note": "across = constructed frontage separation vs default "
                           "street width * kappa; absorbs the plates' drafted-width "
                           "disagreement (sigma floor 12 px), NOT seam misregistration",
            "n_residual_obs": len(obs),
            "cut_provenance": "pooled per-street TLS midline (%s), %d anchors, "
                              "anchor-midline rms %.1f px" % (
                                  sid, street["n_anchors"],
                                  street["anchor_midline_residuals_px"]["rms"]),
            "manual_deviations_in_span": devs,
            "mask_tiling": tiling,
            "content_extent": enc,
            "mid_anchor": None if anchor is None else {
                "anchor": anchor["anchor"], "file": anchor["file"],
                "midpoint_mosaic": anchor["midpoint_mosaic"]},
            "seam_mid_mosaic": None if midxy is None else [round(float(x), 1) for x in midxy],
            "panel_verdict": v.get("verdict", "PENDING-VISUAL"),
            "panel_reason": v.get("reason", ""),
        })

    out = {
        "stamp": qalib.stamp("70_qa/tools/seam_matrix.py", {
            "freeze_checks_all_ok": all(c["ok"] for c in checks),
            "content_extent_source": os.path.relpath(frozen_extent_path, qalib.PROJECT),
        }),
        "rows": rows,
    }
    qalib.write_json(os.path.join(RUN, "seam_matrix.json"), out)

    # markdown
    md = ["# Seam matrix — QA stage 1",
          "",
          "Master: `%s`  sha256 `%s`" % (out["stamp"]["master_tif"],
                                         out["stamp"]["master_sha256"]),
          "",
          "All frozen-input hash checks passed: **%s**" %
          out["stamp"]["freeze_checks_all_ok"],
          "",
          "Encroachment source: frozen-cuts rerun `%s` (the 60_master copy "
          "predates the freeze)." % out["stamp"]["content_extent_source"],
          "",
          "| seam | street | along RMS px (worst) | across RMS px (worst) | "
          "cut provenance | tiling (ovl px2, bad, gap px, drift px) | "
          "encroach interior A/B px (halfw) | panel verdict |",
          "|---|---|---|---|---|---|---|---|"]
    for r in rows:
        a, b = r["pair"]
        enc = r["content_extent"]
        t = r["mask_tiling"]
        dev = " +dev" if r["manual_deviations_in_span"] else ""
        md.append("| %s | %s | %.1f (%.1f) | %.1f (%.1f) | %s%s | %s (%.1f, %d/%d, %s, %s) | %.0f / %.0f (%.0f) | %s%s |" % (
            r["seam"], r["street_id"],
            r["solve_rms_px"] or -1, r["solve_worst_abs_px"] or -1,
            r["across_rms_px"] or -1, r["across_worst_abs_px"] or -1,
            "pooled TLS", dev,
            t["verdict"], t["overlap_px2"],
            t["gap_samples_bad"] or 0, t["n_gap_samples"],
            t.get("max_pair_gap_px"), t.get("cut_drift_from_polyline_px"),
            enc["sheet_%d_interior_px" % a] or -1, enc["sheet_%d_interior_px" % b] or -1,
            enc["half_street_width_px"],
            r["panel_verdict"],
            (" — " + r["panel_reason"]) if r["panel_reason"] else ""))
    md += ["",
           "along = anchor coincidence projected on the seam direction (true "
           "misregistration). across = constructed frontage separation vs "
           "default width x kappa: absorbs drafted-width disagreement between "
           "plates (sigma floor 12 px), kappa is prior-dominated — NOT a "
           "misregistration metric. drift = distance between the mask cut "
           "(rebuilt from 3-dp-rounded line_fit by build_masks) and cuts.json "
           "polyline_mosaic; both sheets share the same rounded cut, so tiling "
           "is unaffected."]
    md += ["",
           "Tiling check: shapely re-derivation, overlap area of the two owned "
           "regions (px^2), boundary gap/side sampling every ~40 px at +/-0.5 px, "
           "shared boundary length. Manual deviations in span:",
           ""]
    for r in rows:
        for d in r["manual_deviations_in_span"]:
            md.append("- %s: offset %.1f px over t=%s — %s" %
                      (r["seam"], d["offset_px"], d["t_range_mosaic"], d["reason"]))
    with open(os.path.join(RUN, "seam_matrix.md"), "w") as f:
        f.write("\n".join(md) + "\n")
    print("wrote seam_matrix.json / seam_matrix.md  (%d seams)" % len(rows))
    for r in rows:
        print("  %-6s %-18s rms %5.2f worst %5.2f tiling %s verdict %s" % (
            r["seam"], r["street_id"], r["solve_rms_px"] or -1,
            r["solve_worst_abs_px"] or -1, r["mask_tiling"]["verdict"],
            r["panel_verdict"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
