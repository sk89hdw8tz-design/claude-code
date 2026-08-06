"""Phase E — deliverable generation.

Format matrix (choose per the user's stated device — ASK FIRST):
- Native TIFF (LZW, 300 ppi) master; split -b 260m if > 450 MB.
- Full JPEG q90 one-file archive.
- Tile set ~45 MP each, 400 px overlap, q93, no chroma subsampling, plus an
  index map — the fix for the ~100 MP iOS decode ceiling.
- Multi-page PDF atlas via img2pdf (lossless JPEG embed, fixed 300 dpi).

Never resize an existing composite here: outputs either reuse native pixels
(crop/tile) or were composed at the right scale in Phase C.
"""

import math
import os
import subprocess

import numpy as np
import cv2

import config


def save_full_jpeg(canvas, path, quality=90):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not cv2.imwrite(path, canvas, [cv2.IMWRITE_JPEG_QUALITY, quality]):
        raise IOError(path)
    return path


def tile_grid(w, h, target_mp=45, overlap=400):
    """Tile origins/sizes covering (w,h) with ~target_mp tiles and overlap."""
    per_side = math.sqrt(target_mp * 1e6)
    nx = max(1, math.ceil((w - overlap) / (per_side - overlap)))
    ny = max(1, math.ceil((h - overlap) / (per_side - overlap)))
    tw = math.ceil((w + (nx - 1) * overlap) / nx)
    th = math.ceil((h + (ny - 1) * overlap) / ny)
    tiles = []
    for j in range(ny):
        for i in range(nx):
            x0 = min(i * (tw - overlap), w - tw) if nx > 1 else 0
            y0 = min(j * (th - overlap), h - th) if ny > 1 else 0
            tiles.append((i, j, max(0, x0), max(0, y0), min(tw, w), min(th, h)))
    return tiles, nx, ny


def write_tiles(canvas, outdir, name, quality=93):
    """JPEG tiles (no chroma subsampling) + a small annotated index map."""
    os.makedirs(outdir, exist_ok=True)
    h, w = canvas.shape[:2]
    tiles, nx, ny = tile_grid(w, h)
    paths = []
    for i, j, x0, y0, tw, th in tiles:
        p = os.path.join(outdir, f"{name}_r{j+1}c{i+1}.jpg")
        crop = canvas[y0 : y0 + th, x0 : x0 + tw]
        cv2.imwrite(
            p, crop,
            [cv2.IMWRITE_JPEG_QUALITY, quality, cv2.IMWRITE_JPEG_SAMPLING_FACTOR,
             cv2.IMWRITE_JPEG_SAMPLING_FACTOR_444],
        )
        paths.append(p)

    idx = cv2.resize(canvas, (1600, round(h * 1600 / w)), interpolation=cv2.INTER_AREA)
    sx, sy = 1600 / w, idx.shape[0] / h
    for i, j, x0, y0, tw, th in tiles:
        p1 = (round(x0 * sx), round(y0 * sy))
        p2 = (round((x0 + tw) * sx), round((y0 + th) * sy))
        cv2.rectangle(idx, p1, p2, (0, 0, 255), 3)
        cv2.putText(idx, f"r{j+1}c{i+1}", (p1[0] + 20, p1[1] + 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.6, (0, 0, 255), 4)
    ip = os.path.join(outdir, f"{name}_index.jpg")
    cv2.imwrite(ip, idx, [cv2.IMWRITE_JPEG_QUALITY, 90])
    return paths, ip


def make_pdf_atlas(jpeg_paths, index_path, out_pdf, dpi=300):
    """img2pdf embeds the JPEGs losslessly — no recompression."""
    import img2pdf

    layout = img2pdf.get_fixed_dpi_layout_fun((dpi, dpi))
    with open(out_pdf, "wb") as f:
        f.write(img2pdf.convert([index_path] + list(jpeg_paths), layout_fun=layout))
    return out_pdf


def split_if_large(path, limit_mb=450, chunk="260m"):
    """Anything over ~450 MB may be silently dropped in delivery — split and
    publish a SHA-256 so reassembly can be verified."""
    if os.path.getsize(path) <= limit_mb << 20:
        return [path]
    subprocess.run(["split", "-b", chunk, path, path + ".part-"], check=True)
    sha = subprocess.run(["sha256sum", path], capture_output=True, text=True).stdout
    with open(path + ".sha256", "w") as f:
        f.write(sha)
    parts = sorted(
        os.path.join(os.path.dirname(path), p)
        for p in os.listdir(os.path.dirname(path))
        if p.startswith(os.path.basename(path) + ".part-")
    )
    return parts + [path + ".sha256"]
