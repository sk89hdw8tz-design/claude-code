"""Phase C — compositing.

Hard-won rules encoded here:
- Clip windows shift ~half a street width PAST each boundary street so each
  street and its printed label belongs to exactly one sheet (no duplicates).
- The printed black map frame is searched for ONLY outside the outermost
  grid lines; an unconstrained search finds interior blocks and clips into
  the map. This same constrained search confines multi-panel sheets
  (1885 sheet 3 lower panel, sheet 11 upper-left) automatically.
- Tonal balance is per-sheet per-channel GAIN only, measured from bright
  low-saturation pixels on the central ~56% of the map interior (never the
  scanner margin), clamped 0.93-1.08, retargeted per edition paper tone.
- Warp exactly ONCE: the sheet->grid affine is composed with any output
  scale so no second resampling pass ever touches the lettering.
- Canvas is uint8; each sheet warps only into its destination ROI; blending
  runs in row chunks. No float32 full-canvas accumulator.
"""

import os

import numpy as np
import cv2

import config

cv2.setNumThreads(2)


def frame_bounds(img01, grid_v, grid_h, search_margin=0.12):
    """Find the printed black map frame, searching ONLY outside the outermost
    grid lines. Returns (x0, y0, x1, y1) clip rectangle in this image's
    coordinates. grid_v/grid_h are line positions at this image's scale."""
    gray = img01.mean(axis=2)
    dark = (gray < 0.45).astype(np.float32)
    h, w = gray.shape
    lo_v, hi_v = min(grid_v), max(grid_v)
    lo_h, hi_h = min(grid_h), max(grid_h)

    def edge(profile, inner, outer_limit, direction):
        # strongest dark line strictly between the outermost grid line and
        # the image edge (bounded by search_margin of the image size)
        if direction < 0:
            seg = profile[int(outer_limit) : int(inner)]
            if len(seg) < 3:
                return outer_limit
            return int(outer_limit) + int(np.argmax(seg))
        seg = profile[int(inner) : int(outer_limit)]
        if len(seg) < 3:
            return outer_limit
        return int(inner) + int(np.argmax(seg))

    col_dark = dark.mean(axis=0)
    row_dark = dark.mean(axis=1)
    x0 = edge(col_dark, lo_v, max(0, lo_v - search_margin * w), -1)
    x1 = edge(col_dark, hi_v, min(w, hi_v + search_margin * w), +1)
    y0 = edge(row_dark, lo_h, max(0, lo_h - search_margin * h), -1)
    y1 = edge(row_dark, hi_h, min(h, hi_h + search_margin * h), +1)
    return x0, y0, x1, y1


def paper_tone(img, frac=0.56, bright=170, sat_max=40):
    """Median BGR of bright, low-saturation pixels on the central `frac` of
    the map interior ONLY. Including scanner margin skews tone wildly."""
    h, w = img.shape[:2]
    cy, cx = round(h * (1 - frac) / 2), round(w * (1 - frac) / 2)
    c = img[cy : h - cy, cx : w - cx]
    c = c[::8, ::8].reshape(-1, 3).astype(np.int16)
    mx = c.max(axis=1)
    mn = c.min(axis=1)
    mask = (mx > bright) & ((mx - mn) < sat_max)
    if mask.sum() < 100:
        mask = mx > bright
    sel = c[mask] if mask.sum() >= 100 else c
    return np.median(sel, axis=0)


def channel_gains(sheet_tone, target_tone):
    g = np.asarray(target_tone, np.float64) / np.maximum(np.asarray(sheet_tone, np.float64), 1)
    return np.clip(g, *config.GAIN_CLAMP)


def clip_window(grid_v, grid_h, frame, shift, ext, composite_edges):
    """Clip rectangle for one sheet: past-boundary-street shift intersected
    with the printed frame. composite_edges = set of 'left','right','top',
    'bottom' edges where this sheet sits on the rim of the whole composite
    (extend outward by ext there instead of shifting)."""
    x0 = min(grid_v) + shift
    x1 = max(grid_v) + shift
    y0 = min(grid_h) + shift
    y1 = max(grid_h) + shift
    if "left" in composite_edges:
        x0 = min(grid_v) - ext
    if "right" in composite_edges:
        x1 = max(grid_v) + ext
    if "top" in composite_edges:
        y0 = min(grid_h) - ext
    if "bottom" in composite_edges:
        y1 = max(grid_h) + ext
    fx0, fy0, fx1, fy1 = frame
    return (max(x0, fx0), max(y0, fy0), min(x1, fx1), min(y1, fy1))


