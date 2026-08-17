#!/usr/bin/env python
"""content_extent_check.py — verify the cuts do not amputate drawn cartography.

The anti-1889-failure tool. For each sheet and each of its bounding cut lines,
measure the sheet's ACTUAL drawn-content (ink) extent near the seam and report
how far ink encroaches BEYOND the cut toward the neighbour's side. Reports
only; never auto-fixes, never moves a cut.

Ink detection uses the page-isolated method (see 90_decisions/
FAILED_EXPERIMENTS.md F-001: the LOC scans sit on a dark gridded backdrop, so
naive thresholds classify the backdrop as ink): the page is the largest
connected bright component (grey > 140), holes filled; ink = grey < 185 within
the page.

Interpretation aid: each plate legitimately draws mid-street furniture past the
centreline (water-pipe runs, street-name labels, width annotations), and its
own neatline/border lives near the page edge beyond the far side of the
street. The report therefore separates encroachment inside the street corridor
(0..half-width past the cut) from ink in the far margin zone, and reports the
deepest connected encroaching blob so a human can read what it is.
"""

import argparse
import json
import os
import sys

import cv2
import numpy as np
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(PROJECT, "50_seams"))
import seamlib as sl  # noqa: E402

PAPER_MIN_GREY = 140  # page isolation: paper is brighter than this
INK_MAX_GREY = 185    # prescribed ink ceiling — see calibration note below
BORDER_ZONE_PX = 100  # ink this close to the page boundary = neatline/margin furniture

# CALIBRATION (validated on sheets 7, 9, 44 before use, per F-001/F-003 policy of
# never trusting a threshold that merely produces output): on the LOC archival
# JP2s the paper tone is ~150-190 grey, so a literal `ink < 185` classifies
# 84-99% of the PAPER as ink — confident, well-formed, meaningless. The page
# isolation (paper > 140) stands; the effective ink threshold is derived per
# page as Otsu within the page region (measured 121-139 on the three validation
# sheets, ink fractions 7-21%, building tints correctly counted as drawn
# content), clamped to [80, INK_MAX_GREY].


