"""Final before/after evidence for the Pier 22 repair.

'After' is cropped from the DELIVERED master_full.tif, not from a test render,
so what is shown is what was shipped. 'Before' is the same integer rectangle
composited with the frozen frontier. Identical crop rectangles for both.
"""

import os
import sys

import cv2
import numpy as np
import tifffile
from PIL import Image

Image.MAX_IMAGE_PIXELS = None

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pier22_candidates as pc  # noqa: E402

G = "/home/user/claude-code/galveston-1912"
OUT = "/home/user/g1912/work/pier22/final"
os.makedirs(OUT, exist_ok=True)

# The crop must show the tracks entering the zone from the north and leaving it
# to the south-west, with the whole circled convergence between.
CX0, CY0, CX1, CY1 = 7900, 6500, 9300, 9400

pc.WX0, pc.WY0, pc.WX1, pc.WY1 = CX0, CY0, CX1, CY1
before = pc.render(None, "final_before")
after = np.ascontiguousarray(
    tifffile.imread(f"{G}/60_master/final/master_full.tif")[CY0:CY1, CX0:CX1])

cv2.imwrite(f"{OUT}/before.jpg", before[:, :, ::-1], [cv2.IMWRITE_JPEG_QUALITY, 95])
cv2.imwrite(f"{OUT}/after.jpg", after[:, :, ::-1], [cv2.IMWRITE_JPEG_QUALITY, 95])

h, w = after.shape[:2]
gap = 40
pair = np.full((h + 60, w * 2 + gap, 3), 255, np.uint8)
pair[60:, :w] = before
pair[60:, w + gap:] = after
cv2.putText(pair, "BEFORE  (frozen boundary)", (10, 42),
            cv2.FONT_HERSHEY_SIMPLEX, 1.1, (0, 0, 0), 2, cv2.LINE_AA)
cv2.putText(pair, "AFTER  (D-014, delivered master)", (w + gap + 10, 42),
            cv2.FONT_HERSHEY_SIMPLEX, 1.1, (0, 0, 0), 2, cv2.LINE_AA)
cv2.imwrite(f"{OUT}/before_after_pair.jpg", pair[:, :, ::-1],
            [cv2.IMWRITE_JPEG_QUALITY, 93])

d = np.abs(before.astype(np.int16) - after.astype(np.int16)).max(axis=2)
print(f"crop canvas x{CX0}-{CX1} y{CY0}-{CY1}  ({w}x{h}) -- identical rectangle both sides")
print(f"pixels differing in the crop: {int((d > 4).sum()):,} "
      f"({100*float((d > 4).mean()):.2f}%)")
print(f"wrote {OUT}/before.jpg, after.jpg, before_after_pair.jpg")
