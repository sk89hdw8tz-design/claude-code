#!/usr/bin/env python3
"""Place a wharf plate (100 ft/in) from its Ave A frontage and cross streets.

    python3 tools/wharfplace.py --year 1912 --sheet 4 [--apply]

Sheets 2, 3, 4 and 6 are the wharf-front plates west and east of sheet 5,
drawn at 100 ft/in (half the block plates' scale) and never placed. They
share Ave A (Water) and every cross street with the block plates behind
them, which is exactly the frontage relationship the master solved for
sheet 5. Scale and rotation are taken from sheet 5's frozen joint solve
(the plates are one series, scanned alike; the pct:50 working copy doubles
the scale); the translation is the least-squares fit of:

  * Ave A centreline: the wharf plate's native x of the corridor centre,
    sampled at each shared street, must land on the block plate's Ave A
    line (its first x-chain in tools/faces.py) through that plate's transform;
  * each shared street: the wharf plate's native y of the street centre must
    land on the block plate's street line at the wharf plate's Ave A.

Correspondences are declared in WHARF below, read off the plates (labels
'AVE. A OR WATER', '29TH ST.' ... and the block-face pairs either side).
Transforms only; the seams are cut by streetcut.py from the control files
this writes (frontage seam 200 native px inside the block plate's neatline,
as for sheet 5).
"""
import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from reciplib import Recipe, px_per_ft   # noqa: E402

# wharf sheet -> {ave_a: native x of the Ave A centre, streets: {block plate: {street: native y}}}
WHARF = {
    "4": {"file": "pct50/sheet_0004.jpg", "ave_a": 3105, "rows": (800, 2300),
          "streets": {"13": {"29": 694, "30": 1270}, "15": {"30": 1270, "31": 1850, "32": 2428, "33": 3005}},
          # 15 chain 0 ([29,235]) is the scan/neatline border, not a corridor (15's extent x0=79);
          # 15's Ave A is chain 1 ([1044,1254], 210 px = 72 ft, "AVE. A OR WATER" + G.C.&S.F.R.R.
          # printed, 3100-block addresses 3102-3126 / 3101-3127). Pinning to chain 0 put sheet 4
          # 348 ft west: its "ELEVATOR (IRON CLAD)" is plate 13's Elevator "B" (same block 748,
          # same annexes), measured 347.9 ft west at 29th St. 13 stays None: all three of its
          # x-chains are paired one face too far west (lattice.json defect, note only).
          "ave_a_chain": {"13": None, "15": 1},
          "note": "piers 29-36, 28th-33rd St; abuts 13 (27th-30th) and 15 (30th-33rd) along Ave A; prints '5' at its top (sheet 5 above) and '3' at its bottom"},
    "6": {"file": "pct50/sheet_0006.jpg", "ave_a": 3219, "rows": (400, 3600),
          "streets": {"21": {"10": 291, "11": 866, "12": 1440}, "27": {"12": 1440, "13": 2013, "14": 2591, "15": 3166},
                      "33": {"15": 3166, "16": 3740}},
          "note": "piers 10-15, 10th-16th St; abuts 21 (9th-12th), 27 (12th-15th) and 33 (15th-18th) along Ave A; prints '5' at its bottom"},
    "3": {"file": "pct50/sheet_0003.jpg", "ave_a": 3130, "rows": (300, 3600),
          "streets": {"67": {"33": 235, "34": 807, "35": 1386, "36": 1966}, "75": {"36": 1966, "37": 2544, "38": 3117, "39": 3691}},
          "ave_a_chain": {"67": None, "75": None},  # 67 begins at Ave B and 75 at Ave C: neither draws Ave A
          "ave_a_from": ("4", 3005),               # Ave A's line continues from sheet 4 (its 33rd St, native y 3005)
          "street_from": ("4", 235.0, 3005.0),     # 33rd St is drawn on both: sheet 3 at native y 235, sheet 4 at 3005
          "note": "piers 33-39, 33rd-39th St; abuts 67 (33rd-36th) and 75 (36th-39th) along Ave A; prints '4' at its top and '2' at its bottom"},
}


