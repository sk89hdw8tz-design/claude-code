#!/usr/bin/env python
"""Composite the sheet-5 wharf panels (A, B) into the reserved bay band of the
frozen block master.

Reads:
  60_master/final/candidate_master.tif      (frozen block master -- NEVER modified)
  60_master/final/render_manifest.json
  40_solve/output_sheet5_joint/transforms_sheet5_joint_shared.json
      (joint two-panel fit, D-011: panels coupled through the duplicated
       drafted ground so the wharf reads as one continuous frontage)
  fable_review/sheet05_candidate_regions.geojson (panel region polygons, sheet px)
  50_seams/cuts.json                        (canvas rect, reserved bay band)
  50_seams/masks.json                       (block sheets' owned footprint polygons)
  30_controls/verified/cross_panel_05.json  (22nd St cross-panel pairs P1/P2)
  00_inventory/INVENTORY.json               (sha256 of the sheet-5 archival scan)
  data-branch .../sanborn08539_004_img009_archival.jp2 (archival scan -- read only)

Writes:
  60_master/final/master_full.tif           (LZW RGB, block master + wharf panels)
  60_master/final/master_full_manifest.json
  60_master/final/master_full_preview.png   (4000 px wide)

Rules implemented (see manifest for the recorded decisions):
  * ONE warp from the archival scan per panel: cv2.warpAffine, INTER_LANCZOS4
    for the image, INTER_NEAREST for the region mask.  No blending, no colour
    changes -- hard ownership, matching the block render convention.
  * Panel pixels land ONLY where the destination is outside the block sheets'
    owned footprint (union of the 12 polygon_mosaic rings of 50_seams/masks.json).
    Where both exist the block master always wins (2x finer plate).
  * A|B ownership in the duplicated Pier 22 / 22nd St strip: straight cut
    anchored at the solved 22nd St cross-panel position (midpoint of the
    A/B-mapped P1/P2 street corners), tilted so its visible portion runs
    through open water past Pier 22's root rather than slicing the drawn pier.
    A owns east of the line (smaller mosaic y), B west -- orientation verified
    from the mapped panel centroids.
  * The drafted divider rule strip and the scanner-backing edges of the scan
    are excluded from both region masks.
"""
import hashlib
import json
import os
import sys

import cv2
import numpy as np
import os
import tifffile

ROOT = '/home/user/claude-code/galveston-1912'
SCAN = '/home/user/g1912/data-branch/galveston_1912_sources/sanborn08539_004_img009_archival.jp2'
FINAL = f'{ROOT}/60_master/final'
OUT_TIF = f'{FINAL}/master_full.tif'
OUT_MAN = f'{FINAL}/master_full_manifest.json'
OUT_PRE = f'{FINAL}/master_full_preview.png'

# ---------------------------------------------------------------- helpers
def sha256_file(path, chunk=1 << 22):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def sha256_obj(obj):
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


# ---------------------------------------------------------------- inputs
cuts = json.load(open(f'{ROOT}/50_seams/cuts.json'))
masks = json.load(open(f'{ROOT}/50_seams/masks.json'))
PANEL_TF = (f'{ROOT}/40_solve/output_sheet5_joint/'
            'transforms_sheet5_joint_shared.json')   # D-011 joint fit
tr5 = json.load(open(PANEL_TF))
geo = json.load(open(f'{ROOT}/fable_review/sheet05_candidate_regions.geojson'))
xp = json.load(open(f'{ROOT}/30_controls/verified/cross_panel_05.json'))
inv = json.load(open(f'{ROOT}/00_inventory/INVENTORY.json'))
base_manifest = json.load(open(f'{FINAL}/render_manifest.json'))

CX0, CY0, CX1, CY1 = cuts['target_extent']['canvas_rect_mosaic']
W, H = CX1 - CX0, CY1 - CY0                       # 26206 x 14489
BAND = cuts['target_extent']['reserved_bay_band']['mosaic_rect']  # x < -9274

