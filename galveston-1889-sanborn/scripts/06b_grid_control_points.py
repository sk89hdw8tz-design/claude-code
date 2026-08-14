#!/usr/bin/env python3
"""06b -- Build control points from street/avenue centreline intersections.

THE IDEA
    Two adjoining Sanborn sheets both draw the street they share, and both draw
    the avenues crossing it. So the crossing of "22nd Street" with "Avenue B" is
    a single physical place that is measurable on BOTH sheets -- even though
    neither sheet necessarily draws the block corner there, because the corner
    belongs to whichever sheet owns that block.

    That gives the tie points their identity for free: the point_id is simply
    "22nd|B". Any two sheets that both see that crossing are tied by it, with no
    matching, no feature descriptors and no ambiguity. On a city grid where
    fifty blocks look alike, that is worth far more than any image-similarity
    method.

INPUT
    config/grid_positions.yaml -- per sheet, the approximate pixel position of
    each named street and avenue, read off the printed labels. Approximate is
    fine: this file supplies IDENTITY, and the refinement supplies PRECISION.

QUALITY GATES
    Each refined band reports how far it moved from its approximate position and
    how much its own slope disagreed with the sheet's shared rotation. A band
    that moved a long way has usually locked onto the wrong feature -- typically
    a street running along the sheet edge beside a railway or wharf, where the
    ink profile is confused. Those are dropped, loudly, rather than quietly
    poisoning the adjustment.

Outputs
    gcps/tiepoints_manual.csv      (consumed by 06_detect_or_define_gcps.py)
    output/qc/grid_control.md
    output/qc/grid_overlays/<sheet>.png    <- LOOK AT THESE
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter, defaultdict
from pathlib import Path

import cv2
import numpy as np
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sanborn import gridlines as GL
from sanborn.config import load_config, paths, setup_logging
from sanborn.render import read_image
from sanborn.tiepoints import write_gcp_csv, write_gcp_geojson


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--profile", default="galveston1889")
    ap.add_argument("--positions", default="config/grid_positions.yaml")
    ap.add_argument("--max-move", type=float, default=150.0,
                    help="reject a band that moved more than this from its approx position")
    ap.add_argument("--max-slope-dev", type=float, default=0.040,
                    help="reject a band whose own slope disagreed with the sheet rotation")
    ap.add_argument("--window", type=float, default=170.0)
    ap.add_argument("--min-rms", type=float, default=4.0,
                    help="reject a band whose fit is impossibly perfect. Blank "
                         "paper is perfectly flat, so the collar fits to <1px "
                         "while a real street band, with its lettering, kerbs "
                         "and pipe notes, fits to tens of px. A boundary street "
                         "legitimately has blocks on only one side, so 'ink on "
                         "both flanks' cannot be required -- those are exactly "
                         "the tie points we need.")
    args = ap.parse_args()

    cfg = load_config(args.profile)
    p = paths().ensure()
    log = setup_logging("06b_grid_control_points")
    root = Path(cfg["_root"])
    pos_path = root / args.positions
    if not pos_path.exists():
        log.error("no %s -- it must list, per sheet, the approximate pixel "
                  "position of each named street and avenue", pos_path)
        return 2
    doc = yaml.safe_load(pos_path.read_text(encoding="utf-8")) or {}
    sheets_cfg = {str(s["id"]): s for s in cfg.get("sheets", [])}
    src_dir = root / ((cfg.get("paths") or {}).get("original_dir") or "data/original")
    outdir = p.qc / "grid_overlays"
    outdir.mkdir(parents=True, exist_ok=True)

    rows, report, dropped = [], [], []
    for sheet_id, spec in (doc.get("sheets") or {}).items():
        sheet_id = str(sheet_id)
        scfg = sheets_cfg.get(sheet_id)
        if not scfg:
            log.warning("sheet %s in grid_positions.yaml is not in the profile", sheet_id)
            continue
        fname = spec.get("file") or scfg.get("file")
        img_path = src_dir / fname
        if not img_path.exists():
            log.error("sheet %s: image not found: %s", sheet_id, img_path)
            continue

        img = read_image(img_path)
        region_id = spec.get("region") or scfg["regions"][0]["id"]
        streets = {str(k): float(v) for k, v in (spec.get("streets") or {}).items()}
        avenues = {str(k): float(v) for k, v in (spec.get("avenues") or {}).items()}
        if not streets or not avenues:
            log.warning("sheet %s: needs both streets and avenues", sheet_id)
            continue

        # Clip band searches to the mapped area declared by this sheet's mask,
        # inset a little so the collar cannot be mistaken for a street.
        sb = ab = None
        mrel = (scfg.get("regions") or [{}])[0].get("mask")
        if mrel and (root / mrel).exists():
            from sanborn import masks as MM
            doc_m = MM.read_mask(root / mrel)
            regs = [r for r in MM.regions(doc_m, keep_only=False) if r[0] == region_id]
            if regs:
                bx0, by0, bx1, by1 = MM.ring_bounds(regs[0][1])
                pad = 45.0
                ab = (bx0 + pad, bx1 - pad)
                sb = (by0 + pad, by1 - pad)
        R = GL.refine_grid(img, streets, avenues, window=args.window,
                           street_bounds=sb, avenue_bounds=ab)
        log.info("sheet %-3s region %-16s rotation: streets %+0.3f deg, avenues %+0.3f deg",
                 sheet_id, region_id,
                 R["rotation_deg_streets"] or 0.0, R["rotation_deg_avenues"] or 0.0)

        def prune(bands, kind):
            keep = {}
            for name, b in bands.items():
                why = []
                if b["moved"] > args.max_move:
                    why.append(f"moved {b['moved']:.0f}px")
                if b["slope_deviation"] > args.max_slope_dev:
                    why.append(f"slope off by {b['slope_deviation']:.4f}")
                if b["rms"] < args.min_rms and b["moved"] > 60:
                    why.append(f"fit impossibly clean (rms {b['rms']:.1f}px) after "
                               f"moving {b['moved']:.0f}px - locked onto blank paper")
                if why:
                    log.warning("   DROP %s %-8s : %s", kind, name, "; ".join(why))
                    dropped.append({"sheet": sheet_id, "kind": kind, "name": name,
                                    "reason": "; ".join(why)})
                else:
                    log.info("   ok   %s %-8s offset=%8.1f moved=%5.1f rms=%5.1f",
                             kind, name, b["offset"], b["moved"], b["rms"])
                    keep[name] = b
            return keep

        R["streets"] = prune(R["streets"], "street")
        R["avenues"] = prune(R["avenues"], "avenue")
        if not R["streets"] or not R["avenues"]:
            log.error("sheet %s: nothing survived the quality gates", sheet_id)
            continue

        pts = GL.grid_intersections(R)
        for pt in pts:
            rows.append({
                "point_id": f"{pt['street']}|{pt['avenue']}",
                "sheet": sheet_id, "region": region_id, "role": "tie",
                "src_x": round(pt["x"], 2), "src_y": round(pt["y"], 2),
                "street_a": pt["street"], "street_b": pt["avenue"],
                "feature": "street centreline intersection",
                "method": "windowed low-ink band fit, shared sheet rotation",
                "confidence": "high" if pt["quality"] < 60 else "medium",
                "selected_by": "06b_grid_control_points.py",
                "accepted": "true",
                "note": f"band rms {pt['quality']:.1f}px",
            })
        report.append({"sheet": sheet_id, "region": region_id,
                       "streets": list(R["streets"]), "avenues": list(R["avenues"]),
                       "points": len(pts),
                       "rot_streets": R["rotation_deg_streets"],
                       "rot_avenues": R["rotation_deg_avenues"]})

        g = {"horizontal": list(R["streets"].values()),
             "vertical": list(R["avenues"].values()),
             "intersections": [{"x": q["x"], "y": q["y"]} for q in pts]}
        cv2.imwrite(str(outdir / f"sheet{sheet_id}.png"),
                    cv2.cvtColor(GL.overlay(img, g, max_dim=1600,
                                            labels_h=list(R["streets"]),
                                            labels_v=list(R["avenues"])),
                                 cv2.COLOR_RGB2BGR))

    if not rows:
        log.error("no control points produced")
        return 3

    # Which crossings are actually SHARED between sheets? Those are the ties.
    seen = defaultdict(set)
    for r in rows:
        seen[r["point_id"]].add(r["region"])
    shared = {k: v for k, v in seen.items() if len(v) > 1}
    pair_counts = Counter()
    for regs in shared.values():
        rl = sorted(regs)
        for i in range(len(rl)):
            for j in range(i + 1, len(rl)):
                pair_counts[(rl[i], rl[j])] += 1

    log.info("%d control observation(s); %d crossing(s) seen on more than one sheet",
             len(rows), len(shared))
    log.info("tie points per sheet pair:")
    for (a, b), n in sorted(pair_counts.items()):
        log.info("   %-14s %-14s %3d%s", a, b, n, "   <-- THIN" if n < 3 else "")
    if not pair_counts:
        log.error("NO crossing is shared between two sheets. The street/avenue "
                  "NAMES must match exactly across sheets for a crossing to be "
                  "recognised as the same place -- check config/grid_positions.yaml.")
        return 4

    write_gcp_csv(p.gcps / "tiepoints_manual.csv", rows)
    write_gcp_geojson(p.gcps / "tiepoints_manual.geojson", rows)

    md = ["# Grid-derived control points", "",
          "Control points are intersections of street and avenue centrelines. A "
          "crossing carries the same `point_id` on every sheet that shows it, "
          "which is what ties those sheets together.", "",
          "| sheet | region | streets kept | avenues kept | points | rot streets | rot avenues |",
          "|---|---|---|---|---|---|---|"]
    for r in report:
        md.append(f"| {r['sheet']} | {r['region']} | {', '.join(r['streets'])} | "
                  f"{', '.join(r['avenues'])} | {r['points']} | "
                  f"{(r['rot_streets'] or 0):+.3f}° | {(r['rot_avenues'] or 0):+.3f}° |")
    md += ["", "## Shared crossings per sheet pair", "", "| pair | shared points |", "|---|---|"]
    for (a, b), n in sorted(pair_counts.items()):
        md.append(f"| {a} – {b} | {n} |")
    if dropped:
        md += ["", "## Bands rejected by the quality gates", "",
               "| sheet | kind | name | reason |", "|---|---|---|---|"]
        for d in dropped:
            md.append(f"| {d['sheet']} | {d['kind']} | {d['name']} | {d['reason']} |")
    md += ["", "Overlays for visual verification are in `output/qc/grid_overlays/`. "
           "Check that each line sits down the middle of its street before "
           "trusting any of this."]
    (p.qc / "grid_control.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    log.info("wrote %s and %d overlay(s)", p.gcps / "tiepoints_manual.csv", len(report))
    log.info("NOW LOOK AT output/qc/grid_overlays/ BEFORE CONTINUING")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
