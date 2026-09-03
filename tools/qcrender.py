#!/usr/bin/env python3
"""Render a mosaic window from the recipe for QC, with optional unit labels.

    python3 tools/qcrender.py --year 1912 --rect X0 Y0 X1 Y1 --downsample 4 --out w.jpg [--labels]
    python3 tools/qcrender.py --year 1912 --around 57 58 --pad 1500 --out seam.jpg

Same compositing as tools/render.py (ownership polygons, single writer), but
it writes a JPEG, can centre on a set of units, and can stamp each unit's id
at its region centroid so a reviewer can tell which plate owns what. Not a
deliverable; review aid only.
"""
import argparse
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from reciplib import Recipe  # noqa: E402


def render(r, x0, y0, x1, y1, d, labels=False, outline=False):
    import cv2
    from shapely.geometry import Polygon, box
    own = r.ownership()
    W, H = int((x1 - x0) / d), int((y1 - y0) / d)
    canvas = np.full((H, W, 3), 255, np.uint8)
    covered = np.zeros((H, W), np.uint8)
    rect = box(x0, y0, x1, y1)
    polys = {}
    for sheet, poly in own:
        P = Polygon(poly)
        if not P.intersects(rect):
            continue
        polys[sheet] = P
        img = cv2.imread(r.fetch(r.sheet_file(sheet)), cv2.IMREAD_COLOR)
        M, t = r.sheet_matrix(sheet)
        A = np.hstack([M / d, ((t - np.array([x0, y0])) / d).reshape(2, 1)])
        shifted = ((poly - np.array([x0, y0])) / d).astype(np.int32)
        wx0 = max(0, int(shifted[:, 0].min()) - 2); wy0 = max(0, int(shifted[:, 1].min()) - 2)
        wx1 = min(W, int(shifted[:, 0].max()) + 3); wy1 = min(H, int(shifted[:, 1].max()) + 3)
        if wx1 <= wx0 or wy1 <= wy0:
            continue
        Aw = A.copy(); Aw[:, 2] -= np.array([wx0, wy0], float)
        warped = cv2.warpAffine(img, Aw, (wx1 - wx0, wy1 - wy0),
                                flags=cv2.INTER_AREA, borderValue=(255, 255, 255))
        mask = np.zeros((wy1 - wy0, wx1 - wx0), np.uint8)
        cv2.fillPoly(mask, [shifted - np.array([wx0, wy0], np.int32)], 255)
        sub_cov = covered[wy0:wy1, wx0:wx1]
        mask &= cv2.inRange(sub_cov, 0, 0)
        m = mask.astype(bool)
        canvas[wy0:wy1, wx0:wx1][m] = warped[m]
        sub_cov |= mask
    # unowned-sliver fallback, as tools/render.py does it
    for sheet, poly in own:
        if sheet not in polys:
            continue
        fp = r.footprint(sheet)
        fpts = ((np.array(fp.exterior.coords) - np.array([x0, y0])) / d).astype(np.int32)
        wx0 = max(0, int(fpts[:, 0].min()) - 2); wy0 = max(0, int(fpts[:, 1].min()) - 2)
        wx1 = min(W, int(fpts[:, 0].max()) + 3); wy1 = min(H, int(fpts[:, 1].max()) + 3)
        if wx1 <= wx0 or wy1 <= wy0:
            continue
        sub_cov = covered[wy0:wy1, wx0:wx1]
        mask = np.zeros((wy1 - wy0, wx1 - wx0), np.uint8)
        cv2.fillPoly(mask, [fpts - np.array([wx0, wy0], np.int32)], 255)
        mask &= cv2.inRange(sub_cov, 0, 0)
        if cv2.countNonZero(mask) == 0:
            continue
        img = cv2.imread(r.fetch(r.sheet_file(sheet)), cv2.IMREAD_COLOR)
        M, t = r.sheet_matrix(sheet)
        Aw = np.hstack([M / d, ((t - np.array([x0, y0])) / d).reshape(2, 1)])
        Aw[:, 2] -= np.array([wx0, wy0], float)
        warped = cv2.warpAffine(img, Aw, (wx1 - wx0, wy1 - wy0), flags=cv2.INTER_AREA,
                                borderValue=(255, 255, 255))
        m = mask.astype(bool)
        canvas[wy0:wy1, wx0:wx1][m] = warped[m]
        sub_cov |= mask
    if outline or labels:
        for sheet, P in polys.items():
            pts = ((np.array(P.exterior.coords) - [x0, y0]) / d).astype(np.int32)
            if outline:
                cv2.polylines(canvas, [pts], True, (0, 0, 255), 1)
            if labels:
                c = P.intersection(rect).centroid
                if not c.is_empty:
                    cv2.putText(canvas, str(sheet), (int((c.x - x0) / d) - 20, int((c.y - y0) / d)),
                                cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 0, 0), 3)
    return canvas


def _interior_mask(r, x0, y0, x1, y1, d, W, H):
    """255 where the window lies inside a hole of the ownership union."""
    import cv2
    import numpy as np
    m = np.zeros((H, W), np.uint8)
    for P in r.interior_unowned():
        pts = ((np.array(P.exterior.coords) - np.array([x0, y0])) / d).astype(np.int32)
        cv2.fillPoly(m, [pts], 255)
        for ring in P.interiors:
            pts = ((np.array(ring.coords) - np.array([x0, y0])) / d).astype(np.int32)
            cv2.fillPoly(m, [pts], 0)
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", type=int, default=1912)
    ap.add_argument("--rect", nargs=4, type=float)
    ap.add_argument("--around", nargs="*", help="units to centre the window on")
    ap.add_argument("--pad", type=float, default=800)
    ap.add_argument("--downsample", type=int, default=4)
    ap.add_argument("--labels", action="store_true")
    ap.add_argument("--outline", action="store_true")
    ap.add_argument("--quality", type=int, default=82)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    import cv2
    r = Recipe(a.year)
    if a.rect:
        x0, y0, x1, y1 = a.rect
    else:
        from shapely.geometry import Polygon
        polys = [Polygon(p) for u, p in r.ownership() if u in set(a.around)]
        xs = [b for P in polys for b in (P.bounds[0], P.bounds[2])]
        ys = [b for P in polys for b in (P.bounds[1], P.bounds[3])]
        x0, y0, x1, y1 = min(xs) - a.pad, min(ys) - a.pad, max(xs) + a.pad, max(ys) + a.pad
    img = render(r, x0, y0, x1, y1, a.downsample, a.labels, a.outline)
    cv2.imwrite(a.out, img, [cv2.IMWRITE_JPEG_QUALITY, a.quality])
    print(f"wrote {a.out} {img.shape[1]}x{img.shape[0]} for rect ({x0:.0f},{y0:.0f})..({x1:.0f},{y1:.0f}) at 1/{a.downsample}")


if __name__ == "__main__":
    main()
