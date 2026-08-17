"""Measure, for all four edges of every plate, the neatline position and the
blank street band inside it.

Every seam in this edition abuts (the index splits boundary streets with its
"only one side of street shown" mark and shows interior streets whole). So the
question that sets the seam network is: how much of the shared street does each
plate actually draw? If each draws about half, the plates tile edge-to-edge; if
each draws the full width, they overlap by a street and the cut has a choice.

Measured from ink, not assumed. Paper is separated from the scans' dark backdrop
first (see FAILED_EXPERIMENTS F-001).
"""

import json

import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None

INV = "/home/user/claude-code/galveston-1912/00_inventory/INVENTORY.json"
OUT = "/home/user/claude-code/galveston-1912/20_plates/edge_margins.json"
DEFERRED = {5}
DS = 2

inv = json.load(open(INV))
rows = {}

for it in inv["items"]:
    sheet = it["sheet"]
    if sheet in DEFERRED:
        continue
    im = Image.open(it["path"]).convert("L")
    W, H = im.size
    a = np.asarray(im.resize((W // DS, H // DS), Image.LANCZOS), dtype=np.uint8)
    h, w = a.shape

    paper = a > 140
    ink = (a < 165) & (a > 40)
    both = ink & paper

    # profiles across each axis, restricted to the paper
    col = both.sum(axis=0) / np.maximum(paper.sum(axis=0), 1)
    row = both.sum(axis=1) / np.maximum(paper.sum(axis=1), 1)
    col = np.convolve(col, np.ones(5) / 5, mode="same")
    row = np.convolve(row, np.ones(5) / 5, mode="same")

    def analyse(prof, n):
        """Return (neatline_index, first_dense_index) scanning inward from 0."""
        # neatline: first strong, narrow spike near the edge
        lim = int(n * 0.10)
        seg = prof[:lim]
        neat = int(np.argmax(seg)) if seg.size else 0
        # first sustained drafted content beyond the neatline
        thr = max(0.035, float(np.percentile(prof, 60)))
        idx = None
        run = 0
        for i in range(neat + 4, n):
            if prof[i] > thr:
                run += 1
                if run >= 6:
                    idx = i - run + 1
                    break
            else:
                run = 0
        return neat, idx

    lo_n, lo_c = analyse(col, w)
    hi_n, hi_c = analyse(col[::-1], w)
    tp_n, tp_c = analyse(row, h)
    bt_n, bt_c = analyse(row[::-1], h)

    def px(v):
        return None if v is None else int(v * DS)

    rows[sheet] = {
        "sheet": sheet,
        "image_size": [W, H],
        "left":   {"neatline_px": px(lo_n), "first_content_px": px(lo_c),
                   "blank_band_px": None if lo_c is None else px(lo_c - lo_n)},
        "right":  {"neatline_px": px(hi_n), "first_content_px": px(hi_c),
                   "blank_band_px": None if hi_c is None else px(hi_c - hi_n)},
        "top":    {"neatline_px": px(tp_n), "first_content_px": px(tp_c),
                   "blank_band_px": None if tp_c is None else px(tp_c - tp_n)},
        "bottom": {"neatline_px": px(bt_n), "first_content_px": px(bt_c),
                   "blank_band_px": None if bt_c is None else px(bt_c - bt_n)},
    }
    r = rows[sheet]
    print(
        f"sheet {sheet:3d}  blank band px  L {str(r['left']['blank_band_px']):>5}"
        f"  R {str(r['right']['blank_band_px']):>5}"
        f"  T {str(r['top']['blank_band_px']):>5}"
        f"  B {str(r['bottom']['blank_band_px']):>5}"
    )

with open(OUT, "w") as fh:
    json.dump({"downsample": DS, "deferred": sorted(DEFERRED), "plates": rows}, fh, indent=1)

for side in ("left", "right", "top", "bottom"):
    vals = [r[side]["blank_band_px"] for r in rows.values() if r[side]["blank_band_px"]]
    if vals:
        print(f"{side:6s} blank band: median {int(np.median(vals)):5d} px  "
              f"min {min(vals):5d}  max {max(vals):5d}  n={len(vals)}")
print(f"\nwrote {OUT}")
