#!/usr/bin/env python3
"""Detect the printed street-width tags (70', 80', ...) at each plate's edges.

    python3 tools/widthtag.py --year 1912 [--units 45 7 ...] [--out DIR]

DETECTOR ONLY -- never writes units.json. On the tools/scalebar.py /
tools/edgeglyph.py pattern: a handful of clean native crops of the series'
`70'` and `80'` tags (horizontal, as printed in a north-south roadway at
the top/bottom neatline, and rotated 90 degrees, as printed in an east-west
roadway at the left/right neatline) template-match a band within BAND px
of every plate's neatline (`extent` in units.json). Every plate prints its
own tag where a street leaves it, so where two plates meet the mosaic
shows both ("70' 70'"); the fix is a furniture box per tag so the seam
cutter can hand that ground to the neighbour. This tool only proposes
the boxes.

Per plate:
  - TM_CCOEFF_NORMED for each template at scales 0.9/1.0/1.1, response
    zeroed outside the neatline band, local maxima >= THRESH, then greedy
    NMS across templates/scales (IoU 0.3, best score wins)
  - each hit's box is fitted to its ink: threshold = local median - 40,
    contiguous run of columns/rows carrying >= INK_MIN_PX ink pixels,
    grown outward from the hit centre until a gap of GAP_PX; a thin
    dashed pipe line crossing the tag (common) cannot drag the box out,
    and the leading digits of a wider tag (100', 120') that the 70'/80'
    template matched only on its "0'" are picked up because the allowance
    extends LEAD_EXTRA px in the reading direction; box padded PAD px
  - gates: box centre within BAND px of the neatline and not more than
    OUTSIDE_TOL px outside it; padded height 25-80 px; darkest row/column
    ink fraction in [DARK_LO, DARK_HI] (true tags measure 0.36-0.7: the
    glyphs are small, so the floor is low and the cap is what matters,
    rejecting a rule swept into the box); no overlap with an existing
    `furniture_native` box; ring-ink (ink fraction in a RING px ring
    around the padded box) <= RING_MAX so a lot number packed against
    its neighbours and block front does not survive as a "tag"; median
    saturation of the box's paper <= SAT_MAX (an italic "D." dwelling
    label on a tinted footprint is the one look-alike the templates hit)
  - recorded, not gated: whether the box overlaps a street interval of
    plates/lattice.json on either axis (a tag sits in a roadway)

Outputs (default outputs/<year>/review/ring1/widthtags/):
  crops/uNN_k.jpg      native crop, box + CROP_MARGIN px, box outlined red
  montage_uNN[_m].jpg  up to 12 labelled crops per image
  candidates.json      [{unit, box, score, edge, orientation, template, ...}]
  summary.json         counts per plate, gate-fail tallies, template list

The template's text ("70'" / "80'") is a guess only: the templates share
the "0'" and a 70' template scores ~0.58 on an 80' tag, so the reviewer
reads the crop. Alley tags ("20'") are not templated and do not fire
except by accident; they are noted in the montage if they do.
"""
import argparse
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
REPO = os.path.dirname(HERE)

# ---- templates: (name, unit, native ink box [x0,y0,x1,y1], orientation, text)
# Ink boxes fitted at threshold median-40 on the working scans; TPL_PAD px
# of paper is added around each so the correlation sees the glyph's edges.
TEMPLATES = [
    ("70h_45a", "45", (2116, 340, 2150, 366), "horizontal", "70'"),   # Ave M 1/2, top
    ("70h_45b", "45", (1119, 3521, 1154, 3549), "horizontal", "70'"),  # Ave M, bottom
    ("70h_7e", "7", (3188, 3486, 3227, 3519), "horizontal", "70'"),    # right/bottom corner
    ("70h_33m", "33", (3169, 318, 3204, 349), "horizontal", "70'"),    # top right
    ("80h_7a", "7", (2161, 322, 2201, 349), "horizontal", "80'"),      # top
    ("80h_33k", "33", (2164, 320, 2204, 354), "horizontal", "80'"),    # top
    ("80r_45a", "45", (2979, 193, 3023, 237), "rotated", "80'"),       # 21st St, right
    ("80r_45b", "45", (232, 3645, 261, 3682), "rotated", "80'"),       # 24th St, left
    ("80r_7f", "7", (3035, 3645, 3065, 3684), "rotated", "80'"),       # bottom right
    # digits only, no prime: rotated tags standing 8 px off a rail line in
    # plate 33's wharf yard score < 0.55 against the prime-included crops
    # because the line falls inside the template window; these two are
    # tolerant of a neighbouring rule (33i is itself crossed by a dashed pipe)
    ("80r_33h", "33", (314, 3660, 334, 3689), "rotated", "80'"),      # left, yard
    ("80r_33i", "33", (313, 2509, 334, 2544), "rotated", "80'"),      # left, yard, dashes
]
TPL_PAD = 4
SCALES = (0.9, 1.0, 1.1)
THRESH = 0.58
NMS_IOU = 0.3
BAND = 300           # px inside the neatline the band (and the centre gate) reach
OUTSIDE_TOL = 5      # px a centre may sit outside `extent` (neatline fit slack);
                     # the scanner's black corner marks sit 20+ px outside
