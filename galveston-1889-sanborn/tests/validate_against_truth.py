#!/usr/bin/env python3
"""Absolute accuracy check of the synthetic run against known ground truth.

Residuals at tie points measure whether the sheets agree WITH EACH OTHER. They
cannot detect an error shared by every sheet -- a whole mosaic uniformly skewed
would show beautiful residuals. Only ground truth catches that, which is the
reason the synthetic fixture exists.

Method
    The fixture records the exact transform from each sheet's page pixels to
    ground truth. The pipeline independently solved its own transform from each
    sheet into the reconstruction plane. Compose the truth of the anchor sheet
    with each solved transform and you get, for every ground-truth intersection,
    where the reconstruction actually put it versus where it belongs.

    Reported in reconstruction-plane pixels, which at pixels_per_unit=1.0 are
    the anchor sheet's own scan pixels -- the same units as every other number
    in this project.

Run after `./run_all.sh synthetic`.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sanborn import geometry as G
from sanborn.config import paths, read_json

REGION_IDS = {"S1": ["S1_main", "S1_detached"]}


def main():
    p = paths()
    truth = json.loads((Path(p.root) / "tests" / "fixture" / "truth.json")
                       .read_text(encoding="utf-8"))
    tdoc = read_json(p.working / "transforms.json")
    solved = {k: np.asarray(v, float) for k, v in tdoc["transforms"].items()}
    anchor = tdoc["anchor_region"]

    # region_id -> true page->ground-truth transform
    true_H = {}
    for sh in truth["sheets"]:
        for i, reg in enumerate(sh["regions"]):
            ids = REGION_IDS.get(sh["name"])
            rid = ids[i] if ids and i < len(ids) else sh["name"]
            true_H[rid] = np.asarray(reg["H_page_to_gt"], float)

    if anchor not in true_H or anchor not in solved:
        print(f"anchor {anchor} not found in both truth and solution")
        return 2

    # The reconstruction plane is the anchor sheet's pixel grid, so ground truth
    # maps into it through the anchor's own true transform, inverted.
    gt_to_plane = np.linalg.inv(true_H[anchor])

    errs, per_region = [], {}
    for X in truth["intersections"]:
        gt = np.array([X["x"], X["y"]], float)
        ideal = G.apply(gt_to_plane, [gt])[0]
        for rid, Ht in true_H.items():
            if rid not in solved:
                continue                      # excluded region (S1_detached)
            page = G.apply(np.linalg.inv(Ht), [gt])[0]
            r = truth_rect(truth, rid)
            if r and not (r[0] + 20 <= page[0] <= r[2] - 20
                          and r[1] + 20 <= page[1] <= r[3] - 20):
                continue                      # not printed on this sheet
            got = G.apply(solved[rid], [page])[0]
            e = float(np.hypot(*(got - ideal)))
            errs.append(e)
            per_region.setdefault(rid, []).append(e)

    if not errs:
        print("no comparable points found")
        return 2

    a = np.array(errs)
    print("=" * 72)
    print("ABSOLUTE ACCURACY vs GROUND TRUTH (reconstruction-plane pixels)")
    print("=" * 72)
    print(f"model: {tdoc['kind']}   anchor: {anchor}   points compared: {a.size}")
    print(f"  median {np.median(a):7.2f}   mean {a.mean():7.2f}   "
          f"rms {np.sqrt((a**2).mean()):7.2f}")
    print(f"  p90    {np.percentile(a,90):7.2f}   p99 {np.percentile(a,99):7.2f}   "
          f"max {a.max():7.2f}")
    print()
    print("per region:")
    for rid in sorted(per_region):
        v = np.array(per_region[rid])
        print(f"  {rid:<14} n={v.size:3d}  median={np.median(v):6.2f}  "
              f"p90={np.percentile(v,90):6.2f}  max={v.max():6.2f}")

    ok = float(np.median(a)) <= 5.0
    print()
    print(f"VERDICT: median absolute error {np.median(a):.2f} px "
          f"{'MEETS' if ok else 'EXCEEDS'} the 5 px target")
    print("(This is error against truth, not merely sheet-to-sheet agreement.)")
    return 0 if ok else 1


def truth_rect(truth, rid):
    for sh in truth["sheets"]:
        for i, reg in enumerate(sh["regions"]):
            ids = REGION_IDS.get(sh["name"])
            this = ids[i] if ids and i < len(ids) else sh["name"]
            if this == rid:
                return reg["page_rect"]
    return None


if __name__ == "__main__":
    raise SystemExit(main())
