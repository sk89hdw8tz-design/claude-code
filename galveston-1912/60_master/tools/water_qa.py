"""Verification for the D-015 water treatment. Every check is an assertion.

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
import water_treatment as wt  # noqa: E402

ROOT = "/home/user/claude-code/galveston-1912"
SPEC = f"{ROOT}/50_seams/water_regions.geojson"
MASTER = f"{ROOT}/60_master/final/master_full.tif"
PDF = f"{ROOT}/deliverables/Galveston_1912_Wharf_Downtown_print.pdf"
OUT = "/home/user/g1912/work/water"
os.makedirs(OUT, exist_ok=True)
fails = []


def check(name, ok, detail=""):
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}{('  ' + detail) if detail else ''}")
    if not ok:
        fails.append(name)


print("loading master ...")
src = tifffile.imread(MASTER)
treated, st = wt.apply(src, SPEC)
print(json.dumps(st, indent=1))

print("\n1. determinism")
# NOT self-idempotence. Compositing ink over the fill with a partial coverage
# alpha is by construction not idempotent: re-running on the OUTPUT blends the
# same ink toward the water colour a second time and lightens it. Re-applying
# to the output is therefore not a meaningful test. What must hold, and what
# reproducibility actually requires, is that the same input always yields the
# same output.
again, _ = wt.apply(src, SPEC)
d = int((np.abs(again.astype(np.int16) - treated.astype(np.int16)).max(axis=2) > 0).sum())
check("same input twice gives identical output", d == 0, f"{d:,} px differ")
del again

print("\n2. upstream untouched")
r = subprocess.run([sys.executable, f"{ROOT}/90_decisions/checkpoints/verify_checkpoint.py"],
                   capture_output=True, text=True)
tail = [l for l in r.stdout.splitlines() if "changed" in l or "byte-identical" in l]
check("frozen-artefact verifier passes", r.returncode == 0, " | ".join(tail[-2:]))
check("master_full.tif not written by this stage",
      "current_master_full" not in r.stdout.split("changed        :")[-1]
      or "CHANGED" not in r.stdout.split("current_master_full")[-1][:40],
      "")

print("\n3. no leak")
geo = json.load(open(SPEC))
bnd = [np.array(f["geometry"]["coordinates"][0], np.float64)
       for f in geo["features"] if f["properties"]["role"] == "bound"][0]
H, W = treated.shape[:2]
bm = np.zeros((H, W), np.uint8)
cv2.fillPoly(bm, [np.round(bnd).astype(np.int32)], 1)
water, alpha, _ = wt.build_mask(src, SPEC)
check("no water outside the bound polygon", int((water & (bm == 0)).sum()) == 0,
      f"{int((water & (bm == 0)).sum()):,} px outside")
AVE_A_X = 9000
check(f"no water east of canvas x={AVE_A_X} (Avenue A frontage)",
      int(water[:, AVE_A_X:].sum()) == 0, f"east bbox {st['recoloured_bbox_canvas'][2]}")

print("\n4. ink preserved")
a_pre = alpha > 0.5
pre = int((water & a_pre).sum())
g = treated.mean(axis=2).astype(np.float32)
bgm = cv2.blur(cv2.morphologyEx(g, cv2.MORPH_CLOSE,
              cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (61, 61))), (121, 121))
post = int((water & (np.clip((wt.INK_HI - g / np.maximum(bgm, 1.0)) /
                             (wt.INK_HI - wt.INK_LO), 0, 1) > 0.5)).sum())
check("ink pixels inside the water mask survive", post >= pre * 0.98,
      f"before {pre:,}  after {post:,}")

print("\n5. colour matches the 1899 sheet")
seed = [np.array(f["geometry"]["coordinates"][0], np.float64)
        for f in geo["features"] if f["properties"]["role"] == "seed"][0]
sm = np.zeros((H, W), np.uint8)
cv2.fillPoly(sm, [np.round(seed).astype(np.int32)], 1)
samp = treated[(sm > 0) & water]
med = tuple(int(v) for v in np.median(samp, axis=0))
check("open water median is exactly the 1899 value", med == wt.WATER_RGB,
      f"{med} vs {wt.WATER_RGB}")

print("\n6. white gone from the water area")
comp = json.load(open(f"{ROOT}/deliverables/print_composition.json"))
mx0, my0, mx1, my1 = comp["map_rect_canvas_xyxy"]
allw = (treated[:, :, 0] == 255) & (treated[:, :, 1] == 255) & (treated[:, :, 2] == 255)
# clip the bound to the PRINTED rect: the bound polygon runs west to canvas x=0,
# and that uncovered canvas is cropped away by the page and never printed.
bay_printed = (bm > 0)
bay_printed[:, :mx0] = False
bay_printed[:my0] = False
bay_printed[my1:] = False
bay_printed[:, mx1:] = False
inbay = int((allw & bay_printed).sum())
check("no pure-255 pixels remain anywhere in the bay", inbay == 0, f"{inbay:,} px")
# Elsewhere in the printed rect a handful of 1 px slivers survive where abutting
# block sheets fail to meet. They are present in candidate_master.tif, so they
# pre-date the wharf composite and this stage entirely, and are unrelated to
# water. Reported, not silently tolerated.
rect = allw[my0:my1, mx0:mx1]
elsewhere = int(rect.sum()) - inbay
print(f"     note: {elsewhere} pure-255 px elsewhere in the printed rect "
      f"(1 px inter-sheet seams, pre-existing in candidate_master.tif)")
del rect, allw, treated, src

print("\n7. PDF integrity")
doc = pymupdf.open(PDF)
p = doc[0]
imgs = p.get_images(full=True)
info = doc.extract_image(imgs[0][0])
dpi_x = info["width"] / (p.rect.width / 72)
dpi_y = info["height"] / (p.rect.height / 72)
check("single page", doc.page_count == 1)
check("one embedded baseline JPEG", len(imgs) == 1 and info["ext"] == "jpeg")
check("exactly 300 DPI both axes", round(dpi_x, 2) == 300.0 and round(dpi_y, 2) == 300.0,
      f"{dpi_x:.2f} x {dpi_y:.2f}")
check("page is 40.00 x 25.84 in",
      round(p.rect.width / 72, 2) == 40.0 and round(p.rect.height / 72, 2) == 25.84,
      f"{p.rect.width/72:.2f} x {p.rect.height/72:.2f}")

print("\n8. native-resolution crops rendered back OUT of the finished PDF")
sc = comp["resample"]["scale"]
ox = oy = int(round(180 * sc))
spots = {"bay_uncovered_seam": (3324, 7700, 5400, 8600),
         "slip_pier22": (6600, 6600, 8400, 8800),
         "bay_lettering": (3600, 10400, 5400, 12000),
         "scalebar": (3300, 6800, 5800, 7500),
         "pier22_splice_D014": (7900, 6500, 9300, 9400)}
for nm, (x0, y0, x1, y1) in spots.items():
    px0 = (ox + (x0 - mx0) * sc) / 300 * 72
    py0 = (oy + (y0 - my0) * sc) / 300 * 72
    px1 = (ox + (x1 - mx0) * sc) / 300 * 72
    py1 = (oy + (y1 - my0) * sc) / 300 * 72
    pm = p.get_pixmap(dpi=300, clip=pymupdf.Rect(px0, py0, px1, py1))
    a = np.frombuffer(pm.samples, np.uint8).reshape(pm.height, pm.width, pm.n)[:, :, :3]
    cv2.imwrite(f"{OUT}/pdf_{nm}.jpg", a[:, :, ::-1], [cv2.IMWRITE_JPEG_QUALITY, 95])
    print(f"     wrote pdf_{nm}.jpg  {a.shape[1]}x{a.shape[0]}")
doc.close()

print("\n" + ("ALL CHECKS PASSED" if not fails else f"FAILURES: {fails}"))
sys.exit(1 if fails else 0)
