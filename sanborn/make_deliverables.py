"""Phase E — generate the full 1885 format matrix from the composite.

Outputs into deliver/1885/:
  galveston_1885_composite.tif        (LZW TIFF master; split if > 450 MB)
  galveston_1885_full.jpg             (q90 one-file archive)
  tiles/galveston_1885_r{J}c{I}.jpg   (~45 MP, 400 px overlap, q93, 4:4:4)
  tiles/galveston_1885_index.jpg      (annotated tile index map)
  galveston_1885_atlas.pdf            (img2pdf lossless embed, 300 dpi pages)
  MANIFEST.txt                        (sha256 + byte size of every file)

No resampling anywhere: tiles and JPEG reuse native composite pixels.
Usage: python3 make_deliverables.py 1885
"""

import hashlib
import os
import shutil
import sys

os.environ.setdefault("OPENCV_IO_MAX_IMAGE_PIXELS", str(2**40))
import cv2

import config
import output as out


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    year = sys.argv[1] if len(sys.argv) > 1 else "1885"
    src = os.path.join(config.BUILD_DIR, year, f"galveston_{year}_composite.tif")
    ddir = os.path.join(config.DELIVER_DIR, year)
    os.makedirs(ddir, exist_ok=True)

    canvas = cv2.imread(src, cv2.IMREAD_COLOR)
    h, w = canvas.shape[:2]
    print(f"[deliver] composite {w}x{h} ({w*h/1e6:.0f} MP)", flush=True)

    # 1. TIFF master (copy of the build output; split for delivery if large)
    tif = os.path.join(ddir, f"galveston_{year}_composite.tif")
    shutil.copy2(src, tif)
    tif_parts = out.split_if_large(tif)
    print(f"[deliver] TIFF master: {len(tif_parts)} file(s)", flush=True)

    # 2. Full JPEG
    jpg = out.save_full_jpeg(canvas, os.path.join(ddir, f"galveston_{year}_full.jpg"))
    print(f"[deliver] full JPEG {os.path.getsize(jpg)>>20} MB", flush=True)

    # 3. Tile set + index map
    tdir = os.path.join(ddir, "tiles")
    tiles, index = out.write_tiles(canvas, tdir, f"galveston_{year}")
    print(f"[deliver] {len(tiles)} tiles + index map", flush=True)

    # 4. PDF atlas (lossless embed of the tiles + index)
    pdf = out.make_pdf_atlas(tiles, index, os.path.join(ddir, f"galveston_{year}_atlas.pdf"))
    print(f"[deliver] atlas PDF {os.path.getsize(pdf)>>20} MB", flush=True)

    # 5. Manifest
    files = []
    for root, _, names in os.walk(ddir):
        for n in sorted(names):
            if n == "MANIFEST.txt":
                continue
            p = os.path.join(root, n)
            files.append((os.path.relpath(p, ddir), os.path.getsize(p), sha256(p)))
    with open(os.path.join(ddir, "MANIFEST.txt"), "w") as f:
        for rel, size, digest in files:
            f.write(f"{digest}  {size:>12}  {rel}\n")
    print(f"[deliver] manifest: {len(files)} files", flush=True)
    for rel, size, _ in files:
        print(f"  {size>>20:>5} MB  {rel}", flush=True)


if __name__ == "__main__":
    main()
