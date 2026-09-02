#!/usr/bin/env python3
"""Residual of every accepted control where it matters: in the two plates'
shared band, sampled at 0.15 and 0.85 of the band's length.

    python3 tools/bandresid.py --year 1912 [--min-ft 6]

The point check (each plate's line at its own extent centre) reports a
rotation difference between two plates as a residual of a full plate
height's worth of tilt; the seam only shows the line where the plates
meet. Same sampling as tools/localsolve.py --similarity.
"""
import argparse
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from reciplib import Recipe, px_per_ft   # noqa: E402
import localsolve as ls                  # noqa: E402


def band_residuals(r):
    ppf = px_per_ft(r)
    out = []
    for f, ua, ub, vert, na, nb in ls.controls(r):
        O = r.footprint(ua).intersection(r.footprint(ub))
        if O.is_empty:
            out.append((f, ua, ub, None, None)); continue
        b = O.bounds
        k = 0 if vert else 1
        res = []
        for frac in (0.15, 0.85):
            vals = []
            for u, nat in ((ua, na), (ub, nb)):
                M, t = r.sheet_matrix(u)
                if vert:
                    ym = b[1] + frac * (b[3] - b[1])
                    p = np.array([nat, ((ym - t[1]) - M[1, 0] * nat) / M[1, 1]])
                else:
                    xm = b[0] + frac * (b[2] - b[0])
                    p = np.array([((xm - t[0]) - M[0, 1] * nat) / M[0, 0], nat])
                vals.append((M @ p + t)[k])
            res.append((vals[0] - vals[1]) / ppf)
        out.append((f, ua, ub, res[0], res[1]))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", type=int, default=1912)
    ap.add_argument("--min-ft", type=float, default=6.0)
    a = ap.parse_args()
    r = Recipe(a.year)
    rows = band_residuals(r)
    worst = [(max(abs(r0), abs(r1)), f, r0, r1) for f, ua, ub, r0, r1 in rows if r0 is not None]
    worst.sort(reverse=True)
    n = sum(1 for w in worst if w[0] > a.min_ft)
    print(f"{len(rows)} accepted controls; {n} with a band residual over {a.min_ft:g} ft "
          f"(median of max-abs {np.median([w[0] for w in worst]):.1f} ft)")
    for m, f, r0, r1 in worst:
        if m > a.min_ft:
            print(f"  {f:28s} {r0:+6.1f} / {r1:+6.1f} ft")
    for f, ua, ub, r0, r1 in rows:
        if r0 is None:
            print(f"  {f:28s} no overlap")


if __name__ == "__main__":
    main()
