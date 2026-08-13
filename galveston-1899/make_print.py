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

# A uniform-scale tile within this many pixels of its cell is snapped to the cell
# so neighbours share an exact boundary. Comfortably above per-cell rounding
# (<=1 px) and far below any real part-sheet shortfall.
SNAP_PX = 3

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


def autocrop_border(im: Image.Image, tol: int = 18, max_frac: float = 0.15,
                    white: int = 250) -> Image.Image:
    """Cut the scan surround and the library caption band off a sheet.

    These scans sit on a pure-white bed and carry a printed credit line under
    the map ("Original located at ..."), separated from the sheet by a band of
    white. The sheet itself is aged cream, well below white, so the sheet is the
    contiguous not-white run through the middle of the image; anything beyond a
    white gap -- the caption, the bed -- is outside it.

    Keying on "not white" rather than "matches the corner pixel" matters: a
    single dark speck at the origin used to disable trimming entirely, and on a
    cream sheet the corner never matches the paper anyway.
    """
    gray = im.convert("L")
    w, h = gray.size
    row_mean = list(gray.resize((1, h), Image.BOX).tobytes())
    col_mean = list(gray.resize((w, 1), Image.BOX).tobytes())

    def middle_run(vals: list[int]) -> tuple[int, int]:
        centre = len(vals) // 2
        lo = centre
        while lo > 0 and vals[lo - 1] < white:
            lo -= 1
        hi = centre
        while hi < len(vals) - 1 and vals[hi + 1] < white:
            hi += 1
        return lo, hi

    top, bottom = middle_run(row_mean)
    left, right = middle_run(col_mean)

    if right - left < w * 0.5 or bottom - top < h * 0.5:
        return im
    return im.crop((left, top, right + 1, bottom + 1))


