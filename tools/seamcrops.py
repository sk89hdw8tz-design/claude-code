#!/usr/bin/env python3
"""Render every seam of the city mosaic as a crop, for grading by eye.

    python3 tools/seamcrops.py --year 1912 [--only 57_63 ...] [--width 4000]

For each seam recorded by tools/streetcut.py (seams/ownership_city.json,
"seams"), renders a window centred on the middle of the pair's overlap,
elongated across the seam, from the recipe: outputs/{year}/qc/seams/
seam_{a}-{b}_100.jpg at full working resolution (1/2 of the plates' 300 ppi
scan, i.e. the 150 ppi web resolution) and seam_{a}-{b}_50.jpg at half that.
A thin tick at each end of the crop marks where the cut line crosses, so a
grader can find it; the map pixels are untouched.

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
        cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
        if s["axis"] == "y":                       # horizontal seam
            cy = s["coord"]
            x0, x1 = cx - ALONG / 2, cx + ALONG / 2
            y0, y1 = cy - ACROSS, cy + ACROSS
        else:
            cx = s["coord"]
            x0, x1 = cx - ACROSS, cx + ACROSS
            y0, y1 = cy - ALONG / 2, cy + ALONG / 2
        tif = os.path.join(out, f"seam_{tag}.tif")
        subprocess.run([sys.executable, os.path.join(REPO, "tools", "render.py"),
                        "--year", a.year, "--rect", str(x0), str(y0), str(x1), str(y1),
                        "--downsample", "2", "--out", tif], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, cwd=REPO)
        img = cv2.imread(tif, cv2.IMREAD_COLOR)
        os.remove(tif)
        H, W = img.shape[:2]
        # ticks at the cut, in the margins only
        if s["axis"] == "y":
            yy = int((s["coord"] - y0) / 2)
            cv2.line(img, (0, yy), (40, yy), (0, 0, 255), 3)
            cv2.line(img, (W - 40, yy), (W, yy), (0, 0, 255), 3)
        else:
            xx = int((s["coord"] - x0) / 2)
            cv2.line(img, (xx, 0), (xx, 40), (0, 0, 255), 3)
            cv2.line(img, (xx, H - 40), (xx, H), (0, 0, 255), 3)
        p100 = os.path.join(out, f"seam_{tag}_100.jpg")
        p50 = os.path.join(out, f"seam_{tag}_50.jpg")
        cv2.imwrite(p100, img, [cv2.IMWRITE_JPEG_QUALITY, 88])
        cv2.imwrite(p50, cv2.resize(img, (W // 2, H // 2), interpolation=cv2.INTER_AREA),
                    [cv2.IMWRITE_JPEG_QUALITY, 88])
        index.append(dict(s, crop_100=os.path.relpath(p100, REPO),
                          crop_50=os.path.relpath(p50, REPO),
                          window=[round(x0), round(y0), round(x1), round(y1)]))
        print(f"{tag:<8} {s['axis']} {s['how']:<8} {s.get('corridor') or '':<18} "
              f"{p100}", flush=True)
    json.dump({"tool": "tools/seamcrops.py", "seams": index},
              open(os.path.join(out, "index.json"), "w"), indent=1)
    print(f"{len(index)} seams rendered; index at {out}/index.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
