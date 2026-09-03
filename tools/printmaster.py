#!/usr/bin/env python3
"""Print deliverables for a finished year: a detail-preserving wall master,
a single-sheet print at a named size, and a full-city preview.

    python3 tools/printmaster.py --year 1912 [--skip-render]

  outputs/<year>/print/<year>_wallmaster_<w>x<h>in_300ppi.tif   1/4 of the
      mosaic frame, deflate/predictor 2, tagged 300 ppi. The mosaic frame is
      ~300 ppi-equivalent at the plates' own scale (5.7966 px/ft), so this
      keeps one printed inch per 25.9 ft of ground and every line the scans
      carry at half the web tiles' reduction.
  outputs/<year>/print/<year>_sheet_<w>x<h>in_300ppi.{tif,pdf}  the whole
      city on one sheet whose long side is SHEET_IN inches at 300 ppi.
  outputs/<year>/preview/<year>_fullcity_preview.jpg            ~1/10, for
      screen review.

Nothing is resampled twice: each output is rendered from the recipe at its
own reduction (tools/render.py), so no output inherits another's blur.
"""
import argparse
import os
import subprocess
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHEET_IN = 40.0          # long side of the single-sheet print, inches at 300 ppi
PPF = 5.7966             # mosaic px per foot (300 ppi-equivalent at 100 ft/in... see units.json)


def run(cmd):
    print("+", " ".join(str(c) for c in cmd), flush=True)
    t = time.time()
    r = subprocess.run([str(c) for c in cmd], cwd=REPO)
    if r.returncode != 0:
        sys.exit(f"failed ({r.returncode}): {' '.join(str(c) for c in cmd)}")
    print(f"  [{time.time() - t:.0f}s]", flush=True)


def mb(p):
    return os.path.getsize(p) / 1e6


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", type=int, default=1912)
    ap.add_argument("--wall-downsample", type=int, default=4)
    ap.add_argument("--preview-downsample", type=int, default=10)
    ap.add_argument("--skip-render", action="store_true")
    a = ap.parse_args()
    y = a.year
    work = os.path.join(REPO, "work", "city")
    pdir = os.path.join(REPO, "outputs", str(y), "print")
    vdir = os.path.join(REPO, "outputs", str(y), "preview")
    for d in (work, pdir, vdir):
        os.makedirs(d, exist_ok=True)

    import numpy as np
    sys.path.insert(0, os.path.join(REPO, "tools"))
    from reciplib import Recipe
    r = Recipe(y)
    P = [p for _, p in r.ownership()]
    x0 = min(p[:, 0].min() for p in P); x1 = max(p[:, 0].max() for p in P)
    y0 = min(p[:, 1].min() for p in P); y1 = max(p[:, 1].max() for p in P)
    W, H = x1 - x0, y1 - y0
    print(f"mosaic extent {W:.0f} x {H:.0f} px ({W/PPF/5280:.2f} x {H/PPF/5280:.2f} miles)")

    # --- wall master: 1/wall-downsample, tagged 300 ppi
    d = a.wall_downsample
    wall_raw = os.path.join(work, f"{y}_wall_{d}.tif")
    if not (a.skip_render and os.path.exists(wall_raw)):
        run([sys.executable, "tools/render.py", "--year", y, "--all",
             "--downsample", d, "--ppi", 300, "--out", wall_raw])
    import pyvips
    im = pyvips.Image.new_from_file(wall_raw)
    win, hin = im.width / 300.0, im.height / 300.0
    wall = os.path.join(pdir, f"{y}_wallmaster_{win:.0f}x{hin:.0f}in_300ppi.tif")
    im.copy(xres=300 / 25.4, yres=300 / 25.4).tiffsave(
        wall, compression="deflate", predictor="horizontal", tile=True,
        tile_width=512, tile_height=512, bigtiff=True)
    print(f"wall master {im.width}x{im.height} = {win:.1f} x {hin:.1f} in at 300 ppi, {mb(wall):.0f} MB")

    # --- single sheet: long side SHEET_IN inches at 300 ppi
    target = SHEET_IN * 300
    ds = max(1, int(round(max(W, H) / target)))
    sheet_raw = os.path.join(work, f"{y}_sheet_{ds}.tif")
    if not (a.skip_render and os.path.exists(sheet_raw)):
        run([sys.executable, "tools/render.py", "--year", y, "--all",
             "--downsample", ds, "--ppi", 300, "--out", sheet_raw])
    im = pyvips.Image.new_from_file(sheet_raw)
    win, hin = im.width / 300.0, im.height / 300.0
    sheet = os.path.join(pdir, f"{y}_sheet_{win:.0f}x{hin:.0f}in_300ppi.tif")
    im.copy(xres=300 / 25.4, yres=300 / 25.4).tiffsave(
        sheet, compression="deflate", predictor="horizontal", tile=True,
        tile_width=512, tile_height=512, bigtiff=True)
    # img2pdf will not embed a tiled TIFF, so the PDF carries a q92 JPEG of
    # the same render at the same pixel size
    pdf = sheet.replace(".tif", ".pdf")
    jpg = os.path.join(work, f"{y}_sheet_{ds}.jpg")
    im.jpegsave(jpg, Q=92)
    run(["img2pdf", "--output", pdf, "--pagesize", f"{win:.2f}inx{hin:.2f}in", jpg])
    print(f"sheet {im.width}x{im.height} = {win:.1f} x {hin:.1f} in at 300 ppi, "
          f"{mb(sheet):.0f} MB tif, {mb(pdf):.0f} MB pdf")

    # --- preview
    dp = a.preview_downsample
    prev_raw = os.path.join(work, f"{y}_prev_{dp}.tif")
    if not (a.skip_render and os.path.exists(prev_raw)):
        run([sys.executable, "tools/render.py", "--year", y, "--all",
             "--downsample", dp, "--out", prev_raw])
    im = pyvips.Image.new_from_file(prev_raw)
    prev = os.path.join(vdir, f"{y}_fullcity_preview.jpg")
    im.jpegsave(prev, Q=88)
    print(f"preview {im.width}x{im.height}, {mb(prev):.0f} MB -> {prev}")


if __name__ == "__main__":
    main()
