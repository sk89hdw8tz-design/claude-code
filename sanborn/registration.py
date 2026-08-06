"""Phase B — grid detection and per-sheet affine registration.

Verified algorithm (do NOT switch to feature matching — Sanborn sheets abut
along street centerlines with zero image overlap, so SIFT/ORB fails here):

1. whiteness() isolates unprinted street paper from colored buildings.
2. Project whiteness to row/column signals over the map interior only
   (inset ~7.5% — bright outer margins otherwise bias the fit).
3. Fix the comb period to the edition pitch and grid-search only the phase.
4. Extend the comb ±3 periods past the fitted range, keep lines inside image.
5. Refine each line by local center-of-mass in a ±80 px window.
6. Fit an axis-aligned affine (x/y scale + translation, no rotation) from
   line identities to the global grid; gate every scale at ±1% (fail at ±2%).

Detection runs at DETECT_WIDTH (3400 px); coordinates scale back to native.
"""

import json
import os

import numpy as np
import cv2

import config


def whiteness(a):
    """a = float RGB/BGR in [0,1]. Streets are bright + unsaturated."""
    mx = a.max(axis=2)
    mn = a.min(axis=2)
    return np.clip(a.mean(axis=2) - 2.2 * (mx - mn), 0, 1)


def load_detect_scale(path):
    """Load a sheet downsampled to DETECT_WIDTH. Returns (img_float01, scale)
    where native_coord = detect_coord * scale."""
    img = cv2.imread(path, cv2.IMREAD_COLOR)
    if img is None:
        raise IOError(f"cannot decode {path}")
    h, w = img.shape[:2]
    scale = w / config.DETECT_WIDTH
    if scale > 1.01:
        img = cv2.resize(
            img, (config.DETECT_WIDTH, round(h / scale)), interpolation=cv2.INTER_AREA
        )
    else:
        scale = 1.0
    return img.astype(np.float32) / 255.0, scale


def profile_signals(img01, inset_frac=0.075):
    """Row/column whiteness profiles over the map interior."""
    wmap = whiteness(img01)
    h, w = wmap.shape
    iy, ix = round(h * inset_frac), round(w * inset_frac)
    interior = wmap[iy : h - iy, ix : w - ix]
    col_sig = interior.mean(axis=0)  # peaks at vertical street lines
    row_sig = interior.mean(axis=1)  # peaks at horizontal street lines
    return row_sig, col_sig, iy, ix


def comb_phase_fit(signal, period, offset):
    """Fixed-period comb: grid-search phase only. Returns line positions in
    full-image coordinates (signal starts at `offset`).

    Fitting period and phase together is unstable (bright margins produce
    nonsense pitches like 1056 vs 920 across sheets) — never do it.
    """
    n = len(signal)
    best_phase, best_score = 0.0, -np.inf
    for phase in np.arange(0, period, period / 400):
        centers = np.arange(phase, n, period)
        idx = centers.round().astype(int)
        idx = idx[(idx >= 0) & (idx < n)]
        if len(idx) < 2:
            continue
        score = signal[idx].sum() / len(idx)
        if score > best_score:
            best_score, best_phase = score, phase
    # Extend ±3 periods so edge lines aren't clipped, keep those inside image.
    k0 = -3
    k1 = int((n - best_phase) / period) + 3
    lines = [best_phase + k * period + offset for k in range(k0, k1 + 1)]
    return [x for x in lines if 0 <= x < n + 2 * offset], best_score


def refine_com(signal, pos, offset, window=None):
    """Center-of-mass refinement in a ±window px window around pos.
    Real block spacing is not perfectly uniform (measured 1101/1170/1133);
    the comb gets close, this lands it."""
    window = window or config.COM_REFINE_WINDOW
    p = pos - offset
    lo, hi = int(max(0, p - window)), int(min(len(signal), p + window + 1))
    if hi - lo < 8:
        return pos
    seg = signal[lo:hi].astype(np.float64)
    seg = seg - seg.min()
    if seg.sum() <= 0:
        return pos
    com = (seg * np.arange(lo, hi)).sum() / seg.sum()
    return com + offset


