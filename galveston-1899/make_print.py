#!/usr/bin/env python3
"""Assemble Galveston 1899 Sanborn sheets into a single fixed-size print.

Two assembly modes:

  grid    Each sheet is kept whole and placed in its own cell with gutters --
          a plate-style montage. Safe default: nothing is cropped, every sheet
          stays readable as a document.

  mosaic  Sheets are butted edge-to-edge with no gutter to approximate a
          continuous map. Use --trim to cut the scan border/neatline first,
          and supply --layout so sheets land in their true geographic
          positions (read them off the Key sheet).

The canvas is a fixed physical size (default 27x40 inches) at a fixed DPI, so
the output is print-ready rather than "some big JPEG".

Examples:

    # inspect what you have and what grid fits, render nothing
    python3 make_print.py --src maps --probe

    # default plate montage at 300 dpi
    python3 make_print.py --src maps --out galveston-27x40.tif

    # geographic mosaic using an explicit layout
    python3 make_print.py --src maps --mode mosaic --trim --layout layout.json
"""

from __future__ import annotations

import argparse
import glob
import json
import math
import os
import re
import sys

from PIL import Image, ImageDraw, ImageFont

# A 27x40in canvas at 300dpi is 97.2 MP, above Pillow's 89.5 MP default guard.
# We are the ones creating the big image, so raise the ceiling deliberately.
Image.MAX_IMAGE_PIXELS = 500_000_000

SHEET_RE = re.compile(r"sheet-(\d+)", re.I)
FRONT_ORDER = ["key", "legend", "title", "index"]

# Sheet order as requested. Front matter is placed first by default.
DEFAULT_SHEET_ORDER = [8, 7, 6, 5, 11, 13, 15, 12, 14, 16, 41, 39, 37]


def find_font(size: int) -> ImageFont.ImageFont:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    for path in glob.glob("/usr/share/fonts/**/*.ttf", recursive=True)[:1]:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            pass
    return ImageFont.load_default()


def sort_key(path: str) -> tuple:
    """Front matter first (key, legend, title, index), then sheets in the
    requested order, then anything else alphabetically."""
    name = os.path.basename(path).lower()
    m = SHEET_RE.search(name)
    if m:
        n = int(m.group(1))
        rank = DEFAULT_SHEET_ORDER.index(n) if n in DEFAULT_SHEET_ORDER else 10_000 + n
        return (1, rank, name)
    for i, kind in enumerate(FRONT_ORDER):
        if kind in name:
            return (0, i, name)
    return (2, 0, name)


def load_paths(src: str, pattern: str) -> list[str]:
    paths = [
        p for p in glob.glob(os.path.join(src, pattern))
        if os.path.splitext(p)[1].lower() in {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".gif"}
    ]
    return sorted(paths, key=sort_key)


