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


def frame_bounds(img01, grid_v, grid_h, search_margin=0.12, region=None):
    """Find the printed black map frame, searching ONLY outside the outermost
    grid lines. Returns (x0, y0, x1, y1) clip rectangle in this image's
    coordinates. grid_v/grid_h are line positions at this image's scale.
    `region` (x0,y0,x1,y1) bounds the search for multi-panel sheets so the
    frame is the panel divider, not the neighboring panel's frame."""
    gray = img01.mean(axis=2)
    dark = (gray < 0.45).astype(np.float32)
    h, w = gray.shape
    if region:
        rx0, ry0, rx1, ry1 = region
    else:
        rx0, ry0, rx1, ry1 = 0, 0, w, h
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
    x0 = edge(col_dark, lo_v, max(rx0, lo_v - search_margin * w), -1)
    x1 = edge(col_dark, hi_v, min(rx1, hi_v + search_margin * w), +1)
    y0 = edge(row_dark, lo_h, max(ry0, lo_h - search_margin * h), -1)
    y1 = edge(row_dark, hi_h, min(ry1, hi_h + search_margin * h), +1)
    return x0, y0, x1, y1


def paper_bounds(img, min_frac=0.35, max_gap=60):
    """Bounding box of the sheet's CREAM PAPER inside the scan.

    A UT scan is the sheet on a white scanner ground, with a black-on-white
    credit caption below it. Both read as background: paper is cream
    (R noticeably above B) and never blows out to white. Needed for two
    jobs the frame detector cannot do:
      - wharf sheets carry a single grid line, so frame_bounds — which only
        searches 0.12*width outside the outermost line — puts the frame a
        few hundred px away instead of at the sheet edge, clipping ~3000 px
        of piers and bay;
      - the retained exterior margin otherwise runs past the paper into the
        caption, compositing "Original located at the Dolph Briscoe
        Center..." into the map.
    """
    r = img[:, :, 2].astype(np.int16)
    b = img[:, :, 0].astype(np.int16)
    cream = (r > 140) & (img.max(axis=2) < 252) & ((r - b) > 6)

    def run(sig):
        on = sig > min_frac
        # Bridge narrow gaps first. A heavily ruled line — Avenue A's frontage
        # rules on sheet 07 at columns 3118 and 3131 — drops the cream
        # fraction below threshold for a few px and splits the sheet in two;
        # taking the longest run then truncated that sheet's paper 240 px
        # early, which made its printed frame appear not to overlap its
        # neighbour's and collapsed the seam cut to a midpoint fallback.
        i = 0
        while i < len(on):
            if not on[i]:
                j = i
                while j < len(on) and not on[j]:
                    j += 1
                if 0 < i and j < len(on) and (j - i) <= max_gap:
                    on[i:j] = True
                i = j
            else:
                i += 1
        best, i = (0, 0, len(on) - 1), 0
        while i < len(on):
            if on[i]:
                j = i
                while j + 1 < len(on) and on[j + 1]:
                    j += 1
                if j - i > best[0]:
                    best = (j - i, i, j)
                i = j + 1
            else:
                i += 1
        return best[1], best[2] + 1

    y0, y1 = run(cream.mean(axis=1))
    x0, x1 = run(cream.mean(axis=0))
    return x0, y0, x1, y1


def paper_tone(img, frac=0.56, bright=170, sat_max=40):
    """Median BGR of bright, low-saturation, CREAM pixels on the central
    `frac` of the map interior ONLY. Including scanner margin skews tone
    wildly. The cream test (G-B > 0.55*(R-B)) rejects pale brick-wash
    pixels, which pass the brightness/saturation gates but sit ~12 levels
    low in green — on wash-dominated sheets (sheet 9, the Strand
    warehouses) they dragged the tone median and the resulting gain
    over-boosted green, painting a cyan cast onto genuinely warm paper."""
    h, w = img.shape[:2]
    cy, cx = round(h * (1 - frac) / 2), round(w * (1 - frac) / 2)
    c = img[cy : h - cy, cx : w - cx]
    c = c[::8, ::8].reshape(-1, 3).astype(np.int16)
    mx = c.max(axis=1)
    mn = c.min(axis=1)
    base = (mx > bright) & ((mx - mn) < sat_max)
    cream = (c[:, 1] - c[:, 0]) > 0.55 * (c[:, 2] - c[:, 0])
    for mask in (base & cream, base, mx > bright):
        if mask.sum() >= 100:
            return np.median(c[mask], axis=0)
    return np.median(c, axis=0)


