#!/usr/bin/env python3
"""City-wide seam cuts + ownership for 1899 (generalizes cuts_1899.py).

Reads out/city_network.json (units, extents, pairs) and
out/affine_city_1899.json; emits out/cuts_city.json + out/masks_city.json
in the recipe's masks layout. Same method as downtown: min-ink DP path in
the both-printed overlap band, ownership = extent quad split by extended
cuts (unit-centre side kept), leftovers reassigned by priority, and the
compositors' disclosed fallback covers residual slivers.
"""
import json
import os
import sys

import cv2
import numpy as np
from shapely.geometry import LineString, Polygon, Point
from shapely.ops import split as shp_split, unary_union

ROOT = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(ROOT)
os.chdir(REPO)

NET = json.load(open(os.path.join(ROOT, "out", "city_network.json")))
AFF = json.load(open(os.path.join(ROOT, "out", "affine_city_1899.json")))["sheets"]

_img = {}
def unit_gray(uid):
    f = NET["units"][uid]["file"]
    if f not in _img:
        _img[f] = cv2.imread(f"work/sheets/1899/Galveston_1899_sheet_{f:02d}.jpg", 0)
        if len(_img) > 10:
            _img.pop(next(iter(_img)))
    return _img[f]

def M_t(uid):
    a = AFF[uid]
    return np.array(a["m"], float), np.array(a["t"], float)

def quad(uid):
    x0, y0, x1, y1 = NET["units"][uid]["extent"]
    M, t = M_t(uid)
    return Polygon([(M @ np.array(p, float) + t)
                    for p in ((x0, y0), (x1, y0), (x1, y1), (x0, y1))])

def cut_pair(ctx, scale=2):
    a, b = ctx["owner"], ctx["nbr"]
    qa, qb = quad(a), quad(b)
    ov = qa.intersection(qb)
    if ov.is_empty or ov.area < 1000:
        return None
    x0, y0, x1, y1 = ov.bounds
    horiz = ctx["axis"] == "h"
    W = int((x1 - x0) / scale) + 1
    H = int((y1 - y0) / scale) + 1
    if W < 4 or H < 4:
        return None
    def warp_ink(uid):
        g = unit_gray(uid)
        M, t = M_t(uid)
        A = np.hstack([M / scale, ((t - np.array([x0, y0])) / scale).reshape(2, 1)])
        w = cv2.warpAffine(g, A, (W, H), flags=cv2.INTER_AREA, borderValue=255)
        return cv2.GaussianBlur((255 - w).astype(np.float32), (0, 0), 2.5)
    cost = warp_ink(a) + warp_ink(b)
    mask = np.zeros((H, W), np.uint8)
    geom = ov if ov.geom_type == "Polygon" else max(ov.geoms, key=lambda g: g.area)
    ring = np.array([((px - x0) / scale, (py - y0) / scale)
                     for px, py in np.array(geom.exterior.coords)], np.int32)
    cv2.fillPoly(mask, [ring], 1)
    BIG = 1e7
    cost = np.where(mask == 1, cost, BIG)
    if not horiz:
        cost = cost.T
    Hc, Wc = cost.shape
    dp = cost.copy()
    back = np.zeros_like(dp, np.int8)
    for xx in range(1, Wc):
        prev = dp[:, xx - 1]
        stacked = np.vstack([np.roll(prev, 1), prev, np.roll(prev, -1)])
        stacked[0, 0] = BIG * 2
        stacked[2, -1] = BIG * 2
        choice = stacked.argmin(axis=0)
        dp[:, xx] += stacked[choice, np.arange(Hc)]
        back[:, xx] = choice - 1
    yend = int(dp[:, -1].argmin())
    path = [yend]
    for xx in range(Wc - 1, 0, -1):
        path.append(int(path[-1]) + int(back[path[-1], xx]))
    path = path[::-1]
    pts = []
    for xx, yy in enumerate(path):
        if horiz:
            pts.append((x0 + xx * scale, y0 + yy * scale))
        else:
            pts.append((x0 + yy * scale, y0 + xx * scale))
    return LineString(pts).simplify(1.5)

