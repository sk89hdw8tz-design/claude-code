"""Render the Pier 22 ownership candidates at native resolution.

Replicates composite_wharf.py's ownership logic exactly, restricted to a window,
with one pluggable change: inside an explicitly bounded repair neighbourhood the
panel/block content frontier may be replaced by a stated polyline. Everything
outside that rectangle uses the frozen frontier unchanged, so the candidates
differ from the delivered master only inside the neighbourhood.

Candidates rendered:
  current  -- the delivered master's rule (no override)
  S        -- SHEET 9 owns the circled rail convergence; boundary moved west
              into the jointly-blank apron between panel B's slip bulkhead and
              sheet 9's westernmost yard ink
  P        -- SHEET 5 PANEL B owns the circled rail convergence; boundary moved
              east past the whole fan

No pixel is painted, cloned, blended or interpolated: each candidate is a pure
re-assignment of which archival plate supplies which pixel.
"""

import json
import os
import sys

import cv2
import numpy as np
import tifffile
from PIL import Image
from scipy.ndimage import maximum_filter1d, median_filter

Image.MAX_IMAGE_PIXELS = None

G = "/home/user/claude-code/galveston-1912"
SCAN = ("/home/user/g1912/data-branch/galveston_1912_sources/"
        "sanborn08539_004_img009_archival.jp2")
FINAL = f"{G}/60_master/final"
OUT = "/home/user/g1912/work/pier22"
os.makedirs(OUT, exist_ok=True)

cuts = json.load(open(f"{G}/50_seams/cuts.json"))
masks = json.load(open(f"{G}/50_seams/masks.json"))
CX0, CY0, CX1, CY1 = cuts["target_extent"]["canvas_rect_mosaic"]
MW, MH = CX1 - CX0, CY1 - CY0

# ---- repair neighbourhood (canvas). Outside this rect nothing changes. -------
RX0, RY0, RX1, RY1 = 7600, 6400, 9400, 9000

# Candidate S: sheet 9 owns the convergence. Breakpoints (canvas_y, canvas_x),
# placed from the measured structure: ~20 px east of sheet 9's own slip bulkhead
# (whose east edge runs 8126 + 0.0525*(y-6600)), and west of the westernmost
# sheet 9 yard ink. The first and last breakpoints equal the frozen frontier at
# those rows, so the repaired boundary meets the frozen one with no step and
# nothing outside y 6400-9000 changes at all.
CAND_S = [(6400, 8161), (6700, 8150), (7000, 8168), (7340, 8186), (7700, 8206),
          (8000, 8216), (8300, 8232), (8500, 8246), (8600, 8210), (8800, 8130),
          (9000, 8153)]
# Candidate P: panel B owns the convergence -- boundary east of the whole fan.
CAND_P = [(6400, 9250), (9000, 9250)]

tf = json.load(open(f"{G}/40_solve/output_sheet5_joint/"
                    "transforms_sheet5_joint_shared.json"))
geo = json.load(open(f"{G}/fable_review/sheet05_candidate_regions.geojson"))
feats = {f["properties"]["region_id"]: f for f in geo["features"]}
xp = json.load(open(f"{G}/30_controls/verified/cross_panel_05.json"))

scan = cv2.imread(SCAN, cv2.IMREAD_COLOR)
SH, SW = scan.shape[:2]
DIV_HALF = 40
EDGE_INSET = {"top": 80, "bottom": 96, "left": 250, "right": 70}
div_x = 3789.0 + 0.0099 * np.arange(SH, dtype=np.float64)


def region_mask(rid):
    poly = np.array(feats[rid]["geometry"]["coordinates"][0], np.float64)
    m = np.zeros((SH, SW), np.uint8)
    cv2.fillPoly(m, [np.round(poly).astype(np.int32)], 255)
    cols = np.arange(SW)[None, :]
    xi = div_x[:, None]
    if rid == "A":
        m[cols >= (xi - DIV_HALF)] = 0
    else:
        m[cols <= (xi + DIV_HALF)] = 0
    m[:EDGE_INSET["top"], :] = 0
    m[SH - EDGE_INSET["bottom"]:, :] = 0
    m[:, :EDGE_INSET["left"]] = 0
    m[:, SW - EDGE_INSET["right"]:] = 0
    return m


def raw_matrix(p):
    r = tf["panels"][p]["raw"]
    return np.array([[r["a"], -r["b"], r["tx"]], [r["b"], r["a"], r["ty"]]], np.float64)


M_A, M_B = raw_matrix("5A"), raw_matrix("5B")
CUT_POLYLINE = [(-1e9, 7750.0), (7850.0, 7750.0), (8100.0, 6620.0), (1e9, 6620.0)]


def cut_y_canvas(xs):
    px = np.array([p[0] for p in CUT_POLYLINE], np.float64)
    py = np.array([p[1] for p in CUT_POLYLINE], np.float64)
    return np.interp(xs, px, py)


