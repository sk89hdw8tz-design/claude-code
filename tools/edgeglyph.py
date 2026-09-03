#!/usr/bin/env python3
"""Detect adjoining-sheet numerals and compass roses as furniture candidates.

    python3 tools/edgeglyph.py --year 1912 [--out PATH] [--crops DIR]

DETECTOR ONLY -- never writes units.json. On the tools/scalebar.py pattern:
one clean crop of the series' compass rose (from plate 19, where a full
rose stands isolated in the Seawall Blvd roadway) and one crop per digit of
the large adjoining-sheet numeral face (from plates 10/12/31/40, where the
numeral already sits in units.json as a confirmed `edge numeral/glyph` box)
template-match every plate's native scan. Digit hits are grouped into runs
(a multi-digit numeral), each run's box is fit to ink and clipped to the
hit footprint + 30 px, then gated:

  - glyph height >= MIN_HEIGHT native px
  - box centre within MAX_NEATLINE_DIST px of the neatline (`extent` vs
    the wider `extent_scan`; a numeral/rose sits in the margin the two
    disagree on)
  - box in a roadway: `plates/lattice.json` records each plate's block
    faces on both axes; a box is rejected if it falls inside a face
    interval on BOTH axes at once (i.e. over a platted block, not a
    street) -- and rejected outright if the plate has no lattice, since
    the roadway gate cannot be checked
  - darkest row of the fitted box carries 0.7-0.95 ink (a solid printed
    glyph, not a stray mark or a filled black disc)

Every surviving candidate gets a native crop for adjudication; nothing is
written to the recipe. False negatives are fine here -- an opus adjudicator
names each candidate before anything is ever written, so the templates
above (six confirmed digits, one rose) are deliberately not the full
digit set; unmatched digits (3679 not covered by 0,1,2,4,5,8) simply do
not fire.
"""
import argparse
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
REPO = os.path.dirname(HERE)

# ---- templates: (unit, native box [x0,y0,x1,y1]) -----------------------
# The rose: an isolated, unclipped compass rose in plate 19's Seawall Blvd
# margin (qc/periphery/review_round2.json edge_00 finding), disc + starburst
# only -- the tail lengths vary plate to plate so they are not templated.
ROSE_TPL = ("19", (850, 170, 1120, 380))

# Digits: cropped from the four plates whose numeral is already a confirmed
# `edge numeral/glyph` box in units.json (10 -> "8", 12 -> "10", 31 -> "25",
# 40 -> "44"), split to one glyph each by column/row ink-gap profiling.
DIGIT_TPL = {
    "0": ("12", (1682, 65, 1752, 190)),
    "2": ("31", (1550, 75, 1633, 150)),
    "4": ("40", (1665, 3736, 1715, 3836)),
    "5": ("31", (1646, 75, 1730, 150)),
    "8": ("10", (1703, 43, 1813, 162)),
}
# "1" (unit 12) is dropped: it is a bare thin vertical stroke and, tested,
# matches almost any dark vertical line on a plate (lot-number tick marks,
# border rules, dashes) at scores overlapping genuine hits -- the single
# largest false-positive source. Numerals containing a "1" simply do not
# fire; false negatives are accepted, false positives are not.

ROSE_THRESH = 0.50
DIGIT_THRESH = 0.62
MIN_HEIGHT = 60          # gate: glyph height >= 60 native px
MAX_NEATLINE_DIST = 400  # gate: box centre within 400 px of the neatline
DARK_LO, DARK_HI = 0.70, 0.95   # gate: darkest row ink fraction
INK = 120                # grey level below which a pixel counts as ink
RUN_Y_TOL = 45            # px: same baseline
RUN_X_GAP = 90            # px: max gap between adjacent glyphs in a run
FIT_PAD = 30              # px: fit box may not exceed hit footprint + this
NMS_IOU = 0.3


def iou(a, b):
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    ix0, iy0 = max(ax0, bx0), max(ay0, by0)
    ix1, iy1 = min(ax1, bx1), min(ay1, by1)
    iw, ih = max(0, ix1 - ix0), max(0, iy1 - iy0)
    inter = iw * ih
    if inter <= 0:
        return 0.0
    ua = (ax1 - ax0) * (ay1 - ay0) + (bx1 - bx0) * (by1 - by0) - inter
    return inter / ua if ua > 0 else 0.0