def measure_free_pitch(signal, expected_period):
    """Free-period comb fit used ONLY as the off-scale panel detector (§3.5):
    if measured pitch deviates >5% from the edition pitch the panel is
    off-scale — exclude and disclose, do not warp it into place."""
    best = (expected_period, -np.inf)
    for period in np.arange(expected_period * 0.5, expected_period * 1.5, expected_period / 200):
        _, score = comb_phase_fit(signal, period, 0)
        if score > best[1]:
            best = (period, score)
    return best[0]


def detect_sheet_grid(path, region=None):
    """Detect street-grid lines on one sheet (optionally within a panel
    region=(x0,y0,x1,y1) in native coords). Returns dict with native-scale
    line positions and the measured free pitch for the off-scale gate."""
    img01, scale = load_detect_scale(path)
    if region:
        x0, y0, x1, y1 = [round(v / scale) for v in region]
        img01 = img01[y0:y1, x0:x1]
        base = (x0, y0)
    else:
        base = (0, 0)

    row_sig, col_sig, iy, ix = profile_signals(img01)

    # Orientation follows the global grid model (X = avenues, Y = streets).
    # [VERIFY] against the first real sheet — if a sheet is scanned rotated,
    # swap the pitches here per coverage.json before fitting.
    v_lines, _ = comb_phase_fit(col_sig, config.PITCH_AV_DETECT, ix)
    h_lines, _ = comb_phase_fit(row_sig, config.PITCH_ST_DETECT, iy)
    v_lines = [refine_com(col_sig, x, ix) for x in v_lines]
    h_lines = [refine_com(row_sig, y, iy) for y in h_lines]

    free_v = measure_free_pitch(col_sig, config.PITCH_AV_DETECT)
    free_h = measure_free_pitch(row_sig, config.PITCH_ST_DETECT)

    return {
        "path": path,
        "scale": scale,
        "v_lines_native": [(x + base[0]) * scale for x in v_lines],
        "h_lines_native": [(y + base[1]) * scale for y in h_lines],
        "free_pitch_av": free_v * scale,
        "free_pitch_st": free_h * scale,
    }


def off_scale(detected, edition):
    ed = config.EDITIONS[edition]
    dev_st = abs(detected["free_pitch_st"] / ed["pitch_st"] - 1)
    dev_av = abs(detected["free_pitch_av"] / ed["pitch_av"] - 1)
    return max(dev_st, dev_av) > config.PANEL_PITCH_TOLERANCE, (dev_av, dev_st)


def fit_affine(controls, edition):
    """Axis-aligned affine per sheet from control points.

    controls: list of dicts {"axis": "x"|"y", "native": px, "identity": n}
      identity for x = avenue index (A=0..J=9); for y = street number.
    Global grid: X = av_idx * P_AV, Y = (street - 16) * P_ST.

    Returns dict with sx, tx, sy, ty mapping native -> global px, plus the
    validation verdict. Scale outside ±2% of 1.0 means a misidentified grid
    line: stop and re-derive, don't proceed.
    """
    ed = config.EDITIONS[edition]
    out = {}
    for axis, pitch, origin in (("x", ed["pitch_av"], 0), ("y", ed["pitch_st"], config.STREET_ORIGIN)):
        pts = [c for c in controls if c["axis"] == axis]
        if len(pts) < 2:
            raise ValueError(f"axis {axis}: need >=2 control points, got {len(pts)}")
        src = np.array([c["native"] for c in pts])
        dst = np.array([(c["identity"] - origin) * pitch for c in pts])
        A = np.vstack([src, np.ones_like(src)]).T
        (s, t), *_ = np.linalg.lstsq(A, dst, rcond=None)
        out[f"s{axis}"] = float(s)
        out[f"t{axis}"] = float(t)
        out[f"n_{axis}"] = len(pts)
    for axis in "xy":
        dev = abs(out[f"s{axis}"] - 1.0)
        out[f"flag_{axis}"] = (
            "FAIL" if dev > config.SCALE_FAIL else "WARN" if dev > config.SCALE_WARN else "OK"
        )
        if out[f"n_{axis}"] < 3:
            out[f"flag_{axis}"] += "+FEW_POINTS"
    return out


def save_json(obj, name):
    os.makedirs(config.BUILD_DIR, exist_ok=True)
    p = os.path.join(config.BUILD_DIR, name)
    with open(p, "w") as f:
        json.dump(obj, f, indent=1)
    return p
