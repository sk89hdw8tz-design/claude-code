#!/usr/bin/env python3
"""1912 city registration: interleaved measure + ring placement.

BFS outward from the frozen archival core (working scale = pct:50; core
transforms pre-scaled in network_1912.json). For each frontier unit, seed
its pose from a placed neighbour + the seam-line estimate, collect edge-NCC
correspondences (two-pass, mutual consistency) against ALL placed
neighbours, fit a similarity, sanity-check (scale 2.0 +-5% for pct50 units
against the archival-frame mosaic; theta within 1.8 deg of the placed
neighbourhood), else place by prior and flag.

Writes out/affine_city_1912.json + out/ring_1912_report.json.
"""
import json
import os
from collections import OrderedDict

import cv2
import numpy as np

ROOT = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(ROOT)
os.chdir(REPO)

NET = json.load(open(os.path.join(ROOT, "out", "network_1912.json")))
UNITS = NET["units"]
PAIRS = NET["pairs"]

_gray, _edge = OrderedDict(), OrderedDict()
def gray(uid):
    if uid not in _gray:
        _gray[uid] = cv2.imread(UNITS[uid]["working"], 0)
        if len(_gray) > 10:
            _gray.popitem(last=False)
    _gray.move_to_end(uid)
    return _gray[uid]

def edges(uid):
    if uid not in _edge:
        g = gray(uid)
        gx = cv2.Sobel(g, cv2.CV_32F, 1, 0, ksize=3)
        gy = cv2.Sobel(g, cv2.CV_32F, 0, 1, ksize=3)
        _edge[uid] = np.clip(cv2.magnitude(gx, gy) / 8.0, 0, 255).astype(np.uint8)
        if len(_edge) > 10:
            _edge.popitem(last=False)
    _edge.move_to_end(uid)
    return _edge[uid]

placed = {uid: {"m": np.array(v["m"]), "t": np.array(v["t"]), "how": "frozen-core"}
          for uid, v in NET["core_working"].items()}
nbr_pairs = {}
for p in PAIRS:
    nbr_pairs.setdefault(p["owner"], []).append(p)
    nbr_pairs.setdefault(p["nbr"], []).append(p)

def seam_mid(uid, p):
    u = UNITS[uid]
    x0, y0, x1, y1 = u["extent"]
    mine = p["owner_native"] if p["owner"] == uid else p["nbr_native"]
    if p["axis"] == "h":
        return np.array([(x0 + x1) / 2, mine], float)
    return np.array([mine, (y0 + y1) / 2], float)

def seed_pose(uid, p, other):
    Mo, to = placed[other]["m"], placed[other]["t"]
    M = Mo.copy() if not UNITS[uid]["core"] else Mo.copy()
    pm = seam_mid(uid, p)
    po = seam_mid(other, p)
    t = (Mo @ po + to) - M @ pm
    return M, t

def match_pts(uid, other, Mu, tu, search, thr=0.42):
    """Sample uid's seam bands vs other; return [(uid_native, mosaic_xy)]."""
    eo = edges(other)
    eu = edges(uid)
    Mo, to = placed[other]["m"], placed[other]["t"]
    Mo_inv = np.linalg.inv(Mo)
    out = []
    for p in nbr_pairs.get(uid, []):
        if (p["nbr"] if p["owner"] == uid else p["owner"]) != other:
            continue
        u = UNITS[uid]
        x0, y0, x1, y1 = (int(v) for v in u["extent"])
        mine = p["owner_native"] if p["owner"] == uid else p["nbr_native"]
        pts = []
        if p["axis"] == "h":
            for band in (-40, 0, 40):
                yy = int(mine) + band
                if 40 < yy < eu.shape[0] - 40:
                    pts += [(x, yy) for x in range(x0 + 60, x1 - 60, 55)]
        else:
            for band in (-40, 0, 40):
                xx = int(mine) + band
                if 40 < xx < eu.shape[1] - 40:
                    pts += [(xx, y) for y in range(y0 + 60, y1 - 60, 55)]
        h = 30
        for (x, y) in pts:
            tpl = eu[y - h:y + h + 1, x - h:x + h + 1]
            if tpl.shape != (2 * h + 1, 2 * h + 1) or tpl.std() < 12:
                continue
            g = Mu @ np.array([x, y], float) + tu
            q = Mo_inv @ (g - to)
            qx, qy = int(q[0]), int(q[1])
            x0s, y0s = qx - search, qy - search
            x1s, y1s = qx + search, qy + search
            x0c, y0c = max(0, x0s), max(0, y0s)
            x1c, y1c = min(eo.shape[1], x1s), min(eo.shape[0], y1s)
            if x1c - x0c < 2 * h + 20 or y1c - y0c < 2 * h + 20:
                continue
            res = cv2.matchTemplate(eo[y0c:y1c, x0c:x1c], tpl, cv2.TM_CCOEFF_NORMED)
            _, mx, _, ml = cv2.minMaxLoc(res)
            if mx < thr:
                continue
            bx, by = x0c + ml[0] + h, y0c + ml[1] + h
            # mutual check
            tpl2 = eo[by - h:by + h + 1, bx - h:bx + h + 1]
            if tpl2.shape != (2 * h + 1, 2 * h + 1) or tpl2.std() < 8:
                continue
            rx0, ry0 = max(0, x - 90), max(0, y - 90)
            res2 = cv2.matchTemplate(eu[ry0:y + 90, rx0:x + 90], tpl2,
                                     cv2.TM_CCOEFF_NORMED)
            _, mx2, _, ml2 = cv2.minMaxLoc(res2)
            if mx2 < thr:
                continue
            rxx, ryy = rx0 + ml2[0] + h, ry0 + ml2[1] + h
            if abs(rxx - x) > 4 or abs(ryy - y) > 4:
                continue
            gm = Mo @ np.array([bx, by], float) + to
            out.append((np.array([x, y], float), gm))
    return out

