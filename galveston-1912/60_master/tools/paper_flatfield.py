"""Per-plate illumination (vignetting) correction for the print (D-017, D-019).

Each LOC plate was photographed with its centre brightest and its edges falling
off, so the same street reads bright mid-sheet and dark near a seam, and dark
bands run along every join. Measured in master space: paper varies 18.9 levels
between plates and 26.0 levels WITHIN a plate (p10-p90), so a per-sheet constant
cannot fix it -- the correction has to vary inside each plate.

Method: estimate the blank-paper level as a smooth field INSIDE each source
region separately (normalized convolution, so the field is never smeared across
a seam), then scale every pixel by target/field. The gain is multiplicative, so
black maps to black and hue is preserved: ink stays ink and type legibility
cannot fall.

D-019 revision -- pixel-accurate region gains. The first implementation
rasterized its region map in 128 px cells, so gain steps landed NEAR but not ON
the ownership seams, painting misaligned pale rectangles wherever ownership is
fine-grained (the wharf yard's content-frontier staircase; every panel/block
border). Regions now come from the compositor's own ownership_map.tif, each
region's field is extrapolated over the whole grid, and the gain applied to a
pixel is ITS OWN region's gain sampled bilinearly -- so tone transitions sit
exactly on the source seams, where matching each side to the common target
makes them invisible.

Runs on the master before tone_match. master_full.tif and the archival scans are
never written.
"""

import json

import cv2
import numpy as np
import tifffile

CELL = 128          # canvas px per field cell
STRIP = 1024


def build_fields(img, own, spec_path):
    """Per-region gain grids (each extrapolated over the full cell grid).

    Returns (gains: {rid: float32 grid (gh,gw,3)}, valid_cells, tgt, stats).
    Estimator: mean of the brightest `bright_frac` of a cell's paper
    candidates -- a median is pulled down by grey fills and shading and
    over-brightens those cells; the bright tail keys the field to blank paper.
    """
    spec = json.load(open(spec_path))
    tgt = np.array(spec["target"]["master_space_rgb"], np.float32)
    pd = spec["method"]["paper_detect"]
    fs = spec["method"]["field"]
    DS = int(fs.get("downsample", 4))
    bf = float(fs.get("bright_frac", 0.30))
    lo, hi = spec["method"]["gain"]["clamp"]
    H, W = img.shape[:2]
    gh, gw = H // CELL + 1, W // CELL + 1

    sm = img[::DS, ::DS]
    own_sm = own[::DS, ::DS]
    hsv = cv2.cvtColor(sm, cv2.COLOR_RGB2HSV)
    pap = ((hsv[:, :, 1].astype(np.float32) / 255 < pd["max_saturation"])
           & (hsv[:, :, 2].astype(np.float32) > pd["min_value"])
           & (own_sm > 0))
    pap &= ~((sm[:, :, 0] == 255) & (sm[:, :, 1] == 255) & (sm[:, :, 2] == 255))

    c = max(CELL // DS, 1)
    lum_sm = (0.299 * sm[:, :, 0] + 0.587 * sm[:, :, 1] + 0.114 * sm[:, :, 2])
    minpx = max(int(fs["min_paper_px_per_cell"]) // (DS * DS), 8)
    nreg = int(own.max())
    mean = np.zeros((nreg + 1, gh, gw, 3), np.float32)
    cnt = np.zeros((nreg + 1, gh, gw), np.int32)
    for gy in range(min(gh, sm.shape[0] // c + 1)):
        y0, y1 = gy * c, min((gy + 1) * c, sm.shape[0])
        if y1 <= y0:
            continue
        for gx in range(min(gw, sm.shape[1] // c + 1)):
            x0, x1 = gx * c, min((gx + 1) * c, sm.shape[1])
            if x1 <= x0:
                continue
            msk = pap[y0:y1, x0:x1]
            if int(msk.sum()) < minpx:
                continue
            rids = own_sm[y0:y1, x0:x1][msk]
            vals = sm[y0:y1, x0:x1][msk]
            lums = lum_sm[y0:y1, x0:x1][msk]
            # per region present in this cell
            for r in np.unique(rids):
                sel = rids == r
                n = int(sel.sum())
                if n < minpx:
                    continue
                v = vals[sel]
                l = lums[sel]
                k = max(int(n * bf), 4)
                idx = np.argpartition(l, n - k)[n - k:]
                mean[r, gy, gx] = v[idx].mean(axis=0)
                cnt[r, gy, gx] = n

    sig = float(fs["smooth_sigma_cells"])
    gains = {}
    n_est = 0
    for r in range(1, nreg + 1):
        wgt = (cnt[r] > 0).astype(np.float32)
        if wgt.sum() < 8:
            continue
        n_est += int(wgt.sum())
        den = cv2.GaussianBlur(wgt, (0, 0), sig)
        field = np.empty((gh, gw, 3), np.float32)
        for ch in range(3):
            num = cv2.GaussianBlur(mean[r, :, :, ch] * wgt, (0, 0), sig)
            fallback = float(np.median(mean[r, :, :, ch][cnt[r] > 0]))
            # extrapolate the region's own level over the WHOLE grid so
            # bilinear sampling near its borders never mixes with a
            # neighbouring region's level
            field[:, :, ch] = np.where(den > 1e-4,
                                       num / np.maximum(den, 1e-6), fallback)
        g = tgt[None, None, :] / np.maximum(field, 1.0)
        gains[r] = np.clip(g, lo, hi).astype(np.float32)
    stats = {"regions_with_field": len(gains),
             "field_cells_measured": n_est,
             "gain_clamp": [lo, hi]}
    return gains, tgt, stats


def apply(img, spec_path, ownership_map_path):
    """Return (corrected copy, stats). `img` is RGB uint8, not modified.

    ownership_map_path: the compositor's ownership_map.tif (uint8 region id per
    pixel; 0 = uncovered canvas, which keeps gain 1.0).
    """
    own = tifffile.imread(ownership_map_path)
    assert own.shape == img.shape[:2], (own.shape, img.shape)
    gains, tgt, st = build_fields(img, own, spec_path)

    H, W = img.shape[:2]
    out = np.empty_like(img)
    clipped = 0
    gmin, gmax = 10.0, 0.0
    for y0 in range(0, H, STRIP):
        y1 = min(y0 + STRIP, H)
        rows = np.linspace(y0 / CELL, y1 / CELL, y1 - y0,
                           endpoint=False, dtype=np.float32)
        cols = np.linspace(0, W / CELL, W, endpoint=False, dtype=np.float32)
        mapx = np.repeat(cols[None, :], y1 - y0, 0)
        mapy = np.repeat(rows[:, None], W, 1)
        g = np.ones((y1 - y0, W, 3), np.float32)
        strip_own = own[y0:y1]
        for r in np.unique(strip_own):
            if r == 0 or r not in gains:
                continue
            gr = cv2.remap(gains[r], mapx, mapy, interpolation=cv2.INTER_LINEAR,
                           borderMode=cv2.BORDER_REPLICATE)
            sel = strip_own == r
            g[sel] = gr[sel]
        gmin, gmax = min(gmin, float(g.min())), max(gmax, float(g.max()))
        x = img[y0:y1].astype(np.float32) * g
        clipped += int((x > 255).any(axis=2).sum())
        out[y0:y1] = np.clip(x, 0, 255).astype(np.uint8)

    st.update({"target_master_rgb": [float(v) for v in tgt],
               "cell_canvas_px": CELL,
               "gain_min": gmin, "gain_max": gmax,
               "px_clipped_by_gain": clipped,
               "region_source": "compositor ownership_map (pixel-accurate)"})
    return out, st
