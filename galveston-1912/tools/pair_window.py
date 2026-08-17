"""Native-resolution windows on the same ground from two adjacent plates.

Both crops are taken from the archival originals at 1:1 -- no resampling -- so
what is compared is the drafted ink itself, not an interpolation of it.

Usage: pair_window.py A_SHEET B_SHEET Y_FRAC [half_height_px] [strip_px]
  Y_FRAC   vertical position of the feature, as a fraction of page height
  strip_px how far in from each shared edge to take
"""

import json
import sys

from PIL import Image, ImageDraw

Image.MAX_IMAGE_PIXELS = None

inv = json.load(open("/home/user/claude-code/galveston-1912/00_inventory/INVENTORY.json"))
by = {i["sheet"]: i for i in inv["items"]}

a_sheet, b_sheet = int(sys.argv[1]), int(sys.argv[2])
yf = float(sys.argv[3])
half = int(sys.argv[4]) if len(sys.argv) > 4 else 700
strip = int(sys.argv[5]) if len(sys.argv) > 5 else 1100

a = Image.open(by[a_sheet]["path"]).convert("RGB")
b = Image.open(by[b_sheet]["path"]).convert("RGB")

ay = int(a.height * yf)
by_ = int(b.height * yf)
a_crop = a.crop((a.width - strip, max(0, ay - half), a.width, min(a.height, ay + half)))
b_crop = b.crop((0, max(0, by_ - half), strip, min(b.height, by_ + half)))

gap = 16
canvas = Image.new("RGB", (a_crop.width + gap + b_crop.width, max(a_crop.height, b_crop.height) + 26), "white")
d = ImageDraw.Draw(canvas)
canvas.paste(a_crop, (0, 26))
canvas.paste(b_crop, (a_crop.width + gap, 26))
d.text((4, 6), f"sheet {a_sheet} right edge (1:1)", fill="black")
d.text((a_crop.width + gap + 4, 6), f"sheet {b_sheet} left edge (1:1)", fill="black")

out = f"/home/user/g1912/work/window_{a_sheet}_{b_sheet}_y{int(yf*100)}.jpg"
canvas.save(out, quality=95)
print(f"wrote {out} {canvas.size}")
