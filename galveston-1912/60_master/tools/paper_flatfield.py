"""Per-plate illumination (vignetting) correction for the print (D-017).

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

Runs on the master before tone_match. master_full.tif and the archival scans are
never written.
"""

import json

import cv2
import numpy as np

CELL = 128          # canvas px per field cell
STRIP = 1024


def _regions(img_shape, spec_root):
    """Coarse region-id map: 1..N for block regions, then the two sheet-5 panels."""
    H, W = img_shape[:2]
    gh, gw = H // CELL + 1, W // CELL + 1
    rid = np.zeros((gh, gw), np.int32)
    masks = json.load(open(f"{spec_root}/50_seams/masks.json"))
    CX0, CY0 = -16734, -8279
    n = 0
    for r in masks["regions"]:
        n += 1
        ring = (np.array(r["polygon_mosaic"]["exterior"], np.float64) - [CX0, CY0]) / CELL
        cv2.fillPoly(rid, [np.round(ring).astype(np.int32)], n)
    # sheet-5 panels: warped region masks, same construction as composite_wharf
    import tone_match  # noqa: F401  (keeps import graph explicit)
    tf = json.load(open(f"{spec_root}/40_solve/output_sheet5_joint/"
                        "transforms_sheet5_joint_shared.json"))["panels"]
    geo = json.load(open(f"{spec_root}/fable_review/sheet05_candidate_regions.geojson"))
    feats = {f["properties"]["region_id"]: f for f in geo["features"]}
    SCAN_WH = (6653, 7795)
    div = lambda y: 3789.0 + 0.0099 * y
    for rid_name, key in (("A", "5A"), ("B", "5B")):
        n += 1
        poly = np.array(feats[rid_name]["geometry"]["coordinates"][0], np.float64)
        ms = np.zeros((SCAN_WH[1], SCAN_WH[0]), np.uint8)
        cv2.fillPoly(ms, [np.round(poly).astype(np.int32)], 255)
        cols = np.arange(SCAN_WH[0])[None, :]
        xi = div(np.arange(SCAN_WH[1], dtype=np.float64))[:, None]
        if rid_name == "A":
            ms[cols >= (xi - 40)] = 0
        else:
            ms[cols <= (xi + 40)] = 0
        r = tf[key]["raw"]
        # sheet px -> canvas -> cell units
        M = np.array([[r["a"] / CELL, -r["b"] / CELL, (r["tx"] - CX0) / CELL],
                      [r["b"] / CELL, r["a"] / CELL, (r["ty"] - CY0) / CELL]], np.float64)
        wm = cv2.warpAffine(ms, M, (gw, gh), flags=cv2.INTER_NEAREST,
                            borderMode=cv2.BORDER_CONSTANT, borderValue=0)
        rid[(wm > 0) & (rid == 0)] = n
    return rid, n