def autocrop_border(im: Image.Image, tol: int = 18, max_frac: float = 0.15) -> Image.Image:
    """Trim a near-uniform border (scan margin) from the edges.

    Conservative by design: refuses to remove more than `max_frac` of either
    dimension, so a sheet with a genuinely pale edge is never gutted.
    """
    gray = im.convert("L")
    w, h = gray.size
    px = gray.load()

    def row_uniform(y: int, ref: int) -> bool:
        step = max(1, w // 256)
        return all(abs(px[x, y] - ref) <= tol for x in range(0, w, step))

    def col_uniform(x: int, ref: int) -> bool:
        step = max(1, h // 256)
        return all(abs(px[x, y] - ref) <= tol for y in range(0, h, step))

    ref = px[0, 0]
    top, bottom, left, right = 0, h - 1, 0, w - 1
    lim_y, lim_x = int(h * max_frac), int(w * max_frac)

    while top < lim_y and row_uniform(top, ref):
        top += 1
    while bottom > h - 1 - lim_y and row_uniform(bottom, ref):
        bottom -= 1
    while left < lim_x and col_uniform(left, ref):
        left += 1
    while right > w - 1 - lim_x and col_uniform(right, ref):
        right -= 1

    if right - left < w * 0.5 or bottom - top < h * 0.5:
        return im
    return im.crop((left, top, right + 1, bottom + 1))


def crop_to_neatline(im: Image.Image, dark: int = 110, min_frac: float = 0.55,
                     search_frac: float = 0.20, pad: int = 2) -> tuple[Image.Image, bool]:
    """Crop to just inside the printed border rule (the neatline).

    For a mosaic the sheets have to butt at the *map* edge, not the paper edge;
    leaving the rule in place draws a black grid through the middle of the
    finished map. Each edge is searched inward for the innermost row/column
    that is predominantly dark -- that is the rule -- and the crop lands just
    inside it.

    Returns (image, found). If a rule is not clearly present on all four sides
    the image is returned untouched, so a sheet that was scanned without one is
    never mangled.
    """
    gray = im.convert("L")
    w, h = gray.size
    # Threshold to a dark mask, then let a BOX resize do the averaging: collapsing
    # to width 1 gives the dark fraction of each row, to height 1 each column.
    # Keeps this Pillow-only -- no numpy -- so the documented install stays true.
    mask = gray.point(lambda v, d=dark: 255 if v < d else 0)
    row_frac = [p / 255 for p in mask.resize((1, h), Image.BOX).tobytes()]
    col_frac = [p / 255 for p in mask.resize((w, 1), Image.BOX).tobytes()]
    sy, sx = max(1, int(h * search_frac)), max(1, int(w * search_frac))

    top_c = [i for i in range(sy) if row_frac[i] >= min_frac]
    bot_c = [i for i in range(h - 1, h - 1 - sy, -1) if row_frac[i] >= min_frac]
    lft_c = [i for i in range(sx) if col_frac[i] >= min_frac]
    rgt_c = [i for i in range(w - 1, w - 1 - sx, -1) if col_frac[i] >= min_frac]

    if not (top_c and bot_c and lft_c and rgt_c):
        return im, False

    # Innermost rule on each side, then step just past it.
    top, bottom = max(top_c) + 1 + pad, min(bot_c) - pad
    left, right = max(lft_c) + 1 + pad, min(rgt_c) - pad

    if right - left < w * 0.5 or bottom - top < h * 0.5:
        return im, False
    return im.crop((left, top, right, bottom)), True


def choose_grid(n: int, canvas_w: float, canvas_h: float, sheet_aspect: float,
                margin: float, gutter: float) -> tuple[int, int, float]:
    """Pick cols x rows that wastes the least canvas.

    Returns (cols, rows, coverage) where coverage is the fraction of the
    printable area actually covered by imagery.
    """
    best = None
    for cols in range(1, n + 1):
        rows = math.ceil(n / cols)
        if cols * rows - n >= cols and rows > 1:
            continue  # a fully empty row means the grid is silly
        avail_w = canvas_w - 2 * margin - gutter * (cols - 1)
        avail_h = canvas_h - 2 * margin - gutter * (rows - 1)
        if avail_w <= 0 or avail_h <= 0:
            continue
        cell_w, cell_h = avail_w / cols, avail_h / rows
        # fit sheet_aspect (w/h) inside the cell
        if cell_w / cell_h > sheet_aspect:
            draw_h, draw_w = cell_h, cell_h * sheet_aspect
        else:
            draw_w, draw_h = cell_w, cell_w / sheet_aspect
        coverage = (draw_w * draw_h * n) / (canvas_w * canvas_h)
        if best is None or coverage > best[2]:
            best = (cols, rows, coverage)
    if best is None:
        raise SystemExit("error: canvas too small for the requested margins/gutters")
    return best


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", default="maps", help="directory of downloaded sheets")
    ap.add_argument("--pattern", default="*", help="glob within --src")
    ap.add_argument("--out", default="galveston-1899-27x40.tif", help="output path (.tif/.png/.jpg)")
    ap.add_argument("--mode", choices=["grid", "mosaic"], default="grid")
    ap.add_argument("--width-in", type=float, default=27.0)
    ap.add_argument("--height-in", type=float, default=40.0)
    ap.add_argument("--dpi", type=int, default=300)
    ap.add_argument("--margin-in", type=float, default=0.5, help="outer margin (grid mode)")
    ap.add_argument("--gutter-in", type=float, default=0.12, help="space between cells (grid mode)")
    ap.add_argument("--cols", type=int, default=0, help="force column count (0 = auto)")
    ap.add_argument("--rows", type=int, default=0, help="force row count (0 = auto)")
    ap.add_argument("--fit", choices=["block", "stretch"], default="block",
                    help="block: cells match the sheet aspect and the whole block is centred, "
                         "so leftover space becomes even margin (default). "
                         "stretch: cells fill the canvas and each sheet letterboxes inside its cell.")
    ap.add_argument("--label-in", type=float, default=0.22,
                    help="height of the caption band under each cell, inches")
    ap.add_argument("--layout", default=None,
                    help="JSON mapping label -> [row, col] for explicit placement")
    ap.add_argument("--trim", action="store_true", help="auto-trim uniform scan borders")
    ap.add_argument("--trim-tol", type=int, default=18)
    ap.add_argument("--neatline", action="store_true",
                    help="after --trim, crop just inside the printed border rule so sheets "
                         "butt at the map edge (recommended for --mode mosaic)")
    ap.add_argument("--exclude", default="",
                    help="comma-separated substrings; matching files are left out of the "
                         "print entirely (e.g. --exclude key)")
    ap.add_argument("--labels", action="store_true", help="draw the sheet label under each cell")
    ap.add_argument("--bg", default="#ffffff", help="canvas background colour")
    ap.add_argument("--proof", default=None, help="also write a downsampled JPEG proof here")
    ap.add_argument("--proof-px", type=int, default=2400, help="long edge of the proof")
    ap.add_argument("--pdf", default=None, help="also write a PDF at this path")
    ap.add_argument("--probe", action="store_true", help="report sizes/fit and exit without rendering")
    args = ap.parse_args()

    paths = load_paths(args.src, args.pattern)
    if not paths:
        print(f"error: no images found in {args.src!r} matching {args.pattern!r}", file=sys.stderr)
        return 1

    drops = [d.strip().lower() for d in args.exclude.split(",") if d.strip()]
    if drops:
        kept = [p for p in paths if not any(d in os.path.basename(p).lower() for d in drops)]
        for p in paths:
            if p not in kept:
                print(f"  excluded from print: {os.path.basename(p)}")
        paths = kept
        if not paths:
            print(f"error: --exclude {args.exclude!r} removed every image", file=sys.stderr)
            return 1

    print(f"Found {len(paths)} image(s) in {args.src}")
    sizes = []
    for p in paths:
        with Image.open(p) as im:
            sizes.append(im.size)
    aspects = [w / h for w, h in sizes]
    median_aspect = sorted(aspects)[len(aspects) // 2]
    for p, (w, h) in zip(paths, sizes):
        print(f"  {os.path.basename(p):<28} {w:>6} x {h:<6}  aspect {w / h:.3f}")
    spread = max(aspects) / min(aspects)
    print(f"\nMedian aspect {median_aspect:.3f} (spread {spread:.2f}x)")
    if spread > 1.25:
        print("  ! Sheets vary a lot in shape; cells are sized to the median, "
              "so odd ones will letterbox.")

    canvas_px = (int(round(args.width_in * args.dpi)), int(round(args.height_in * args.dpi)))
    print(f"Canvas: {args.width_in}\" x {args.height_in}\" @ {args.dpi} dpi "
          f"= {canvas_px[0]} x {canvas_px[1]} px ({canvas_px[0] * canvas_px[1] / 1e6:.1f} MP)")

    n = len(paths)
    margin = args.margin_in if args.mode == "grid" else 0.0
    gutter = args.gutter_in if args.mode == "grid" else 0.0

    layout = None
    if args.layout:
        with open(args.layout) as fh:
            raw = json.load(fh)
        layout = {k: v for k, v in raw.items() if not k.startswith("_")}
        bad = [k for k, v in layout.items()
               if not (isinstance(v, (list, tuple)) and len(v) == 2
                       and all(isinstance(i, int) and i >= 0 for i in v))]
        if bad:
            print(f"error: layout entries must be [row, col] with non-negative ints; "
                  f"bad: {', '.join(sorted(bad))}", file=sys.stderr)
            return 2
        seen: dict[tuple[int, int], str] = {}
        for k, (r, c) in layout.items():
            if (r, c) in seen:
                print(f"error: layout puts {seen[(r, c)]!r} and {k!r} both at "
                      f"[{r}, {c}]", file=sys.stderr)
                return 2
            seen[(r, c)] = k
        print(f"Layout: {len(layout)} placement(s) from {args.layout}")
        labels_present = {os.path.splitext(os.path.basename(p))[0] for p in paths}
        unplaced = sorted(labels_present - set(layout))
        unknown = sorted(set(layout) - labels_present)
        if unplaced:
            print(f"  ! not in layout, will be left out: {', '.join(unplaced)}")
        if unknown:
            print(f"  ! in layout but no such file: {', '.join(unknown)}")

    if args.cols and args.rows:
        cols, rows = args.cols, args.rows
    elif args.cols:
        cols, rows = args.cols, math.ceil(n / args.cols)
    elif args.rows:
        rows = args.rows
        cols = math.ceil(n / rows)
    elif layout:
        # The layout defines the geography; the grid must match its extent, not
        # the image count, or sheets fall outside the grid and get dropped.
        cols = max(c for _, c in layout.values()) + 1
        rows = max(r for r, _ in layout.values()) + 1
        print(f"Grid from layout extent: {cols} x {rows}")
    else:
        cols, rows, cov = choose_grid(n, args.width_in, args.height_in, median_aspect, margin, gutter)
        print(f"Auto grid: {cols} x {rows} (coverage {cov * 100:.1f}% of the sheet)")
    n_cells = len(layout) if layout else n
    if cols * rows < n_cells:
        print(f"error: {cols}x{rows} = {cols * rows} cells cannot hold {n_cells} images",
              file=sys.stderr)
        return 2
    print(f"Grid: {cols} cols x {rows} rows ({cols * rows - n_cells} empty cell(s))")

    label_h_in = args.label_in if args.labels else 0.0
    avail_w = args.width_in - 2 * margin - gutter * (cols - 1)
    avail_h = args.height_in - 2 * margin - gutter * (rows - 1)

    if args.fit == "block":
        # Size the cell to the sheet aspect so images fill their cells exactly,
        # then centre the whole block. Leftover space lands in the outer margin
        # instead of pooling between rows.
        #
        # This matters most in mosaic mode: stretching each sheet to a cell of a
        # different aspect scales the map by different factors horizontally and
        # vertically, so a city block prints as the wrong shape. A map has one
        # scale or it is not a map.
        cw = avail_w / cols
        ch = (avail_h / rows) - label_h_in
        if ch <= 0:
            print(f"error: --label-in {label_h_in}\" leaves no height for images "
                  f"in a {rows}-row grid", file=sys.stderr)
            return 2
        if cw / ch > median_aspect:            # height-limited
            cell_h_in, cell_w_in = ch + label_h_in, ch * median_aspect
        else:                                   # width-limited
            cell_w_in, cell_h_in = cw, cw / median_aspect + label_h_in
        block_w = cell_w_in * cols + gutter * (cols - 1)
        block_h = cell_h_in * rows + gutter * (rows - 1)
        off_x = (args.width_in - block_w) / 2
        off_y = (args.height_in - block_h) / 2
        print(f"Block {block_w:.2f}\" x {block_h:.2f}\" centred; "
              f"outer margin {off_x:.2f}\" x {off_y:.2f}\"")
    else:
        cell_w_in, cell_h_in = avail_w / cols, avail_h / rows
        off_x = off_y = margin
        if args.mode == "mosaic":
            sx = (cell_w_in / (cell_h_in - label_h_in)) / median_aspect
            if abs(sx - 1) > 0.02:
                print(f"  ! --fit stretch distorts the mosaic: sheets are scaled "
                      f"{abs(sx - 1) * 100:.1f}% differently across than down, so the "
                      f"map has two scales. Use --fit block to keep it true.")
    img_h_in = cell_h_in - label_h_in
    print(f"Cell: {cell_w_in:.2f}\" x {cell_h_in:.2f}\" (image area {cell_w_in:.2f}\" x {img_h_in:.2f}\")")

    # Resolution sanity: how much are we scaling each source?
    worst = None
    for p, (w, h) in zip(paths, sizes):
        a = w / h
        if cell_w_in / img_h_in > a:
            draw_h_in, draw_w_in = img_h_in, img_h_in * a
        else:
            draw_w_in, draw_h_in = cell_w_in, cell_w_in / a
        eff = w / draw_w_in  # source pixels per printed inch
        if worst is None or eff < worst[1]:
            worst = (os.path.basename(p), eff)
    print(f"Effective resolution: worst sheet is {worst[0]} at {worst[1]:.0f} ppi "
          f"({'upsampling' if worst[1] < args.dpi else 'downsampling'} to {args.dpi} dpi)")
    if worst[1] < 150:
        print("  ! Below 150 ppi -- expect visible softness at arm's length. "
              "Consider fewer sheets per print or a larger canvas.")

    if args.probe:
        print("\n--probe: stopping before render.")
        return 0

    canvas = Image.new("RGB", canvas_px, args.bg)
    font = find_font(max(12, int(label_h_in * args.dpi * 0.6))) if args.labels else None
    draw = ImageDraw.Draw(canvas) if args.labels else None

    # A partial final row looks ragged left-aligned; nudge it to centre.
    # Only for implicit row-major placement -- an explicit layout means the
    # caller has decided where things go.
    row_indent = [0.0] * rows
    if layout is None and args.mode == "grid":
        for r in range(rows):
            in_row = max(0, min(n - r * cols, cols))
            if 0 < in_row < cols:
                row_indent[r] = (cols - in_row) * (cell_w_in + gutter) / 2

    def cell_origin(r: int, c: int) -> tuple[float, float]:
        return (off_x + row_indent[r] + c * (cell_w_in + gutter),
                off_y + r * (cell_h_in + gutter))

    placed = 0
    neatline_misses: list[str] = []
    for i, p in enumerate(paths):
        label = os.path.splitext(os.path.basename(p))[0]
        if layout is not None:
            if label not in layout:
                print(f"  ! {label}: not in layout, skipped")
                continue
            r, c = layout[label]
        else:
            r, c = divmod(i, cols)
        if r >= rows or c >= cols:
            print(f"  ! {label}: position ({r},{c}) is outside the {rows}x{cols} grid, skipped")
            continue

        with Image.open(p) as im:
            im = im.convert("RGB")
            if args.trim:
                before = im.size
                im = autocrop_border(im, tol=args.trim_tol)
                note = ""
                if args.neatline:
                    im, found = crop_to_neatline(im)
                    note = " (to neatline)" if found else " (no rule found)"
                    if not found:
                        neatline_misses.append(label)
                if im.size != before:
                    print(f"  {label}: trimmed {before[0]}x{before[1]} -> "
                          f"{im.size[0]}x{im.size[1]}{note}")

            ox_in, oy_in = cell_origin(r, c)

            if args.mode == "mosaic":
                # Derive the tile's pixel box from the rounded cell *boundaries*,
                # not from a rounded cell size. Rounding a shared size and each
                # origin independently lets round(r*s) exceed round((r-1)*s)+
                # round(s), which leaves an uncovered scanline -- a white hairline
                # printed straight across a map that is meant to butt edge to edge.
                # Taking both edges from the same rounding makes neighbours share
                # their boundary pixel by construction.
                x0 = int(round(ox_in * args.dpi))
                x1 = int(round((ox_in + cell_w_in) * args.dpi))
                y0 = int(round(oy_in * args.dpi))
                y1 = int(round((oy_in + img_h_in) * args.dpi))
                im = im.resize((max(1, x1 - x0), max(1, y1 - y0)), Image.LANCZOS)
                ox, oy = x0, y0
            else:
                a = im.width / im.height
                if cell_w_in / img_h_in > a:
                    dh_in, dw_in = img_h_in, img_h_in * a
                else:
                    dw_in, dh_in = cell_w_in, cell_w_in / a
                im = im.resize(
                    (max(1, int(round(dw_in * args.dpi))), max(1, int(round(dh_in * args.dpi)))),
                    Image.LANCZOS,
                )
                ox = int(round((ox_in + (cell_w_in - dw_in) / 2) * args.dpi))
                oy = int(round((oy_in + (img_h_in - dh_in) / 2) * args.dpi))

            canvas.paste(im, (ox, oy))
            placed += 1

            if draw and font:
                text = label.replace("-", " ").replace("sheet ", "Sheet ").title()
                ty = int(round((oy_in + img_h_in + label_h_in * 0.1) * args.dpi))
                tw = draw.textlength(text, font=font)
                draw.text((int(round((ox_in + cell_w_in / 2) * args.dpi) - tw / 2), ty),
                          text, fill="#333333", font=font)

    print(f"\nPlaced {placed}/{len(paths)} image(s)")
    if neatline_misses:
        print(f"  ! no border rule detected on {len(neatline_misses)} sheet(s): "
              f"{', '.join(neatline_misses)}")
        print("    those sheets keep their paper edge and will not butt cleanly; "
              "check the proof before printing.")

    ext = os.path.splitext(args.out)[1].lower()
    save_kw = {"dpi": (args.dpi, args.dpi)}
    if ext in {".tif", ".tiff"}:
        save_kw["compression"] = "tiff_lzw"
    elif ext in {".jpg", ".jpeg"}:
        save_kw.update(quality=95, subsampling=0, optimize=True)
    canvas.save(args.out, **save_kw)
    print(f"Wrote {args.out} ({os.path.getsize(args.out) / 1e6:.1f} MB)")

    if args.proof:
        proof = canvas.copy()
        proof.thumbnail((args.proof_px, args.proof_px), Image.LANCZOS)
        proof.save(args.proof, quality=88, optimize=True)
        print(f"Wrote {args.proof} ({proof.width}x{proof.height}, "
              f"{os.path.getsize(args.proof) / 1e6:.1f} MB)")

    if args.pdf:
        canvas.save(args.pdf, "PDF", resolution=args.dpi)
        print(f"Wrote {args.pdf} ({os.path.getsize(args.pdf) / 1e6:.1f} MB)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
