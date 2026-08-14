#!/usr/bin/env python3
"""06 -- Assemble and refine the control-point set.

A control point here is a feature identified on a sheet. When the SAME
point_id appears on two sheets, those two observations become a tie that
mathematically forces the sheets to meet -- which is the whole basis of the
reconstruction. Preferred features, in order: street-centreline intersections,
block corners, wharf/waterfront geometry. Individual buildings are avoided;
they burn down, get rebuilt and get redrawn between editions.

This script:
  * loads the human-authored control CSV (the authority);
  * drops observations that fall outside a kept region's mask -- this is where
    Sheet 1's detached section gets filtered out, so its points can never
    influence the adjustment;
  * optionally refines each observation by predictive normalised
    cross-correlation, using a prior transform so matching happens in a common
    frame instead of blindly (--refine);
  * optionally proposes extra ties where sheets genuinely overlap (--auto);
  * reports coverage per region and per pair, because clustered points give
    good residuals and a bad mosaic.

Outputs
    gcps/tiepoints.csv / .geojson      the accepted control set
    output/qc/gcp_coverage.md
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sanborn import masks as M
from sanborn.config import (all_regions, load_config, paths, read_json,
                            regions_from_config, setup_logging, write_json)
from sanborn.render import image_size, read_image
from sanborn.tiepoints import (read_gcp_csv, ties_from_rows, write_gcp_csv,
                               write_gcp_geojson)


def source_dir(cfg, p):
    sub = (cfg.get("paths") or {}).get("original_dir")
    return Path(cfg["_root"]) / sub if sub else p.original


def load_masks(cfg, p, log):
    """region_id -> (ring, keep, sheet_file)."""
    out = {}
    for sheet in cfg.get("sheets", []):
        for reg in sheet.get("regions", []):
            rel = reg.get("mask")
            if not rel:
                continue
            path = Path(cfg["_root"]) / rel
            if not path.exists():
                log.warning("mask file missing for %s: %s", reg["id"], path)
                continue
            doc = M.read_mask(path)
            for rid, ring, props in M.regions(doc, keep_only=False):
                if rid == reg["id"]:
                    out[rid] = (ring, bool(props.get("keep", True)),
                                sheet.get("file", ""))
    return out


def inside(ring, pt):
    import cv2
    poly = np.round(np.asarray(ring, dtype=float)).astype(np.int32)
    return cv2.pointPolygonTest(poly, (float(pt[0]), float(pt[1])), False) >= 0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--profile", default="galveston1889")
    ap.add_argument("--input", default="", help="control CSV (default: per profile)")
    ap.add_argument("--refine", action="store_true",
                    help="sub-pixel refine each observation by predictive NCC")
    ap.add_argument("--auto", action="store_true",
                    help="propose extra ties in genuine overlap areas")
    ap.add_argument("--min-score", type=float, default=0.5)
    args = ap.parse_args()

    cfg = load_config(args.profile)
    p = paths().ensure()
    log = setup_logging("06_detect_or_define_gcps")

    default_csv = (p.gcps / ("synthetic_tiepoints.csv" if args.profile == "synthetic"
                             else "tiepoints_manual.csv"))
    csv_path = Path(args.input) if args.input else default_csv
    if not csv_path.exists():
        log.error("no control CSV at %s", csv_path)
        log.error("Create it by identifying the same feature on adjacent sheets: "
                  "give both rows the SAME point_id. Columns are documented in "
                  "sanborn/tiepoints.py (GCP_FIELDS).")
        return 2

    rows = read_gcp_csv(csv_path)
    log.info("loaded %d control observation(s) from %s", len(rows), csv_path)

    kept_ids = {r["region_id"] for r in regions_from_config(cfg)}
    all_ids = {r["id"] for r in all_regions(cfg)}
    region_masks = load_masks(cfg, p, log)

    accepted, rejected = [], []
    for r in rows:
        rid = r.get("region", "")
        if rid not in all_ids:
            r["note"] = (r.get("note", "") + " | unknown region id").strip(" |")
            rejected.append(("unknown region", r))
            continue
        if rid not in kept_ids:
            rejected.append(("region excluded from mosaic", r))
            continue
        mk = region_masks.get(rid)
        if mk and not inside(mk[0], (r["src_x"], r["src_y"])):
            rejected.append(("outside region mask", r))
            continue
        accepted.append(r)

    by_reason = Counter(reason for reason, _ in rejected)
    for reason, n in by_reason.items():
        log.info("rejected %d observation(s): %s", n, reason)
    log.info("%d observation(s) accepted", len(accepted))

    # ---- optional refinement ----------------------------------------------
    if args.refine or args.auto:
        from sanborn import geometry as G
        from sanborn.tiepoints import auto_tiepoints_in_overlap, refine_pair

        src = source_dir(cfg, p)
        files = {}
        for sheet in cfg.get("sheets", []):
            for reg in sheet.get("regions", []):
                files[reg["id"]] = src / sheet.get("file", "")
        images = {}

        def img_for(rid):
            if rid not in images:
                images[rid] = read_image(files[rid])
            return images[rid]

        ties = ties_from_rows(accepted)
        regions = sorted({r["region"] for r in accepted})
        anchor = (cfg.get("geometry") or {}).get("anchor_region") or regions[0]
        try:
            prior = G.adjust(regions, ties, kind="similarity", anchor_sheet=anchor,
                             robust=True)["transforms"]
        except Exception as exc:
            log.warning("could not fit a prior transform (%s); refinement skipped", exc)
            prior = None

        if prior and args.refine:
            by_pt = defaultdict(list)
            for r in accepted:
                by_pt[r["point_id"]].append(r)
            n_moved, moves = 0, []
            for pid, obs in by_pt.items():
                if len(obs) < 2:
                    continue
                base = obs[0]
                for other in obs[1:]:
                    if base["region"] not in prior or other["region"] not in prior:
                        continue
                    res = refine_pair(
                        img_for(base["region"]), (base["src_x"], base["src_y"]),
                        img_for(other["region"]), (other["src_x"], other["src_y"]),
                        prior[base["region"]], prior[other["region"]],
                        min_score=args.min_score)
                    if res["score"] is None or res["score"] < args.min_score:
                        continue
                    shift = float(np.hypot(res["dx"], res["dy"]))
                    if shift > 40:
                        log.warning("  %s: refinement moved %.1f px -- rejected as "
                                    "an implausible jump", pid, shift)
                        continue
                    other["src_x"], other["src_y"] = res["refined"]
                    other["method"] = (other.get("method", "") + " + NCC refine").strip(" +")
                    n_moved += 1
                    moves.append(shift)
            if moves:
                log.info("refined %d observation(s); median shift %.2f px, max %.2f px",
                         n_moved, float(np.median(moves)), float(np.max(moves)))
            else:
                log.info("refinement produced no accepted corrections")

        if prior and args.auto:
            from shapely.geometry import Polygon
            added = 0
            rings = {rid: M.regions(M.read_mask(Path(cfg["_root"]) / rel), False)
                     for rid, rel in []}   # placeholder; overlap uses masks below
            planes = {}
            for rid, (ring, keep, _f) in region_masks.items():
                if rid in prior:
                    planes[rid] = G.apply(prior[rid], ring)
            ids = sorted(planes)
            for i in range(len(ids)):
                for j in range(i + 1, len(ids)):
                    a, b = ids[i], ids[j]
                    pa, pb = Polygon(planes[a]).buffer(0), Polygon(planes[b]).buffer(0)
                    inter = pa.intersection(pb)
                    if inter.is_empty or inter.area < 5000:
                        continue
                    cands = auto_tiepoints_in_overlap(
                        img_for(a), img_for(b), prior[a], prior[b],
                        np.array(inter.exterior.coords), min_score=args.min_score)
                    for k, c in enumerate(cands):
                        pid = f"AUTO_{a}_{b}_{k:02d}"
                        for rid, pt in ((a, c["pa"]), (b, c["pb"])):
                            accepted.append({
                                "point_id": pid, "sheet": rid, "region": rid,
                                "role": "tie", "src_x": round(pt[0], 2),
                                "src_y": round(pt[1], 2),
                                "feature": "auto NCC match in overlap",
                                "method": "predictive NCC", "confidence": "medium",
                                "selected_by": "06 --auto", "accepted": "true",
                                "note": f"score={c['score']:.3f}"})
                        added += 1
            log.info("auto-proposed %d tie point(s) in overlap areas", added)

    # ---- coverage report ---------------------------------------------------
    ties = ties_from_rows(accepted)
    per_region = Counter(r["region"] for r in accepted)
    per_pair = Counter(tuple(sorted([t.a, t.b])) for t in ties)

    log.info("control coverage:")
    thin = []
    for rid in sorted(kept_ids):
        n = per_region.get(rid, 0)
        pts = np.array([[r["src_x"], r["src_y"]] for r in accepted
                        if r["region"] == rid], dtype=float)
        spread = ""
        if len(pts) >= 3:
            c = pts - pts.mean(0)
            sv = np.linalg.svd(c, compute_uv=False)
            ratio = sv[0] / max(sv[1], 1e-9)
            spread = f"  spread ratio {ratio:6.2f}" + \
                     ("  <-- nearly collinear" if ratio > 8 else "")
        flag = "  <-- THIN" if n < 6 else ""
        log.info("   %-16s %3d observation(s)%s%s", rid, n, spread, flag)
        if n < 6:
            thin.append(rid)
    log.info("tie points per sheet pair:")
    for (a, b), n in sorted(per_pair.items()):
        log.info("   %-14s %-14s %3d%s", a, b, n, "  <-- THIN" if n < 3 else "")

    if thin:
        log.warning("regions with fewer than 6 control observations: %s. The brief "
                    "targets 6-12 well-distributed points per region.", thin)

    write_gcp_csv(p.gcps / "tiepoints.csv", accepted)
    # Stamp the profile so a later step cannot silently consume another
    # profile's control points (see config.require_profile).
    write_json(p.gcps / "tiepoints.meta.json",
               {"profile": args.profile, "source_csv": str(csv_path),
                "accepted": len(accepted), "rejected": len(rejected)})
    write_gcp_geojson(p.gcps / "tiepoints.geojson", accepted)
    write_json(p.gcps / "rejected.json",
               [{"reason": reason, **{k: v for k, v in r.items()}}
                for reason, r in rejected])

    md = ["# Control point coverage", "", f"Profile `{args.profile}`", "",
          f"- input: `{csv_path}`", f"- accepted: {len(accepted)}",
          f"- rejected: {len(rejected)} ({dict(by_reason)})",
          f"- tie observations: {len(ties)}", "",
          "| region | observations |", "|---|---|"]
    for rid in sorted(kept_ids):
        md.append(f"| {rid} | {per_region.get(rid,0)} |")
    md += ["", "| pair | shared points |", "|---|---|"]
    for (a, b), n in sorted(per_pair.items()):
        md.append(f"| {a} - {b} | {n} |")
    (p.qc / "gcp_coverage.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    log.info("wrote %s (%d observations, %d ties)", p.gcps / "tiepoints.csv",
             len(accepted), len(ties))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
