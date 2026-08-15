#!/usr/bin/env python3
"""18 -- Does the shared street come out the RIGHT WIDTH after assembly?

This is the acceptance test the control cannot perform on itself.

Three of the ten seams join sheets that share no inked ground: each plate
draws only its own frontage line and the roadway between is drawn by neither.
Their tie points are CONSTRUCTED by stepping half the street width inward from
each plate.  A wrong step biases the seam by the same amount at every point,
so it is invisible in that seam's own residuals -- the seam fits itself
perfectly while sitting in the wrong place.

But the two frontage lines are still drawn, one on each plate, and after
assembly the gap between them is a physical distance the map asserts.  Compare
it with what the Galveston plat says it should be and the systematic has
nowhere to hide.

TWO WAYS TO MEASURE IT, AND ONLY ONE OF THEM WORKS
    The obvious way -- profile the master across the seam and find the two
    frontage lines in the ink -- was tried and is NOT reliable on this
    material.  Its answer moves by 15% when the search window changes width,
    because a heavy party wall or a block of lettering inside the block is
    darker than a street frontage line, so any threshold relative to the
    profile maximum either skips the frontage or lands on the next block.  A
    metric that unstable is evidence about the detector, not about the map,
    and tuning it until it agrees with the expected answer would be selecting
    on the outcome.  It is retained below as a DIAGNOSTIC only, never a gate.

    The sound way uses the control that already exists.  On seams where the
    observers identified corners on BOTH property lines of the shared street,
    the separation of those two families in the reconstruction plane is the
    street width, measured from semantically identified features rather than
    detected ink.  That is what this script gates on.

    Where control lies on ONE line only -- every avenue seam, because the two
    plates share no inked ground there -- this test cannot be performed, and
    the script says so rather than inventing a number.  Those seams' across-
    seam placement rests on the printed street width and is not independently
    verified.

REFERENCE WIDTHS
    Numbered streets are drawn true: 80 ft measures 80.5 ft against a scale
    derived from grid pitch.  Lettered avenues are drawn about 3% narrow: a
    printed 70 ft measures 68.0 ft, a printed 80 ft (Av. B) measures 77.2.
    Both figures come from sheet 9's own grid pitch, which needs no printed
    width at all -- the plat fixes avenue pitch at 260+70 = 330 ft and street
    pitch at 300+80 = 380 ft. See research/experiment_log.md entry 15.

Outputs
    output/qc/shared_street_width.csv
"""
from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import rasterio
from rasterio.windows import Window

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sanborn import geometry as G
from sanborn.config import load_config, paths, read_json, setup_logging
from sanborn.render import OutputGrid

# Drawn width in feet of each shared street, from grid-pitch calibration.
DRAWN_FT = {"street": 80.5, "avenue70": 68.0, "avenue80": 77.2}


def classify(shared: str) -> str:
    s = (shared or "").lower()
    if "av." in s or "avenue" in s:
        return "avenue80" if "strand" in s or "av. b" in s else "avenue70"
    return "street"