def fit_similarity(cor):
    A = np.array([c[0] for c in cor]); B = np.array([c[1] for c in cor])
    w = np.ones(len(A)); res = np.full(len(A), 1e9)
    for it in range(8):
        if w.sum() < 1e-6:
            return None
        ca = (A * w[:, None]).sum(0) / w.sum()
        cb = (B * w[:, None]).sum(0) / w.sum()
        A0, B0 = A - ca, B - cb
        H = (A0 * w[:, None]).T @ B0
        den = ((A0 ** 2) * w[:, None]).sum()
        if not np.isfinite(H).all() or den < 1e-6:
            return None
        try:
            U, S, Vt = np.linalg.svd(H)
        except np.linalg.LinAlgError:
            return None
        R = Vt.T @ U.T
        if np.linalg.det(R) < 0:
            Vt[-1] *= -1; R = Vt.T @ U.T
        s = S.sum() / den
        t = cb - s * R @ ca
        res = np.hypot(*(((s * (R @ A0.T)).T + cb) - B).T)
        w = np.where(res <= 12, 1.0, np.sqrt(12 / np.maximum(res, 1e-9)))
        if it >= 2:                     # let the fit settle before hard cuts
            w = np.where(res > 120, 0.0, w)
    keep = w > 0
    if keep.sum() < 3:
        return None
    return s * R, t, float(np.median(res[keep])), int(keep.sum())

def fit_multi(cors_by_nbr):
    """Per-neighbour pre-fits, then a merged fit over agreeing neighbours.
    Different seed poses put different neighbours' correspondences in
    conflict; fitting per neighbour first and merging only those whose
    poses agree (within 2 deg / 5% / 250 px at the unit centre) avoids the
    mid-way collapse."""
    pre = {}
    for nb, cor in cors_by_nbr.items():
        if len(cor) >= 3:
            f = fit_similarity(cor)
            if f:
                pre[nb] = (f, cor)
    if not pre:
        return None, "no per-neighbour fit"
    # cluster by pose agreement, seed = most-supported fit
    best_nb = max(pre, key=lambda nb: pre[nb][0][3])
    (Mb, tb, _, _), _ = pre[best_nb]
    merged = list(pre[best_nb][1])
    agree = [best_nb]
    c0 = np.array([1700.0, 2000.0])
    for nb, ((M, t, _, _), cor) in pre.items():
        if nb == best_nb:
            continue
        dth = abs(np.degrees(np.arctan2(M[1,0],M[0,0])) - np.degrees(np.arctan2(Mb[1,0],Mb[0,0])))
        dsc = abs(np.hypot(M[0,0],M[1,0]) - np.hypot(Mb[0,0],Mb[1,0]))
        dpt = np.hypot(*((M @ c0 + t) - (Mb @ c0 + tb)))
        if dth <= 2.0 and dsc <= 0.1 and dpt <= 250:
            merged += cor
            agree.append(nb)
    f = fit_similarity(merged)
    if not f:
        return None, "merged fit failed"
    return f, f"merged {len(agree)}/{len(pre)} neighbours"

