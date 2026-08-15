#!/usr/bin/env python3
"""Toolkit for measuring DRAWN avenue widths (frontage line to frontage line).

Everything local. No network, no external image APIs.
"""
import os
import numpy as np
from PIL import Image
Image.MAX_IMAGE_PIXELS = None

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ORIG = os.path.join(ROOT, 'data/original')
CROPS = os.path.join(ROOT, 'output/qc/manual_crops')
os.makedirs(CROPS, exist_ok=True)

SHEETS = ['1', '2', '7', '8', '9', '10', '27', '29']
_cache = {}


def path(n):
    return os.path.join(ORIG, f'txu-sanborn-galveston-1889-Sheet {n}.jpg')


def gray(n):
    """Full-sheet greyscale float32 array, cached."""
    n = str(n)
    if n not in _cache:
        _cache[n] = np.asarray(Image.open(path(n)).convert('L')).astype(np.float32)
    return _cache[n]


def shape(n):
    g = gray(n)
    return g.shape  # (h, w)


def overview(n, width=1100, out=None):
    im = Image.open(path(n)).convert('L')
    w, h = im.size
    im2 = im.resize((width, int(h * width / w)), Image.LANCZOS)
    out = out or os.path.join(CROPS, f'S{n}_overview.png')
    im2.save(out)
    return out


def crop(n, x0, y0, x1, y1, zoom=1, out=None, grid=0, gridcolor=(255, 0, 0)):
    """Save a crop, optionally upscaled with NEAREST so 1 source px is visible,
    with an optional overlay grid every `grid` SOURCE pixels."""
    g = gray(n)
    h, w = g.shape
    x0, y0 = max(0, int(x0)), max(0, int(y0))
    x1, y1 = min(w, int(x1)), min(h, int(y1))
    a = g[y0:y1, x0:x1].astype(np.uint8)
    im = Image.fromarray(a).convert('RGB')
    if zoom != 1:
        im = im.resize(((x1 - x0) * zoom, (y1 - y0) * zoom), Image.NEAREST)
    if grid:
        arr = np.asarray(im).copy()
        for sx in range(0, x1 - x0, grid):
            arr[:, sx * zoom:sx * zoom + 1] = gridcolor
        for sy in range(0, y1 - y0, grid):
            arr[sy * zoom:sy * zoom + 1, :] = gridcolor
        im = Image.fromarray(arr)
    out = out or os.path.join(CROPS, f'S{n}_{x0}_{y0}_{x1}_{y1}_z{zoom}.png')
    im.save(out)
    return out


# ---------------------------------------------------------------- profiles

def col_darkness(n, y0, y1, x0, x1):
    """Mean darkness (255-grey) per column over rows y0:y1. Returns (xs, v)."""
    g = gray(n)[y0:y1, x0:x1]
    v = 255.0 - g.mean(axis=0)
    return np.arange(x0, x1), v


def row_darkness(n, x0, x1, y0, y1):
    g = gray(n)[y0:y1, x0:x1]
    v = 255.0 - g.mean(axis=1)
    return np.arange(y0, y1), v


def peaks(xs, v, thresh_frac=0.5, minsep=8):
    """Crude peak list for reconnaissance."""
    thr = v.min() + (v.max() - v.min()) * thresh_frac
    out = []
    i = 0
    while i < len(v):
        if v[i] >= thr:
            j = i
            while j < len(v) and v[j] >= thr:
                j += 1
            seg = v[i:j]
            idx = np.arange(i, j)
            c = (seg * idx).sum() / seg.sum()
            out.append((float(xs[0] + c), float(seg.max()), j - i))
            i = j
        else:
            i += 1
    return out


# --------------------------------------------------- sub-pixel line centre

def line_centre(n, xguess, y0, y1, half=12, axis='v', bgpct=15):
    """Darkness-weighted centroid of the dark line nearest xguess, using the
    contiguous above-threshold run containing the local maximum.

    axis='v': near-vertical line, profile across x over rows y0:y1.
    axis='h': near-horizontal line, profile across y over cols y0:y1 (naming reused).
    Returns (centre, peak_darkness, run_width_px) or (None, 0, 0).
    """
    g = gray(n)
    xg = int(round(xguess))
    if axis == 'v':
        a = g[y0:y1, max(0, xg - half):xg + half + 1]
        v = 255.0 - a.mean(axis=0)
        base = max(0, xg - half)
    else:
        a = g[max(0, xg - half):xg + half + 1, y0:y1]
        v = 255.0 - a.mean(axis=1)
        base = max(0, xg - half)
    if v.size == 0:
        return None, 0.0, 0
    bg = np.percentile(v, bgpct)
    v = v - bg
    v[v < 0] = 0
    if v.max() <= 0:
        return None, 0.0, 0
    i = int(np.argmax(v))
    thr = v[i] * 0.5          # half-max run -> stable centroid, ignores tails
    lo = hi = i
    while lo > 0 and v[lo - 1] > thr:
        lo -= 1
    while hi < len(v) - 1 and v[hi + 1] > thr:
        hi += 1
    idx = np.arange(lo, hi + 1)
    w = v[lo:hi + 1]
    c = (w * idx).sum() / w.sum()
    return float(base + c), float(v[i]), int(hi - lo + 1)