def feather_mask(w, h, feather):
    """Coarse (1/8-scale) float mask with feathered edges; warp with a scaled
    matrix rather than materializing a full-size float mask."""
    cw, ch, cf = max(1, w // 8), max(1, h // 8), max(1, feather // 8)
    m = np.ones((ch, cw), np.float32)
    ramp = np.linspace(0, 1, cf, endpoint=False, dtype=np.float32)
    m[:cf, :] *= ramp[:, None]
    m[-cf:, :] *= ramp[::-1][:, None]
    m[:, :cf] *= ramp[None, :]
    m[:, -cf:] *= ramp[::-1][None, :]
    return m


def warp_sheet_into(canvas, weight_hint, img, affine, clip, gains, feather):
    """Warp one clipped, gain-corrected sheet into its destination ROI on the
    uint8 canvas in a single resampling pass, blending in row chunks.

    affine: dict sx,tx,sy,ty (native px -> canvas px). weight_hint: uint8
    canvas-size array tracking blend weight (0..255) at 1/8 scale."""
    x0, y0, x1, y1 = [int(round(v)) for v in clip]
    sub = img[y0:y1, x0:x1]
    sub = np.clip(sub.astype(np.float32) * gains[None, None, :], 0, 255).astype(np.uint8)

    sx, sy = affine["sx"], affine["sy"]
    tx, ty = affine["tx"] + sx * x0, affine["ty"] + sy * y0
    dx0 = int(np.floor(tx))
    dy0 = int(np.floor(ty))
    dw = int(np.ceil(sub.shape[1] * sx)) + 1
    dh = int(np.ceil(sub.shape[0] * sy)) + 1
    dx0c, dy0c = max(0, dx0), max(0, dy0)
    dx1c = min(canvas.shape[1], dx0 + dw)
    dy1c = min(canvas.shape[0], dy0 + dh)
    if dx1c <= dx0c or dy1c <= dy0c:
        return

    M = np.array([[sx, 0, tx - dx0c], [0, sy, ty - dy0c]], np.float64)
    roi_w, roi_h = dx1c - dx0c, dy1c - dy0c
    warped = cv2.warpAffine(
        sub, M, (roi_w, roi_h),
        flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_CONSTANT, borderValue=0,
    )
    cm = feather_mask(sub.shape[1], sub.shape[0], feather)
    mask = cv2.resize(cm, (roi_w, roi_h), interpolation=cv2.INTER_LINEAR)

    chunk = 1500
    for r0 in range(0, roi_h, chunk):
        r1 = min(roi_h, r0 + chunk)
        m = mask[r0:r1][:, :, None]
        dst = canvas[dy0c + r0 : dy0c + r1, dx0c:dx1c]
        src = warped[r0:r1]
        prev_w = weight_hint[dy0c + r0 : dy0c + r1, dx0c:dx1c].astype(np.float32)[:, :, None] / 255.0
        total = prev_w + m
        safe = np.maximum(total, 1e-6)
        blended = (dst.astype(np.float32) * prev_w + src.astype(np.float32) * m) / safe
        out = np.where(total > 1e-6, blended, dst.astype(np.float32))
        canvas[dy0c + r0 : dy0c + r1, dx0c:dx1c] = np.clip(out, 0, 255).astype(np.uint8)
        weight_hint[dy0c + r0 : dy0c + r1, dx0c:dx1c] = np.clip(
            total[:, :, 0] * 255, 0, 255
        ).astype(np.uint8)


def new_canvas(width, height, paper_bgr):
    """uint8 canvas prefilled with edition paper tone (genuine gaps show as
    flat paper, disclosed — never generated content)."""
    canvas = np.empty((height, width, 3), np.uint8)
    canvas[:] = np.asarray(paper_bgr, np.uint8)[None, None, :]
    weight = np.zeros((height, width), np.uint8)
    return canvas, weight


def save_tiff(canvas, path):
    """cv2.imwrite, never PIL (PIL save of 484 MP OOM-kills at ~3 GB RAM)."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    ok = cv2.imwrite(path, canvas, [cv2.IMWRITE_TIFF_COMPRESSION, 5])  # LZW
    if not ok:
        raise IOError(f"imwrite failed: {path}")
    return path