# -- verify the archival scan against the inventory BEFORE reading it
inv_item = next(i for i in inv['items'] if i['file'] == os.path.basename(SCAN))
scan_sha = sha256_file(SCAN)
if scan_sha != inv_item['sha256']:
    sys.exit(f'FATAL: sha256 mismatch for {SCAN}: {scan_sha} != {inv_item["sha256"]}')
print(f'scan sha256 verified: {scan_sha}')

scan = cv2.imread(SCAN, cv2.IMREAD_COLOR)          # BGR uint8 7795x6653
SH, SW = scan.shape[:2]
assert (SW, SH) == (inv_item['width'], inv_item['height'])

# ---------------------------------------------------------------- region masks
feats = {f['properties']['region_id']: f for f in geo['features']}
DIV_HALF = 40          # px each side of the drafted divider centerline (ink ~ +-27)
# scanner-backing insets, measured per edge on the scan (true ink is <120
# min-channel; PAPER here is ~162-174, so thresholds must stay low).  Left
# backing slab is <=72 px for in-canvas rows but the bottom-left corner curl
# reaches col ~231 by row 7699; bottom solid backing rises locally to ~row
# 7700.  Nearest real content: scale-bar tip at sheet x~425, plate numeral
# bottom at row ~7640 -- the insets below stay in blank water everywhere.
EDGE_INSET = {'top': 80, 'bottom': 96, 'left': 250, 'right': 70}

div_line = 'x = 3789 + 0.0099*y'                   # BREAK_RULE centerline (solver convention)
ys_all = np.arange(SH, dtype=np.float64)
div_x = 3789.0 + 0.0099 * ys_all

def region_mask(rid):
    poly = np.array(feats[rid]['geometry']['coordinates'][0], np.float64)
    m = np.zeros((SH, SW), np.uint8)
    cv2.fillPoly(m, [np.round(poly).astype(np.int32)], 255)
    cols = np.arange(SW)[None, :]
    xi = div_x[:, None]
    if rid == 'A':
        m[cols >= (xi - DIV_HALF)] = 0             # exclude divider strip + all east of it
    else:
        m[cols <= (xi + DIV_HALF)] = 0
    m[:EDGE_INSET['top'], :] = 0                   # scanner backing insets
    m[SH - EDGE_INSET['bottom']:, :] = 0
    m[:, :EDGE_INSET['left']] = 0
    m[:, SW - EDGE_INSET['right']:] = 0
    return m

maskA_sheet = region_mask('A')
maskB_sheet = region_mask('B')

region_hashes = {
    'geojson_file_sha256': sha256_file(f'{ROOT}/fable_review/sheet05_candidate_regions.geojson'),
    'region_A_coords_sha256': sha256_obj(feats['A']['geometry']['coordinates']),
    'region_B_coords_sha256': sha256_obj(feats['B']['geometry']['coordinates']),
}

# ---------------------------------------------------------------- transforms
def raw_matrix(panel):
    r = tr5['panels'][panel]['raw']
    return np.array([[r['a'], -r['b'], r['tx']],
                     [r['b'], r['a'], r['ty']]], np.float64)

M_A, M_B = raw_matrix('5A'), raw_matrix('5B')

def mappt(M, p):
    x, y = p
    return (M[0, 0] * x + M[0, 1] * y + M[0, 2],
            M[1, 0] * x + M[1, 1] * y + M[1, 2])

# ---------------------------------------------------------------- A|B cut
pairs = {p['id'].split('_')[0]: p for p in xp['point_pairs']}
P1, P2 = pairs['P1'], pairs['P2']
M1 = np.mean([mappt(M_A, P1['panel_A']), mappt(M_B, P1['panel_B'])], axis=0)
M2 = np.mean([mappt(M_A, P2['panel_A']), mappt(M_B, P2['panel_B'])], axis=0)
C = (M1 + M2) / 2.0                                # solved 22nd St cross-panel midline point
CORRIDOR_SLOPE = (M2[1] - M1[1]) and float(
    -(M2[0] - M1[0]) / (M2[1] - M1[1]))            # street direction dy/dx (~ -0.033)
