"""Verification for the D-016 tone match. Every check is an assertion.

Run from 60_master/tools. Exits non-zero on any failure.
"""

import json
import os
import subprocess
import sys

import cv2
import numpy as np
import pymupdf
import tifffile
from PIL import Image

Image.MAX_IMAGE_PIXELS = None
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tone_match  # noqa: E402

ROOT = "/home/user/claude-code/galveston-1912"
SPEC = f"{ROOT}/50_seams/tone_anchors.json"
PDF = f"{ROOT}/deliverables/Galveston_1912_Wharf_Downtown_print.pdf"
U = "/root/.claude/uploads/3107d3d8-6779-530e-9ae5-ba7b48239c4e"
REF99 = f"{U}/e3e4a0e2-Galveston_1899_Wharf_Downtown_print_8102026___27x40.pdf"
OUT = "/home/user/g1912/work/tone"
os.makedirs(OUT, exist_ok=True)
fails = []


def check(name, ok, detail=""):
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}{('  ' + detail) if detail else ''}")
    if not ok:
        fails.append(name)


lum = lambda x: 0.299 * x[..., 0] + 0.587 * x[..., 1] + 0.114 * x[..., 2]

print("rendering finished PDF at 150 dpi ...")
doc = pymupdf.open(PDF)
page = doc[0]
pix = page.get_pixmap(dpi=150)
a = np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.width, pix.n)[:, :, :3].copy()
h, w = a.shape[:2]
content = a[int(0.015 * h):int(0.925 * h), int(0.012 * w):int(0.985 * w)]
land = content.reshape(-1, 3)
land = land[~(((land[:, 0] == 199) & (land[:, 1] == 214) & (land[:, 2] == 209))
              | (land.min(axis=1) >= 250))]

d99 = pymupdf.open(REF99)
pix99 = d99[0].get_pixmap(dpi=150)
a99 = np.frombuffer(pix99.samples, np.uint8).reshape(pix99.height, pix99.width, pix99.n)[:, :, :3].copy()
h9, w9 = a99.shape[:2]
land99 = a99[int(0.015 * h9):int(0.925 * h9), int(0.012 * w9):int(0.985 * w9)].reshape(-1, 3)
land99 = land99[~(((land99[:, 0] == 199) & (land99[:, 1] == 214) & (land99[:, 2] == 209))
                  | (land99.min(axis=1) >= 250))]
d99.close()

# previous (pre-D-016) print for the legibility comparison
PREV = f"{U}/1e54644f-Galveston_1912_Wharf_Downtown_print_2.pdf"
dp = pymupdf.open(PREV)
pixp = dp[0].get_pixmap(dpi=150)
ap = np.frombuffer(pixp.samples, np.uint8).reshape(pixp.height, pixp.width, pixp.n)[:, :, :3].copy()
dp.close()

print("\n1. legibility increases in every lettering region")
# six lettering-rich page-fraction rects spread across the sheet (x0,y0,x1,y1)
REGIONS = {
    "pier labels W":       (0.04, 0.18, 0.16, 0.50),
    "wharf shed lettering": (0.16, 0.55, 0.30, 0.90),
    "downtown NW":         (0.32, 0.04, 0.55, 0.30),
    "downtown centre":     (0.45, 0.35, 0.70, 0.65),
    "downtown SE":         (0.70, 0.60, 0.95, 0.88),
    "park / courthouse":   (0.78, 0.06, 0.98, 0.38),
}
def contrast(img, r):
    hh, ww = img.shape[:2]
    x0, y0, x1, y1 = (int(r[0] * ww), int(r[1] * hh), int(r[2] * ww), int(r[3] * hh))
    l = lum(img[y0:y1, x0:x1].astype(np.float32))
    return float(np.percentile(l, 98) - np.percentile(l, 2))
for nm, r in REGIONS.items():
    cb, ca = contrast(ap, r), contrast(a, r)
    check(f"contrast up: {nm}", ca > cb, f"{cb:.1f} -> {ca:.1f} ({100*(ca/cb-1):+.1f}%)")
ink_p1 = float(np.percentile(lum(land.astype(np.float32)), 1))
check("ink stays dark (land lum p1 < 80)", ink_p1 < 80, f"p1 {ink_p1:.1f}")

print("\n2. no clipping of map content")
clip = 100 * float((content.max(axis=2) >= 255).mean())
check("0.00% of map content at 255", clip < 0.01, f"{clip:.3f}%")

