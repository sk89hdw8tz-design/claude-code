#!/usr/bin/env python3
"""Render every seam of the city mosaic as a crop, for grading by eye.

    python3 tools/seamcrops.py --year 1912 [--only 57_63 ...] [--width 4000]

For each seam recorded by tools/streetcut.py (seams/ownership_city.json,
"seams"), renders a window centred on the middle of the pair's overlap,
elongated across the seam, from the recipe: outputs/{year}/qc/seams/
seam_{a}-{b}_100.jpg at full working resolution (1/2 of the plates' 300 ppi
scan, i.e. the 150 ppi web resolution) and seam_{a}-{b}_50.jpg at half that.
A thin tick at each end of the crop marks where the cut line crosses, so a
grader can find it; the map pixels are untouched. The tick is placed on the
ACTUAL ownership boundary there (a min-ink path wanders up to DP_HALF = 320
mosaic px from the seam's nominal coordinate, and a tick at the coordinate
then hides the cut instead of finding it); where the two differ by more than
8 px the nominal coordinate is kept as a thin blue tick beside it.

Also writes seams/index.json: one row per seam with the crop paths, the
cut's source (control / lattice / midpoint), and the lattice disagreement
where there is one. The brief's Stage 5 graders work from these.
"""
import argparse
import json
import os
import subprocess
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from reciplib import Recipe                      # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ACROSS = 1600        # mosaic px each side of the cut (~275 ft)
ALONG = 5000         # mosaic px along the seam (~860 ft)


def boundary_at(shared, axis, along, across_range):
    """Where the two regions actually meet at position `along` on the seam.

    `shared` is the (buffered) intersection of the two ownership polygons --
    a thin strip lying on the cut itself, wherever the cut runs. Sampling it
    with a line across the seam gives the cut's real position there, path
    wander included. Returns None where the strip does not reach that end of
    the crop (a corner seam that stops short), and the caller falls back to
    the seam's nominal coordinate.
    """
    from shapely.geometry import LineString
    lo, hi = across_range
    ln = LineString([(along, lo), (along, hi)] if axis == "y"
                    else [(lo, along), (hi, along)])
    g = shared.intersection(ln)
    if g.is_empty:
        return None
    c = g.centroid
    return float(c.y if axis == "y" else c.x)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", required=True, choices=["1912"])
    ap.add_argument("--only", nargs="*", default=None, help="pairs like 57_63")
    ap.add_argument("--kinds", default="band", help="band, corner or band,corner")
    a = ap.parse_args()
    r = Recipe(int(a.year))
    doc = json.load(open(os.path.join(r.dir, "seams", "ownership_city.json")))
    seams = doc.get("seams") or []
    kinds = set(a.kinds.split(","))
    out = os.path.join(REPO, "outputs", a.year, "qc", "seams")
    os.makedirs(out, exist_ok=True)
    import cv2
    from qcrender import render as qc_render
    index = []
    for s in seams:
        u, v = s["pair"]
        tag = f"{u}_{v}"
        if a.only and tag not in a.only:
            continue
        if s["kind"] not in kinds:
            continue
        # window: the overlap's middle, elongated along the seam
        from shapely.geometry import Polygon
        regs = {x["unit"]: Polygon(x["polygon_mosaic"]["exterior"]) for x in doc["regions"]
                if x["unit"] in (u, v)}
        if len(regs) < 2:
            continue
        shared = regs[u].buffer(2).intersection(regs[v].buffer(2))
        if shared.is_empty:
            continue
        b = shared.bounds
        # tile the WHOLE seam: a band seam runs the length of a plate side
        # (~7,500 px), longer than one window, and the census must see all
        # of it, not its middle
        if s["axis"] == "y":                       # horizontal seam
            lo, hi = b[0], b[2]
        else:
            lo, hi = b[1], b[3]
        n = max(1, int(np.ceil((hi - lo) / ALONG)))
        starts = [lo + (hi - lo - ALONG) * i / max(1, n - 1) for i in range(n)] if hi - lo > ALONG \
            else [(lo + hi) / 2 - ALONG / 2]
        crops = []
        for j, a0 in enumerate(starts):
            if s["axis"] == "y":
                cy = s["coord"]
                x0, x1 = a0, a0 + ALONG
                y0, y1 = cy - ACROSS, cy + ACROSS
            else:
                cx = s["coord"]
                x0, x1 = cx - ACROSS, cx + ACROSS
                y0, y1 = a0, a0 + ALONG
            img = qc_render(r, x0, y0, x1, y1, 2)
            H, W = img.shape[:2]
            # The tick must mark the OWNERSHIP BOUNDARY, not the seam's
            # nominal coordinate: a min-ink path may wander up to DP_HALF
            # (320 mosaic px, 55 ft) from it, and a tick drawn at the
            # coordinate then points at open ground while the cut -- and any
            # defect on it -- is elsewhere in the crop. That is how a straight
            # cut 320 px off its coord passed two graders on 3|4. So the red
            # tick follows the real boundary between the two regions at each
            # end of the crop, and a thin blue tick keeps the nominal
            # coordinate visible wherever the two differ by more than 8 px.
            for end in (0, 1):
                along = (x0 + 20, x1 - 20)[end] if s["axis"] == "y" else (y0 + 20, y1 - 20)[end]
                across = (y0, y1) if s["axis"] == "y" else (x0, x1)
                real = boundary_at(shared, s["axis"], along, across)
                marks = [(s["coord"], (255, 0, 0), 2)]        # nominal, thin blue
                if real is not None:
                    marks = [(real, (0, 0, 255), 3)] + (
                        [] if abs(real - s["coord"]) <= 8 else marks)
                else:
                    marks = [(s["coord"], (0, 0, 255), 3)]    # nothing better to draw
                for val, colour, thick in marks:
                    if s["axis"] == "y":
                        yy = int((val - y0) / 2)
                        if not 0 <= yy < H:
                            continue
                        pt = ((0, yy), (40, yy)) if end == 0 else ((W - 40, yy), (W, yy))
                    else:
                        xx = int((val - x0) / 2)
                        if not 0 <= xx < W:
                            continue
                        pt = ((xx, 0), (xx, 40)) if end == 0 else ((xx, H - 40), (xx, H))
                    cv2.line(img, pt[0], pt[1], colour, thick)
            suf = "" if n == 1 else f"_{chr(97 + j)}"
            p100 = os.path.join(out, f"seam_{tag}{suf}_100.jpg")
            p50 = os.path.join(out, f"seam_{tag}{suf}_50.jpg")
            cv2.imwrite(p100, img, [cv2.IMWRITE_JPEG_QUALITY, 88])
            cv2.imwrite(p50, cv2.resize(img, (W // 2, H // 2), interpolation=cv2.INTER_AREA),
                        [cv2.IMWRITE_JPEG_QUALITY, 88])
            crops.append({"crop_100": os.path.relpath(p100, REPO), "crop_50": os.path.relpath(p50, REPO),
                          "window": [round(x0), round(y0), round(x1), round(y1)]})
        index.append(dict(s, crops=crops, crop_100=crops[0]["crop_100"], crop_50=crops[0]["crop_50"],
                          window=crops[0]["window"]))
        print(f"{tag:<8} {s['axis']} {s['how']:<8} {s.get('corridor') or '':<18} {len(crops)} crops", flush=True)
    json.dump({"tool": "tools/seamcrops.py", "seams": index},
              open(os.path.join(out, "index.json"), "w"), indent=1)
    print(f"{len(index)} seams rendered; index at {out}/index.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
