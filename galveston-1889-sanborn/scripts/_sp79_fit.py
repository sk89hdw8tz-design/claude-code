#!/usr/bin/env python3
"""Line fitting / profiling for S7|S9 second pass. Local only, no network."""
import os
import numpy as np
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHEETS = {
    '7': os.path.join(ROOT, 'data/original/txu-sanborn-galveston-1889-Sheet 7.jpg'),
    '9': os.path.join(ROOT, 'data/original/txu-sanborn-galveston-1889-Sheet 9.jpg'),
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

def fit_vert(n, xguess, y0, y1, half=6, bg=200.0, minw=40.0, clip=3.0, iters=3):
    """Fit a near-vertical ink line. Returns dict with at(y)."""
    g = gray(n)
    pts = []
    for y in range(int(y0), int(y1)+1):
        lo, hi = int(round(xguess-half)), int(round(xguess+half))
        row = g[y, lo:hi+1]
        c, w = _cent(row, np.arange(lo, hi+1, dtype=np.float32), bg)
        if c is None or w < minw: continue
        pts.append((y, c, w))
    if len(pts) < 8: return None
    P = np.array(pts, float)
    for _ in range(iters):
        A = np.vstack([P[:,0], np.ones(len(P))]).T
        sol, *_ = np.linalg.lstsq(A, P[:,1], rcond=None)
        res = P[:,1] - A@sol
        s = np.sqrt((res**2).mean())
        keep = np.abs(res) < max(clip*s, 0.6)
        if keep.sum() < 8 or keep.all(): break
        P = P[keep]
    A = np.vstack([P[:,0], np.ones(len(P))]).T
    sol, *_ = np.linalg.lstsq(A, P[:,1], rcond=None)
    res = P[:,1] - A@sol
    rms = float(np.sqrt((res**2).mean()))
    return dict(m=float(sol[0]), b=float(sol[1]), n=int(len(P)), rms=rms,
                span=(float(P[:,0].min()), float(P[:,0].max())),
                at=lambda y, s=sol: float(s[0]*y + s[1]),
                sigma_mean=rms/np.sqrt(len(P)))

def fit_horz(n, yguess, x0, x1, half=6, bg=200.0, minw=40.0, clip=3.0, iters=3):
    g = gray(n)
    pts = []
    for x in range(int(x0), int(x1)+1):
        lo, hi = int(round(yguess-half)), int(round(yguess+half))
        col = g[lo:hi+1, x]
        c, w = _cent(col, np.arange(lo, hi+1, dtype=np.float32), bg)
        if c is None or w < minw: continue
        pts.append((x, c, w))
    if len(pts) < 8: return None
    P = np.array(pts, float)
    for _ in range(iters):
        A = np.vstack([P[:,0], np.ones(len(P))]).T
        sol, *_ = np.linalg.lstsq(A, P[:,1], rcond=None)
        res = P[:,1] - A@sol
        s = np.sqrt((res**2).mean())
        keep = np.abs(res) < max(clip*s, 0.6)
        if keep.sum() < 8 or keep.all(): break
        P = P[keep]
    A = np.vstack([P[:,0], np.ones(len(P))]).T
    sol, *_ = np.linalg.lstsq(A, P[:,1], rcond=None)
    res = P[:,1] - A@sol
    rms = float(np.sqrt((res**2).mean()))
    return dict(m=float(sol[0]), b=float(sol[1]), n=int(len(P)), rms=rms,
                span=(float(P[:,0].min()), float(P[:,0].max())),
                at=lambda x, s=sol: float(s[0]*x + s[1]),
                sigma_mean=rms/np.sqrt(len(P)))

def intersect(v, h):
    """v: near-vertical fit x=m*y+b ; h: near-horizontal y=m*x+b."""
    # x = mv*y+bv ; y = mh*x+bh  ->  x = mv*(mh*x+bh)+bv
    x = (v['m']*h['b'] + v['b'])/(1 - v['m']*h['m'])
    y = h['m']*x + h['b']
    return float(x), float(y)

def rowprof(n, y0, y1, x0, x1, bg=200.0):
    g = gray(n)[y0:y1+1, x0:x1+1]
    return np.clip(bg-g, 0, None).mean(axis=1)

def colprof(n, x0, x1, y0, y1, bg=200.0):
    g = gray(n)[y0:y1+1, x0:x1+1]
    return np.clip(bg-g, 0, None).mean(axis=0)

def show(prof, start, thresh=None, label=''):
    mx = prof.max()
    t = thresh if thresh is not None else mx*0.35
    out = []
    i = 0
    while i < len(prof):
        if prof[i] > t:
            j = i
            while j < len(prof) and prof[j] > t: j += 1
            seg = prof[i:j]
            c = (np.arange(i, j)*seg).sum()/seg.sum() + start
            out.append((round(float(c),2), round(float(seg.max()),1), j-i))
            i = j
        else:
            i += 1
    print(label, 'max=%.1f thr=%.1f'%(mx,t))
    for o in out: print('   c=%8.2f peak=%6.1f w=%d'%o)
    return out
