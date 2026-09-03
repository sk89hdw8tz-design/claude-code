#!/usr/bin/env python3
"""Re-render the periphery review windows from the current recipe.

    python3 tools/perirender.py --year 1912

The window list (outputs/<year>/qc/periphery/windows.json) is a walk along
the outer boundary of the mosaic: [index, x0, y0, x1, y1] in mosaic px.
Each is rendered at 1/4 (1 px ~= 1.4 ft) with unit labels, as the
periphery brief describes them.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import qcrender                       # noqa: E402
from reciplib import Recipe           # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", type=int, default=1912)
    ap.add_argument("--downsample", type=int, default=4)
    ap.add_argument("--only", nargs="*", type=int)
    a = ap.parse_args()
    import cv2
    r = Recipe(a.year)
    d = os.path.join("outputs", str(a.year), "qc", "periphery")
    wins = json.load(open(os.path.join(d, "windows.json")))
    for w in wins:
        i, x0, y0, x1, y1 = w
        if a.only and i not in a.only:
            continue
        img = qcrender.render(r, x0, y0, x1, y1, a.downsample, labels=True, outline=False)
        p = os.path.join(d, f"edge_{i:02d}.jpg")
        cv2.imwrite(p, img, [cv2.IMWRITE_JPEG_QUALITY, 82])
        print(f"{p} {img.shape[1]}x{img.shape[0]}", flush=True)


if __name__ == "__main__":
    main()