def flatten_illumination(img, target_tone, clip_lo=0.70, clip_hi=1.40):
    """Flatten one scan's illumination field to the edition paper tone.

    Estimate the smooth per-channel paper field from bright low-saturation
    (paper) pixels at 1/8 scale, fill wash/ink holes by iterative masked
    blurring, low-pass hard (~200 px native), and multiply the sheet by
    target/field, clipped so a bad field estimate cannot swing any pixel
    by more than ~±30%. Ink and washes ride along with their local paper,
    so printed colour ratios are preserved; only the lighting is removed."""
    small = img[::8, ::8].astype(np.float32)
    mx = small.max(axis=2)
    mn = small.min(axis=2)
    # paper: bright, low-saturation, but NOT scanner backing — backing is
    # near-neutral white (min channel > ~225) while aged cream keeps its
    # blue channel around 195-210; letting backing into the field pulls
    # the last ~200 px of real paper toward white and INVERTS the
    # correction at the very edges the flattening exists to fix.
    mask = ((mx > 170) & ((mx - mn) < 40) & (mn < 225)).astype(np.float32)
    field = small * mask[..., None]
    den = mask.copy()
    for _ in range(6):        # masked diffusion fills wash blocks and bay
        field = cv2.blur(field, (61, 61))
        den = cv2.blur(den, (61, 61))
    med = np.median(small.reshape(-1, 3)[mask.reshape(-1) > 0], axis=0) \
        if mask.sum() > 100 else np.median(small.reshape(-1, 3), axis=0)
    out = np.empty_like(field)
    for c in range(3):
        f = np.where(den > 1e-3, field[..., c] / np.maximum(den, 1e-3), med[c])
        out[..., c] = cv2.GaussianBlur(f, (0, 0), 10)
    gain = np.asarray(target_tone, np.float32) / np.maximum(out, 1.0)
    gain = np.clip(gain, clip_lo, clip_hi)
    # 1-D residual pass: steep edge vignettes in the last ~150 px defeat
    # the 2-D field (border reflection biases it toward the brighter
    # interior; the wharf sheets' bottom bands survived at 15-21 levels).
    # Row/column masked paper medians of the CORRECTED result catch them
    # at full cross-axis fidelity; rows with thin paper support keep
    # gain 1 so wash-dominated bands are never stretched.
    tgt = np.asarray(target_tone, np.float32)
    corr = small * gain
    for axis in (0, 1):            # 0: per-row gains, 1: per-column gains
        n = corr.shape[axis]
        sup = mask.sum(axis=1 - axis)
        med = np.tile(tgt, (n, 1)).astype(np.float32)
        for i in range(n):
            if sup[i] < 12:
                continue
            line = corr[i] if axis == 0 else corr[:, i]
            lm = (mask[i] if axis == 0 else mask[:, i]) > 0
            med[i] = np.median(line[lm], axis=0)
        g1 = np.clip(tgt / np.maximum(med, 1.0), 0.85, 1.2)
        g1[sup < 12] = 1.0
        g1 = cv2.GaussianBlur(g1.reshape(-1, 1, 3), (1, 9), 0).reshape(-1, 3)
        gain = gain * (g1[:, None, :] if axis == 0 else g1[None, :, :])
        corr = small * gain
    gain = np.clip(gain, clip_lo * 0.9, clip_hi * 1.15)
    gain_full = cv2.resize(gain, (img.shape[1], img.shape[0]),
                           interpolation=cv2.INTER_LINEAR)
    return np.clip(img.astype(np.float32) * gain_full, 0, 255).astype(np.uint8)


def channel_gains(sheet_tone, target_tone):
    """Full chromatic white-balance to the edition paper tone. The old
    per-channel clamp left a residual cast whenever one channel hit the
    limit (sheet 9's cyan patch survived it); equalizing the channel
    RATIOS exactly removes the cast, while GAIN_CLAMP now bounds only the
    MEAN gain so overall lightness stays subtle. 0.85-1.18 per channel is
    a hard safety range against a corrupt tone estimate."""
    if getattr(config, "PRESERVE_COLORS", False):
        # Original-colour mode: the printed washes are the artefact, so no
        # chromatic correction is applied at all. Sheets keep the exact hue
        # and lightness of their scans; any scan-to-scan tone difference
        # stays visible at the joins rather than being averaged away.
        return np.ones(3, np.float64)
    g = np.asarray(target_tone, np.float64) / np.maximum(np.asarray(sheet_tone, np.float64), 1)
    m = float(g.mean())
    g *= np.clip(m, *config.GAIN_CLAMP) / max(m, 1e-9)
    return np.clip(g, 0.85, 1.18)


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