def crop_to_neatline(im: Image.Image, dark_drop: int = 40,
                     search_frac: float = 0.22, pad: int = 2) -> tuple[Image.Image, bool]:
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
    # Collapse to a 1-px strip so each value is a whole row's or column's mean
    # brightness. Pillow-only, and mean brightness finds a thin printed rule that
    # a hard "fraction of pixels below X" test misses: an antialiased 2px line on
    # aged paper never gets a majority of the row under a black threshold, but it
    # does move the row's mean well below the paper tone.
    row_mean = list(gray.resize((1, h), Image.BOX).tobytes())
    col_mean = list(gray.resize((w, 1), Image.BOX).tobytes())

    # Paper tone from the middle of the sheet, so the scan's own background sets
    # the reference rather than an assumed white.
    mid = sorted(row_mean[int(h * 0.25):int(h * 0.75)])
    paper = mid[len(mid) // 2] if mid else 255
    floor = paper - dark_drop

    sy, sx = max(2, int(h * search_frac)), max(2, int(w * search_frac))

    def darkest(vals, lo, hi):
        """Index of the darkest line in a window, if it is a rule and not paper."""
        window = range(max(0, lo), min(len(vals), hi))
        best = min(window, key=lambda i: vals[i], default=None)
        return best if best is not None and vals[best] <= floor else None

    top = darkest(row_mean, 0, sy)
    bottom = darkest(row_mean, h - sy, h)
    left = darkest(col_mean, 0, sx)
    right = darkest(col_mean, w - sx, w)

    if None in (top, bottom, left, right):
        return im, False

    box = (left + 1 + pad, top + 1 + pad, right - pad, bottom - pad)
    if box[2] - box[0] < w * 0.5 or box[3] - box[1] < h * 0.5:
        return im, False
    return im.crop(box), True


def apply_inset(im: Image.Image, inset: list) -> Image.Image:
    """Crop a fraction off each side: [left, top, right, bottom].

    Used to cut the printed margin so sheets butt at the map edge instead of the
    paper edge. Applied after trimming, so the fractions are of the trimmed
    sheet, which is what makes one set of numbers valid across the batch.
    """
    l, t, r, b = inset
    w, h = im.size
    box = (int(w * l), int(h * t), int(w * (1 - r)), int(h * (1 - b)))
    if box[2] - box[0] < 8 or box[3] - box[1] < 8:
        return im
    return im.crop(box)


def content_extent(im: Image.Image, white: int = 244) -> dict:
    """Measure how much of a sheet actually carries map content.

    A shoreline sheet is mostly open water, so its ink occupies a fraction of
    the paper. Forcing such a sheet to fill a whole mosaic cell stretches its
    built-up part across ground it does not cover. This measures the ink
    bounding box so those sheets can be found and anchored instead of guessed
    at.

    Returns fractions of the sheet covered by the ink bbox, plus where that box
    sits (n/s/e/w) so the sheet can be pinned to the right edge of its cell.
    """
    gray = im.convert("L")
    mask = gray.point(lambda v, t=white: 255 if v < t else 0)
    bbox = mask.getbbox()
    w, h = gray.size
    if not bbox:
        return {"w_frac": 0.0, "h_frac": 0.0, "area_frac": 0.0, "anchor": "c", "bbox": None}

    x0, y0, x1, y1 = bbox
    w_frac, h_frac = (x1 - x0) / w, (y1 - y0) / h

    # Which way the content leans. Slack ABOVE the ink means the content sits
    # low on the sheet, i.e. to the south -- so the sheet is pinned south.
    v = "s" if y0 > (h - y1) else ("n" if (h - y1) > y0 else "")
    hor = "e" if x0 > (w - x1) else ("w" if (w - x1) > x0 else "")
    # Only call it a lean when the sheet is genuinely lopsided.
    if h_frac > 0.9:
        v = ""
    if w_frac > 0.9:
        hor = ""
    anchor = (v + hor) or "c"
    return {
        "w_frac": w_frac,
        "h_frac": h_frac,
        "area_frac": w_frac * h_frac,
        "anchor": anchor,
        "bbox": bbox,
    }


ANCHORS = {
    "c": (0.5, 0.5), "n": (0.5, 0.0), "s": (0.5, 1.0), "w": (0.0, 0.5), "e": (1.0, 0.5),
    "nw": (0.0, 0.0), "ne": (1.0, 0.0), "sw": (0.0, 1.0), "se": (1.0, 1.0),
}


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
    ap.add_argument("--mosaic-scale", choices=["uniform", "cell"], default="uniform",
                    help="uniform: every sheet drawn at one common scale and anchored in "
                         "its cell, so a part-sheet (e.g. mostly open water) occupies only "
                         "the ground it covers (default). cell: stretch each sheet to fill "
                         "its cell -- only correct when every sheet covers equal ground.")
    ap.add_argument("--coverage", action="store_true",
                    help="report how much map content each sheet carries and flag part-sheets")
    ap.add_argument("--inset", default="",
                    help="after trimming, crop this much off each side as percentages of the "
                         "sheet, 'L,T,R,B' (e.g. 7.2,3.7,9.3,8.2). Use to cut the printed "
                         "margin so sheets butt at the map edge rather than the paper edge.")
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

    inset = None
    if args.inset:
        try:
            inset = [float(x) / 100.0 for x in args.inset.split(",")]
        except ValueError:
            inset = None
        if inset is None or len(inset) != 4 or not all(0 <= v < 0.45 for v in inset):
            print("error: --inset takes four percentages 'L,T,R,B', each 0-45", file=sys.stderr)
            return 2

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

    def prepared(path: str) -> Image.Image:
        """Open a sheet and apply exactly the crops the renderer will apply."""
        im = Image.open(path).convert("RGB")
        if args.trim:
            im = autocrop_border(im, tol=args.trim_tol)
            if args.neatline:
                im, _ = crop_to_neatline(im)
        if inset:
            im = apply_inset(im, inset)
        return im

    # Measure the sheets as they will actually be placed, not as they arrive.
    # Cell shape is derived from these, and trimming changes the aspect
    # materially (0.831 raw -> 0.811 after trim and inset on this batch). Sizing
    # cells from the raw aspect while pasting trimmed sheets makes the uniform
    # scale bind on height, leaving each sheet short of its cell width and
    # pillarboxed -- a white gutter down every vertical seam.
    sizes = []
    for p in paths:
        with prepared(p) as im:
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
        # [row, col] or [row, col, anchor]; the anchor pins a part-sheet to the
        # edge of its cell where its content actually belongs.
        anchors: dict[str, str] = {}
        bad = []
        for k, v in list(layout.items()):
            # Rows and columns may be fractional. Sheet runs that follow a
            # shoreline do not line up with the inland street grid -- here the
            # wharf column sits about two thirds of a sheet above it -- and only
            # a fractional row can say so.
            ok = (isinstance(v, (list, tuple)) and len(v) in (2, 3)
                  and all(isinstance(i, (int, float)) and not isinstance(i, bool) and i >= 0
                          for i in v[:2])
                  and (len(v) == 2 or (isinstance(v[2], str) and v[2].lower() in ANCHORS)))
            if not ok:
                bad.append(k)
                continue
            if len(v) == 3:
                anchors[k] = v[2].lower()
            layout[k] = (v[0], v[1])
        if bad:
            print(f"error: layout entries must be [row, col] or [row, col, anchor] with "
                  f"anchor in {sorted(ANCHORS)}; bad: {', '.join(sorted(bad))}",
                  file=sys.stderr)
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
        # Positions may be fractional, and a sheet at row 2.67 still occupies a
        # full cell below it, so the extent is ceil(max + 1).
        cols = math.ceil(max(c for _, c in layout.values()) + 1)
        rows = math.ceil(max(r for r, _ in layout.values()) + 1)
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

    if args.coverage or args.probe:
        print("\nContent coverage (ink bounding box as a fraction of the sheet):")
        cov = []
        for p in paths:
            with Image.open(p) as im:
                im = im.convert("RGB")
                if args.trim:
                    im = autocrop_border(im, tol=args.trim_tol)
                    if args.neatline:
                        im, _ = crop_to_neatline(im)
                if inset:
                    im = apply_inset(im, inset)
                cov.append((os.path.basename(p), content_extent(im)))
        areas = sorted(c["area_frac"] for _, c in cov)
        med = areas[len(areas) // 2] if areas else 0.0
        for name, c in cov:
            rel = (c["area_frac"] / med) if med else 1.0
            flag = ""
            if rel < 0.7:
                flag = f"  <-- only {rel * 100:.0f}% of the typical sheet, leans {c['anchor']}"
            print(f"  {name:<28} {c['w_frac'] * 100:5.1f}% wide x {c['h_frac'] * 100:5.1f}% tall"
                  f"  area {c['area_frac'] * 100:5.1f}%{flag}")
        light = [(n, c) for n, c in cov if med and c["area_frac"] / med < 0.7]
        if light:
            print(f"\n  ! {len(light)} sheet(s) carry much less content than the rest — "
                  f"typical of a shoreline sheet that is mostly open water.")
            print("    In a mosaic these must NOT be stretched to fill a cell. Either give")
            print("    them an anchor in the layout, e.g.")
            for n, c in light[:2]:
                lbl = os.path.splitext(n)[0]
                print(f"        \"{lbl}\": [row, col, \"{c['anchor']}\"]")
            print("    or keep --mosaic-scale uniform (the default), which places every")
            print("    sheet at one common scale rather than filling each cell.")
        else:
            print("\n  All sheets carry comparable content; none looks like a part-sheet.")

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
        # row_indent only applies to implicit row-major placement, where r is a
        # whole number; an explicit layout may use fractional rows.
        indent = row_indent[int(r)] if layout is None else 0.0
        return (off_x + indent + c * (cell_w_in + gutter),
                off_y + r * (cell_h_in + gutter))

    # For a uniform-scale mosaic every sheet is drawn at the same source-pixels-
    # per-printed-inch, so they must be measured after trimming before any are
    # placed. The median sheet is the one that fills a cell exactly.
    uniform_ppi = None
    if args.mode == "mosaic" and args.mosaic_scale == "uniform":
        widths = []
        for p in paths:
            with prepared(p) as im:
                widths.append(im.width)
        widths.sort()
        uniform_ppi = widths[len(widths) // 2] / cell_w_in
        print(f"Uniform mosaic scale: {uniform_ppi:.0f} source px per printed inch "
              f"(median sheet fills a {cell_w_in:.2f}\" cell)")

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
            if inset:
                im = apply_inset(im, inset)

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
                cw_px, ch_px = max(1, x1 - x0), max(1, y1 - y0)

                if args.mosaic_scale == "cell":
                    im = im.resize((cw_px, ch_px), Image.LANCZOS)
                    ox, oy = x0, y0
                else:
                    # One scale for the whole map: a sheet covering less ground
                    # takes less space rather than being stretched to fill a cell.
                    sw = max(1, int(round(im.width * (args.dpi / uniform_ppi))))
                    sh = max(1, int(round(im.height * (args.dpi / uniform_ppi))))
                    if sw > cw_px or sh > ch_px:
                        k = min(cw_px / sw, ch_px / sh)
                        sw, sh = max(1, int(sw * k)), max(1, int(sh * k))
                    # A sheet that covers the whole cell must land on the cell
                    # boundary exactly; otherwise the same sub-pixel rounding that
                    # caused the earlier hairlines reappears here, since the cell
                    # box varies by a pixel across the grid while this size does
                    # not. Genuine part-sheets fall well short of the tolerance
                    # and keep their true, smaller size.
                    if abs(sw - cw_px) <= SNAP_PX:
                        sw = cw_px
                    if abs(sh - ch_px) <= SNAP_PX:
                        sh = ch_px
                    im = im.resize((sw, sh), Image.LANCZOS)
                    ax, ay = ANCHORS[anchors.get(label, "c")]
                    ox = x0 + int(round((cw_px - sw) * ax))
                    oy = y0 + int(round((ch_px - sh) * ay))
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
