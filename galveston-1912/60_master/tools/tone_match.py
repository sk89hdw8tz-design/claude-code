"""Tone/colour match of the 1912 print to the 1899 companion sheet (D-016).

Pipeline (order matters, see make_print_pdf.py):
    tone_match.apply()  ->  water_treatment.apply()  ->  crop/downsample/encode

  1. per-channel affine levels  (ink -> ink, paper -> paper; print-to-print fit)
  2. soft highlight shoulder    (without it 15.3% of map content clips to 255)
  3. chroma gain about Rec.601 luma, with the orange band feather-excluded
     (the 1899 has no orange class to match; orange brightens via 1-2 only)

All constants live in 50_seams/tone_anchors.json with their measurement
provenance. Pure presentation stage: master_full.tif and the archival scans are
never written. Processes in horizontal strips to bound peak memory.
"""

import json

import cv2
import numpy as np

STRIP = 1024                     # rows per processing strip


def _spec(path):
    s = json.load(open(path))
    lv = s["levels"]
    sh = s["shoulder"]
    ch = s["chroma"]
    oc = s["orange_carveout"]
    return {
        "gain": np.array(lv["gain"], np.float32),
        "offset": np.array(lv["offset"], np.float32),
        "knee": float(sh["knee"]),
        "chroma": float(ch["gain"]),
        "o_h0": float(oc["hue_deg"][0]), "o_h1": float(oc["hue_deg"][1]),
        "o_smin": float(oc["sat_min"]),
        "o_fh": float(oc["feather_hue_deg"]), "o_fs": float(oc["feather_sat"]),
    }


def _orange_weight(rgb_u8, p):
    """1.0 inside the orange band, feathered to 0.0 outside.

    Measured on the ORIGINAL pixels, before any adjustment, so the carve-out is
    stable under the transform itself.
    """
    hsv = cv2.cvtColor(rgb_u8, cv2.COLOR_RGB2HSV).astype(np.float32)
    H = hsv[..., 0] * 2.0
    S = hsv[..., 1] / 255.0
    fh, fs = p["o_fh"], p["o_fs"]
    wh = np.clip((H - (p["o_h0"] - fh)) / fh, 0, 1) * \
        np.clip(((p["o_h1"] + fh) - H) / fh, 0, 1)
    ws = np.clip((S - (p["o_smin"] - fs)) / fs, 0, 1)
    return wh * ws


def apply(img, spec_path):
    """Return (treated uint8 copy, stats). `img` is RGB uint8, not modified."""
    p = _spec(spec_path)
    H, W = img.shape[:2]
    out = np.empty_like(img)
    K = p["knee"]
    R = 255.0 - K
    n_orange = 0
    for y0 in range(0, H, STRIP):
        y1 = min(y0 + STRIP, H)
        src = img[y0:y1]
        x = src.astype(np.float32) * p["gain"] + p["offset"]
        m = x > K                                  # soft shoulder
        x[m] = K + R * (1.0 - np.exp(-(x[m] - K) / R))
        Y = (0.299 * x[..., 0] + 0.587 * x[..., 1] + 0.114 * x[..., 2])[..., None]
        w = _orange_weight(src, p)[..., None]      # 1 = orange, hold saturation
        # Orange must HOLD its saturation, not merely skip the chroma boost:
        # the levels step itself saturates warm colours (red gain 1.327 vs blue
        # 1.244 widens R-B), measured +12% on the orange median with a plain
        # gain-1.0 carve-out. So inside the band the chroma factor is computed
        # per pixel to keep chroma proportional to luminance (S ~ c/Y constant):
        # c_desired = c_src * (Y_now / Y_src), factor = c_desired / c_now.
        f = src.astype(np.float32)
        Ys = (0.299 * f[..., 0] + 0.587 * f[..., 1] + 0.114 * f[..., 2])[..., None]
        c_src = np.linalg.norm(f - Ys, axis=-1, keepdims=True)
        c_now = np.linalg.norm(x - Y, axis=-1, keepdims=True)
        hold = (c_src * np.maximum(Y, 1.0) / np.maximum(Ys, 1.0)) / np.maximum(c_now, 1e-3)
        G = p["chroma"] + (hold - p["chroma"]) * w
        x = Y + (x - Y) * G
        out[y0:y1] = np.clip(x, 0, 255).astype(np.uint8)
        n_orange += int((w > 0.5).sum())
    return out, {
        "levels_gain": [round(float(v), 4) for v in p["gain"]],
        "levels_offset": [round(float(v), 3) for v in p["offset"]],
        "shoulder_knee": K,
        "chroma_gain": p["chroma"],
        "orange_carveout_px": n_orange,
    }