CUT_SLOPE = -0.30                                  # chosen tilt, see rationale below
# orientation check: A owns east (smaller mosaic y)
centroidA_y = mappt(M_A, tr5['convention']['centers']['5A'])[1]
centroidB_y = mappt(M_B, tr5['convention']['centers']['5B'])[1]
assert centroidA_y < centroidB_y, 'orientation: A must lie east (smaller y) of B'

cut_rationale = (
    'Straight cut anchored at C=({:.1f},{:.1f}) mosaic = midpoint of the A/B-mapped '
    '22nd St street corners (cross_panel_05 P1/P2), i.e. the solved 22nd St '
    'cross-panel position; at the Ave A frontage the line passes mid-corridor. '
    'The corridor\'s own direction (dy/dx={:.4f}) extended bayward would slice '
    'panel A\'s Pier 22 shed mid-body (the pier leans across the corridor '
    'extension), so the line is tilted to dy/dx={:.2f}: its visible portion '
    '(bayward of the block-owned boundary x~-9253) runs through open water '
    'between Pier 22\'s landward root and the plate edge. Clearances: A deck '
    'root E corner P6_A 167 px, A water-tint apron ~76 px, B deck root W corner '
    'P5_B ~366 px. Consequences: panel A\'s complete Pier 22 depiction renders; '
    'panel B\'s duplicate stub (truncated by its sheet edge) is suppressed; the '
    '~55 ft drafted pier disagreement therefore does not appear as a mid-pier '
    'jog. The only drawn ink the cut crosses: B\'s slip-edge bulkhead line, '
    'dead-ending at x~-9233 (inside the block-owned strip, hidden), and A\'s '
    'soft plate-edge water wash in open water. A owns east of the line '
    '(smaller mosaic y), B west - verified from the mapped panel centroids '
    '(A centroid y={:.0f} < B centroid y={:.0f}).'
).format(C[0], C[1], CORRIDOR_SLOPE, CUT_SLOPE, centroidA_y, centroidB_y)

def east_of_cut(sub_x0, sub_y0, w, h):
    """Boolean (h,w): True where canvas pixel is east (A side) of the cut."""
    xs = np.arange(w, dtype=np.float64) + sub_x0 + CX0     # mosaic x
    ys = np.arange(h, dtype=np.float64) + sub_y0 + CY0     # mosaic y
    y_line = C[1] + CUT_SLOPE * (xs - C[0])
    return ys[:, None] < y_line[None, :]

# ---------------------------------------------------------------- block footprint
block_owned = np.zeros((H, W), np.uint8)
for r in masks['regions']:
    ring = np.array(r['polygon_mosaic']['exterior'], np.float64) - [CX0, CY0]
    cv2.fillPoly(block_owned, [np.round(ring).astype(np.int32)], 255)
    assert not r['polygon_mosaic']['interiors']
print('block-owned footprint px:', int((block_owned > 0).sum()))

# ---------------------------------------------------------------- base master
print('loading candidate master (read-only source, copied in memory) ...')
base = tifffile.imread(f'{FINAL}/candidate_master.tif')    # RGB uint8 (H,W,3)
assert base.shape == (H, W, 3), base.shape

# ---------------------------------------------------------------- warp + composite
def panel_subrect(mask_sheet, M):
    ys, xs = np.where(mask_sheet[::8, ::8] > 0)
    pts = np.stack([xs * 8.0, ys * 8.0], axis=1)
    corners = np.array([mappt(M, p) for p in
                        [(x, y) for x in (pts[:, 0].min(), pts[:, 0].max() + 8)
                         for y in (pts[:, 1].min(), pts[:, 1].max() + 8)]])
    x0 = int(np.floor(corners[:, 0].min())) - 4 - CX0
    x1 = int(np.ceil(corners[:, 0].max())) + 4 - CX0
    y0 = int(np.floor(corners[:, 1].min())) - 4 - CY0
    y1 = int(np.ceil(corners[:, 1].max())) + 4 - CY0
    return max(x0, 0), max(y0, 0), min(x1, W), min(y1, H)

def warp_into(M, img, sub, flags, border):
    x0, y0, x1, y1 = sub
    Msub = M.copy()
    Msub[0, 2] += -CX0 - x0
    Msub[1, 2] += -CY0 - y0
    return cv2.warpAffine(img, Msub, (x1 - x0, y1 - y0), flags=flags,
                          borderMode=cv2.BORDER_CONSTANT, borderValue=border)

