#!/usr/bin/env python3
"""Seam cuts for the 1899 rebuild: minimum-ink paths, then per-sheet
ownership polygons.

Per pair: rasterize the overlap band in the mosaic frame at 1/2 resolution,
cost = blurred ink of BOTH sheets (a path through paper on both), dynamic
programming along the boundary direction with the path clamped to the band
where both sheets carry printed map. Straight-line cuts are banned (SEED
prompt): the DP path bends around lettering.

Ownership: each sheet's warped page quad, split by each of its cuts, keeping
the piece on the sheet's side. Writes out/cuts_1899.json and
out/masks_1899.json (mosaic-frame polygons, 1912-style layout).
"""
import json
import os
import sys

import cv2
import numpy as np
from shapely.geometry import LineString, Polygon, Point
from shapely.ops import split as shp_split

ROOT = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(ROOT)
sys.path.insert(0, os.path.join(REPO, "tools"))
OUT = os.path.join(ROOT, "out")

AFF = json.load(open(os.path.join(OUT, "affine_1899.json")))["sheets"]
PAIR_CTX = json.load(open(os.path.join(REPO, "work", "seed_pipeline",
                                       "SEED_1899", "pair_context.json")))
SHEETS_DIR = os.path.join(REPO, "work", "sheets", "1899")
CAPTION_BAND = 155          # credit line below the paper, excluded everywhere

_img = {}
def sheet_gray(n):
    if n not in _img:
        g = cv2.imread(os.path.join(SHEETS_DIR, f"Galveston_1899_sheet_{n}.jpg"), 0)
        _img[n] = g
    return _img[n]

def M_t(s):
    a = AFF[s]
    return np.array(a["m"], float), np.array(a["t"], float)

def printed_extent(n):
    """(x0,y0,x1,y1) native: image minus scanner-white margins and caption."""
    g = sheet_gray(n)
    H, W = g.shape
    core = g[:H - CAPTION_BAND]
    colink = (core < 200).mean(axis=0)
    rowink = (core < 200).mean(axis=1)
    def first_last(v, thr=0.02):
        idx = np.where(v > thr)[0]
        return (int(idx[0]), int(idx[-1])) if len(idx) else (0, len(v) - 1)
    x0, x1 = first_last(colink)
    y0, y1 = first_last(rowink)
    return x0, y0, x1, min(y1, H - CAPTION_BAND)

def cut_pair(ctx, scale=2):
    a, b = ctx["owner"], ctx["nbr"]
    Ma, ta = M_t(a); Mb, tb = M_t(b)
    # overlap: intersection of both printed extents in mosaic frame
    def quad(n, M, t):
        x0, y0, x1, y1 = printed_extent(n)
        pts = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
        return Polygon([(M @ np.array(p) + t) for p in pts])
    qa, qb = quad(a, Ma, ta), quad(b, Mb, tb)
    ov = qa.intersection(qb)
    if ov.is_empty or ov.area < 1000:
        return None, (qa, qb)
    x0, y0, x1, y1 = ov.bounds
    # pad along the boundary direction so the cut spans the full shared edge
    horiz = ctx["axis"] == "h"          # boundary horizontal: path runs in x
    W = int((x1 - x0) / scale) + 1
    H = int((y1 - y0) / scale) + 1
    if W < 4 or H < 4:
        return None, (qa, qb)
    def warp_ink(n, M, t):
        g = sheet_gray(n)
        A = np.hstack([M / scale, ((t - np.array([x0, y0])) / scale).reshape(2, 1)])
        w = cv2.warpAffine(g, A, (W, H), flags=cv2.INTER_AREA, borderValue=255)
        ink = 255 - w
        return cv2.GaussianBlur(ink.astype(np.float32), (0, 0), 2.5)
    cost = warp_ink(a, Ma, ta) + warp_ink(b, Mb, tb)
    # mask outside the true overlap polygon: forbidden
    mask = np.zeros((H, W), np.uint8)
    ring = np.array([( (px - x0) / scale, (py - y0) / scale)
                     for px, py in np.array(ov.exterior.coords)], np.int32)
    cv2.fillPoly(mask, [ring], 1)
    BIG = 1e7
    cost = np.where(mask == 1, cost, BIG)
    if not horiz:
        cost = cost.T          # DP always marches along axis 1
    Hc, Wc = cost.shape
    dp = cost.copy()
    back = np.zeros_like(dp, np.int8)
    for x in range(1, Wc):
        prev = dp[:, x - 1]
        stacked = np.vstack([np.roll(prev, 1), prev, np.roll(prev, -1)])
        stacked[0, 0] = BIG * 2
        stacked[2, -1] = BIG * 2
        choice = stacked.argmin(axis=0)
        dp[:, x] += stacked[choice, np.arange(Hc)]
        back[:, x] = choice - 1
    yend = int(dp[:, -1].argmin())
    path = [yend]
    for x in range(Wc - 1, 0, -1):
        path.append(path[-1] + back[path[-1], x])
    path = path[::-1]
    pts = []
    for x, y in enumerate(path):
        if horiz:
            pts.append((x0 + x * scale, y0 + y * scale))
        else:
            pts.append((x0 + y * scale, y0 + x * scale))
    # simplify
    line = LineString(pts).simplify(1.5)
    return line, (qa, qb)

