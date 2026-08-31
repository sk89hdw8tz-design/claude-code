#!/usr/bin/env python3
"""Prepare the evidence a registration agent needs to identify one pair's
shared corridor, the way recipe/controls/pair_*.json were made.

    python3 tools/paircrops.py --year 1912 --pair 75 76

Writes, under work/paircrops/<A>_<B>/:
  sheet_<A>.jpg, sheet_<B>.jpg   the seam edge of each sheet, downscaled,
                                 with every detected corridor drawn and
                                 numbered, and a native-pixel ruler
  task.json                      candidates, key-map coverage, and what the
                                 agent must return

Automation proposes the candidate lines; the agent decides which candidate on
each sheet is the SAME corridor, using the printed address runs — the step
that ordinal matching gets wrong when detection misses a line.
"""
import argparse
import glob
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from reciplib import Recipe                       # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def keymap(year):
    km = {}
    for f in glob.glob(os.path.join(REPO, "rebuild_1899", "out",
                                    f"keymap_{year}_*.json")):
        for e in json.load(open(f)).get("results", []):
            km[str(e["sheet"])] = e
    return km


def build(year, ua, ub, outdir=None):
    import cv2
    from shapely.geometry import Polygon
    r = Recipe(int(year))
    det = json.load(open(os.path.join(r.dir, "corridors.json")))
    km = keymap(year)
    own = dict(r.ownership())
    if ua not in own or ub not in own or ua not in det or ub not in det:
        return None
    pa, pb = Polygon(own[ua]), Polygon(own[ub])
    shared = pa.boundary.intersection(pb.boundary)
    if not shared.is_empty and shared.length > 200:
        x0, y0, x1, y1 = shared.bounds
        vertical = (y1 - y0) >= (x1 - x0)   # seam runs N-S => side by side
        ca = np.array([shared.centroid.x, shared.centroid.y])
    else:
        # sheets that share a corridor but whose cut regions do not touch —
        # the core block is like this, and those are the anchors to it
        ka = np.array([pa.centroid.x, pa.centroid.y])
        kb = np.array([pb.centroid.x, pb.centroid.y])
        vertical = abs(kb[0] - ka[0]) >= abs(kb[1] - ka[1])
        ca = (ka + kb) / 2.0
    axis = "avenue" if vertical else "street"
    outdir = outdir or os.path.join(REPO, "work", "paircrops", f"{ua}_{ub}")
    os.makedirs(outdir, exist_ok=True)

    info = {"pair": [ua, ub], "axis": axis,
            "seam_is": "vertical (sheets side by side)" if vertical
                       else "horizontal (sheets one above the other)",
            "keymap": {ua: km.get(ua, {}), ub: km.get(ub, {})},
            "candidates": {}}

    for uid in (ua, ub):
        d = det[uid]
        M, t = r.sheet_matrix(uid)
        lines = sorted(d["cols"] if vertical else d["rows"])
        # distance from the shared seam, in mosaic px, for ordering
        scored = []
        for v in lines:
            p = M @ (np.array([v, d["rows"][0]], float) if vertical
                     else np.array([d["cols"][0], v], float)) + t
            dist = abs((p[0] if vertical else p[1]) - (ca[0] if vertical else ca[1]))
            scored.append((dist, float(v), float(p[0] if vertical else p[1])))
        scored.sort()
        info["candidates"][uid] = [
            {"id": i + 1, "native": round(v, 1), "mosaic": round(m, 1),
             "dist_to_seam_px": round(dd, 1)}
            for i, (dd, v, m) in enumerate(scored)]

        img = cv2.imread(r.fetch(r.sheet_file(uid)), cv2.IMREAD_COLOR)
        H, W = img.shape[:2]
        # one near-native crop per candidate: address digits stay readable,
        # which a whole-sheet view does not allow
        for i, (dd, v, m) in enumerate(scored[:2]):
            p = int(round(v))
            if vertical:
                a0, a1 = max(0, p - 780), min(W, p + 780)
                b0, b1 = max(0, H // 2 - 1100), min(H, H // 2 + 1100)
            else:
                a0, a1 = max(0, W // 2 - 1100), min(W, W // 2 + 1100)
                b0, b1 = max(0, p - 780), min(H, p + 780)
            crop = img[b0:b1, a0:a1].copy()
            if vertical:
                cv2.line(crop, (p - a0, 0), (p - a0, crop.shape[0]), (0, 0, 255), 4)
            else:
                cv2.line(crop, (0, p - b0), (crop.shape[1], p - b0), (0, 0, 255), 4)
            # native-pixel ruler: detection can miss a corridor at the sheet
            # edge, so the agent must be able to report a coordinate we did
            # not propose
            for g in range(int(np.ceil(a0 / 100.0)) * 100, a1, 100):
                gx = g - a0
                big = (g % 500 == 0)
                cv2.line(crop, (gx, 0), (gx, 34 if big else 18), (0, 150, 0), 3)
                if big:
                    cv2.putText(crop, str(g), (gx + 4, 66),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.85, (0, 150, 0), 2)
            for g in range(int(np.ceil(b0 / 100.0)) * 100, b1, 100):
                gy = g - b0
                big = (g % 500 == 0)
                cv2.line(crop, (0, gy), (34 if big else 18, gy), (0, 150, 0), 3)
                if big:
                    cv2.putText(crop, str(g), (40, gy + 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.85, (0, 150, 0), 2)
            cv2.putText(crop, f"sheet {uid}  cand #{i+1} at native "
                        f"{'x' if vertical else 'y'}={p}  (green ruler = native px)",
                        (60, 100), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (200, 0, 0), 3)
            ch, cw = crop.shape[:2]
            sc = min(1.0, 1500.0 / max(ch, cw))
            cv2.imwrite(os.path.join(outdir, f"sheet_{uid}_cand{i+1}.jpg"),
                        cv2.resize(crop, (int(cw * sc), int(ch * sc))),
                        [cv2.IMWRITE_JPEG_QUALITY, 92])

    info["return"] = {
        "file": f"outputs/{year}/recipe/controls/pair_{ua}_{ub}.json",
        "schema": {"pair": [int(ua) if ua.isdigit() else ua,
                            int(ub) if ub.isdigit() else ub],
                   "axis": axis,
                   "observer": "<your agent id>",
                   "method": "candidate lines proposed by corridor detection; "
                             "identity decided from printed address runs",
                   "a_native": "<native px of the chosen line on sheet A>",
                   "b_native": "<native px of the chosen line on sheet B>",
                   "corridor": "<e.g. 'Ave F (Church)'>",
                   "why_not_one_block_off": "<address-run evidence>",
                   "status": "ACCEPTED | UNRESOLVED"}}
    json.dump(info, open(os.path.join(outdir, "task.json"), "w"), indent=1)
    return outdir


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", required=True, choices=["1912", "1899"])
    ap.add_argument("--pair", nargs=2)
    ap.add_argument("--all", action="store_true")
    a = ap.parse_args()
    if a.pair:
        d = build(a.year, a.pair[0], a.pair[1])
        print(d or "no shared boundary")
        return 0
    from shapely.geometry import Polygon
    r = Recipe(int(a.year))
    own = [(u, Polygon(p)) for u, p in r.ownership()]
    n = 0
    for i in range(len(own)):
        for j in range(i + 1, len(own)):
            sh = own[i][1].boundary.intersection(own[j][1].boundary)
            if own[i][1].intersects(own[j][1]) and not sh.is_empty and sh.length > 200:
                if build(a.year, own[i][0], own[j][0]):
                    n += 1
    print(f"prepared {n} pairs")
    return 0


if __name__ == "__main__":
    sys.exit(main())