def extend_line(line, amt=40000):
    c = np.array(line.coords)
    d0 = c[0] - c[1]; d0 = d0 / (np.linalg.norm(d0) + 1e-9)
    d1 = c[-1] - c[-2]; d1 = d1 / (np.linalg.norm(d1) + 1e-9)
    return LineString(np.vstack([c[0] + d0 * amt, c, c[-1] + d1 * amt]))

def main():
    cuts = {}
    for k, ctx in enumerate(NET["pairs"]):
        key = f"{ctx['owner']}|{ctx['nbr']}"
        try:
            line = cut_pair(ctx)
        except Exception as e:
            line = None
            print(f"  {key}: cut error {e}")
        if line is None:
            cuts[key] = {"boundary": ctx["boundary"], "status": "no-overlap"}
        else:
            cuts[key] = {"boundary": ctx["boundary"], "axis": ctx["axis"],
                         "status": "ok",
                         "polyline_mosaic": [[round(x, 1), round(y, 1)]
                                             for x, y in line.coords]}
        if (k + 1) % 40 == 0:
            print(f"  cuts {k+1}/{len(NET['pairs'])}", flush=True)
    json.dump({"convention": "1899 city mosaic frame; min-ink DP cuts",
               "cuts": cuts},
              open(os.path.join(ROOT, "out", "cuts_city.json"), "w"))

    regions = []
    owned = {}
    quads = {uid: quad(uid) for uid in NET["units"]}
    for uid, q in quads.items():
        poly = q
        M, t = M_t(uid)
        u = NET["units"][uid]
        cx = (u["extent"][0] + u["extent"][2]) / 2
        cy = (u["extent"][1] + u["extent"][3]) / 2
        centre = M @ np.array([cx, cy]) + t
        for ctx in NET["pairs"]:
            if uid not in (ctx["owner"], ctx["nbr"]):
                continue
            rec = cuts.get(f"{ctx['owner']}|{ctx['nbr']}")
            if not rec or rec.get("status") != "ok":
                continue
            line = extend_line(LineString(rec["polyline_mosaic"]))
            try:
                pieces = shp_split(poly, line)
            except Exception:
                continue
            for p in pieces.geoms:
                if p.contains(Point(centre)):
                    poly = p
                    break
        if poly.geom_type == "Polygon":
            regions.append({"sheet": uid, "polygon_mosaic": {"exterior":
                [[round(x, 1), round(y, 1)] for x, y in np.array(poly.exterior.coords)]}})
            owned[uid] = poly
    total = unary_union([q.buffer(20) for q in quads.values()])
    covered = unary_union(list(owned.values()))
    leftover = total.difference(covered)
    pieces = list(getattr(leftover, "geoms", [leftover])) if not leftover.is_empty else []
    PRIORITY = sorted(quads, key=lambda u: NET["units"][u]["file"])
    n_extra = 0
    for piece in pieces:
        rest = piece
        for uid in PRIORITY:
            if rest.is_empty or rest.area < 500:
                break
            clip = quads[uid].buffer(35).intersection(rest)
            if clip.is_empty or clip.area < 500:
                continue
            for geom in getattr(clip, "geoms", [clip]):
                if geom.geom_type != "Polygon" or geom.area < 500:
                    continue
                regions.append({"sheet": uid, "reassigned_leftover": True,
                                "polygon_mosaic": {"exterior":
                                    [[round(x, 1), round(y, 1)]
                                     for x, y in np.array(geom.exterior.coords)]}})
                n_extra += 1
            rest = rest.difference(clip)
    json.dump({"convention": "1899 city mosaic frame; extent quads split by "
                             "extended cuts, centre side kept; leftovers "
                             "reassigned by file order",
               "regions": regions},
              open(os.path.join(ROOT, "out", "masks_city.json"), "w"))
    print(f"cuts {sum(1 for c in cuts.values() if c.get('status')=='ok')}/{len(cuts)} ok; "
          f"regions {len(regions)} ({n_extra} leftover reassignments)")

if __name__ == "__main__":
    main()
