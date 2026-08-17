#!/usr/bin/env python
"""census.py — QA stage 6: whole-footprint hidden-content census.

Question (QA_PLAN #6): does any ORIGINAL plate draw meaningful cartography, on
ground covered by the master, that the master does not show?

Method, per contributing sheet:
  * page-isolated drawn-content map at ds=4 using the SAME calibration as the
    render agent's content_extent_check (page = largest bright CC of grey>140,
    holes filled; ink = grey < Otsu-within-page clamped [80,185] — the literal
    ink<185 was validated and REJECTED for these scans, see
    60_master/content_extent_report.json "method"),
  * warped into the mosaic canvas at 1/2 native scale (INTER_NEAREST),
  * minus the sheet's own ownership raster (dilated 1 px = 2 native px, the
    raster ambiguity of the cut line — disclosed tolerance),
  * restricted to the canvas (the master's ground).
  Connected components of the remainder > 400 native px^2 are listed; every
  component > 2000 native px^2 gets a side-by-side inspection crop (original
  scan vs master at the same ground) for MANDATORY visual verdicts:
  OWNED-BY-NEIGHBOUR-CORRECTLY / FURNITURE-BY-DESIGN / HIDDEN-CONTENT-FAIL.

Self-test (tool-validation gate): a synthetic 200x200 px square of
"cartography" hidden outside the ownership region MUST be detected before the
real census runs.

Report-only. Writes only under 70_qa/run1/census/.
"""

import json
import os
import sys

import cv2
import numpy as np
from scipy import ndimage

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import qalib
from qalib import RUN, sl

sys.path.insert(0, os.path.join(qalib.PROJECT, "60_master", "tools"))
from content_extent_check import page_and_ink  # noqa: E402  (method identity)

OUT_DIR = os.path.join(RUN, "census")
CSCALE = 0.5          # census canvas scale (area factor 4 native px^2 per px)
DS = 4                # sheet-frame downsample for ink extraction
LIST_MIN_PX2 = 400    # native px^2
INSPECT_MIN_PX2 = 2000


def ink_to_canvas(geo, sheet, ink_ds, shape_hw, T=None):
    """Warp a ds-downsampled sheet-frame binary into the census canvas."""
    x0m, y0m = geo["mosaic_rect"][:2]
    T = T or geo["raw"][sheet]
    M = sl.warp_matrix(T, origin=(x0m, y0m), scale=geo["scale"] * CSCALE)
    Mds = M.copy()
    Mds[:, :2] *= DS
    Mds[:, 2] += Mds[:, :2] @ np.array([0.5 * (DS - 1) / DS] * 2)
    H, W = shape_hw
    return cv2.warpAffine(ink_ds, Mds, (W, H), flags=cv2.INTER_NEAREST,
                          borderMode=cv2.BORDER_CONSTANT, borderValue=0)


def own_raster_canvas(geo, shape_hw, sheets=None):
    """{sheet: canvas-scale ownership raster} via polygon fill (census scale)."""
    H, W = shape_hw
    x0m, y0m = geo["mosaic_rect"][:2]
    s = geo["scale"] * CSCALE
    out = {}
    for r in geo["regions"]:
        if sheets is not None and r["sheet"] not in sheets:
            continue
        m = out.setdefault(r["sheet"], np.zeros((H, W), np.uint8))
        ext = np.asarray(r["feat"]["polygon_mosaic"]["exterior"], float)
        ext = np.rint((ext - [x0m, y0m]) * s).astype(np.int32)
        cv2.fillPoly(m, [ext], 255)
        for hole in r["feat"]["polygon_mosaic"]["interiors"]:
            h = np.rint((np.asarray(hole, float) - [x0m, y0m]) * s).astype(np.int32)
            cv2.fillPoly(m, [h], 0)
    return out


def census_components(diff, min_px2_native):
    """Connected components of a census-scale binary, area in native px^2."""
    n, lab, stats, cent = cv2.connectedComponentsWithStats(
        diff.astype(np.uint8), connectivity=8)
    comps = []
    factor = (1.0 / CSCALE) ** 2
    for i in range(1, n):
        area_native = stats[i, cv2.CC_STAT_AREA] * factor
        if area_native >= min_px2_native:
            x, y, w, h = (stats[i, cv2.CC_STAT_LEFT], stats[i, cv2.CC_STAT_TOP],
                          stats[i, cv2.CC_STAT_WIDTH], stats[i, cv2.CC_STAT_HEIGHT])
            comps.append({"label": int(i),
                          "area_native_px2": int(area_native),
                          "bbox_census": [int(x), int(y), int(w), int(h)],
                          "centroid_census": [float(cent[i][0]), float(cent[i][1])]})
    comps.sort(key=lambda c: -c["area_native_px2"])
    return comps, lab


# ---------------------------------------------------------------------------
# self-test

