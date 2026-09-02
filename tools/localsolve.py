#!/usr/bin/env python3
"""Re-solve the translation of a few named units from the accepted controls,
with every other unit held exactly where it is.

    python3 tools/localsolve.py --year 1912 --units 48 74 [--apply]

For a sheet found to be misplaced on plate evidence (HQ-27: 48 and 74 sat one
street row north of the row their outlot numbering and adjoining-sheet
numerals put them in), a city-wide re-solve would move every ring sheet a
little for the sake of two. This moves only the named units: each accepted
control between a free unit and a fixed one is an equation on x (avenue
control) or y (street control), read exactly as streetcut.load_cuts reads
it, and the free units' translations are the least-squares solution.
Rotation and scale are untouched. Transforms only; no pixel is altered.
"""
import argparse
import json
import os
import re
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from reciplib import Recipe, px_per_ft   # noqa: E402


def controls(r):
    out = []
    cdir = os.path.join(r.dir, "controls")
    for f in sorted(os.listdir(cdir)):
        m = re.match(r"pair_([0-9]+[a-z]?)_([0-9]+[a-z]?)(?:_[xy])?\.json$", f)
        if not m:
            continue
        d = json.load(open(os.path.join(cdir, f)))
        if "a_native" not in d or str(d.get("status", "")).upper() != "ACCEPTED":
            continue
        ua, ub = m.group(1).lstrip("0"), m.group(2).lstrip("0")
        if ua not in r.units or ub not in r.units:
            continue
        vert = str(d.get("axis", "")).lower().startswith("av")
        out.append((f, ua, ub, vert, float(d["a_native"]), float(d["b_native"])))
    return out


def point(r, u, nat, vert):
    e = r.units[u]["extent"]
    return (np.array([nat, (e[1] + e[3]) / 2.0]) if vert
            else np.array([(e[0] + e[2]) / 2.0, nat]))


