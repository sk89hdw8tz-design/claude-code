"""Presentation-stage water treatment for the 1912 print deliverable (D-015).

Fills open water -- Galveston Bay, the slips, and the frontage bands -- with the
flat colour the 1899 companion sheet uses, RGB(199,214,209), measured off that
sheet (84.7% of its bay region carries that literal value; p5 = p95 = median, so
its bay is a flat fill and not scanned tint).

Why a mask and not a colour key: the 1912 bay measures -12.5 on B-(R+G)/2 and a
blank downtown street measures -11.5, so colour alone cannot tell water from
paper. The 1912 plates DO tint the bay -- sheet 5's water reads 30-43 levels
cooler than its own bare paper -- but over strongly yellowed paper on a dim scan
it composites to warm grey.

Shape comes from an ink-constrained flood fill seeded inside `seed_*` polygons
and capped by `bound` (50_seams/water_regions.geojson). The flood snaps to the
drafted shoreline and reaches every slip that is open to the bay, which is what
"all water" means hydrographically, without hand-tracing a pier face.

Ink is composited, never thresholded away: a continuous coverage alpha keeps the
"Galveston Bay" lettering, compass roses, scale bar, soundings, pier outlines and
bulkheads at full darkness with clean antialiased edges over the flat colour.

Applied ONLY on the way to the PDF. master_full.tif and the archival scans are
never written by this module.
"""

import json

import cv2
import numpy as np

WATER_RGB = (199, 214, 209)      # measured on the 1899 companion print
INK_LO, INK_HI = 0.78, 0.94      # rel = grey/local paper; >=HI pure water, <=LO solid ink
BARRIER_ALPHA = 0.35             # alpha above this blocks the flood
HOLE_MAX_PX = 400000             # largest island of non-water that may be absorbed
WORK_RECT = (2600, 0, 9400, 14489)   # canvas x0,y0,x1,y1 enclosing `bound`


def _polys(spec_path):
    geo = json.load(open(spec_path))
    seeds, bounds = [], []
    for f in geo["features"]:
        ring = np.array(f["geometry"]["coordinates"][0], np.float64)
        (seeds if f["properties"]["role"] == "seed" else bounds).append(ring)
    if not seeds or not bounds:
        raise ValueError("water_regions.geojson needs at least one seed and one bound")
    return seeds, bounds


def ink_alpha(bgr_or_rgb):
    """Continuous ink coverage in [0,1], flat-fielded against local paper level.

    Same flat-fielding used for the Pier 22 diagnosis (60_master/tools/
    pier22_anaglyph.py): the sheets differ in tone by tens of levels, so any
    fixed grey threshold measures illumination rather than line work.
    """
    g = bgr_or_rgb.mean(axis=2).astype(np.float32)
    bg = cv2.morphologyEx(g, cv2.MORPH_CLOSE,
                          cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (61, 61)))
    bg = cv2.blur(bg, (121, 121))
    rel = g / np.maximum(bg, 1.0)
    return np.clip((INK_HI - rel) / (INK_HI - INK_LO), 0.0, 1.0)


