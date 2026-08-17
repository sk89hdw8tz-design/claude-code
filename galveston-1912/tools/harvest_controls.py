"""Harvest candidate seam controls for every internal pair of the 12-sheet block.

Each seam street/avenue is split between its two plates, so the genuinely common
geometry is the features CROSSING the seam. Their flanking block-face lines are
the same drafted lines on both plates and are the along-seam observables.

Method (v3): measure the LINES directly. A block-face line flanking a crossing
feature is a long straight ink run spanning the measurement strip. Morphological
opening with a long structuring element keeps only such runs; their centroids
give line positions at ~drafted-line precision. A street/avenue is then a pair
of lines 150-460 px apart with little long-line ink between them. This replaces
two failed absence-of-ink detectors (see FAILED_EXPERIMENTS F-001/F-003 for the
family of failure): measuring presence of drafted geometry, not absence of ink.

All candidates are PROPOSALS carrying semantic anchors; nothing enters the
solve until visually verified on A/B panels.
"""

import json
import os

import cv2
import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None

BASE = "/home/user/claude-code/galveston-1912"
OUT_DIR = f"{BASE}/30_controls/harvest"
os.makedirs(OUT_DIR, exist_ok=True)

inv = json.load(open(f"{BASE}/00_inventory/INVENTORY.json"))
BY = {i["sheet"]: i for i in inv["items"]}

PAIRS = [
    (7, 8, "v"), (9, 10, "v"), (11, 12, "v"),
    (8, 39, "v"), (10, 43, "v"), (12, 49, "v"),
    (39, 40, "v"), (43, 44, "v"), (49, 50, "v"),
    (7, 9, "h"), (9, 11, "h"), (8, 10, "h"), (10, 12, "h"),
    (39, 43, "h"), (43, 49, "h"), (40, 44, "h"), (44, 50, "h"),
]

CROSSING = {
    ("v", 1): ["19th St", "20th St"],
    ("v", 2): ["22nd St", "23rd St"],
    ("v", 3): ["25th St", "26th St"],
    ("h", 1): ["Ave. B (Strand)"],
    ("h", 2): ["Ave. D (Market)", "Ave. E (Post Office)"],
    ("h", 3): ["Ave. G (Winnie)", "Ave. H (Ball)"],
    ("h", 4): ["Ave. J (Broadway)"],
}
ROW = {7: 1, 8: 1, 39: 1, 40: 1, 9: 2, 10: 2, 43: 2, 44: 2, 11: 3, 12: 3, 49: 3, 50: 3}
COL = {7: 1, 9: 1, 11: 1, 8: 2, 10: 2, 12: 2, 39: 3, 43: 3, 49: 3, 40: 4, 44: 4, 50: 4}

DS = 2
STRIP_LO, STRIP_HI = 0.58, 0.88   # measurement strip on the near-seam side
LINE_LEN_FR = 0.55                # a block-face line spans >= this of the strip
MIN_GAP_PX, MAX_GAP_PX = 150, 460 # full-res street width between flanking lines
END_GUARD_PX = 150