def page_and_ink(grey):
    """Page mask (largest bright component, holes filled), ink-on-page, and the
    effective per-page ink threshold."""
    bright = grey > PAPER_MIN_GREY
    lab, n = ndimage.label(bright)
    if n == 0:
        raise RuntimeError("no bright page component found")
    sizes = ndimage.sum(bright, lab, range(1, n + 1))
    page = lab == (1 + int(np.argmax(sizes)))
    page = ndimage.binary_fill_holes(page)
    vals = grey[page].astype(np.uint8)
    t_otsu, _ = cv2.threshold(vals.reshape(-1, 1), 0, 255,
                              cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    t_ink = float(np.clip(t_otsu, 80, INK_MAX_GREY))
    ink = (grey < t_ink) & page
    return page, ink, t_ink


def line_to_sheet_frame(line, T):
    """Map a mosaic-frame cut line into this sheet's pixel frame."""
    inv = sl.invert_raw(T)
    p0 = sl.apply_raw(inv, np.asarray(line["p0"], float))
    p1 = sl.apply_raw(inv, np.asarray(line["p0"], float) + np.asarray(line["dir"], float))
    d = p1 - p0
    d /= np.linalg.norm(d)
    n = np.array([-d[1], d[0]])
    return {"p0": [float(p0[0]), float(p0[1])],
            "dir": [float(d[0]), float(d[1])],
            "normal": [float(n[0]), float(n[1])]}


def check_sheet_street(page_ds, ink_ds, edge_dist_ds, ds, T, street, sheet):
    """Encroachment stats for one sheet against one street's cut line.

    NOTE: uses the street's fitted straight line; if cuts.json ever contains
    flagged deviated spans, their extra clearance is by construction AWAY from
    this sheet's content, so this straight-line check is conservative."""
    line_s = line_to_sheet_frame(street["line_fit"], T)
    sgn = street["sheet_side_sign"][str(sheet)]
    halfw = float(street["mean_half_street_width_px"])

    h, w = page_ds.shape
    ys, xs = np.mgrid[0:h, 0:w]
    fx = (xs + 0.5) * ds
    fy = (ys + 0.5) * ds
    off = (fx - line_s["p0"][0]) * line_s["normal"][0] + \
          (fy - line_s["p0"][1]) * line_s["normal"][1]
    enc = -sgn * off  # >0 = beyond the cut, toward the neighbour

    border = edge_dist_ds * ds <= BORDER_ZONE_PX  # neatline / margin furniture zone
    corridor = ink_ds & (enc > 0) & (enc <= halfw)
    interior = corridor & ~border
    corridor_area = ((enc > 0) & (enc <= halfw) & page_ds).sum()
    margin_zone = ink_ds & (enc > halfw) & (enc <= halfw + 300)

    out = {
        "sheet": sheet,
        "street_id": street["street_id"],
        "half_street_width_px": halfw,
        "corridor_ink_px2": int(corridor.sum()) * ds * ds,
        "corridor_ink_fraction": float(corridor.sum() / max(1, corridor_area)),
        "corridor_border_zone_ink_px2": int((corridor & border).sum()) * ds * ds,
        "corridor_interior_ink_px2": int(interior.sum()) * ds * ds,
        "margin_zone_ink_px2": int(margin_zone.sum()) * ds * ds,
        "bands_interior_px2": {},
        "max_encroachment_px": 0.0,
        "max_encroachment_interior_px": 0.0,
        "deepest_interior_blob": None,
    }
    for b0, b1 in ((0, 40), (40, 120), (120, int(halfw))):
        sel = interior & (enc > b0) & (enc <= b1)
        out["bands_interior_px2"]["%d-%d" % (b0, b1)] = int(sel.sum()) * ds * ds

    if corridor.any():
        out["max_encroachment_px"] = float(enc[corridor].max())
    if interior.any():
        e = np.where(interior, enc, -np.inf)
        iy, ix = np.unravel_index(int(np.argmax(e)), e.shape)
        out["max_encroachment_interior_px"] = float(enc[iy, ix])
        lab, _ = ndimage.label(interior)
        blob = lab == lab[iy, ix]
        bys, bxs = np.where(blob)
        out["deepest_interior_blob"] = {
            "bbox_sheet_px": [int(bxs.min() * ds), int(bys.min() * ds),
                              int((bxs.max() + 1) * ds), int((bys.max() + 1) * ds)],
            "area_px2": int(blob.sum()) * ds * ds,
            "deepest_point_sheet_px": [float(fx[iy, ix]), float(fy[iy, ix])],
            "deepest_point_mosaic": [float(v) for v in
                                     sl.apply_raw(T, np.array([fx[iy, ix], fy[iy, ix]]))],
        }
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--transforms", default=sl.TRANSFORMS_JSON)
    ap.add_argument("--cuts", default=sl.CUTS_JSON)
    ap.add_argument("--masks", default=sl.MASKS_JSON)
    ap.add_argument("--downsample", type=int, default=4)
    ap.add_argument("--out", default=os.path.join(PROJECT, "60_master",
                                                  "content_extent_report.json"))
    args = ap.parse_args(argv)

    raw, _ = sl.load_transforms(args.transforms)
    with open(args.cuts) as f:
        cuts = json.load(f)
    with open(args.masks) as f:
        masks = json.load(f)
    inv_items, _ = sl.load_inventory()
    streets = {s["street_id"]: s for s in cuts["streets"]}
    ds = args.downsample

    bounding = {}
    for feat in masks["regions"]:
        sheet = int(feat["sheet"])
        for bc in feat["bounding_cuts"]:
            bounding.setdefault(sheet, set()).add(bc["street_id"])

    results = []
    for sheet in sorted(bounding):
        src = inv_items[sheet]["path"]
        grey = cv2.imread(src, cv2.IMREAD_GRAYSCALE)
        if grey is None:
            raise SystemExit("decode failure for sheet %d" % sheet)
        grey_ds = cv2.resize(grey, (grey.shape[1] // ds, grey.shape[0] // ds),
                             interpolation=cv2.INTER_AREA)
        del grey
        page_ds, ink_ds, t_ink = page_and_ink(grey_ds)
        edge_dist_ds = ndimage.distance_transform_edt(page_ds)
        for sid in sorted(bounding[sheet]):
            r = check_sheet_street(page_ds, ink_ds, edge_dist_ds, ds,
                                   raw[sheet], streets[sid], sheet)
            r["ink_threshold_effective"] = t_ink
            results.append(r)
            blob = r["deepest_interior_blob"]
            print("sheet %2d @ %-20s ink<%3.0f  max_enc %5.1f px (interior %5.1f)  "
                  "corridor ink %7d px2 (%4.1f%%, border-zone %d, interior %d)%s" % (
                      sheet, sid, t_ink, r["max_encroachment_px"],
                      r["max_encroachment_interior_px"], r["corridor_ink_px2"],
                      100 * r["corridor_ink_fraction"],
                      r["corridor_border_zone_ink_px2"],
                      r["corridor_interior_ink_px2"],
                      ("  deepest interior blob bbox %s area %d" %
                       (blob["bbox_sheet_px"], blob["area_px2"])) if blob else ""))

    worst = sorted(results, key=lambda r: -r["max_encroachment_interior_px"])[:5]
    out = {
        "generated_by": "60_master/tools/content_extent_check.py",
        "method": {
            "page_isolation": "largest connected component of grey>%d, holes filled "
                              "(F-001: naive thresholds read the dark scan backdrop "
                              "as ink)" % PAPER_MIN_GREY,
            "ink": "grey < per-page Otsu-within-page, clamped to [80, %d]. The "
                   "prescribed literal 'ink<%d' was validated first and REJECTED "
                   "for these LOC archival scans: paper tone is 150-190 grey, so "
                   "it classifies 84-99%% of the paper as ink (validated on sheets "
                   "7, 9, 44; Otsu-in-page lands 121-139, ink fractions 7-21%%, "
                   "building tints correctly included as drawn content)"
                   % (INK_MAX_GREY, INK_MAX_GREY),
            "border_zone": "ink within %d px of the page boundary reported "
                           "separately (neatline/margin furniture, discarded by the "
                           "ownership mask, not amputated cartography)" % BORDER_ZONE_PX,
            "downsample": ds,
            "corridor": "0..half-street-width past the cut toward the neighbour",
            "policy": "report only; never auto-fix",
        },
        "inputs": {
            "transforms_json": {"sha256": sl.sha256_file(args.transforms)},
            "cuts_json": {"sha256": sl.sha256_file(args.cuts)},
            "masks_json": {"sha256": sl.sha256_file(args.masks)},
        },
        "results": results,
        "worst_encroachments": [
            {"sheet": r["sheet"], "street_id": r["street_id"],
             "max_encroachment_interior_px": r["max_encroachment_interior_px"],
             "max_encroachment_px": r["max_encroachment_px"]} for r in worst],
    }
    sl.write_canonical_json(args.out, out)
    print("wrote %s" % args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
