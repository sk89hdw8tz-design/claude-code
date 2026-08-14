#!/usr/bin/env python3
"""11 -- Independent quality control on the finished mosaic.

A GeoTIFF existing is not success. This script tries to find what is wrong with
the result, and reports it whether or not the numbers are flattering.

Three independent lines of evidence
    1. RESIDUALS at control points, and -- more importantly -- at HELD-OUT
       control points the adjustment never saw. Fitting error can always be
       driven down by adding parameters; held-out error cannot.
    2. SEAM PANELS at every junction, cropped at full resolution and rendered
       three ways: sheet A alone, sheet B alone, and the merged mosaic. Seeing
       each contributor separately is what distinguishes a street that genuinely
       runs through from one that only appears to because the upper sheet is
       painted over the lower sheet's error.
    3. A PIXEL-STEP measurement across each seam line, compared against the
       image's own local variation, so a visible join can be quantified rather
       than argued about.

Interpreting the thresholds
    The brief targets a median seam mismatch around 5 px with nothing
    unexplained beyond 10-15 px. Those are goals, not laws. An 1889 sheet
    contains real drafting and surveying inconsistency, and where two sheets
    genuinely disagree about where a street was, no transform can make both
    right. This script therefore separates "over target" from "explained", and
    flags anything that looks like PROCESSING error -- a systematic shift along
    a whole seam, a rotation, a scale step -- as distinct from scattered
    disagreement, which is the signature of source inconsistency.

Outputs
    output/qc/seam_report/<pair>_<n>.png
    output/qc/qc_report.md
    output/qc/qc_summary.json
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sanborn import geometry as G
from sanborn import masks as M
from sanborn import qc as QC
from sanborn.config import (ProfileMismatch, load_config, paths, read_json,
                            require_profile, setup_logging,
                            utcnow, write_json)
from sanborn.render import OutputGrid
from sanborn.tiepoints import read_gcp_csv, ties_from_rows


def classify_seam(residuals):
    """Systematic shift (processing) vs scattered spread (source disagreement).

    A whole seam displaced in one direction points at the transform; residuals
    of similar size pointing every which way point at the 1889 draughtsman.
    """
    if len(residuals) < 3:
        return {"verdict": "too few points to classify", "bias": None, "scatter": None}
    d = np.array([[r["dx"], r["dy"]] for r in residuals], dtype=float)
    bias = float(np.hypot(*d.mean(axis=0)))
    scatter = float(np.median(np.hypot(*(d - d.mean(axis=0)).T)))
    if bias > 2.0 * max(scatter, 1e-6):
        verdict = ("SYSTEMATIC -- the whole seam is displaced; suspect the "
                   "transform or a mis-identified control point")
    elif scatter > 2.0 * max(bias, 1e-6):
        verdict = ("SCATTERED -- consistent with drafting/survey disagreement "
                   "between the two 1889 sheets rather than processing error")
    else:
        verdict = "mixed"
    return {"verdict": verdict, "bias": bias, "scatter": scatter}


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--profile", default="galveston1889")
    ap.add_argument("--samples", type=int, default=0)
    args = ap.parse_args()

    cfg = load_config(args.profile)
    p = paths().ensure()
    log = setup_logging("11_quality_control")

    gdoc = read_json(p.working / "grid.json")
    try:
        require_profile(gdoc, args.profile, p.working / "grid.json", log)
    except ProfileMismatch:
        return 6
    grid = OutputGrid.from_dict(gdoc["grid"])
    tdoc = read_json(p.working / "transforms.json")
    rdoc = read_json(p.gcps / "residuals.json")
    master = p.output / cfg["output"]["master_name"]
    if not master.exists():
        log.error("no master at %s -- run 10_build_mosaic.py", master)
        return 2

    good = float(cfg["qc"]["good_residual_px"])
    gross = float(cfg["qc"]["gross_residual_px"])
    samples = args.samples or int(cfg["qc"].get("seam_samples_per_pair", 5))
    size = int(cfg["qc"].get("seam_crop_size", 520))
    zoom = int(cfg["qc"].get("seam_zoom", 2))

    # ---- 1. residuals ------------------------------------------------------
    report = rdoc["report"]
    ov = report["overall"]
    log.info("=== residuals at control points (model: %s) ===", tdoc["kind"])
    log.info("n=%d median=%.2f rms=%.2f p90=%.2f max=%.2f px",
             ov["n"], ov["median"], ov["rms"], ov["p90"], ov["max"])
    cvs = (tdoc.get("crossval") or {}).get("held_out")
    if cvs:
        log.info("HELD-OUT (never fitted): n=%d median=%.2f rms=%.2f max=%.2f px",
                 cvs["n"], cvs["median"], cvs["rms"], cvs["max"])

    verdict_overall = []
    if ov["median"] <= good:
        verdict_overall.append(f"median {ov['median']:.2f} px meets the <= {good:.0f} px target")
    else:
        verdict_overall.append(f"median {ov['median']:.2f} px EXCEEDS the {good:.0f} px target")
    if ov["max"] > gross:
        verdict_overall.append(f"{ov['over_gross']} point(s) exceed {gross:.0f} px")

    # ---- 2. per-seam classification ---------------------------------------
    by_pair = defaultdict(list)
    for r in rdoc["residuals"]:
        if r["kind"] != "tie":
            continue
        by_pair[tuple(sorted([r["sheet_a"], r["sheet_b"]]))].append(r)

    log.info("=== seam-by-seam ===")
    seam_rows = []
    for pair, res in sorted(by_pair.items()):
        vals = np.array([r["residual"] for r in res])
        cls = classify_seam(res)
        flag = ""
        if np.median(vals) > good:
            flag = "  <-- OVER TARGET"
        log.info("%-14s %-14s n=%2d median=%5.2f max=%6.2f  bias=%5.2f scatter=%5.2f%s",
                 pair[0], pair[1], len(res), float(np.median(vals)), float(vals.max()),
                 cls["bias"] or 0.0, cls["scatter"] or 0.0, flag)
        log.info("                              %s", cls["verdict"])
        seam_rows.append({"pair": list(pair), "n": len(res),
                          "median": float(np.median(vals)), "max": float(vals.max()),
                          **cls})

    # ---- 3. seam panels ----------------------------------------------------
    log.info("=== seam panels ===")
    rings = {}
    for w in gdoc["regions"]:
        rid = w["region_id"]
        rings[rid] = None
    for sheet in cfg.get("sheets", []):
        for reg in sheet.get("regions", []):
            if reg["id"] not in rings or not reg.get("mask"):
                continue
            doc = M.read_mask(Path(cfg["_root"]) / reg["mask"])
            for r, ring, _ in M.regions(doc, keep_only=False):
                if r == reg["id"]:
                    H = np.asarray(tdoc["transforms"][r], dtype=float)
                    rings[r] = G.apply(H, ring)

    contacts = {}
    for pair in by_pair:
        a, b = pair
        if rings.get(a) is not None and rings.get(b) is not None:
            contacts[pair] = QC.contact_type(rings[a], rings[b])
    corner_pairs = [p_ for p_, c in contacts.items() if c["contact"] == "corner"]
    if corner_pairs:
        log.info("corner contacts (diagonal neighbours -- they share only a "
                 "corner, carry few tie points, and are the weakest-constrained "
                 "joins by construction): %s",
                 ", ".join(f"{a}|{b}" for a, b in sorted(corner_pairs)))
    for row in seam_rows:
        c = contacts.get(tuple(row["pair"]))
        row["contact"] = c["contact"] if c else "unknown"
        row["extent_ratio"] = c["extent_ratio"] if c else None

    paths_by_region = {w["region_id"]: w["path"] for w in gdoc["regions"]}
    made, steps, skipped = [], [], []
    for pair in sorted(by_pair):
        a, b = pair
        if rings.get(a) is None or rings.get(b) is None:
            continue
        pts = QC.shared_boundary_points(rings[a], rings[b], samples=samples)
        if not pts:
            log.warning("%s | %s: could not locate a shared boundary to sample", a, b)
            continue
        for i, pt in enumerate(pts):
            panel = QC.seam_panel(
                master, [paths_by_region[a], paths_by_region[b]], pt, grid,
                size=size, zoom=zoom, labels=(a, b),
                title=f"{a} | {b}  seam sample {i+1}/{len(pts)}  "
                      f"plane ({pt[0]:.0f}, {pt[1]:.0f})")
            out = p.seams / f"{a}__{b}__{i+1:02d}.png"
            cv2.imwrite(str(out), cv2.cvtColor(panel, cv2.COLOR_RGB2BGR))
            made.append(str(out))

            nxt = pts[min(i + 1, len(pts) - 1)]
            d = (nxt[0] - pt[0], nxt[1] - pt[1]) if nxt != pt else (0.0, 1.0)
            st = QC.seam_discontinuity(master, grid, pt, d, size=min(size, 256))
            if st and st.get("ratio"):
                steps.append({"pair": [a, b], "sample": i + 1,
                              "contact": contacts.get(pair, {}).get("contact", "?"),
                              **st})
            elif st and st.get("skipped"):
                skipped.append({"pair": [a, b], "sample": i + 1, **st})
        log.info("%-14s %-14s %d panel(s)", a, b, len(pts))

    if steps:
        ratios = np.array([s["ratio"] for s in steps], dtype=float)
        tones = np.array([abs(s.get("tone_offset") or 0.0) for s in steps], dtype=float)
        log.info("structural step across seams: median ratio %.2f (1.0 = the join "
                 "is indistinguishable from ordinary adjacent pixels), max %.2f",
                 float(np.median(ratios)), float(ratios.max()))
        log.info("scan tone difference across seams: median %.1f grey levels, "
                 "max %.1f -- PRESERVED deliberately, not a defect (no exposure "
                 "matching is applied)", float(np.median(tones)), float(tones.max()))
        edge_steps = [s for s in steps if s.get("contact") == "edge"]
        if edge_steps:
            er = np.array([s["ratio"] for s in edge_steps], float)
            log.info("   restricted to true EDGE seams: median ratio %.2f, max %.2f "
                     "over %d sample(s)", float(np.median(er)), float(er.max()),
                     len(edge_steps))
        pool = edge_steps or steps
        worst = max(pool, key=lambda s: s["ratio"])
        if worst["ratio"] > 3.0:
            log.warning("SCREENING FLAG (not a verdict): largest structural step at "
                        "%s sample %d (ratio %.2f, %s contact). Inspect the panel in "
                        "output/qc/seam_report/; the ratio is oversensitive where a "
                        "seam crosses near-blank paper. Residuals are authoritative.",
                        worst["pair"], worst["sample"], worst["ratio"],
                        worst.get("contact", "?"))
        else:
            log.info("no seam sample shows a step above 3x local variation")
    if skipped:
        log.info("%d seam sample(s) not measured: they touch the mosaic's outer "
                 "edge, where the step is against empty space rather than "
                 "another sheet", len(skipped))

    # ---- coverage / collar check ------------------------------------------
    import rasterio
    with rasterio.open(master) as ds:
        step = max(1, int(max(ds.width, ds.height) / 3000))
        a4 = ds.read(4, out_shape=(max(1, ds.height // step), max(1, ds.width // step)))
        coverage = float((a4 > 0).mean())
        holes = int((a4 == 0).sum())
    log.info("coverage %.1f%% (transparent %.1f%% -- genuine gaps, nothing invented)",
             100 * coverage, 100 * (1 - coverage))

    summary = {
        "generated_utc": utcnow(), "profile": args.profile,
        "model": tdoc["kind"], "anchor_region": tdoc["anchor_region"],
        "thresholds": {"good_px": good, "gross_px": gross},
        "residuals_overall": ov, "held_out": cvs,
        "seams": seam_rows, "seam_panels": len(made),
        "seam_steps": steps, "seam_steps_skipped": skipped, "coverage_fraction": coverage,
        "implausible_regions": tdoc.get("implausible", []),
        "verdict": verdict_overall,
    }
    write_json(p.qc / "qc_summary.json", summary)

    md = ["# Quality control", "", f"Profile `{args.profile}` -- {summary['generated_utc']}",
          "", f"- transform model: **{tdoc['kind']}**",
          f"- anchor region: `{tdoc['anchor_region']}`",
          f"- coverage: {100*coverage:.1f}% (remainder transparent; no synthesised content)",
          "", "## Residuals", "",
          f"| set | n | median | rms | p90 | max |", "|---|---|---|---|---|---|",
          f"| at control points | {ov['n']} | {ov['median']:.2f} | {ov['rms']:.2f} | "
          f"{ov['p90']:.2f} | {ov['max']:.2f} |"]
    if cvs:
        md.append(f"| held out (cross-validated) | {cvs['n']} | {cvs['median']:.2f} | "
                  f"{cvs['rms']:.2f} | {cvs['p90']:.2f} | {cvs['max']:.2f} |")
    md += ["", f"Target: median <= {good:.0f} px, nothing unexplained above {gross:.0f} px.",
           "", "## Seams", "",
           "| sheet A | sheet B | contact | n | median px | max px | bias | scatter | reading |",
           "|---|---|---|---|---|---|---|---|---|"]
    for s in seam_rows:
        md.append(f"| {s['pair'][0]} | {s['pair'][1]} | {s.get('contact','?')} | "
                  f"{s['n']} | {s['median']:.2f} | "
                  f"{s['max']:.2f} | {(s['bias'] or 0):.2f} | {(s['scatter'] or 0):.2f} | "
                  f"{s['verdict']} |")
    md += ["", "`bias` is the mean displacement of the whole seam (a systematic "
           "shift points at processing); `scatter` is the spread about that mean "
           "(which points at genuine 1889 disagreement).", "",
           "## Seam panels", "",
           f"{len(made)} full-resolution panels in `output/qc/seam_report/`. "
           "Each shows sheet A alone, sheet B alone, then the merged mosaic, so a "
           "street that only *looks* continuous because one sheet covers the "
           "other's error is visible.", ""]
    if steps:
        ratios = [s["ratio"] for s in steps]
        md += [f"Pixel step across seams: median ratio {np.median(ratios):.2f}, "
               f"max {max(ratios):.2f} (1.0 = indistinguishable from ordinary "
               f"adjacent pixels).", ""]
    md += ["## Verdict", ""] + [f"- {v}" for v in verdict_overall]
    if tdoc.get("implausible"):
        md += ["", "**Implausible sheet geometry flagged:** " +
               ", ".join(f"`{d['region']}` ({'/'.join(d['flags'])})"
                         for d in tdoc["implausible"])]
    (p.qc / "qc_report.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    log.info("wrote %s and %d seam panel(s)", p.qc / "qc_report.md", len(made))
    for v in verdict_overall:
        log.info("VERDICT: %s", v)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
