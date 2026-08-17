"""Read the full landward edge of the wharf strip (sheet 5).

Sheet 5 spans several street rows, so its landward edge carries more than one
adjoining-sheet reference. Sampling only the centre of that edge finds just one
and makes the adjacency look non-reciprocal.
"""

import json

from PIL import Image, ImageDraw

Image.MAX_IMAGE_PIXELS = None

inv = json.load(open("/home/user/claude-code/galveston-1912/00_inventory/INVENTORY.json"))
it = {i["sheet"]: i for i in inv["items"]}[5]
im = Image.open(it["path"]).convert("RGB")
W, H = im.size

strip = im.crop((int(W * 0.86), 0, W, H)).transpose(Image.ROTATE_90)
n = 3
seg_h = strip.height
parts = []
for k in range(n):
    x0 = int(strip.width * k / n)
    x1 = int(strip.width * (k + 1) / n)
    p = strip.crop((x0, 0, x1, seg_h))
    p = p.resize((1650, int(p.height * 1650 / p.width)), Image.LANCZOS)
    parts.append(p)

canvas = Image.new("RGB", (1650, sum(p.height + 24 for p in parts)), "white")
d = ImageDraw.Draw(canvas)
y = 0
for k, p in enumerate(parts):
    d.text((6, y + 5), f"sheet 5 landward edge, segment {k+1}/{n}", fill="black")
    canvas.paste(p, (0, y + 24))
    y += p.height + 24
canvas.save("/home/user/g1912/work/sheet05_landward_edge.jpg", quality=93)
print("wrote", canvas.size)
