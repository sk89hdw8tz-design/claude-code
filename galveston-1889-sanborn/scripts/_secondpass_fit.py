#!/usr/bin/env python3
"""Fit near-vertical / near-horizontal ink lines and intersect them."""
import os
import numpy as np
from PIL import Image
Image.MAX_IMAGE_PIXELS = None

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHEETS = {
    '1': os.path.join(ROOT, 'data/original/txu-sanborn-galveston-1889-Sheet 1.jpg'),
    '2': os.path.join(ROOT, 'data/original/txu-sanborn-galveston-1889-Sheet 2.jpg'),
}
_c = {}


def gray(n):
    if n not in _c:
        _c[n] = np.asarray(Image.open(SHEETS[n]).convert('L')).astype(np.float32)
    return _c[n]


def _cent(vals, coords, bg):
    w = np.clip(bg - vals, 0, None)
    if w.sum() < 1e-6:
        return None, 0.0
    return float((w*coords).sum()/w.sum()), float(w.sum())


def fit_vert(n, xguess, y0, y1, half=7, bg=205.0, minw=60.0):
    """Return (slope dx/dy, x at y=0 intercept, samples, rms)."""
    g = gray(n)
    xs, ys = [], []
    for y in range(y0, y1+1):
        lo, hi = int(xguess-half), int(xguess+half)
        row = g[y, lo:hi+1]
        c, w = _cent(row, np.arange(lo, hi+1, dtype=np.float32), bg)
        if c is None or w < minw:
            continue
        xs.append(c); ys.append(y)
    if len(ys) < 5:
        return None
    ys = np.array(ys, float); xs = np.array(xs, float)
    A = np.vstack([ys, np.ones_like(ys)]).T
    sol, *_ = np.linalg.lstsq(A, xs, rcond=None)
    res = xs - A@sol
    return dict(m=sol[0], b=sol[1], n=len(ys), rms=float(np.sqrt((res**2).mean())),
                at=lambda y, s=sol: s[0]*y + s[1])


def fit_horz(n, yguess, x0, x1, half=7, bg=205.0, minw=60.0):
    g = gray(n)
    xs, ys = [], []
    for x in range(x0, x1+1):
        lo, hi = int(yguess-half), int(yguess+half)
        col = g[lo:hi+1, x]
        c, w = _cent(col, np.arange(lo, hi+1, dtype=np.float32), bg)
        if c is None or w < minw:
            continue
        ys.append(c); xs.append(x)
    if len(xs) < 5:
        return None
    xs = np.array(xs, float); ys = np.array(ys, float)
    A = np.vstack([xs, np.ones_like(xs)]).T
    sol, *_ = np.linalg.lstsq(A, ys, rcond=None)
    res = ys - A@sol
    return dict(m=sol[0], b=sol[1], n=len(xs), rms=float(np.sqrt((res**2).mean())),
                at=lambda x, s=sol: s[0]*x + s[1])


def intersect(v, h):
    """v: x = mv*y + bv ; h: y = mh*x + bh."""
    mv, bv = v['m'], v['b']
    mh, bh = h['m'], h['b']
    y = (mh*bv + bh)/(1 - mh*mv)
    x = mv*y + bv
    return float(x), float(y)
