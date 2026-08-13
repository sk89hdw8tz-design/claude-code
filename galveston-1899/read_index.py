#!/usr/bin/env python3
"""Prepare the index map for transcription, and validate the result.

The mosaic has to be aligned the way the atlas says, not the way the sheet
numbers happen to run. The index map (the diagram showing which numbered sheet
covers which part of the city) is the authority for that, but the numbers on it
are small on a full-page scan. This script blows it up into readable tiles so
the sheet positions can be transcribed accurately, then checks the transcription
before it is used for a 97 MP render.

    # 1. make the index map readable
    python3 read_index.py tiles --src maps/00-index.jpg --out index-tiles

    # 2. transcribe positions into layout-index.json, then check it
    python3 read_index.py validate --layout layout-index.json
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys

from PIL import Image, ImageOps

Image.MAX_IMAGE_PIXELS = 500_000_000

# The sheets this print is made of.
EXPECTED = [8, 7, 6, 5, 11, 13, 15, 12, 14, 16, 41, 39, 37]


def cmd_tiles(args: argparse.Namespace) -> int:
    if not os.path.exists(args.src):
        print(f"error: {args.src} not found. Download it first with fetch_maps.py.",
              file=sys.stderr)
        return 1

    with Image.open(args.src) as im:
        im = im.convert("L")
        print(f"Index map: {im.width} x {im.height}")

        if args.enhance:
            im = ImageOps.autocontrast(im, cutoff=1)

        scale = args.scale
        big = im.resize((int(im.width * scale), int(im.height * scale)), Image.LANCZOS)
        os.makedirs(args.out, exist_ok=True)

        whole = os.path.join(args.out, "index-full.png")
        preview = big.copy()
        preview.thumbnail((args.preview_px, args.preview_px), Image.LANCZOS)
        preview.save(whole)
        print(f"  {whole}  ({preview.width}x{preview.height}) -- overall shape")

        cols, rows = args.cols, args.rows
        # Overlap so a number sitting on a tile seam is still legible somewhere.
        ov = args.overlap
        tw, th = big.width / cols, big.height / rows
        n = 0
        for r in range(rows):
            for c in range(cols):
                x0 = max(0, int(c * tw - ov * tw))
                y0 = max(0, int(r * th - ov * th))
                x1 = min(big.width, int((c + 1) * tw + ov * tw))
                y1 = min(big.height, int((r + 1) * th + ov * th))
                tile = big.crop((x0, y0, x1, y1))
                path = os.path.join(args.out, f"tile-r{r}c{c}.png")
                tile.save(path)
                n += 1
        print(f"  {n} tiles ({cols}x{rows}, {ov:.0%} overlap) at {scale}x in {args.out}/")
        print("\nRead the sheet numbers off the tiles and write layout-index.json as")
        print('  {"sheet-08": [row, col], ...}   # row 0 = north, col 0 = west')
        print("then check it with:  python3 read_index.py validate --layout layout-index.json")
    return 0


def short_name(label: str) -> str:
    """Three-character cell label for the ASCII map.

    Any key can appear here -- someone may place '00-index' or a renamed sheet --
    so this never assumes the 'sheet-<int>' shape.
    """
    m = re.search(r"(\d+)\s*$", label)
    if m:
        return str(int(m.group(1)))
    return label[:3]


def cmd_validate(args: argparse.Namespace) -> int:
    with open(args.layout) as fh:
        raw = json.load(fh)
    layout = {k: v for k, v in raw.items() if not k.startswith("_")}

    problems: list[str] = []
    warnings: list[str] = []

    for k, v in layout.items():
        if not (isinstance(v, (list, tuple)) and len(v) == 2
                and all(isinstance(i, int) and i >= 0 for i in v)):
            problems.append(f"{k}: value must be [row, col] of non-negative ints, got {v!r}")

    if problems:
        for p in problems:
            print(f"  ✗ {p}")
        return 1

    seen: dict[tuple[int, int], str] = {}
    for k, (r, c) in sorted(layout.items()):
        if (r, c) in seen:
            problems.append(f"{k} and {seen[(r, c)]} both sit at [{r}, {c}]")
        seen[(r, c)] = k

    expected = {f"sheet-{n:02d}" for n in EXPECTED}
    got = set(layout)
    missing, extra = sorted(expected - got), sorted(got - expected)
    if missing:
        problems.append(f"missing from layout: {', '.join(missing)}")
    if extra:
        warnings.append(f"not in the requested 13: {', '.join(extra)}")

    rows = max((r for r, _ in layout.values()), default=-1) + 1
    cols = max((c for _, c in layout.values()), default=-1) + 1

    # A gap inside the footprint means the finished map has a hole in it. That
    # can be correct -- the selection need not be a solid rectangle -- so it is
    # a warning, not an error.
    holes = [(r, c) for r in range(rows) for c in range(cols) if (r, c) not in seen]
    if holes:
        warnings.append(
            f"{len(holes)} empty cell(s) inside the {rows}x{cols} footprint "
            f"{holes[:8]}{' ...' if len(holes) > 8 else ''} -- the print will have "
            f"blank gaps there"
        )

    print(f"Layout: {len(layout)} sheets in a {rows} x {cols} footprint")
    grid = []
    for r in range(rows):
        cells = []
        for c in range(cols):
            name = seen.get((r, c))
            cells.append(f"{short_name(name):>3}" if name else "  .")
        grid.append(" ".join(cells))
    print("\n  (row 0 = north, col 0 = west)")
    for line in grid:
        print(f"    {line}")
    print()

    for w in warnings:
        print(f"  ! {w}")
    for p in problems:
        print(f"  ✗ {p}")

    if problems:
        print(f"\n{len(problems)} problem(s) -- fix before rendering.", file=sys.stderr)
        return 1
    print("Layout is consistent." + (" Warnings above are worth a look." if warnings else ""))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    t = sub.add_parser("tiles", help="blow up the index map into readable tiles")
    t.add_argument("--src", default="maps/00-index.jpg")
    t.add_argument("--out", default="index-tiles")
    t.add_argument("--scale", type=float, default=3.0, help="upscale factor")
    t.add_argument("--cols", type=int, default=3)
    t.add_argument("--rows", type=int, default=4)
    t.add_argument("--overlap", type=float, default=0.08)
    t.add_argument("--preview-px", type=int, default=1600)
    t.add_argument("--no-enhance", dest="enhance", action="store_false")
    t.set_defaults(func=cmd_tiles)

    v = sub.add_parser("validate", help="check a transcribed layout")
    v.add_argument("--layout", default="layout-index.json")
    v.set_defaults(func=cmd_validate)

    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
