"""Composite the 1889 sheets covering the delivered 1899 poster's frame.

Frame: Avenue A (Water) -> Avenue I (Sealy), 19th -> 25th (Rosenberg),
plus the wharf front west of Avenue A.

These are the sheets the user originally selected off the 1889 key map:
1, 2 (wharf front) and 7, 8, 29 / 9, 10, 27 (downtown, three sheets per
street band across A-J) -- the same three-across structure the 1899 atlas
uses for 11/12/41 and 13/14/39.

1889 shares 1899's physical grid (avenue 1006, street ~1163 px on 3400 px
UT scans), so the corridor-SLOT model applies unchanged.

Styling matches the delivered 1899 poster: original washes
(PRESERVE_COLORS) over a flattened illumination field (FLATTEN_ILLUM).
"""
import json
import os
import sys

sys.path.insert(0, "/home/user/claude-code/sanborn")
import numpy as np
import cv2

import config
import coverage_prior as cov
import run_build as rb

YEAR = "1889"
UNITS = ["02", "01",              # wharf front (Av A + piers)
         "07", "08", "29",        # 19th-22nd  x  A-D, D-G, G-J
         "09", "10", "27"]        # 22nd-25th  x  A-D, D-G, G-J
ST_LO, ST_HI = 19, 25
AV_HI_SLOT = 8                    # Avenue I, east limit of the frame

ed = config.EDITIONS[YEAR]
config.STREET_ORIGIN = ed["street_origin"]
config.PRESERVE_COLORS = True
config.FLATTEN_ILLUM = True
config.CANVAS_PAD = 3400          # room for the piers west of Avenue A
k = config.DETECT_WIDTH / ed["native_size"][0]
config.PITCH_AV_DETECT = ed["pitch_av"] * k
config.PITCH_ST_DETECT = ed["pitch_st"] * k
LM = "/home/user/claude-code/sanborn/SEED_PRE1900/landmarks_1889.json"
if os.path.exists(LM):
    config.LANDMARKS_PATH = LM
# Wharf units carry a SINGLE avenue line each, so their x-scale is not
# constrained by detection at all; let the solver scale them and it will
# chase the landmark scatter. Hold them rigid (translation only) and let
# the downtown sheets take the scale, as 1899 did with its wharf trio.
config.RIGID_UNITS = ("01", "02")

cov.COVERAGE[YEAR] = {u: cov.COVERAGE[YEAR][u] for u in UNITS}

registration = rb.register_edition(YEAR)
bad = {u: r["status"] for u, r in registration.items() if r["status"] != "ok"}
if bad:
    print("BLOCKED:", bad)
    sys.exit(1)
tif = rb.composite_edition(YEAR, registration)

a0, a1, s0, s1 = cov.composite_extent(YEAR)
pad = config.CANVAS_PAD
ox = a0 * ed["pitch_av"] - pad
oy = (s0 - config.STREET_ORIGIN) * ed["pitch_st"] - pad
r = json.load(open(os.path.join(config.BUILD_DIR, YEAR, "registration.json")))
X = {int(a): v for a, v in r["consensus_av"].items()}
Y = {int(s): v for s, v in r["consensus_st"].items()}

img = cv2.imread(tif, cv2.IMREAD_COLOR)
mask = cv2.imread(os.path.join(config.BUILD_DIR, YEAR, "coverage_mask.png"),
                  cv2.IMREAD_GRAYSCALE)
H, W = img.shape[:2]

y0 = int(round(Y[ST_LO] - oy - 0.30 * ed["pitch_st"]))
y1 = int(round(Y[ST_HI] - oy + 0.30 * ed["pitch_st"]))
x1 = int(round(X[AV_HI_SLOT] - ox + 0.32 * ed["pitch_av"]))
band = mask[max(0, y0):min(H, y1), :]
cols = np.where(band.max(axis=0) > 0)[0]
x0 = int(max(0, cols.min() - 40)) if len(cols) else 0
x0, y0 = max(0, x0), max(0, y0)
x1, y1 = min(W, x1), min(H, y1)
tile = img[y0:y1, x0:x1]
sub = mask[y0:y1, x0:x1]
cover = 100.0 * (sub > 0).mean()
print(f"crop [{x0},{y0},{x1},{y1}] -> {tile.shape[1]}x{tile.shape[0]}, "
      f"source coverage {cover:.2f}%")

out_dir = os.path.join(config.DELIVER_DIR, YEAR)
os.makedirs(out_dir, exist_ok=True)
png = os.path.join(out_dir, "galveston_1889_downtown_wharf.png")
cv2.imwrite(png, tile)
json.dump({"units": UNITS, "crop": [x0, y0, x1, y1],
           "size": [tile.shape[1], tile.shape[0]],
           "coverage_pct": cover, "original_colors": True,
           "footprint": {"streets": [ST_LO, ST_HI], "av_slot_max": AV_HI_SLOT}},
          open(os.path.join(out_dir, "downtown_wharf_meta.json"), "w"), indent=1)
print("WROTE", png, os.path.getsize(png) >> 20, "MB")
