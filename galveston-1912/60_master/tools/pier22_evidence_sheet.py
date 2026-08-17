"""Native-resolution evidence crops for the Pier 22 repair decision.

Three bands down the splice, each 1200x1500 canvas px shown 1:1, so the rail
tracks can be followed INTO and OUT OF the problem area rather than judged from
a downscaled preview. For each band every candidate source is cropped from the
identical integer rectangle -- the crop-clamping defence the brief calls for.
"""

import os
import sys

import cv2
import numpy as np
import tifffile
from PIL import Image

Image.MAX_IMAGE_PIXELS = None

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pier22_candidates import (CAND_S, CAND_P, render, WX0, WY0, WX1, WY1)  # noqa

OUT = "/home/user/g1912/work/pier22/evidence"
os.makedirs(OUT, exist_ok=True)

BANDS = {
    "N": (8000, 6700, 9200, 8200),      # label rows, water pipe, tracks 5/7
    "C": (7800, 8000, 9000, 9500),      # fan through the boundary
    "S": (7500, 9000, 8700, 10500),     # convergence and departure south-west
}

variants = {}
for tag, spec in [("current", None), ("S", CAND_S), ("P", CAND_P)]:
    variants[tag] = render(spec, f"ev_{tag}")
    print(f"rendered {tag}")

for bname, (bx0, by0, bx1, by1) in BANDS.items():
    assert WX0 <= bx0 and bx1 <= WX1 and WY0 <= by0 and by1 <= WY1, bname
    sx0, sy0 = bx0 - WX0, by0 - WY0
    sx1, sy1 = bx1 - WX0, by1 - WY0
    for tag, img in variants.items():
        crop = img[sy0:sy1, sx0:sx1]
        cv2.imwrite(f"{OUT}/{bname}_{tag}.jpg", crop[:, :, ::-1],
                    [cv2.IMWRITE_JPEG_QUALITY, 95])
    print(f"band {bname}: canvas x{bx0}-{bx1} y{by0}-{by1} "
          f"({bx1-bx0}x{by1-by0}) written")
print(f"\nevidence in {OUT}")