def match_hits(img, tpl, thresh):
    """[(score, x0, y0, x1, y1)] local maxima of tpl in img above thresh,
    greedily non-max-suppressed against the template's own footprint."""
    import cv2
    th, tw = tpl.shape
    if img.shape[0] < th or img.shape[1] < tw:
        return []
    res = cv2.matchTemplate(img, tpl, cv2.TM_CCOEFF_NORMED)
    ys, xs = np.where(res >= thresh)
    cand = sorted(((float(res[y, x]), x, y) for y, x in zip(ys, xs)), reverse=True)
    kept = []
    for s, x, y in cand:
        box = (x, y, x + tw, y + th)
        if any(iou(box, k[1]) > NMS_IOU for k in kept):
            continue
        kept.append((s, box))
    return [(s, *b) for s, b in kept]


def group_runs(hits):
    """hits: [(score, x0, y0, x1, y1, digit)] -> list of runs, each a list
    of hits on the same baseline within RUN_X_GAP of each other."""
    hits = sorted(hits, key=lambda h: h[1])
    used = [False] * len(hits)
    runs = []
    for i, h in enumerate(hits):
        if used[i]:
            continue
        run = [h]
        used[i] = True
        cy = (h[2] + h[4]) / 2
        cx1 = h[3]
        changed = True
        while changed:
            changed = False
            for j, h2 in enumerate(hits):
                if used[j]:
                    continue
                cy2 = (h2[2] + h2[4]) / 2
                if abs(cy2 - cy) > RUN_Y_TOL:
                    continue
                if h2[1] < cx1 - 5 or h2[1] - cx1 > RUN_X_GAP:
                    continue
                run.append(h2)
                used[j] = True
                cx1 = max(cx1, h2[3])
                cy = sum((r[2] + r[4]) / 2 for r in run) / len(run)
                changed = True
        runs.append(run)
    return runs


def neatline_dist(cx, cy, extent):
    ex0, ey0, ex1, ey1 = extent
    dx = max(ex0 - cx, 0, cx - ex1)
    dy = max(ey0 - cy, 0, cy - ey1)
    if dx == 0 and dy == 0:
        return min(cx - ex0, ex1 - cx, cy - ey0, ey1 - cy)
    return float(np.hypot(dx, dy))


def in_roadway(box, lat):
    """True if box does NOT sit inside a block cell (a face interval on
    both axes at once). lat is the unit's plates/lattice.json entry, or
    None if the plate has no lattice -- callers must reject that case."""
    if lat is None:
        return False
    x0, y0, x1, y1 = box
    xf = (lat.get("x") or {}).get("faces") or []
    yf = (lat.get("y") or {}).get("faces") or []

    def hits(faces, lo, hi):
        return any(not (hi < f[0] or lo > f[1]) for f in faces)

    on_x_face = hits(xf, x0, x1)
    on_y_face = hits(yf, y0, y1)
    return not (on_x_face and on_y_face)


def ink_fit(gray, seed_box, allow_box):
    """Tighten seed_box to the bbox of dark pixels inside allow_box."""
    ax0, ay0, ax1, ay1 = allow_box
    ax0, ay0 = max(0, ax0), max(0, ay0)
    ax1, ay1 = min(gray.shape[1], ax1), min(gray.shape[0], ay1)
    sub = gray[ay0:ay1, ax0:ax1]
    if sub.size == 0:
        return seed_box
    dark = sub < INK
    if not dark.any():
        return seed_box
    ys, xs = np.where(dark)
    x0, x1 = ax0 + int(xs.min()), ax0 + int(xs.max()) + 1
    y0, y1 = ay0 + int(ys.min()), ay0 + int(ys.max()) + 1
    return (x0, y0, x1, y1)


