#!/usr/bin/env python
"""Produce the print deliverable from master_full.tif at the 1899 reference's
standard: single-page PDF, one embedded baseline JPEG (quality 92), exactly
300.0 DPI, long side 40.0 in (12000 px).

Composition:
  * Crop master_full.tif to the printed extent: full block footprint plus
    enough bay band to include the drawn pier heads with ~250 px (mosaic) of
    water beyond the longest pier; trailing white trimmed so the map rect ends
    at drawn content (the canvas cut lines at top/bottom/east are the content
    edges there).
  * Uniform intentional white margins (~180 px mosaic) around the map rect;
    the bottom margin is deepened just enough to carry the caption strip.
    Caption text sits INSIDE the bottom margin, never over map content.
  * ONE Lanczos downsample of the crop (presentation resampling only; the
    archival-resolution master remains the primary deliverable).

Outputs (deliverables/):
  Galveston_1912_Wharf_Downtown_print.pdf
  Galveston_1912_Wharf_Downtown_print.jpg          (embedded JPEG, kept)
  Galveston_1912_SelectedArea_HISTORICAL_MASTER.tif (byte-copy of master_full)
  SHA256SUMS.txt
  print_composition.json                            (recorded geometry)
"""
import hashlib
import json
import os
import shutil

import cv2
import numpy as np
import tifffile
import pymupdf
import paper_flatfield
import tone_match
import water_treatment
from PIL import Image, ImageDraw, ImageFont

ROOT = '/home/user/claude-code/galveston-1912'
FINAL = f'{ROOT}/60_master/final'
DELIV = f'{ROOT}/deliverables'
os.makedirs(DELIV, exist_ok=True)

CX0, CY0 = -16734, -8279
DPI = 300.0
LONG_SIDE_PX = 12000
WATER_MARGIN = 250          # mosaic px beyond the longest pier
WHITE_MARGIN = 180          # mosaic px intentional margin
JPEG_QUALITY = 92
FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
WATER_SPEC = f'{ROOT}/50_seams/water_regions.geojson'
TONE_SPEC = f'{ROOT}/50_seams/tone_anchors.json'
FF_SPEC = f'{ROOT}/50_seams/paper_flatfield.json'
CAPTION = ('GALVESTON, TEXAS - WHARF FRONT AND DOWNTOWN, 1912 / '
           'Avenue A (Water) to Avenue I (Sealy) - 19th Street to 25th Street '
           '(Rosenberg Avenue) - Piers 19-25 / '
           'Composited from 14 source regions of the 1912 Sanborn Fire '
           'Insurance Map (LOC sanborn08539_004); sheets '
           '5(A,B),7,8,9,10,11,12,39,40,43,44,49,50; land colors as scanned; '
           'open water flat-filled to the 1899 companion sheet, the bay beyond '
           '1912 sheet coverage filled likewise and carrying no source detail; '
           'per-plate illumination corrected so streets and open ground read '
           'one tone; tone and color matched to the 1899 sheet (levels, '
           'highlight shoulder, saturation; orange fills brightened only); '
           'plate disagreements preserved; wharf plates (100 ft/in) unified to '
           'the grid scale of 50 ft/in - printed at approx. 80 ft/in.')


def sha256_file(path, chunk=1 << 22):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


print('loading master_full.tif ...')
img = tifffile.imread(f'{FINAL}/master_full.tif')       # RGB uint8
H, W = img.shape[:2]

# ---------------------------------------------------------------- extents
# non-white content (rendered border/unowned canvas is exact 255 white)
nonwhite = (img.min(axis=2) < 254)
col_ct = nonwhite.sum(axis=0)
row_ct = nonwhite.sum(axis=1)
cols = np.where(col_ct > 20)[0]
rows = np.where(row_ct > 20)[0]
content_x0, content_x1 = int(cols[0]), int(cols[-1]) + 1
content_y0, content_y1 = int(rows[0]), int(rows[-1]) + 1
print(f'non-white content bbox canvas: x {content_x0}..{content_x1}, '
      f'y {content_y0}..{content_y1} (mosaic x {content_x0+CX0}..{content_x1+CX0})')

