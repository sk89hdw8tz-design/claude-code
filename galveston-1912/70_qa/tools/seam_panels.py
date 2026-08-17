#!/usr/bin/env python
"""seam_panels.py — QA stage 2: native-resolution seam panels.

Per seam: A-only / B-only / merged, all three cut from ONE precomputed INTEGER
rectangle in the canvas frame (canvas px == mosaic px re-origined at the final
scale 1.0). The rectangle is computed once, stored in the artifact metadata,
and shared by all three images. Merged = the actual master bytes. A/B-only =
render-path-exact warps of each full plate (no ownership masking), so the
reviewer sees what each plate draws across the seam.

Guards (QA_PLAN tool-validation gates):
  * self-test on a synthetic checker mosaic BEFORE any real panel: renders a
    synthetic master through the renderer's exact strip path, then asserts the
    panel path reproduces it BYTE-EXACTLY on owned pixels from a clamped
    integer rectangle, and that a float rectangle is refused
    (float-truncation / crop-clamping failure classes).
  * On the real master the same byte-exact assertion runs per seam per side;
    any nonzero mismatch on owned pixels is recorded and fails the panel.
  * Every panel PNG carries a header bar with the seam id, rect, and the
    master's sha256; the same data is in seam_panels_meta.json.

Report-only; nothing outside 70_qa/run1 is written.
"""

import json
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import qalib
from qalib import RUN, sl

PANEL_DIR = os.path.join(RUN, "seam_panels")


# ---------------------------------------------------------------------------
# synthetic self-test

