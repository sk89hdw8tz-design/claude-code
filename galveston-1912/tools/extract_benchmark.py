"""Extract the 1899 reference image losslessly from the supplied PDF.

Copies the raw DCTDecode (JPEG) stream out of the PDF without re-encoding, so
the benchmark we measure against is bit-identical to what the PDF carries.
"""

import hashlib
import json
import os

import pymupdf
from PIL import Image

Image.MAX_IMAGE_PIXELS = None

SRC = (
    "/root/.claude/uploads/3107d3d8-6779-530e-9ae5-ba7b48239c4e/"
    "dd1e1a53-Galveston_1899_Wharf_Downtown_print_81020261.pdf"
)
OUT_DIR = "/home/user/g1912/benchmark"
os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs("/home/user/g1912/work", exist_ok=True)

doc = pymupdf.open(SRC)
imgs = doc.get_page_images(0)
print("pages:", doc.page_count, "images on page 1:", len(imgs))

xref = imgs[0][0]
raw = doc.xref_stream_raw(xref)
out = os.path.join(OUT_DIR, "galveston_1899_print_master.jpg")
with open(out, "wb") as fh:
    fh.write(raw)

sha = hashlib.sha256(raw).hexdigest()
im = Image.open(out)
print(f"wrote {out}: {len(raw)} bytes, {im.format} {im.size} {im.mode}, sha256 {sha[:16]}")

page = doc[0]
rect = page.rect
meta = {
    "source_pdf": SRC,
    "extraction": "raw DCTDecode stream copied without re-encoding",
    "pixels": list(im.size),
    "page_points": [rect.width, rect.height],
    "print_inches": [round(rect.width / 72, 3), round(rect.height / 72, 3)],
    "dpi": [
        round(im.size[0] / (rect.width / 72), 2),
        round(im.size[1] / (rect.height / 72), 2),
    ],
    "megapixels": round(im.size[0] * im.size[1] / 1e6, 1),
    "mode": im.mode,
    "sha256": sha,
}
with open(os.path.join(OUT_DIR, "benchmark_meta.json"), "w") as fh:
    json.dump(meta, fh, indent=1)
print(json.dumps(meta, indent=1))
