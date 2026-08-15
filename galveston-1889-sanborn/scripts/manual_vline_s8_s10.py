#!/usr/bin/env python3
"""Locate a near-vertical printed line precisely in successive y-bands,
then fit x = x0 + slope*(y - yref) and evaluate at the seam property lines.

Only used after the line has been identified SEMANTICALLY from a crop.
"""
import json
import sys
import numpy as np
from manual_profile_s8_s10 import get


def line_x(sheet, xguess, y0, y1, half=9):
    """Darkness-weighted centroid of the dark line nearest xguess."""
    a = get(sheet)[y0:y1, int(xguess) - half:int(xguess) + half + 1]
    v = 255.0 - a.mean(axis=0)
    v = v - np.percentile(v, 10)
    v[v < 0] = 0
    # keep only the contiguous dark run containing the maximum
    i = int(np.argmax(v))
    lo, hi = i, i
    thr = v[i] * 0.30
    while lo > 0 and v[lo - 1] > thr:
        lo -= 1
    while hi < len(v) - 1 and v[hi + 1] > thr:
        hi += 1
    idx = np.arange(lo, hi + 1)
    w = v[lo:hi + 1]
    c = (w * idx).sum() / w.sum()
    return int(xguess) - half + c, float(v[i])


def fit(sheet, xguess, bands, half=9):
    pts = []
    for (y0, y1) in bands:
        x, s = line_x(sheet, xguess, y0, y1, half)
        pts.append((0.5 * (y0 + y1), x, s))
    ys = np.array([p[0] for p in pts])
    xs = np.array([p[1] for p in pts])
    if len(pts) > 1:
        A = np.vstack([ys - ys.mean(), np.ones(len(ys))]).T
        sol, *_ = np.linalg.lstsq(A, xs, rcond=None)
        slope, x_at_mean = sol
        resid = xs - (A @ sol)
    else:
        slope, x_at_mean, resid = 0.0, xs[0], np.array([0.0])
    return {
        "pts": [(round(p[0], 1), round(p[1], 2), round(p[2], 1)) for p in pts],
        "slope": float(slope), "ymean": float(ys.mean()),
        "x_at_ymean": float(x_at_mean),
        "resid_rms": float(np.sqrt((resid ** 2).mean())),
    }


def at(f, y):
    return f["x_at_ymean"] + f["slope"] * (y - f["ymean"])


if __name__ == "__main__":
    spec = json.loads(sys.argv[1])
    for name, sheet, xg, bands, evals in spec:
        f = fit(str(sheet), xg, [tuple(b) for b in bands])
        vals = {str(y): round(at(f, y), 2) for y in evals}
        print(f"{name:42s} S{sheet}  pts={f['pts']}  slope={f['slope']:+.5f}"
              f"  rms={f['resid_rms']:.2f}  ->  {vals}")
