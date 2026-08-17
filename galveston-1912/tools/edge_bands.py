"""Montage each plate's four edge bands, where adjoining-sheet numbers are printed.

Sanborn prints the neighbouring sheet's number centred on each edge of the map
body ("reference to adjoining sheet" in the key's legend). Reading those gives
the adjacency graph from the plates themselves -- a source independent of both
the key map and the street index.
"""

import json
import os
import sys

from PIL import Image, ImageDraw

Image.MAX_IMAGE_PIXELS = None

INV = "/home/user/claude-code/galveston-1912/00_inventory/INVENTORY.json"
OUT = "/home/user/g1912/work/edges"
os.makedirs(OUT, exist_ok=True)

inv = json.load(open(INV))
by_sheet = {i["sheet"]: i for i in inv["items"]}
sheets = [int(s) for s in sys.argv[1:]] or [i["sheet"] for i in inv["items"]]

BAND = 0.085  # fraction of the page taken as an edge band
TW = 1700     # montage width


def band_imgs(im):
    W, H = im.size
    return {
        "top": im.crop((0, 0, W, int(H * BAND))),
        "bottom": im.crop((0, int(H * (1 - BAND)), W, H)),
        "left": im.crop((0, 0, int(W * BAND), H)).transpose(Image.ROTATE_270),
        "right": im.crop((int(W * (1 - BAND)), 0, W, H)).transpose(Image.ROTATE_90),
    }


for sheet in sheets:
    im = Image.open(by_sheet[sheet]["path"]).convert("RGB")
    bands = band_imgs(im)
    scaled = []
    for name in ("top", "bottom", "left", "right"):
        b = bands[name]
        b = b.resize((TW, max(1, int(b.height * TW / b.width))), Image.LANCZOS)
        scaled.append((name, b))

    total = sum(b.height + 26 for _, b in scaled)
    canvas = Image.new("RGB", (TW, total), "white")
    d = ImageDraw.Draw(canvas)
    y = 0
    for name, b in scaled:
        d.text((6, y + 6), f"sheet {sheet} — {name} edge", fill="black")
        canvas.paste(b, (0, y + 26))
        y += b.height + 26
    canvas.save(f"{OUT}/sheet{sheet:02d}_edges.jpg", quality=92)
    print(f"sheet {sheet}: {canvas.size}")