def _synth_sheet(w, h, tint, seed):
    rng = np.random.default_rng(seed)
    img = np.full((h, w, 3), 235, np.uint8)
    yy, xx = np.mgrid[0:h, 0:w]
    checker = ((xx // 50 + yy // 50) % 2).astype(bool)
    img[checker] = tint
    img ^= rng.integers(0, 24, img.shape).astype(np.uint8)  # break flat areas
    return img


def _render_synth_master(sheets, W, H, strip_h=256):
    """Replicates render_master.py's compositing loop (strip path, x-window)."""
    canvas = np.full((H, W, 3), 255, np.uint8)
    bboxes = {}
    for sid in sorted(sheets):
        s = sheets[sid]
        img, own, T = s["img"], s["own"], s["T"]
        M = sl.warp_matrix(T, origin=(0.0, 0.0), scale=1.0)
        h, w = img.shape[:2]
        quad = np.asarray([[0, 0], [w, 0], [w, h], [0, h]], float)
        qc = (M[:, :2] @ quad.T).T + M[:, 2]
        bx0 = max(0, int(np.floor(qc[:, 0].min())))
        bx1 = min(W, int(np.ceil(qc[:, 0].max())) + 1)
        by0 = max(0, int(np.floor(qc[:, 1].min())))
        by1 = min(H, int(np.ceil(qc[:, 1].max())) + 1)
        bboxes[sid] = [bx0, by0, bx1, by1]
        for y0 in range(by0 - by0 % strip_h, by1, strip_h):
            sy0, sy1 = max(y0, 0), min(y0 + strip_h, H)
            if sy1 <= max(by0, 0):
                continue
            ww, hh = bx1 - bx0, sy1 - sy0
            Ms = M.copy()
            Ms[0, 2] -= bx0
            Ms[1, 2] -= sy0
            warped = cv2.warpAffine(img, Ms, (ww, hh), flags=cv2.INTER_LANCZOS4,
                                    borderMode=cv2.BORDER_CONSTANT,
                                    borderValue=(255, 255, 255))
            ownw = cv2.warpAffine(own, Ms, (ww, hh), flags=cv2.INTER_NEAREST,
                                  borderMode=cv2.BORDER_CONSTANT, borderValue=0)
            sel = ownw > 0
            if sel.any():
                roi = canvas[sy0:sy1, bx0:bx1]
                roi[sel] = warped[sel]
    return canvas, bboxes


def self_test():
    W, H = 2000, 1300
    a_img = _synth_sheet(1400, 1200, (200, 120, 120), 1)
    b_img = _synth_sheet(1400, 1200, (120, 130, 210), 2)
    Ta = {"a": 1.0003, "b": 0.0082, "tx": -40.5, "ty": 30.25}
    Tb = {"a": 0.9991, "b": -0.0046, "tx": 890.75, "ty": 42.5}
    # ownership: cut with a jog around x~1030 canvas
    a_own = np.zeros((1200, 1400), np.uint8)
    cv2.fillPoly(a_own, [np.array([[30, 40], [1060, 30], [1000, 600],
                                   [1060, 1160], [40, 1170]], np.int32)], 255)
    b_own = np.zeros((1200, 1400), np.uint8)
    cv2.fillPoly(b_own, [np.array([[175, 20], [1370, 25], [1360, 1180],
                                   [180, 1150], [120, 580]], np.int32)], 255)
    sheets = {1: {"img": a_img, "own": a_own, "T": Ta},
              2: {"img": b_img, "own": b_own, "T": Tb}}
    master, bboxes = _render_synth_master(sheets, W, H)
    geo = {"mosaic_rect": (0.0, 0.0, float(W), float(H)), "scale": 1.0,
           "raw": {1: Ta, 2: Tb},
           "sheet_bbox": {k: v for k, v in bboxes.items()}}

    # rect deliberately overhanging the canvas edge -> clamp, keep integers
    want = (880, -60, 2200, 700)
    rect = clamp_rect(want, W, H)
    assert all(isinstance(v, int) for v in rect), "clamped rect must be int"
    assert rect[1] == 0 and rect[0] + rect[2] <= W, "clamp failed"

    a_rgb, a_ownw = qalib.warp_window(geo, 1, rect, img=a_img[..., ::-1].copy(),
                                      own=a_own)
    b_rgb, b_ownw = qalib.warp_window(geo, 2, rect, img=b_img[..., ::-1].copy(),
                                      own=b_own)
    rx, ry, rw, rh = rect
    crop = master[ry:ry + rh, rx:rx + rw]
    # ownership in the master: recompute the same way the renderer did
    assert a_ownw.any() and b_ownw.any(), "self-test rect must straddle the cut"
    assert not (a_ownw & b_ownw).any(), "synthetic ownerships overlap in rect"
    da = (crop != a_rgb)[a_ownw]
    db = (crop != b_rgb)[b_ownw & ~a_ownw]
    assert not da.any(), "A-owned pixels differ from master: %d" % da.sum()
    assert not db.any(), "B-owned pixels differ from master: %d" % db.sum()
    merged = np.full((rh, rw, 3), 255, np.uint8)
    merged[b_ownw] = b_rgb[b_ownw]
    merged[a_ownw] = a_rgb[a_ownw]   # same order as render: sheet 1 after 2? no —
    # render order is ascending sheet id, later sheets overwrite; replicate:
    merged = np.full((rh, rw, 3), 255, np.uint8)
    merged[a_ownw] = a_rgb[a_ownw]
    merged[b_ownw] = b_rgb[b_ownw]
    both = a_ownw | b_ownw
    assert np.array_equal(merged[both], crop[both]), "recomposed merged != master"
    # float rect must be refused
    try:
        qalib.warp_window(geo, 1, (880.5, 0, 2200, 700),
                          img=a_img[..., ::-1].copy(), own=a_own)
        raise AssertionError("float rect was not refused")
    except ValueError:
        pass
    # shapes match the stored rect
    for im in (a_rgb, b_rgb, merged, crop):
        assert im.shape[:2] == (rh, rw), "image shape != stored rect"
    return {"synthetic_canvas": [W, H], "rect_requested": list(want),
            "rect_clamped": list(rect),
            "checks": ["clamped-int-rect", "A-owned byte-exact",
                       "B-owned byte-exact", "recomposed==master",
                       "float-rect refused", "shapes==rect"],
            "result": "PASS"}


def clamp_rect(rect, W, H):
    """Slide the rect fully inside the canvas, preserving its size (shrink
    only if the canvas itself is smaller — the crop-clamping failure class is
    a rect that silently changes size for one image but not another)."""
    rx, ry, rw, rh = (int(round(v)) for v in rect)
    rw, rh = min(rw, W), min(rh, H)
    rx = max(0, min(rx, W - rw))
    ry = max(0, min(ry, H - rh))
    return (rx, ry, rw, rh)


# ---------------------------------------------------------------------------
# real panels

def panel_rects(matrix, geo):
    """ONE integer rect per seam, centred on the seam's mid-anchor."""
    W, H = geo["size"]
    rects = {}
    for row in matrix["rows"]:
        sid = row["street_id"]
        street = geo["streets"][sid]
        horiz = street["orientation"] == "horizontal"
        anch = row.get("mid_anchor")
        rw, rh = (2200, 1500) if horiz else (1500, 2200)
        # centre on the mid-anchor unless it sits at/off the canvas edge, in
        # which case use the canvas-visible seam midpoint
        centre_m = None
        if anch:
            c = geo["m2c"](np.asarray(anch["midpoint_mosaic"], float))
            margin = 0.45 * min(rw, rh)
            if (margin <= c[0] <= W - margin) and (margin <= c[1] <= H - margin):
                centre_m = anch["midpoint_mosaic"]
        if centre_m is None:
            centre_m = row["seam_mid_mosaic"]
        c = geo["m2c"](np.asarray(centre_m, float))
        rect = clamp_rect((int(round(c[0] - rw / 2)), int(round(c[1] - rh / 2)),
                           rw, rh), W, H)
        rects[row["seam"]] = {"rect": list(rect),
                              "centre_mosaic": [float(centre_m[0]), float(centre_m[1])],
                              "anchor": anch["anchor"] if anch else "(seam midpoint)",
                              "orientation": street["orientation"]}
    return rects


def draw_cut_overlay(img_rgb, geo, row, rect):
    """Merged panel + dashed cut polyline + side labels (review aid only)."""
    out = img_rgb.copy()
    rx, ry, rw, rh = rect
    street = geo["streets"][row["street_id"]]
    pts_m = np.asarray(street["polyline_mosaic"], float)
    # densify the polyline, map to canvas, draw dashes inside the rect
    dense = []
    for p, q in zip(pts_m[:-1], pts_m[1:]):
        seg = np.linspace(p, q, max(2, int(np.hypot(*(q - p)) // 8)))
        dense.append(seg)
    dense = np.concatenate(dense)
    cpts = geo["m2c"](dense) - [rx, ry]
    inside = ((cpts[:, 0] >= 0) & (cpts[:, 0] < rw) &
              (cpts[:, 1] >= 0) & (cpts[:, 1] < rh))
    for i, (x, y) in enumerate(cpts[inside]):
        if (i // 5) % 2 == 0:
            cv2.circle(out, (int(x), int(y)), 2, (255, 0, 0), -1)
    a, b = row["pair"]
    sgn_a = street["sheet_side_sign"][str(a)]
    n = np.asarray(street["line_fit"]["normal"])
    centre = np.asarray([rw / 2, rh / 2])
    for sheet, sgn in ((a, sgn_a), (b, -sgn_a)):
        pos = centre + sgn * n * (min(rw, rh) * 0.33)
        cv2.putText(out, "s%d" % sheet, (int(pos[0]), int(pos[1])),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.6, (255, 0, 0), 3, cv2.LINE_AA)
    return out


def main():
    os.makedirs(PANEL_DIR, exist_ok=True)
    man, fz, checks = qalib.verify_frozen_inputs()

    st = self_test()
    print("self-test:", st["result"], "-", ", ".join(st["checks"]))

    geo = qalib.load_geometry()
    with open(os.path.join(RUN, "seam_matrix.json")) as f:
        matrix = json.load(f)
    msha = qalib.master_sha256()
    if matrix["stamp"]["master_sha256"] != msha:
        raise SystemExit("seam_matrix.json is stale (different master sha)")
    master = qalib.master_array()

    rects = panel_rects(matrix, geo)
    rows_by_seam = {r["seam"]: r for r in matrix["rows"]}

    # group work by sheet so each plate is decoded once
    need = {}
    for seam, info in rects.items():
        a, b = rows_by_seam[seam]["pair"]
        need.setdefault(a, []).append((seam, "A"))
        need.setdefault(b, []).append((seam, "B"))

    panels = {}
    for sheet in sorted(need):
        print("warping sheet %d (%d panels)..." % (sheet, len(need[sheet])))
        img = qalib._load_sheet_bgr(geo, sheet)
        own = qalib.sheet_own_raster(geo, sheet)
        for seam, role in need[sheet]:
            rect = tuple(rects[seam]["rect"])
            rgb, ownw = qalib.warp_window(geo, sheet, rect, img=img, own=own)
            panels.setdefault(seam, {})[role] = (rgb, ownw)
        del img, own

    meta = {"stamp": qalib.stamp("70_qa/tools/seam_panels.py",
                                 {"self_test": st}),
            "seams": {}}
    for seam, info in sorted(rects.items()):
        row = rows_by_seam[seam]
        rect = tuple(info["rect"])
        rx, ry, rw, rh = rect
        crop = np.asarray(master[ry:ry + rh, rx:rx + rw])
        (a_rgb, a_own) = panels[seam]["A"]
        (b_rgb, b_own) = panels[seam]["B"]
        # byte-exact guard against the real master. The renderer composites
        # sheets in ascending id order, so at raster boundary pixels claimed by
        # BOTH ownership rasters (fillPoly includes the 1-px cut line in each)
        # the higher sheet id wins. Mirror that: A-owned = a_own & ~b_own.
        a, b = row["pair"]
        assert a < b, "pair ordering assumption broken"
        overlap_px = int((a_own & b_own).sum())
        mis_a = int((crop != a_rgb)[a_own & ~b_own].sum())
        mis_b = int((crop != b_rgb)[b_own].sum())
        unowned = ~(a_own | b_own)
        reg_ok = (mis_a == 0 and mis_b == 0)

        sha16 = msha[:16]
        base = seam.replace("-", "_")
        for tag, im in (("A", a_rgb), ("B", b_rgb), ("merged", crop)):
            hdr = qalib.label_bar(rw, ["seam %s  %s-only%s  rect=%s" % (
                seam, tag, "" if tag != "merged" else " (master bytes)",
                list(rect)),
                "master sha256 %s...  anchor: %s" % (sha16, info["anchor"])])
            qalib.save_png(os.path.join(PANEL_DIR, "seam_%s_%s.png" % (base, tag)),
                           np.vstack([hdr, im]))
        annot = draw_cut_overlay(crop, geo, row, rect)
        hdr = qalib.label_bar(rw, ["seam %s  merged+cut overlay (REVIEW AID)  "
                                   "rect=%s" % (seam, list(rect)),
                                   "master sha256 %s...  A=s%d B=s%d" %
                                   (sha16, row["pair"][0], row["pair"][1])])
        qalib.save_png(os.path.join(PANEL_DIR, "seam_%s_annot.png" % base),
                       np.vstack([hdr, annot]))

        meta["seams"][seam] = {
            "rect_canvas": list(rect), "anchor": info["anchor"],
            "centre_mosaic": info["centre_mosaic"],
            "registration": {
                "A_owned_mismatch_px": mis_a, "B_owned_mismatch_px": mis_b,
                "AB_ownership_overlap_px": overlap_px,
                "unowned_px_in_rect": int(unowned.sum()),
                "byte_exact_vs_master": reg_ok},
            "files": ["seam_%s_A.png" % base, "seam_%s_B.png" % base,
                      "seam_%s_merged.png" % base, "seam_%s_annot.png" % base],
        }
        print("  %-6s rect=%s  misA=%d misB=%d ovl=%d unowned=%d  %s" % (
            seam, list(rect), mis_a, mis_b, overlap_px, int(unowned.sum()),
            "BYTE-EXACT" if reg_ok else "MISMATCH"))

    qalib.write_json(os.path.join(RUN, "seam_panels_meta.json"), meta)
    print("wrote seam_panels_meta.json + %d panel sets" % len(rects))
    return 0


if __name__ == "__main__":
    sys.exit(main())