# ---- frozen frontier, recomputed exactly as composite_wharf.py does ----------
blk_only = tifffile.imread(f"{FINAL}/candidate_master.tif")
gg = blk_only[:, 6900:11000].mean(axis=2).astype(np.float32)
ii = (gg < 140).astype(np.float32)
dd = cv2.boxFilter(ii, -1, (41, 41), normalize=True)
run = cv2.boxFilter(dd, -1, (301, 1), normalize=True)
frontier0 = np.full(run.shape[0], 10 ** 9, np.int64)
for yy in range(run.shape[0]):
    ok = np.where(run[yy] > 0.05)[0]
    if len(ok):
        frontier0[yy] = 6900 + ok[0]
frontier0 = maximum_filter1d(frontier0, size=281)
frontier0 = median_filter(frontier0, size=41)
del gg, ii, dd, run

block_owned = np.zeros((MH, MW), np.uint8)
for r in masks["regions"]:
    ring = np.array(r["polygon_mosaic"]["exterior"], np.float64) - [CX0, CY0]
    cv2.fillPoly(block_owned, [np.round(ring).astype(np.int32)], 255)


def make_frontier(spec):
    f = frontier0.copy()
    if spec is None:
        return f
    ys = np.array([p[0] for p in spec], np.float64)
    xs = np.array([p[1] for p in spec], np.float64)
    rows = np.arange(RY0, RY1)
    f[RY0:RY1] = np.round(np.interp(rows, ys, xs)).astype(np.int64)
    return f


# ---- window render ----------------------------------------------------------
WX0, WY0, WX1, WY1 = 7300, 6400, 9500, 10600
WW, WH_ = WX1 - WX0, WY1 - WY0
maskA_sheet, maskB_sheet = region_mask("A"), region_mask("B")


def render(spec, tag):
    # window read from module globals on every call, so callers may retarget it
    WX0, WY0, WX1, WY1 = globals()["WX0"], globals()["WY0"], globals()["WX1"], globals()["WY1"]
    WW, WH_ = WX1 - WX0, WY1 - WY0
    frontier = make_frontier(spec)
    base = np.ascontiguousarray(
        tifffile.imread(f"{FINAL}/candidate_master.tif")[WY0:WY1, WX0:WX1])
    for name, (M, mine, other, M_other, owns_east) in {
            "A": (M_A, maskA_sheet, maskB_sheet, M_B, True),
            "B": (M_B, maskB_sheet, maskA_sheet, M_A, False)}.items():
        Msub = M.copy()
        Msub[0, 2] += -CX0 - WX0
        Msub[1, 2] += -CY0 - WY0
        wimg = cv2.warpAffine(scan, Msub, (WW, WH_), flags=cv2.INTER_LANCZOS4,
                              borderMode=cv2.BORDER_CONSTANT, borderValue=(255, 255, 255))
        wmask = cv2.warpAffine(mine, Msub, (WW, WH_), flags=cv2.INTER_NEAREST,
                               borderMode=cv2.BORDER_CONSTANT, borderValue=0) > 0
        Mo = M_other.copy()
        Mo[0, 2] += -CX0 - WX0
        Mo[1, 2] += -CY0 - WY0
        womask = cv2.warpAffine(other, Mo, (WW, WH_), flags=cv2.INTER_NEAREST,
                                borderMode=cv2.BORDER_CONSTANT, borderValue=0) > 0
        xs_c = np.arange(WX0, WX1, dtype=np.float64)
        ys_c = np.arange(WY0, WY1, dtype=np.float64)
        east = ys_c[:, None] < cut_y_canvas(xs_c)[None, :]
        myside = east if owns_east else ~east
        blk_own = block_owned[WY0:WY1, WX0:WX1] > 0
        blk = blk_own & (np.arange(WX0, WX1)[None, :] >= frontier[WY0:WY1, None])
        allowed = wmask & ~blk & (~womask | myside)
        base[allowed] = wimg[allowed][:, ::-1]
    cv2.imwrite(f"{OUT}/cand_{tag}.jpg", base[:, :, ::-1],
                [cv2.IMWRITE_JPEG_QUALITY, 94])
    return base


if __name__ == "__main__":
    outs = {}
    for tag, spec in [("current", None), ("S", CAND_S), ("P", CAND_P)]:
        outs[tag] = render(spec, tag)
        print(f"rendered cand_{tag}.jpg")

    def ink(a):
        g = cv2.cvtColor(a[:, :, ::-1], cv2.COLOR_BGR2GRAY)
        return float((g < 145).mean())

    print(f"\nwindow canvas x{WX0}-{WX1} y{WY0}-{WY1}  ({WW}x{WH_})")
    for tag in outs:
        print(f"  cand_{tag}: ink {ink(outs[tag]):.4f}")
    d = np.abs(outs["current"].astype(np.int16) - outs["S"].astype(np.int16)).max(axis=2)
    print(f"  pixels changed current->S: {int((d > 6).sum()):,} "
          f"({100*float((d > 6).mean()):.2f}% of window)")
    ys, xs = np.where(d > 6)
    if len(xs):
        print(f"  change bbox canvas x{WX0+xs.min()}..{WX0+xs.max()} "
              f"y{WY0+ys.min()}..{WY0+ys.max()}")
