#!/usr/bin/env python3
"""Rebuild a region — or the whole mosaic — from the recipe, deterministically.

The recipe (outputs/{year}/recipe/) is the product; this renders it. The
pipeline is: fetch each involved sheet (hash-verified; git mirror first,
recorded source URL second), warp through its frozen transform, composite by
the frozen ownership polygons. Output is deterministic for a given recipe
and tool version: same inputs, same bytes.

  python3 tools/render.py --year 1912 --all --out master_1912.tif
  python3 tools/render.py --year 1912 --rect -5000 -5000 5000 5000 --out r.tif
  python3 tools/render.py --year 1912 --all --dry-run     # disk estimate only
  python3 tools/render.py --year 1912 --all --downsample 4 --out preview.tif

Disk needs are printed before rendering starts; --dry-run stops there.
Full-resolution whole-city output is intended for a local machine, not the
cloud VM (see REPORT.md).
"""
import argparse
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from reciplib import Recipe  # noqa: E402

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", type=int, required=True, choices=(1899, 1912))
    ap.add_argument("--all", action="store_true", help="full mosaic extent")
    ap.add_argument("--rect", nargs=4, type=float,
                    metavar=("X0", "Y0", "X1", "Y1"), help="mosaic-frame rect")
    ap.add_argument("--downsample", type=int, default=1,
                    help="render at 1/N scale (QC previews)")
    ap.add_argument("--out", default=None)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--dzi", action="store_true",
                    help="also write a DeepZoom pyramid next to --out")
    a = ap.parse_args()

    r = Recipe(a.year)
    if r.transforms is None or r.masks is None:
        sys.exit(f"the {a.year} recipe has no transforms/masks yet")
    own = r.ownership()

    if a.rect:
        x0, y0, x1, y1 = a.rect
    else:
        allpts = np.vstack([p for _, p in own])
        x0, y0 = allpts.min(axis=0)
        x1, y1 = allpts.max(axis=0)
    d = a.downsample
    W, H = int((x1 - x0) / d), int((y1 - y0) / d)

    from shapely.geometry import Polygon, box
    rect = box(x0, y0, x1, y1)
    involved = [(s, p) for s, p in own if Polygon(p).intersects(rect)]
    src_bytes = sum(r.source_bytes(s) for s, _ in involved)
    out_bytes = W * H * 3
    print(f"extent: ({x0:.0f},{y0:.0f})..({x1:.0f},{y1:.0f}) mosaic px, "
          f"output {W}x{H} at 1/{d} scale")
    print(f"sheets involved: {len(involved)} ({[s for s, _ in involved]})")
    print(f"disk needed: ~{src_bytes/1e6:.0f} MB sources (cached under work/sheets/) "
          f"+ ~{out_bytes/1e6:.0f} MB uncompressed canvas "
          f"(TIFF-LZW output typically 30-60% of that)")
    if a.dry_run:
        return
    if out_bytes > 6e9:
        print("canvas over 6 GB — run this on a machine with the RAM/disk for it, "
              "or use --downsample / --rect")

    import cv2
    canvas = np.full((H, W, 3), 255, np.uint8)
    covered = np.zeros((H, W), np.uint8)
    for sheet, poly in involved:
        path = r.fetch(r.sheet_file(sheet))
        img = cv2.imread(path, cv2.IMREAD_COLOR)
        M, t = r.sheet_matrix(sheet)
        A = np.hstack([M / d, ((t - np.array([x0, y0])) / d).reshape(2, 1)])
        warped = cv2.warpAffine(img, A, (W, H), flags=cv2.INTER_LANCZOS4 if d == 1
                                else cv2.INTER_AREA,
                                borderValue=(255, 255, 255))
        mask = np.zeros((H, W), np.uint8)
        shifted = ((poly - np.array([x0, y0])) / d).astype(np.int32)
        cv2.fillPoly(mask, [shifted], 255)
        mask &= cv2.inRange(covered, 0, 0)
        canvas[mask > 0] = warped[mask > 0]
        covered |= mask
        print(f"  sheet {sheet} composited")
    out = a.out or f"render_{a.year}.tif"
    from PIL import Image
    Image.fromarray(cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB)).save(
        out, compression="tiff_lzw")
    print(f"wrote {out}")
    if a.dzi:
        import pyvips
        base = os.path.splitext(out)[0]
        pyvips.Image.new_from_file(out).dzsave(base, suffix=".jpg[Q=85]")
        print(f"wrote {base}.dzi + {base}_files/")

if __name__ == "__main__":
    main()
