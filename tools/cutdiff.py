#!/usr/bin/env python3
"""Diff two `streetcut.py --dump-cuts` dumps: which seams' cut lines moved.

    python3 tools/streetcut.py --year 1912 --dump-cuts before.json
    ... change something ...
    python3 tools/streetcut.py --year 1912 --dump-cuts after.json
    python3 tools/cutdiff.py before.json after.json [--min-move 50] [--out moved.json]

The re-cut agent needs the CHANGED-SEAM SET, not a re-grade of all 249 seams
(HQ P1-2). Each dump holds one entry per pair cut on a min-ink path, with the
path in mosaic px. Two paths are compared by sampling the later one at the
earlier one's positions ALONG the seam and taking the distance ACROSS it, so
the numbers are in the same units the graders use: median, 90th percentile and
maximum movement in px and ft. Pairs cut in only one of the two runs are
listed separately -- that is a change of kind, not of position.
"""
import argparse
import json
import sys

import numpy as np

PX_PER_FT = 5.7966          # 1912 city mosaic ground scale


def load(p):
    d = json.load(open(p))
    out = {}
    for c in d["cuts"]:
        out[tuple(c["pair"])] = c
    return d, out


def move(a, b):
    """(median, p90, max) across-seam movement in px between two cut lines."""
    axis = a["axis"]
    A = np.array(a["line"], float)
    B = np.array(b["line"], float)
    if A.ndim != 2 or B.ndim != 2 or len(A) < 2 or len(B) < 2:
        return None
    # along = the axis the path marches down; across = the axis the seam cuts on
    ai, xi = (1, 0) if axis == "x" else (0, 1)
    o = np.argsort(B[:, ai])
    lo, hi = max(A[:, ai].min(), B[:, ai].min()), min(A[:, ai].max(), B[:, ai].max())
    s = A[(A[:, ai] >= lo) & (A[:, ai] <= hi)]
    if len(s) < 2:
        return None
    at = np.interp(s[:, ai], B[o, ai], B[o, xi])
    d = np.abs(at - s[:, xi])
    return float(np.median(d)), float(np.percentile(d, 90)), float(d.max())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("before")
    ap.add_argument("after")
    ap.add_argument("--min-move", type=float, default=50.0,
                    help="px: report a seam as moved above this maximum movement")
    ap.add_argument("--out", default=None, help="write the changed-seam set as JSON")
    a = ap.parse_args()

    da, A = load(a.before)
    db, B = load(a.after)
    print(f"{a.before}: {len(A)} cuts (blank-band rule "
          f"{'on' if da.get('blank_band_rule') else 'off'})")
    print(f"{a.after}:  {len(B)} cuts (blank-band rule "
          f"{'on' if db.get('blank_band_rule') else 'off'})")
    only_a = sorted(set(A) - set(B))
    only_b = sorted(set(B) - set(A))
    rows = []
    for k in sorted(set(A) & set(B)):
        m = move(A[k], B[k])
        if m is None:
            continue
        med, p90, mx = m
        rows.append({"pair": list(k), "axis": A[k]["axis"],
                     "median_px": round(med, 1), "p90_px": round(p90, 1),
                     "max_px": round(mx, 1), "max_ft": round(mx / PX_PER_FT, 1),
                     "coord_before": A[k]["coord"], "coord_after": B[k]["coord"],
                     "off_before": A[k].get("off"), "off_after": B[k].get("off"),
                     "blank_band_before": A[k].get("blank_band"),
                     "blank_band_after": B[k].get("blank_band")})
    moved = [r for r in rows if r["max_px"] > a.min_move]
    moved.sort(key=lambda r: -r["max_px"])
    print(f"{len(moved)} of {len(rows)} shared seams moved more than "
          f"{a.min_move:.0f} px ({a.min_move / PX_PER_FT:.0f} ft):")
    for r in moved:
        bb = r["blank_band_after"]
        print(f"    {r['pair'][0]:>3}|{r['pair'][1]:<3} {r['axis']}  max "
              f"{r['max_px']:8.1f} px ({r['max_ft']:6.1f} ft)  median "
              f"{r['median_px']:8.1f}  off {r['off_before']} -> {r['off_after']}"
              + (f"  blank band -> {bb['winner']} (ratio {bb['ink_ratio']:.2f})" if bb else ""))
    if only_a:
        print(f"cut on a min-ink path in {a.before} only: "
              f"{', '.join('|'.join(k) for k in only_a)}")
    if only_b:
        print(f"cut on a min-ink path in {a.after} only: "
              f"{', '.join('|'.join(k) for k in only_b)}")
    if a.out:
        json.dump({"before": a.before, "after": a.after,
                   "min_move_px": a.min_move,
                   "changed_pairs": [r["pair"] for r in moved],
                   "moved": moved,
                   "only_before": [list(k) for k in only_a],
                   "only_after": [list(k) for k in only_b]},
                  open(a.out, "w"), indent=1)
        print(f"wrote {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
