#!/usr/bin/env python3
"""Similarity solve from shared-corridor controls: rotation and scale too.

    python3 tools/netsolve2.py --year 1912 [--apply]

netsolve.py solves a translation per sheet. That leaves what the seam
census saw in round 2: offsets that taper along a seam -- 15 ft at one end,
nothing at the other -- which is a rotation (or a residual scale) the
translation cannot touch.

A control is a LINE, not a point: the plate's street runs the length of the
shared band. Sampling it at both ends of the overlap makes the rotation
observable. With M = [[a, -b], [b, a]] the mosaic y of a native point (x, y)
is b x + a y + ty, linear in (a, b, ty); so "u's street and v's street are
the same line" at two sample points gives two linear equations in both
plates' (a, b, tx, ty). The core is frozen. A damping term keeps each free
plate's scale and rotation near what it has (its scale came from its own
blocks, tools/platescale.py), so a plate with few controls does not swing.

Transforms only; no pixel is touched.
"""
import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from reciplib import Recipe, px_per_ft           # noqa: E402
from netsolve import load_controls                # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LAM_AB = 1500.0     # px of residual equivalent per unit change of a or b
LAM_T = 1e-3        # keeps unconstrained sheets where they are
INSET = 0.08        # sample the line this far in from the overlap's ends


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", required=True, choices=["1912"])
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    from shapely.geometry import Polygon

    r = Recipe(int(a.year))
    ppf = px_per_ft(r)
    gj = json.load(open(os.path.join(r.dir, "sheets_city.geojson")))
    core = {str(f["properties"]["unit"]) for f in gj["features"]
            if f["properties"].get("tier") == "core"}
    ctl = load_controls(r)
    print(f"{len(ctl)} usable controls", flush=True)

    def foot(u):
        e = r.units[u]["extent"]
        M, t = r.sheet_matrix(u)
        return Polygon([tuple(M @ np.array(c, float) + t) for c in
                        ((e[0], e[1]), (e[2], e[1]), (e[2], e[3]), (e[0], e[3]))])
    feet = {u: foot(u) for u in r.units}
    MT = {u: r.sheet_matrix(u) for u in r.units}

    units = sorted(r.units, key=lambda k: int("".join(c for c in k if c.isdigit())))
    free = [u for u in units if u not in core]
    ix = {u: i for i, u in enumerate(free)}
    n = len(free)

    # re-read the native coordinates: load_controls only gives mosaic coords
    import re
    cdir = os.path.join(r.dir, "controls")
    rows, rhs, tags = [], [], []
    before = []
    for ua, ub, ax, ma, mb, corr, fn in ctl:
        d = json.load(open(os.path.join(cdir, os.path.basename(fn))))
        na, nb = float(d["a_native"]), float(d["b_native"])
        Ma, ta = MT[ua]
        Mb, tb = MT[ub]
        # sample positions along the shared band, in mosaic coordinates
        O = feet[ua].intersection(feet[ub])
        if O.is_empty:
            O = feet[ua].buffer(600).intersection(feet[ub].buffer(600))
        b = O.bounds
        k = 0 if ax == "x" else 1          # the controlled coordinate
        j = 1 - k                          # the coordinate along the line
        lo, hi = b[j], b[j + 2]
        samples = [lo + (hi - lo) * INSET, hi - (hi - lo) * INSET]
        for s in samples:
            # native point on each plate: controlled coordinate = the control,
            # along-coordinate such that the mosaic along-coordinate is s
            def native(M, t, nat_ctrl):
                Minv = np.linalg.inv(M)
                # solve for the along coordinate: start from the inverse of
                # the point (s, s) and fix the controlled one
                q = Minv @ (np.array([s, s]) - t)
                q[k] = nat_ctrl
                # iterate once so the along-coordinate lands on s
                p = M @ q + t
                q[j] += (s - p[j]) / M[j][j]
                return q
            qa = native(Ma, ta, na)
            qb = native(Mb, tb, nb)
            pa = Ma @ qa + ta
            pb = Mb @ qb + tb
            res = pa[k] - pb[k]
            row = np.zeros(4 * n)
            # d(mosaic k-coordinate)/d(a, b, tx, ty)
            def coeffs(q):
                x, y = q
                if k == 1:     # y = b x + a y + ty
                    return np.array([y, x, 0.0, 1.0])
                return np.array([x, -y, 1.0, 0.0])      # x = a x - b y + tx
            if ua in ix:
                row[4 * ix[ua]:4 * ix[ua] + 4] += coeffs(qa)
            if ub in ix:
                row[4 * ix[ub]:4 * ix[ub] + 4] -= coeffs(qb)
            if not row.any():
                continue
            if not (np.all(np.isfinite(row)) and np.isfinite(res)):
                print(f"  non-finite sample on {ua}|{ub} {ax} ({os.path.basename(fn)}): "
                      f"qa={qa} qb={qb} res={res}; skipped", flush=True)
                continue
            rows.append(row)
            rhs.append(-res)
            before.append(res)
            tags.append((f"{ua}|{ub}", ax, corr, os.path.basename(fn)))
    A = np.array(rows)
    bvec = np.array(rhs)
    # damping
    D = np.zeros((4 * n, 4 * n))
    for i in range(n):
        D[4 * i, 4 * i] = LAM_AB
        D[4 * i + 1, 4 * i + 1] = LAM_AB
        D[4 * i + 2, 4 * i + 2] = LAM_T
        D[4 * i + 3, 4 * i + 3] = LAM_T
    A2 = np.vstack([A, D])
    b2 = np.concatenate([bvec, np.zeros(4 * n)])
    sol, *_ = np.linalg.lstsq(A2, b2, rcond=None)
    after = A @ sol - bvec
    bf = np.abs(before) / ppf
    af = np.abs(after) / ppf
    print(f"line residuals at the band ends (ft): before median {np.median(bf):.1f}, "
          f"90th {np.percentile(bf, 90):.1f}, max {bf.max():.1f}")
    print(f"                                     after  median {np.median(af):.1f}, "
          f"90th {np.percentile(af, 90):.1f}, max {af.max():.1f}")
    worst = np.argsort(-np.abs(after))[:8]
    for i in worst:
        print(f"   {tags[i][0]:<9} {tags[i][1]}  {abs(after[i])/ppf:6.1f} ft  [{tags[i][2]}]")

    out = {"generated_by": "tools/netsolve2.py",
           "note": "similarity per sheet from shared-corridor line controls sampled at "
                   "both ends of the overlap; core frozen; damped toward the current "
                   "scale and rotation",
           "controls_used": len(rows) // 2,
           "residual_ft": {"before_median": float(np.median(bf)), "after_median": float(np.median(af)),
                           "after_max": float(af.max())},
           "sheets": {}}
    changes = []
    for u in units:
        M, t = MT[u]
        if u in ix:
            da, db, dtx, dty = sol[4 * ix[u]:4 * ix[u] + 4]
            M2 = M + np.array([[da, -db], [db, da]])
            t2 = t + np.array([dtx, dty])
            s1, s2 = np.hypot(M[0][0], M[1][0]), np.hypot(M2[0][0], M2[1][0])
            r1 = np.degrees(np.arctan2(M[1][0], M[0][0]))
            r2 = np.degrees(np.arctan2(M2[1][0], M2[0][0]))
            e = r.units[u]["extent"]
            c = np.array([(e[0] + e[2]) / 2, (e[1] + e[3]) / 2])
            move = float(np.linalg.norm((M2 @ c + t2) - (M @ c + t)) / ppf)
            changes.append((u, s2 / s1 - 1, r2 - r1, move))
            out["sheets"][u] = {"m": [list(map(float, M2[0])), list(map(float, M2[1]))],
                                "t": [float(t2[0]), float(t2[1])],
                                "scale_change": float(s2 / s1 - 1), "rotation_change_deg": float(r2 - r1),
                                "centre_move_ft": move, "source": "similarity-solved"}
        else:
            out["sheets"][u] = {"m": [list(map(float, M[0])), list(map(float, M[1]))],
                                "t": [float(t[0]), float(t[1])], "source": "frozen-core"}
    sc = np.array([abs(c[1]) for c in changes]) * 100
    rot = np.array([abs(c[2]) for c in changes])
    mv = np.array([c[3] for c in changes])
    print(f"\n{len(changes)} free sheets: |scale change| median {np.median(sc):.2f}% max {sc.max():.2f}%; "
          f"|rotation change| median {np.median(rot):.2f} deg max {rot.max():.2f}; "
          f"centre move median {np.median(mv):.1f} ft max {mv.max():.1f}")
    big = sorted(changes, key=lambda c: -abs(c[2]))[:6]
    print("largest rotations:", ", ".join(f"{u}:{dr:+.2f}deg" for u, ds, dr, m in big))
    big = sorted(changes, key=lambda c: -abs(c[1]))[:6]
    print("largest scale changes:", ", ".join(f"{u}:{ds*100:+.2f}%" for u, ds, dr, m in big))
    big = sorted(changes, key=lambda c: -c[3])[:6]
    print("largest moves:", ", ".join(f"{u}:{m:.0f}ft" for u, ds, dr, m in big))
    p = os.path.join(r.dir, "transforms_similarity.json")
    json.dump(out, open(p, "w"), indent=1)
    print(f"wrote {p}")
    if a.apply:
        tp = os.path.join(r.dir, "transforms_city.json")
        cur = json.load(open(tp))
        for u, s in out["sheets"].items():
            if s["source"] == "similarity-solved":
                keep = {k_: v_ for k_, v_ in cur["sheets"][u].items() if k_ not in ("m", "t")}
                cur["sheets"][u] = dict(keep, m=s["m"], t=s["t"], tier="control",
                                        how="shared-corridor lines, similarity solve")
        json.dump(cur, open(tp, "w"), indent=1)
        print(f"applied to {tp}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
