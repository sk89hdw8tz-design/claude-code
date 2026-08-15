#!/usr/bin/env python3
"""Local horizontal-line locator: deeper-peak centroid in narrow x windows, then line fit."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import _sp79_fit as F

def peak_center(n, ylo, yhi, x0, x1, pick='first', bg=200.0, minfrac=0.45):
    """Row profile over [ylo,yhi] x [x0,x1]; segment above minfrac*max; return centroid of
    the chosen segment ('first' = smallest y, 'last' = largest y, 'max' = strongest)."""
    p = F.rowprof(n, ylo, yhi, x0, x1, bg=bg)
    if p.max() < 12: return None
    t = p.max()*minfrac
    segs=[]; i=0
    while i < len(p):
        if p[i] > t:
            j=i
            while j < len(p) and p[j] > t: j+=1
            s=p[i:j]; c=(np.arange(i,j)*s).sum()/s.sum()+ylo
            segs.append((float(c), float(s.max()), j-i))
            i=j
        else: i+=1
    if not segs: return None
    if pick=='first': return segs[0]
    if pick=='last':  return segs[-1]
    return max(segs, key=lambda s:s[1])

def local_hline(n, yguess, xc, pick, windows, halfy=9, bg=200.0, minfrac=0.45, verbose=False):
    """windows: list of (x0,x1) sample windows. Fit y = m*x + b to their peak centres."""
    pts=[]
    for (x0,x1) in windows:
        r = peak_center(n, int(yguess-halfy), int(yguess+halfy), x0, x1, pick=pick, bg=bg, minfrac=minfrac)
        if r is None: continue
        pts.append(((x0+x1)/2.0, r[0], r[1], r[2]))
    if len(pts) < 2: return None
    P=np.array([(a,b) for a,b,_,_ in pts])
    A=np.vstack([P[:,0], np.ones(len(P))]).T
    sol,*_=np.linalg.lstsq(A,P[:,1],rcond=None)
    res=P[:,1]-A@sol
    rms=float(np.sqrt((res**2).mean())) if len(P)>2 else 0.0
    if verbose:
        for (xm,yv,pk,w) in pts: print('      win x=%7.1f  y=%9.3f peak=%5.1f w=%d'%(xm,yv,pk,w))
    return dict(m=float(sol[0]), b=float(sol[1]), n=len(P), rms=rms,
                at=lambda x,s=sol: float(s[0]*x+s[1]), pts=pts)
