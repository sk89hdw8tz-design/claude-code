#!/usr/bin/env python3
"""06d -- Recover edge boundary streets, and add street-DIRECTION constraints.

TWO CORRECTIONS, BOTH FROM A PRECISE DIAGNOSIS
    The earlier claim that "sheets 1 and 2 have collinear control and that is the
    root cause" was WRONG, and the rank test in geometry.py already said so:
    per-sheet similarity has nullity 0 with collinear ties. Two separated points
    determine a similarity. Collinearity is fatal to affine, not to similarity.

    The actual causes of the failing seams are these.

    (1) TWO SEAMS HAD NO SHARED CONTROL AT ALL. Sheet 1 lost its 22nd Street and
        sheet 29 lost its 22nd, because a sheet's BOUNDARY street lies at the
        very edge of the paper where the band search is least reliable and the
        quality gates -- correctly -- threw the measurement away. The result was
        S1_main|S2 and S27|S29 sharing zero point ids. A seam cannot be measured,
        let alone solved, without a shared observation.

        The fix is to predict where the boundary street should be from the
        sheet's OWN regular grid pitch, then MEASURE there in a tight window.
        The prediction only says where to look. If no genuine band is found the
        point is still refused -- an extrapolated coordinate is not an
        observation and is never recorded as one.

    (2) WHERE TIES ARE COLLINEAR, ONE NOISY SLOPE CONTROLS A WHOLE DEGREE OF
        FREEDOM. With every tie on one line, the solved rotation of a sheet is
        set by how that single line's direction was measured. Sheet 1's avenue
        slope came from ONE avenue, and it dragged the sheet to +1.51 degrees
        while every neighbour sat near zero.

        The fix is independent evidence for direction. Sheets 1 and 9 both draw
        22nd, 23rd, 24th and 25th Streets -- the SAME physical streets. Their
        directions, pooled over four streets per sheet, are a far better
        rotation measurement than one avenue. That is encoded here as a
        synthetic correspondence a long way along the shared street from a
        genuine shared intersection: "travel L pixels along 23rd Street from
        Avenue A and you arrive at the same place on both sheets". It is a
        direction constraint expressed in the point language the adjustment
        already speaks, and it is historical evidence, not an image match.

Outputs
    gcps/tiepoints_boundary.csv    recovered boundary-street intersections
    gcps/tiepoints_direction.csv   direction constraints
    config/line_constraints.yaml   the shared lines used, for the record
    output/qc/boundary_recovery.md
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sanborn import geometry as G
from sanborn import gridlines as GL
from sanborn import masks as M
from sanborn.config import load_config, paths, setup_logging, write_yaml
from sanborn.render import read_image
from sanborn.tiepoints import write_gcp_csv


def street_num(name):
    return int("".join(c for c in str(name) if c.isdigit()) or 0)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--profile", default="galveston1889")
    ap.add_argument("--recover-window", type=float, default=90.0,
                    help="tight search window around the grid-predicted position")
    ap.add_argument("--recover-max-move", type=float, default=70.0)
    ap.add_argument("--min-rms", type=float, default=4.0)
    ap.add_argument("--direction-length", type=float, default=2500.0,
                    help="lever arm for the direction constraint, in source px")
    args = ap.parse_args()

    cfg = load_config(args.profile)
    p = paths().ensure()
    log = setup_logging("06d_boundary_and_direction")
    root = Path(cfg["_root"])
    src_dir = root / ((cfg.get("paths") or {}).get("original_dir") or "data/original")
    pos = (yaml.safe_load((p.config / "grid_positions.yaml").read_text(encoding="utf-8"))
           or {}).get("sheets", {})
    sheets_cfg = {str(s["id"]): s for s in cfg.get("sheets", [])}

    # ---------------- pass 1: refine every sheet's grid ---------------------
    grids, notes = {}, []
    for sid, spec in sorted(pos.items(), key=lambda kv: int(kv[0])):
        rid = spec["region"]
        img = read_image(src_dir / spec["file"])
        scfg = sheets_cfg[sid]
        mrel = next((r.get("mask") for r in scfg["regions"] if r.get("mask")), None)
        sb = ab = None
        if mrel:
            doc = M.read_mask(root / mrel)
            for r, ring, _ in M.regions(doc, keep_only=False):
                if r == rid:
                    bx0, by0, bx1, by1 = M.ring_bounds(ring)
                    ab, sb = (bx0 + 45, bx1 - 45), (by0 + 45, by1 - 45)
        streets = {k: float(v) for k, v in (spec.get("streets") or {}).items()}
        avenues = {k: float(v) for k, v in (spec.get("avenues") or {}).items()}
        R = GL.refine_grid(img, streets, avenues, street_bounds=sb, avenue_bounds=ab)

        def accepted(b):
            return (b["moved"] <= 150 and b["slope_deviation"] <= 0.040
                    and not (b["rms"] < args.min_rms and b["moved"] > 60))

        good_st = {k: v for k, v in R["streets"].items() if accepted(v)}
        good_av = {k: v for k, v in R["avenues"].items() if accepted(v)}
        lost_st = [k for k in R["streets"] if k not in good_st]
        lost_av = [k for k in R["avenues"] if k not in good_av]

        # -------- recover a lost band by predicting from the sheet's own pitch
        for name in list(lost_st):
            if len(good_st) < 2:
                break
            ks = sorted(good_st, key=street_num)
            xs = np.array([street_num(k) for k in ks], float)
            ys = np.array([good_st[k]["offset"] for k in ks], float)
            A = np.column_stack([np.ones_like(xs), xs])
            sol, *_ = np.linalg.lstsq(A, ys, rcond=None)
            pred = float(sol[0] + sol[1] * street_num(name))
            b = GL.refine_band(img, pred, True, window=args.recover_window,
                               bounds=sb)
            if b is None:
                notes.append(f"sheet {sid}: street {name} -- predicted y={pred:.0f}, "
                             f"no band measurable there; REFUSED (not extrapolated in)")
                continue
            b["approx"] = pred
            b["moved"] = abs(b["offset"] - pred)
            b["slope_individual"] = b["slope"]
            shared = R["shared_slope_streets"]
            if shared is not None:
                mid = img.shape[1] / 2.0
                centre = b["offset"] + b["slope"] * mid
                b["slope"] = shared
                b["offset"] = centre - shared * mid
            b["slope_deviation"] = abs(b["slope_individual"] - (shared or b["slope"]))
            if b["moved"] > args.recover_max_move or b["rms"] < args.min_rms:
                notes.append(f"sheet {sid}: street {name} -- measured at "
                             f"y={b['offset']:.0f} but moved {b['moved']:.0f}px / "
                             f"rms {b['rms']:.1f}; REFUSED")
                continue
            good_st[name] = b
            notes.append(f"sheet {sid}: street {name} RECOVERED at y={b['offset']:.0f} "
                         f"(predicted {pred:.0f}, moved {b['moved']:.0f}px, "
                         f"rms {b['rms']:.1f})")
            log.info("sheet %-3s RECOVERED street %-5s y=%8.1f (pred %8.1f, moved %5.1f)",
                     sid, name, b["offset"], pred, b["moved"])

        grids[rid] = {"streets": good_st, "avenues": good_av, "sheet": sid,
                      "rot_streets": R["rotation_deg_streets"],
                      "rot_avenues": R["rotation_deg_avenues"]}
        log.info("sheet %-3s %-10s streets=%s avenues=%s (lost st=%s av=%s)",
                 sid, rid, sorted(good_st), sorted(good_av), lost_st, lost_av)

    # ---------------- boundary control points -------------------------------
    rows = []
    for rid, g in grids.items():
        for sname, hl in g["streets"].items():
            for aname, vl in g["avenues"].items():
                q = GL.intersect(hl, vl)
                if q is None:
                    continue
                rows.append({"point_id": f"{sname}|{aname}", "sheet": g["sheet"],
                             "region": rid, "role": "tie",
                             "src_x": round(q[0], 2), "src_y": round(q[1], 2),
                             "street_a": sname, "street_b": aname,
                             "feature": "street centreline intersection",
                             "method": "windowed band fit (incl. recovered boundary)",
                             "confidence": "high", "accepted": "true",
                             "selected_by": "06d_boundary_and_direction.py", "note": ""})
    write_gcp_csv(p.gcps / "tiepoints_boundary.csv", rows)
    log.info("wrote %d control observation(s) after boundary recovery", len(rows))

    # ---------------- direction constraints ---------------------------------
    # For each adjacency, find streets (or avenues) drawn on BOTH sheets and a
    # genuine shared intersection to anchor the lever arm.
    shared_ids = defaultdict(set)
    by_region = defaultdict(dict)
    for r in rows:
        by_region[r["region"]][r["point_id"]] = (r["src_x"], r["src_y"])
    dir_rows, line_doc = [], []
    L = args.direction_length
    for t in cfg.get("topology", []):
        a, b = t["region"], t["neighbour"]
        if a not in grids or b not in grids:
            continue
        anchors = sorted(set(by_region[a]) & set(by_region[b]))
        if not anchors:
            log.warning("%s|%s: no shared intersection to anchor a direction "
                        "constraint", a, b)
            continue
        anchor = anchors[len(anchors) // 2]
        for kind, key in (("street", "streets"), ("avenue", "avenues")):
            common = sorted(set(grids[a][key]) & set(grids[b][key]))
            if len(common) < 2:
                continue
            # pooled direction of the shared family on each sheet
            def unit(g):
                sl = float(np.median([g[key][c]["slope"] for c in common]))
                d = np.array([1.0, sl]) if key == "streets" else np.array([sl, 1.0])
                return d / np.linalg.norm(d)
            da, db = unit(grids[a]), unit(grids[b])
            pa, pb = np.array(by_region[a][anchor]), np.array(by_region[b][anchor])
            for sign in (+1, -1):
                pid = f"DIR_{a}_{b}_{kind}_{'p' if sign > 0 else 'm'}"
                for rid, pt in ((a, pa + sign * L * da), (b, pb + sign * L * db)):
                    dir_rows.append({
                        "point_id": pid, "sheet": grids[rid]["sheet"], "region": rid,
                        "role": "direction", "src_x": round(float(pt[0]), 2),
                        "src_y": round(float(pt[1]), 2),
                        "feature": f"direction of shared {kind}s {','.join(common)}",
                        "method": f"lever arm {L:.0f}px along the pooled {kind} "
                                  f"direction from shared point {anchor}",
                        "confidence": "high", "accepted": "true",
                        "selected_by": "06d_boundary_and_direction.py",
                        "note": "synthetic point encoding a DIRECTION constraint"})
            line_doc.append({"pair": [a, b], "kind": kind, "shared": common,
                             "anchor_point": anchor,
                             "dir_a": [float(da[0]), float(da[1])],
                             "dir_b": [float(db[0]), float(db[1])],
                             "lever_px": L})
            log.info("%s|%s: direction constraint from %d shared %s(s) %s "
                     "(anchor %s)", a, b, len(common), kind, common, anchor)
    write_gcp_csv(p.gcps / "tiepoints_direction.csv", dir_rows)
    write_yaml(p.config / "line_constraints.yaml",
               {"note": "Shared lines used to build direction constraints. These "
                        "encode that a street drawn on two sheets is the same "
                        "street and must run the same way on both.",
                "constraints": line_doc})
    log.info("wrote %d direction observation(s) over %d shared-line family(ies)",
             len(dir_rows), len(line_doc))

    md = ["# Boundary recovery and direction constraints", "", "## Boundary recovery", ""]
    md += [f"- {n}" for n in notes] or ["- nothing needed recovery"]
    md += ["", "## Direction constraints", "",
           "| pair | kind | shared lines | anchor | lever px |", "|---|---|---|---|---|"]
    for l in line_doc:
        md.append(f"| {l['pair'][0]} – {l['pair'][1]} | {l['kind']} | "
                  f"{', '.join(l['shared'])} | {l['anchor_point']} | {l['lever_px']:.0f} |")
    (p.qc / "boundary_recovery.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