def darkest_row_frac(gray, box):
    x0, y0, x1, y1 = box
    sub = gray[max(0, y0):y1, max(0, x0):x1]
    if sub.size == 0:
        return 0.0
    dark = sub < INK
    if sub.shape[1] == 0:
        return 0.0
    rowfrac = dark.sum(axis=1) / sub.shape[1]
    return float(rowfrac.max()) if rowfrac.size else 0.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", type=int, default=1912)
    ap.add_argument("--out", default=os.path.join(
        "/tmp/claude-0/-home-user-claude-code/667180c2-8c6a-5c7c-8f63-764f5714e1d7",
        "scratchpad", "edgeglyph_candidates.json"))
    ap.add_argument("--crops", default=os.path.join(
        "/tmp/claude-0/-home-user-claude-code/667180c2-8c6a-5c7c-8f63-764f5714e1d7",
        "scratchpad", "edgeglyph_crops"))
    ap.add_argument("--units", nargs="*", default=None)
    a = ap.parse_args()
    import cv2
    from reciplib import Recipe
    r = Recipe(a.year)
    os.makedirs(a.crops, exist_ok=True)

    latpath = os.path.join(r.dir, "plates", "lattice.json")
    lattice = json.load(open(latpath))["units"] if os.path.exists(latpath) else {}

    def tpl_gray(unit, box):
        img = cv2.imread(r.fetch(r.sheet_file(unit)), cv2.IMREAD_GRAYSCALE)
        x0, y0, x1, y1 = box
        return img[y0:y1, x0:x1]

    rose_tpl = tpl_gray(*ROSE_TPL)
    digit_tpls = {d: tpl_gray(*spec) for d, spec in DIGIT_TPL.items()}

    units = a.units or sorted(r.units, key=lambda z: (len(z), z))
    candidates = []
    counts = {"rose_hits": 0, "digit_runs": 0, "gate_fail": 0, "kept": 0}

    for u in units:
        ud = r.units.get(u, {})
        if ud.get("panel_of"):
            continue
        path = r.fetch(r.sheet_file(u))
        gray = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
        if gray is None:
            continue
        extent = ud.get("extent")
        lat = lattice.get(u)
        found_here = []

        # ---- compass rose ----
        for s, x0, y0, x1, y1 in match_hits(gray, rose_tpl, ROSE_THRESH):
            counts["rose_hits"] += 1
            found_here.append(("compass rose", s, (x0, y0, x1, y1), (x0, y0, x1, y1)))

        # ---- digit runs ----
        all_hits = []
        for d, tpl in digit_tpls.items():
            for s, x0, y0, x1, y1 in match_hits(gray, tpl, DIGIT_THRESH):
                all_hits.append((s, x0, y0, x1, y1, d))
        for run in group_runs(all_hits):
            counts["digit_runs"] += 1
            run.sort(key=lambda h: h[1])
            digits = "".join(h[5] for h in run)
            x0 = min(h[1] for h in run)
            y0 = min(h[2] for h in run)
            x1 = max(h[3] for h in run)
            y1 = max(h[4] for h in run)
            score = sum(h[0] for h in run) / len(run)
            allow = (x0 - FIT_PAD, y0 - FIT_PAD, x1 + FIT_PAD, y1 + FIT_PAD)
            found_here.append((f"adjoining numeral {digits}", score, (x0, y0, x1, y1), allow))

        for kind, score, seed, allow in found_here:
            box = ink_fit(gray, seed, allow)
            # clip to hit footprint + FIT_PAD regardless of what ink_fit found
            fx0 = max(box[0], allow[0]); fy0 = max(box[1], allow[1])
            fx1 = min(box[2], allow[2]); fy1 = min(box[3], allow[3])
            box = (fx0, fy0, fx1, fy1)
            h = box[3] - box[1]
            reasons = []
            if h < MIN_HEIGHT:
                reasons.append(f"height {h} < {MIN_HEIGHT}")
            cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
            if extent is None:
                reasons.append("no extent recorded")
                nd = None
            else:
                nd = neatline_dist(cx, cy, extent)
                if nd > MAX_NEATLINE_DIST:
                    reasons.append(f"neatline dist {nd:.0f} > {MAX_NEATLINE_DIST}")
            if lat is None:
                reasons.append("no lattice for plate (roadway gate unverifiable)")
            elif not in_roadway(box, lat):
                reasons.append("box crosses a block-face rule (not roadway)")
            dr = darkest_row_frac(gray, box)
            if not (DARK_LO <= dr <= DARK_HI):
                reasons.append(f"darkest row {dr:.2f} outside [{DARK_LO},{DARK_HI}]")

            if reasons:
                counts["gate_fail"] += 1
                continue
            counts["kept"] += 1
            crop_name = f"u{u}_{kind.replace(' ', '_')}_{box[0]}_{box[1]}.jpg"
            crop_path = os.path.join(a.crops, crop_name)
            pad = 25
            cx0, cy0 = max(0, box[0] - pad), max(0, box[1] - pad)
            cx1, cy1 = min(gray.shape[1], box[2] + pad), min(gray.shape[0], box[3] + pad)
            crop = cv2.imread(path)[cy0:cy1, cx0:cx1]
            cv2.imwrite(crop_path, crop)
            candidates.append({
                "unit": u, "kind": kind, "box": list(box),
                "score": round(score, 3), "darkest_row_frac": round(dr, 3),
                "neatline_dist": None if nd is None else round(nd, 1),
                "crop_path": crop_path,
            })
            print(f"KEEP  u{u:3s} {kind:22s} score={score:.3f} box={box} "
                  f"dr={dr:.2f} nd={None if nd is None else round(nd)}")

    json.dump(candidates, open(a.out, "w"), indent=1)
    print(f"\n{counts['rose_hits']} raw rose hits, {counts['digit_runs']} digit runs, "
          f"{counts['gate_fail']} dropped at the gates, {counts['kept']} candidates kept")
    print(f"candidates -> {a.out}")
    print(f"crops -> {a.crops}")


if __name__ == "__main__":
    main()
