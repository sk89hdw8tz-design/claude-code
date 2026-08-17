"""Annotated A/B seam panels for manual control verification, one per pair.

The panel shows both plates' near-seam strips with a full-resolution pixel
ruler drawn every 500 px along the seam axis. Controls are read off these
panels by a human (band centres and flanking lines of each crossing feature)
and recorded in 30_controls/verified/ -- automation proposes and illustrates,
it does not decide. This is the semi-manual mode the brief prescribes, adopted
after three automated detectors failed on this material (F-001, F-003, F-004).
"""

import json
import os
import sys

from PIL import Image, ImageDraw

Image.MAX_IMAGE_PIXELS = None

BASE = "/home/user/claude-code/galveston-1912"
OUT = "/home/user/g1912/work/panels"
os.makedirs(OUT, exist_ok=True)

inv = json.load(open(f"{BASE}/00_inventory/INVENTORY.json"))
BY = {i["sheet"]: i for i in inv["items"]}

PAIRS = [
    (7, 8, "v"), (9, 10, "v"), (11, 12, "v"),
    (8, 39, "v"), (10, 43, "v"), (12, 49, "v"),
    (39, 40, "v"), (43, 44, "v"), (49, 50, "v"),
    (7, 9, "h"), (9, 11, "h"), (8, 10, "h"), (10, 12, "h"),
    (39, 43, "h"), (43, 49, "h"), (40, 44, "h"), (44, 50, "h"),
]

STRIP = 0.17     # page fraction nearest the seam shown per plate
PANEL_LONG = 1900  # panel size along the seam axis


def ruler(draw, length_px, scale, offset, vertical, size):
    for t in range(0, length_px + 1, 500):
        p = int(t * scale)
        if vertical:
            draw.line([(offset, p), (offset + 18, p)], fill=(255, 0, 0), width=2)
            draw.text((offset + 22, max(0, p - 7)), str(t), fill=(255, 0, 0))
        else:
            draw.line([(p, offset), (p, offset + 18)], fill=(255, 0, 0), width=2)
            draw.text((max(0, p - 14), offset + 22), str(t), fill=(255, 0, 0))


def make_panel(A, B, axis):
    a = Image.open(BY[A]["path"]).convert("RGB")
    b = Image.open(BY[B]["path"]).convert("RGB")
    if axis == "v":
        aw = int(a.width * STRIP)
        bw = int(b.width * STRIP)
        sa = a.crop((a.width - aw, 0, a.width, a.height))
        sb = b.crop((0, 0, bw, b.height))
        scale = PANEL_LONG / a.height
        sa = sa.resize((int(sa.width * scale), PANEL_LONG), Image.LANCZOS)
        sb = sb.resize((int(sb.width * scale), PANEL_LONG), Image.LANCZOS)
        gap = 26
        panel = Image.new("RGB", (sa.width + sb.width + gap + 130, PANEL_LONG + 30), "white")
        panel.paste(sa, (0, 30))
        panel.paste(sb, (sa.width + gap + 65, 30))
        d = ImageDraw.Draw(panel)
        d.text((4, 4), f"pair {A}-{B} (vertical seam)  LEFT: sheet {A} right strip", fill="black")
        d.text((sa.width + gap + 69, 4), f"RIGHT: sheet {B} left strip", fill="black")
        ruler(d, a.height, scale, sa.width + 2, True, panel.size)
        for t in range(0, b.height + 1, 500):
            p = int(t * scale) + 30
            d.line([(sa.width + gap + 45, p), (sa.width + gap + 63, p)], fill=(0, 0, 255), width=2)
    else:
        ah = int(a.height * STRIP)
        bh = int(b.height * STRIP)
        sa = a.crop((0, a.height - ah, a.width, a.height))
        sb = b.crop((0, 0, b.width, bh))
        scale = PANEL_LONG / a.width
        sa = sa.resize((PANEL_LONG, int(sa.height * scale)), Image.LANCZOS)
        sb = sb.resize((PANEL_LONG, int(sb.height * scale)), Image.LANCZOS)
        gap = 60
        panel = Image.new("RGB", (PANEL_LONG, sa.height + sb.height + gap + 60), "white")
        panel.paste(sa, (0, 30))
        panel.paste(sb, (0, sa.height + gap + 30))
        d = ImageDraw.Draw(panel)
        d.text((4, 4), f"pair {A}-{B} (horizontal seam)  TOP: sheet {A} bottom strip", fill="black")
        d.text((4, sa.height + 34), f"BOTTOM: sheet {B} top strip", fill="black")
        ruler(d, a.width, scale, sa.height + 32, False, panel.size)
    out = f"{OUT}/pair_{A:02d}_{B:02d}.jpg"
    panel.save(out, quality=90)
    return out, panel.size


targets = PAIRS
if len(sys.argv) > 2:
    targets = [(int(sys.argv[1]), int(sys.argv[2]),
                dict(((a, b), ax) for a, b, ax in PAIRS)[(int(sys.argv[1]), int(sys.argv[2]))])]
for A, B, axis in targets:
    out, size = make_panel(A, B, axis)
    print(f"pair {A:2d}-{B:2d}: {out} {size}")
