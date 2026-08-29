#!/usr/bin/env python3
"""Landmark gate for the full-affine build.

Same check as SEED_1899/tools/landmark_check.py — map each ground-truth
landmark through BOTH sheets' transforms, the disagreement IS the
registration error — extended to a full 2x2 affine, which the seed tool's
axis-separable knots cannot represent (disclosed deviation; the seed tool is
also run on a knots approximation as a cross-check).

Pass/fail per THE BAR: surveyed-vs-surveyed landmarks <= 8 px, none > 12 px.
Features flagged schematic (wharf sheets' outline redraws of downtown
blocks) are reported but excluded, per the prompt's asterisk.
"""
import json
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(ROOT)
SEED = os.path.join(REPO, "work", "seed_pipeline", "SEED_1899")

def main(aff_path, max_ok=8.0, hard=12.0):
    lm = json.load(open(os.path.join(SEED, "landmarks.json")))
    aff = json.load(open(aff_path))["sheets"]
    rows = []
    for f in lm["features"]:
        a, b = f["sheet_a"], f["sheet_b"]
        Ta, Tb = aff[a], aff[b]
        ga = np.array(Ta["m"]) @ np.array(f["a_xy"]) + np.array(Ta["t"])
        gb = np.array(Tb["m"]) @ np.array(f["b_xy"]) + np.array(Tb["t"])
        d = gb - ga
        rows.append({"id": f["id"], "pair": f"{a}|{b}",
                     "schematic": bool(f.get("schematic")),
                     "dx": round(float(d[0]), 1), "dy": round(float(d[1]), 1),
                     "step": round(float(np.hypot(*d)), 1)})
    surveyed = [r for r in rows if not r["schematic"]]
    schematic = [r for r in rows if r["schematic"]]
    rows.sort(key=lambda r: -r["step"])
    for r in rows:
        tag = " (schematic)" if r["schematic"] else ""
        flag = "  <== OVER" if not r["schematic"] and r["step"] > max_ok else ""
        print(f"{r['id'][:28]:28} {r['pair']:8} {r['dx']:8.1f} {r['dy']:8.1f} "
              f"{r['step']:8.1f}{tag}{flag}")
    st = sorted(r["step"] for r in surveyed)
    over = sum(1 for s in st if s > max_ok)
    print(f"\nsurveyed landmarks: {len(st)}  median {st[len(st)//2]:.1f} px  "
          f"max {st[-1]:.1f} px  over {max_ok:g}: {over}  over {hard:g}: "
          f"{sum(1 for s in st if s > hard)}")
    if schematic:
        ss = sorted(r["step"] for r in schematic)
        print(f"schematic (reported, excluded): {len(ss)}  median "
              f"{ss[len(ss)//2]:.1f} px  max {ss[-1]:.1f} px")
    by_pair = {}
    for r in surveyed:
        by_pair.setdefault(r["pair"], []).append(r)
    print("\nper pair (surveyed only):")
    for p, rs in sorted(by_pair.items()):
        mdx = np.mean([r["dx"] for r in rs]); mdy = np.mean([r["dy"] for r in rs])
        mx = max(r["step"] for r in rs)
        print(f"  {p:8} n={len(rs)}  mean dx={mdx:+7.1f} dy={mdy:+7.1f}  max={mx:6.1f}")
    ok = st[-1] <= hard and over == 0
    print("\nGATE:", "PASS" if ok else "FAIL")
    json.dump({"rows": rows,
               "surveyed": {"n": len(st), "median": st[len(st)//2],
                            "max": st[-1], "over_8": over},
               "pass": ok},
              open(os.path.join(ROOT, "out", "gate_report.json"), "w"), indent=1)
    return 0 if ok else 1

if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else
                  os.path.join(ROOT, "out", "affine_1899.json")))
