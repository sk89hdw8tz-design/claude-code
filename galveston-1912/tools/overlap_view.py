"""Place two adjacent plates' shared-edge strips side by side.

For a vertical seam (shared avenue) the left sheet's right strip and the right
sheet's left strip depict the same ground, so butting them together shows what
geometry the pair genuinely has in common -- the basis for choosing controls.

Usage: overlap_view.py LEFT_SHEET RIGHT_SHEET [strip_fraction]
"""

import json
import sys

from PIL import Image, ImageDraw

Image.MAX_IMAGE_PIXELS = None

inv = json.load(open("/home/user/claude-code/galveston-1912/00_inventory/INVENTORY.json"))
by = {i["sheet"]: i for i in inv["items"]}

a_sheet = int(sys.argv[1])
b_sheet = int(sys.argv[2])
frac = float(sys.argv[3]) if len(sys.argv) > 3 else 0.16

a = Image.open(by[a_sheet]["path"]).convert("RGB")
b = Image.open(by[b_sheet]["path"]).convert("RGB")
AW, AH = a.size
BW, BH = b.size

a_strip = a.crop((int(AW * (1 - frac)), 0, AW, AH))  # left sheet's right edge
b_strip = b.crop((0, 0, int(BW * frac), BH))         # right sheet's left edge

TH = 1900  # display height
def fit(im):
    return im.resize((max(1, int(im.width * TH / im.height)), TH), Image.LANCZOS)

a_s, b_s = fit(a_strip), fit(b_strip)
gap = 14
canvas = Image.new("RGB", (a_s.width + gap + b_s.width, TH + 26), "white")
d = ImageDraw.Draw(canvas)
canvas.paste(a_s, (0, 26))
canvas.paste(b_s, (a_s.width + gap, 26))
d.text((4, 6), f"sheet {a_sheet} — right {frac:.0%} strip", fill="black")
d.text((a_s.width + gap + 4, 6), f"sheet {b_sheet} — left {frac:.0%} strip", fill="black")

out = f"/home/user/g1912/work/overlap_{a_sheet}_{b_sheet}.jpg"
canvas.save(out, quality=93)
print(f"wrote {out} {canvas.size}")