SAT_MAX = 45         # median HSV saturation of the box's paper pixels; tags sit
                     # on plain paper (16-30), an italic "D." dwelling label sits
                     # on a tinted footprint (55-113)
WALL_FRAC = 0.85     # a column/row this full of ink is a rule, not glyph ink
INK_DELTA = 40       # ink threshold = local median - INK_DELTA
INK_MIN_PX = 5       # a column/row counts as glyph ink with >= this many ink px
GAP_PX = 6           # consecutive empty columns/rows that end the glyph run
ALLOW = 10           # px the fit may grow past the hit box on every side
LEAD_EXTRA = 45      # extra allowance in the reading direction (leading digits)
PAD = 6
H_MIN, H_MAX = 25, 80
W_MIN, W_MAX = 20, 120
DARK_LO, DARK_HI = 0.30, 0.95
RING = 12
RING_MAX = 0.30
CROP_MARGIN = 120
MONTAGE_TILE = 300
MONTAGE_PER = 12


def iou(a, b):
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    ix0, iy0 = max(ax0, bx0), max(ay0, by0)
    ix1, iy1 = min(ax1, bx1), min(ay1, by1)
    inter = max(0, ix1 - ix0) * max(0, iy1 - iy0)
    if inter <= 0:
        return 0.0
    ua = (ax1 - ax0) * (ay1 - ay0) + (bx1 - bx0) * (by1 - by0) - inter
    return inter / ua if ua > 0 else 0.0


def overlaps(a, b):
    return not (a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1])


def band_mask(shape, extent):
    """Boolean mask of the pixels within BAND px inside (or OUTSIDE_TOL px
    outside) the neatline."""
    h, w = shape
    ex0, ey0, ex1, ey1 = extent
    m = np.zeros((h, w), bool)
    lo_x, hi_x = max(0, ex0 - OUTSIDE_TOL), min(w, ex1 + OUTSIDE_TOL)
    lo_y, hi_y = max(0, ey0 - OUTSIDE_TOL), min(h, ey1 + OUTSIDE_TOL)
    m[lo_y:hi_y, lo_x:min(w, ex0 + BAND)] = True
    m[lo_y:hi_y, max(0, ex1 - BAND):hi_x] = True
    m[lo_y:min(h, ey0 + BAND), lo_x:hi_x] = True
    m[max(0, ey1 - BAND):hi_y, lo_x:hi_x] = True
    return m


def match_hits(gray, tpl, thresh, mask):
    """Local maxima of tpl's TM_CCOEFF_NORMED response >= thresh whose
    box centre lies in mask -> [(score, (x0,y0,x1,y1))]."""
    import cv2
    th, tw = tpl.shape
    if gray.shape[0] < th or gray.shape[1] < tw:
        return []
    res = cv2.matchTemplate(gray, tpl, cv2.TM_CCOEFF_NORMED)
    # centre of the box at response (x, y) is (x + tw/2, y + th/2)
    sub = mask[th // 2: th // 2 + res.shape[0], tw // 2: tw // 2 + res.shape[1]]
    res = np.where(sub, res, 0.0).astype(np.float32)
    k = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 15))
    peak = (res >= thresh) & (res >= cv2.dilate(res, k))
    ys, xs = np.where(peak)
    return [(float(res[y, x]), (int(x), int(y), int(x + tw), int(y + th)))
            for y, x in zip(ys, xs)]


def nms(hits):
    """hits: [(score, box, meta)] -> greedy best-first suppression."""
    hits = sorted(hits, key=lambda h: -h[0])
    kept = []
    for h in hits:
        if any(iou(h[1], k[1]) > NMS_IOU for k in kept):
            continue
        kept.append(h)
    return kept


