#!/usr/bin/env python
"""junction_panels.py — QA stage 3: 4-sheet junction + outer-corner panels.

The six interior 4-sheet junctions (both Ave I/Sealy junctions FIRST, per the
QA plan), plus the four outer corners of the rendered footprint. Per junction:
  * merged master crop (the real bytes) from ONE integer rect,
  * annotated copy (both cut polylines dashed, sheet ids in their quadrants),
  * 2x2 registered montage of the four contributing plates warped WITHOUT
    ownership masking (what each plate draws at the junction),
  * numeric checks: unowned pixels inside the rect, non-white master pixels in
    unowned areas (must be none away from the canvas edge), per-quadrant owner.

Visual verdicts are recorded by the reviewer into junction_verdicts.json and
folded into the QA report. Report-only; writes nothing outside 70_qa/run1.
"""

import json
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import qalib
from qalib import RUN, sl
from seam_panels import clamp_rect

OUT_DIR = os.path.join(RUN, "junction_panels")

JUNCTIONS = [
    # (id, horizontal street, vertical street, [sheets]) — Sealy pair first
    ("J_21st_x_sealy", "21st_or_center_st", "ave_i_or_sealy", [39, 40, 43, 44]),
    ("J_24th_x_sealy", "24th_st", "ave_i_or_sealy", [43, 44, 49, 50]),
    ("J_21st_x_aveC", "21st_or_center_st", "ave_c_or_mechanic", [7, 8, 9, 10]),
    ("J_21st_x_aveF", "21st_or_center_st", "ave_f_or_church", [8, 39, 10, 43]),
    ("J_24th_x_aveC", "24th_st", "ave_c_or_mechanic", [9, 10, 11, 12]),
    ("J_24th_x_aveF", "24th_st", "ave_f_or_church", [10, 43, 12, 49]),
]

RECT_WH = 1800
CORNER_WH = 1600


def junction_point(geo, h_street, v_street):
    from shapely.geometry import LineString
    ph = LineString(geo["streets"][h_street]["polyline_mosaic"])
    pv = LineString(geo["streets"][v_street]["polyline_mosaic"])
    p = ph.intersection(pv)
    if p.is_empty:
        raise SystemExit("streets %s x %s do not intersect" % (h_street, v_street))
    if p.geom_type != "Point":
        p = p.centroid
    return np.array([p.x, p.y])


def rect_masks(geo, rect, sheets):
    """Per-sheet warped ownership bools inside rect (render-path-exact)."""
    out = {}
    for s in sheets:
        own = qalib.sheet_own_raster(geo, s)
        item = geo["inventory"][s]
        # ownership warp only (no image needed): reuse warp_window with a
        # dummy white image to avoid decoding the plate twice
        dummy = np.full((item["height"], item["width"], 3), 255, np.uint8)
        _, ownw = qalib.warp_window(geo, s, rect, img=dummy, own=own)
        out[s] = ownw
    return out


