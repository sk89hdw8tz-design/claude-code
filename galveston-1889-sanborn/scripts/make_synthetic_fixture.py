#!/usr/bin/env python3
"""Build the SYNTHETIC self-test fixture (imagery + masks + control points).

Why this exists
    The real 1889 scans could not be downloaded in the environment where this
    pipeline was built, so "the code works" had to be demonstrated rather than
    asserted. This generates a multi-sheet map whose true geometry is known
    exactly, runs through the identical pipeline, and lets reconstruction error
    be measured against ground truth instead of merely against itself.

What it writes
    tests/fixture/original/synthetic_S*.jpg   sheet scans (JPEG, like archives)
    tests/fixture/ground_truth.png            the undivided reference map
    tests/fixture/truth.json                  exact per-sheet transforms
    masks/synthetic_S*_regions.geojson        region masks in source pixels
    gcps/synthetic_tiepoints.csv              control points with picking noise

The masks and control points stand in for the human step of the real workflow:
someone reads the Key, draws each mapped region, and clicks matching features.
Picking noise is injected deliberately so the residuals mean something.

NOTHING HERE IS HISTORICAL DATA.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sanborn import geometry as G
from sanborn import masks as M
from sanborn.config import paths, read_json, setup_logging
from sanborn.synthetic import build_fixture
from sanborn.tiepoints import write_gcp_csv, write_gcp_geojson

# Which fixture regions are kept. S1's second region is the analogue of the
# detached 43rd-45th Street section and is deliberately excluded.
REGION_IDS = {"S1": ["S1_main", "S1_detached"]}
KEEP = {"S1_detached": False}


def region_id_for(sheet_name, idx):
    ids = REGION_IDS.get(sheet_name)
    return ids[idx] if ids and idx < len(ids) else sheet_name


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seed", type=int, default=11)
    ap.add_argument("--pick-noise", type=float, default=1.5,
                    help="stdev of simulated human click error, in source pixels")
    ap.add_argument("--border-inset", type=float, default=6.0,
                    help="pixels pulled in from each region's printed border")
    args = ap.parse_args()

    p = paths().ensure()
    log = setup_logging("make_synthetic_fixture")
    root = Path(p.root)
    outdir = root / "tests" / "fixture"

    log.info("generating fixture (seed=%d) ...", args.seed)
    truth = build_fixture(outdir, seed=args.seed)
    log.info("wrote %d sheet scans to %s", len(truth["sheets"]), outdir / "original")

    rng = np.random.default_rng(args.seed + 999)

    # ---- masks: one file per sheet, one polygon per mapped region ----------
    for sh in truth["sheets"]:
        feats = []
        for i, reg in enumerate(sh["regions"]):
            rid = region_id_for(sh["name"], i)
            x0, y0, x1, y1 = reg["page_rect"]
            ins = args.border_inset
            ring = M.rect_ring(x0 + ins, y0 + ins, x1 - ins, y1 - ins)
            feats.append(M.polygon_feature(
                sheet=sh["name"], region=rid, ring=ring,
                keep=KEEP.get(rid, True),
                role="map_region" if KEEP.get(rid, True) else "excluded_region",
                source_image=sh["file"],
                confidence="high",
                defined_by="fixture generator (stands in for human inspection)",
                note=("Detached section analogue -- excluded from the mosaic."
                      if not KEEP.get(rid, True) else
                      "Mapped region retained in the mosaic.")))
        path = p.masks / f"synthetic_{sh['name']}_regions.geojson"
        M.write_mask(path, feats, extra={
            "note": "SYNTHETIC FIXTURE MASK - not historical data",
            "source_image": sh["file"],
            "image_size": sh["page_size"]})
        log.info("  mask %s (%d region(s))", path.name, len(feats))

    # ---- control points ---------------------------------------------------
    # Project each ground-truth intersection into every sheet that shows it,
    # then add picking noise. A point seen on two sheets becomes a tie.
    sheets_by_name = {s["name"]: s for s in truth["sheets"]}
    rows = []
    for X in truth["intersections"]:
        gt = np.array([X["x"], X["y"]], dtype=float)
        for sh in truth["sheets"]:
            for i, reg in enumerate(sh["regions"]):
                rid = region_id_for(sh["name"], i)
                H = np.array(reg["H_page_to_gt"], dtype=float)   # page -> gt
                px = G.apply(np.linalg.inv(H), [gt])[0]          # gt -> page
                x0, y0, x1, y1 = reg["page_rect"]
                m = args.border_inset + 18
                if not (x0 + m <= px[0] <= x1 - m and y0 + m <= px[1] <= y1 - m):
                    continue
                noisy = px + rng.normal(0, args.pick_noise, 2)
                rows.append({
                    "point_id": X["id"], "sheet": sh["name"], "region": rid,
                    "role": "tie",
                    "src_x": round(float(noisy[0]), 2),
                    "src_y": round(float(noisy[1]), 2),
                    "street_a": X["street_a"], "street_b": X["street_b"],
                    "feature": "street intersection",
                    "method": "synthetic projection + gaussian pick noise",
                    "confidence": "high",
                    "selected_by": "fixture generator",
                    "accepted": "true",
                    "note": f"pick noise sigma={args.pick_noise}px",
                })

    csv_path = p.gcps / "synthetic_tiepoints.csv"
    write_gcp_csv(csv_path, rows)
    write_gcp_geojson(p.gcps / "synthetic_tiepoints.geojson", rows)

    from collections import Counter
    per_region = Counter(r["region"] for r in rows)
    shared = Counter()
    by_pt = {}
    for r in rows:
        by_pt.setdefault(r["point_id"], set()).add(r["region"])
    for regs in by_pt.values():
        for a in regs:
            for b in regs:
                if a < b:
                    shared[(a, b)] += 1

    log.info("wrote %d control observations to %s", len(rows), csv_path)
    log.info("observations per region: %s", dict(sorted(per_region.items())))
    log.info("shared points per region pair:")
    for (a, b), n in sorted(shared.items()):
        log.info("    %-12s %-12s %d", a, b, n)

    excluded = [r for r in rows if not KEEP.get(r["region"], True)]
    log.info("control points falling in EXCLUDED regions: %d "
             "(they are present in the file and must be filtered by the mask/"
             "keep flags, which is exactly what the pipeline is tested on)",
             len(excluded))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