def build_mask(img, spec_path):
    """Boolean water mask over the whole canvas, plus the alpha used to build it."""
    H, W = img.shape[:2]
    x0, y0, x1, y1 = WORK_RECT
    x1, y1 = min(x1, W), min(y1, H)
    sub = np.ascontiguousarray(img[y0:y1, x0:x1])

    # Neutralise uncovered canvas BEFORE estimating ink.
    #
    # Uncovered canvas is exact 255 white -- geometry, not image content. Left
    # in place it wrecks the flat-fielding: the 121 px background blur reads it
    # as very bright paper, so genuine bay tint within ~60 px of the boundary
    # scores rel ~ 0.75 and is misclassified as ink. That produced a hairline
    # of unfilled water tracing the panel coverage edges -- which looked like a
    # page edge in the scan but was an artefact of this detector.
    #
    # Replacing it with the median tone of covered water inside the seed makes
    # the background continuous across the boundary. It cannot affect output:
    # these pixels are uncovered, so their alpha is 0 and they receive the flat
    # fill regardless of what stands in for them here.
    seeds, bounds = _polys(spec_path)
    hb, wb = y1 - y0, x1 - x0
    sd = np.zeros((hb, wb), np.uint8)
    for r in seeds:
        cv2.fillPoly(sd, [np.round(r - [x0, y0]).astype(np.int32)], 1)
    uncov = (sub[:, :, 0] == 255) & (sub[:, :, 1] == 255) & (sub[:, :, 2] == 255)
    covered_seed = (sd > 0) & ~uncov
    work = sub
    if uncov.any() and covered_seed.any():
        neutral = np.median(sub[covered_seed], axis=0).astype(np.uint8)
        work = sub.copy()
        work[uncov] = neutral
    alpha = ink_alpha(work)

    bnd = np.zeros((hb, wb), np.uint8)
    for r in bounds:
        cv2.fillPoly(bnd, [np.round(r - [x0, y0]).astype(np.int32)], 1)

    allowed = ((alpha < BARRIER_ALPHA) & (bnd > 0)).astype(np.uint8)
    n, lab = cv2.connectedComponents(allowed, connectivity=4)
    keep = np.unique(lab[(sd > 0) & (allowed > 0)])
    keep = keep[keep != 0]
    water_sub = np.isin(lab, keep)
    del lab

    # Absorb islands entirely enclosed by water. The flood stops at ink, so
    # without this every stroke of the "Galveston Bay" lettering, the compass
    # roses, the scale bar and the soundings sit outside the mask and keep the
    # old warm paper tone in their antialiased edges -- a grey halo around each
    # mark on flat blue. It also closes the hairline left where panel A's warped
    # page edge meets the uncovered canvas, which is a render artefact of the
    # composite rather than anything drafted.
    # Land is never absorbed: piers join the shore, so the land component
    # reaches the work-rect border. HOLE_MAX_PX is a second guard against
    # swallowing any large enclosed body.
    inv = (~water_sub & (bnd > 0)).astype(np.uint8)
    n2, lab2, st2, _ = cv2.connectedComponentsWithStats(inv, connectivity=4)
    border = np.unique(np.concatenate([lab2[0], lab2[-1], lab2[:, 0], lab2[:, -1]]))
    absorbed = 0
    fill = np.zeros(n2, bool)
    for i in range(1, n2):
        if i in border or st2[i, 4] > HOLE_MAX_PX:
            continue
        fill[i] = True
        absorbed += int(st2[i, 4])
    water_sub |= fill[lab2]
    del lab2, inv

    water = np.zeros((H, W), bool)
    water[y0:y1, x0:x1] = water_sub
    a = np.zeros((H, W), np.float32)
    a[y0:y1, x0:x1] = alpha
    return water, a, {"components_kept": int(len(keep)),
                      "components_total": int(n - 1),
                      "enclosed_islands_absorbed_px": absorbed,
                      "uncovered_canvas_neutralised_px": int(uncov.sum())}


def apply(img, spec_path, mask_img=None):
    """Return (treated copy, stats). Pure: `img` is not modified.

    mask_img: image to build the water mask and ink alpha on. Defaults to
    `img`. Pass the ORIGINAL master when `img` has been tone-matched (D-016):
    the mask logic keys uncovered canvas on exact-255 pixels, and the highlight
    shoulder maps 255 to ~251, so the mask must be measured on the original
    while the fill is applied to the adjusted image.
    """
    if mask_img is None:
        mask_img = img
    water, alpha, st = build_mask(mask_img, spec_path)
    out = img.copy()
    idx = np.where(water)
    if len(idx[0]):
        a = alpha[idx][:, None]
        orig = out[idx].astype(np.float32)
        tgt = np.array(WATER_RGB, np.float32)[None, :]
        out[idx] = np.round(a * orig + (1.0 - a) * tgt).astype(np.uint8)

    was_white = ((mask_img[:, :, 0] == 255) & (mask_img[:, :, 1] == 255)
                 & (mask_img[:, :, 2] == 255))
    st.update({
        "water_rgb": list(WATER_RGB),
        "ink_alpha_band": [INK_LO, INK_HI],
        "barrier_alpha": BARRIER_ALPHA,
        "work_rect_canvas": list(WORK_RECT),
        "recoloured_px": int(water.sum()),
        "recoloured_from_uncovered_canvas_px": int((water & was_white).sum()),
        "recoloured_from_scanned_tint_px": int((water & ~was_white).sum()),
        "ink_px_preserved_in_mask": int((water & (alpha > 0.5)).sum()),
    })
    ys, xs = idx
    if len(ys):
        st["recoloured_bbox_canvas"] = [int(xs.min()), int(ys.min()),
                                        int(xs.max()) + 1, int(ys.max()) + 1]
    return out, st