print("\n3. anchors land on the 1899")
def paper_mode(s):
    q = (s // 3 * 3).astype(np.int32)
    k = q[:, 0] * 65536 + q[:, 1] * 256 + q[:, 2]
    v, c = np.unique(k, return_counts=True)
    mk = v[np.argmax(c)]
    return np.array([mk // 65536, (mk // 256) % 256, mk % 256], np.float64) + 1.5
p12, p99v = paper_mode(land), paper_mode(land99)
check("paper within 12 levels of the 1899", np.abs(p12 - p99v).max() < 12,
      f"1912 {tuple(p12)} vs 1899 {tuple(p99v)}  max d {np.abs(p12-p99v).max():.1f}")

def sat_of(s, h0, h1, smin=0.28, vmin=100):
    hsv = cv2.cvtColor(s.reshape(-1, 1, 3), cv2.COLOR_RGB2HSV).reshape(-1, 3).astype(np.float32)
    H, S, V = hsv[:, 0] * 2, hsv[:, 1] / 255, hsv[:, 2]
    if h1 <= 360:
        m = (H >= h0) & (H < h1) & (S > smin) & (V > vmin)
    else:
        m = ((H >= h0) | (H < h1 - 360)) & (S > smin) & (V > vmin)
    return S[m]
for nm, h0, h1 in [("yellow", 44, 70), ("pink", 340, 375)]:
    S12 = sat_of(land, h0, h1)
    S99 = sat_of(land99, h0, h1)
    if len(S12) < 1000 or len(S99) < 1000:
        check(f"{nm} sample present", False, f"{len(S12)} / {len(S99)} px")
        continue
    sat_ratio = float(np.median(S12) / np.median(S99))
    check(f"{nm} saturation within 25% of the 1899", 0.75 < sat_ratio < 1.25,
          f"ratio {sat_ratio:.2f} (median S 1912 {np.median(S12):.3f} vs 1899 {np.median(S99):.3f})")

print("\n4. orange brightened but not saturated")
def orange(s):
    hsv = cv2.cvtColor(s.reshape(-1, 1, 3), cv2.COLOR_RGB2HSV).reshape(-1, 3).astype(np.float32)
    H, S, V = hsv[:, 0] * 2, hsv[:, 1] / 255, hsv[:, 2]
    m = (H >= 18) & (H < 42) & (S > 0.30) & (V > 100)
    return S[m], V[m]
Sb, Vb = orange(ap[int(0.015*h):int(0.925*h), int(0.012*w):int(0.985*w)].reshape(-1, 3))
Sa, Va = orange(land)
check("orange median saturation within +-4% of before",
      abs(float(np.median(Sa) / np.median(Sb)) - 1) < 0.04,
      f"S {np.median(Sb):.3f} -> {np.median(Sa):.3f}")
check("orange median luminance increased", float(np.median(Va)) > float(np.median(Vb)),
      f"V {np.median(Vb):.1f} -> {np.median(Va):.1f}")

print("\n5. hue preserved")
def med_hue(s, h0, h1, smin=0.28):
    hsv = cv2.cvtColor(s.reshape(-1, 1, 3), cv2.COLOR_RGB2HSV).reshape(-1, 3).astype(np.float32)
    H, S = hsv[:, 0] * 2, hsv[:, 1] / 255
    m = (H >= h0) & (H < h1) & (S > smin)
    return float(np.median(H[m])) if m.sum() > 500 else None
for nm, h0, h1 in [("orange", 18, 42), ("yellow", 44, 70)]:
    hb = med_hue(ap.reshape(-1, 3), h0, h1)
    ha = med_hue(land, h0, h1)
    check(f"{nm} hue shift < 3 deg", hb is not None and ha is not None and abs(ha - hb) < 3,
          f"{hb:.1f} -> {ha:.1f} deg")

print("\n6. water still exactly the 1899 blue")
bay = a[int(0.55 * h):int(0.85 * h), int(0.02 * w):int(0.10 * w)].reshape(-1, 3)
med = tuple(int(v) for v in np.median(bay, axis=0))
check("open water median (199,214,209)", med == (199, 214, 209), f"{med}")

print("\n7. determinism")
m = tifffile.imread(f"{ROOT}/60_master/final/master_full.tif")
t1, _ = tone_match.apply(m[6000:8000, 8000:12000], SPEC)
t2, _ = tone_match.apply(m[6000:8000, 8000:12000], SPEC)
check("same input twice byte-identical", int((t1 != t2).sum()) == 0)
del m, t1, t2

print("\n8. upstream frozen")
r = subprocess.run([sys.executable, f"{ROOT}/90_decisions/checkpoints/verify_checkpoint.py"],
                   capture_output=True, text=True)
check("frozen-artefact verifier passes", r.returncode == 0)

print("\n9. PDF integrity")
imgs = page.get_images(full=True)
info = doc.extract_image(imgs[0][0])
check("single page", doc.page_count == 1)
check("one embedded baseline JPEG", len(imgs) == 1 and info["ext"] == "jpeg")
check("exactly 300 DPI both axes",
      round(info["width"] / (page.rect.width / 72), 2) == 300.0
      and round(info["height"] / (page.rect.height / 72), 2) == 300.0)
check("page is 40.00 x 25.84 in",
      round(page.rect.width / 72, 2) == 40.0 and round(page.rect.height / 72, 2) == 25.84)

print("\n10. visual: Central Park out of the finished PDF vs the 1899")
W, Hp = page.rect.width, page.rect.height
pm = page.get_pixmap(dpi=150, clip=pymupdf.Rect(0.79 * W, 0.05 * Hp, 1.0 * W, 0.40 * Hp))
b = np.frombuffer(pm.samples, np.uint8).reshape(pm.height, pm.width, pm.n)[:, :, :3]
cv2.imwrite(f"{OUT}/park_after.jpg", b[:, :, ::-1], [cv2.IMWRITE_JPEG_QUALITY, 94])
print(f"     wrote {OUT}/park_after.jpg")
doc.close()

print("\n" + ("ALL CHECKS PASSED" if not fails else f"FAILURES: {fails}"))
sys.exit(1 if fails else 0)