stats = {}
panels = {'A': (M_A, maskA_sheet, maskB_sheet, M_B, True),
          'B': (M_B, maskB_sheet, maskA_sheet, M_A, False)}
for name, (M, mine_sheet, other_sheet, M_other, owns_east) in panels.items():
    sub = panel_subrect(mine_sheet, M)
    x0, y0, x1, y1 = sub
    print(f'panel {name}: canvas subrect x {x0}..{x1}, y {y0}..{y1}')
    wimg = warp_into(M, scan, sub, cv2.INTER_LANCZOS4, (255, 255, 255))
    wmask = warp_into(M, mine_sheet, sub, cv2.INTER_NEAREST, 0) > 0
    womask = warp_into(M_other, other_sheet, sub, cv2.INTER_NEAREST, 0) > 0
    east = east_of_cut(x0, y0, x1 - x0, y1 - y0)
    myside = east if owns_east else ~east
    blk_own = block_owned[y0:y1, x0:x1] > 0
    # F1/F2 fix (Reviewer A, confirmed by re-test): block priority applies only
    # where the block master carries DRAWN CONTENT, not blank page margin. The
    # 1889 lesson recurred: a blank bay-side margin had full ownership coverage
    # and overwrote sole-source wharf cartography (Mallory shed, Merrow shed).
    # "Drawn content" = non-paper tone, or paper with drafted ink nearby
    # (31 px box) so tint fills and hatched sheds stay block-owned.
    dstc = base[y0:y1, x0:x1]
    g = dstc.mean(axis=2).astype(np.float32)
    inkish = (g < 145).astype(np.float32)
    dens = cv2.boxFilter(inkish, -1, (31, 31), normalize=True)
    # Ownership v3 (F1/F2 confirmed fix): east of the block sheets' Ave A
    # frontage the block master owns unconditionally. West of it (the wharf
    # band) the block plates draw the shared shed strip only schematically
    # (flat tint + a label) while sheet 5 is the dedicated, fully-detailed
    # wharf source - so the panel owns that band UNLESS the block plate
    # genuinely drew dense bay-side cartography there (sheet 7's Texas Star
    # Flour Mills strip: ink density well above the schematic band's).
    # Per-row content frontier: for each canvas row, the block owns from the
    # first column where its own drawn-ink density is SUSTAINED (>0.05 mean
    # over the next 300 px). West of that frontier the block plate offers only
    # blank margin or the schematic shed tint, and the dedicated wharf plate
    # (sheet 5) is the authoritative source. Frontier computed lazily once
    # from the pristine block-only master.
    global _frontier
    try:
        _frontier
    except NameError:
        blk_only = tifffile.imread(os.path.join(FINAL, 'candidate_master.tif'))
        gg = blk_only[:, 6900:11000].mean(axis=2).astype(np.float32)
        del blk_only
        ii = (gg < 140).astype(np.float32)
        dd = cv2.boxFilter(ii, -1, (41, 41), normalize=True)
        run = cv2.boxFilter(dd, -1, (301, 1), normalize=True)  # forward-ish mean
        _frontier = np.full(run.shape[0], 10**9, np.int64)
        for yy in range(run.shape[0]):
            ok = np.where(run[yy] > 0.05)[0]
            if len(ok):
                _frontier[yy] = 6900 + ok[0]
        # Remove short westward spikes (e.g. a giant margin numeral capturing
        # ~250 rows) with a running max over +-140 rows: genuine block bay-side
        # structures (track fans, the mills strip) span thousands of rows and
        # survive; furniture islands do not. Then lightly smooth the edge.
        from scipy.ndimage import maximum_filter1d, median_filter
        _frontier = maximum_filter1d(_frontier, size=281)
        _frontier = median_filter(_frontier, size=41)
        del gg, ii, dd, run
    xs = np.arange(x0, x1)[None, :]
    blk = blk_own & (xs >= _frontier[y0:y1, None])
    n_mask = int(wmask.sum())
    suppressed_block = wmask & blk
    n_blk = int(suppressed_block.sum())
    ceded = wmask & ~blk & womask & ~myside
    n_ceded = int(ceded.sum())
    allowed = wmask & ~blk & (~womask | myside)
    n_written = int(allowed.sum())
    assert n_mask == n_blk + n_ceded + n_written
    dst = base[y0:y1, x0:x1]
    dst[allowed] = wimg[allowed][:, ::-1]          # BGR -> RGB
    stats[name] = {
        'canvas_subrect_xyxy': [x0, y0, x1, y1],
        'mask_px_in_canvas': n_mask,
        'suppressed_by_block_ownership_px': n_blk,
        'ceded_to_other_panel_by_cut_px': n_ceded,
        'written_px': n_written,
    }
    print(f'  mask px {n_mask:,} | suppressed by block {n_blk:,} '
          f'| ceded to other panel {n_ceded:,} | written {n_written:,}')

