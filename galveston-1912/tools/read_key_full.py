"""Decode the archival key map and cut high-zoom crops over the target extent."""

from PIL import Image

Image.MAX_IMAGE_PIXELS = None
SRC = "/home/user/g1912/data-branch/galveston_1912_sources/sanborn08539_004_img004_archival.jp2"
OUT = "/home/user/g1912/work/"

k = Image.open(SRC)
print("key archival:", k.size, k.mode)
k = k.convert("RGB")

# Same fractional windows as the thumbnail reads, now at 4x the detail.
regions = {
    # bay strip + Avenue A-F, 17th-27th: sheets 5,7,8,9,10,11,12
    "keyfull_wharf_downtown": (0.10, 0.30, 0.40, 0.62),
    # inland Avenue F-K, 18th-27th: sheets 39,40,43,44,49,50
    "keyfull_inland": (0.30, 0.30, 0.62, 0.62),
}
for name, (l, t, r, b) in regions.items():
    box = (int(k.width * l), int(k.height * t), int(k.width * r), int(k.height * b))
    c = k.crop(box)
    # downsample to a readable but detailed size
    target_w = 2400
    if c.width > target_w:
        c = c.resize((target_w, int(c.height * target_w / c.width)), Image.LANCZOS)
    c.save(OUT + name + ".jpg", quality=94)
    print(f"{name}: {box} -> {c.size}")
