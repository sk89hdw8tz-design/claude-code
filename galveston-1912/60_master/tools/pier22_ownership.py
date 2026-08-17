"""Empirical source-ownership map for the Sheet 5 / Pier 22 rail-fan window.

Rather than reasoning about what the compositor *should* have done, this reads
the delivered master and asks, per pixel, which candidate source it actually
equals. That converts "who owns this grey blob?" from an inference into a
measurement, which is what the repair brief requires before anything is changed.

Sources compared: block-only master (candidate_master.tif), sheet-5 panel A,
sheet-5 panel B. Anything matching none of them is reported as UNMATCHED, which
would itself be a finding.
"""

import json
import os

import cv2
import numpy as np
import tifffile
from PIL import Image

Image.MAX_IMAGE_PIXELS = None

G = "/home/user/claude-code/galveston-1912"
SCAN = ("/home/user/g1912/data-branch/galveston_1912_sources/"
        "sanborn08539_004_img009_archival.jp2")
OUT = "/home/user/g1912/work/pier22"
os.makedirs(OUT, exist_ok=True)

X0, Y0, X1, Y1 = 7400, 7100, 9300, 9400
W, H = X1 - X0, Y1 - Y0
CX0, CY0 = -16734, -8279

tf = json.load(open(f"{G}/40_solve/output_sheet5_joint/"
                    "transforms_sheet5_joint_shared.json"))["panels"]
geo = json.load(open(f"{G}/fable_review/sheet05_candidate_regions.geojson"))
feats = {f["properties"].get("region_id"): f for f in geo["features"]}

scan = cv2.imread(SCAN, cv2.IMREAD_COLOR)
SH, SW = scan.shape[:2]


def panel_layer(rid):
    key = "5A" if "A" in rid else "5B"
    r = tf[key]["raw"]
    M = np.array([[r["a"], -r["b"], r["tx"] - CX0 - X0],
                  [r["b"], r["a"], r["ty"] - CY0 - Y0]], np.float64)
    ring = np.array(feats[rid]["geometry"]["coordinates"][0], np.float64)
    ms = np.zeros((SH, SW), np.uint8)
    cv2.fillPoly(ms, [np.round(ring).astype(np.int32)], 255)
    img = cv2.warpAffine(scan, M, (W, H), flags=cv2.INTER_LANCZOS4,
                         borderMode=cv2.BORDER_CONSTANT, borderValue=(255, 255, 255))
    msk = cv2.warpAffine(ms, M, (W, H), flags=cv2.INTER_NEAREST,
                         borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    return img, msk > 0


def crop_master(path):
    m = tifffile.imread(path)
    out = np.ascontiguousarray(m[Y0:Y1, X0:X1])
    del m
    return out[:, :, ::-1]


master = crop_master(f"{G}/60_master/final/master_full.tif")
block = crop_master(f"{G}/60_master/final/candidate_master.tif")
imgA, mA = panel_layer("A")
imgB, mB = panel_layer("B")

cv2.imwrite(f"{OUT}/w_master.jpg", master, [cv2.IMWRITE_JPEG_QUALITY, 95])
cv2.imwrite(f"{OUT}/w_block.jpg", block, [cv2.IMWRITE_JPEG_QUALITY, 95])
cv2.imwrite(f"{OUT}/w_panelA.jpg", imgA, [cv2.IMWRITE_JPEG_QUALITY, 95])
cv2.imwrite(f"{OUT}/w_panelB.jpg", imgB, [cv2.IMWRITE_JPEG_QUALITY, 95])

mf = master.astype(np.int16)
cands = [("block", block, np.ones((H, W), bool)),
         ("A", imgA, mA),
         ("B", imgB, mB)]
d = np.full((len(cands), H, W), 1e4, np.float32)
for i, (nm, im, mk) in enumerate(cands):
    dd = np.abs(im.astype(np.int16) - mf).max(axis=2).astype(np.float32)
    dd[~mk] = 1e4
    d[i] = dd

best = np.argmin(d, axis=0)
bestd = d.min(axis=0)
TOL = 6
own = np.where(bestd <= TOL, best, 3).astype(np.uint8)     # 3 = UNMATCHED

names = ["block", "panelA", "panelB", "UNMATCHED"]
cols = np.array([[90, 160, 90], [40, 40, 230], [230, 160, 40], [30, 30, 30]], np.uint8)
vis = cols[own]
blend = (0.55 * vis + 0.45 * master).astype(np.uint8)
cv2.imwrite(f"{OUT}/w_ownership.png", vis)
cv2.imwrite(f"{OUT}/w_ownership_blend.jpg", blend, [cv2.IMWRITE_JPEG_QUALITY, 95])

print(f"window canvas x{X0}-{X1} y{Y0}-{Y1}  ({W}x{H} = {W*H:,} px)")
for i, nm in enumerate(names):
    frac = float((own == i).mean())
    print(f"  {nm:10s} {frac*100:6.2f}%")

# where does each source's ownership live, in x?
for i, nm in enumerate(names[:3]):
    m_ = own == i
    if m_.any():
        xs = np.where(m_.any(axis=0))[0]
        ys = np.where(m_.any(axis=1))[0]
        print(f"  {nm:10s} canvas x {X0+xs.min()}..{X0+xs.max()}  "
              f"y {Y0+ys.min()}..{Y0+ys.max()}")

# ink comparison restricted to the disputed strip
def ink(bgr, mk=None):
    g = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    k = g < 140
    if mk is not None:
        k &= mk
        n = max(int(mk.sum()), 1)
    else:
        n = k.size
    return float(k.sum()) / n

strip = np.zeros((H, W), bool)
strip[:, (7900 - X0):(8600 - X0)] = True
strip[:(7300 - Y0)] = False
strip[(9000 - Y0):] = False
print("\ndisputed strip canvas x7900-8600 y7300-9000:")
print(f"  master ink {ink(master, strip):.4f}")
print(f"  block  ink {ink(block, strip):.4f}")
print(f"  A      ink {ink(imgA, strip & mA):.4f}  cover {float((strip & mA).sum())/strip.sum():.3f}")
print(f"  B      ink {ink(imgB, strip & mB):.4f}  cover {float((strip & mB).sum())/strip.sum():.3f}")
print(f"wrote {OUT}/w_ownership.png")
