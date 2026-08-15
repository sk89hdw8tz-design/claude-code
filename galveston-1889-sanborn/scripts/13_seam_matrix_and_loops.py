#!/usr/bin/env python3
"""13 -- Seam matrix, loop-closure test, and street/rail continuity checks.

Three things a residual table cannot tell you, all required before this can be
called finished:

LOOP CLOSURE -- AND WHY IT READS ZERO HERE
    Every pairwise seam can be individually tight while the network as a whole
    is distorted. Going A->B->C->D->A should return you to where you started.

    BE CAREFUL READING THIS TEST IN THIS PROJECT. It comes out at exactly 0.000
    px, and that is not an achievement -- it is arithmetic. Sheets here are
    solved by a single global adjustment that assigns each sheet ONE absolute
    transform, so a loop composed from those transforms is the identity by
    construction, whatever the data says. The test is only informative for a
    pipeline that registers pairs sequentially and chains them.

    The genuine equivalent of loop closure for a global solve is the per-seam
    RESIDUAL, which is where drift shows up instead. Read the seam matrix, not
    this number.

STREET WIDTH ACROSS A SEAM
    A street that changes width as it crosses a join is evidence of a scale or
    skew error, and it is visible to a reader in a way that an RMS number is
    not. Widths are measured from the ink profile a short distance either side
    of each seam and compared. A modest difference is expected -- 1889 draughting
    was not uniform -- so this is reported as evidence, not enforced.

LINE DIRECTION ACROSS A SEAM -- A SCREENING HEURISTIC ONLY
    A railroad or long straight street must not change bearing merely because
    two scans were registered independently. The dominant orientation of linear
    structure is estimated either side of the seam and the difference reported.

    ITS LIMITATION IS REAL AND LARGE. It measures whatever linear structure
    dominates each crop, not a specific tracked feature. Near a seam one side
    is often dominated by the roadway (running along the seam) and the other by
    block and building edges (running across it), which produces differences
    approaching 90 degrees with nothing whatever wrong. Values near 90 should
    be read as "the two crops contain different kinds of structure", not as a
    bearing discontinuity. Only a small, non-zero difference on a seam where
    BOTH sides are dominated by the same through-running feature is evidence.
    Tracking an identified rail centreline across the seam would be the sound
    version of this test; it is not implemented.

Outputs
    output/qc/seam_matrix.csv
    output/qc/loop_closure.csv
    output/qc/transform_summary.csv
"""

from __future__ import annotations

import argparse
import csv
import itertools
import sys
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sanborn import geometry as G
from sanborn import masks as M
from sanborn import qc as QC
from sanborn.config import load_config, paths, read_json, setup_logging
from sanborn.render import OutputGrid

OPP = {"north": "south", "south": "north", "east": "west", "west": "east"}


def local_orientation(gray):
    """Dominant orientation (deg) of linear structure, via the structure tensor."""
    if gray.size == 0 or float(gray.std()) < 2.0:
        return None
    gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    jxx, jyy, jxy = float((gx * gx).sum()), float((gy * gy).sum()), float((gx * gy).sum())
    denom = jxx - jyy
    if abs(denom) < 1e-9 and abs(jxy) < 1e-9:
        return None
    # principal direction of the gradient tensor; add 90 deg for the line itself
    ang = 0.5 * np.degrees(np.arctan2(2.0 * jxy, denom))
    return float((ang + 90.0) % 180.0)