def draw_cuts(img, geo, rect, street_ids, labels):
    out = img.copy()
    rx, ry, rw, rh = rect
    for sid in street_ids:
        pts_m = np.asarray(geo["streets"][sid]["polyline_mosaic"], float)
        dense = []
        for p, q in zip(pts_m[:-1], pts_m[1:]):
            seg = np.linspace(p, q, max(2, int(np.hypot(*(q - p)) // 8)))
            dense.append(seg)
        cpts = geo["m2c"](np.concatenate(dense)) - [rx, ry]
        ins = ((cpts[:, 0] >= 0) & (cpts[:, 0] < rw) &
               (cpts[:, 1] >= 0) & (cpts[:, 1] < rh))
        for i, (x, y) in enumerate(cpts[ins]):
            if (i // 5) % 2 == 0:
                cv2.circle(out, (int(x), int(y)), 2, (255, 0, 0), -1)
    for txt, (x, y) in labels:
        cv2.putText(out, txt, (int(x), int(y)), cv2.FONT_HERSHEY_SIMPLEX,
                    1.5, (255, 0, 0), 3, cv2.LINE_AA)
    return out


def montage(panels, scale=0.5):
    keys = sorted(panels)
    ims = []
    for k in keys:
        im = panels[k]
        im = cv2.resize(im, (0, 0), fx=scale, fy=scale,
                        interpolation=cv2.INTER_AREA)
        im = im.copy()
        cv2.putText(im, "sheet %s ONLY" % k, (14, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.1, (255, 0, 0), 2, cv2.LINE_AA)
        ims.append(im)
    h, w = ims[0].shape[:2]
    sep_v = np.full((h, 6, 3), 30, np.uint8)
    sep_h = np.full((6, w * 2 + 6, 3), 30, np.uint8)
    top = np.hstack([ims[0], sep_v, ims[1]])
    bot = np.hstack([ims[2], sep_v, ims[3]]) if len(ims) >= 4 else None
    return np.vstack([top, sep_h, bot]) if bot is not None else top


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    qalib.verify_frozen_inputs()
    geo = qalib.load_geometry()
    master = qalib.master_array()
    W, H = geo["size"]
    msha = qalib.master_sha256()
    sha16 = msha[:16]

    entries = []

    for jid, hs, vs, sheets in JUNCTIONS:
        pm = junction_point(geo, hs, vs)
        c = geo["m2c"](pm)
        rect = clamp_rect((int(round(c[0])) - RECT_WH // 2,
                           int(round(c[1])) - RECT_WH // 2,
                           RECT_WH, RECT_WH), W, H)
        rx, ry, rw, rh = rect
        crop = np.asarray(master[ry:ry + rh, rx:rx + rw])

        masks = rect_masks(geo, rect, sheets)
        owncount = np.zeros((rh, rw), np.int16)
        for s in sheets:
            owncount += masks[s].astype(np.int16)
        unowned = owncount == 0
        # master must be pure white wherever no sheet owns (render invariant)
        nonwhite_unowned = int(((crop != 255).any(axis=2) & unowned).sum())
        # holes: unowned pixels well inside the junction core (300 px radius)
        yy, xx = np.mgrid[0:rh, 0:rw]
        core = (np.hypot(xx - (c[0] - rx), yy - (c[1] - ry)) < 300)
        core_unowned = int((core & unowned).sum())

        # sheet-only panels (registered, same rect)
        panels = {}
        for s in sheets:
            img = qalib._load_sheet_bgr(geo, s)
            rgb, _ = qalib.warp_window(geo, s, rect, img=img, own=None)
            panels[s] = rgb
            del img
        labels = []
        for s in sheets:
            ys, xs = np.where(masks[s])
            if len(xs):
                labels.append(("s%d" % s, (np.median(xs), np.median(ys))))
        annot = draw_cuts(crop, geo, rect, [hs, vs], labels)

        hdr1 = qalib.label_bar(rw, ["%s  merged (master bytes)  rect=%s" %
                                    (jid, list(rect)),
                                    "master sha256 %s...  sheets %s" %
                                    (sha16, sheets)])
        qalib.save_png(os.path.join(OUT_DIR, "%s_merged.png" % jid),
                       np.vstack([hdr1, crop]))
        hdr2 = qalib.label_bar(rw, ["%s  merged + cuts overlay (REVIEW AID)" % jid,
                                    "master sha256 %s..." % sha16])
        qalib.save_png(os.path.join(OUT_DIR, "%s_annot.png" % jid),
                       np.vstack([hdr2, annot]))
        mon = montage(panels)
        hdr3 = qalib.label_bar(mon.shape[1],
                               ["%s  four plates WITHOUT ownership (0.5x)" % jid,
                                "master sha256 %s...  rect=%s" % (sha16, list(rect))])
        qalib.save_png(os.path.join(OUT_DIR, "%s_plates.png" % jid),
                       np.vstack([hdr3, mon]))

        entries.append({
            "id": jid, "type": "interior-junction",
            "streets": [hs, vs], "sheets": sheets,
            "junction_mosaic": [round(float(pm[0]), 1), round(float(pm[1]), 1)],
            "rect_canvas": list(rect),
            "unowned_px_in_rect": int(unowned.sum()),
            "unowned_px_in_300px_core": core_unowned,
            "nonwhite_master_px_in_unowned": nonwhite_unowned,
            "max_own_multiplicity": int(owncount.max()),
        })
        print("%s rect=%s core_unowned=%d nonwhite_unowned=%d maxmult=%d" %
              (jid, list(rect), core_unowned, nonwhite_unowned, int(owncount.max())))

    # outer corners of the rendered footprint (owned-union corners in canvas)
    from shapely.ops import unary_union
    U = unary_union([r["poly_mosaic"] for r in geo["regions"]])
    ux0, uy0, ux1, uy1 = U.bounds
    x0m, y0m, x1m, y1m = geo["mosaic_rect"]
    # clip to canvas
    cx0, cy0 = geo["m2c"]((max(ux0, x0m), max(uy0, y0m)))
    cx1, cy1 = geo["m2c"]((min(ux1, x1m), min(uy1, y1m)))
    corners = [
        ("C_NW", (cx0, cy0)), ("C_NE", (cx1, cy0)),
        ("C_SW", (cx0, cy1)), ("C_SE", (cx1, cy1)),
    ]
    for cid, (px, py) in corners:
        rect = clamp_rect((int(round(px)) - CORNER_WH // 2,
                           int(round(py)) - CORNER_WH // 2,
                           CORNER_WH, CORNER_WH), W, H)
        rx, ry, rw, rh = rect
        crop = np.asarray(master[ry:ry + rh, rx:rx + rw])
        dark = (np.asarray(crop, np.int32).sum(axis=2) < 240)  # near-black
        hdr = qalib.label_bar(rw, ["%s  outer corner (master bytes)  rect=%s" %
                                   (cid, list(rect)),
                                   "master sha256 %s...  dark(<80/ch avg) px=%d" %
                                   (sha16, int(dark.sum()))])
        qalib.save_png(os.path.join(OUT_DIR, "%s.png" % cid),
                       np.vstack([hdr, crop]))
        entries.append({"id": cid, "type": "outer-corner",
                        "rect_canvas": list(rect),
                        "near_black_px": int(dark.sum())})
        print("%s rect=%s near_black=%d" % (cid, list(rect), int(dark.sum())))

    meta = {"stamp": qalib.stamp("70_qa/tools/junction_panels.py"),
            "entries": entries}
    qalib.write_json(os.path.join(RUN, "junction_panels_meta.json"), meta)
    print("wrote junction_panels_meta.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
