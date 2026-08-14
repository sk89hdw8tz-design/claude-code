#!/usr/bin/env python3
"""07 -- Solve every sheet transform at once, and justify the model chosen.

METHOD
    All sheets are solved jointly (a block adjustment), not one at a time.
    Fitting sheets independently and hoping they line up is what produces the
    classic mosaic where each seam is individually plausible and the whole is
    skewed. Here, one tie point observed on two sheets contributes a single
    equation forcing those sheets to agree, and every equation is solved
    together.

    One region is held fixed to remove the gauge freedom (a tie-point network
    alone determines the solution only up to a global transform). Holding a
    real sheet at identity also makes the reconstruction plane that sheet's own
    pixel grid, so every residual is readable as original scan pixels.

MODEL SELECTION
    Progressive, least deformable first, and a richer model must EARN its extra
    freedom by improving held-out (cross-validated) error, not fitting error.
    Two hard gates run first:

      * Rank check. Sheets that abut along a line give only collinear tie
        points, and a per-sheet affine model is then rank deficient -- there is
        an exact shear of the plane that leaves every residual near zero while
        deforming the sheets to nonsense. Measured on a 2x2 test network: affine
        nullity 4, similarity nullity 0. A rank-deficient model is refused
        outright however good its residuals look.

      * Plausibility. A solved sheet whose scale, rotation or shear exceeds what
        a scanned page can physically explain is reported loudly. The job is to
        correct page and scan geometry, not to rewrite the 1889 survey.

Outputs
    working/transforms.json
    gcps/residuals.json
    output/qc/transform_report.md
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sanborn import geometry as G
from sanborn import qc as QC
from sanborn.config import (ProfileMismatch, load_config, paths, read_json,
                            regions_from_config, require_profile, setup_logging,
                            utcnow, write_json)
from sanborn.tiepoints import read_gcp_csv, ties_from_rows

def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--profile", default="galveston1889")
    ap.add_argument("--kind", default="", help="force a transform family")
    args = ap.parse_args()

    cfg = load_config(args.profile)
    p = paths().ensure()
    log = setup_logging("07_fit_and_evaluate_transforms")
    geo = cfg.get("geometry", {})

    csv_path = p.gcps / "tiepoints.csv"
    if not csv_path.exists():
        log.error("no %s -- run 06_detect_or_define_gcps.py first", csv_path)
        return 2
    meta_path = p.gcps / "tiepoints.meta.json"
    if not meta_path.exists():
        log.error("no %s -- re-run 06_detect_or_define_gcps.py so the control "
                  "set is stamped with its profile", meta_path)
        return 2
    try:
        require_profile(read_json(meta_path), args.profile, meta_path, log)
    except ProfileMismatch:
        return 6
    rows = read_gcp_csv(csv_path)
    regions = [r["region_id"] for r in regions_from_config(cfg)]
    ties = [t for t in ties_from_rows(rows) if t.a in regions and t.b in regions]
    log.info("%d region(s), %d tie observation(s)", len(regions), len(ties))
    if not ties:
        log.error("no tie points connect any two regions -- nothing to solve")
        return 3

    anchor = geo.get("anchor_region") or regions[0]
    if anchor not in regions:
        log.error("anchor_region %r is not a kept region", anchor)
        return 4
    log.info("anchor region (held at identity): %s", anchor)

    cw = float(geo.get("conformal_weight", 0.0))
    kw = dict(anchor_sheet=anchor, robust=bool(geo.get("robust", True)),
              huber_delta=float(geo.get("huber_delta", 6.0)))

    # ---- gates + selection -------------------------------------------------
    candidates = [args.kind] if args.kind else list(geo.get("candidates",
                                                            ["similarity", "affine"]))
    log.info("candidate models: %s (conformal_weight=%.1f)", candidates, cw)
    for kind in candidates:
        rank = G.design_rank_report(regions, ties, kind=kind, anchor_sheet=anchor,
                                    conformal_weight=cw)
        det = G.check_determinacy(regions, ties, kind=kind)
        log.info("  %-11s params=%-3d rank=%-3d nullity=%d cond=%s%s",
                 kind, rank["ncol"], rank["rank"], rank["nullity"],
                 f"{rank['condition']:.1f}" if rank["condition"] else "n/a",
                 "  <-- RANK DEFICIENT" if rank["nullity"] else "")
        if rank["nullity"]:
            log.warning("     %s", rank["note"])
        if det["underdetermined"]:
            log.warning("     too few points on: %s", det["underdetermined"])

    sel = QC.select_transform(regions, ties, candidates=candidates,
                              conformal_weight=cw,
                              folds=int(geo.get("crossval_folds", 5)),
                              tolerance=float(geo.get("improvement_tolerance", 0.9)),
                              **kw)
    for c in sel["candidates"]:
        if c.get("score") is not None:
            log.info("  %-11s cross-validated median %.3f px (fit median %.3f px)",
                     c["kind"], c["score"], c["fit_stats"]["median"])
        else:
            log.info("  %-11s UNUSABLE: %s", c["kind"], c.get("reason", "?"))
    kind = args.kind or sel["chosen"]
    if not kind:
        log.error("no usable transform model. Add tie points with real 2-D "
                  "spread on each sheet, or allow 'similarity'.")
        return 5
    log.info("SELECTED MODEL: %s", kind)

    # ---- final fit ---------------------------------------------------------
    fit = G.adjust(regions, ties, kind=kind, conformal_weight=cw, **kw)
    stats = fit["stats"]
    log.info("fit residuals: n=%d median=%.2f rms=%.2f p90=%.2f max=%.2f px",
             stats["n"], stats["median"], stats["rms"], stats["p90"], stats["max"])

    cv = QC.crossvalidate(regions, ties, kind=kind, conformal_weight=cw,
                          folds=int(geo.get("crossval_folds", 5)), **kw)
    if cv.get("held_out"):
        h = cv["held_out"]
        log.info("held-out residuals: n=%d median=%.2f rms=%.2f max=%.2f px",
                 h["n"], h["median"], h["rms"], h["max"])

    good = float(cfg["qc"]["good_residual_px"])
    gross = float(cfg["qc"]["gross_residual_px"])
    report = QC.residual_report(fit["residuals"], (good, gross))
    log.info("seam mismatch by pair (target median <= %.0f px):", good)
    for pair, s in report["by_pair"].items():
        flag = "  <-- OVER TARGET" if s["median"] > good else ""
        log.info("   %-30s n=%3d median=%6.2f max=%6.2f%s",
                 pair, s["n"], s["median"], s["max"], flag)
    for w in report["worst"][:5]:
        if w["residual"] > gross:
            log.warning("   gross mismatch %.1f px at %s (%s)", w["residual"],
                        w["label"], w["sheets"])

    # ---- plausibility ------------------------------------------------------
    log.info("solved sheet geometry:")
    implausible = []
    decomp = {}
    for rid in regions:
        d = G.decompose_affine(fit["transforms"][rid])
        decomp[rid] = d
        bad = G.plausibility_flags(fit["transforms"][rid])
        log.info("   %-16s scale %.4f/%.4f  rot %+6.2f deg  shear %+5.2f deg  aniso %.4f%s",
                 rid, d["scale_x"], d["scale_y"], d["rotation_deg"], d["shear_deg"],
                 d["anisotropy"], ("  <-- " + ",".join(bad)) if bad else "")
        if bad:
            implausible.append((rid, bad))
    if implausible:
        log.warning("implausible sheet geometry on %d region(s): %s",
                    len(implausible), implausible)
        log.warning("Check the control points on those sheets before trusting "
                    "the mosaic -- a scanned page cannot do this.")

    write_json(p.working / "transforms.json", {
        "generated_utc": utcnow(), "profile": args.profile, "kind": kind,
        "anchor_region": anchor, "conformal_weight": cw,
        "selection": sel,
        "transforms": {k: np.asarray(v).tolist() for k, v in fit["transforms"].items()},
        "decomposition": decomp,
        "fit_stats": stats,
        "crossval": {k: v for k, v in cv.items() if k != "detail"},
        "implausible": [{"region": r, "flags": f} for r, f in implausible],
    })
    write_json(p.gcps / "residuals.json",
               {"kind": kind, "report": report, "residuals": fit["residuals"],
                "crossval_detail": cv.get("detail", [])})

    md = ["# Transform fitting", "", f"Profile `{args.profile}` -- {utcnow()}", "",
          f"- model selected: **{kind}**", f"- anchor region: `{anchor}`",
          f"- conformal weight: {cw}", f"- tie observations: {len(ties)}", "",
          "## Model comparison", "",
          "| model | usable | cross-validated median (px) | fit median (px) | note |",
          "|---|---|---|---|---|"]
    for c in sel["candidates"]:
        md.append("| {} | {} | {} | {} | {} |".format(
            c["kind"], c.get("usable"),
            f"{c['score']:.3f}" if c.get("score") is not None else "-",
            f"{c['fit_stats']['median']:.3f}" if c.get("fit_stats") else "-",
            c.get("reason", c["rank"].get("note", ""))))
    md += ["", "## Residuals by sheet pair", "",
           "| pair | n | median | p90 | max | over target | gross |", "|---|---|---|---|---|---|---|"]
    for pair, s in report["by_pair"].items():
        md.append(f"| {pair} | {s['n']} | {s['median']:.2f} | {s['p90']:.2f} | "
                  f"{s['max']:.2f} | {s['over_good']} | {s['over_gross']} |")
    md += ["", "## Solved sheet geometry", "",
           "| region | scale x | scale y | rotation | shear | anisotropy |",
           "|---|---|---|---|---|---|"]
    for rid in regions:
        d = decomp[rid]
        md.append(f"| {rid} | {d['scale_x']:.4f} | {d['scale_y']:.4f} | "
                  f"{d['rotation_deg']:+.2f} | {d['shear_deg']:+.2f} | {d['anisotropy']:.4f} |")
    (p.qc / "transform_report.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    log.info("wrote %s", p.working / "transforms.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
