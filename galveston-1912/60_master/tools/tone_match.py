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
    pk = s.get("pink_wash_boost")
    out = {
        "gain": np.array(lv["gain"], np.float32),
        "offset": np.array(lv["offset"], np.float32),
        "knee": float(sh["knee"]),
        "chroma": float(ch["gain"]),
        "o_h0": float(oc["hue_deg"][0]), "o_h1": float(oc["hue_deg"][1]),
        "o_smin": float(oc["sat_min"]),
        "o_fh": float(oc["feather_hue_deg"]), "o_fs": float(oc["feather_sat"]),
        "pink": None,
    }
    if pk:
        out["pink"] = {
            "h0": float(pk["hue_deg"][0]), "h1": float(pk["hue_deg"][1]),
            "smin": float(pk["sat_min"]),
            "fh": float(pk["feather_hue_deg"]), "fs": float(pk["feather_sat"]),
            "y0": float(pk["value_ramp"][0]), "y1": float(pk["value_ramp"][1]),
            "g": float(pk["extra_chroma_gain"]),
        }
    return out


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


def _pink_weight(rgb_u8, pk):
    """1.0 inside the pink band (hue wraps through 0 deg), feathered to 0.0.

    Measured on the ORIGINAL pixels, like the orange carve-out, so band
    membership is stable under the transform (which preserves hue).
    """
    hsv = cv2.cvtColor(rgb_u8, cv2.COLOR_RGB2HSV).astype(np.float32)
    H = hsv[..., 0] * 2.0
    S = hsv[..., 1] / 255.0
    fh, fs = pk["fh"], pk["fs"]
    Hw = np.where(H >= 180.0, H - 360.0, H)      # wrap: band is h0-360..h1
    h0 = pk["h0"] - 360.0                        # e.g. -30
    h1 = pk["h1"]                                # e.g. +20
    wh = np.clip((Hw - (h0 - fh)) / fh, 0, 1) * \
        np.clip(((h1 + fh) - Hw) / fh, 0, 1)
    ws = np.clip((S - (pk["smin"] - fs)) / fs, 0, 1)
    return wh * ws


def apply(img, spec_path):
    """Return (treated uint8 copy, stats). `img` is RGB uint8, not modified."""
    p = _spec(spec_path)
    H, W = img.shape[:2]
    out = np.empty_like(img)
    K = p["knee"]
    R = 255.0 - K
    n_orange = 0
    n_pink = 0
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
        # D-021 pink-wash boost: the light pink building wash lands 5% under
        # the 1899's saturation while the mid and deep red tones already
        # match, so the extra gain is confined by a luma ramp to the wash and
        # gated off wherever the orange hold applies. Chroma-only about the
        # same luma axis: hue and luminance (hence legibility) are untouched.
        if p["pink"] is not None:
            pk = p["pink"]
            wp = _pink_weight(src, pk)[..., None] * (1.0 - w)
            # ramp on HSV V (max channel) of the POST-transform pixel -- the
            # statistic the wash/mid/deep subclasses were measured with. (Rec.
            # 601 luma of the wash is ~187 and would leave the ramp dark.)
            Vx = x.max(axis=-1, keepdims=True)
            wy = np.clip((Vx - pk["y0"]) / (pk["y1"] - pk["y0"]), 0, 1)
            wp = wp * wy
            G = G * (1.0 + (pk["g"] - 1.0) * wp)
            n_pink += int((wp > 0.5).sum())
        x = Y + (x - Y) * G
        out[y0:y1] = np.clip(x, 0, 255).astype(np.uint8)
        n_orange += int((w > 0.5).sum())
    return out, {
        "levels_gain": [round(float(v), 4) for v in p["gain"]],
        "levels_offset": [round(float(v), 3) for v in p["offset"]],
        "shoulder_knee": K,
        "chroma_gain": p["chroma"],
        "orange_carveout_px": n_orange,
        "pink_wash_boost_px": n_pink,
        "pink_wash_extra_chroma_gain": (p["pink"]["g"] if p["pink"] else None),
    }
