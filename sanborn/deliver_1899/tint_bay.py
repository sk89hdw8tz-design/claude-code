"""Stylized water fill for Galveston Bay (user-directed).

The atlas prints open water as uncolored paper, tinting only shoreline
edging strips. At the user's direction the open bay + slips are filled
with the SAME printed wash tone, applied multiplicatively so paper
texture and overprinted ink (bay lettering, compasses, scale bars)
survive. Region: flood fill from open-bay seeds across cream/canvas
pixels; ink lines and existing washes (the shoreline edging) are the
barriers; small strips opened away, lettering fringes closed over,
enclosed islands filled; explicit clamp kills the bottom-margin strip
leak. Disclosed in PRODUCTION_REPORT.md — this is the one deliberate
departure from as-printed colour.
"""
import cv2
import numpy as np

WASH = np.array([210.8, 221.6, 217.3])    # sampled printed water wash (BGR)
CREAM = np.array([203.6, 228.6, 238.9])   # edition paper target

def tint(png_path):
    img = cv2.imread(png_path)
    s = img[::2, ::2].astype(np.int16)
    b, g, r = s[:, :, 0], s[:, :, 1], s[:, :, 2]
    mn = s.min(axis=2)
    tintable = ((mn > 175) & ((r - b) > 15) & ((r - b) < 55)
                & ((r - g) < 25) & ((g - b) < 45)).astype(np.uint8)
    mask = np.zeros((tintable.shape[0] + 2, tintable.shape[1] + 2), np.uint8)
    ff = tintable.copy()
    for y in range(200, tintable.shape[0] - 100, 150):
        if ff[y, 80]:
            cv2.floodFill(ff, mask, (80, y), 2)
    region = (ff == 2).astype(np.uint8)
    # The flood leaks through linework gaps into vacant yard blocks
    # (742/744), the West Platform yards, the Fire Limits corridor and
    # the bottom sheet margin. Crude x-clamps left rectangular untinted
    # steps in the open water at the bottom-left; instead the flood's own
    # shoreline is kept and only the measured leak zones are excluded.
    for ya, yb, xmax in ((0, 3550, 2100), (3550, 6550, 2450)):
        region[ya // 2:min(yb // 2, region.shape[0]), xmax // 2:] = 0
    for x0, y0, x1, y1 in ((2100, 6550, 3400, 7560),   # 744/platform/Fire Limits
                           (1500, 7530, 10 ** 9, 10 ** 9)):  # bottom margin strip
        region[y0 // 2:min(y1 // 2, region.shape[0]),
               x0 // 2:min(x1 // 2, region.shape[1])] = 0
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
    region = cv2.morphologyEx(region, cv2.MORPH_OPEN, k)
    k2 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (31, 31))
    region = cv2.morphologyEx(region, cv2.MORPH_CLOSE, k2)
    inv = (region == 0).astype(np.uint8)
    n, lab = cv2.connectedComponents(inv)
    border = set(np.unique(np.concatenate(
        [lab[0], lab[-1], lab[:, 0], lab[:, -1]])))
    region[np.isin(lab, list(set(range(1, n)) - border))] = 1
    # keep only water connected to the open bay (west edge)
    n2, lab2, stats2, _ = cv2.connectedComponentsWithStats(region)
    keep = [i for i in range(1, n2) if stats2[i][0] < 60]
    region = np.isin(lab2, keep).astype(np.uint8)
    rf = cv2.resize(region, (img.shape[1], img.shape[0]),
                    interpolation=cv2.INTER_NEAREST).astype(bool)
    # Region-scoped paper flattening before the wash: a plain multiply
    # reproduces every residual paper gradient IN the blue (sheet seam
    # lines banded the bay). Estimate the bright-paper field inside the
    # water only, divide it out fully, multiply by the wash; ink stays
    # dark, fine grain survives, bands vanish.
    s = img[::4, ::4].astype(np.float32)
    r4 = rf[::4, ::4]
    mx = s.max(axis=2)
    mn = s.min(axis=2)
    paper = (r4 & (mx > 185) & ((mx - mn) < 45)).astype(np.float32)
    field = s * paper[..., None]
    den = paper.copy()
    for _ in range(5):
        field = cv2.blur(field, (41, 41))
        den = cv2.blur(den, (41, 41))
    med = np.median(s.reshape(-1, 3)[paper.reshape(-1) > 0], axis=0)
    gain4 = np.empty_like(field)
    for c in range(3):
        f = np.where(den > 1e-3, field[..., c] / np.maximum(den, 1e-3), med[c])
        f = cv2.GaussianBlur(f, (0, 0), 4)
        gain4[..., c] = WASH[c] / np.maximum(f, 1.0)
    gain4 = np.clip(gain4, 0.6, 1.6)
    gain = cv2.resize(gain4, (img.shape[1], img.shape[0]),
                      interpolation=cv2.INTER_LINEAR)
    img[rf] = np.clip(img[rf].astype(np.float32) * gain[rf], 0, 255).astype(np.uint8)
    cv2.imwrite(png_path, img)
    return float(rf.mean())

if __name__ == "__main__":
    import sys
    frac = tint(sys.argv[1])
    print(f"bay tinted: {frac:.1%} of image")