def frontage_gap(master, grid, pt, along, px_per_ft, half=170, band=7):
    """Distance between the last strong ink line either side of the seam.

    Profiles the master perpendicular to the seam, smooths along the seam to
    suppress lettering and symbols, and takes the ink minimum NEAREST the
    centre on each side -- the roadway is blank, so the lines bounding it are
    the first ink you meet going outward.

    The search window is deliberately short (+/-170 px, about +/-56 ft). A
    longer profile reaches deep into the blocks either side, where a heavy
    party wall or a block of lettering is darker than a street frontage line;
    a threshold relative to THAT maximum then skips the frontage entirely and
    the measurement lands on the far side of the next block. Keeping the
    window just wider than the widest street here (80 ft) makes the frontage
    lines the strongest thing in it.
    """
    col, row = grid.plane_to_pixel([pt])[0]
    perp = np.array([-along[1], along[0]], float)
    perp /= np.linalg.norm(perp)
    ts = np.arange(-half, half + 1, 1.0)
    ss = np.arange(-40, 41, 2.0)
    cols = (col + np.outer(ts, perp[0]) + np.outer(np.ones_like(ts), ss * along[0]))
    rows = (row + np.outer(ts, perp[1]) + np.outer(np.ones_like(ts), ss * along[1]))

    c0, r0 = int(cols.min()) - 2, int(rows.min()) - 2
    w = int(cols.max() - cols.min()) + 5
    h = int(rows.max() - rows.min()) + 5
    with rasterio.open(master) as ds:
        arr = ds.read(window=Window(c0, r0, w, h), boundless=True, fill_value=0)
    a = np.transpose(arr, (1, 2, 0))
    if a.shape[2] >= 4:
        alpha = a[..., 3].astype(np.float32) / 255.0
        grey = a[..., :3].astype(np.float32).mean(axis=2) * alpha + 255.0 * (1 - alpha)
    else:
        grey = a[..., :3].astype(np.float32).mean(axis=2)

    ci = np.clip((cols - c0).astype(int), 0, grey.shape[1] - 1)
    ri = np.clip((rows - r0).astype(int), 0, grey.shape[0] - 1)
    prof = grey[ri, ci].mean(axis=1)
    if not np.isfinite(prof).all() or prof.size < 50:
        return None
    k = np.ones(band) / band
    prof = np.convolve(prof, k, mode="same")

    ink = prof.max() - prof
    if ink.max() < 20:                      # nothing but paper here
        return None
    mid0 = len(ts) // 2
    mid_guard_lo, mid_guard_hi = mid0 - 6, mid0 + 7
    strong = ink > 0.45 * ink.max()
    # Ignore ink within a few px of the exact centre: a seam that happens to
    # fall on a drawn line would otherwise measure a width of zero.
    strong[mid_guard_lo:mid_guard_hi] = False
    mid = len(ts) // 2
    left = np.where(strong[:mid])[0]
    right = np.where(strong[mid:])[0]
    if not left.size or not right.size:
        return None
    # The roadway is the BLANK band between the two frontage lines, so the
    # lines that bound it are the strong ink nearest the centre on each side,
    # not the outermost ink in the profile.
    return float(ts[right[0] + mid] - ts[left[-1]]) / px_per_ft


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", default="galveston1889")
    ap.add_argument("--stations", type=int, default=9)
    ap.add_argument("--ink-diagnostic", action="store_true",
                    help="also run the unreliable ink-profile estimate")
    args = ap.parse_args()

    cfg = load_config(args.profile)
    p = paths().ensure()
    log = setup_logging("18_shared_street_width")
    T = {k: np.asarray(v, float)
         for k, v in read_json(p.working / "transforms.json")["transforms"].items()}
    grid = OutputGrid.from_dict(read_json(p.working / "grid.json")["grid"])
    master = p.output / cfg["output"]["master_name"]
    px_per_ft = 3.0429           # anchor sheet's own scale, from grid pitch

    by_id = defaultdict(list)
    with (p.gcps / "tiepoints_verified.csv").open(newline="") as fh:
        for row in csv.DictReader(fh):
            by_id[row["point_id"]].append(row)
    mids = defaultdict(list)
    for pid, rows in by_id.items():
        if len(rows) != 2 or rows[0].get("control_class") == "symbol":
            continue
        ra, rb = rows[0]["region"], rows[1]["region"]
        if ra not in T or rb not in T:
            continue
        pa = G.apply(T[ra], [(float(rows[0]["src_x"]), float(rows[0]["src_y"]))])[0]
        pb = G.apply(T[rb], [(float(rows[1]["src_x"]), float(rows[1]["src_y"]))])[0]
        mids[tuple(sorted((ra, rb)))].append(0.5 * (pa + pb))

    out = []
    for t in cfg.get("topology", []):
        a, b = t["region"], t["neighbour"]
        P = np.asarray(mids.get(tuple(sorted((a, b))), []), float)
        if P.shape[0] < 2:
            continue
        kind = classify(t.get("shared_street", ""))
        expect = DRAWN_FT[kind]

        if t["direction"] in ("north", "south"):
            m, _ = np.polyfit(P[:, 0], P[:, 1], 1)
            normal = np.array([-m, 1.0])
        else:
            m, _ = np.polyfit(P[:, 1], P[:, 0], 1)
            normal = np.array([1.0, -m])
        d = (normal @ P.T) / np.linalg.norm(normal)

        # Two property lines show up as two clusters of perpendicular offset.
        # Use the 10th/90th percentile span so an unbalanced count between the
        # two sides cannot bias the answer.
        span_px = float(np.percentile(d, 90) - np.percentile(d, 10))
        span_ft = span_px / px_per_ft
        row = {"seam": f"{a}|{b}", "shared": t.get("shared_street", ""),
               "kind": kind, "expected_ft": round(expect, 1),
               "n_control": int(P.shape[0]),
               "control_span_px": round(span_px, 1)}

        if span_px < 60:
            row.update({"measured_ft": "", "error_ft": "", "error_pct": "",
                        "verdict": "NOT TESTABLE",
                        "note": "control lies on ONE line of the shared street, "
                                "so its width is not observed; the across-seam "
                                "placement rests on the printed width and is "
                                "not independently verified here"})
        else:
            err = span_ft - expect
            pct = 100.0 * err / expect
            row.update({"measured_ft": round(span_ft, 1), "error_ft": round(err, 1),
                        "error_pct": round(pct, 1),
                        "verdict": ("PASS" if abs(pct) <= 5 else
                                    "REVIEW" if abs(pct) <= 10 else "FAIL"),
                        "note": "measured between the two identified property-line "
                                "families in the reconstruction plane"})

        if args.ink_diagnostic and master.exists():
            along = np.array([1.0, m]) / np.hypot(1.0, m) if t["direction"] in ("north", "south") \
                else np.array([m, 1.0]) / np.hypot(m, 1.0)
            centre = 0.5 * (np.percentile(d, 10) + np.percentile(d, 90))
            base = P.mean(axis=0)
            n = normal / np.linalg.norm(normal)
            stations = [base + n * (centre - (n @ base)) + along * s
                        for s in np.linspace(-1200, 1200, args.stations)]
            vals = [frontage_gap(master, grid, s, along, px_per_ft) for s in stations]
            vals = [v for v in vals if v is not None and 45 < v < 115]
            row["ink_diagnostic_ft"] = round(float(np.median(vals)), 1) if vals else ""
            row["ink_diagnostic_n"] = len(vals)
        out.append(row)

    with (p.qc / "shared_street_width.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out[0].keys()))
        w.writeheader()
        w.writerows(out)

    print("\n  Shared-street width, measured between the two IDENTIFIED "
          "property-line\n  families in the reconstruction plane "
          f"(scale {px_per_ft:.4f} px/ft).\n")
    print(f"  {'seam':<16}{'shared street':<24}{'n':>3}{'exp':>7}{'meas':>7}"
          f"{'err %':>7}  verdict")
    for r in out:
        print(f"  {r['seam']:<16}{r['shared'][:23]:<24}{r['n_control']:>3}"
              f"{r['expected_ft']:>7.1f}{str(r['measured_ft']):>7}"
              f"{str(r['error_pct']):>7}  {r['verdict']}")
    testable = [r for r in out if r["verdict"] not in ("NOT TESTABLE",)]
    print(f"\n  {len(testable)} of {len(out)} seams can be tested this way; "
          f"the rest share no inked ground and their width is not observed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