def _extend_knots(native, glob, span=30000.0):
    """Extend a monotone knot list linearly beyond both ends using the end
    segments' slopes, so np.interp extrapolates instead of clamping."""
    n = list(map(float, native))
    g = list(map(float, glob))
    s0 = (g[1] - g[0]) / (n[1] - n[0])
    s1 = (g[-1] - g[-2]) / (n[-1] - n[-2])
    n = [n[0] - span] + n + [n[-1] + span]
    g = [g[0] - span * s0] + g + [g[-1] + span * s1]
    return np.array(n), np.array(g)


def pw_fwd(v, native, glob):
    """native -> global, piecewise-linear with linear extrapolation."""
    n, g = _extend_knots(native, glob)
    return np.interp(v, n, g)


def pw_inv(v, native, glob):
    """global -> native."""
    n, g = _extend_knots(native, glob)
    return np.interp(v, g, n)


def warp_sheet_piecewise(canvas, weight_hint, img, xkn, xkg, ykn, ykg,
                         clip, gains, feather, shear=(0.0, 0.0),
                         shear_pivot=None, border_bgr=None):
    """Warp one sheet with a separable monotone piecewise-linear mapping that
    places every detected grid line exactly at its consensus global position
    (linear between lines, linear extrapolation beyond). Single resampling
    pass via cv2.remap; blending in row chunks on the uint8 canvas.

    xkn/xkg: native/global knot arrays for x (avenues); ykn/ykg for y.
    clip: native-space rectangle to contribute."""
    x0, y0, x1, y1 = [float(v) for v in clip]
    gx0, gx1 = pw_fwd([x0, x1], xkn, xkg)
    gy0, gy1 = pw_fwd([y0, y1], ykn, ykg)
    dx0c, dy0c = max(0, int(np.floor(gx0))), max(0, int(np.floor(gy0)))
    dx1c = min(canvas.shape[1], int(np.ceil(gx1)))
    dy1c = min(canvas.shape[0], int(np.ceil(gy1)))
    if dx1c <= dx0c or dy1c <= dy0c:
        return
    roi_w, roi_h = dx1c - dx0c, dy1c - dy0c

    mapx1 = pw_inv(np.arange(dx0c, dx1c, dtype=np.float64) + 0.5, xkn, xkg).astype(np.float32)
    mapy1 = pw_inv(np.arange(dy0c, dy1c, dtype=np.float64) + 0.5, ykn, ykg).astype(np.float32)
    kx, ky = shear
    if abs(kx) > 1e-6 or abs(ky) > 1e-6:
        # panel skew: sample the source along its tilted lines so avenues/
        # streets render straight. Pivot must be clip-INDEPENDENT (callers
        # pass the knot centroid): pivoting on the clip center made the
        # whole unit translate by shear x center-shift whenever the clip
        # changed (QC v3-3 measured 1-5 px rigid drifts from the v3 margin
        # extension alone).
        if shear_pivot is not None:
            xc, yc = float(shear_pivot[0]), float(shear_pivot[1])
        else:
            yc = float(np.mean(mapy1))
            xc = float(np.mean(mapx1))
        mapx = mapx1[None, :] + (kx * (mapy1[:, None] - yc)).astype(np.float32)
        mapy = mapy1[:, None] + (ky * (mapx1[None, :] - xc)).astype(np.float32)
        mapx = np.ascontiguousarray(np.broadcast_to(mapx, (roi_h, roi_w)).astype(np.float32))
        mapy = np.ascontiguousarray(np.broadcast_to(mapy, (roi_h, roi_w)).astype(np.float32))
    else:
        mapx = np.ascontiguousarray(np.broadcast_to(mapx1[None, :], (roi_h, roi_w)))
        mapy = np.ascontiguousarray(np.broadcast_to(mapy1[:, None], (roi_h, roi_w)))

    # border = paper tone, NOT black: shear displaces edge samples past the
    # sheet boundary (sheet 14's ky=-0.049 shifts corners ~150px), and a
    # black border FABRICATED 83,809 pure-black px on v4's margins plus a
    # Lanczos overshoot ring of channel-255 px around them (QC v4-B). The
    # border is pre-divided by the gains so it lands exactly on the fill.
    if border_bgr is None:
        bv = 0.0, 0.0, 0.0
    else:
        bv = tuple(float(b) / max(float(g), 1e-6)
                   for b, g in zip(border_bgr, gains))
    warped = cv2.remap(img, mapx, mapy, interpolation=cv2.INTER_LANCZOS4,
                       borderMode=cv2.BORDER_CONSTANT, borderValue=bv)
    del mapx, mapy
    warped = np.clip(warped.astype(np.float32) * gains[None, None, :], 0, 255).astype(np.uint8)

    mask = cv2.resize(feather_mask(roi_w, roi_h, feather), (roi_w, roi_h),
                      interpolation=cv2.INTER_LINEAR)

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
