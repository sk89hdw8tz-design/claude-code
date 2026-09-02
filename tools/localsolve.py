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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", required=True, choices=["1912"])
    ap.add_argument("--units", nargs="+", required=True)
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    r = Recipe(int(a.year))
    ppf = px_per_ft(r)
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
