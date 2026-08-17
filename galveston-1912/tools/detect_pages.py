"""Detect the physical page and its scan skew for each 1912 plate.

The scans place the sheet on a dark gridded backdrop, so the page is found as
the dominant bright region rather than by any blank-paper heuristic. A rotated
minimum-area rectangle gives both the page quadrilateral and the per-sheet skew
angle -- evidence that each plate carries its own rotation, which is why the
fit must leave rotation free per sheet rather than assuming a common frame.

Non-destructive: originals are opened read-only; results are geometry only.
"""

import json
import os

import cv2
import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None

INV = "/home/user/claude-code/galveston-1912/00_inventory/INVENTORY.json"
OUT_DIR = "/home/user/claude-code/galveston-1912/20_plates"
os.makedirs(OUT_DIR, exist_ok=True)
PREVIEW = "/home/user/g1912/work/plates"
os.makedirs(PREVIEW, exist_ok=True)

DS = 8  # analysis downsample factor

inv = json.load(open(INV))
results = []

for it in inv["items"]:
    sheet, path = it["sheet"], it["path"]
    im = Image.open(path).convert("RGB")
    W, H = im.size
    small = im.resize((W // DS, H // DS), Image.LANCZOS)
    a = np.asarray(small)
    g = cv2.cvtColor(a, cv2.COLOR_RGB2GRAY)

    # Page = bright region. Otsu separates cream paper from the dark backdrop.
    thr, mask = cv2.threshold(g, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((9, 9), np.uint8))

    n, lab, stats, _ = cv2.connectedComponentsWithStats(mask, 8)
    if n < 2:
        raise SystemExit(f"sheet {sheet}: no page component found")
    k = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    page = (lab == k).astype(np.uint8)

    cnts, _ = cv2.findContours(page, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    c = max(cnts, key=cv2.contourArea)
    rect = cv2.minAreaRect(c)  # ((cx,cy),(w,h),angle) in downsampled px
    (cx, cy), (rw, rh), ang = rect
    box = cv2.boxPoints(rect)

    # Normalise the angle to a small signed skew about 0
    skew = ang if abs(ang) <= 45 else (ang - 90 if ang > 0 else ang + 90)
    if rw < rh:
        # portrait: minAreaRect may report the long side first
        pass

    page_area_frac = float(page.sum()) / page.size
    rect_fill = float(cv2.contourArea(c)) / max(rw * rh, 1)

    res = {
        "sheet": sheet,
        "image_size": [W, H],
        "otsu_threshold": float(thr),
        "page_center_fullres": [round(cx * DS, 1), round(cy * DS, 1)],
        "page_size_fullres": [round(rw * DS, 1), round(rh * DS, 1)],
        "page_skew_deg": round(float(skew), 4),
        "page_quad_fullres": [[round(float(x) * DS, 1), round(float(y) * DS, 1)] for x, y in box],
        "page_area_fraction": round(page_area_frac, 4),
        "rect_fill_ratio": round(rect_fill, 4),
    }
    results.append(res)
    print(
        f"sheet {sheet:3d}: page {rw*DS:6.0f}x{rh*DS:6.0f} px  skew {skew:+6.3f} deg  "
        f"area {page_area_frac:.3f}  fill {rect_fill:.3f}"
    )

    # preview with the detected page outline
    vis = a.copy()
    cv2.drawContours(vis, [box.astype(int)], -1, (255, 0, 0), 3)
    Image.fromarray(vis).save(f"{PREVIEW}/sheet{sheet:02d}_page.jpg", quality=85)

with open(f"{OUT_DIR}/plate_structure.json", "w") as fh:
    json.dump(
        {"downsample": DS, "method": "otsu bright-region + minAreaRect", "plates": results},
        fh,
        indent=1,
    )

sk = [r["page_skew_deg"] for r in results]
print(f"\nskew: min {min(sk):+.3f}  max {max(sk):+.3f}  spread {max(sk)-min(sk):.3f} deg")
print(f"wrote {OUT_DIR}/plate_structure.json")
