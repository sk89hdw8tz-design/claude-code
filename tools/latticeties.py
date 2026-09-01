#!/usr/bin/env python3
"""Street and avenue ties read off the plates' own lattices.

    python3 tools/latticeties.py --year 1912 [--write]

Every adjacent pair of sheets shares a corridor along the seam. The observer
programme measured it for 133 pairs; the rest were placed by the old tie
network and never had the constraint. tools/faces.py now reads every
corridor on every plate (validated against the observers' 378 coordinates:
median 4 px), so for each uncontrolled pair the shared corridor's native
position on both plates is known, and that is exactly what a control is.

Identity is settled by the placement the pair already has: the two plates'
readings of the shared corridor must fall within IDENT_FRACTION of a block
of each other under the current transforms. The current placement is good to
a few tens of feet on every controlled pair, and a whole block is 350-400 ft,
so nothing here can pick the wrong street; a pair that is further apart than
that is reported and left alone. Both lattices must be clean (not flagged
weak) and the corridor must be one whose faces were actually measured on
each plate, not the extrapolated one beyond the edge.

Writes control files in the existing schema, with observer "lattice", so
tools/netsolve.py and tools/streetcut.py use them like any other. Dry-run by
default.
"""
import argparse
import json
import os
import re
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from reciplib import Recipe, px_per_ft          # noqa: E402
from faces import lattice_all                    # noqa: E402
from streetcut import load_cuts, BAND_FRACTION   # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IDENT_FRACTION = 0.45     # of a block pitch; beyond this the pair is left alone
NEAR_PX = 500             # non-overlapping plates this close still share a corridor
MIN_OVERLAP = 2500.0


