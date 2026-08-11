"""Print-ready posters of the Galveston 1889 wharf-front + downtown composite.

Two fixed sheet sizes, both landscape, both scaled from the full-resolution
master (never upscaled): 40 x 27 in (27x40 stock rotated) and 36 x 24 in.
"""
import json
import os
import sys

sys.path.insert(0, "/home/user/claude-code/sanborn")
from PIL import Image, ImageDraw, ImageFont
import config

Image.MAX_IMAGE_PIXELS = None
DPI = 300
YEAR = "1889"
SIZES = [(40, 27, "40x27"), (36, 24, "36x24")]

d = os.path.join(config.DELIVER_DIR, YEAR)
meta = json.load(open(os.path.join(d, "downtown_wharf_meta.json")))
master = Image.open(os.path.join(d, "galveston_1889_downtown_wharf.png")).convert("RGB")
MW, MH = master.size
print(f"master {MW}x{MH} px, aspect {MW/MH:.3f}")

F = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FB = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"

for win, hin, tag in SIZES:
    PW, PH = int(win * DPI), int(hin * DPI)
    margin = int(0.85 * DPI)
    cap = int(1.35 * DPI)
    avail_w, avail_h = PW - 2 * margin, PH - margin - cap
    scale = min(avail_w / MW, avail_h / MH)
    if scale > 1.0:
        scale = 1.0                     # never upscale the master
    mw, mh = int(MW * scale), int(MH * scale)
    eff_dpi = MW / (mw / DPI)
    page = Image.new("RGB", (PW, PH), (255, 255, 255))
    img = master.resize((mw, mh), Image.LANCZOS)
    ox = (PW - mw) // 2
    oy = margin
    page.paste(img, (ox, oy))
    dr = ImageDraw.Draw(page)
    dr.rectangle([ox - 3, oy - 3, ox + mw + 2, oy + mh + 2],
                 outline=(110, 110, 110), width=3)

    ts = max(38, int(0.235 * DPI))
    title = ImageFont.truetype(FB, ts)
    sub = ImageFont.truetype(F, int(ts * 0.55))
    small = ImageFont.truetype(F, int(ts * 0.38))
    y = oy + mh + int(0.30 * DPI)
    dr.text((ox, y), "GALVESTON, TEXAS — WHARF FRONT AND DOWNTOWN, 1889",
            font=title, fill=(15, 15, 15))
    dr.text((ox, y + int(ts * 1.30)),
            "Avenue A (Water) to Avenue I (Sealy)  ·  19th Street to 25th "
            "(Bath Avenue)  ·  Galveston Bay and the wharf front",
            font=sub, fill=(45, 45, 45))
    lines = [
        "Sanborn Map Co., 1889 edition. Composited from sheets "
        + ", ".join(str(int(u)) for u in meta["units"])
        + " — the eight sheets indexed to this ground on the edition's own key map.",
        "Original printed colours retained: no per-sheet white balance, so every wash renders as scanned. "
        f"Source coverage {meta['coverage_pct']:.2f}% of the frame; the unmapped south-west bay is left as flat paper.",
        "Galveston Bay and the slips are filled with the atlas's own printed waterline tone — the single "
        "deliberate stylization, applied only where the sheets draw water. No map content is generated anywhere.",
        "Source scans: Sanborn Fire Insurance Maps, Dolph Briscoe Center for American History, University of Texas at Austin.",
    ]
    for i, ln in enumerate(lines):
        dr.text((ox, y + int(ts * 2.05) + i * int(ts * 0.52)), ln,
                font=small, fill=(70, 70, 70))

    out = os.path.join(d, f"Galveston_1889_Wharf_Downtown_{tag}.pdf")
    page.save(out, "PDF", resolution=DPI, quality=94)
    print(f"{tag}: page {win}x{hin} in, map {mw/DPI:.2f}x{mh/DPI:.2f} in "
          f"at {eff_dpi:.0f} dpi -> {os.path.getsize(out)>>20} MB")
