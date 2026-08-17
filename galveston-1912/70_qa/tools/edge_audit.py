#!/usr/bin/env python
"""edge_audit.py — QA stage 5: paper-edge / scanner-surround audit.

The LOC scans sit on a dark gridded backdrop (F-001). Nothing of that backdrop,
and no physical page edge, may appear in the master; no ownership mask may
quietly include scanner surround as "content".

Checks:
  1. PAINT CONTAINMENT (native, strip-wise): every non-white master pixel must
     lie inside the warped ownership union. The renderer writes only owned
     pixels, so any non-white outside = corrupted provenance. Uses the same
     render-path warp of the ownership rasters (NEAREST, per-sheet x-window).
  2. OWNERSHIP INSIDE PAPER (vector): per sheet, area of (owned region minus
     page quad grown by 2 px) must be 0 — the mask never claims scanner
     surround. Also reports the margin between ownership and the page quad.
  3. PAGE-EDGE PROXIMITY (native sampling): along each sheet's page-quad
     boundary where it runs inside the canvas, sample the master in the owned
     zone just inside the edge; report dark (<110 mean) samples with canvas
     coordinates — paper-edge shadow / backdrop bleed shows up here.
  4. CANVAS BORDER: per 256-px segment of all four borders, dark-pixel
     fraction in an 8-px band (a backdrop band would be ~100 % dark; drawn
     ink at a trimmed edge is sparse). Segments > 30 % dark are flagged.

Artifacts: edge_audit.json (+ crops of the worst offenders). Report-only.
"""

import json
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import qalib
from qalib import RUN, sl

OUT_DIR = os.path.join(RUN, "edge_audit")
DARK_MEAN = 110.0
STRIP = 2000


