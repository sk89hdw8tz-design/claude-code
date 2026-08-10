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
    region[3760:, 450:] = 0            # bottom sheet-margin strip is not water
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
    region = cv2.morphologyEx(region, cv2.MORPH_OPEN, k)
    k2 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (31, 31))
    region = cv2.morphologyEx(region, cv2.MORPH_CLOSE, k2)
    inv = (region == 0).astype(np.uint8)
    n, lab = cv2.connectedComponents(inv)
    border = set(np.unique(np.concatenate(
        [lab[0], lab[-1], lab[:, 0], lab[:, -1]])))
    region[np.isin(lab, list(set(range(1, n)) - border))] = 1
    rf = cv2.resize(region, (img.shape[1], img.shape[0]),
                    interpolation=cv2.INTER_NEAREST).astype(bool)
    factor = (WASH / CREAM).astype(np.float32)
    img[rf] = np.clip(img[rf].astype(np.float32) * factor, 0, 255).astype(np.uint8)
    cv2.imwrite(png_path, img)
    return float(rf.mean())

if __name__ == "__main__":
    import sys
    frac = tint(sys.argv[1])
    print(f"bay tinted: {frac:.1%} of image")
