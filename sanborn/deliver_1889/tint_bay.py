"""Flat water fill for the 1889 composite (user-directed stylization).

Same algorithm as the 1899 deliverable's tint_bay.py: flood the open water
from west-edge seeds across paper-like pixels with ink and existing washes
as barriers, level the result to the sheet's own printed waterline colour,
and blend ink back through a smoothstep so lettering keeps clean edges.

Two 1889-specific rules:

* The fill is masked to pixels the SOURCES actually cover. Sheet 2
  (19th-22nd) draws far more of Galveston Bay than sheet 1 (22nd-25th),
  so the south-west bay is not mapped at this frame width. Tinting that
  canvas would present unmapped ground as surveyed water; it stays flat
  paper and is disclosed instead.
* The region is verified by contour overlay before use — the flood leaks
  through gaps in linework, which on 1899 put railroad yards under blue.
"""
import cv2
import numpy as np

WASH = np.array([188.0, 202.0, 198.0])   # median of the printed edging strips
CREAM = np.array([181.0, 214.0, 236.0])  # composite paper median


def water_region(img, cover):
    s = img[::2, ::2].astype(np.int16)
    c2 = cover[::2, ::2] > 0
    b, g, r = s[:, :, 0], s[:, :, 1], s[:, :, 2]
    mn = s.min(axis=2)
    paperish = ((mn > 150) & ((r - b) > 8) & ((r - b) < 70)
                & ((r - g) < 40) & (g - b < 60) & c2).astype(np.uint8)
    ff = paperish.copy()
    mask = np.zeros((ff.shape[0] + 2, ff.shape[1] + 2), np.uint8)
    seeded = False
    for y in range(40, ff.shape[0] - 40, 60):
        for x in (12, 40, 80):
            if ff[y, x] == 1:
                cv2.floodFill(ff, mask, (x, y), 2)
                seeded = True
    if not seeded:
        return np.zeros_like(paperish)
    region = (ff == 2).astype(np.uint8)
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    region = cv2.morphologyEx(region, cv2.MORPH_OPEN, k)
    k2 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (25, 25))
    region = cv2.morphologyEx(region, cv2.MORPH_CLOSE, k2)
    inv = (region == 0).astype(np.uint8)
    n, lab = cv2.connectedComponents(inv)
    border = set(np.unique(np.concatenate(
        [lab[0], lab[-1], lab[:, 0], lab[:, -1]])))
    region[np.isin(lab, list(set(range(1, n)) - border))] = 1
    n2, lab2, stats2, _ = cv2.connectedComponentsWithStats(region)
    keep = [i for i in range(1, n2) if stats2[i][0] < 40]   # touching far west
    return np.isin(lab2, keep).astype(np.uint8)


def tint(png_path, mask_path, crop):
    img = cv2.imread(png_path)
    cov = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)
    x0, y0, x1, y1 = crop
    cov = cov[y0:y1, x0:x1]
    region = water_region(img, cov)
    rf = cv2.resize(region, (img.shape[1], img.shape[0]),
                    interpolation=cv2.INTER_NEAREST).astype(bool)
    if rf.sum() == 0:
        print("no water region found")
        return 0.0, region
    # flatten the paper field inside the water only, then level to WASH
    s = img[::4, ::4].astype(np.float32)
    r4 = rf[::4, ::4]
    mx, mn = s.max(axis=2), s.min(axis=2)
    paper = (r4 & (mx > 165) & ((mx - mn) < 55)).astype(np.float32)
    field, den = s * paper[..., None], paper.copy()
    for _ in range(5):
        field = cv2.blur(field, (41, 41))
        den = cv2.blur(den, (41, 41))
    med = (np.median(s.reshape(-1, 3)[paper.reshape(-1) > 0], axis=0)
           if paper.sum() > 100 else np.median(s.reshape(-1, 3), axis=0))
    fld4 = np.empty_like(field)
    for c in range(3):
        f = np.where(den > 1e-3, field[..., c] / np.maximum(den, 1e-3), med[c])
        fld4[..., c] = cv2.GaussianBlur(f, (0, 0), 4)
    fld = cv2.resize(fld4, (img.shape[1], img.shape[0]),
                     interpolation=cv2.INTER_LINEAR)
    px = img[rf].astype(np.float32)
    f = fld[rf]
    ratio = np.clip(px / np.maximum(f, 1.0), 0, 1.4).min(axis=1)
    a = np.clip((ratio - 0.72) / (0.90 - 0.72), 0, 1)
    a = (a * a * (3 - 2 * a))[:, None]
    inked = np.clip(px * (WASH / np.maximum(f, 1.0)), 0, 255)
    img[rf] = np.clip(a * WASH + (1 - a) * inked, 0, 255).astype(np.uint8)
    cv2.imwrite(png_path, img)
    return float(rf.mean()), region


if __name__ == "__main__":
    import json, sys
    SP = "/tmp/claude-0/-home-user-claude-code/2bd63ebc-a879-5d86-b98a-dc1ab929f20f/scratchpad/sanborn"
    m = json.load(open(f"{SP}/deliver/1889/downtown_wharf_meta.json"))
    frac, region = tint(f"{SP}/deliver/1889/galveston_1889_downtown_wharf.png",
                        f"{SP}/build/1889/coverage_mask.png", m["crop"])
    print(f"water tinted: {frac:.1%} of the image")
    img = cv2.imread(f"{SP}/deliver/1889/galveston_1889_downtown_wharf.png")
    rf = cv2.resize(region, (img.shape[1], img.shape[0]),
                    interpolation=cv2.INTER_NEAREST)
    vis = img.copy()
    cnts, _ = cv2.findContours(rf, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cv2.drawContours(vis, cnts, -1, (0, 0, 255), 6)
    sc = 1400.0 / vis.shape[1]
    cv2.imwrite(f"{SP}/qc/water_contour_1889.jpg",
                cv2.resize(vis, None, fx=sc, fy=sc, interpolation=cv2.INTER_AREA),
                [cv2.IMWRITE_JPEG_QUALITY, 88])