def warp_own_strip(geo, sheet, own, y0, y1, W):
    """Ownership of `sheet` on canvas rows y0:y1 (render-path-exact)."""
    bx0, by0, bx1, by1 = geo["sheet_bbox"][sheet]
    if y1 <= by0 or y0 >= by1 or bx1 <= bx0:
        return None, None
    x0m, y0m = geo["mosaic_rect"][:2]
    M = sl.warp_matrix(geo["raw"][sheet], origin=(x0m, y0m), scale=geo["scale"])
    Ms = M.copy()
    Ms[0, 2] -= bx0
    Ms[1, 2] -= y0
    ownw = cv2.warpAffine(own, Ms, (bx1 - bx0, y1 - y0),
                          flags=cv2.INTER_NEAREST,
                          borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    return ownw, (bx0, bx1)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    qalib.verify_frozen_inputs()
    geo = qalib.load_geometry()
    master = qalib.master_array()
    W, H = geo["size"]
    x0m, y0m = geo["mosaic_rect"][:2]

    # --- check 2 (vector) -------------------------------------------------
    from shapely.geometry import Polygon
    from shapely.ops import unary_union
    vec = []
    for sheet in sorted(geo["raw"]):
        own_polys = [r["poly_mosaic"] for r in geo["regions"] if r["sheet"] == sheet]
        own_u = unary_union(own_polys)
        quad = Polygon(sl.apply_raw(geo["raw"][sheet], geo["quads"][sheet]))
        outside = own_u.difference(quad.buffer(2.0)).area
        margin = own_u.distance(quad.exterior) if not own_u.intersects(quad.exterior) \
            else 0.0
        vec.append({"sheet": sheet,
                    "ownership_outside_page_px2": round(float(outside), 1),
                    "ownership_touches_page_edge": bool(margin == 0.0)})
    print("check2 ownership-outside-page px2:",
          {v["sheet"]: v["ownership_outside_page_px2"] for v in vec})

    # --- checks 1 + 4 (native strip sweep) --------------------------------
    own_rasters = {s: qalib.sheet_own_raster(geo, s) for s in sorted(geo["raw"])}
    stray = []            # non-white outside ownership
    stray_count = 0
    border_segs = []
    band = 8
    for y0 in range(0, H, STRIP):
        y1 = min(y0 + STRIP, H)
        rows = np.asarray(master[y0:y1])
        nonwhite = (rows != 255).any(axis=2)
        ownu = np.zeros((y1 - y0, W), bool)
        for s, own in own_rasters.items():
            ownw, xs = warp_own_strip(geo, s, own, y0, y1, W)
            if ownw is not None:
                ownu[:, xs[0]:xs[1]] |= ownw > 0
        bad = nonwhite & ~ownu
        n = int(bad.sum())
        stray_count += n
        if n:
            ys, xs_ = np.where(bad)
            for k in range(0, min(n, 20)):
                stray.append({"canvas_xy": [int(xs_[k]), int(ys[k] + y0)],
                              "rgb": [int(v) for v in rows[ys[k], xs_[k]]]})
        # canvas left/right border bands (dark fraction per 256-px segment)
        grey = rows.mean(axis=2)
        for x0b, tag in ((0, "left"), (W - band, "right")):
            seg = grey[:, x0b:x0b + band] < DARK_MEAN
            for s0 in range(0, seg.shape[0], 256):
                frac = float(seg[s0:s0 + 256].mean())
                if frac > 0.0:
                    border_segs.append({"border": tag, "y0": int(y0 + s0),
                                        "dark_fraction": round(frac, 3)})
        if y0 == 0 or y1 == H:
            edge_rows = grey[:band] if y0 == 0 else grey[-band:]
            tag = "top" if y0 == 0 else "bottom"
            segd = edge_rows < DARK_MEAN
            for s0 in range(0, W, 256):
                frac = float(segd[:, s0:s0 + 256].mean())
                if frac > 0.0:
                    border_segs.append({"border": tag, "x0": int(s0),
                                        "dark_fraction": round(frac, 3)})
    flagged_border = [b for b in border_segs if b["dark_fraction"] > 0.30]
    print("check1 stray non-white outside ownership:", stray_count)
    print("check4 border segments >30%% dark: %d (of %d nonzero)" %
          (len(flagged_border), len(border_segs)))

    # --- check 3: sample master along page-quad boundaries ----------------
    edge_hits = []
    n_samples = 0
    for sheet in sorted(geo["raw"]):
        quad_m = sl.apply_raw(geo["raw"][sheet], geo["quads"][sheet])
        ring = np.vstack([quad_m, quad_m[:1]])
        from shapely.geometry import LineString
        from shapely.ops import unary_union as uu
        own_u = uu([r["poly_mosaic"] for r in geo["regions"] if r["sheet"] == sheet])
        L = LineString(ring)
        total = L.length
        step = 40.0
        t = 0.0
        while t < total:
            p = L.interpolate(t)
            t += step
            # sample 6 px INSIDE the page (toward centroid) in the owned zone
            c = own_u.centroid
            v = np.array([c.x - p.x, c.y - p.y])
            v /= max(np.linalg.norm(v), 1e-9)
            q = np.array([p.x, p.y]) + 6.0 * v
            from shapely.geometry import Point
            if not own_u.covers(Point(q[0], q[1])):
                continue
            cx, cy = geo["m2c"](q)
            xi, yi = int(round(cx)), int(round(cy))
            if not (0 <= xi < W and 0 <= yi < H):
                continue
            n_samples += 1
            px = np.asarray(master[yi, xi], float).mean()
            if px < DARK_MEAN:
                edge_hits.append({"sheet": sheet, "canvas_xy": [xi, yi],
                                  "mean_grey": round(px, 1)})
        # done sheet
    print("check3 page-edge-proximity samples:", n_samples,
          "dark hits:", len(edge_hits))

    # crops of the worst border segments + edge hits for visual confirmation
    crops = []
    worst = sorted(flagged_border, key=lambda b: -b["dark_fraction"])[:4]
    for i, b in enumerate(worst):
        if "y0" in b:
            cy = min(max(b["y0"] + 128, 300), H - 300)
            cx = 300 if b["border"] == "left" else W - 300
        else:
            cx = min(max(b["x0"] + 128, 300), W - 300)
            cy = 300 if b["border"] == "top" else H - 300
        crop = np.asarray(master[max(0, cy - 300):cy + 300,
                                 max(0, cx - 300):cx + 300])
        fn = "border_%s_%d.png" % (b["border"], i)
        qalib.save_png(os.path.join(OUT_DIR, fn), crop)
        crops.append(fn)
    for i, hset in enumerate(edge_hits[:6]):
        xi, yi = hset["canvas_xy"]
        crop = np.asarray(master[max(0, yi - 250):yi + 250,
                                 max(0, xi - 250):xi + 250])
        fn = "edgehit_s%d_%d.png" % (hset["sheet"], i)
        qalib.save_png(os.path.join(OUT_DIR, fn), crop)
        crops.append(fn)

    out = {
        "stamp": qalib.stamp("70_qa/tools/edge_audit.py"),
        "check1_paint_containment": {
            "stray_nonwhite_px_outside_ownership": stray_count,
            "examples": stray[:20],
            "verdict": "PASS" if stray_count == 0 else "FAIL"},
        "check2_ownership_inside_paper": {
            "per_sheet": vec,
            "verdict": "PASS" if all(v["ownership_outside_page_px2"] == 0
                                     for v in vec) else "FAIL"},
        "check3_page_edge_proximity": {
            "n_samples": n_samples, "dark_hits": edge_hits,
            "verdict": "PASS" if not edge_hits else "REVIEW"},
        "check4_canvas_border": {
            "segments_nonzero_dark": len(border_segs),
            "segments_over_30pct": flagged_border,
            "verdict": "PASS" if not flagged_border else "REVIEW"},
        "crops": crops,
    }
    qalib.write_json(os.path.join(RUN, "edge_audit.json"), out)
    print("wrote edge_audit.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
