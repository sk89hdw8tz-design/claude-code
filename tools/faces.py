#!/usr/bin/env python3
"""Block-face lines read off a plate, in its own pixels.

A Sanborn plate's block faces are the long straight rules that bound each
block; the roadway between two facing rules is the street. Reading them off
the ink profile gives two things the seam work needs without any placement
being assumed:

  first_face(u, axis, side)   the face that bounds the shared street on a
                              plate's edge -- the north face on the sheet
                              above, the south face on the sheet below
  enclosing(u, axis, coord)   the two faces either side of a coordinate, whose
                              separation says whether that coordinate is in a
                              70 ft avenue (~206-214 px), an 80 ft street
                              (~230-250 px) or a 20 ft alley (~60 px)

Profiles are taken in the plate's native frame, where its drafting grid is
straight (the mosaic frame tilts each plate by up to ~0.6 deg, which smears a
rule across 60 px and hides it). A rule shows as a spike in the fraction of
the row (or column) that is ink; margin furniture -- the neighbour brackets
along the paper edge, the plate number -- also spikes, so a face is
recognised by what follows it: the next rule inward sits a block away.
"""
import functools
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from reciplib import Recipe                      # noqa: E402

PAPER_MIN = 100
INK_MIN = 110          # the plates' ink; Otsu may raise this on a stained page
INK_MAX = 130
SPIKE = 0.15            # fraction of the page row that is ink
BLOCK_PX = {"y": (780, 1060),    # face-to-face block depth between streets
            "x": (680, 1000)}    # between avenues (280 ft) and the M-1/2 outlots
_cache = {}