def load_gray(sheet):
    im = Image.open(BY[sheet]["path"]).convert("L")
    W, H = im.size
    a = np.asarray(im.resize((W // DS, H // DS), Image.LANCZOS), dtype=np.uint8)
    return a, (W, H)


def strip_slice(n, near_high):
    lo, hi = int(n * STRIP_LO), int(n * STRIP_HI)
    return slice(lo, hi) if near_high else slice(n - hi, n - lo)


def long_lines(a, axis, near_high):
    """Positions (full-res px along seam axis) of long straight ink lines in the
    strip, plus the strip's plain-ink profile for the between-lines check."""
    h, w = a.shape
    paper = a > 140
    # <185 keeps the anti-aliased core of thin drafted lines at DS=2, which a
    # <165 threshold fragments (diagnosed on pair 7-8: body lines vanished while
    # thick page borders survived).
    ink = ((a < 185) & paper).astype(np.uint8)

    if axis == "v":
        sl = strip_slice(w, near_high)
        strip = ink[:, sl]
    else:
        sl = strip_slice(h, near_high)
        strip = ink[sl, :].T          # transpose: lines become horizontal
    span = strip.shape[1]

    # Bridge the +-1 px cross-axis wobble of a long thin line before demanding a
    # long contiguous run of it; otherwise the opening finds nothing but borders.
    strip = cv2.dilate(strip, cv2.getStructuringElement(cv2.MORPH_RECT, (1, 3)))
    kern = cv2.getStructuringElement(cv2.MORPH_RECT, (max(9, int(span * 0.25)), 1))
    opened = cv2.morphologyEx(strip, cv2.MORPH_OPEN, kern)
    frac = opened.sum(axis=1) / span            # fraction of strip covered by long runs
    inkfrac = strip.sum(axis=1) / span

    on = frac > LINE_LEN_FR
    lines = []
    i = 0
    n = len(on)
    while i < n:
        if on[i]:
            j = i
            while j < n and on[j]:
                j += 1
            seg = frac[i:j]
            centroid = (i + float(np.average(np.arange(j - i), weights=seg))) * DS
            lines.append(centroid)
            i = j
        else:
            i += 1
    return lines, inkfrac


def streets_from_lines(lines, inkfrac, limit):
    """Pairs of consecutive long lines separated by a street-width gap with low
    long-line ink between them."""
    out = []
    for p, q in zip(lines, lines[1:]):
        gap = q - p
        if not (MIN_GAP_PX <= gap <= MAX_GAP_PX):
            continue
        if p < END_GUARD_PX or limit - q < END_GUARD_PX:
            continue
        lo_i, hi_i = int(p / DS) + 3, int(q / DS) - 3
        if hi_i <= lo_i:
            continue
        between = float(np.mean(inkfrac[lo_i:hi_i]))
        if between < 0.30:  # street interior: sparse ink (labels only)
            out.append({"lines": [round(p, 1), round(q, 1)],
                        "centre": round((p + q) / 2, 1),
                        "width_px": round(gap, 1),
                        "between_ink": round(between, 3)})
    return out


def match(streets_a, streets_b, names, lim_a, lim_b):
    """Match by normalised centre position; label by drafted order."""
    out, used = [], set()
    for sa in streets_a:
        ca = sa["centre"] / lim_a
        best = None
        for j, sb in enumerate(streets_b):
            if j in used:
                continue
            d = abs(ca - sb["centre"] / lim_b)
            if d < 0.04 and (best is None or d < best[0]):
                best = (d, j)
        if best:
            used.add(best[1])
            out.append((ca, sa, streets_b[best[1]]))
    out.sort(key=lambda t: t[0])
    named = []
    for k, (ca, sa, sb) in enumerate(out):
        name = names[k] if len(out) == len(names) else None
        named.append((name, sa, sb))
    return named


all_pairs, n_cand = [], 0
for A, B, axis in PAIRS:
    a_img, size_a = load_gray(A)
    b_img, size_b = load_gray(B)
    lim_a = size_a[1] if axis == "v" else size_a[0]
    lim_b = size_b[1] if axis == "v" else size_b[0]

    lines_a, inkf_a = long_lines(a_img, axis, near_high=True)
    lines_b, inkf_b = long_lines(b_img, axis, near_high=False)
    st_a = streets_from_lines(lines_a, inkf_a, lim_a)
    st_b = streets_from_lines(lines_b, inkf_b, lim_b)

    key = ("v", ROW[A]) if axis == "v" else (("h", COL[A]))
    names = CROSSING[key]
    matched = match(st_a, st_b, names, lim_a, lim_b)

    cands = [
        {
            "anchor": name,
            "verified": False,
            "class": "observed",
            "sigma_along_px": 6.0,
            "measurement": "centroids of long block-face lines flanking the crossing feature",
            "A": sa,
            "B": sb,
        }
        for name, sa, sb in matched
    ]
    n_cand += len(cands)
    all_pairs.append(
        {
            "pair": [A, B],
            "axis": "vertical" if axis == "v" else "horizontal",
            "lines_detected": {"A": len(lines_a), "B": len(lines_b)},
            "streets_detected": {"A": len(st_a), "B": len(st_b)},
            "expected_interior": len(names),
            "candidates": cands,
        }
    )
    ok = "OK " if len(cands) == len(names) else "CHECK"
    print(
        f"[{ok}] pair {A:2d}-{B:2d} {axis}  lines A={len(lines_a)} B={len(lines_b)}  "
        f"streets A={len(st_a)} B={len(st_b)}  matched={len(cands)}/{len(names)}"
    )

with open(f"{OUT_DIR}/candidates.json", "w") as fh:
    json.dump(
        {
            "note": "PROPOSALS ONLY - nothing enters the solve until verified on A/B panels",
            "method": "morphological long-line extraction v3",
            "strip_range": [STRIP_LO, STRIP_HI],
            "pairs": all_pairs,
        },
        fh,
        indent=1,
    )
print(f"\n{n_cand} candidate controls across {len(PAIRS)} pairs")
print(f"wrote {OUT_DIR}/candidates.json")
