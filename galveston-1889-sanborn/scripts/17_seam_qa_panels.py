#!/usr/bin/env python3
"""17 -- Native-resolution visual QA panels along every seam.

A seam's residual statistics say whether the CONTROL agrees.  They cannot say
whether the map looks right, because control is sparse and a street can be
pulled straight at two measured corners while bending between them.  The only
test for that is looking at the join at 1:1, and looking at each contributor
ALONE as well as merged -- a street that appears continuous in the merged
mosaic may simply be the upper sheet covering the lower sheet's error.

Panels are placed at two kinds of station:

  control   centred on each verified correspondence, so every measured point
            is inspected where it was measured;
  interval  evenly spaced along the shared boundary, so the spans BETWEEN
            control points -- where an undetected bend would hide -- are
            inspected too.

Every panel is written at zoom 1.  One output pixel is one master pixel is one
original scan pixel; nothing is resampled for display.

Outputs
    output/qc/seam_report/<A>__<B>/panel_NN_<station>.png
    output/qc/seam_report/index.csv
"""
from __future__ import annotations

import argparse
import csv
import json
import pathlib
import sys
from collections import defaultdict

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import cv2

from sanborn import geometry as G
from sanborn import masks as M
from sanborn import qc as QC
from sanborn.config import load_config, paths, read_json, setup_logging
from sanborn.render import OutputGrid


def stations_for_seam(a, b, rings, ties_plane, n_interval, n_control):
    """Panel centres in reconstruction-plane coordinates."""
    out = []
    for label, pt in ties_plane.get(tuple(sorted((a, b))), [])[:n_control]:
        out.append((f"control_{label}", pt))
    if a in rings and b in rings:
        pts = QC.shared_boundary_points(rings[a], rings[b], samples=n_interval)
        for i, pt in enumerate(pts[:n_interval]):
            out.append((f"interval_{i:02d}", tuple(pt)))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", default="galveston1889")
    ap.add_argument("--size", type=int, default=560, help="crop side, master px")
    ap.add_argument("--control-panels", type=int, default=6)
    ap.add_argument("--interval-panels", type=int, default=5)
    ap.add_argument("--only", default="", help="restrict to seams containing this region")
    args = ap.parse_args()

    cfg = load_config(args.profile)
    p = paths().ensure()
    log = setup_logging("17_seam_qa_panels")

    tdoc = read_json(p.working / "transforms.json")
    T = {k: np.asarray(v, float) for k, v in tdoc["transforms"].items()}
    grid = OutputGrid.from_dict(read_json(p.working / "grid.json")["grid"])
    master = p.output / cfg["output"]["master_name"]
    if not master.exists():
        log.error("no master at %s -- run 10_build_mosaic.py first", master)
        return 2

    warped = {q.stem: q for q in sorted((p.working / "warped").glob("*.tif"))}

    # Region outlines in the reconstruction plane, exactly as script 13 builds
    # them, so the "interval" stations sit on the same shared boundary the
    # seam matrix measures.
    root = pathlib.Path(cfg["_root"])
    rings = {}
    for sh in cfg.get("sheets", []):
        for reg in sh.get("regions", []):
            if not reg.get("keep", True) or reg["id"] not in T:
                continue
            doc = M.read_mask(root / reg["mask"])
            for rid, ring, _ in M.regions(doc, keep_only=False):
                if rid == reg["id"]:
                    rings[rid] = G.apply(T[rid], ring)

    # ---- control stations, pushed through the solved transforms ----------
    ties_plane: dict[tuple, list] = defaultdict(list)
    vpath = p.gcps / "tiepoints_verified.csv"
    if vpath.exists():
        by_id: dict[str, list[dict]] = defaultdict(list)
        with vpath.open(newline="") as fh:
            for row in csv.DictReader(fh):
                by_id[row["point_id"]].append(row)
        for pid, rows in by_id.items():
            if len(rows) != 2:
                continue
            if rows[0].get("control_class") == "symbol":
                continue          # a hand-placed symbol marks nothing to inspect
            ra, rb = rows[0]["region"], rows[1]["region"]
            if ra not in T or rb not in T:
                continue
            pa = G.apply(T[ra], [(float(rows[0]["src_x"]), float(rows[0]["src_y"]))])[0]
            pb = G.apply(T[rb], [(float(rows[1]["src_x"]), float(rows[1]["src_y"]))])[0]
            mid = tuple(0.5 * (pa + pb))
            ties_plane[tuple(sorted((ra, rb)))].append((pid, mid))

    pairs = set()
    for t in cfg.get("topology", []):
        r, n = t["region"], t["neighbour"]
        if r in T and n in T:
            pairs.add(tuple(sorted((r, n))))
    pairs |= set(ties_plane)

    outdir = p.qc / "seam_report"
    outdir.mkdir(parents=True, exist_ok=True)
    index = []
    for a, b in sorted(pairs):
        if args.only and args.only not in (a, b):
            continue
        seamdir = outdir / f"{a}__{b}"
        seamdir.mkdir(exist_ok=True)
        # Clear panels from any earlier solve. A directory holding a mix of
        # old and new joins is worse than no panels at all: the reviewer
        # cannot tell which image shows the geometry actually published.
        for stale in seamdir.glob("panel_*.png"):
            stale.unlink()
        stations = stations_for_seam(a, b, rings, ties_plane,
                                     args.interval_panels, args.control_panels)
        if not stations:
            log.warning("%s | %s: no stations to inspect", a, b)
            continue
        paths_ab = [warped.get(a), warped.get(b)]
        if not all(paths_ab):
            log.warning("%s | %s: missing warped raster(s)", a, b)
            continue
        for i, (name, pt) in enumerate(stations):
            panel = QC.seam_panel(master, paths_ab, pt, grid, size=args.size,
                                  zoom=1, labels=(a, b),
                                  title=f"{a} | {b}   {name}   "
                                        f"plane ({pt[0]:.0f},{pt[1]:.0f})   "
                                        f"1:1, no display resampling")
            fn = seamdir / f"panel_{i:02d}_{name}.png"
            cv2.imwrite(str(fn), cv2.cvtColor(panel, cv2.COLOR_RGB2BGR))
            index.append({"seam": f"{a}|{b}", "station": name,
                          "plane_x": round(pt[0], 1), "plane_y": round(pt[1], 1),
                          "file": str(fn.relative_to(p.qc)), "zoom": 1,
                          "crop_px": args.size})
        log.info("%s | %s: %d panels at native resolution", a, b, len(stations))

    if index:
        with (outdir / "index.csv").open("w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(index[0].keys()))
            w.writeheader()
            w.writerows(index)
    print(f"{len(index)} native-resolution panels over "
          f"{len({i['seam'] for i in index})} seams -> "
          f"{outdir.relative_to(pathlib.Path(cfg['_root']))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