def fit_line(n, xguess, ybands, half=12, axis='v', yref=2000.0, minpeak=6.0):
    """Fit x = a + b*(y - yref) over a list of (y0,y1) bands.
    Robust: one pass, then drop >2.5 sigma outliers and refit."""
    pts = []
    for (y0, y1) in ybands:
        c, pk, wd = line_centre(n, xguess, y0, y1, half=half, axis=axis)
        if c is None or pk < minpeak:
            continue
        pts.append((0.5 * (y0 + y1), c, pk, wd))
    if len(pts) < 2:
        return None
    def solve(P):
        ys = np.array([p[0] for p in P]); xs = np.array([p[1] for p in P])
        A = np.vstack([np.ones(len(ys)), ys - yref]).T
        sol, *_ = np.linalg.lstsq(A, xs, rcond=None)
        r = xs - A @ sol
        return sol, r
    sol, r = solve(pts)
    if len(pts) > 4:
        s = r.std()
        if s > 0:
            keep = [p for p, rr in zip(pts, r) if abs(rr) <= 2.5 * s]
            if 2 <= len(keep) < len(pts):
                pts = keep
                sol, r = solve(pts)
    return {
        'a': float(sol[0]), 'b': float(sol[1]), 'yref': float(yref),
        'rms': float(np.sqrt((r ** 2).mean())),
        'n': len(pts),
        'mean_peak': float(np.mean([p[2] for p in pts])),
        'mean_width': float(np.mean([p[3] for p in pts])),
        'pts': [(round(p[0], 1), round(p[1], 3), round(p[2], 1), p[3]) for p in pts],
    }


def at(f, y):
    return f['a'] + f['b'] * (y - f['yref'])


def bands(y0, y1, nb, bh=None):
    """nb bands spanning y0..y1."""
    step = (y1 - y0) / nb
    bh = bh or step
    return [(int(y0 + i * step), int(y0 + i * step + bh)) for i in range(nb)]


# ============================================================ robust detector

def _baseline(v, pct=20):
    return np.percentile(v, pct)


def find_line_halfmax(n, xguess, y0, y1, half=14, axis='v', frac=0.5,
                      return_profile=False):
    """Locate a near-vertical (axis='v') or near-horizontal (axis='h') heavy
    line by half-max crossing midpoint of the dominant peak near xguess.

    Half-max midpoint is used rather than a centroid because it is insensitive
    to asymmetric ink (adjacent thin lot lines, address numerals) that biases a
    centroid, while still being sub-pixel.
    Returns dict or None.
    """
    g = gray(n)
    xg = int(round(xguess))
    lo_i = max(0, xg - half)
    if axis == 'v':
        a = g[y0:y1, lo_i:xg + half + 1]
        v = 255.0 - a.mean(axis=0)
    else:
        a = g[lo_i:xg + half + 1, y0:y1]
        v = 255.0 - a.mean(axis=1)
    if v.size < 5:
        return None
    v = v - _baseline(v)
    v[v < 0] = 0
    if v.max() <= 0:
        return None
    i = int(np.argmax(v))
    hm = v[i] * frac
    # left crossing
    j = i
    while j > 0 and v[j] >= hm:
        j -= 1
    if v[j] >= hm:
        return None
    xl = j + (hm - v[j]) / (v[j + 1] - v[j])
    k = i
    while k < len(v) - 1 and v[k] >= hm:
        k += 1
    if v[k] >= hm:
        return None
    xr = k - (hm - v[k]) / (v[k - 1] - v[k])
    c = lo_i + 0.5 * (xl + xr)
    out = {'c': float(c), 'peak': float(v[i]), 'fwhm': float(xr - xl)}
    if return_profile:
        out['prof'] = (np.arange(lo_i, lo_i + len(v)), v)
    return out


