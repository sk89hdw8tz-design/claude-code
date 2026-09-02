#!/usr/bin/env python3
"""Set each ring plate's scale from its own block depths.

    python3 tools/platescale.py --year 1912 [--apply]

The city solve only ever moved sheets; their scales came from the tie
network and were never checked against the ground. The plates' own street
chains (tools/faces.py) measure every block face-to-face, and the frozen
core -- the accepted master -- says what a block is in mosaic pixels:
314.6 ft between street faces, 274.6 ft between avenue faces, each to
+-0.7% over 70 core blocks. A ring plate's scale is therefore its nominal
block depth over its measured one, on each axis it reads cleanly.

Before this, 49 of 81 ring plates were more than 1% off and the worst
(30, 37, 56, 79) 7-10%: across a 7,700 px plate that is 40-60 ft, and it
is why the graders saw steps that grow along a seam. Rotation is left
alone; the plate is rescaled about its own centre so the translation solve
that follows starts from where it was.
"""
import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from reciplib import Recipe, px_per_ft          # noqa: E402
from faces import lattice_all                    # noqa: E402

CORE = ["7", "8", "9", "10", "11", "12", "39", "40", "43", "44", "49", "50"]
MAX_CHANGE = 0.12       # a plate whose implied scale differs more than this is
                        # reported, not rescaled: its chain is reading something else


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", required=True, choices=["1912"])
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    r = Recipe(int(a.year))
    ppf = px_per_ft(r)
    lat = lattice_all(r)

    def scale_of(M):
        return float(np.hypot(M[0][0], M[1][0]))

    # nominal block depths from the core's own chains at the master's scale
    nominal = {}
    for ax in ("y", "x"):
        vals = []
        for u in CORE:
            L = lat[u].get(ax)
            if L and not L["weak"]:
                M, _ = r.sheet_matrix(u)
                vals += [b * scale_of(M) for b in L.get("blocks", [])]
        nominal[ax] = float(np.median(vals))
        print(f"{ax}: nominal block {nominal[ax]:.1f} mosaic px = {nominal[ax]/ppf:.1f} ft "
              f"(core, n={len(vals)}, 10-90%: {np.percentile(vals,10):.0f}-{np.percentile(vals,90):.0f})")

    out, changes = {}, []
    for u in sorted(r.units, key=int):
        M, t = r.sheet_matrix(u)
        s_old = scale_of(M)
        if u in CORE:
            continue
        est, wts = [], []
        for ax in ("y", "x"):
            L = lat[u].get(ax)
            if not L or L["weak"] or not L.get("blocks"):
                continue
            bl = np.array(L["blocks"], float)
            est.append(nominal[ax] / float(np.median(bl)))
            wts.append(len(bl))
        if not est:
            out[u] = {"scale_old": s_old, "scale_new": s_old, "how": "no clean chain; kept"}
            continue
        s_new = float(np.average(est, weights=wts))
        if abs(s_new / s_old - 1) > MAX_CHANGE:
            out[u] = {"scale_old": s_old, "scale_new": s_old, "implied": s_new,
                      "how": f"implied {s_new/s_old-1:+.1%}, beyond {MAX_CHANGE:.0%}; kept, check the plate"}
            continue
        out[u] = {"scale_old": s_old, "scale_new": s_new, "axes": est, "how": "block depth"}
        changes.append(s_new / s_old - 1)

    ch = np.abs(changes) * 100
    print(f"\n{len(changes)} ring plates rescaled: |change| median {np.median(ch):.2f}%, "
          f"90th {np.percentile(ch, 90):.2f}%, max {ch.max():.2f}%")
    big = sorted(((abs(v['scale_new']/v['scale_old']-1), u) for u, v in out.items()), reverse=True)[:10]
    print("largest:", ", ".join(f"{u}:{d*100:+.1f}%" for d, u in big))
    for u, v in out.items():
        if v["how"].startswith("implied") or v["how"].startswith("no clean"):
            print(f"  {u}: {v['how']}")

    p = os.path.join(r.dir, "plates", "plate_scales.json")
    json.dump({"tool": "tools/platescale.py", "nominal_block_mosaic_px": nominal,
               "units": out}, open(p, "w"), indent=1)
    print(f"wrote {p}")
    if not a.apply:
        print("dry run -- pass --apply to rescale transforms_city.json")
        return 0
    tp = os.path.join(r.dir, "transforms_city.json")
    doc = json.load(open(tp))
    n = 0
    for u, v in out.items():
        if v["scale_new"] == v["scale_old"]:
            continue
        M, t = r.sheet_matrix(u)
        e = r.units[u]["extent"]
        c = np.array([(e[0] + e[2]) / 2.0, (e[1] + e[3]) / 2.0])
        pc = M @ c + t                                   # keep the centre put
        k = v["scale_new"] / v["scale_old"]
        M2 = M * k
        t2 = pc - M2 @ c
        s = doc["sheets"][u]
        s["m"] = [[float(M2[0][0]), float(M2[0][1])], [float(M2[1][0]), float(M2[1][1])]]
        s["t"] = [float(t2[0]), float(t2[1])]
        s["scale_from"] = "plate block depths vs the core's (tools/platescale.py)"
        s["scale_was"] = v["scale_old"]
        n += 1
    json.dump(doc, open(tp, "w"), indent=1)
    print(f"rescaled {n} plates in {tp}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
