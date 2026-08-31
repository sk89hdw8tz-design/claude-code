#!/usr/bin/env python3
"""On-demand crop: address + print size -> print-ready TIFF/PDF.

Lazy by design: resolves the address against the recipe's corridor grid,
finds the sheets whose ownership regions intersect the crop, fetches ONLY
those sheets (hash-cached under work/sheets/), renders at native scale
through the recipe transforms, and composites by the frozen ownership
polygons. Runs in a fresh clone with nothing pre-downloaded.

Examples:
  python3 tools/crop.py --year 1912 --street 22 --avenue E \
      --width-in 8 --height-in 10 --out pier_office.tif
  python3 tools/crop.py --year 1912 --street 21 --avenue C \
      --width-in 27 --height-in 40 --scale-ft-per-in 200 --pdf
"""
import argparse
import json
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from reciplib import Recipe, px_per_ft  # noqa: E402

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", type=int, required=True, choices=(1899, 1912))
    ap.add_argument("--street", type=int, help="street number, e.g. 22")
    ap.add_argument("--avenue", help="avenue letter A-K or 'Broadway'")
    ap.add_argument("--cx", type=float, help="mosaic x (overrides address)")
    ap.add_argument("--cy", type=float, help="mosaic y (overrides address)")
    ap.add_argument("--width-in", type=float, default=8.0)
    ap.add_argument("--height-in", type=float, default=10.0)
    ap.add_argument("--scale-ft-per-in", type=float, default=100.0,
                    help="ground feet per printed inch; 100 matches the 27x40 masters "
                         "(the sheets are DRAWN at 50, the masters print at ~99)")
    ap.add_argument("--dpi", type=int, default=300)
    ap.add_argument("--out", default=None)
    ap.add_argument("--pdf", action="store_true", help="also write a PDF")
    a = ap.parse_args()

    r = Recipe(a.year)
    if r.transforms is None or r.masks is None:
        sys.exit(f"the {a.year} recipe has no transforms/masks yet")
    ppf = px_per_ft(r)

    # centre of the crop, mosaic frame
    if a.cx is not None and a.cy is not None:
        cx, cy = a.cx, a.cy
    else:
        if a.street is None or a.avenue is None:
            sys.exit("give --street and --avenue, or --cx/--cy")
        cx, cy = r.locate(a.street, a.avenue)
        if cx is None or cy is None:
            sys.exit("address not in the grid index")

    half_w = a.width_in * a.scale_ft_per_in * ppf / 2.0
    half_h = a.height_in * a.scale_ft_per_in * ppf / 2.0
    x0, y0, x1, y1 = cx - half_w, cy - half_h, cx + half_w, cy + half_h
    W = int(round(x1 - x0))
    H = int(round(y1 - y0))
    print(f"crop mosaic rect: ({x0:.0f},{y0:.0f})..({x1:.0f},{y1:.0f})  "
          f"{W}x{H} px at native scale")

    from shapely.geometry import Polygon, box
    rect = box(x0, y0, x1, y1)
    involved = []
    for sheet, poly in r.ownership():
        if Polygon(poly).intersects(rect):
            involved.append((sheet, poly))
    print("sheets involved:", [s for s, _ in involved])
    if not involved:
        sys.exit("no source sheet covers this area (outside the mosaic)")

    canvas = np.full((H, W, 3), 255, np.uint8)
    covered = np.zeros((H, W), np.uint8)
    for sheet, poly in involved:
        path = r.fetch(r.sheet_file(sheet))
        img = cv2.imread(path, cv2.IMREAD_COLOR)
        if img is None:
            sys.exit(f"failed to decode {path}")
        M, t = r.sheet_matrix(sheet)
        # native -> crop canvas: p_canvas = M @ p_native + t - [x0, y0]
        A = np.hstack([M, (t - np.array([x0, y0])).reshape(2, 1)])
        warped = cv2.warpAffine(img, A, (W, H), flags=cv2.INTER_LANCZOS4,
                                borderValue=(255, 255, 255))
        mask = np.zeros((H, W), np.uint8)
        shifted = (poly - np.array([x0, y0])).astype(np.int32)
        cv2.fillPoly(mask, [shifted], 255)
        mask &= cv2.inRange(covered, 0, 0)   # first writer wins inside overlap gaps
        canvas[mask > 0] = warped[mask > 0]
        covered |= mask
        print(f"  sheet {sheet}: composited {int((mask > 0).sum())} px")
    # fallback: pixels no ownership polygon claims but that lie on a real
    # sheet's scan are filled from that sheet, in deterministic priority
    # order (wharf sheets first). No content is invented; slivers between
    # neighbouring regions' bookkeeping edges get real ink.
    order = sorted({s for s, _ in involved},
                   key=lambda s: (s not in ("7", "07", "6", "06", "8", "08"), int(s)))
    for sheet in order:
        if not (covered == 0).any():
            break
        path_ = r.fetch(r.sheet_file(sheet))
        img = cv2.imread(path_, cv2.IMREAD_COLOR)
        M, t = r.sheet_matrix(sheet)
        A = np.hstack([M, (t - np.array([x0, y0])).reshape(2, 1)])
        warped = cv2.warpAffine(img, A, (W, H), flags=cv2.INTER_LANCZOS4,
                                borderValue=(255, 255, 255))
        inb = np.zeros((H, W), np.uint8)
        wq, hq = img.shape[1], img.shape[0]
        ins = 60      # keep scanner-edge junk out of the fallback fill
        bot = 230 if getattr(r, "year", None) == 1899 else ins  # 1899 credit caption band
        corners = np.array([(M @ np.array(p) + t - [x0, y0])
                            for p in [(ins, ins), (wq - ins, ins),
                                      (wq - ins, hq - bot), (ins, hq - bot)]],
                           np.int32)
        cv2.fillPoly(inb, [corners], 255)
        fb = (covered == 0) & (inb > 0)
        n = int(fb.sum())
        if n:
            canvas[fb] = warped[fb]
            covered[fb] = 255
            print(f"  sheet {sheet}: +{n} px unowned-sliver fallback (disclosed)")
    uncovered = int((covered == 0).sum())
    if uncovered:
        print(f"  note: {uncovered} px outside every source sheet left paper-white (disclosed)")

    out_w = int(round(a.width_in * a.dpi))
    out_h = int(round(a.height_in * a.dpi))
    resized = cv2.resize(canvas, (out_w, out_h), interpolation=cv2.INTER_AREA
                         if out_w < W else cv2.INTER_LANCZOS4)
    name = a.out or f"crop_{a.year}_{a.street}_{a.avenue}.tif"
    from PIL import Image
    im = Image.fromarray(cv2.cvtColor(resized, cv2.COLOR_BGR2RGB))
    im.save(name, dpi=(a.dpi, a.dpi), compression="tiff_lzw")
    print(f"wrote {name} ({out_w}x{out_h} at {a.dpi} dpi = "
          f"{a.width_in}x{a.height_in} in, {a.scale_ft_per_in} ft/in)")
    if a.pdf:
        pdf = os.path.splitext(name)[0] + ".pdf"
        im.save(pdf, "PDF", resolution=a.dpi)
        print(f"wrote {pdf}")

if __name__ == "__main__":
    main()