def local_ink_thresh(gray, box):
    x0, y0, x1, y1 = box
    cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
    r = 100
    win = gray[max(0, cy - r):cy + r, max(0, cx - r):cx + r]
    return float(np.median(win)) - INK_DELTA if win.size else 128.0 - INK_DELTA


def grow_run(profile, wall, lo, hi):
    """Extend [lo, hi) over profile (bool per column/row) outward until
    GAP_PX consecutive False entries are met on that side, or a wall (a
    rule running the full length of the window) is reached."""
    n = len(profile)
    # left/up
    gap, i, lo_new = 0, lo - 1, lo
    while i >= 0 and gap < GAP_PX and not wall[i]:
        if profile[i]:
            lo_new = i
            gap = 0
        else:
            gap += 1
        i -= 1
    gap, i, hi_new = 0, hi, hi
    while i < n and gap < GAP_PX and not wall[i]:
        if profile[i]:
            hi_new = i + 1
            gap = 0
        else:
            gap += 1
        i += 1
    return lo_new, hi_new


def ink_fit(gray, hit_box, orientation):
    """Fit hit_box to the glyph ink around it (see module docstring)."""
    x0, y0, x1, y1 = hit_box
    ax0, ay0, ax1, ay1 = x0 - ALLOW, y0 - ALLOW, x1 + ALLOW, y1 + ALLOW
    if orientation == "horizontal":
        ax0 -= LEAD_EXTRA          # leading digits sit to the left
    else:
        ay1 += LEAD_EXTRA          # rotated tags read bottom-to-top
    ax0, ay0 = max(0, ax0), max(0, ay0)
    ax1, ay1 = min(gray.shape[1], ax1), min(gray.shape[0], ay1)
    sub = gray[ay0:ay1, ax0:ax1]
    if sub.size == 0:
        return hit_box, 0.0
    thr = local_ink_thresh(gray, hit_box)
    dark = sub < thr
    cc, rc = dark.sum(axis=0), dark.sum(axis=1)
    wall_c, wall_r = cc >= WALL_FRAC * dark.shape[0], rc >= WALL_FRAC * dark.shape[1]
    cols = (cc >= INK_MIN_PX) & ~wall_c
    rows = (rc >= INK_MIN_PX) & ~wall_r
    # seed: the central third of the hit box on each axis
    cxl, cxh = (x0 - ax0) + (x1 - x0) // 3, (x0 - ax0) + 2 * (x1 - x0) // 3
    cyl, cyh = (y0 - ay0) + (y1 - y0) // 3, (y0 - ay0) + 2 * (y1 - y0) // 3
    fx0, fx1 = grow_run(cols, wall_c, cxl, cxh)
    fy0, fy1 = grow_run(rows, wall_r, cyl, cyh)
    # tighten each axis to actual ink inside the other axis' run
    block = dark[fy0:fy1, fx0:fx1]
    if block.any():
        ys, xs = np.where(block)
        fx0, fx1 = fx0 + int(xs.min()), fx0 + int(xs.max()) + 1
        fy0, fy1 = fy0 + int(ys.min()), fy0 + int(ys.max()) + 1
    return (ax0 + fx0, ay0 + fy0, ax0 + fx1, ay0 + fy1), thr


def darkest_line_frac(gray, box, thr):
    x0, y0, x1, y1 = box
    sub = gray[max(0, y0):y1, max(0, x0):x1]
    if sub.size == 0:
        return 0.0
    dark = sub < thr
    r = dark.sum(axis=1) / sub.shape[1]
    c = dark.sum(axis=0) / sub.shape[0]
    return float(max(r.max(), c.max()))


def ring_ink(gray, box, thr):
    x0, y0, x1, y1 = box
    ox0, oy0 = max(0, x0 - RING), max(0, y0 - RING)
    ox1, oy1 = min(gray.shape[1], x1 + RING), min(gray.shape[0], y1 + RING)
    outer = gray[oy0:oy1, ox0:ox1] < thr
    inner = np.zeros_like(outer)
    inner[y0 - oy0:y1 - oy0, x0 - ox0:x1 - ox0] = True
    ring = outer & ~inner
    n = (~inner).sum()
    return float(ring.sum() / n) if n else 0.0


def paper_saturation(color, box, thr):
    """Median HSV saturation of the non-ink pixels inside box."""
    import cv2
    x0, y0, x1, y1 = box
    sub = color[max(0, y0):y1, max(0, x0):x1]
    if sub.size == 0:
        return 0.0
    hsv = cv2.cvtColor(sub, cv2.COLOR_BGR2HSV)
    paper = cv2.cvtColor(sub, cv2.COLOR_BGR2GRAY) >= thr
    return float(np.median(hsv[..., 1][paper])) if paper.any() else 0.0


