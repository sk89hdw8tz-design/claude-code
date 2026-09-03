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

NATIVE_PPI = 300.0    # what the plates scan and the masters print at


def save(canvas, out, ppi=None):
    """Write the BGR canvas as a tiled, pyramidal TIFF.

    Streams through libvips off the existing buffer: converting to RGB with
    cv2.cvtColor and handing that to Pillow allocates two more copies of the
    whole canvas, which OOMs at gigapixel sizes.

    ppi is written into the TIFF resolution tags. Without it libvips falls
    back to its default 1 pixel/mm and the file claims 25.4 ppi -- the first
    published COG said that, six times finer than the 150 ppi it actually is,
    which would mis-scale anything printed or measured from it.
    """
    H, W = canvas.shape[:2]
    try:
        import pyvips
        v = pyvips.Image.new_from_memory(canvas.data, W, H, 3, "uchar")
        v = v[2].bandjoin([v[1], v[0]])                 # BGR -> RGB, lazily
        kw = {}
        if ppi:
            v = v.copy(xres=ppi / 25.4, yres=ppi / 25.4)   # libvips is px/mm
            kw = {"resunit": "inch"}
        v.tiffsave(out, compression="lzw", tile=True, tile_width=512,
                   tile_height=512, pyramid=True, bigtiff=True, **kw)
        return
    except ImportError:
        pass
    import cv2
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = None
    if not cv2.imwrite(out, canvas):                     # BGR, no extra copy
        Image.fromarray(cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB)).save(
            out, compression="tiff_lzw")


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
    ap.add_argument("--year", type=int, required=True, choices=(1899, 1912))
    ap.add_argument("--all", action="store_true", help="full mosaic extent")
    ap.add_argument("--rect", nargs=4, type=float,
                    metavar=("X0", "Y0", "X1", "Y1"), help="mosaic-frame rect")
    ap.add_argument("--ppi", type=float, default=None,
                    help="resolution to record in the TIFF tags; defaults to "
                         "the plates' ~300 ppi divided by --downsample")
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
    holes = {u: [np.array(ring.coords, float) for ring in P.interiors]
             for u, P in r.ownership_shapes() if P.interiors}

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
        # Warp into the sheet's OWN window, not the whole canvas. A sheet
        # covers a few percent of a city-wide mosaic, so a full-canvas warp
        # allocated a second canvas-sized buffer per sheet -- 4 GB each at 1/2
        # on the city -- for the sake of a 50 MB footprint.
        shifted = ((poly - np.array([x0, y0])) / d).astype(np.int32)
        wx0 = max(0, int(shifted[:, 0].min()) - 2)
        wy0 = max(0, int(shifted[:, 1].min()) - 2)
        wx1 = min(W, int(shifted[:, 0].max()) + 3)
        wy1 = min(H, int(shifted[:, 1].max()) + 3)
        if wx1 <= wx0 or wy1 <= wy0:
            print(f"  sheet {sheet} outside the render rect", flush=True)
            continue
        ww, wh = wx1 - wx0, wy1 - wy0
        Aw = A.copy()
        Aw[:, 2] -= np.array([wx0, wy0], float)
        warped = cv2.warpAffine(img, Aw, (ww, wh),
                                flags=cv2.INTER_LANCZOS4 if d == 1
                                else cv2.INTER_AREA,
                                borderValue=(255, 255, 255))
        mask = np.zeros((wh, ww), np.uint8)
        cv2.fillPoly(mask, [shifted - np.array([wx0, wy0], np.int32)], 255)
        for ring in holes.get(sheet, []):
            h = ((ring - np.array([x0, y0])) / d).astype(np.int32) - np.array([wx0, wy0], np.int32)
            cv2.fillPoly(mask, [h], 0)
        sub_cov = covered[wy0:wy1, wx0:wx1]
        mask &= cv2.inRange(sub_cov, 0, 0)
        # write through the canvas view. cv2.copyTo will not take a
        # column-sliced numpy view as its destination -- it is not contiguous
        # -- and the fancy-index temporaries it used to avoid are now bounded
        # by the sheet window rather than the whole canvas.
        sub = canvas[wy0:wy1, wx0:wx1]
        m = mask.astype(bool)
        sub[m] = warped[m]
        sub_cov |= mask
        del warped, mask, sub, m, sub_cov
        print(f"  sheet {sheet} composited", flush=True)
    # Second pass: ground no region claims (cut-line slivers at plate corners,
    # notches between a min-ink path and a neighbouring cut, the strip a
    # neighbour's neat line stops short of) is painted from any plate whose
    # trimmed footprint covers it. Nothing is invented: the pixels are that
    # plate's own scan of that ground, and the area is reported. The footprint
    # used here is the furniture-aware one, so a marking a neighbour can
    # replace in full is never painted back, while one no neighbour maps stays
    # on the plate's own paper rather than leaving a hole.
    fallback = 0
    for sheet, poly in involved:
        try:
            fp = r.footprint(sheet)
        except Exception:
            continue
        fpts = ((np.array(fp.exterior.coords) - np.array([x0, y0])) / d).astype(np.int32)
        wx0 = max(0, int(fpts[:, 0].min()) - 2); wy0 = max(0, int(fpts[:, 1].min()) - 2)
        wx1 = min(W, int(fpts[:, 0].max()) + 3); wy1 = min(H, int(fpts[:, 1].max()) + 3)
        if wx1 <= wx0 or wy1 <= wy0:
            continue
        sub_cov = covered[wy0:wy1, wx0:wx1]
        mask = np.zeros((wy1 - wy0, wx1 - wx0), np.uint8)
        cv2.fillPoly(mask, [fpts - np.array([wx0, wy0], np.int32)], 255)
        mask &= cv2.inRange(sub_cov, 0, 0)
        n = int(cv2.countNonZero(mask))
        if n == 0:
            continue
        img = cv2.imread(r.fetch(r.sheet_file(sheet)), cv2.IMREAD_COLOR)
        M, t = r.sheet_matrix(sheet)
        Aw = np.hstack([M / d, ((t - np.array([x0, y0])) / d).reshape(2, 1)])
        Aw[:, 2] -= np.array([wx0, wy0], float)
        warped = cv2.warpAffine(img, Aw, (wx1 - wx0, wy1 - wy0),
                                flags=cv2.INTER_LANCZOS4 if d == 1 else cv2.INTER_AREA,
                                borderValue=(255, 255, 255))
        m = mask.astype(bool)
        canvas[wy0:wy1, wx0:wx1][m] = warped[m]
        sub_cov |= mask
        fallback += n
        del warped, mask, m, img
    if fallback:
        print(f"  unowned-sliver fallback: {fallback} px at 1/{d} painted from covering "
              f"plates (disclosed; ownership polygons unchanged)", flush=True)
    del covered
    out = a.out or f"render_{a.year}.tif"
    save(canvas, out, ppi=a.ppi if a.ppi else NATIVE_PPI / d)
    print(f"wrote {out}")
    if a.dzi:
        import pyvips
        base = os.path.splitext(out)[0]
        pyvips.Image.new_from_file(out).dzsave(base, suffix=".jpg[Q=85]")
        print(f"wrote {base}.dzi + {base}_files/")

if __name__ == "__main__":
    main()
