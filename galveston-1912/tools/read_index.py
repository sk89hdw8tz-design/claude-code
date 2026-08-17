"""Crop the archival street index so street->sheet assignments can be verified.

Independent cross-check on the key-map reading: the index lists each street with
address ranges and the sheet number carrying that range.
"""

from PIL import Image

Image.MAX_IMAGE_PIXELS = None
SRC = "/home/user/g1912/data-branch/galveston_1912_sources/sanborn08539_004_img001_archival.jp2"
OUT = "/home/user/g1912/work/"

im = Image.open(SRC).convert("RGB")
print("index archival:", im.size)
W, H = im.size

# The index is a dense multi-column table. Cut it into readable vertical slabs.
cols = {
    "idx_col1": (0.06, 0.05, 0.20, 0.62),  # Avenue A ... Avenue K
    "idx_col2": (0.19, 0.05, 0.33, 0.62),  # Avenue K ... B/Broadway/Center
    "idx_col5": (0.47, 0.05, 0.62, 0.62),  # S: Seawall/Strand region
}
for name, (l, t, r, b) in cols.items():
    box = (int(W * l), int(H * t), int(W * r), int(H * b))
    c = im.crop(box)
    tw = 1500
    if c.width > tw:
        c = c.resize((tw, int(c.height * tw / c.width)), Image.LANCZOS)
    c.save(OUT + name + ".jpg", quality=95)
    print(f"{name}: {box} -> {c.size}")
