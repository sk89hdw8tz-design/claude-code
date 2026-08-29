#!/usr/bin/env python3
"""Place the ring-flagged units by 1D corridor-profile alignment.

Vacant outlot sheets defeat 2D patch matching (repeating lot ticks alias),
but their STREET STRUCTURE is still drawn: the ink-line profile along a
seam band has unambiguous peaks at the streets crossing it. Aligning the
two sheets' profiles by 1D correlation (search +-700) gives the along-seam
offset; the boundary corridor's own detected line gives the across-seam
offset. Rotation/scale = the placed neighbourhood's median (rigid-scan
physics; the profiles cannot alias at street pitch because a sheet carries
only 3-4 streets and its ends are distinct).

Reads out/affine_city_1899.json (ring result), rewrites flagged units in
place, appends 'profile' placements to out/ring_report.json.
"""
import json
import os
from collections import OrderedDict

import cv2
import numpy as np

ROOT = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(ROOT)
os.chdir(REPO)

NET = json.load(open(os.path.join(ROOT, "out", "city_network.json")))
AFFJ = json.load(open(os.path.join(ROOT, "out", "affine_city_1899.json")))
AFF = AFFJ["sheets"]
RR = json.load(open(os.path.join(ROOT, "out", "ring_report.json")))
FLAGGED = set(RR["flags"])

_gray = OrderedDict()
def unit_gray(uid):
    f = NET["units"][uid]["file"]
    if f not in _gray:
        _gray[f] = cv2.imread(f"work/sheets/1899/Galveston_1899_sheet_{f:02d}.jpg", 0)
        if len(_gray) > 8:
            _gray.popitem(last=False)
    return _gray[f]

def ink_profile(uid, axis, band_center, band_half=260):
    """Summed ink along the seam direction inside the band around the
    boundary line; returns a 1D profile indexed by the ALONG coordinate."""
    g = unit_gray(uid)
    x0, y0, x1, y1 = (int(v) for v in NET["units"][uid]["extent"])
    ink = (g < 205).astype(np.float32)
    if axis == "v":     # boundary vertical: band in x, profile over y
        lo = max(x0, int(band_center - band_half))
        hi = min(x1, int(band_center + band_half))
        prof = ink[y0:y1, lo:hi].mean(axis=1)
        base = y0
    else:               # boundary horizontal: band in y, profile over x
        lo = max(y0, int(band_center - band_half))
        hi = min(y1, int(band_center + band_half))
        prof = ink[lo:hi, x0:x1].mean(axis=0)
        base = x0
    k = np.ones(31) / 31
    return np.convolve(prof, k, mode="same"), base

def align_1d(pa, pb, search=700):
    """offset such that pb[i] ~ pa[i + offset]; normalized correlation."""
    best, best_v = None, -2
    la, lb = len(pa), len(pb)
    for off in range(-search, search + 1, 4):
        a0 = max(0, off); b0 = max(0, -off)
        n = min(la - a0, lb - b0)
        if n < 800:
            continue
        va = pa[a0:a0 + n] - pa[a0:a0 + n].mean()
        vb = pb[b0:b0 + n] - pb[b0:b0 + n].mean()
        d = np.sqrt((va ** 2).sum() * (vb ** 2).sum())
        if d < 1e-9:
            continue
        v = float((va * vb).sum() / d)
        if v > best_v:
            best, best_v = off, v
    return best, best_v

def neighbour_pose(uid):
    ths, scs = [], []
    for p in NET["pairs"]:
        if uid not in (p["owner"], p["nbr"]):
            continue
        other = p["nbr"] if p["owner"] == uid else p["owner"]
        if other in FLAGGED or other not in AFF:
            continue
        M = np.array(AFF[other]["m"])
        ths.append(np.degrees(np.arctan2(M[1, 0], M[0, 0])))
        scs.append(np.hypot(M[0, 0], M[1, 0]))
    th = float(np.median(ths)) if ths else 0.0
    sc = float(np.median(scs)) if scs else 0.985
    r = np.radians(th)
    return sc * np.array([[np.cos(r), -np.sin(r)], [np.sin(r), np.cos(r)]]), th, sc

placed_order = [u for u in FLAGGED]
results = {}
for uid in sorted(placed_order):
    M, th, sc = neighbour_pose(uid)
    votes = []
    for p in NET["pairs"]:
        if uid not in (p["owner"], p["nbr"]):
            continue
        other = p["nbr"] if p["owner"] == uid else p["owner"]
        if other in FLAGGED or other not in AFF:
            continue
        i_am_owner = p["owner"] == uid
        my_native = p["owner_native"] if i_am_owner else p["nbr_native"]
        their_native = p["nbr_native"] if i_am_owner else p["owner_native"]
        pa, base_a = ink_profile(uid, p["axis"], my_native)
        pb, base_b = ink_profile(other, p["axis"], their_native)
        off, score = align_1d(pa, pb)
        if off is None or score < 0.35:
            continue
        # my ALONG coordinate c maps to their (c - base_a + base_b + ... )
        Mo = np.array(AFF[other]["m"]); to = np.array(AFF[other]["t"])
        if p["axis"] == "v":
            # same y-line: my (my_native, y) ~ their (their_native, y')
            y_mid = base_a + len(pa) // 2
            their_y = (y_mid - base_a - off) + base_b
            mine = np.array([my_native, y_mid], float)
            theirs = np.array([their_native, their_y], float)
        else:
            x_mid = base_a + len(pa) // 2
            their_x = (x_mid - base_a - off) + base_b
            mine = np.array([x_mid, my_native], float)
            theirs = np.array([their_x, their_native], float)
        g = Mo @ theirs + to
        t_vote = g - M @ mine
        votes.append((t_vote, score, f"{p['owner']}|{p['nbr']}"))
    if votes:
        t = np.median(np.array([v[0] for v in votes]), axis=0)
        AFF[uid] = {"m": [[float(v) for v in row] for row in M],
                    "t": [float(v) for v in t],
                    "how": f"profile(n={len(votes)},th={th:.2f},sc={sc:.4f})"}
        results[uid] = {"votes": [(list(map(float, v[0])), round(v[1], 3), v[2])
                                  for v in votes],
                        "theta": th, "scale": sc}
        spread = np.array([v[0] for v in votes])
        sp = float(np.abs(spread - spread.mean(0)).max()) if len(votes) > 1 else 0.0
        print(f"  {uid}: {len(votes)} profile votes, spread {sp:.0f}px, "
              f"scores {[round(v[1],2) for v in votes]}")
    else:
        print(f"  {uid}: NO profile alignment (stays prior-placed)")
json.dump(AFFJ, open(os.path.join(ROOT, "out", "affine_city_1899.json"), "w"), indent=1)
RR["profile_placements"] = results
json.dump(RR, open(os.path.join(ROOT, "out", "ring_report.json"), "w"), indent=1)
print(f"profile-placed {len(results)}/{len(FLAGGED)} flagged units")