def similarity(r, a, ppf):
    """Solve M=[[A,-B],[B,A]], t for the free units from line controls.

    A control is the plate's street/avenue line; the two plates' lines must
    coincide along the length of their shared band, so each control is
    sampled where the band starts and ends (through the current transforms),
    which makes rotation and scale observable (as tools/netsolve2.py does).
    Unknowns per free unit: (A, B, tx, ty); mosaic coordinate of a native
    point (x, y) is A x - B y + tx (x) or B x + A y + ty (y): linear.
    Damping keeps each free unit's (A, B) near its current values.
    """
    from shapely.geometry import Polygon
    free = {u: i for i, u in enumerate(a.units)}
    rows, rhs, tags = [], [], []

    def band_samples(ua, ub):
        fa, fb = r.footprint(ua), r.footprint(ub)
        O = fa.intersection(fb)
        if O.is_empty:
            return None
        return O.bounds

    for f, ua, ub, vert, na, nb in controls(r):
        if ua not in free and ub not in free:
            continue
        b = band_samples(ua, ub)
        if b is None:
            continue
        k = 0 if vert else 1
        # two sample points along the band on each plate's native line
        for frac in (0.15, 0.85):
            eq = np.zeros(4 * len(free)); c = 0.0
            for u, nat, sign in ((ua, na, 1.0), (ub, nb, -1.0)):
                M, t = r.sheet_matrix(u)
                Minv = np.linalg.inv(M)
                # the along-band mosaic coordinate at this fraction, taken back to native
                if vert:
                    ym = b[1] + frac * (b[3] - b[1])
                    # native point on the line x=nat whose mosaic y is ym
                    p_nat = np.array([nat, (Minv @ (np.array([0.0, ym]) - t))[1]])
                    p_nat[1] = ((ym - t[1]) - M[1, 0] * nat) / M[1, 1]
                else:
                    xm = b[0] + frac * (b[2] - b[0])
                    p_nat = np.array([((xm - t[0]) + M[0, 1] * 0) / M[0, 0], nat])
                    p_nat[0] = ((xm - t[0]) - M[0, 1] * nat) / M[0, 0]
                x, y = p_nat
                if u in free:
                    i = free[u]
                    if vert:   # mosaic x = A x - B y + tx
                        eq[4*i] += sign * x; eq[4*i+1] += -sign * y; eq[4*i+2] += sign
                    else:      # mosaic y = B x + A y + ty
                        eq[4*i] += sign * y; eq[4*i+1] += sign * x; eq[4*i+3] += sign
                else:
                    pm = M @ p_nat + t
                    c -= sign * pm[k]
            rows.append(eq); rhs.append(c); tags.append((f, ua, ub, "x" if vert else "y", frac))
    # damping toward the current A, B (weight in px per unit of A,B ~ plate half-size)
    W_DAMP = float(a.damp)
    for u, i in free.items():
        M, t = r.sheet_matrix(u)
        for j, val in ((0, M[0, 0]), (1, M[1, 0])):
            eq = np.zeros(4 * len(free)); eq[4*i+j] = W_DAMP
            rows.append(eq); rhs.append(W_DAMP * val); tags.append(("damp", u, "", "AB"[j], 0))
    A_, b_ = np.array(rows), np.array(rhs)
    sol, *_ = np.linalg.lstsq(A_, b_, rcond=None)
    res = A_ @ sol - b_
    ctl = [(tg, rr) for tg, rr in zip(tags, res) if tg[0] != "damp"]
    print(f"{len(ctl)} line samples touch {a.units}; residuals after (ft): median "
          f"{np.median(np.abs([rr for _, rr in ctl]))/ppf:.1f}, max {np.abs([rr for _, rr in ctl]).max()/ppf:.1f}")
    for (f, ua, ub, ax, frac), rr in sorted(ctl, key=lambda z: -abs(z[1]))[:12]:
        print(f"   {f:28s} {ax} @{frac:.2f} {rr/ppf:+7.1f} ft")
    doc = json.load(open(os.path.join(r.dir, "transforms_city.json")))
    for u, i in free.items():
        A, B, tx, ty = sol[4*i:4*i+4]
        M, t = r.sheet_matrix(u)
        s_old, s_new = float(np.hypot(M[0, 0], M[1, 0])), float(np.hypot(A, B))
        r_old, r_new = np.degrees(np.arctan2(M[1, 0], M[0, 0])), np.degrees(np.arctan2(B, A))
        c = np.array([1663.0, 1949.0])
        mv = ((np.array([[A, -B], [B, A]]) @ c + np.array([tx, ty])) - (M @ c + t)) / ppf
        print(f"unit {u}: scale {s_old:.4f} -> {s_new:.4f} ({(s_new/s_old-1)*100:+.2f}%), "
              f"rotation {r_old:+.3f} -> {r_new:+.3f} deg, centre moves ({mv[0]:+.0f}, {mv[1]:+.0f}) ft")
        if a.apply:
            doc["sheets"][u]["m"] = [[float(A), float(-B)], [float(B), float(A)]]
            doc["sheets"][u]["t"] = [float(tx), float(ty)]
            doc["sheets"][u]["scale"] = s_new; doc["sheets"][u]["theta_deg"] = float(r_new)
            doc["sheets"][u]["how"] = (doc["sheets"][u].get("how", "") +
                                       "; similarity re-solved locally from line controls (tools/localsolve.py)")
    if a.apply:
        json.dump(doc, open(os.path.join(r.dir, "transforms_city.json"), "w"), indent=1)
        print("applied to transforms_city.json")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", required=True, choices=["1912"])
    ap.add_argument("--units", nargs="+", required=True)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--damp", type=float, default=3000.0,
                    help="similarity: weight holding (A,B) at their current values (px per unit)")
    ap.add_argument("--similarity", action="store_true",
                    help="solve rotation and scale too, from the controls as lines")
    a = ap.parse_args()
    r = Recipe(int(a.year))
    ppf = px_per_ft(r)
    if a.similarity:
        return similarity(r, a, ppf)
    free = {u: i for i, u in enumerate(a.units)}
    rows, rhs, tags = [], [], []
    for f, ua, ub, vert, na, nb in controls(r):
        if ua not in free and ub not in free:
            continue
        k = 0 if vert else 1
        Ma, ta = r.sheet_matrix(ua)
        Mb, tb = r.sheet_matrix(ub)
        pa = (Ma @ point(r, ua, na, vert))[k]
        pb = (Mb @ point(r, ub, nb, vert))[k]
        # (pa + ta[k]) - (pb + tb[k]) = 0 ; unknown t for free units, known for fixed
        row = np.zeros(2 * len(free))
        c = pb - pa
        if ua in free:
            row[2 * free[ua] + k] += 1
        else:
            c -= ta[k]
        if ub in free:
            row[2 * free[ub] + k] -= 1
        else:
            c += tb[k]
        rows.append(row); rhs.append(c); tags.append((f, ua, ub, "x" if vert else "y"))
    A, b = np.array(rows), np.array(rhs)
    sol, *_ = np.linalg.lstsq(A, b, rcond=None)
    res = A @ sol - b
    print(f"{len(rows)} controls touch {a.units}; residuals after (ft): "
          f"median {np.median(np.abs(res))/ppf:.1f}, max {np.abs(res).max()/ppf:.1f}")
    for (f, ua, ub, ax), rr in sorted(zip(tags, res), key=lambda z: -abs(z[1])):
        print(f"   {f:28s} {ax} {rr/ppf:+7.1f} ft")
    doc = json.load(open(os.path.join(r.dir, "transforms_city.json")))
    for u, i in free.items():
        old = np.array(doc["sheets"][u]["t"], float)
        new = sol[2 * i:2 * i + 2]
        print(f"unit {u}: t {old.round(1).tolist()} -> {new.round(1).tolist()}  "
              f"move ({(new[0]-old[0])/ppf:+.0f}, {(new[1]-old[1])/ppf:+.0f}) ft")
        if a.apply:
            doc["sheets"][u]["t"] = [float(new[0]), float(new[1])]
            doc["sheets"][u]["how"] = (doc["sheets"][u].get("how", "") +
                                       "; translation re-solved locally (tools/localsolve.py)")
    if a.apply:
        json.dump(doc, open(os.path.join(r.dir, "transforms_city.json"), "w"), indent=1)
        print("applied to transforms_city.json")


if __name__ == "__main__":
    main()
