#!/usr/bin/env python3
"""HQ-18: is every control on a roadway, or did one take the mid-block alley?

    python3 tools/widthcheck.py --year 1912

The corridor detector that proposed candidate lines to the observers finds
alleys (20 ft, dashed, mid-block) rather than avenues (70 ft, lettered). A
control that took the alley on one sheet and the avenue on the other would be
off by ~400 native px and invisible in the solve residuals, because netsolve
only ever sees the difference.

The plate's own periodic lattice (tools/faces.py) settles it without the
observer: a control coordinate on a roadway sits within a few px of a lattice
corridor centre; an alley sits half an avenue pitch away from every one.
Reports every accepted control's distance to the nearest corridor on each
sheet, and flags anything beyond TOL.
"""
import argparse
import glob
import json
import os
import re
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from reciplib import Recipe                      # noqa: E402
from faces import lattice_all                    # noqa: E402

TOL = 30.0          # native px (~10 ft); observer reads agree to 0-5 px


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", required=True, choices=["1912"])
    ap.add_argument("--json", default=None, help="write the table here")
    a = ap.parse_args()
    r = Recipe(int(a.year))
    lat = lattice_all(r)

    def nearest(u, axis, v):
        L = (lat.get(u) or {}).get(axis)
        if not L or not L["centres"]:
            return None, None
        c = min(L["centres"], key=lambda x: abs(x - v))
        return c, v - c

    rows, flagged, nolat = [], [], []
    for fn in sorted(glob.glob(os.path.join(r.dir, "controls", "pair_*.json"))):
        m = re.match(r"pair_([0-9]+[a-z]?)_([0-9]+[a-z]?)(?:_[xy])?\.json$",
                     os.path.basename(fn))
        d = json.load(open(fn))
        if not m or "a_native" not in d or str(d.get("status", "")).upper() != "ACCEPTED":
            continue
        ua, ub = m.group(1).lstrip("0"), m.group(2).lstrip("0")
        axis = "x" if str(d.get("axis", "")).lower().startswith("av") else "y"
        row = {"file": os.path.basename(fn), "pair": f"{ua}|{ub}", "axis": axis,
               "corridor": d.get("corridor")}
        ok = True
        for side, u, v in (("a", ua, float(d["a_native"])), ("b", ub, float(d["b_native"]))):
            c, off = nearest(u, axis, v)
            row[side] = {"unit": u, "native": v, "lattice": c,
                         "offset": None if off is None else round(off, 1)}
            if c is None:
                nolat.append((row["pair"], u))
            elif abs(off) > TOL:
                ok = False
        row["verdict"] = "on-corridor" if ok else "OFF-CORRIDOR"
        rows.append(row)
        if not ok:
            flagged.append(row)

    offs = [abs(rw[s]["offset"]) for rw in rows for s in ("a", "b")
            if rw[s]["offset"] is not None]
    print(f"{len(rows)} accepted controls, {len(offs)} coordinates checked "
          f"against the plates' own lattices")
    print(f"|offset| to nearest corridor centre: median {np.median(offs):.1f} px, "
          f"90th {np.percentile(offs, 90):.1f}, max {max(offs):.1f}")
    print(f"flagged beyond {TOL:.0f} px: {len(flagged)}")
    def fmt(side):
        if side["offset"] is None:
            return f"{side['unit']}: {side['native']:.0f} (no lattice)"
        return (f"{side['unit']}: {side['native']:.0f} vs {side['lattice']} "
                f"({side['offset']:+.0f})")
    for rw in flagged:
        print(f"  {rw['pair']:<8} {rw['axis']} {str(rw['corridor'])[:18]:<20} "
              f"{fmt(rw['a'])}   {fmt(rw['b'])}")
    if nolat:
        print(f"no lattice on: {sorted(set(nolat))}")
    if a.json:
        json.dump({"tool": "tools/widthcheck.py", "tolerance_px": TOL,
                   "controls": rows}, open(a.json, "w"), indent=1)
        print(f"wrote {a.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
