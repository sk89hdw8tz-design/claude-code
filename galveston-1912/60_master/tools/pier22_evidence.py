"""Evidence panel for the Sheet 5 / Pier 22 rail-fan splice.

Renders the SAME native-resolution window from every candidate source, so the
question "who actually draws these tracks?" is answered from the originals
rather than from the composite. Nothing is modified; this only reads.

Window is the circled rail convergence east of the slip's south-east corner.
"""

import json
import os
import sys

import cv2
import numpy as np
import tifffile
from PIL import Image, ImageDraw

Image.MAX_IMAGE_PIXELS = None

G = "/home/user/claude-code/galveston-1912"
SCAN = ("/home/user/g1912/data-branch/galveston_1912_sources/"
        "sanborn08539_004_img009_archival.jp2")
OUT = "/home/user/g1912/work/pier22"
os.makedirs(OUT, exist_ok=True)

# canvas window (generous: shows tracks entering AND leaving the zone)
X0, Y0, X1, Y1 = 7900, 7300, 9300, 9300
W, H = X1 - X0, Y1 - Y0
CX0, CY0 = -16734, -8279            # canvas = mosaic - (CX0, CY0)

tf = json.load(open(f"{G}/40_solve/output_sheet5_joint/"
                    "transforms_sheet5_joint_shared.json"))["panels"]
geo = json.load(open(f"{G}/fable_review/sheet05_candidate_regions.geojson"))
feats = {f["properties"].get("region_id"): f for f in geo["features"]}

scan = cv2.imread(SCAN, cv2.IMREAD_COLOR)
SH, SW = scan.shape[:2]


def panel_layer(rid):
    """Warp one sheet-5 panel into the window; white where the panel is absent."""
    key = "5A" if "A" in rid else "5B"
    r = tf[key]["raw"]
    M = np.array([[r["a"], -r["b"], r["tx"] - CX0 - X0],
                  [r["b"], r["a"], r["ty"] - CY0 - Y0]], np.float64)
    ring = np.array(feats[rid]["geometry"]["coordinates"][0], np.float64)
    mask_sheet = np.zeros((SH, SW), np.uint8)
    cv2.fillPoly(mask_sheet, [np.round(ring).astype(np.int32)], 255)
    img = cv2.warpAffine(scan, M, (W, H), flags=cv2.INTER_LANCZOS4,
                         borderMode=cv2.BORDER_CONSTANT, borderValue=(255, 255, 255))
    msk = cv2.warpAffine(mask_sheet, M, (W, H), flags=cv2.INTER_NEAREST,
                         borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    img[msk == 0] = 255
    return img, msk > 0


def crop_master(path):
    m = tifffile.imread(path)
    out = np.ascontiguousarray(m[Y0:Y1, X0:X1])
    del m
    return out[:, :, ::-1]          # RGB -> BGR for cv2 writing


layers = {}
layers["1_current_master"] = crop_master(f"{G}/60_master/final/master_full.tif")
layers["2_block_only"] = crop_master(f"{G}/60_master/final/candidate_master.tif")
imgA, mA = panel_layer("A")
imgB, mB = panel_layer("B")
layers["3_panel_A_only"] = imgA
layers["4_panel_B_only"] = imgB

for name, img in layers.items():
    out = img.copy()
    cv2.imwrite(f"{OUT}/{name}.jpg", out, [cv2.IMWRITE_JPEG_QUALITY, 95])

# ink census inside the window, to answer "who draws the tracks" numerically
def ink_frac(bgr, mask=None):
    g = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    ink = (g < 140)
    if mask is not None:
        ink &= mask
        n = max(mask.sum(), 1)
    else:
        n = ink.size
    return float(ink.sum()) / n

print(f"window canvas x{X0}-{X1} y{Y0}-{Y1} ({W}x{H})")
print(f"  current master   ink {ink_frac(layers['1_current_master']):.4f}")
print(f"  block-only       ink {ink_frac(layers['2_block_only']):.4f}")
print(f"  panel A (in mask) ink {ink_frac(imgA, mA):.4f}   coverage {mA.mean():.3f}")
print(f"  panel B (in mask) ink {ink_frac(imgB, mB):.4f}   coverage {mB.mean():.3f}")
print(f"wrote layers to {OUT}")
