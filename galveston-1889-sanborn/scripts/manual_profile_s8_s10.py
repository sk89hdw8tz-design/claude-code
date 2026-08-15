#!/usr/bin/env python3
"""Darkness profile helper for manual seam measurement.

profile(sheet, axis, lo, hi, other_lo, other_hi) -> list of (position, darkness)
Reports local dark minima with sub-pixel centroid, so a printed line can be
located precisely once it has been identified semantically from a crop.
"""
import sys
import os
import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None
BASE = "/home/user/claude-code/galveston-1889-sanborn"
ORIG = os.path.join(BASE, "data/original")
_cache = {}


def get(n):
    if n not in _cache:
        im = Image.open(os.path.join(
            ORIG, f"txu-sanborn-galveston-1889-Sheet {n}.jpg")).convert("L")
        _cache[n] = np.asarray(im, dtype=np.float32)
    return _cache[n]


def profile(sheet, axis, x0, x1, y0, y1):
    """axis='row' -> darkness vs y (averaged over x0..x1);
       axis='col' -> darkness vs x (averaged over y0..y1)."""
    a = get(sheet)[y0:y1, x0:x1]
    if axis == "row":
        v = 255.0 - a.mean(axis=1)
        base = y0
    else:
        v = 255.0 - a.mean(axis=0)
        base = x0
    return base, v


def peaks(base, v, min_prom=8.0, halfwin=3):
    """Return dark peaks (line centres) with parabolic sub-pixel refinement."""
    out = []
    med = np.median(v)
    for i in range(1, len(v) - 1):
        if v[i] >= v[i - 1] and v[i] > v[i + 1] and (v[i] - med) > min_prom:
            lo = max(0, i - halfwin)
            hi = min(len(v), i + halfwin + 1)
            w = v[lo:hi] - med
            w[w < 0] = 0
            if w.sum() <= 0:
                continue
            idx = np.arange(lo, hi)
            c = (w * idx).sum() / w.sum()
            out.append((round(base + c, 2), round(float(v[i] - med), 1)))
    # merge peaks closer than 2 px, keep strongest
    merged = []
    for p in out:
        if merged and abs(p[0] - merged[-1][0]) < 2.5:
            if p[1] > merged[-1][1]:
                merged[-1] = p
        else:
            merged.append(p)
    return merged


if __name__ == "__main__":
    sheet, axis = sys.argv[1], sys.argv[2]
    x0, x1, y0, y1 = (int(v) for v in sys.argv[3:7])
    prom = float(sys.argv[7]) if len(sys.argv) > 7 else 8.0
    b, v = profile(sheet, axis, x0, x1, y0, y1)
    print(f"sheet {sheet} {axis} band x[{x0},{x1}) y[{y0},{y1}) median={np.median(v):.1f}")
    for p, s in peaks(b, v, prom):
        print(f"  {p:9.2f}   strength {s:6.1f}")