def extend_line(line, amt=30000):
    c = np.array(line.coords)
    d0 = c[0] - c[1]; d0 = d0 / (np.linalg.norm(d0) + 1e-9)
    d1 = c[-1] - c[-2]; d1 = d1 / (np.linalg.norm(d1) + 1e-9)
    return LineString(np.vstack([c[0] + d0 * amt, c, c[-1] + d1 * amt]))

def main():
    cuts = {}
    quads = {}
    for ctx in PAIR_CTX:
        key = f"{ctx['owner']}|{ctx['nbr']}"
        line, (qa, qb) = cut_pair(ctx)
        quads.setdefault(ctx["owner"], qa)
        quads.setdefault(ctx["nbr"], qb)
        if line is None:
            print(f"  {key}: NO OVERLAP (flagged)")
            cuts[key] = {"boundary": ctx["boundary"], "status": "no-overlap"}
            continue
        cuts[key] = {"boundary": ctx["boundary"], "axis": ctx["axis"],
                     "status": "ok",
                     "polyline_mosaic": [[round(x, 1), round(y, 1)]
                                         for x, y in line.coords]}
        print(f"  {key}: cut with {len(line.coords)} vertices")
    json.dump({"convention": "mosaic frame (1899 ground grid); cuts are "
                             "min-ink DP paths inside the both-printed band",
               "cuts": cuts},
              open(os.path.join(OUT, "cuts_1899.json"), "w"), indent=1)

    regions = []
    for ctx in PAIR_CTX:
        pass
    for sheet, q in quads.items():
        poly = q
        centre = np.array(AFF[sheet]["m"]) @ np.array([1700, 2050]) + np.array(AFF[sheet]["t"])
        for ctx in PAIR_CTX:
            key = f"{ctx['owner']}|{ctx['nbr']}"
            if sheet not in (ctx["owner"], ctx["nbr"]):
                continue
            rec = cuts.get(key)
            if not rec or rec.get("status") != "ok":
                continue
            line = extend_line(LineString(rec["polyline_mosaic"]))
            try:
                pieces = shp_split(poly, line)
            except Exception:
                continue
            got = None
            for p in pieces.geoms:
                if p.contains(Point(centre)):
                    got = p
                    break
            if got is not None:
                poly = got
        regions.append({"sheet": sheet,
                        "polygon_mosaic": {"exterior":
                            [[round(x, 1), round(y, 1)]
                             for x, y in np.array(poly.exterior.coords)]}})
    json.dump({"convention": "1899 mosaic frame; ownership = printed extent "
                             "split by extended cuts, sheet-centre side kept",
               "regions": regions},
              open(os.path.join(OUT, "masks_1899.json"), "w"), indent=1)
    print(f"wrote cuts_1899.json + masks_1899.json ({len(regions)} regions)")

if __name__ == "__main__":
    main()
