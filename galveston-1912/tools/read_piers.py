from PIL import Image

Image.MAX_IMAGE_PIXELS = None
SRC = "/home/user/g1912/data-branch/galveston_1912_sources/sanborn08539_004_img001_archival.jp2"
im = Image.open(SRC).convert("RGB")
W, H = im.size
# "PIERS." block sits at the foot of the last (right-most) index column
box = (int(W * 0.855), int(H * 0.80), int(W * 0.99), int(H * 0.98))
c = im.crop(box)
c = c.resize((c.width * 2, c.height * 2), Image.LANCZOS)
c.save("/home/user/g1912/work/idx_piers.jpg", quality=95)
print(box, "->", c.size)
