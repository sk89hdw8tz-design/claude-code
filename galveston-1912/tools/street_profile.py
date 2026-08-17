"""Locate cross-street bands and the mapped-content limit near a shared edge.

For a pair sharing an avenue, the questions that decide the control strategy are:
  (a) where do the cross streets cross the shared avenue (the along-seam anchors), and
  (b) how far does each plate's drafted content actually extend toward the seam?

Both are answered from ink density rather than from any assumption about margins.
Paper is isolated from the scans' dark backdrop first (see FAILED_EXPERIMENTS F-001).
"""

import json
import sys

import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None

inv = json.load(open("/home/user/claude-code/galveston-1912/00_inventory/INVENTORY.json"))
by = {i["sheet"]: i for i in inv["items"]}
sheet = int(sys.argv[1])
side = sys.argv[2] if len(sys.argv) > 2 else "right"

im = Image.open(by[sheet]["path"]).convert("L")
W, H = im.size
DS = 4
small = np.asarray(im.resize((W // DS, H // DS), Image.LANCZOS), dtype=np.uint8)
h, w = small.shape

# paper = bright; backdrop = dark. Take paper as > 140 to exclude the surround.
paper = small > 140
# ink = markedly darker than local paper, but still on paper
ink = (small < 165) & (small > 40)

# --- (b) content extent across the page, measured column by column ----------
col_ink = (ink & paper).sum(axis=0) / np.maximum(paper.sum(axis=0), 1)
# smooth
k = np.ones(9) / 9
col_s = np.convolve(col_ink, k, mode="same")
thr = 0.012
cols = np.where(col_s > thr)[0]
content_x = (int(cols[0]) * DS, int(cols[-1]) * DS) if len(cols) else None

# --- (a) cross-street bands: rows with little ink over the built-up columns --
if side == "right":
    band = slice(int(w * 0.55), int(w * 0.88))
else:
    band = slice(int(w * 0.12), int(w * 0.45))
row_ink = (ink & paper)[:, band].sum(axis=1) / max((paper[:, band]).sum(axis=1).max(), 1)
row_s = np.convolve(row_ink, np.ones(7) / 7, mode="same")

# streets are sustained low-ink runs inside the content area
lo = row_s < (0.25 * row_s[row_s > 0].mean() if (row_s > 0).any() else 0.01)
runs, start = [], None
for i, v in enumerate(lo):
    if v and start is None:
        start = i
    elif not v and start is not None:
        if i - start >= 12:  # >= ~48 px full-res: a real street, not a gap
            runs.append((start * DS, i * DS))
        start = None
if start is not None and len(lo) - start >= 12:
    runs.append((start * DS, len(lo) * DS))

print(f"sheet {sheet} ({side} side), image {W}x{H}")
print(f"  drafted content spans x = {content_x}  (page width {W})")
if content_x:
    print(f"  margin beyond content: left {content_x[0]} px, right {W - content_x[1]} px")
print(f"  candidate cross-street bands (y ranges, full-res):")
for a, b in runs:
    print(f"    {a:5d} - {b:5d}   height {b-a:4d} px   centre y/H = {(a+b)/2/H:.3f}")
