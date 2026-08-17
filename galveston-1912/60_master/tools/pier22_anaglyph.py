"""Registration test between the two plates that both draw the Pier 22 rail fan.

Provenance (masks.json) shows the non-panel content here is region s09_r0 —
Sheet 9 — so the boundary breaking the tracks is *Sheet 5 panel B vs Sheet 9*,
not the A|B panel cut. This renders both in the same canvas frame as a red/cyan
anaglyph: agreement prints neutral, disagreement splits into a red ghost and a
cyan ghost whose separation IS the misregistration.

The sheet-5 scan darkens markedly toward its right side (bright page detected
only to x=4447 of 6653), so a fixed grey threshold measures illumination rather
than line work. Both layers are therefore flat-fielded against a large-kernel
background estimate before any ink is extracted or correlated.
"""

import json
import os

import cv2
import numpy as np
import tifffile
from PIL import Image

Image.MAX_IMAGE_PIXELS = None

G = "/home/user/claude-code/galveston-1912"
SCAN = ("/home/user/g1912/data-branch/galveston_1912_sources/"
        "sanborn08539_004_img009_archival.jp2")
OUT = "/home/user/g1912/work/pier22"
os.makedirs(OUT, exist_ok=True)

X0, Y0, X1, Y1 = 7400, 7100, 9300, 9400
W, H = X1 - X0, Y1 - Y0
CX0, CY0 = -16734, -8279
PX_PER_FT = 5.76

tf = json.load(open(f"{G}/40_solve/output_sheet5_joint/"
                    "transforms_sheet5_joint_shared.json"))["panels"]
geo = json.load(open(f"{G}/fable_review/sheet05_candidate_regions.geojson"))
feats = {f["properties"].get("region_id"): f for f in geo["features"]}
scan = cv2.imread(SCAN, cv2.IMREAD_COLOR)
SH, SW = scan.shape[:2]


def panel_layer(rid):
    key = "5A" if "A" in rid else "5B"
    r = tf[key]["raw"]
    M = np.array([[r["a"], -r["b"], r["tx"] - CX0 - X0],
                  [r["b"], r["a"], r["ty"] - CY0 - Y0]], np.float64)
    ring = np.array(feats[rid]["geometry"]["coordinates"][0], np.float64)
    ms = np.zeros((SH, SW), np.uint8)
    cv2.fillPoly(ms, [np.round(ring).astype(np.int32)], 255)
    img = cv2.warpAffine(scan, M, (W, H), flags=cv2.INTER_LANCZOS4,
                         borderMode=cv2.BORDER_CONSTANT, borderValue=(255, 255, 255))
    msk = cv2.warpAffine(ms, M, (W, H), flags=cv2.INTER_NEAREST,
                         borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    img[msk == 0] = 255
    return img, msk > 0


def flat_ink(bgr, drop=0.16):
    """Ink mask relative to a locally-estimated paper level (flat-fielding)."""
    g = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY).astype(np.float32)
    bg = cv2.morphologyEx(g, cv2.MORPH_CLOSE,
                          cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (61, 61)))
    bg = cv2.blur(bg, (121, 121))
    rel = g / np.maximum(bg, 1.0)
    return (rel < (1.0 - drop)), rel


s9 = np.ascontiguousarray(
    tifffile.imread(f"{G}/60_master/final/candidate_master.tif")[Y0:Y1, X0:X1][:, :, ::-1])
imgB, mB = panel_layer("B")

ink9, rel9 = flat_ink(s9)
inkB, relB = flat_ink(imgB)
inkB &= mB

# tone-normalised anaglyph: panel B -> red, sheet 9 -> cyan
vB = np.clip(relB * 255, 0, 255).astype(np.uint8)
v9 = np.clip(rel9 * 255, 0, 255).astype(np.uint8)
cv2.imwrite(f"{OUT}/w_anaglyph_B_vs_s9.jpg", np.dstack([vB, v9, v9]),
            [cv2.IMWRITE_JPEG_QUALITY, 94])
cv2.imwrite(f"{OUT}/w_flat_panelB.jpg", vB, [cv2.IMWRITE_JPEG_QUALITY, 94])
cv2.imwrite(f"{OUT}/w_flat_sheet9.jpg", v9, [cv2.IMWRITE_JPEG_QUALITY, 94])

RX0, RX1, RY0, RY1 = 8500, 9300, 7300, 9200          # rail fan, both plates draw it
sl = (slice(RY0 - Y0, RY1 - Y0), slice(RX0 - X0, RX1 - X0))
a = inkB[sl].astype(np.float32)
b = ink9[sl].astype(np.float32)
print(f"rail-fan test region canvas x{RX0}-{RX1} y{RY0}-{RY1}")
print(f"  flat-field ink: panelB {a.mean():.4f}   sheet9 {b.mean():.4f}")

best = None
grid = []
for oy in range(-70, 71):
    for ox in range(-70, 71):
        bb = np.roll(np.roll(b, oy, axis=0), ox, axis=1)
        s = float((a * bb).sum())
        grid.append((s, ox, oy))
        if best is None or s > best[0]:
            best = (s, ox, oy)
base = float((a * b).sum())
print(f"  best ink overlap at (dx,dy) = ({best[1]:+d},{best[2]:+d}) px "
      f"= {np.hypot(best[1], best[2])/PX_PER_FT:.1f} ft")
print(f"  score {best[0]:,.0f}  vs zero-shift {base:,.0f}  "
      f"(gain {100*(best[0]/max(base,1)-1):+.1f}%)")
grid.sort(reverse=True)
print("  top-5 shifts:", [(o[1], o[2], round(o[0])) for o in grid[:5]])

print("\nper-row leftmost sustained drafted content (canvas x)")
print("   row     panelB   sheet9")


def frontier(ink):
    d = cv2.boxFilter(ink.astype(np.float32), -1, (81, 81), normalize=True)
    out = np.full(H, -1.0)
    for y in range(H):
        idx = np.where(d[y] > 0.012)[0]
        if len(idx):
            out[y] = idx[0] + X0
    return out


fB, f9 = frontier(inkB), frontier(ink9)
for y in range(0, H, 200):
    print(f"   {Y0+y:5d}  {fB[y]:9.0f} {f9[y]:8.0f}")
print(f"\nwrote {OUT}/w_anaglyph_B_vs_s9.jpg")
