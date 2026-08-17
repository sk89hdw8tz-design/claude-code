"""Measure each plate's drafted street-grid orientation.

Page-edge skew from minAreaRect proved useless (it snapped to exactly 0.000 on
11 of 13 plates -- a quantisation artefact, not a measurement). The meaningful
quantity is the orientation of the *drafted* map grid, since that is what has
to agree between neighbouring sheets once they are placed in a common plane.

Method: Canny + Hough line segments over the map body, pooled into a modulo-90
orientation histogram weighted by segment length. Reported per sheet with a
concentration figure so a weak or bimodal estimate cannot masquerade as a
confident one.
"""

import json
import os

import cv2
import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None

INV = "/home/user/claude-code/galveston-1912/00_inventory/INVENTORY.json"
OUT = "/home/user/claude-code/galveston-1912/20_plates"
os.makedirs(OUT, exist_ok=True)
DS = 4

inv = json.load(open(INV))
rows = []

for it in inv["items"]:
    sheet = it["sheet"]
    im = Image.open(it["path"]).convert("L")
    W, H = im.size
    small = im.resize((W // DS, H // DS), Image.LANCZOS)
    g = np.asarray(small)

    # restrict to the plate interior so page edges and backdrop cannot vote
    h, w = g.shape
    m = 0.10
    roi = g[int(h * m) : int(h * (1 - m)), int(w * m) : int(w * (1 - m))]

    edges = cv2.Canny(roi, 60, 160, apertureSize=3)
    segs = cv2.HoughLinesP(
        edges, 1, np.pi / 1800, threshold=80, minLineLength=90, maxLineGap=4
    )
    if segs is None:
        rows.append({"sheet": sheet, "grid_angle_deg": None, "note": "no segments"})
        print(f"sheet {sheet:3d}: NO SEGMENTS")
        continue

    segs = np.asarray(segs).reshape(-1, 4)
    dx = segs[:, 2] - segs[:, 0]
    dy = segs[:, 3] - segs[:, 1]
    length = np.hypot(dx, dy)
    ang = np.degrees(np.arctan2(dy, dx)) % 90.0  # street grid is orthogonal

    # circular-ish histogram on a 90-degree period, 0.1 deg bins
    bins = np.arange(0, 90.0 + 0.1, 0.1)
    hist, _ = np.histogram(ang, bins=bins, weights=length)
    # smooth so a single noisy bin cannot win
    kern = np.ones(5) / 5.0
    hs = np.convolve(np.r_[hist[-2:], hist, hist[:2]], kern, mode="same")[2:-2]
    peak = int(np.argmax(hs))

    # refine by length-weighted mean within +-1.5 deg of the peak (wrapped)
    centre = bins[peak] + 0.05
    d = (ang - centre + 45) % 90 - 45
    sel = np.abs(d) < 1.5
    refined = (centre + np.average(d[sel], weights=length[sel])) % 90 if sel.any() else centre

    concentration = float(length[sel].sum() / length.sum()) if sel.any() else 0.0
    # express as a signed deviation from the nearest axis
    dev = ((refined + 45) % 90) - 45

    rows.append(
        {
            "sheet": sheet,
            "grid_angle_mod90_deg": round(float(refined), 4),
            "grid_dev_from_axis_deg": round(float(dev), 4),
            "concentration": round(concentration, 4),
            "n_segments": int(len(segs)),
            "total_segment_px": round(float(length.sum()), 1),
        }
    )
    print(
        f"sheet {sheet:3d}: grid {refined:7.3f} deg (dev {dev:+.3f})  "
        f"conc {concentration:.3f}  n={len(segs)}"
    )

good = [r for r in rows if r.get("grid_dev_from_axis_deg") is not None]
devs = [r["grid_dev_from_axis_deg"] for r in good]
print(f"\ndeviation from axis: min {min(devs):+.3f}  max {max(devs):+.3f}  spread {max(devs)-min(devs):.3f} deg")
print(f"median concentration {np.median([r['concentration'] for r in good]):.3f}")

with open(f"{OUT}/grid_orientation.json", "w") as fh:
    json.dump(
        {
            "method": "Canny + HoughLinesP, length-weighted mod-90 orientation histogram",
            "downsample": DS,
            "roi_margin": 0.10,
            "plates": rows,
        },
        fh,
        indent=1,
    )
print(f"wrote {OUT}/grid_orientation.json")
