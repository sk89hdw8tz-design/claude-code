"""Feature-level regression QA for the Pier 22 repair.

The repair provably changed only canvas x8130..8471, y6402..8998 (see
pier22_regression.py). This renders the wharf frontage from the DELIVERED master
with that rectangle outlined, so each named feature in the brief's regression
list can be located and its relationship to the changed rectangle read directly.
"""

import os

import cv2
import numpy as np
import tifffile
from PIL import Image

Image.MAX_IMAGE_PIXELS = None

G = "/home/user/claude-code/galveston-1912"
OUT = "/home/user/g1912/work/pier22"
CHANGED = (8130, 6402, 8472, 8999)          # x0,y0,x1,y1 canvas

# whole wharf frontage, bay side
X0, Y0, X1, Y1 = 2600, 1500, 11000, 14489
m = tifffile.imread(f"{G}/60_master/final/master_full.tif")[Y0:Y1, X0:X1]
vis = np.ascontiguousarray(m[:, :, ::-1])
cv2.rectangle(vis, (CHANGED[0] - X0, CHANGED[1] - Y0),
              (CHANGED[2] - X0, CHANGED[3] - Y0), (0, 0, 255), 14)
sc = 0.14
small = cv2.resize(vis, None, fx=sc, fy=sc, interpolation=cv2.INTER_AREA)
cv2.imwrite(f"{OUT}/qa_wharf_overview.jpg", small, [cv2.IMWRITE_JPEG_QUALITY, 92])
print(f"wharf overview canvas x{X0}-{X1} y{Y0}-{Y1} at {sc}x -> {small.shape[1]}x{small.shape[0]}")
print(f"changed rectangle outlined: x{CHANGED[0]}..{CHANGED[2]} y{CHANGED[1]}..{CHANGED[3]}")