def continuity(n, x, y0, y1, halfw=3, thresh=100):
    """Fraction of rows in y0:y1 where some pixel within +/-halfw of x is
    darker than `thresh`. ~1.0 for a heavy continuous line, ~0.5 for dashed."""
    g = gray(n)
    a = g[y0:y1, max(0, int(round(x)) - halfw):int(round(x)) + halfw + 1]
    return float((a.min(axis=1) < thresh).mean())


def fit_halfmax(n, xguess, ybands, half=14, axis='v', yref=2000.0,
                minpeak=15.0, sigma_clip=2.5):
    """Fit centre = a + b*(t - yref) using half-max detection in each band."""
    pts = []
    xg = xguess
    for (y0, y1) in ybands:
        r = find_line_halfmax(n, xg, y0, y1, half=half, axis=axis)
        if r is None or r['peak'] < minpeak:
            continue
        pts.append((0.5 * (y0 + y1), r['c'], r['peak'], r['fwhm']))
    if len(pts) < 2:
        return None

    def solve(P):
        ts = np.array([p[0] for p in P]); cs = np.array([p[1] for p in P])
        A = np.vstack([np.ones(len(ts)), ts - yref]).T
        sol, *_ = np.linalg.lstsq(A, cs, rcond=None)
        return sol, cs - A @ sol
    sol, r = solve(pts)
    for _ in range(2):
        if len(pts) <= 4:
            break
        s = r.std()
        if s <= 1e-9:
            break
        keep = [p for p, rr in zip(pts, r) if abs(rr) <= sigma_clip * s]
        if len(keep) == len(pts) or len(keep) < 3:
            break
        pts = keep
        sol, r = solve(pts)
    return {'a': float(sol[0]), 'b': float(sol[1]), 'yref': float(yref),
            'rms': float(np.sqrt((r ** 2).mean())), 'n': len(pts),
            'span': (float(min(p[0] for p in pts)), float(max(p[0] for p in pts))),
            'mean_peak': float(np.mean([p[2] for p in pts])),
            'mean_fwhm': float(np.mean([p[3] for p in pts])),
            'pts': [(round(p[0], 1), round(p[1], 3), round(p[2], 1), round(p[3], 2)) for p in pts]}


# ================================================== stacked reconnaissance

def stack_profile(n, xc, halfwin, ybands, axis='v'):
    """Median-over-bands of the baseline-subtracted mean-darkness profile.

    Taking the MEDIAN across widely separated bands suppresses anything that is
    not present at every latitude (lettering, address numerals, party walls) and
    keeps structures that run the full height of the sheet -- which is exactly
    what a street frontage line is.
    """
    g = gray(n)
    lo = max(0, int(xc - halfwin)); hi = int(xc + halfwin)
    mats = []
    for (a, b) in ybands:
        if axis == 'v':
            v = 255.0 - g[a:b, lo:hi].mean(axis=0)
        else:
            v = 255.0 - g[lo:hi, a:b].mean(axis=1)
        v = v - np.percentile(v, 20)
        mats.append(v)
    m = np.median(np.vstack(mats), axis=0)
    return np.arange(lo, hi), m


def find_peaks_simple(xs, v, minprom=6.0, minsep=6):
    """Local maxima with prominence against the local minima either side."""
    out = []
    for i in range(1, len(v) - 1):
        if v[i] >= v[i - 1] and v[i] > v[i + 1]:
            j = i
            while j > 0 and v[j - 1] <= v[j]:
                j -= 1
            k = i
            while k < len(v) - 1 and v[k + 1] <= v[k]:
                k += 1
            prom = v[i] - max(v[j], v[k])
            if prom >= minprom:
                out.append({'x': float(xs[i]), 'v': float(v[i]), 'prom': float(prom)})
    out.sort(key=lambda d: -d['v'])
    keep = []
    for p in out:
        if all(abs(p['x'] - q['x']) >= minsep for q in keep):
            keep.append(p)
    keep.sort(key=lambda d: d['x'])
    return keep


def describe_candidates(n, xc, halfwin, ybands, axis='v', thresh=110):
    xs, v = stack_profile(n, xc, halfwin, ybands, axis=axis)
    ps = find_peaks_simple(xs, v)
    y0 = min(b[0] for b in ybands); y1 = max(b[1] for b in ybands)
    for p in ps:
        if axis == 'v':
            p['cont'] = continuity(n, p['x'], y0, y1, halfw=3, thresh=thresh)
        else:
            g = gray(n)
            a = g[max(0, int(p['x']) - 3):int(p['x']) + 4, y0:y1]
            p['cont'] = float((a.min(axis=0) < thresh).mean())
        p['d_from_centre'] = round(p['x'] - xc, 1)
    return ps
