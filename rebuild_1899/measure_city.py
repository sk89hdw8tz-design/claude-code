#!/usr/bin/env python3
"""City-wide dense seam measurement over the 196-pair network.

Reuses measure.py's matcher (edge-NCC, two-pass with clustering, mutual
consistency) with the city network's units, estimated offsets, and an LRU
sheet cache. No landmarks exist outside downtown, so pass-1 clustering is
the only lock-selection; the rigid solve's loop consistency and the visual
sweep are the guards (suspect pairs get flagged for adjudication).

Writes out/city_measurements.json.
"""
import json
import os
import sys
from collections import Counter, OrderedDict

import cv2
import numpy as np

ROOT = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(ROOT)
sys.path.insert(0, ROOT)
import measure  # noqa: E402

NET = json.load(open(os.path.join(ROOT, "out", "city_network.json")))
UNITS = NET["units"]

# ---- monkeypatch measure for city units ----
_gray = OrderedDict()
def sheet_gray(uid):
    if uid in _gray:
        _gray.move_to_end(uid)
        return _gray[uid]
    f = UNITS[uid]["file"]
    g = cv2.imread(os.path.join(REPO, "work", "sheets", "1899",
                                f"Galveston_1899_sheet_{f:02d}.jpg"), 0)
    _gray[uid] = g
    if len(_gray) > 12:
        _gray.popitem(last=False)
    return g

_edge = OrderedDict()
def sheet_edges(uid):
    if uid in _edge:
        _edge.move_to_end(uid)
        return _edge[uid]
    e = measure.edges(sheet_gray(uid))
    _edge[uid] = e
    if len(_edge) > 12:
        _edge.popitem(last=False)
    return e

measure.sheet_gray = sheet_gray
measure.sheet_edges = sheet_edges
measure.OFFSETS = {uid: tuple(u["offsets"]) for uid, u in UNITS.items()}
import os as _os
if _os.environ.get("CITY_REFINE"):
    measure.TRANSFORMS = json.load(open(os.path.join(ROOT, "out", "affine_city_1899.json")))["sheets"]
    print("REFINE MODE: predictions through current city solve")
else:
    measure.TRANSFORMS = None
# wharf-family v-pairs get the wide band; everything else narrow
WHARF_UNITS = {"04", "05", "06", "07", "08"}
measure.WHARF_PAIRS = {(p["owner"], p["nbr"]) for p in NET["pairs"]
                       if p["owner"] in WHARF_UNITS and p["axis"] == "h"}
# measure.seam_samples consults ctx axis + WHARF_PAIRS + owner in 06/07/08
# for wide bands; the string check there covers city wharf pairs too.

def main():
    seams, matches = [], {}
    for k, ctx in enumerate(NET["pairs"]):
        ctx = dict(ctx, owner_native=int(round(ctx["owner_native"])),
                   nbr_native=int(round(ctx["nbr_native"])))
        key = f"{ctx['owner']}|{ctx['nbr']}"
        try:
            s, recs = measure.measure_pair(ctx, lm_bias=None)
        except Exception as e:
            s, recs = {"pair": [ctx["owner"], ctx["nbr"]], "error": str(e)}, []
            print("ERROR", key, e, flush=True)
        seams.append(s)
        matches[key] = recs
        print(f"[{k+1:3d}/{len(NET['pairs'])}] {key:9} {ctx['boundary']:<16} "
              f"n={len(recs):3d} {s.get('bias_source','')}"
              f"{' CONFLICT' if s.get('bias_conflict') else ''}", flush=True)
        if (k + 1) % 25 == 0:
            json.dump({"seam_summaries": seams, "seam_matches": matches,
                       "anchor_offsets": measure.OFFSETS},
                      open(os.path.join(ROOT, "out", "city_measurements.json"), "w"))
    json.dump({"seam_summaries": seams, "seam_matches": matches,
               "anchor_offsets": measure.OFFSETS},
              open(os.path.join(ROOT, "out", "city_measurements.json"), "w"))
    ns = [len(v) for v in matches.values()]
    print(f"done: {sum(ns)} matches; pairs with n>=6: "
          f"{sum(1 for n in ns if n >= 6)}/{len(ns)}; zero: {sum(1 for n in ns if n == 0)}")

if __name__ == "__main__":
    main()