# drawn-ink west extent in the bay band (scale bar / bay lettering / pier
# heads).  True ink on this scan is min-channel < 120 (paper sits at ~162-174);
# connected components >= 250 px reject dust specks and foxing stains.
band = img[:, :7460]
dark = (band.min(axis=2) < 120).astype(np.uint8)
dark = cv2.morphologyEx(dark, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
n_cc, _lab, cc_stats, _cen = cv2.connectedComponentsWithStats(dark, connectivity=8)
comps = sorted((int(cc_stats[i, 0]), int(cc_stats[i, 4]),
                int(cc_stats[i, 1]), int(cc_stats[i, 2]), int(cc_stats[i, 3]))
               for i in range(1, n_cc) if cc_stats[i, 4] >= 250)
ink_x0 = comps[0][0]
print('westernmost drawn ink components (x0/area/y0/w/h):', comps[:4])
print(f'westernmost drawn ink in band: canvas x {ink_x0} (mosaic {ink_x0 + CX0})')

# map rect (canvas coords).  West bound: the neatline-content rule binds --
# WHITE_MARGIN beyond the westernmost drawn content (the graphic scale bar);
# this leaves far more than WATER_MARGIN of drawn water beyond the longest
# pier (pier heads sit ~1200 px further east), satisfying both rules.
map_x0 = max(ink_x0 - WHITE_MARGIN, 0)
map_x1 = content_x1
map_y0 = content_y0
map_y1 = content_y1
print(f'map rect canvas: x {map_x0}..{map_x1}, y {map_y0}..{map_y1} '
      f'({map_x1-map_x0} x {map_y1-map_y0})')

# ---------------------------------------------------------------- scale
# print page = map rect + margins; caption deepens the bottom margin.
scale = None
mw, mh = map_x1 - map_x0, map_y1 - map_y0
# provisional scale from width (landscape long side):
s0 = LONG_SIDE_PX / (mw + 2 * WHITE_MARGIN)
# caption strip: three lines, plain, sized at print resolution
line_h1, line_h2 = 40, 31                                # px @300dpi (~9.6/7.4 pt)
gap, pad_top, pad_bot = 12, 26, 26
caption_px = pad_top + line_h1 + gap + line_h2 + gap + line_h2 + pad_bot
bottom_margin_mosaic = max(WHITE_MARGIN, int(np.ceil(caption_px / s0)))
page_w_mosaic = mw + 2 * WHITE_MARGIN
page_h_mosaic = mh + WHITE_MARGIN + bottom_margin_mosaic
assert page_w_mosaic > page_h_mosaic, 'expected landscape'
scale = LONG_SIDE_PX / page_w_mosaic
page_w_px = LONG_SIDE_PX
page_h_px = int(round(page_h_mosaic * scale))
print(f'page mosaic {page_w_mosaic} x {page_h_mosaic}; scale {scale:.6f}; '
      f'page px {page_w_px} x {page_h_px}; '
      f'{page_w_px/DPI:.2f} x {page_h_px/DPI:.2f} in @ {DPI} DPI')

# ---------------------------------------------------------------- water (D-015)
# Presentation stage only: master_full.tif and the archival scans are never
# written. Deliberately applied AFTER the extents above are measured, so the
# printed page geometry is derived from the untreated master and is unchanged
# by the treatment.
# D-016 tone match FIRST, then the water fill: the other way round the bay
# would be dragged off its exact 1899 value by the levels gain.
img_orig = img                       # kept for water-mask measurement only
print('applying per-plate illumination correction ...')
img, ff_stats = paper_flatfield.apply(
    img, FF_SPEC, f'{FINAL}/ownership_map.tif')
for k, v in ff_stats.items():
    print(f'  {k}: {v}')
print('applying tone match ...')
img, tone_stats = tone_match.apply(img, TONE_SPEC)
for k, v in tone_stats.items():
    print(f'  {k}: {v}')
print('applying water treatment ...')
# mask measured on the ORIGINAL master (uncovered canvas is exact 255 there);
# fill applied to the tone-matched image
img, water_stats = water_treatment.apply(img, WATER_SPEC, mask_img=img_orig)
del img_orig
for k, v in water_stats.items():
    print(f'  {k}: {v}')

# ---------------------------------------------------------------- compose
crop = img[map_y0:map_y1, map_x0:map_x1]
tw = int(round(mw * scale))
th = int(round(mh * scale))
print(f'ONE-step Lanczos downsample {mw}x{mh} -> {tw}x{th}')
small = cv2.resize(crop, (tw, th), interpolation=cv2.INTER_LANCZOS4)
del crop, img, nonwhite, band, dark

page = np.full((page_h_px, page_w_px, 3), 255, np.uint8)
ox = int(round(WHITE_MARGIN * scale))
oy = int(round(WHITE_MARGIN * scale))
page[oy:oy + th, ox:ox + tw] = small

# caption inside the bottom margin (below map content, white ground)
pil = Image.fromarray(page)
draw = ImageDraw.Draw(pil)
f1 = ImageFont.truetype(FONT, line_h1)
f2 = ImageFont.truetype(FONT, line_h2)
lines = [s.strip() for s in CAPTION.split(' / ')]
y = oy + th + pad_top
for text, f in zip(lines, (f1, f2, f2)):
    tb = draw.textbbox((0, 0), text, font=f)
    tx = (page_w_px - (tb[2] - tb[0])) // 2
    assert y + (tb[3] - tb[1]) < page_h_px, 'caption must stay on the page'
    draw.text((tx, y), text, fill=(30, 30, 30), font=f)
    y += (f.size + gap)
assert y - gap + pad_bot <= page_h_px + 4
page = np.asarray(pil)

# ---------------------------------------------------------------- outputs
jpg_path = f'{DELIV}/Galveston_1912_Wharf_Downtown_print.jpg'
pdf_path = f'{DELIV}/Galveston_1912_Wharf_Downtown_print.pdf'
cv2.imwrite(jpg_path, page[:, :, ::-1],
            [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY,
             cv2.IMWRITE_JPEG_PROGRESSIVE, 0])           # baseline JPEG

doc = pymupdf.open()
pw_pt, ph_pt = page_w_px / DPI * 72.0, page_h_px / DPI * 72.0
p = doc.new_page(width=pw_pt, height=ph_pt)
p.insert_image(pymupdf.Rect(0, 0, pw_pt, ph_pt), filename=jpg_path)
doc.set_metadata({
    'title': 'Galveston, Texas - Wharf Front and Downtown, 1912 '
             '(Sanborn composite)',
    'subject': 'Composite of the 1912 Sanborn Fire Insurance Map of '
               'Galveston, LOC sanborn08539_004',
    'creator': 'galveston-1912 reconstruction pipeline',
})
doc.save(pdf_path, garbage=4, deflate=True)
doc.close()

master_copy = f'{DELIV}/Galveston_1912_SelectedArea_HISTORICAL_MASTER.tif'
shutil.copyfile(f'{FINAL}/master_full.tif', master_copy)

sums = {}
for path in (pdf_path, master_copy, jpg_path):
    sums[os.path.basename(path)] = sha256_file(path)
with open(f'{DELIV}/SHA256SUMS.txt', 'w') as f:
    for name, h in sums.items():
        f.write(f'{h}  {name}\n')

comp = {
    'source': {'path': '60_master/final/master_full.tif',
               'sha256': sums['Galveston_1912_SelectedArea_HISTORICAL_MASTER.tif']},
    'map_rect_canvas_xyxy': [map_x0, map_y0, map_x1, map_y1],
    'map_rect_mosaic_xyxy': [map_x0 + CX0, map_y0 + CY0,
                             map_x1 + CX0, map_y1 + CY0],
    'westernmost_drawn_ink_mosaic_x': ink_x0 + CX0,
    'west_bound_rule': 'westernmost drawn content (graphic scale bar) minus '
                       f'{WHITE_MARGIN} px drawn-water margin; longest pier '
                       f'head retains >> {WATER_MARGIN} px of drawn water',
    'water_margin_required_beyond_longest_pier_px': WATER_MARGIN,
    'white_margin_mosaic_px': {'top': WHITE_MARGIN, 'left': WHITE_MARGIN,
                               'right': WHITE_MARGIN,
                               'bottom': bottom_margin_mosaic},
    'resample': {'method': 'cv2.INTER_LANCZOS4', 'steps': 1,
                 'scale': scale, 'upsampled': False},
    'page': {'px': [page_w_px, page_h_px], 'dpi': DPI,
             'inches': [page_w_px / DPI, page_h_px / DPI],
             'points': [pw_pt, ph_pt]},
    'paper_flatfield': dict(ff_stats, decision='D-017',
                            spec='50_seams/paper_flatfield.json',
                            spec_sha256=sha256_file(FF_SPEC),
                            applied_to='print deliverable only',
                            master_full_tif_modified=False),
    'tone_match': dict(tone_stats, decision='D-016',
                       spec='50_seams/tone_anchors.json',
                       spec_sha256=sha256_file(TONE_SPEC),
                       applied_to='print deliverable only',
                       master_full_tif_modified=False),
    'water_treatment': dict(water_stats, decision='D-015',
                            spec='50_seams/water_regions.geojson',
                            spec_sha256=sha256_file(WATER_SPEC),
                            applied_to='print deliverable only',
                            master_full_tif_modified=False),
    'jpeg_quality': JPEG_QUALITY,
    'caption_lines': lines,
    'sha256': sums,
}
with open(f'{DELIV}/print_composition.json', 'w') as f:
    json.dump(comp, f, indent=1)

print(json.dumps({k: v for k, v in comp.items() if k != 'sha256'}, indent=1))
for n, h in sums.items():
    print(f'{h}  {n}')
print('PDF size bytes:', os.path.getsize(pdf_path))
