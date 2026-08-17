"""Tile the centre of every plate edge, where the adjoining-sheet number sits.

Produces one image: 13 plates x 4 edges. Reading it yields the adjacency graph
straight from the plates, independent of the key map and the street index.
"""

import json
import os

from PIL import Image, ImageDraw

Image.MAX_IMAGE_PIXELS = None

INV = "/home/user/claude-code/galveston-1912/00_inventory/INVENTORY.json"
OUT = "/home/user/g1912/work"
os.makedirs(OUT, exist_ok=True)

inv = json.load(open(INV))
items = inv["items"]

BAND = 0.075   # depth into the page
CENTRE = 0.34  # fraction of the long dimension kept, centred
CW, CH = 380, 150
pad, lab = 6, 20

canvas = Image.new("RGB", (4 * (CW + pad) + 60, len(items) * (CH + lab + pad)), "white")
d = ImageDraw.Draw(canvas)

for r, it in enumerate(items):
    im = Image.open(it["path"]).convert("RGB")
    W, H = im.size
    x0, x1 = int(W * (0.5 - CENTRE / 2)), int(W * (0.5 + CENTRE / 2))
    y0, y1 = int(H * (0.5 - CENTRE / 2)), int(H * (0.5 + CENTRE / 2))

    edges = {
        "top": im.crop((x0, 0, x1, int(H * BAND))),
        "bottom": im.crop((x0, int(H * (1 - BAND)), x1, H)),
        "left": im.crop((0, y0, int(W * BAND), y1)).transpose(Image.ROTATE_270),
        "right": im.crop((int(W * (1 - BAND)), y0, W, y1)).transpose(Image.ROTATE_90),
    }

    y = r * (CH + lab + pad)
    d.text((4, y + 4), f"sheet {it['sheet']}", fill="black")
    for c, name in enumerate(("top", "bottom", "left", "right")):
        e = edges[name].resize((CW, CH), Image.LANCZOS)
        x = 60 + c * (CW + pad)
        canvas.paste(e, (x, y + lab))
        d.text((x + 2, y + 4), name, fill="black")

canvas.save(f"{OUT}/adjacency_grid.jpg", quality=93)
print("wrote adjacency grid:", canvas.size)