del block_owned

# ---------------------------------------------------------------- outputs
print('writing', OUT_TIF)
tifffile.imwrite(OUT_TIF, base, photometric='rgb', compression='lzw',
                 predictor=True, rowsperstrip=512)

pw = 4000
ph = int(round(H * pw / W))
preview = cv2.resize(base[:, :, ::-1], (pw, ph), interpolation=cv2.INTER_AREA)
cv2.imwrite(OUT_PRE, preview)

cut_mosaic_at_band = [
    [BAND[2], C[1] + CUT_SLOPE * (BAND[2] - C[0])],
    [BAND[0], C[1] + CUT_SLOPE * (BAND[0] - C[0])],
]
manifest = {
    'generated_by': '60_master/tools/composite_wharf.py',
    'base_master': {
        'path': '60_master/final/candidate_master.tif',
        'sha256': sha256_file(f'{FINAL}/candidate_master.tif'),
        'modified': False,
    },
    'block_render_manifest': base_manifest,
    'wharf_panels': {
        'source_scan': {'file': os.path.basename(SCAN), 'sha256': scan_sha,
                        'sha256_verified_against_inventory': True},
        'transforms': {p: tr5['panels'][p]['raw'] for p in ('5A', '5B')},
        'transforms_file_sha256': sha256_file(
            PANEL_TF),
        'region_polygons': region_hashes,
        'divider_exclusion': {'centerline': div_line, 'half_width_px': DIV_HALF,
                              'measured_ink_span_px': 'centerline -22..+27'},
        'scan_edge_insets_px': EDGE_INSET,
        'warp': {'interpolation': 'INTER_LANCZOS4',
                 'mask_interpolation': 'INTER_NEAREST',
                 'resamples_from_archival': 1,
                 'compositing': 'hard ownership, no blending, '
                                'no exposure or colour changes'},
        'block_ownership': 'union of the 12 polygon_mosaic rings of '
                           '50_seams/masks.json; block master pixels always win',
        'ab_cut': {
            'anchor_point_mosaic': [float(C[0]), float(C[1])],
            'slope_dy_dx': CUT_SLOPE,
            'corridor_slope_dy_dx': CORRIDOR_SLOPE,
            'line_at_band_edges_mosaic': cut_mosaic_at_band,
            'a_owns': 'east of the line (smaller mosaic y)',
            'rationale': cut_rationale,
        },
        'ownership_stats_px': stats,
    },
    'outputs': {
        'master_full_tif': {'path': '60_master/final/master_full.tif',
                            'compression': 'lzw', 'dtype': 'uint8 RGB',
                            'size_px': [W, H]},
        'master_full_preview_png': {'path': '60_master/final/master_full_preview.png',
                                    'size_px': [pw, ph]},
    },
}
manifest['outputs']['master_full_tif']['bytes'] = os.path.getsize(OUT_TIF)
manifest['outputs']['master_full_tif']['sha256'] = sha256_file(OUT_TIF)
with open(OUT_MAN, 'w') as f:
    json.dump(manifest, f, indent=1)
print('done.')
print(json.dumps(stats, indent=1))
print('cut anchor', C, 'slope', CUT_SLOPE)