flags, report = {}, {}
# 1) chained prior poses for EVERY unit (BFS from core): a prior only aims
#    the match search window; the fit corrects the pose from real ink.
from collections import deque
q = deque(placed)
seen = set(placed)
while q:
    cur = q.popleft()
    for p in nbr_pairs.get(cur, []):
        other = p["nbr"] if p["owner"] == cur else p["owner"]
        if other in seen:
            continue
        Mu, tu = seed_pose(other, p, cur)
        placed[other] = {"m": Mu, "t": tu, "how": "prior-seed"}
        seen.add(other)
        q.append(other)
for uid in set(UNITS) - seen:
    placed[uid] = {"m": 2 * np.eye(2), "t": np.zeros(2), "how": "isolated"}
    flags[uid] = "no path from core"

# 2) iterate fit rounds: every non-fitted unit re-matches against all its
#    neighbours' CURRENT poses; accepted fits update the pose and firm the
#    neighbourhood for the next round.
fitted = set(NET["core_working"])
rounds = 0
while rounds < 6:
    rounds += 1
    progress = False
    for uid in sorted(set(UNITS) - fitted,
                      key=lambda u: -sum(1 for p in nbr_pairs.get(u, [])
                                         if (p["nbr"] if p["owner"] == u else p["owner"]) in fitted)):
        cors_by_nbr = {}
        nb_th, nb_sc = [], []
        for p in nbr_pairs.get(uid, []):
            other = p["nbr"] if p["owner"] == uid else p["owner"]
            M = placed[other]["m"]
            if other in fitted:
                nb_th.append(np.degrees(np.arctan2(M[1, 0], M[0, 0])))
                nb_sc.append(np.hypot(M[0, 0], M[1, 0]))
            Mu, tu = placed[uid]["m"], placed[uid]["t"]
            got = match_pts(uid, other, Mu, tu, search=380)
            if got:
                cors_by_nbr.setdefault(other, []).extend(got)
        if not cors_by_nbr:
            flags[uid] = "no matches to any neighbour"
            continue
        if not nb_th:
            nb_th, nb_sc = [0.0], [2.0]
        nth, nsc = float(np.median(nb_th)), float(np.median(nb_sc))
        fit, fitnote = fit_multi(cors_by_nbr)
        if not fit:
            flags[uid] = f"fit failed ({fitnote})"
            continue
        M, t, med, kept = fit
        th = float(np.degrees(np.arctan2(M[1, 0], M[0, 0])))
        sc = float(np.hypot(M[0, 0], M[1, 0]))
        if abs(sc - nsc) <= 0.05 * nsc and abs(th - nth) <= 1.8 and med <= 25 and kept >= 5:
            placed[uid] = {"m": M, "t": t,
                           "how": f"fit(n={kept},med={med:.1f},round={rounds})"}
            report[uid] = {"how": "fit", "n": kept, "med": round(med, 1),
                           "theta": round(th, 2), "scale": round(sc, 4),
                           "round": rounds}
            fitted.add(uid)
            flags.pop(uid, None)
            progress = True
            print(f"  {uid}: fit n={kept} med={med:.1f} th={th:+.2f} sc={sc:.3f} "
                  f"(round {rounds})", flush=True)
        else:
            # keep the fitted pose as an improved seed even when rejected:
            # it aims the next round's search better than the chained prior
            if med <= 60 and kept >= 4 and abs(sc - nsc) <= 0.15 * nsc:
                placed[uid] = {"m": M, "t": t, "how": "seed-improved"}
            flags[uid] = (f"fit rejected med={med:.1f} kept={kept} th={th:.2f} "
                          f"(nbr {nth:.2f}) sc={sc:.4f} (nbr {nsc:.4f})")
    if not progress:
        break
for uid in set(UNITS) - fitted:
    report[uid] = {"how": placed[uid]["how"], "flag": flags.get(uid, "")}
    print(f"  {uid}: UNFITTED ({placed[uid]['how']}: {flags.get(uid,'')})", flush=True)

n_fit = sum(1 for r in report.values() if r.get("how") == "fit")
print(f"placed {len(placed)}: {len(NET['core_working'])} core, {n_fit} fit, "
      f"{len(flags)} flagged")
aff = {uid: {"m": [[float(v) for v in row] for row in p["m"]],
             "t": [float(v) for v in p["t"]], "how": p["how"]}
       for uid, p in placed.items()}
json.dump({"convention": {"frame": NET["frame"],
                          "native": "WORKING scale (pct50; core x0.5 archival)"},
           "sheets": aff},
          open(os.path.join(ROOT, "out", "affine_city_1912.json"), "w"), indent=1)
json.dump({"report": report, "flags": flags},
          open(os.path.join(ROOT, "out", "ring_1912_report.json"), "w"), indent=1)
print("wrote affine_city_1912.json + ring_1912_report.json")
