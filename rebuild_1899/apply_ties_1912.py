#!/usr/bin/env python3
"""Place the flagged 1899 units from the adjudicators' blind ties.

Iterative: a flagged unit with ties to already-placed units gets placed
(full similarity fit when >=3 well-spread ties pass IRLS; otherwise
neighbourhood pose + median-translation from the ties), then can anchor its
own flagged neighbours on the next sweep. Updates
out/affine_city_1912.json in place; remaining uncovered units stay flagged.
"""
import json
import os

import numpy as np

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "out")
NET = json.load(open(os.path.join(OUT, "network_1912.json")))
AFFJ = json.load(open(os.path.join(OUT, "affine_city_1912.json")))
AFF = AFFJ["sheets"]
RR = json.load(open(os.path.join(OUT, "ring_1912_report.json")))
FLAGGED = set(RR["flags"])

ties = []
for tag in ("G", "H"):
    _p = os.path.join(OUT, f"adjudicate_{tag}_result.json")
    if not os.path.exists(_p):
        continue
    for t in json.load(open(_p))["ties"]:
        if "owner_xy" in t and "nbr_xy" in t and t.get("confidence") != "low":
            ties.append(t)
print(f"{len(ties)} usable ties")

def pose_of(uid):
    M = np.array(AFF[uid]["m"])
    return M, np.array(AFF[uid]["t"])

def nbr_pose(uid, solid):
    ths, scs = [], []
    for p in NET["pairs"]:
        if uid not in (p["owner"], p["nbr"]):
            continue
        o = p["nbr"] if p["owner"] == uid else p["owner"]
        if o in solid:
            M = np.array(AFF[o]["m"])
            ths.append(np.degrees(np.arctan2(M[1, 0], M[0, 0])))
            scs.append(np.hypot(M[0, 0], M[1, 0]))
    th = float(np.median(ths)) if ths else 0.0
    sc = float(np.median(scs)) if scs else 2.0
    r = np.radians(th)
    return sc * np.array([[np.cos(r), -np.sin(r)], [np.sin(r), np.cos(r)]])

def fit_sim(cor):
    A = np.array([c[0] for c in cor]); B = np.array([c[1] for c in cor])
    w = np.ones(len(A))
    for _ in range(5):
        if w.sum() < 1e-6:
            return None
        ca = (A*w[:,None]).sum(0)/w.sum(); cb = (B*w[:,None]).sum(0)/w.sum()
        A0, B0 = A-ca, B-cb
        H = (A0*w[:,None]).T @ B0
        den = ((A0**2)*w[:,None]).sum()
        if not np.isfinite(H).all() or den < 1e-6:
            return None
        try:
            U,S,Vt = np.linalg.svd(H)
        except np.linalg.LinAlgError:
            return None
        R = Vt.T @ U.T
        if np.linalg.det(R) < 0:
            Vt[-1] *= -1; R = Vt.T @ U.T
        s = S.sum()/den; t = cb - s*R@ca
        res = np.hypot(*(((s*(R@A0.T)).T+cb)-B).T)
        w = np.where(res <= 8, 1.0, np.sqrt(8/np.maximum(res,1e-9)))
        w = np.where(res > 80, 0.0, w)
    keep = w > 0
    if keep.sum() < 2:
        return None
    return s*R, t, float(np.median(res[keep])), int(keep.sum())

solid = set(AFF) - FLAGGED
placed_now = {}
for sweep in range(6):
    progress = False
    for uid in sorted(FLAGGED - set(placed_now)):
        cor = []
        for t in ties:
            a, b = t["pair"]
            if a == uid and b in solid:
                Mo, to = pose_of(b)
                cor.append((np.array(t["owner_xy"], float),
                            Mo @ np.array(t["nbr_xy"], float) + to))
            elif b == uid and a in solid:
                Mo, to = pose_of(a)
                cor.append((np.array(t["nbr_xy"], float),
                            Mo @ np.array(t["owner_xy"], float) + to))
        if len(cor) < 2:
            continue
        spread = np.ptp(np.array([c[0] for c in cor]), axis=0).max() if len(cor) > 2 else 0
        fit = fit_sim(cor) if len(cor) >= 3 and spread > 800 else None
        if fit:
            M, t_, med, kept = fit
            sc = float(np.hypot(M[0,0], M[1,0]))
            th = float(np.degrees(np.arctan2(M[1,0], M[0,0])))
            if not (0.90 <= sc <= 2.20 and abs(th) <= 3.0 and med <= 25):
                fit = None
        if fit:
            M, t_, med, kept = fit
            how = f"ties-sim(n={kept},med={med:.1f})"
        else:
            M = nbr_pose(uid, solid)
            votes = np.array([g - M @ m for m, g in cor])
            # Largest agreeing cluster wins: a single mismeasured tie must not
            # drag the median (2-vote medians are maximally fragile).
            best, best_n = None, 0
            for c in votes:
                inl = votes[np.hypot(*(votes - c).T) <= 150]
                if len(inl) > best_n:
                    best, best_n = inl, len(inl)
            if best_n < 2 and len(votes) > 1:
                sp = float(np.hypot(*(votes - votes.mean(0)).T).max())
                print(f"  {uid}: tie votes disagree by {sp:.0f}px — left flagged")
                continue
            t_ = np.median(best, axis=0)
            sp = float(np.hypot(*(best - t_).T).max()) if best_n > 1 else 0.0
            how = f"ties-trans(n={best_n}/{len(votes)},spread={sp:.0f})"
        AFF[uid] = {"m": [[float(v) for v in r] for r in M],
                    "t": [float(v) for v in t_], "how": how}
        placed_now[uid] = how
        solid.add(uid)
        progress = True
        print(f"  {uid}: {how}")
    if not progress:
        break

RR["tie_placements"] = placed_now
RR["still_flagged"] = sorted(FLAGGED - set(placed_now))
json.dump(AFFJ, open(os.path.join(OUT, "affine_city_1912.json"), "w"), indent=1)
json.dump(RR, open(os.path.join(OUT, "ring_1912_report.json"), "w"), indent=1)
print(f"tie-placed {len(placed_now)}; still flagged: {RR['still_flagged']}")
