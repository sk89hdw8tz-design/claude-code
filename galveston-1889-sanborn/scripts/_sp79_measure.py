#!/usr/bin/env python3
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import _sp79_fit as F
import _sp79_lines as L
_cent = F._cent

def shared_slope(n, xguesses, y0, y1, half=5, bg=200., minw=40.):
    g = F.gray(n); data=[]
    for xg in xguesses:
        pts=[]
        for y in range(y0,y1+1):
            lo,hi=int(round(xg-half)),int(round(xg+half))
            c,w=_cent(g[y,lo:hi+1], np.arange(lo,hi+1,dtype=np.float32), bg)
            if c is None or w<minw: continue
            pts.append((y,c))
        data.append(np.array(pts,float))
    keep=[np.ones(len(d),bool) for d in data]; K=len(data)
    for it in range(5):
        rows=[];rhs=[]
        for k,d in enumerate(data):
            for y,x in d[keep[k]]:
                r=np.zeros(K+1); r[0]=y; r[1+k]=1.0; rows.append(r); rhs.append(x)
        sol,*_=np.linalg.lstsq(np.array(rows),np.array(rhs),rcond=None)
        m=sol[0]; ints=sol[1:]
        for k,d in enumerate(data):
            res=d[:,1]-(m*d[:,0]+ints[k])
            s=np.sqrt((res[keep[k]]**2).mean()); keep[k]=np.abs(res)<max(2.5*s,0.8)
    out=[]
    for k,d in enumerate(data):
        res=d[keep[k],1]-(m*d[keep[k],0]+ints[k])
        out.append(dict(m=float(m), b=float(ints[k]), n=int(keep[k].sum()),
                        rms=float(np.sqrt((res**2).mean())),
                        at=lambda y,mm=m,bb=ints[k]: float(mm*y+bb)))
    return out

def wins(center, side, n=5, w=40, gap=10):
    """n windows of width w on 'side' ('L' or 'R') of center, starting gap px away."""
    out=[]
    for i in range(n):
        if side=='R':
            x0=int(center+gap+i*w)
        else:
            x0=int(center-gap-(i+1)*w)
        out.append((x0,x0+w))
    return out