def build_field(img, spec_path, spec_root, water=None):
    """Smooth blank-paper level per source region.

    Estimated on a 1/DS downsample so a ROBUST per-cell statistic is affordable:
    the mean of the BRIGHTEST `bright_frac` of that cell's paper candidates. A
    median pulls the estimate down wherever the candidate set is polluted by grey
    fills or shading, which over-brightens those cells; taking the bright tail
    keys the field to true blank paper.
    """
    spec = json.load(open(spec_path))
    tgt = np.array(spec["target"]["master_space_rgb"], np.float32)
    pd = spec["method"]["paper_detect"]
    fs = spec["method"]["field"]
    DS = int(fs.get("downsample", 4))
    bf = float(fs.get("bright_frac", 0.30))
    H, W = img.shape[:2]
    gh, gw = H // CELL + 1, W // CELL + 1
    rid, nreg = _regions(img.shape, spec_root)

    sm = img[::DS, ::DS]
    hsv = cv2.cvtColor(sm, cv2.COLOR_RGB2HSV)
    pap = ((hsv[:, :, 1].astype(np.float32) / 255 < pd["max_saturation"])
           & (hsv[:, :, 2].astype(np.float32) > pd["min_value"]))
    pap &= ~((sm[:, :, 0] == 255) & (sm[:, :, 1] == 255) & (sm[:, :, 2] == 255))
    if water is not None:
        pap &= ~water[::DS, ::DS]

    c = max(CELL // DS, 1)
    lum_sm = (0.299 * sm[:, :, 0] + 0.587 * sm[:, :, 1] + 0.114 * sm[:, :, 2])
    mean = np.zeros((gh, gw, 3), np.float32)
    valid = np.zeros((gh, gw), bool)
    minpx = max(int(fs["min_paper_px_per_cell"]) // (DS * DS), 8)
    for gy in range(min(gh, sm.shape[0] // c + 1)):
        y0, y1 = gy * c, min((gy + 1) * c, sm.shape[0])
        if y1 <= y0:
            continue
        prow = pap[y0:y1]
        srow = sm[y0:y1]
        lrow = lum_sm[y0:y1]
        for gx in range(min(gw, sm.shape[1] // c + 1)):
            x0, x1 = gx * c, min((gx + 1) * c, sm.shape[1])
            if x1 <= x0:
                continue
            msk = prow[:, x0:x1]
            n = int(msk.sum())
            if n < minpx:
                continue
            v = srow[:, x0:x1][msk]
            l = lrow[:, x0:x1][msk]
            k = max(int(n * bf), 4)
            idx = np.argpartition(l, n - k)[n - k:]
            mean[gy, gx] = v[idx].mean(axis=0)
            valid[gy, gx] = True

    sig = float(fs["smooth_sigma_cells"])
    field = np.repeat(tgt[None, None, :], gh, 0).repeat(gw, 1).astype(np.float32)
    for r in range(1, nreg + 1):
        inr = rid == r
        wgt = (valid & inr).astype(np.float32)
        if wgt.sum() < 8:
            continue
        den = cv2.GaussianBlur(wgt, (0, 0), sig)
        for ch in range(3):
            num = cv2.GaussianBlur(mean[:, :, ch] * wgt, (0, 0), sig)
            fallback = float(np.median(mean[:, :, ch][valid & inr]))
            est = np.where(den > 1e-3, num / np.maximum(den, 1e-6), fallback)
            field[:, :, ch][inr] = est[inr]
    return field, rid, valid, tgt


def apply(img, spec_path, spec_root, water=None):
    """Return (corrected copy, stats). `img` is RGB uint8 and is not modified."""
    spec = json.load(open(spec_path))
    lo, hi = spec["method"]["gain"]["clamp"]
    field, rid, valid, tgt = build_field(img, spec_path, spec_root, water)
    gain = tgt[None, None, :] / np.maximum(field, 1.0)
    gain = np.clip(gain, lo, hi).astype(np.float32)

    H, W = img.shape[:2]
    out = np.empty_like(img)
    clipped = 0
    for y0 in range(0, H, STRIP):
        y1 = min(y0 + STRIP, H)
        # sample the coarse gain field for exactly these rows
        gy0, gy1 = y0 / CELL, y1 / CELL
        rows = np.linspace(gy0, gy1, y1 - y0, endpoint=False, dtype=np.float32)
        cols = np.linspace(0, W / CELL, W, endpoint=False, dtype=np.float32)
        mapx = np.repeat(cols[None, :], y1 - y0, 0)
        mapy = np.repeat(rows[:, None], W, 1)
        g = cv2.remap(gain, mapx, mapy, interpolation=cv2.INTER_LINEAR,
                      borderMode=cv2.BORDER_REPLICATE)
        x = img[y0:y1].astype(np.float32) * g
        clipped += int((x > 255).any(axis=2).sum())
        out[y0:y1] = np.clip(x, 0, 255).astype(np.uint8)

    lum = lambda c: 0.299 * c[..., 0] + 0.587 * c[..., 1] + 0.114 * c[..., 2]
    return out, {
        "target_master_rgb": [float(v) for v in tgt],
        "cell_canvas_px": CELL,
        "gain_clamp": [lo, hi],
        "gain_min": float(gain.min()), "gain_max": float(gain.max()),
        "gain_median": float(np.median(gain)),
        "field_cells_measured": int(valid.sum()),
        "field_cells_total": int(valid.size),
        "field_lum_min": float(lum(field).min()), "field_lum_max": float(lum(field).max()),
        "px_clipped_by_gain": clipped,
    }