def ink_profile_width(gray, axis):
    """Width (px) of the widest low-ink band, i.e. the roadway."""
    if gray.size == 0:
        return None
    ink = (cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C,
                                 cv2.THRESH_BINARY_INV, 51, 12) > 0).astype(np.float32)
    prof = ink.mean(axis=axis)
    if prof.size < 5:
        return None
    thr = prof.min() + 0.25 * (prof.max() - prof.min())
    runs, cur = [], 0
    for v in prof:
        if v <= thr:
            cur += 1
        else:
            if cur:
                runs.append(cur)
            cur = 0
    if cur:
        runs.append(cur)
    return float(max(runs)) if runs else None


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--profile", default="galveston1889")
    ap.add_argument("--samples", type=int, default=5)
    args = ap.parse_args()

    cfg = load_config(args.profile)
    p = paths().ensure()
    log = setup_logging("13_seam_matrix_and_loops")
    root = Path(cfg["_root"])

    tdoc = read_json(p.working / "transforms.json")
    T = {k: np.asarray(v, float) for k, v in tdoc["transforms"].items()}
    gdoc = read_json(p.working / "grid.json")
    grid = OutputGrid.from_dict(gdoc["grid"])
    rdoc = read_json(p.gcps / "residuals.json")
    master = p.output / cfg["output"]["master_name"]
    good = float(cfg["qc"]["good_residual_px"])
    gross = float(cfg["qc"]["gross_residual_px"])

    # ---- transform summary -------------------------------------------------
    with (p.qc / "transform_summary.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["region", "model", "scale_x", "scale_y", "rotation_deg",
                    "shear_deg", "anisotropy", "determinant", "plausible"])
        for rid, H in sorted(T.items()):
            d = G.decompose_affine(H)
            flags = G.plausibility_flags(H)
            w.writerow([rid, tdoc["kind"], f"{d['scale_x']:.6f}", f"{d['scale_y']:.6f}",
                        f"{d['rotation_deg']:.4f}", f"{d['shear_deg']:.4f}",
                        f"{d['anisotropy']:.6f}", f"{d['determinant']:.6f}",
                        "yes" if not flags else "/".join(flags)])
    log.info("wrote transform_summary.csv")

    # ---- loop closure ------------------------------------------------------
    adj = defaultdict(set)
    for t in cfg.get("topology", []):
        if t["region"] in T and t["neighbour"] in T:
            adj[t["region"]].add(t["neighbour"])
            adj[t["neighbour"]].add(t["region"])

    # residual-derived relative transforms: use the solved absolute transforms,
    # so a loop composes to identity only if the network is globally consistent
    loops, seen = [], set()
    nodes = sorted(T)
    for cyc_len in (3, 4):
        for combo in itertools.combinations(nodes, cyc_len):
            for perm in itertools.permutations(combo[1:]):
                cycle = (combo[0],) + perm
                if not all(cycle[(i + 1) % cyc_len] in adj[cycle[i]] for i in range(cyc_len)):
                    continue
                key = frozenset(cycle)
                if key in seen:
                    continue
                seen.add(key)
                # compose relative transforms around the loop
                Hacc = np.eye(3)
                for i in range(cyc_len):
                    a, b = cycle[i], cycle[(i + 1) % cyc_len]
                    Hacc = (np.linalg.inv(T[b]) @ T[a]) @ Hacc
                # a perfectly consistent network returns identity
                probe = np.array([[0.0, 0.0], [2000.0, 0.0], [0.0, 2000.0]])
                disp = np.linalg.norm(G.apply(Hacc, probe) - probe, axis=1)
                loops.append({"cycle": " -> ".join(cycle) + f" -> {cycle[0]}",
                              "length": cyc_len,
                              "closure_px_at_origin": float(disp[0]),
                              "closure_px_at_2000x": float(disp[1]),
                              "closure_px_at_2000y": float(disp[2]),
                              "max_closure_px": float(disp.max())})
    loops.sort(key=lambda d: -d["max_closure_px"])
    with (p.qc / "loop_closure.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(loops[0].keys()) if loops else
                           ["cycle", "length", "max_closure_px"])
        w.writeheader()
        for l in loops:
            w.writerow(l)
    if loops:
        log.info("loop closure over %d independent cycle(s): worst %.3f px, "
                 "median %.3f px", len(loops), loops[0]["max_closure_px"],
                 float(np.median([l["max_closure_px"] for l in loops])))
        for l in loops[:4]:
            log.info("   %-46s max closure %8.3f px", l["cycle"], l["max_closure_px"])
    else:
        log.warning("no closed loops in the adjacency graph")

    # ---- seam matrix -------------------------------------------------------
    by_pair = defaultdict(list)
    # Seams are graded on GEOMETRIC control only. Symbol control (fire plugs,
    # valve discs) was placed by eye by the 1889 draughtsman and differs by up
    # to 46 px between plates of one edition -- see research/experiment_log.md
    # entry 17. It is reported separately as drafting scatter, never graded.
    by_pair_symbol = defaultdict(list)
    for r in rdoc["residuals"]:
        if r["kind"] != "tie":
            continue
        key = tuple(sorted([r["sheet_a"], r["sheet_b"]]))
        if r.get("control_class", "geometric") == "symbol":
            by_pair_symbol[key].append(r)
        else:
            by_pair[key].append(r)

    rings = {}
    for sh in cfg.get("sheets", []):
        for reg in sh.get("regions", []):
            if not reg.get("keep", True) or reg["id"] not in T:
                continue
            doc = M.read_mask(root / reg["mask"])
            for rid, ring, _ in M.regions(doc, keep_only=False):
                if rid == reg["id"]:
                    rings[rid] = G.apply(T[rid], ring)

    direction = {}
    for t in cfg.get("topology", []):
        direction[tuple(sorted([t["region"], t["neighbour"]]))] = t.get("direction", "")

    rows = []
    for pair in sorted(set(list(by_pair) + list(direction))):
        a, b = pair
        res = by_pair.get(pair, [])
        vals = np.array([r["residual"] for r in res]) if res else np.array([])
        d = direction.get(pair, "")
        edge_a = {"north": "top", "south": "bottom", "east": "right", "west": "left"}.get(d, "")
        edge_b = {"north": "bottom", "south": "top", "east": "left", "west": "right"}.get(d, "")

        widths, angles = [], []
        if a in rings and b in rings and master.exists():
            pts = QC.shared_boundary_points(rings[a], rings[b], samples=args.samples)
            for pt in pts[:args.samples]:
                col, row = grid.plane_to_pixel([pt])[0]
                crop = QC.read_crop(master, col, row, 420)
                if crop is None:
                    continue
                g = cv2.cvtColor(QC.flatten_rgba(crop), cv2.COLOR_RGB2GRAY)
                h_, w_ = g.shape
                if d in ("north", "south"):
                    s1, s2 = g[:h_ // 2 - 12, :], g[h_ // 2 + 12:, :]
                    ax = 1
                else:
                    s1, s2 = g[:, :w_ // 2 - 12], g[:, w_ // 2 + 12:]
                    ax = 0
                w1, w2 = ink_profile_width(s1, ax), ink_profile_width(s2, ax)
                if w1 and w2:
                    widths.append(abs(w1 - w2) / max(w1, w2))
                o1, o2 = local_orientation(s1), local_orientation(s2)
                if o1 is not None and o2 is not None:
                    da = abs(o1 - o2) % 180.0
                    angles.append(min(da, 180.0 - da))

        med = float(np.median(vals)) if vals.size else None
        p95 = float(np.percentile(vals, 95)) if vals.size else None
        rmse = float(np.sqrt((vals ** 2).mean())) if vals.size else None
        mx = float(vals.max()) if vals.size else None
        sym = np.array([r["residual"] for r in by_pair_symbol.get(pair, [])])
        wdisc = float(np.median(widths)) if widths else None
        adisc = float(np.median(angles)) if angles else None

        if not vals.size:
            status, note = "FAIL", "no shared correspondences measured"
        elif med <= 3:
            status, note = "PASS", "excellent"
        elif med <= good:
            status, note = "PASS", "within target"
        elif med <= 10:
            status, note = "REVIEW", "median in the 5-10 px review band"
        else:
            status, note = "FAIL", "median above 10 px"
        if vals.size and mx > gross:
            note += f"; max {mx:.0f}px exceeds {gross:.0f}px"
        # INFORMATIONAL ONLY -- never a gate. This metric measures whichever
        # structure dominates each crop, so a value near 90 deg means "different
        # structure on the two sides", not a discontinuity. Using it as a gate
        # is what flooded the previous matrix with REVIEW verdicts.
        if adisc is not None and adisc > 3.0:
            note += (f"; line bearing differs {adisc:.1f} deg across the seam "
                     "(informational: this metric reads the dominant structure "
                     "in each crop, not a join)")
        if vals.size and vals.size < 3:
            note += f"; only {vals.size} correspondence(s) -- weakly constrained"
            if status == "PASS":
                status = "REVIEW"

        rows.append({
            "sheet_a": a, "sheet_b": b, "edge_a": edge_a, "edge_b": edge_b,
            "geometric_control_count": int(vals.size),
            "median_error_px": "" if med is None else f"{med:.2f}",
            "rmse_px": "" if rmse is None else f"{rmse:.2f}",
            "p95_error_px": "" if p95 is None else f"{p95:.2f}",
            "max_error_px": "" if mx is None else f"{mx:.2f}",
            "symbol_control_count": int(sym.size),
            "symbol_scatter_median_px": "" if not sym.size else f"{np.median(sym):.2f}",
            "symbol_scatter_max_px": "" if not sym.size else f"{sym.max():.2f}",
            "street_width_discrepancy": "" if wdisc is None else f"{wdisc:.3f}",
            "line_bearing_diff_deg": "" if adisc is None else f"{adisc:.2f}",
            "visual_status": "see output/qc/seam_report/",
            "geometry_status": status,
            "mask_status": "cut at shared centreline" if a in rings and b in rings else "n/a",
            "final_status": status, "notes": note,
        })

    with (p.qc / "seam_matrix.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        for r in rows:
            w.writerow(r)
    log.info("seam matrix: %d adjacency row(s)", len(rows))
    for r in rows:
        log.info("   %-9s %-9s n=%2s med=%-7s bearing=%-6s  %s -- %s",
                 r["sheet_a"], r["sheet_b"], r["geometric_control_count"],
                 r["median_error_px"] or "-", r["line_bearing_diff_deg"] or "-",
                 r["final_status"], r["notes"])
    counts = defaultdict(int)
    for r in rows:
        counts[r["final_status"]] += 1
    log.info("STATUS: %s", dict(counts))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