def neatline_info(cx, cy, extent):
    ex0, ey0, ex1, ey1 = extent
    d = {"left": cx - ex0, "right": ex1 - cx, "top": cy - ey0, "bottom": ey1 - cy}
    edge = min(d, key=d.get)
    return edge, float(d[edge])


def street_flags(box, lat):
    if not lat:
        return None, None
    x0, y0, x1, y1 = box
    xf = (lat.get("x") or {}).get("faces") or []
    yf = (lat.get("y") or {}).get("faces") or []

    def hits(faces, lo, hi):
        return any(not (hi < f[0] or lo > f[1]) for f in faces)
    return hits(xf, x0, x1), hits(yf, y0, y1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", type=int, default=1912)
    ap.add_argument("--units", nargs="*", default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--thresh", type=float, default=THRESH)
    ap.add_argument("--notes", default=None,
                    help="JSON file merged into summary.json (e.g. by-eye spot-check misses)")
    a = ap.parse_args()
    import cv2
    from reciplib import Recipe
    r = Recipe(a.year)
    out = a.out or os.path.join(REPO, "outputs", str(a.year), "review", "ring1", "widthtags")
    crops_dir = os.path.join(out, "crops")
    os.makedirs(crops_dir, exist_ok=True)

    latpath = os.path.join(r.dir, "plates", "lattice.json")
    lattice = json.load(open(latpath))["units"] if os.path.exists(latpath) else {}

    tpl_cache = {}

    def scan(unit):
        if unit not in tpl_cache:
            tpl_cache[unit] = cv2.imread(r.fetch(r.sheet_file(unit)), cv2.IMREAD_GRAYSCALE)
        return tpl_cache[unit]

    templates = []
    for name, unit, (x0, y0, x1, y1), orient, text in TEMPLATES:
        g = scan(unit)
        base = g[y0 - TPL_PAD:y1 + TPL_PAD, x0 - TPL_PAD:x1 + TPL_PAD]
        for s in SCALES:
            t = base if s == 1.0 else cv2.resize(
                base, None, fx=s, fy=s, interpolation=cv2.INTER_AREA if s < 1 else cv2.INTER_CUBIC)
            templates.append((name, s, orient, text, t))
    tpl_cache.clear()

    units = a.units or sorted(r.units, key=lambda z: (len(z), z))
    candidates, summary = [], {"per_plate": {}, "gate_fail": {}, "thresh": a.thresh,
                               "templates": [t[0] for t in TEMPLATES]}
    for u in units:
        ud = r.units.get(u, {})
        if ud.get("panel_of") or not ud.get("extent"):
            continue
        path = r.fetch(r.sheet_file(u))
        gray = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
        if gray is None:
            continue
        extent = ud["extent"]
        furn = [f["box"] for f in ud.get("furniture_native", []) if f.get("box")]
        mask = band_mask(gray.shape, extent)
        color = cv2.imread(path)
        hits = []
        for name, s, orient, text, t in templates:
            for score, box in match_hits(gray, t, a.thresh, mask):
                hits.append((score, box, (name, s, orient, text)))
        kept_here = []
        fails = {}
        for score, hbox, (name, s, orient, text) in nms(hits):
            fbox, thr = ink_fit(gray, hbox, orient)
            box = (fbox[0] - PAD, fbox[1] - PAD, fbox[2] + PAD, fbox[3] + PAD)
            w, h = box[2] - box[0], box[3] - box[1]
            cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
            edge, nd = neatline_info(cx, cy, extent)
            dl = darkest_line_frac(gray, box, thr)
            ri = ring_ink(gray, box, thr)
            sx, sy = street_flags(box, lattice.get(u))
            sat = paper_saturation(color, box, thr)
            reasons = []
            if sat > SAT_MAX:
                reasons.append("tinted")
            if not (H_MIN <= h <= H_MAX):
                reasons.append("height")
            if not (W_MIN <= w <= W_MAX):
                reasons.append("width")
            if nd > BAND or nd < -OUTSIDE_TOL:
                reasons.append("neatline")
            if not (DARK_LO <= dl <= DARK_HI):
                reasons.append("darkest")
            if any(overlaps(box, f) for f in furn):
                reasons.append("furniture")
            if ri > RING_MAX:
                reasons.append("ring")
            if any(iou(box, k["box"]) > NMS_IOU for k in kept_here):
                reasons.append("dup")
            if reasons:
                for rs in reasons:
                    fails[rs] = fails.get(rs, 0) + 1
                continue
            kept_here.append({
                "unit": u, "box": [int(v) for v in box], "score": round(score, 3),
                "edge": edge, "orientation": orient, "template": name,
                "text_guess": text, "scale": s,
                "neatline_dist": round(nd, 1), "darkest_line_frac": round(dl, 3),
                "ring_ink": round(ri, 3), "paper_sat": round(sat, 1),
                "in_street_x": sx, "in_street_y": sy,
                "hit_box": [int(v) for v in hbox],
            })
        # order along the plate edge for stable numbering
        kept_here.sort(key=lambda c: ({"top": 0, "right": 1, "bottom": 2, "left": 3}[c["edge"]],
                                      c["box"][0] if c["edge"] in ("top", "bottom") else c["box"][1]))
        tiles = []
        for k, c in enumerate(kept_here, 1):
            x0, y0, x1, y1 = c["box"]
            cx0, cy0 = max(0, x0 - CROP_MARGIN), max(0, y0 - CROP_MARGIN)
            cx1, cy1 = min(gray.shape[1], x1 + CROP_MARGIN), min(gray.shape[0], y1 + CROP_MARGIN)
            crop = color[cy0:cy1, cx0:cx1].copy()
            cv2.rectangle(crop, (x0 - cx0, y0 - cy0), (x1 - cx0 - 1, y1 - cy0 - 1), (0, 0, 255), 1)
            name = f"u{u}_{k}.jpg"
            cv2.imwrite(os.path.join(crops_dir, name), crop, [cv2.IMWRITE_JPEG_QUALITY, 80])
            c["k"] = k
            c["crop"] = os.path.relpath(os.path.join(crops_dir, name), REPO)
            tile = np.full((MONTAGE_TILE, MONTAGE_TILE, 3), 255, np.uint8)
            th, tw = crop.shape[:2]
            f = min((MONTAGE_TILE - 22) / th, MONTAGE_TILE / tw, 1.0)
            small = cv2.resize(crop, (int(tw * f), int(th * f)), interpolation=cv2.INTER_AREA)
            tile[22:22 + small.shape[0], :small.shape[1]] = small
            label = (f"u{u}#{k} {c['edge']} {c['orientation'][0]} {c['template']} "
                     f"s={c['score']:.2f} r={c['ring_ink']:.2f}")
            cv2.putText(tile, label, (3, 15), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 0, 0), 1)
            tiles.append(tile)
            print(f"KEEP u{u:3s} #{k:2d} {c['edge']:6s} {c['orientation']:10s} {c['template']:8s} "
                  f"s={c['score']:.2f} box={c['box']} nd={c['neatline_dist']:.0f} "
                  f"dl={c['darkest_line_frac']:.2f} ring={c['ring_ink']:.2f} "
                  f"street=({c['in_street_x']},{c['in_street_y']})")
        for m in range(0, len(tiles), MONTAGE_PER):
            chunk = tiles[m:m + MONTAGE_PER]
            while len(chunk) % 4:
                chunk.append(np.full((MONTAGE_TILE, MONTAGE_TILE, 3), 255, np.uint8))
            rows = [np.hstack(chunk[i:i + 4]) for i in range(0, len(chunk), 4)]
            suffix = "" if m == 0 else f"_{m // MONTAGE_PER + 1}"
            cv2.imwrite(os.path.join(out, f"montage_u{u}{suffix}.jpg"), np.vstack(rows),
                        [cv2.IMWRITE_JPEG_QUALITY, 80])
        candidates.extend(kept_here)
        summary["per_plate"][u] = {
            "kept": len(kept_here),
            "by_edge": {e: sum(1 for c in kept_here if c["edge"] == e)
                        for e in ("top", "right", "bottom", "left")},
            "raw_hits": len(hits), "gate_fail": fails,
        }
        for rs, n in fails.items():
            summary["gate_fail"][rs] = summary["gate_fail"].get(rs, 0) + n
        print(f"u{u}: {len(kept_here)} kept of {len(hits)} raw hits; fails {fails}")

    if a.notes and os.path.exists(a.notes):
        summary.update(json.load(open(a.notes)))
    summary["total"] = len(candidates)
    json.dump(candidates, open(os.path.join(out, "candidates.json"), "w"), indent=1)
    json.dump(summary, open(os.path.join(out, "summary.json"), "w"), indent=1)
    print(f"\n{len(candidates)} candidates -> {os.path.join(out, 'candidates.json')}")


if __name__ == "__main__":
    main()