def ordinal(n):
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", required=True, choices=["1912"])
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()

    from shapely.geometry import Polygon
    r = Recipe(int(a.year))
    ppf = px_per_ft(r)
    lat = lattice_all(r)
    cuts = load_cuts(r)
    try:
        from paircrops import keymap
        km = keymap(a.year, warn=False)
    except Exception:
        km = {}

    def foot(u):
        e = r.units[u]["extent"]
        M, t = r.sheet_matrix(u)
        return Polygon([tuple(M @ np.array(c, float) + t) for c in
                        ((e[0], e[1]), (e[2], e[1]), (e[2], e[3]), (e[0], e[3]))])
    feet = {u: foot(u) for u in r.units}
    cen = {u: np.array([feet[u].centroid.x, feet[u].centroid.y]) for u in feet}
    units = sorted(feet, key=lambda k: int("".join(c for c in k if c.isdigit())))
    cdir = os.path.join(r.dir, "controls")
    existing = set(os.listdir(cdir))
    gj = json.load(open(os.path.join(r.dir, "sheets_city.geojson")))
    core = {str(f["properties"]["unit"]) for f in gj["features"]
            if f["properties"].get("tier") == "core"}

    def measured(u, axis, mid):
        """(native centre, mosaic coord) of u's measured corridor nearest mid."""
        L = (lat.get(u) or {}).get(axis)
        if not L or L.get("weak"):
            return None
        M, t = r.sheet_matrix(u)
        nat = np.linalg.inv(M) @ (np.array(mid, float) - t)
        k = 0 if axis == "x" else 1
        best = None
        for fa, fb in L["faces"]:
            c = (fa + fb) / 2.0
            q = nat.copy()
            q[k] = c
            p = M @ q + t
            if best is None or abs(p[k] - mid[k]) < abs(best[1] - mid[k]):
                best = (c, float(p[k]), fb - fa)
        return best

    def name(u, v, axis):
        """Shared corridor from the key maps, when both plates are listed."""
        try:
            if axis == "y":
                su = sorted(int(re.sub(r"[^0-9]", "", str(x))) for x in km[u]["streets"])
                sv = sorted(int(re.sub(r"[^0-9]", "", str(x))) for x in km[v]["streets"])
                sh = set(su) & set(sv)
                return f"{ordinal(sorted(sh)[0])} St" if len(sh) == 1 else None
            au = {Recipe.avenue_slot(str(x)) for x in km[u]["avenues"]}
            av = {Recipe.avenue_slot(str(x)) for x in km[v]["avenues"]}
            sh = au & av
            if len(sh) == 1:
                from crossrow import AVNAME
                return f"Ave {AVNAME.get(sorted(sh)[0], sorted(sh)[0])}"
        except Exception:
            return None
        return None

    ties, skipped = [], []
    for i, u in enumerate(units):
        for v in units[i + 1:]:
            d = cen[v] - cen[u]
            axis = "x" if abs(d[0]) >= abs(d[1]) else "y"
            if feet[u].intersects(feet[v]):
                O = feet[u].intersection(feet[v])
                if O.area < MIN_OVERLAP:
                    continue
                b = O.bounds
            else:
                # plates that each draw only their half of the shared
                # corridor do not overlap at all; if their paper edges are
                # within a roadway of each other they still share it, and
                # the lattice reads it on both (61|62, 69|70, 76|77 left
                # 14-19 ft white strips down the avenue for want of this)
                if feet[u].distance(feet[v]) > NEAR_PX:
                    continue
                bu, bv = feet[u].bounds, feet[v].bounds
                b = (max(bu[0], bv[0]) if axis != "x" else min(bu[2], bv[2]),
                     max(bu[1], bv[1]) if axis != "y" else min(bu[3], bv[3]),
                     min(bu[2], bv[2]) if axis != "x" else max(bu[0], bv[0]),
                     min(bu[3], bv[3]) if axis != "y" else max(bu[1], bv[1]))
            span = (b[3] - b[1]) if axis == "x" else (b[2] - b[0])
            across = min(feet[u].bounds[3] - feet[u].bounds[1],
                         feet[v].bounds[3] - feet[v].bounds[1]) if axis == "x" else \
                     min(feet[u].bounds[2] - feet[u].bounds[0],
                         feet[v].bounds[2] - feet[v].bounds[0])
            if span < BAND_FRACTION * across:
                continue                                   # corner contact
            key = (u, v) if (u, v) in cuts else ((v, u) if (v, u) in cuts else None)
            if key and cuts[key].get(axis):
                continue                                   # observer control exists
            if u in core and v in core:
                continue                                   # the master's own seam
            mid = np.array([(b[0] + b[2]) / 2, (b[1] + b[3]) / 2])
            mu, mv = measured(u, axis, mid), measured(v, axis, mid)
            if mu is None or mv is None:
                skipped.append((u, v, axis, "no clean lattice on "
                                + ("both" if mu is None and mv is None else (u if mu is None else v))))
                continue
            pitch = (lat[u][axis]["pitch"] + lat[v][axis]["pitch"]) / 2.0 * 2.0   # mosaic px
            gap = abs(mu[1] - mv[1])
            if gap > IDENT_FRACTION * pitch:
                skipped.append((u, v, axis, f"plates {gap/ppf:.0f} ft apart under the current "
                                f"placement; identity not safe"))
                continue
            ties.append({"pair": [int(u), int(v)],
                         "axis": "avenue" if axis == "x" else "street",
                         "observer": "lattice (tools/faces.py)",
                         "method": ("corridor centre = midpoint of the two block faces read "
                                    "off the plate's own street chain; identity from the "
                                    "current placement (the two readings are within "
                                    f"{gap/ppf:.0f} ft, a block is {pitch/ppf:.0f} ft) and "
                                    "the key maps' coverage"),
                         "a_native": round(mu[0], 1), "b_native": round(mv[0], 1),
                         "corridor": name(u, v, axis) or "?",
                         "roadway_px": [int(mu[2]), int(mv[2])],
                         "disagreement_before_ft": round(gap / ppf, 1),
                         "status": "ACCEPTED"})
    print(f"{len(ties)} lattice ties for uncontrolled seams; {len(skipped)} pairs left alone")
    gaps = [t["disagreement_before_ft"] for t in ties]
    if gaps:
        print(f"current placement disagrees with the plates by median {np.median(gaps):.0f} ft, "
              f"90th {np.percentile(gaps, 90):.0f}, max {max(gaps):.0f}")
    for t in ties:
        print(f"  {t['pair'][0]}|{t['pair'][1]} {t['axis']:<6} {t['corridor']:<12} "
              f"a={t['a_native']:7.1f} b={t['b_native']:7.1f}  road {t['roadway_px']}  "
              f"was {t['disagreement_before_ft']:.0f} ft apart")
    for u, v, axis, why in skipped:
        print(f"  skip {u}|{v} {axis}: {why}")
    if not a.write:
        print("dry run -- pass --write to create the control files")
        return 0
    n = 0
    for t in ties:
        u, v = t["pair"]
        base = f"pair_{u}_{v}"
        fn = base + ".json"
        if fn in existing:
            fn = base + ("_x" if t["axis"] == "avenue" else "_y") + ".json"
        if fn in existing:
            print(f"  not overwriting {fn}")
            continue
        json.dump(t, open(os.path.join(cdir, fn), "w"), indent=1)
        n += 1
    print(f"wrote {n} control files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