def page_ink(r, u):
    if u in _cache:
        return _cache[u]
    import cv2
    from scipy import ndimage
    a = cv2.imread(r.fetch(r.sheet_file(u)), 0)
    # the LOC backdrop is ~30-80 grey; stained outlot plates (96) run to
    # ~120 on the paper, so the page is whatever is brighter than the
    # backdrop, and ink is the dark tail of the page's own histogram
    bright = a > PAPER_MIN
    lab, n = ndimage.label(bright)
    sizes = ndimage.sum(bright, lab, range(1, n + 1))
    page = ndimage.binary_fill_holes(lab == (1 + int(np.argmax(sizes))))
    vals = a[page]
    t, _ = cv2.threshold(vals.reshape(-1, 1), 0, 255,
                         cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    ink = (a < float(np.clip(t, INK_MIN, INK_MAX))) & page
    _cache[u] = (page, ink)
    return _cache[u]


def profile(r, u, axis):
    """Ink fraction along the page, per row (axis y) or column (axis x)."""
    page, ink = page_ink(r, u)
    ax = 1 if axis == "y" else 0
    p = ink.sum(ax) / np.maximum(page.sum(ax), 1)
    cov = page.sum(ax) / page.shape[ax]
    p[cov < 0.5] = 0.0                     # rows mostly off the paper
    return p


def spikes(r, u, axis):
    """[(pos, strength)] of rules, non-maximum suppressed over 6 px."""
    p = profile(r, u, axis)
    from scipy import ndimage
    pm = ndimage.maximum_filter1d(p, 3)
    out = []
    i = 1
    while i < len(p) - 1:
        if pm[i] >= SPIKE and p[i] >= p[i - 1] and p[i] >= p[i + 1]:
            j = i
            while j + 1 < len(p) and j - i < 6:
                j += 1
            k = i + int(np.argmax(p[i:j + 1]))
            out.append((int(k), float(p[k])))
            i = j + 1
        else:
            i += 1
    return out


def first_face(r, u, axis, side):
    """Native coordinate of the block face nearest the given edge of the
    plate that actually starts a block (the next rule inward is a block
    away), or None. side: 'low' = top/left edge, 'high' = bottom/right."""
    sp = spikes(r, u, axis)
    lo, hi = BLOCK_PX[axis]
    if side == "high":
        sp = sp[::-1]
    for i, (pos, s) in enumerate(sp):
        for pos2, s2 in sp[i + 1:]:
            d = abs(pos2 - pos)
            if d > hi:
                break
            if lo <= d <= hi:
                return pos
    return None


def enclosing(r, u, axis, coord, max_dist=400):
    """(low_face, high_face) bracketing coord, each within max_dist, else None
    for the missing side."""
    sp = [p for p, s in spikes(r, u, axis)]
    below = [p for p in sp if p <= coord and coord - p <= max_dist]
    above = [p for p in sp if p >= coord and p - coord <= max_dist]
    return (max(below) if below else None, min(above) if above else None)


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", default="1912")
    ap.add_argument("unit")
    ap.add_argument("axis", choices=["x", "y"])
    a = ap.parse_args()
    r = Recipe(int(a.year))
    for pos, s in spikes(r, a.unit, a.axis):
        print(f"{pos:5d}  {s:.2f}")
    print("first_face low :", first_face(r, a.unit, a.axis, "low"))
    print("first_face high:", first_face(r, a.unit, a.axis, "high"))


# ---------------------------------------------------------------------------
# Periodic street/avenue model: the robust reading.
#
# A single spike can be a face, a bracket, the north arrow's bar, a scale bar
# or a bleacher. A whole plate's rules cannot: its streets recur at the city
# pitch (399.5 ft between street centres, 350.4 ft between avenues) and every
# street is two faces a roadway apart. Fitting that pattern to all the spikes
# at once reads every corridor on the plate, including the ones at its edges
# that the plate draws only half of.
# ---------------------------------------------------------------------------
PITCH_PX = {"y": (1090, 1200), "x": (950, 1040)}   # native px, ~2.86 px/ft
WIDTHS = {"y": (200, 215, 230, 245), "x": (195, 206, 215, 230)}
ROAD_PENALTY = 3.0     # x mean ink fraction inside a roadway (a block interior is ~0.08)
WIDTH_PRIOR = 0.5      # x |width - default| / default


BLOCK_PX = {"y": (850, 990),     # face-to-face block depth between streets
            "x": (730, 880)}     # between avenues
ROAD_PX = {"y": (190, 400), "x": (180, 330)}   # roadway width; 25th St is ~125 ft
BLOCK_NOMINAL = {"y": (870, 950), "x": (765, 840)}   # 320 ft / 280 ft, +-4%
DEFAULT_ROAD = {"y": 245, "x": 206}
EDGE_ZONE = 420                 # a lone face this close to the edge may be a
                                # half-drawn street whose other face is off-page


def lattice(r, u, axis):
    """Read every corridor on the plate as a chain of streets.

    A street is two faces a roadway apart with little ink between them; the
    next street's near face is a block away. Widths are free per street (25th
    St is a 125 ft boulevard; most are 70-80 ft), blocks are the city's
    uniform depth. Dynamic programming over the rule spikes picks the chain
    with the strongest faces and the cleanest roadways; a street at the
    plate's edge may show only one face.

    Returns {"centres", "widths", "faces", "pitch", "width", "score",
    "weak"} with centres in native px, or None.
    """
    sp = spikes(r, u, axis)
    weak = False
    if len(sp) < 6:
        global SPIKE
        keep, SPIKE = SPIKE, 0.10
        try:
            sp = spikes(r, u, axis)
        finally:
            SPIKE = keep
        weak = True
    if len(sp) < 2:
        return None
    page, _ = page_ink(r, u)
    n = page.shape[0 if axis == "y" else 1]
    prof = profile(r, u, axis)
    cum = np.concatenate([[0.0], np.cumsum(prof)])
    pos = [p for p, s in sp]
    st = [min(s, 0.5) for p, s in sp]
    rlo, rhi = ROAD_PX[axis]
    blo, bhi = BLOCK_PX[axis]
    wdef = DEFAULT_ROAD[axis]

    def road_ink(a, b):
        a0, a1 = max(0, a + 10), min(n, b - 10)
        return (cum[a1] - cum[a0]) / max(1, a1 - a0) if a1 > a0 else 0.0

    # candidate streets: (lo_face, hi_face, score, virtual)
    streets = []
    for i, a in enumerate(pos):
        for j in range(i + 1, len(pos)):
            b = pos[j]
            if b - a < rlo:
                continue
            if b - a > rhi:
                break
            # mild prior for the usual 70-80 ft roadway: a boulevard's two
            # strong faces still win it, a bleacher rule paired with a lot
            # line 130 ft away does not
            prior = WIDTH_PRIOR * abs(b - a - wdef) / wdef
            streets.append((a, b, st[i] + st[j] - ROAD_PENALTY * road_ink(a, b) - prior, False))
    for i, a in enumerate(pos):                  # half streets at the edges
        if a < EDGE_ZONE:
            streets.append((a - wdef, a, st[i] - ROAD_PENALTY * road_ink(0, a), True))
        if a > n - EDGE_ZONE:
            streets.append((a, a + wdef, st[i] - ROAD_PENALTY * road_ink(a, n), True))
    if not streets:
        return None
    streets.sort()
    # DP: best chain ending at each street
    best = [(sc, None) for a, b, sc, v in streets]
    for k, (a, b, sc, v) in enumerate(streets):
        for m in range(k):
            a2, b2, sc2, v2 = streets[m]
            d = a - b2
            if blo <= d <= bhi and best[m][0] + sc > best[k][0]:
                best[k] = (best[m][0] + sc, m)
    k = int(np.argmax([b[0] for b in best]))
    total = best[k][0]
    chain = []
    while k is not None:
        chain.append(streets[k])
        k = best[k][1]
    chain.reverse()
    if len(chain) < 2:
        return None
    centres = [int(round((a + b) / 2)) for a, b, _, _ in chain]
    widths = [int(b - a) for a, b, _, _ in chain]
    pitches = np.diff(centres)
    # extend one corridor beyond each end at the median pitch, so a street
    # just off the paper (the neighbour draws it) is still addressable
    P = int(np.median(pitches)) if len(pitches) else (1150 if axis == "y" else 1000)
    ext = [centres[0] - P] + centres + [centres[-1] + P]
    ext = [c for c in ext if -wdef <= c <= n + wdef]
    # blocks are the city's uniform depth; a chain whose blocks are not is
    # reading something else (rail lines on 75, beach strips on 99)
    blocks = [chain[i + 1][0] - chain[i][1] for i in range(len(chain) - 1)]
    nb_lo, nb_hi = BLOCK_NOMINAL[axis]
    odd = [d for d in blocks if not nb_lo <= d <= nb_hi]
    return {"s0": centres[0], "pitch": P, "width": int(np.median(widths)),
            "score": round(float(total), 2), "centres": ext,
            "widths": widths, "faces": [[int(a), int(b)] for a, b, _, _ in chain],
            "blocks": blocks, "n_streets": len(chain),
            "weak": bool(weak or len(chain) < 3 or total < 1.0 or odd)}


def edge_corridor(r, u, axis, side):
    """Centreline (native px) of the corridor at the plate's low/high edge:
    the last lattice corridor whose roadway still touches the page."""
    L = lattice(r, u, axis)
    if not L:
        return None, None
    page, _ = page_ink(r, u)
    n = page.shape[0 if axis == "y" else 1]
    cs = [c for c in L["centres"] if -L["width"] / 2 <= c <= n + L["width"] / 2]
    if not cs:
        return None, L
    return (min(cs) if side == "low" else max(cs)), L


def lattice_all(r, path=None, force=False):
    """Fit every unit on both axes; cached at recipe/plates/lattice.json."""
    import json
    path = path or os.path.join(r.dir, "plates", "lattice.json")
    if os.path.exists(path) and not force:
        return json.load(open(path))["units"]
    out = {}
    for u in sorted(r.units, key=lambda k: int("".join(c for c in k if c.isdigit()))):
        out[u] = {}
        for ax in ("y", "x"):
            L = lattice(r, u, ax)
            out[u][ax] = L
            print(f"unit {u:>3} {ax}: " + (f"pitch {L['pitch']} width {L['width']} "
                  f"score {L['score']:.2f} centres {L['centres']}" if L else "none"),
                  flush=True)
        _cache.pop(u, None)                 # free the page masks
    os.makedirs(os.path.dirname(path), exist_ok=True)
    json.dump({"tool": "tools/faces.py lattice()", "frame": "working image px",
               "model": "corridor centres s0 + k*pitch; faces at +-width/2",
               "units": out}, open(path, "w"), indent=1)
    return out
