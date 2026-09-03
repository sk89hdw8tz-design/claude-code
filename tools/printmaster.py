#!/usr/bin/env python3
"""Print deliverables for a finished year: a detail-preserving wall master,
a single-sheet print at a named size, and a full-city preview.

    python3 tools/printmaster.py --year 1912 [--skip-render]
    python3 tools/printmaster.py --year 1912 --tiles 2x2 [--skip-render]

  outputs/<year>/print/<year>_wallmaster_<w>x<h>in_300ppi.tif   1/4 of the
      mosaic frame, deflate/predictor 2, tagged 300 ppi. The mosaic frame is
      ~300 ppi-equivalent at the plates' own scale (5.7966 px/ft), so this
      keeps one printed inch per 25.9 ft of ground and every line the scans
      carry at half the web tiles' reduction.
  outputs/<year>/print/<year>_sheet_<w>x<h>in_300ppi.{tif,pdf}  the whole
      city on one sheet whose long side is SHEET_IN inches at 300 ppi.
  outputs/<year>/preview/<year>_fullcity_preview.jpg            ~1/10, for
      screen review.
  outputs/<year>/print/tiles/<year>_tile_<C>x<R>_c<i>r<j>_<w>x<h>in_300ppi.{tif,pdf}
      --tiles COLSxROWS: the wall master (work/city/<year>_wall_4.tif,
      rendered only if missing) cropped into a COLSxROWS panel grid, each
      panel <= 36x44 in at 300 ppi with a 300 px (1 in) overlap shared with
      its neighbours plus a blank bleed margin carrying corner registration
      marks and a panel label -- never over map pixels.
  outputs/<year>/print/tiles/manifest.json  each panel's mosaic rect (core,
      no overlap), its cropped rect (with overlap) and the overlap widths
      shared with each neighbour, in wall-master pixel coordinates.

Nothing is resampled twice: each output is rendered from the recipe at its
own reduction (tools/render.py), so no output inherits another's blur. The
tile grid reuses the wall master pixel-for-pixel (a crop, not a re-render),
so panel content matches the untiled wall master exactly.
"""
import argparse
import json
import os
import subprocess
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHEET_IN = 40.0          # long side of the single-sheet print, inches at 300 ppi
PPF = 5.7966             # mosaic px per foot (300 ppi-equivalent at 100 ft/in... see units.json)
TILE_OVERLAP_PX = 300    # 1 in at 300 ppi, shared between adjacent panels
TILE_BLEED_PX = 150      # 0.5 in blank margin outside the crop: reg marks + label only
TILE_MAX_IN = (36.0, 44.0)  # panel budget (w, h) inches at 300 ppi, bleed included


def run(cmd):
    print("+", " ".join(str(c) for c in cmd), flush=True)
    t = time.time()
    r = subprocess.run([str(c) for c in cmd], cwd=REPO)
    if r.returncode != 0:
        sys.exit(f"failed ({r.returncode}): {' '.join(str(c) for c in cmd)}")
    print(f"  [{time.time() - t:.0f}s]", flush=True)


def mb(p):
    return os.path.getsize(p) / 1e6


def ensure_wall(y, work, d, skip_render):
    """Reuse work/city/<y>_wall_<d>.tif; render it only if missing."""
    wall_raw = os.path.join(work, f"{y}_wall_{d}.tif")
    if not os.path.exists(wall_raw):
        run([sys.executable, "tools/render.py", "--year", y, "--all",
             "--downsample", d, "--ppi", 300, "--out", wall_raw])
    return wall_raw