def self_test():
    """Hide a 200x200 native-px square of synthetic cartography outside the
    ownership region; the census pipeline must find it."""
    # synthetic sheet scan: dark backdrop, noisy bright page, square of ink.
    # (values chosen with realistic bimodal separation — a first attempt used
    # square==Otsu threshold exactly and detected nothing; the gate caught it)
    rng = np.random.default_rng(3)
    sw, sh = 2400, 2000
    scan = np.full((sh, sw), 60, np.uint8)                       # backdrop
    scan[100:1900, 100:2300] = rng.normal(
        172, 6, (1800, 2200)).clip(150, 195).astype(np.uint8)    # paper
    for y in range(300, 1700, 97):                               # drawn grid
        scan[y:y + 3, 200:2200] = rng.normal(
            105, 10, (3, 2000)).clip(70, 140).astype(np.uint8)
    sq = (900, 800)                                              # square origin
    scan[sq[1]:sq[1] + 200, sq[0]:sq[0] + 200] = rng.normal(
        88, 8, (200, 200)).clip(60, 120).astype(np.uint8)        # hidden square
    page_ds, ink_ds, t_ink = page_and_ink(
        cv2.resize(scan, (sw // DS, sh // DS), interpolation=cv2.INTER_AREA))
    # geometry: identity transform, canvas == sheet, ownership excludes square
    geo = {"mosaic_rect": (0.0, 0.0, float(sw), float(sh)), "scale": 1.0,
           "raw": {1: {"a": 1.0, "b": 0.0, "tx": 0.0, "ty": 0.0}},
           "regions": [{"sheet": 1, "feat": {"polygon_mosaic": {
               "exterior": [[100, 100], [800, 100], [800, 1900], [100, 1900]],
               "interiors": []}}}]}
    shape_hw = (int(sh * CSCALE), int(sw * CSCALE))
    inkc = ink_to_canvas(geo, 1, (ink_ds * 255).astype(np.uint8), shape_hw)
    own = own_raster_canvas(geo, shape_hw)[1]
    own = cv2.dilate(own, np.ones((3, 3), np.uint8))
    diff = (inkc > 0) & (own == 0)
    comps, _ = census_components(diff, LIST_MIN_PX2)
    hits = [c for c in comps
            if abs(c["centroid_census"][0] - (sq[0] + 100) * CSCALE) < 40
            and abs(c["centroid_census"][1] - (sq[1] + 100) * CSCALE) < 40
            and c["area_native_px2"] >= 200 * 200 * 0.6]
    assert hits, "census self-test FAILED: hidden 200px square not detected"
    return {"result": "PASS",
            "detected_area_native_px2": hits[0]["area_native_px2"],
            "expected_px2": 40000, "ink_threshold": float(t_ink)}


# ---------------------------------------------------------------------------

def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    qalib.verify_frozen_inputs()

    st = self_test()
    print("census self-test:", st["result"],
          "(detected %(detected_area_native_px2)d px2 of expected 40000)" % st)

    geo = qalib.load_geometry()
    master = qalib.master_array()
    W, H = geo["size"]
    shape_hw = (int(round(H * CSCALE)), int(round(W * CSCALE)))
    msha = qalib.master_sha256()
    sha16 = msha[:16]
    band_w_census = geo["manifest"]["canvas"]["reserved_bay_band_canvas_px"][2] * CSCALE

    owns = own_raster_canvas(geo, shape_hw)
    own_all = {s: (m > 0) for s, m in owns.items()}
    kernel = np.ones((3, 3), np.uint8)

    results = []
    for sheet in sorted(geo["raw"]):
        item = geo["inventory"][sheet]
        bgr = qalib._load_sheet_bgr(geo, sheet)
        grey = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        grey_ds = cv2.resize(grey, (grey.shape[1] // DS, grey.shape[0] // DS),
                             interpolation=cv2.INTER_AREA)
        del grey
        page_ds, ink_ds, t_ink = page_and_ink(grey_ds)
        edge_dist_ds = ndimage.distance_transform_edt(page_ds)

        inkc = ink_to_canvas(geo, sheet, (ink_ds * 255).astype(np.uint8), shape_hw)
        own_dil = cv2.dilate(owns[sheet], kernel)
        diff = (inkc > 0) & (own_dil == 0)

        comps, lab = census_components(diff, LIST_MIN_PX2)
        neigh = np.zeros(shape_hw, bool)
        for s2, m2 in own_all.items():
            if s2 != sheet:
                neigh |= m2

        Tinv = sl.invert_raw(geo["raw"][sheet])
        x0m, y0m = geo["mosaic_rect"][:2]
        for c in comps:
            x, y, w, h = c["bbox_census"]
            sel = lab[y:y + h, x:x + w] == c["label"]
            c["sheet"] = sheet
            c["pct_owned_by_neighbour"] = round(
                100.0 * (sel & neigh[y:y + h, x:x + w]).sum() / sel.sum(), 1)
            c["pct_in_reserved_band"] = round(
                100.0 * (sel & (np.arange(x, x + w) < band_w_census)[None, :]).sum()
                / sel.sum(), 1)
            # centroid in mosaic / sheet frames; page-edge distance
            cm = np.array(c["centroid_census"]) / CSCALE + [x0m, y0m]
            ps = sl.apply_raw(Tinv, cm)
            c["centroid_mosaic"] = [round(float(cm[0]), 1), round(float(cm[1]), 1)]
            c["centroid_sheet_px"] = [round(float(ps[0]), 1), round(float(ps[1]), 1)]
            iy = int(np.clip(ps[1] / DS, 0, edge_dist_ds.shape[0] - 1))
            ix = int(np.clip(ps[0] / DS, 0, edge_dist_ds.shape[1] - 1))
            c["page_edge_dist_px"] = round(float(edge_dist_ds[iy, ix] * DS), 1)
            c["inspect"] = bool(c["area_native_px2"] >= INSPECT_MIN_PX2)

        # inspection crops: original scan vs master, same ground, native res
        for c in [c for c in comps if c["inspect"]]:
            x, y, w, h = c["bbox_census"]
            pad = 40
            nx0 = int(max(0, (x - pad) / CSCALE))
            ny0 = int(max(0, (y - pad) / CSCALE))
            nx1 = int(min(W, (x + w + pad) / CSCALE))
            ny1 = int(min(H, (y + h + pad) / CSCALE))
            mcrop = np.asarray(master[ny0:ny1, nx0:nx1])
            # map the same canvas rect corners into the sheet frame
            corners_c = np.array([[nx0, ny0], [nx1, ny0], [nx1, ny1], [nx0, ny1]],
                                 float)
            corners_m = corners_c / geo["scale"] + [x0m, y0m]
            corners_s = sl.apply_raw(Tinv, corners_m)
            sx0, sy0 = np.floor(corners_s.min(axis=0)).astype(int)
            sx1, sy1 = np.ceil(corners_s.max(axis=0)).astype(int)
            sx0, sy0 = max(0, sx0), max(0, sy0)
            sx1 = min(item["width"], sx1)
            sy1 = min(item["height"], sy1)
            scrop = bgr[sy0:sy1, sx0:sx1][..., ::-1]
            hmax = max(mcrop.shape[0], scrop.shape[0], 1)

            def fit(im):
                if im.size == 0:
                    return np.full((hmax, 60, 3), 200, np.uint8)
                if im.shape[0] != hmax:
                    f = hmax / im.shape[0]
                    im = cv2.resize(im, (max(1, int(im.shape[1] * f)), hmax),
                                    interpolation=cv2.INTER_AREA)
                return im
            sep = np.full((hmax, 8, 3), 30, np.uint8)
            panel = np.hstack([fit(scrop), sep, fit(mcrop)])
            maxw = 2000
            if panel.shape[1] > maxw:
                f = maxw / panel.shape[1]
                panel = cv2.resize(panel, (maxw, max(1, int(panel.shape[0] * f))),
                                   interpolation=cv2.INTER_AREA)
            cid = "s%02d_c%03d" % (sheet, c["label"])
            hdr = qalib.label_bar(panel.shape[1], [
                "census %s  area %d px2  nbr %.0f%%  band %.0f%%  edge %spx" % (
                    cid, c["area_native_px2"], c["pct_owned_by_neighbour"],
                    c["pct_in_reserved_band"], c["page_edge_dist_px"]),
                "LEFT original sheet %d [%d:%d,%d:%d]  RIGHT master canvas "
                "[%d:%d,%d:%d]  sha %s..." % (sheet, sx0, sx1, sy0, sy1,
                                              nx0, nx1, ny0, ny1, sha16)])
            qalib.save_png(os.path.join(OUT_DIR, "census_%s.png" % cid),
                           np.vstack([hdr, panel]))
            c["crop_png"] = "census_census_%s.png" % cid
            c["crop_png"] = "census_%s.png" % cid
            c["id"] = cid

        results.extend(comps)
        n_big = sum(1 for c in comps if c["inspect"])
        print("sheet %2d ink<%.0f: %3d comps > %d px2, %2d to inspect "
              "(largest %d px2)" % (sheet, t_ink, len(comps), LIST_MIN_PX2,
                                    n_big, comps[0]["area_native_px2"] if comps else 0))
        del bgr

    meta = {
        "stamp": qalib.stamp("70_qa/tools/census.py", {"self_test": st}),
        "method": {
            "ink": "page-isolated Otsu-within-page clamp [80,185] at ds=%d "
                   "(content_extent_check.page_and_ink, method identity)" % DS,
            "census_scale": CSCALE,
            "ownership_tolerance": "own raster dilated 1 census px (= 2 native "
                                   "px cut-line raster ambiguity)",
            "list_threshold_native_px2": LIST_MIN_PX2,
            "inspect_threshold_native_px2": INSPECT_MIN_PX2,
        },
        "components": results,
        "verdict_placeholder": "visual verdicts recorded in census_verdicts.json",
    }
    qalib.write_json(os.path.join(RUN, "census_components.json"), meta)
    print("wrote census_components.json: %d listed, %d to inspect" %
          (len(results), sum(1 for c in results if c["inspect"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