def street_index(r, u, street):
    s0 = int(r.units[u]["streets"][0])
    return int(street) - s0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", required=True, choices=["1912"])
    ap.add_argument("--sheet", required=True, choices=sorted(WHARF))
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    r = Recipe(int(a.year))
    ppf = px_per_ft(r)
    spec = WHARF[a.sheet]
    L = json.load(open(os.path.join(r.dir, "plates", "lattice.json")))["units"]
    t5 = json.load(open(os.path.join(r.dir, "transforms_sheet5.json")))["panels"]["5A"]["raw"]
    s = 2.0 * float(np.hypot(t5["a"], t5["b"]))          # pct:50 copy: twice the archival scale
    th = np.arctan2(t5["b"], t5["a"])
    M = s * np.array([[np.cos(th), -np.sin(th)], [np.sin(th), np.cos(th)]])

    # unknowns: [k, tx, ty] where the mosaic point is k * R @ p_native + t and
    # R is the sheet-5 rotation. Scale was taken from the sheet-5 solve, but a
    # wharf plate's own cross streets can disagree with the block plates'
    # spacing by half a percent, which shows as a residual that grows along
    # the plate (sheet 3: +6.5 ft at 33rd to -11.9 at 39th). Eight street
    # equations constrain one scale comfortably.
    R = M / s
    rows, rhs, tags = [], [], []
    xa = float(spec["ave_a"])
    for bp, streets in spec["streets"].items():
        Mb, tb = r.sheet_matrix(bp)
        e = r.units[bp]["extent"]
        chain = spec.get("ave_a_chain", {}).get(bp, 0)
        ax_nat = None
        if chain is not None:
            fx = L[bp]["x"]["faces"][chain]
            ax_nat = (fx[0] + fx[1]) / 2.0                 # block plate's Ave A centre, native x
        for st, yw in streets.items():
            i = street_index(r, bp, st)
            fy = L[bp]["y"]["faces"]
            if not (0 <= i < len(fy)):
                print(f"  {bp}: street {st} has no chain (index {i}); skipped")
                continue
            sy_nat = (fy[i][0] + fy[i][1]) / 2.0
            # the block plate's street y at (its Ave A, or its extent centre)
            p = Mb @ np.array([ax_nat if ax_nat is not None else (e[0] + e[2]) / 2.0, sy_nat]) + tb
            q = R @ np.array([xa, float(yw)])               # unit-scale wharf point
            for k in ((0, 1) if ax_nat is not None else (1,)):
                row = np.zeros(3); row[0] = q[k]; row[1 + k] = 1.0
                rows.append(row); rhs.append(p[k]); tags.append((bp, st, "xy"[k]))
    if spec.get("street_from"):
        # the shared cross street of an already-placed wharf sheet: without it
        # each wharf plate follows only the block plates behind it, and where
        # those rows disagree the two wharf plates step at their common street
        # (3|4 stood 19 ft apart at 33rd St). One equation, weighted like the
        # others, so the step is shared rather than pushed onto one plate.
        wu, y_self, y_other = spec["street_from"]
        Mw, tw = r.sheet_matrix(wu)
        ew = r.units[wu]["extent"]
        p = Mw @ np.array([(ew[0] + ew[2]) / 2.0, float(y_other)]) + tw
        e_self = [40, 40, 3287, 3858]
        q = R @ np.array([(e_self[0] + e_self[2]) / 2.0, float(y_self)])
        row = np.zeros(3); row[0] = q[1]; row[2] = 1.0
        rows.append(row); rhs.append(p[1]); tags.append((wu, "33rd St", "y"))
    if spec.get("ave_a_from"):
        # Ave A continues from an already-placed wharf sheet: its native Ave A x at the shared street
        wu, yw_ref = spec["ave_a_from"]
        Mw, tw = r.sheet_matrix(wu)
        p = Mw @ np.array([float(WHARF[wu]["ave_a"]), float(yw_ref)]) + tw
        st0 = list(spec["streets"].values())[0]
        yw = float(list(st0.values())[0])
        q = R @ np.array([xa, yw])
        row = np.zeros(3); row[0] = q[0]; row[1] = 1.0
        rows.append(row); rhs.append(p[0]); tags.append((wu, "Ave A", "x"))
    A, b = np.array(rows), np.array(rhs)
    sol, *_ = np.linalg.lstsq(A, b, rcond=None)
    res = A @ sol - b
    k, t = float(sol[0]), sol[1:]
    M = k * R
    print(f"sheet {a.sheet}: scale {s:.4f} -> {k:.4f} ({(k/s-1)*100:+.2f}%), "
          f"rotation {np.degrees(th):+.3f} deg, t = {t.round(1).tolist()}; {len(rows)} equations, "
          f"residual median {np.median(np.abs(res))/ppf:.1f} ft, max {np.abs(res).max()/ppf:.1f} ft")
    for (bp, st, ax), rr in zip(tags, res):
        print(f"   plate {bp} {st}th St {ax}: {rr/ppf:+6.1f} ft")
    if not a.apply:
        return
    # units.json: a working copy of the pct50 scan, neatline extent filled by neatline.py later
    U = json.load(open(os.path.join(r.dir, "units.json")))
    W = json.load(open(os.path.join(r.dir, "working_sources.json")))
    T = json.load(open(os.path.join(r.dir, "transforms_city.json")))
    u = a.sheet
    prev = U["units"].get(u, {})
    U["units"][u] = {"file": int(u), "region": None,
                     # a re-run must not undo the neatline trim or the furniture boxes
                     "extent": prev.get("extent", [40, 40, 3287, 3858]), "streets": None,
                     "avenue_slots": None, "source_image": f"work/sheets/1912w/u{u}.jpg",
                     "scale_note": "wharf plate drawn at 100 ft/in; pct:50 working copy",
                     "seam_axis": {"default": "x", "5a": "y", "5b": "y", "2": "y", "3": "y", "4": "y", "6": "y"},
                     "note": spec["note"]}
    for key in ("extent_scan", "extent_fallback_sides", "furniture_native"):
        # NB: not "k" - that is the solved scale, used below for transforms_city
        if key in prev:
            U["units"][u][key] = prev[key]
    W["units"][u] = {"file": spec["file"], "op": "copy", "bytes": r.items_by_file[spec["file"]]["bytes"]}
    T["sheets"][u] = {"m": M.tolist(), "t": [float(t[0]), float(t[1])],
                      "how": "tools/wharfplace.py: rotation from the sheet-5 joint solve; scale and translation from Ave A and the shared cross streets against the block plates (and, for sheet 3, its 33rd St against sheet 4)",
                      "tier": "wharf-frontage", "theta_deg": float(np.degrees(th)), "scale": float(k)}
    json.dump(U, open(os.path.join(r.dir, "units.json"), "w"), indent=1)
    json.dump(W, open(os.path.join(r.dir, "working_sources.json"), "w"), indent=1)
    json.dump(T, open(os.path.join(r.dir, "transforms_city.json"), "w"), indent=1)
    # frontage seam controls, as for the sheet-5 panels: 200 native px inside the block plate's neatline
    for bp in spec["streets"]:
        Mb, tb = r.sheet_matrix(bp)
        e = r.units[bp]["extent"]
        xc = 200
        pm = Mb @ np.array([xc, (e[1] + e[3]) / 2.0]) + tb
        yc = (40 + 3858) / 2.0
        xn = (pm[0] - t[0] - M[0, 1] * yc) / M[0, 0]
        d = {"pair": [u, bp], "axis": "avenue",
             "corridor": f"wharf frontage: 200 native px inside sheet {bp}'s bay-side neatline",
             "observer": "session 018fqghgw6 (tools/wharfplace.py)",
             "a_native": round(float(xn), 1), "b_native": xc,
             "why_not_one_block_off": (f"Not a street. Sheet {bp} draws the wharf yard at 50 ft/in up to its bay-side neatline and keeps it; the 100 ft/in wharf plate supplies the piers and bay beyond. Same rule as the sheet-5 panels."),
             "status": "ACCEPTED"}
        json.dump(d, open(os.path.join(r.dir, "controls", f"pair_{u}_{bp}.json"), "w"), indent=1)
    print(f"applied: unit {u} added; controls written for {list(spec['streets'])}")


if __name__ == "__main__":
    main()
