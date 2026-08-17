"""Crop the index's numbered-street entries (Twentieth .. Twenty-fifth).

The vertical seam avenues carry the index's '*' mark ("only one side of street
shown"), which is what told us those plates abut. The horizontal seams run along
21st (Center) and 24th St, so the same notation decides whether those pairs abut
or genuinely share both frontages -- without assuming the vertical result carries.
"""

import sys

from PIL import Image

Image.MAX_IMAGE_PIXELS = None
SRC = "/home/user/g1912/data-branch/galveston_1912_sources/sanborn08539_004_img001_archival.jp2"

im = Image.open(SRC).convert("RGB")
W, H = im.size

l = float(sys.argv[1]) if len(sys.argv) > 1 else 0.585
r = float(sys.argv[2]) if len(sys.argv) > 2 else 0.73
t = float(sys.argv[3]) if len(sys.argv) > 3 else 0.05
b = float(sys.argv[4]) if len(sys.argv) > 4 else 0.62

box = (int(W * l), int(H * t), int(W * r), int(H * b))
c = im.crop(box)
tw = 1450
c = c.resize((tw, int(c.height * tw / c.width)), Image.LANCZOS)
out = f"/home/user/g1912/work/idx_streets_{int(l*1000)}.jpg"
c.save(out, quality=95)
print(f"{box} -> {c.size}  {out}")
