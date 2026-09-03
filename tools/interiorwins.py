#!/usr/bin/env python3
"""Sample 1:1 windows across the interior of the mosaic for close review.

    python3 tools/interiorwins.py --year 1912 [--cols 6 --rows 8 --size 1500]

A grid of windows over the ownership union, keeping only those whose centre
is owned (so the sample is inside the mapped city, not in the bay). Each is
rendered at 1:1 -- 1 px = 0.1725 ft, the plates' own resolution -- so a
reviewer sees exactly what the print carries.
"""
import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import qcrender                        # noqa: E402
from reciplib import Recipe            # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", type=int, default=1912)
    ap.add_argument("--cols", type=int, default=6)
    ap.add_argument("--rows", type=int, default=8)
    ap.add_argument("--size", type=int, default=1500)
    ap.add_argument("--downsample", type=int, default=1)
    a = ap.parse_args()
    import cv2
    from shapely.geometry import Point, Polygon
    from shapely.ops import unary_union
    r = Recipe(a.year)
    own = r.ownership()
    U = unary_union([Polygon(p).buffer(0) for _, p in own])
    x0, y0, x1, y1 = U.bounds
    d = os.path.join("outputs", str(a.year), "qc", "interior")
    os.makedirs(d, exist_ok=True)
    out = []
    k = 0
    for i in range(a.cols):
        for j in range(a.rows):
            cx = x0 + (i + 0.5) * (x1 - x0) / a.cols
            cy = y0 + (j + 0.5) * (y1 - y0) / a.rows
            if not U.contains(Point(cx, cy)):
                continue
            h = a.size * a.downsample / 2.0
            w = [cx - h, cy - h, cx + h, cy + h]
            img = qcrender.render(r, *w, a.downsample, labels=False, outline=False)
            p = os.path.join(d, f"win_{k:02d}.jpg")
            cv2.imwrite(p, img, [cv2.IMWRITE_JPEG_QUALITY, 88])
            owners = sorted({u for u, poly in own
                             if Polygon(poly).intersects(Polygon([(w[0], w[1]), (w[2], w[1]), (w[2], w[3]), (w[0], w[3])]))},
                            key=lambda z: (len(z), z))
            out.append({"window": f"win_{k:02d}.jpg", "rect": [round(v) for v in w],
                        "units": owners})
            print(f"{p} {img.shape[1]}x{img.shape[0]} units {owners}", flush=True)
            k += 1
    json.dump(out, open(os.path.join(d, "windows.json"), "w"), indent=1)
    print(f"{len(out)} interior windows")


if __name__ == "__main__":
    main()
