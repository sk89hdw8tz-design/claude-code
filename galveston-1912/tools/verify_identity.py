"""Montage the printed sheet number from each plate's top-left corner.

The LOC page-id mapping says which sheet each file is; the number engraved on
the plate is the independent witness. Any disagreement means the volume index
is mis-mapped and every downstream step would be built on the wrong plates.
"""

import json

from PIL import Image, ImageDraw

Image.MAX_IMAGE_PIXELS = None

inv = json.load(open("/home/user/claude-code/galveston-1912/00_inventory/INVENTORY.json"))
items = inv["items"]

CW, CH = 430, 300  # corner crop size after scaling
cols, rows = 5, 3
pad, label_h = 8, 26
sheet_w = CW + pad * 2
sheet_h = CH + label_h + pad

canvas = Image.new("RGB", (cols * sheet_w, rows * sheet_h), "white")
draw = ImageDraw.Draw(canvas)

for n, it in enumerate(items):
    im = Image.open(it["path"]).convert("RGB")
    W, H = im.size
    # top-left corner of the plate, where Sanborn prints the sheet number
    crop = im.crop((0, 0, int(W * 0.16), int(H * 0.09)))
    crop = crop.resize((CW, CH), Image.LANCZOS)
    cx = (n % cols) * sheet_w + pad
    cy = (n // cols) * sheet_h + label_h
    canvas.paste(crop, (cx, cy))
    draw.text((cx, cy - 18), f"file says sheet {it['sheet']}", fill="black")

canvas.save("/home/user/g1912/work/identity_montage.jpg", quality=94)
print("wrote identity montage:", canvas.size, f"({len(items)} plates)")