def do_tiles(a, y, work, pdir):
    """Crop the wall master into a COLSxROWS panel grid with overlap and a
    blank bleed margin carrying registration marks + a panel label."""
    import pyvips

    cols, rows = (int(x) for x in a.tiles.lower().split("x"))
    d = a.wall_downsample
    wall_raw = ensure_wall(y, work, d, a.skip_render)
    im = pyvips.Image.new_from_file(wall_raw)
    W, H = im.width, im.height
    OV, BL = TILE_OVERLAP_PX, TILE_BLEED_PX
    max_w_px, max_h_px = TILE_MAX_IN[0] * 300, TILE_MAX_IN[1] * 300

    # core (non-overlapping) grid lines that tile the mosaic exactly
    xs = [round(c * W / cols) for c in range(cols + 1)]
    ys = [round(rr * H / rows) for rr in range(rows + 1)]

    tdir = os.path.join(pdir, "tiles")
    os.makedirs(tdir, exist_ok=True)
    manifest = {
        "year": y, "grid": f"{cols}x{rows}",
        "source": os.path.relpath(wall_raw, REPO),
        "mosaic_px": [W, H], "overlap_px": OV, "bleed_px": BL,
        "panels": [],
    }

    for ri in range(rows):
        for ci in range(cols):
            core_x0, core_x1 = xs[ci], xs[ci + 1]
            core_y0, core_y1 = ys[ri], ys[ri + 1]
            ov_l = OV if ci > 0 else 0
            ov_r = OV if ci < cols - 1 else 0
            ov_t = OV if ri > 0 else 0
            ov_b = OV if ri < rows - 1 else 0
            crop_x0, crop_x1 = core_x0 - ov_l, core_x1 + ov_r
            crop_y0, crop_y1 = core_y0 - ov_t, core_y1 + ov_b
            cw, ch = crop_x1 - crop_x0, crop_y1 - crop_y0
            panel_w, panel_h = cw + 2 * BL, ch + 2 * BL
            if panel_w > max_w_px or panel_h > max_h_px:
                sys.exit(f"panel c{ci}r{ri} {panel_w}x{panel_h}px "
                         f"({panel_w/300:.1f}x{panel_h/300:.1f}in) exceeds "
                         f"{TILE_MAX_IN[0]}x{TILE_MAX_IN[1]}in @300ppi budget")

            crop = im.crop(crop_x0, crop_y0, cw, ch)
            canvas = pyvips.Image.black(panel_w, panel_h, bands=3).cast("uchar") + [255, 255, 255]
            canvas = canvas.cast("uchar").copy(interpretation="srgb")
            canvas = canvas.insert(crop, BL, BL)

            # corner registration marks: crosshair + ring, centered in the
            # bleed strip's midline, never reaching the crop (which starts
            # at BL) or the outer edge (which is 0 / panel_w / panel_h).
            # pyvips draw_* ops return a new image rather than mutating in
            # place, so every call below must be reassigned.
            mlen, rad = 40, 8
            moff = BL // 2
            for (cx, cy) in ((moff, moff), (panel_w - moff, moff),
                             (moff, panel_h - moff), (panel_w - moff, panel_h - moff)):
                canvas = canvas.draw_line([0, 0, 0], cx - mlen // 2, cy, cx + mlen // 2, cy)
                canvas = canvas.draw_line([0, 0, 0], cx, cy - mlen // 2, cx, cy + mlen // 2)
                canvas = canvas.draw_circle([0, 0, 0], cx, cy, rad, fill=False)

            # panel label, bottom bleed strip only -- entirely below the crop
            label_txt = (f"{y} Galveston wall master -- tile grid {cols}x{rows} -- "
                         f"panel c{ci}r{ri} (col {ci+1}/{cols}, row {ri+1}/{rows}) -- "
                         f"300 ppi -- overlap {OV}px")
            label = pyvips.Image.text(label_txt, dpi=300, font="sans 10")
            label = label.ifthenelse([0, 0, 0], [255, 255, 255])
            lx = BL + 20
            ly = panel_h - BL + (BL - label.height) // 2
            lw = min(label.width, panel_w - BL - lx)
            if lw < label.width:
                label = label.crop(0, 0, lw, label.height)
            canvas = canvas.insert(label, lx, ly)

            win, hin = panel_w / 300.0, panel_h / 300.0
            base = f"{y}_tile_{cols}x{rows}_c{ci}r{ri}_{win:.0f}x{hin:.0f}in_300ppi"
            tif = os.path.join(tdir, base + ".tif")
            canvas.copy(xres=300 / 25.4, yres=300 / 25.4).tiffsave(
                tif, compression="deflate", predictor="horizontal", tile=True,
                tile_width=512, tile_height=512, bigtiff=True)
            pdf = os.path.join(tdir, base + ".pdf")
            jpg = os.path.join(work, f"{y}_tile_{cols}x{rows}_c{ci}r{ri}.jpg")
            canvas.jpegsave(jpg, Q=92)
            run(["img2pdf", "--output", pdf, "--pagesize", f"{win:.2f}inx{hin:.2f}in", jpg])
            print(f"tile c{ci}r{ri} {canvas.width}x{canvas.height} = "
                  f"{win:.1f} x {hin:.1f} in at 300 ppi, {mb(tif):.0f} MB tif, {mb(pdf):.0f} MB pdf")

            manifest["panels"].append({
                "id": f"c{ci}r{ri}", "col": ci, "row": ri,
                "core_rect_px": [core_x0, core_y0, core_x1, core_y1],
                "crop_rect_px": [crop_x0, crop_y0, crop_x1, crop_y1],
                "crop_size_px": [cw, ch],
                "panel_size_px": [panel_w, panel_h],
                "panel_size_in": [round(win, 2), round(hin, 2)],
                "overlap_px": {"left": ov_l, "right": ov_r, "top": ov_t, "bottom": ov_b},
                "tif": os.path.relpath(tif, REPO), "pdf": os.path.relpath(pdf, REPO),
            })

    mpath = os.path.join(tdir, "manifest.json")
    with open(mpath, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"tile manifest -> {mpath} ({len(manifest['panels'])} panels)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", type=int, default=1912)
    ap.add_argument("--wall-downsample", type=int, default=4)
    ap.add_argument("--preview-downsample", type=int, default=10)
    ap.add_argument("--skip-render", action="store_true")
    ap.add_argument("--tiles", default=None,
                     help="COLSxROWS, e.g. 2x2: crop the wall master into a print tile "
                          "grid instead of building the wall/sheet/preview outputs")
    a = ap.parse_args()
    y = a.year
    work = os.path.join(REPO, "work", "city")
    pdir = os.path.join(REPO, "outputs", str(y), "print")
    vdir = os.path.join(REPO, "outputs", str(y), "preview")
    for d in (work, pdir, vdir):
        os.makedirs(d, exist_ok=True)

    if a.tiles:
        do_tiles(a, y, work, pdir)
        return

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
