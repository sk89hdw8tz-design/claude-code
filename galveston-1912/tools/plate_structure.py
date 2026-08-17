"""Plate-structure pass: verify sheet identity and locate the mapped area.

Two products per sheet:
  1. a corner crop at readable zoom, so the sheet number *printed on the plate*
     can be checked against the number the LOC page-id mapping claims -- this is
     the guard against a mis-mapped volume index;
  2. a downsampled full view plus an ink-coverage profile, which bounds the
     drawn map body inside the page (the basis for masks later, derived from
     content rather than from blank-paper guessing).
"""

import json
import os

import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None

INV = "/home/user/claude-code/galveston-1912/00_inventory/INVENTORY.json"
OUT = "/home/user/g1912/work/plates"
os.makedirs(OUT, exist_ok=True)

inv = json.load(open(INV))
report = []

for it in inv["items"]:
    sheet, path = it["sheet"], it["path"]
    im = Image.open(path).convert("RGB")
    W, H = im.size

    # 1. Sheet number is printed in the upper-right of the plate.
    cw, ch = int(W * 0.22), int(H * 0.10)
    corner = im.crop((W - cw, 0, W, ch))
    corner = corner.resize((corner.width // 2, corner.height // 2), Image.LANCZOS)
    corner.save(f"{OUT}/sheet{sheet:02d}_corner.jpg", quality=93)

    # 2. Downsampled overview
    ov = im.resize((W // 8, H // 8), Image.LANCZOS)
    ov.save(f"{OUT}/sheet{sheet:02d}_overview.jpg", quality=88)

    # 3. Ink profile -> bounding box of drawn content (map body + furniture)
    g = np.asarray(ov.convert("L"), dtype=np.float32)
    ink = g < 200  # anything appreciably darker than paper
    rows = ink.mean(axis=1)
    cols = ink.mean(axis=0)
    thr = 0.02
    ys = np.where(rows > thr)[0]
    xs = np.where(cols > thr)[0]
    bbox8 = (
        (int(xs[0]), int(ys[0]), int(xs[-1]) + 1, int(ys[-1]) + 1)
        if len(xs) and len(ys)
        else None
    )
    bbox = tuple(v * 8 for v in bbox8) if bbox8 else None

    report.append(
        {
            "sheet": sheet,
            "size": [W, H],
            "content_bbox_fullres": bbox,
            "content_frac": (
                [round(bbox[0] / W, 4), round(bbox[1] / H, 4),
                 round(bbox[2] / W, 4), round(bbox[3] / H, 4)]
                if bbox else None
            ),
            "ink_fraction": round(float(ink.mean()), 4),
        }
    )
    print(f"sheet {sheet:3d}: content bbox {bbox}  ink {ink.mean():.3f}")

with open(f"{OUT}/plate_structure.json", "w") as fh:
    json.dump(report, fh, indent=1)
print(f"\nwrote {OUT}/plate_structure.json")
