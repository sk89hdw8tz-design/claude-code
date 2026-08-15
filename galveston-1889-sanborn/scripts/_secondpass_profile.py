#!/usr/bin/env python3
"""Ink-profile helper: locate line centres to sub-pixel precision on a chosen band."""
import sys, os
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
        im = Image.open(SHEETS[n]).convert('L')
        _c[n] = np.asarray(im).astype(np.float32)
    return _c[n]

def ink(n, x0, y0, x1, y1, thresh=140.0):
    """Return ink mask (1 = dark) for region."""
    g = gray(n)[y0:y1, x0:x1]
    return (g < thresh).astype(np.float32)

def rowprof(n, x0, x1, y0, y1, thresh=140.0):
    m = ink(n, x0, y0, x1, y1, thresh)
    s = m.sum(axis=1)
    return [(y0+i, float(v)) for i, v in enumerate(s)]

def colprof(n, y0, y1, x0, x1, thresh=140.0):
    m = ink(n, x0, y0, x1, y1, thresh)
    s = m.sum(axis=0)
    return [(x0+i, float(v)) for i, v in enumerate(s)]

def centroid(prof, lo, hi):
    """Darkness-weighted centroid of a peak between coords lo..hi inclusive."""
    sel = [(c, v) for c, v in prof if lo <= c <= hi]
    tot = sum(v for _, v in sel)
    if tot == 0:
        return None, 0.0
    return sum(c*v for c, v in sel)/tot, tot

def show(prof, minv=1.0):
    for c, v in prof:
        if v >= minv:
            print(f"{c:6d} {v:8.1f} {'#'*int(min(v, 90))}")
