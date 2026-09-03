#!/usr/bin/env python3
"""Cut sheet ownership along street centrelines, as the brief requires.

    python3 tools/streetcut.py --year 1912 [--apply]

Non-negotiable §2.5: "cut seams down street centrelines so no building
footprint is ever split across a seam". Three sources decide where a seam
between two overlapping sheets goes, in order:

  1. a CONTROL on the seam's axis -- the shared corridor an observer named
     and measured on both plates (recipe/controls/): the seam IS that line;
  2. the plates' own LATTICE (tools/faces.py) -- every plate's streets recur
     at the city pitch, so the corridor nearest the middle of the two sheets'
     overlap is read off each plate, mapped through its transform, and the
     seam is the mean of the two readings. The two readings also measure how
     far the pair still disagrees; that residual is reported;
  3. the midpoint of the overlap (corner contacts, or no lattice).

Two things this version does differently from the first, both from HQ-19:

  * A sheet is trimmed ONLY inside its overlap with each neighbour. The first
    version intersected whole half-planes, so a diagonal neighbour's cut
    reached across the entire sheet and stranded ground (the 57|63 white band
    was exactly that: an inlet of unclaimed ground between two half-planes
    that did not meet, open to the exterior so the hole audit never saw it).
    Now region(u) = base(u) - U_v (base(u) n base(v) n v's side), which can
    only remove ground the neighbour keeps.
  * The frozen downtown core keeps its accepted min-ink DP masks
    (seams/masks.json, the 27x40 master's own cuts) as its base; the first
    version had silently replaced them with bisector boxes. Ring neighbours
    are cut against the core exactly as against each other.

Geometry only; no pixel is altered.
"""
import argparse
import json
import os
import re
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from reciplib import Recipe, px_per_ft          # noqa: E402
from faces import lattice_all                    # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIG = 1e7
MIN_OVERLAP = 2500.0          # px^2; below this two sheets merely touch
BAND_FRACTION = 0.6           # overlap spanning this much of the shorter
                              # sheet across the seam axis is a true seam


def load_cuts(r):
    """{(a,b): {axis: (mosaic_coord, corridor)}} from every accepted control.

    A pair can carry TWO controls: the street it abuts along and, for a
    stacked pair, the avenue it crosses. Both are kept, keyed by axis, and
    the caller asks for the axis the seam's own geometry calls for.
    """
    out = {}
    cdir = os.path.join(r.dir, "controls")
    for f in sorted(os.listdir(cdir)):
        m = re.match(r"pair_([0-9]+[a-z]?)_([0-9]+[a-z]?)(?:_[xy])?\.json$", f)
        if not m:
            continue
        try:
            d = json.load(open(os.path.join(cdir, f)))
        except Exception:
            continue
        if "a_native" not in d or str(d.get("status", "")).upper() != "ACCEPTED":
            continue
        ua, ub = m.group(1).lstrip("0"), m.group(2).lstrip("0")
        if ua not in r.units or ub not in r.units:
            continue
        vert = str(d.get("axis", "")).lower().startswith("av")
        pos = []
        for uid, nat in ((ua, d["a_native"]), (ub, d["b_native"])):
            M, t = r.sheet_matrix(uid)
            e = r.units[uid]["extent"]
            p = M @ (np.array([float(nat), (e[1] + e[3]) / 2]) if vert
                     else np.array([(e[0] + e[2]) / 2, float(nat)])) + t
            pos.append(float(p[0] if vert else p[1]))
        out.setdefault((ua, ub), {})["x" if vert else "y"] = (
            float(np.mean(pos)), d.get("corridor", "?"))
    return out


_gray = {}


def gray(r, u):
    """Grey working image, cached (a handful at a time)."""
    if u not in _gray:
        import cv2
        if len(_gray) > 24:
            _gray.pop(next(iter(_gray)))
        _gray[u] = cv2.imread(r.fetch(r.sheet_file(u)), 0)
    return _gray[u]


DP_SCALE = 4           # mosaic px per cost cell (0.69 ft)
DP_HALF = 320.0        # px either side of the control line the path may wander
DP_PULL = 0.2          # cost per cell of distance from the control line (ink is 0-255)
DP_DILATE = 13         # cells (~52 mosaic px, 9 ft): merges lettering and both plates' copies of it
DP_SIDE = 120.0        # px: side candidates run between the lot-number column at the block face and the street name at the centre

# --- blank-band ownership (HQ P1-2) --------------------------------------
# The visible-ink sort below asks which candidate leaves less ink showing. It
# is the right question only when both plates DRAW the band. Where one plate
# has run past its own rule and prints blank paper while the other draws the
# street in detail, "least visible ink" hands the band to the blank plate and
# the detail is buried under paper. So: measure each plate's own ink inside
# the band first; if one plate has essentially none, the band belongs to the
# other plate outright and the cut is pinned at the blank plate's own band
# edge, bypassing the sort.
# DEFAULT OFF. The rule is implemented and tested (see band_ink and the fourth
# candidate below), but on this recipe it fires on exactly one of 172 min-ink
# seams -- 5b|11 -- and that firing is wrong: plate 11 draws the Wharf Co's
# terminal yard (blocks 744-746, Ave A or Water St) in full detail there. The
# 0.13 ratio comes from the +-DP_HALF strip the control happens to sit in, at
# the extreme west edge of 11, where 11 has only open yard and track while 5b
# has the shed outline and its hatching; the pinned candidate then reassigns
# the WHOLE 2,714 px (468 ft) overlap, moving 16.5M px2 from 11 to 5b and
# opening 764k px2 of new unclaimed ground. And the two pairs the rule was
# written for do not need it: at 94|95 and 13|14 BOTH plates draw the corridor
# (both print "AVENUE N1/2"; both draw the 6" W. PIPE run), ratios 0.55 and
# 0.93. Enable with --blank-band only for a seam where the blank strip has
# been confirmed on the native scan to lie beyond that plate's own rule.
BLANK_BAND = False     # --blank-band turns the rule on; --no-blank-band is explicit off
BLANK_RATIO = 0.20     # blank if one plate's band ink < this * the other's
BLANK_FLOOR = 25.0     # grey levels below the plate's own paper tone that count as ink
BLANK_PAPER_PCT = 80   # percentile of the band's greys taken as that plate's paper tone
DP_HALF_BLANK = 4000.0 # the pinned candidate may need the whole overlap, not DP_HALF
DP_BLANK_PULL = 25.0   # per cell: holds the pinned path on the band edge, but still
                       # lets it step round a building rather than slice it

# --- wave-4 cut-placement options (ALL DEFAULT OFF) ----------------------
# Four recurring cut-placement defects were traced to four distinct causes in
# the wave-4 regrade (outputs/1912/qc/wave4/proposal_cuts.md). Each cause gets
# one switch, so the orchestrator can run --dump-cuts with and without and
# diff with tools/cutdiff.py. Nothing below changes the cut unless its flag is
# passed; with no flags this file reproduces the accepted build byte for byte.

# 1. LINE AVOIDANCE. A water main is drawn ALONG the street centreline, which
#    is exactly where a control or midpoint puts the seam. Two failure modes
#    follow. (a) The cut runs along the main and shears it (63|71: plate 63's
#    10" W. PIPE erased over 165 ft). (b) The two plates draw the same main a
#    registration error apart and the cut threads BETWEEN the two copies, so
#    each copy lands on the side owned by the plate that does not draw it and
#    the main disappears from both (64|72: copies 25 px = 4.3 ft apart, the
#    cut at their midpoint). DP_DILATE spreads ink isotropically, which cannot
#    tell these apart: it is symmetric in "along" and "across". This term is
#    deliberately ANISOTROPIC -- each plate's ink is dilated only ACROSS the
#    seam, by LINE_AVOID_K px -- so a path that runs parallel to a drawn line
#    pays at every cell of the run, while a path that crosses it pays only the
#    few cells of the crossing. Riding a line, and threading between two
#    copies of one, both become expensive; crossing one stays cheap.
LINE_AVOID = 0.0       # --line-avoid W: weight (0 = off). 1.0 is one grey level
                       # of either plate's ink per cell of parallel running
LINE_AVOID_K = 36.0    # px across the seam; 6.2 ft, wider than the largest
                       # same-feature registration split measured (64|72, 4.3 ft)

# 2. CANDIDATE CHOICE. `sides` is preferred over `centre` whenever ONE side
#    candidate is feasible, whatever it scores. Where the band is narrow the
#    forbidden half-plane makes one side infeasible, so the surviving side
#    wins by default -- at 20|20b and 25|25b it is worse than the centre on
#    BOTH visible ink and crossed ink and still wins, which is what keeps a
#    plate-20 "AVENUE" fragment beside the inset's complete label and the
#    parent's duplicate 80' tick beside 25b's. With this on, every feasible
#    candidate (centre included) is scored and the best is taken.
PICK_BEST = False      # --pick-best: score every candidate on visible ink.
                       # DIAGNOSTIC ONLY -- it moves 115 of 171 shared seams and
                       # reverts the side preference at 57|58 (+8.7% visible) and
                       # 76|84 (+1.3%), the two pairs the rule was written for, so
                       # `visible` is evidently not the quantity the side rule
                       # optimises. Use --panel-centre for the real defect.
# 2b. PANEL SEAMS. The side rule exists to hide one of TWO PLATES' copies of a
#     street name. A parent and its own detached inset are not two plates: they
#     are one scan, and the strip of parent beside the panel is duplicated
#     content by construction, not a second observation. At 20|20b and 25|25b
#     the band is narrow enough (243 px, 860 px) that one side is infeasible,
#     so the surviving side wins unopposed and hands the parent a 110-120 px
#     strip -- exactly the strip carrying plate 20's "AVENUE" and the parent's
#     second 80' tick. With this on, a parent|panel pair takes the centre
#     candidate unless a side beats it on visible ink.
PANEL_CENTRE = False   # --panel-centre
# 2c. PANEL CLAMP. Even the centre candidate jags across the corridor to get
#     round the panel's own lettering: at 20|20b it reaches x 15425, 118 px
#     east of the control, and the parent's "AVENUE" at x 15340-15400 stays
#     visible beside the inset's complete "AVENUE L.". The two copies are only
#     136 px apart in a 243 px band, so no free path separates them -- but a
#     path CLAMPED to the parent's side of the centreline does. This adds a
#     fourth candidate for a parent|panel pair: the centre line with the
#     panel's side forbidden outright and no margin, i.e. the regrade's
#     "force the path back to mosaic x <= 15311".
PANEL_CLAMP = False    # --panel-clamp

# 3. BAND MASK. dp_cut fills its cost mask from O.exterior only, so an
#    interior ring is harmless but a NOTCH is a wall. A `cut: true` furniture
#    box whose 6 px grow reaches past its plate's own extent cuts a notch
#    through the footprint boundary instead of a hole, and the notch survives
#    into the overlap: 22 of the min-ink seams have columns pinched under
#    100 px that way (88|96 1,172 px of them -- the win_123 "2117" clip).
#    With this on, the band mask is built from FURNITURE-FREE footprints, so
#    the path may route across a furniture box; ownership is unchanged,
#    because each unit's own region already has its furniture removed.
BAND_FURNITURE_FREE = False    # --band-furniture-free

# 4. BAND TEST. `band` requires the overlap to span BAND_FRACTION of the
#    SHORTER SHEET, so a diagonal neighbour pair sharing a full roadway is
#    classed "corner" and gets an axis-aligned half-plane on the corridor
#    coordinate -- straight down the water main. 63|71 (1.15M px2, 406 ft of
#    33rd St) and 64|72 (1.13M px2, 391 ft) are both cut that way. With this
#    set, an overlap that spans at least this many px along the seam is a band
#    seam whatever fraction of the sheet it is, and gets a min-ink path.
MIN_BAND_SPAN = None   # --min-band-span PX (None = off)

# 5. FURNITURE IN THE VISIBLE-INK SCORE. `visible` counts every grey level the
#    same, so a plate's bottom-margin "Scale of Feet" legend scores like the
#    roadway it sits on and the candidate that leaves it showing can still win
#    by a fraction of a percent (63|70: the +120 side wins 13.221M to 13.417M
#    and keeps plate 63's legend and both scan-ruler rectangles in 33rd St).
#    A furniture box is not map content: leaving one visible inside ground the
#    neighbour maps is the defect the whole furniture machinery exists to
#    prevent. With W > 1 those pixels are weighted W times in the score, so a
#    candidate that hands the box to the neighbour wins.
FURN_VISIBLE = 1.0     # --furniture-visible W (1.0 = current behaviour)

def band_ink(g, mask):
    """That plate's own ink inside the band, in grey-levels x cells.

    Not `255 - g`: a Sanborn scan's paper is grey (155-175 here, and darker
    still where the sheet is shadowed), so `255 - g` summed over a band is
    dominated by paper tone and two plates' sums come out within 20% of each
    other whatever is drawn on them. Ink is measured against the plate's own
    paper tone in this band -- the BLANK_PAPER_PCT percentile of its greys,
    which survives a band that is half covered in ink -- so a blank strip
    scores ~0 on any scan and a drawn street scores high on any scan.
    """
    import numpy as np
    m = mask == 1
    if not m.any():
        return 0.0
    vals = g[m].astype(np.float32)
    paper = float(np.percentile(vals, BLANK_PAPER_PCT))
    return float(np.clip(paper - BLANK_FLOOR - vals, 0.0, None).sum())


def dp_cut(r, u, v, axis, coord, O, lower=None, info=None, panel=False):
    """Min-ink path through the shared roadway, as the master's cuts were made.

    A straight centreline cut slices through whatever both plates print at
    the centre of the street -- the street name, the plate number, the
    north arrow -- and the census read the result as ghosted lettering
    (12|14: half of each plate's "27TH ST."). The cut is therefore a path
    that stays inside the roadway band about the control line and crosses
    as little ink as possible on BOTH plates, so it runs between the label
    and the block face and one plate's label survives whole.

    `info`, if given, is filled with what the cut did: the two plates' band
    ink, and a "blank_band" record when the blank-band rule fired.

    Returns a shapely LineString in mosaic px along the seam axis, or None.
    """
    import cv2
    from shapely.geometry import LineString
    if O.geom_type != "Polygon":
        O = max(O.geoms, key=lambda g: g.area)        # a band pinched into parts: cut the main one
    b = O.bounds

    def grid(half):
        """Warp both plates into the band about `coord`, `half` px either side."""
        if axis == "y":
            gx0, gx1 = b[0], b[2]
            gy0, gy1 = max(b[1], coord - half), min(b[3], coord + half)
        else:
            gy0, gy1 = b[1], b[3]
            gx0, gx1 = max(b[0], coord - half), min(b[2], coord + half)
        W, H = int((gx1 - gx0) / DP_SCALE) + 1, int((gy1 - gy0) / DP_SCALE) + 1
        if W < 8 or H < 8:
            return None
        cost = np.zeros((H, W), np.float32)
        raw, grey = {}, {}
        for w_ in (u, v):
            M, t = r.sheet_matrix(w_)
            A = np.hstack([M / DP_SCALE, ((t - np.array([gx0, gy0])) / DP_SCALE).reshape(2, 1)])
            g = cv2.warpAffine(gray(r, w_), A, (W, H), flags=cv2.INTER_AREA, borderValue=255)
            grey[w_] = g
            ink = (255 - g).astype(np.float32)
            raw[w_] = ink.copy()
            # thicken the ink: a street name is letters with gaps, and two plates'
            # copies of it sit a registration error apart; without this the path
            # threads the gap between the copies and both survive (57|58 test).
            # Dilated, the copies merge into one blob the path must go round.
            ink = cv2.dilate(ink, np.ones((DP_DILATE, DP_DILATE), np.uint8))
            cost += cv2.GaussianBlur(ink, (0, 0), 1.5)
        mask = np.zeros((H, W), np.uint8)
        ring = np.array([((px - gx0) / DP_SCALE, (py - gy0) / DP_SCALE)
                         for px, py in np.array(O.exterior.coords)], np.int32)
        cv2.fillPoly(mask, [ring], 1)
        cost = np.where(mask == 1, cost, BIG)
        # line-avoidance field: each plate's ink measured against its OWN paper
        # tone (band_ink's per-pixel quantity, so a grey scan does not read as
        # ink), dilated ONLY across the seam. Built always -- it costs one
        # dilate per plate -- but only charged when LINE_AVOID > 0.
        k = max(1, int(round(LINE_AVOID_K / DP_SCALE)))
        ker = np.ones((2 * k + 1, 1), np.uint8) if axis == "y" else np.ones((1, 2 * k + 1), np.uint8)
        avoid = np.zeros((H, W), np.float32)
        for w_ in (u, v):
            g = grey[w_]
            vals = g[mask == 1]
            paper = float(np.percentile(vals, BLANK_PAPER_PCT)) if vals.size else 255.0
            sig = np.clip(paper - BLANK_FLOOR - g.astype(np.float32), 0.0, None)
            avoid += cv2.dilate(sig, ker)
        avoid = np.where(mask == 1, avoid, 0.0)
        return dict(x0=gx0, y0=gy0, x1=gx1, y1=gy1, W=W, H=H,
                    cost=cost, raw=raw, grey=grey, mask=mask, avoid=avoid)

    G = grid(DP_HALF)
    if G is None:
        return None
    # --- is one plate blank paper across this band? -----------------------
    ink_band = {w_: band_ink(G["grey"][w_], G["mask"]) for w_ in (u, v)}
    blank = min(ink_band, key=ink_band.get)
    drawn = v if blank == u else u
    ratio = ink_band[blank] / ink_band[drawn] if ink_band[drawn] > 0 else 1.0
    is_blank_band = BLANK_BAND and ink_band[blank] < BLANK_RATIO * ink_band[drawn]
    if os.environ.get("DP_DEBUG"):
        print(f"    dp {u}|{v}: band ink {u}={ink_band[u]:,.0f} {v}={ink_band[v]:,.0f} "
              f"ratio {ratio:.3f}{'  BLANK BAND -> ' + drawn if is_blank_band else ''}")
    if is_blank_band:
        # the pinned candidate runs on the blank plate's own edge of the
        # overlap, which is routinely further than DP_HALF from the control
        G = grid(DP_HALF_BLANK) or G
    x0, y0, x1, y1 = G["x0"], G["y0"], G["x1"], G["y1"]
    W, H, cost, raw, mask = G["W"], G["H"], G["cost"], G["raw"], G["mask"]
    avoid = G["avoid"]
    # Three candidate paths: pulled to the control line, and pulled to a line
    # DP_SIDE px either side of it (just inside the block faces). Both plates
    # letter the street name in the roadway; a path that zigzags round each
    # label on its cheaper side leaves both (or neither) showing, whereas a
    # path that keeps to ONE side of the roadway shows exactly one plate's
    # label (76|84 test). Candidates are scored by the ink left VISIBLE in
    # the band (the lower unit's ink on the low side plus the upper unit's
    # on the high side): the block faces and pipes are drawn by both plates
    # and cost the same whichever side shows them, so the difference between
    # candidates is the duplicated lettering, and the candidate that hides
    # one copy wins (57|58, 76|84 tests). Ink the path itself crosses is
    # charged on top so a label is not sliced in half.
    ink_only = cost.copy()
    cands = []
    low_u = lower if lower in (u, v) else u
    high_u = v if low_u == u else u
    inkL = np.where(mask == 1, raw[low_u], 0.0)
    inkH = np.where(mask == 1, raw[high_u], 0.0)
    if FURN_VISIBLE != 1.0:
        # weight each plate's OWN furniture boxes in the visible-ink score
        from shapely.affinity import affine_transform
        from shapely.geometry import box as _sbox
        for w_, arr in ((low_u, inkL), (high_u, inkH)):
            src = r.units[w_]
            if src.get("panel_of"):
                src = r.units[str(src["panel_of"])]
            M, t = r.sheet_matrix(w_ if not r.units[w_].get("panel_of")
                                  else str(r.units[w_]["panel_of"]))
            for f in src.get("furniture_native") or []:
                bx = f["box"]
                gbox = affine_transform(_sbox(bx[0], bx[1], bx[2], bx[3]),
                                        [M[0, 0], M[0, 1], M[1, 0], M[1, 1], t[0], t[1]])
                pts = np.array([((px - x0) / DP_SCALE, (py - y0) / DP_SCALE)
                                for px, py in np.array(gbox.exterior.coords)], np.int32)
                fm = np.zeros_like(mask)
                cv2.fillPoly(fm, [pts], 1)
                arr *= np.where(fm == 1, FURN_VISIBLE, 1.0).astype(arr.dtype)
    if axis != "y":
        inkL, inkH = inkL.T, inkH.T          # rows = across the seam, cols = along it
    cumL = np.cumsum(inkL, axis=0)           # low-side ink up to and including row y
    totH = inkH.sum(axis=0)
    cumH = np.cumsum(inkH, axis=0)
    CROSS_W = 8.0                            # a crossed cell counts like an 8-cell column of visible ink
    # the band is the plates' overlap, often narrower than the roadway once
    # footprints stop at the neatline (57|58 overlap by 21 ft): keep the side
    # targets inside it
    across = (y1 - y0) if axis == "y" else (x1 - x0)
    side = min(DP_SIDE, max(0.0, across / 2.0 - 3 * DP_SCALE))
    margin = min(40.0, 0.5 * side)     # px: a side path never comes nearer the centreline than this

    def candidate(target, pull_k, forbid, margin_px=None):
        """DP path pulled towards `target`; `forbid` bans one side of the
        centreline outright ('low' = everything below coord - margin)."""
        c = ink_only.copy()
        if LINE_AVOID:
            c = c + LINE_AVOID * avoid
        across_px = (y0 + np.arange(H) * DP_SCALE) if axis == "y" else (x0 + np.arange(W) * DP_SCALE)
        pull = pull_k * np.abs((across_px - target) / DP_SCALE)
        m_ = margin if margin_px is None else margin_px
        if forbid == "low":
            pull = pull + np.where(across_px < coord + m_, BIG, 0.0)
        elif forbid == "high":
            pull = pull + np.where(across_px > coord - m_, BIG, 0.0)
        if axis == "y":
            c += pull[:, None]
        else:
            c += pull[None, :]
            c = c.T                                   # march along the seam
        Hc, Wc = c.shape
        dp = c.copy()
        back = np.zeros_like(dp, np.int8)
        for x in range(1, Wc):
            prev = dp[:, x - 1]
            st = np.vstack([np.roll(prev, 1), prev, np.roll(prev, -1)])
            st[0, 0] = BIG * 2
            st[2, -1] = BIG * 2
            ch = st.argmin(axis=0)
            dp[:, x] += st[ch, np.arange(Hc)]
            back[:, x] = ch - 1
        yend = int(dp[:, -1].argmin())
        path = [yend]
        for x in range(Wc - 1, 0, -1):
            path.append(min(Hc - 1, max(0, int(path[-1]) + int(back[path[-1], x]))))
        path = path[::-1]
        io = ink_only if axis == "y" else ink_only.T
        av = avoid if axis == "y" else avoid.T
        ink_sum = float(sum(io[y, x] for x, y in enumerate(path)))
        avoid_sum = float(sum(av[y, x] for x, y in enumerate(path)))
        cols = np.arange(len(path)); rows = np.array(path)
        visible = float(cumL[rows, cols].sum() + (totH[cols] - cumH[rows, cols]).sum())
        return ink_sum, visible, path, avoid_sum

    for off in (0.0, -side, side):
        # a side path is only worth having if it really keeps to its side:
        # with the pull alone it drifted back through the lettering strip
        # wherever the ink was thinner there (76|84). Forbid the far side
        # of the centreline and its margin outright.
        forbid = None if off == 0.0 else ("high" if off < 0 else "low")
        ink_sum, visible, path, avoid_sum = candidate(coord + off, DP_PULL, forbid)
        if os.environ.get("DP_DEBUG"):
            print(f"    dp {u}|{v} off {off:+6.1f}: visible {visible:12.0f} "
                  f"crossed {ink_sum:9.0f} along-line {avoid_sum:11.0f}")
        cands.append((off, ink_sum, visible, path, avoid_sum))
    # The centreline candidate weaves round each plate's label on its cheaper
    # side and so crosses the least ink while leaving BOTH labels showing
    # (76|84: the two '39TH ST' are 800 px apart along the street). A side
    # candidate keeps to one side of the lettering strip, so one plate's
    # label is hidden under the other's ownership. Prefer the side that
    # crosses less ink; take the centreline only when both side paths cut
    # through far more ink (a band that is not a roadway) or the band is too
    # narrow for a side path to clear the centre strip.
    centre = cands[0]
    # between the two sides, the one leaving less ink visible in the band
    # is the one whose hidden copy of the lettering was the larger
    sides = [c for c in cands[1:] if c[1] < BIG / 4 and c[1] <= 2.0 * centre[1] + 1.0]
    sides.sort(key=lambda c: c[2])
    if PANEL_CLAMP and panel:
        # the parent keeps the low side when it is the lower unit
        parent = u if r.units[v].get("panel_of") == u else v
        forbid = "high" if parent == low_u else "low"
        ink_sum, visible, path, avoid_sum = candidate(coord, DP_PULL, forbid, margin_px=0.0)
        if ink_sum < BIG / 4:
            cands.append((0.0, ink_sum, visible, path, avoid_sum))
            sides = sides + [cands[-1]]
            sides.sort(key=lambda c: c[2])
        if os.environ.get("DP_DEBUG"):
            print(f"    dp {u}|{v} panel clamp ({forbid} forbidden at margin 0): "
                  f"visible {visible:12.0f} crossed {ink_sum:9.0f}")
    if PANEL_CENTRE and panel and not PICK_BEST:
        # a panel and its parent are one scan: prefer a side only if it really
        # leaves less ink showing than the centre does
        sides = [c for c in sides if c[2] <= centre[2]]
    if PICK_BEST:
        # score every feasible candidate, the centre included, on the same
        # ruler: ink left visible in the band, plus what the path pays for
        # running along a drawn line when that term is on. The old rule took
        # a side whenever one was feasible, so where the band's width made
        # the other side infeasible the survivor won unopposed.
        feas = [c for c in cands if c[1] < BIG / 4]
        best = min(feas, key=lambda c: c[2] + LINE_AVOID * c[4]) if feas else centre
    elif side >= 40.0 and sides:
        best = sides[0]
    else:
        best = centre
    if is_blank_band:
        # fourth candidate: pinned at the blank plate's own edge of the band,
        # so the blank plate keeps none of it and the plate that draws the
        # street owns the whole band. Selected outright -- the visible-ink
        # sort has nothing to say about a band only one plate draws.
        k = 0 if axis == "x" else 1
        edge = (x0 if axis == "x" else y0) if blank == low_u else (x1 if axis == "x" else y1)
        ink_sum, visible, path, avoid_sum = candidate(edge, DP_BLANK_PULL, None)
        cands.append((edge - coord, ink_sum, visible, path, avoid_sum))
        best = cands[-1]
        if info is not None:
            info["blank_band"] = {"winner": drawn, "ink_ratio": round(ratio, 4)}
        if os.environ.get("DP_DEBUG"):
            print(f"    dp {u}|{v} blank {blank} -> pinned at {'x' if axis=='x' else 'y'}="
                  f"{edge:.0f} (off {edge-coord:+.0f}): visible {visible:12.0f} crossed {ink_sum:9.0f}")
    if info is not None:
        info["band_ink"] = {u: round(ink_band[u]), v: round(ink_band[v])}
        info["ink_ratio"] = round(ratio, 4)
        info["off"] = round(float(best[0]), 1)
        info["candidates"] = [{"off": round(float(c[0]), 1),
                               "crossed": round(c[1], 1),
                               "visible": round(c[2], 1),
                               "along_line": round(c[4], 1),
                               "feasible": bool(c[1] < BIG / 4),
                               "chosen": c is best} for c in cands]
    if os.environ.get("DP_DEBUG"):
        print(f"    dp {u}|{v}: chose off {best[0]:+.0f} (side {side:.0f})"
              f"{' [blank-band]' if is_blank_band else ''}")
    path = best[3]
    pts = []
    for x, y in enumerate(path):
        if axis == "y":
            pts.append((x0 + x * DP_SCALE, y0 + y * DP_SCALE))
        else:
            pts.append((x0 + y * DP_SCALE, y0 + x * DP_SCALE))
    # extend straight past both ends so the side polygons close cleanly
    c = np.array(pts, float)
    d0 = c[0] - c[1]
    d1 = c[-1] - c[-2]
    d0 /= (np.linalg.norm(d0) + 1e-9)
    d1 /= (np.linalg.norm(d1) + 1e-9)
    c = np.vstack([c[0] + d0 * 20000, c, c[-1] + d1 * 20000])
    return LineString(c).simplify(1.0)


def side_polygons(line, axis):
    """(low_side, high_side) polygons split by the extended path."""
    from shapely.geometry import Polygon
    c = np.array(line.coords)
    if axis == "y":
        low = Polygon(np.vstack([c, [[c[-1][0], -BIG], [c[0][0], -BIG]]]))
        high = Polygon(np.vstack([c, [[c[-1][0], BIG], [c[0][0], BIG]]]))
    else:
        low = Polygon(np.vstack([c, [[-BIG, c[-1][1]], [-BIG, c[0][1]]]]))
        high = Polygon(np.vstack([c, [[BIG, c[-1][1]], [BIG, c[0][1]]]]))
    return low.buffer(0), high.buffer(0)


def half_plane(axis, coord, keep_low):
    from shapely.geometry import box
    if axis == "x":
        return box(-BIG, -BIG, coord, BIG) if keep_low else box(coord, -BIG, BIG, BIG)
    return box(-BIG, -BIG, BIG, coord) if keep_low else box(-BIG, coord, BIG, BIG)


def lattice_coord(r, lat, u, axis, mid_xy):
    """Mosaic coordinate on `axis` of the lattice corridor of unit u nearest
    the mosaic point mid_xy, read through u's transform at that point."""
    L = (lat.get(u) or {}).get(axis)
    if not L or not L.get("faces") or L.get("weak"):
        return None
    M, t = r.sheet_matrix(u)
    Minv = np.linalg.inv(M)
    nat = Minv @ (np.array(mid_xy, float) - t)
    k = 0 if axis == "x" else 1
    best = None
    # only corridors whose faces were measured on the plate: the corridor
    # extrapolated one pitch past the chain was 100 px off on sheet 71
    for c in [(fa + fb) / 2.0 for fa, fb in L["faces"]]:
        q = nat.copy()
        q[k] = c
        p = M @ q + t
        if best is None or abs(p[k] - mid_xy[k]) < abs(best - mid_xy[k]):
            best = float(p[k])
    return best


def main():
    global LINE_AVOID, LINE_AVOID_K, PICK_BEST, PANEL_CENTRE
    global BAND_FURNITURE_FREE, MIN_BAND_SPAN, FURN_VISIBLE, PANEL_CLAMP
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", required=True, choices=["1912"])
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--debug-unit", default=None)
    ap.add_argument("--straight", action="store_true",
                    help="straight centreline cuts instead of min-ink paths")
    ap.add_argument("--pull", type=float, default=None,
                    help="override DP_PULL (cost per cell of distance from the control line)")
    ap.add_argument("--blank-band", dest="blank_band", action="store_true", default=None,
                    help="enable the blank-band ownership rule (default off; see BLANK_BAND)")
    ap.add_argument("--no-blank-band", dest="blank_band", action="store_false",
                    help="explicitly disable the blank-band ownership rule")
    ap.add_argument("--dump-cuts", default=None, metavar="PATH",
                    help="write every pair's cut line to PATH as JSON, so two runs "
                         "can be diffed with tools/cutdiff.py")
    ap.add_argument("--out", default=None, metavar="PATH",
                    help="where to write the ownership document (default "
                         "recipe/seams/ownership_streetcut.json); --apply still "
                         "writes ownership_city.json")
    ap.add_argument("--line-avoid", dest="line_avoid", type=float, default=None,
                    metavar="W", help="penalise a path for running ALONG either "
                    "plate's ink (weight W; default 0 = off). See LINE_AVOID")
    ap.add_argument("--line-avoid-k", dest="line_avoid_k", type=float, default=None,
                    metavar="PX", help=f"half-width across the seam of the "
                    f"line-avoidance field (default {LINE_AVOID_K:.0f} px)")
    ap.add_argument("--furniture-visible", dest="furn_visible", type=float,
                    default=None, metavar="W",
                    help="weight a plate's own furniture-box pixels W times in "
                         "the visible-ink score (default 1.0 = off)")
    ap.add_argument("--panel-clamp", dest="panel_clamp", action="store_true",
                    help="at a parent|panel seam, add a candidate clamped to "
                         "the parent's side of the centreline")
    ap.add_argument("--panel-centre", dest="panel_centre", action="store_true",
                    help="at a parent|panel seam, prefer a side candidate only "
                         "when it beats the centre on visible ink")
    ap.add_argument("--pick-best", dest="pick_best", action="store_true",
                    help="choose the best of centre and the feasible side "
                         "candidates on the visible-ink score, instead of "
                         "preferring a side whenever one is feasible")
    ap.add_argument("--band-furniture-free", dest="band_ff", action="store_true",
                    help="build the DP band mask from furniture-free footprints, "
                         "so a furniture notch cannot pinch the corridor")
    ap.add_argument("--min-band-span", dest="min_band_span", type=float,
                    default=None, metavar="PX",
                    help="an overlap spanning at least this many px along the "
                         "seam is a band seam (min-ink path) whatever fraction "
                         "of the sheet it is; default off")
    ap.add_argument("--cand-dump", default=None, metavar="PATH",
                    help="write every min-ink seam's candidate costs (off, "
                         "crossed, visible, along-line, chosen) to PATH as JSON")
    a = ap.parse_args()
    if a.line_avoid is not None:
        LINE_AVOID = a.line_avoid
    if a.line_avoid_k is not None:
        LINE_AVOID_K = a.line_avoid_k
    PICK_BEST = bool(a.pick_best)
    PANEL_CENTRE = bool(a.panel_centre)
    PANEL_CLAMP = bool(a.panel_clamp)
    if a.furn_visible is not None:
        FURN_VISIBLE = a.furn_visible
    BAND_FURNITURE_FREE = bool(a.band_ff)
    MIN_BAND_SPAN = a.min_band_span
    if a.blank_band is not None:
        global BLANK_BAND
        BLANK_BAND = a.blank_band
    if a.pull is not None:
        global DP_PULL
        DP_PULL = a.pull

    from shapely.geometry import Polygon
    from shapely.ops import unary_union

    r = Recipe(int(a.year))
    ppf = px_per_ft(r)
    cuts = load_cuts(r)
    lat = lattice_all(r)
    print(f"{sum(len(v) for v in cuts.values())} accepted controls over "
          f"{len(cuts)} pairs; lattices for "
          f"{sum(1 for u in lat if lat[u].get('y') and lat[u].get('x'))} units",
          flush=True)

    def foot(u):
        # neatline-trimmed extent, minus inset frames; a panel's own region
        return r.footprint(u)

    feet = {u: foot(u) for u in r.units}
    cen = {u: np.array([feet[u].centroid.x, feet[u].centroid.y]) for u in feet}
    # the same footprints with the furniture boxes left in: the ground each
    # scan actually holds. Only the DP band mask uses these (--band-furniture-
    # free); ownership is still differenced against `base`, whose furniture is
    # already gone, so the boxes stay out of the mosaic either way.
    feet_nf = {u: r.footprint(u, furniture=False).buffer(0) for u in r.units} \
        if BAND_FURNITURE_FREE else {}
    for u, g in list(feet_nf.items()):
        if g.geom_type != "Polygon":
            feet_nf[u] = max(g.geoms, key=lambda p: p.area)

    # the accepted core: its own DP cuts are the base, not the paper quad
    core = {}
    mp = os.path.join(r.dir, "seams", "masks.json")
    if os.path.exists(mp):
        for reg in json.load(open(mp))["regions"]:
            u = str(reg.get("unit", reg.get("sheet")))
            if u in feet:
                core[u] = Polygon(reg["polygon_mosaic"]["exterior"]).buffer(0)
    # the core keeps the master's own cut lines, but still inside this
    # recipe's footprint: the neatline trim and the furniture boxes apply to
    # a core plate as much as to a ring plate (plates 12, 14 and 49 printed
    # their Scale of Feet legends in the street because the core base bypassed
    # footprint() entirely).
    base = {u: (core[u].intersection(feet[u]).buffer(0) if u in core else feet[u])
            for u in feet}
    for u, g in list(base.items()):
        if g.geom_type != "Polygon":
            base[u] = max(g.geoms, key=lambda p: p.area)
    print(f"core base from masks.json: {sorted(core, key=int)}", flush=True)
    base_nf = {u: (core[u].intersection(feet_nf[u]).buffer(0) if u in core else feet_nf[u])
               for u in feet_nf}
    for u, g in list(base_nf.items()):
        if g.geom_type != "Polygon":
            base_nf[u] = max(g.geoms, key=lambda p: p.area)

    units = sorted(feet, key=lambda k: int("".join(c for c in k if c.isdigit())))
    seams, loss, cutlines, cand_rows = [], {u: [] for u in units}, [], []
    stats = {"control": 0, "lattice": 0, "midpoint": 0, "core-core": 0, "dp": 0}
    for i, u in enumerate(units):
        for v in units[i + 1:]:
            if not base[u].intersects(base[v]):
                continue
            O = base[u].intersection(base[v])
            if O.area < MIN_OVERLAP:
                continue
            if u in core and v in core:
                stats["core-core"] += 1       # already partitioned by the master
                continue
            d = cen[v] - cen[u]
            axis = "x" if abs(d[0]) >= abs(d[1]) else "y"
            # a unit may say which way its seams run: the wharf panels are
            # tall strips whose centres sit far from the core plates' in y,
            # yet every seam with a core plate is the frontage line (x)
            for a_, b_ in ((u, v), (v, u)):
                sa = r.units[a_].get("seam_axis")
                if isinstance(sa, dict):
                    axis = sa.get(b_, sa.get("default", axis))
            k = 0 if axis == "x" else 1
            b = O.bounds
            span = (b[3] - b[1]) if axis == "x" else (b[2] - b[0])
            across = min(feet[u].bounds[3] - feet[u].bounds[1],
                         feet[v].bounds[3] - feet[v].bounds[1]) if axis == "x" else \
                     min(feet[u].bounds[2] - feet[u].bounds[0],
                         feet[v].bounds[2] - feet[v].bounds[0])
            band = span >= BAND_FRACTION * across or (
                MIN_BAND_SPAN is not None and span >= MIN_BAND_SPAN)
            mid = np.array([(b[0] + b[2]) / 2, (b[1] + b[3]) / 2])
            key = (u, v) if (u, v) in cuts else ((v, u) if (v, u) in cuts else None)
            got = cuts[key].get(axis) if key else None
            how, corridor, resid = None, None, None
            if got:
                coord, corridor = got
                how = "control"
            else:
                cu = lattice_coord(r, lat, u, axis, mid) if band else None
                cv = lattice_coord(r, lat, v, axis, mid) if band else None
                if cu is not None and cv is not None:
                    coord = (cu + cv) / 2.0
                    resid = abs(cu - cv)
                    how = "lattice"
                else:
                    coord = float(mid[k])
                    how = "midpoint"
            stats[how] += 1
            lower = u if cen[u][k] < cen[v][k] else v
            upper = v if lower == u else u
            path, info = None, {}
            if band and not a.straight:
                O_band = O
                if BAND_FURNITURE_FREE:
                    q = base_nf[u].intersection(base_nf[v])
                    if not q.is_empty and q.area >= O.area:
                        O_band = q
                try:
                    panel = (r.units[u].get("panel_of") == v
                             or r.units[v].get("panel_of") == u)
                    path = dp_cut(r, u, v, axis, coord, O_band, lower,
                                  info=info, panel=panel)
                except Exception as ex:          # fall back to the straight line
                    print(f"  dp cut failed on {u}|{v}: {ex}", flush=True)
            if path is not None:
                low_side, high_side = side_polygons(path, axis)
                loss[lower].append(O.intersection(high_side))
                loss[upper].append(O.intersection(low_side))
                stats["dp"] += 1
            else:
                loss[lower].append(O.intersection(half_plane(axis, coord, False)))
                loss[upper].append(O.intersection(half_plane(axis, coord, True)))
            seams.append({"pair": [u, v], "axis": axis, "coord": round(coord, 2),
                          "cut": "min-ink path" if path is not None else "straight",
                          "how": how, "corridor": corridor, "kind": "band" if band else "corner",
                          "overlap_px2": round(O.area), "span_px": round(span),
                          "lattice_disagreement_px": None if resid is None else round(resid, 1),
                          "lattice_disagreement_ft": None if resid is None else round(resid / ppf, 1)})
            if "blank_band" in info:
                seams[-1]["blank_band"] = info["blank_band"]
                print(f"  blank band {u}|{v}: ink ratio "
                      f"{info['blank_band']['ink_ratio']:.3f}, whole band to "
                      f"{info['blank_band']['winner']}", flush=True)
            if path is not None and info.get("candidates"):
                cand_rows.append({"pair": [u, v], "axis": axis,
                                  "coord": round(coord, 2), "how": how,
                                  "band_ink": info.get("band_ink"),
                                  "candidates": info["candidates"]})
            if path is not None:
                cutlines.append({"pair": [u, v], "axis": axis,
                                 "coord": round(coord, 2),
                                 "blank_band": info.get("blank_band"),
                                 "ink_ratio": info.get("ink_ratio"),
                                 "off": info.get("off"),
                                 "line": [[round(x, 1), round(y, 1)] for x, y in
                                          (np.array(path.coords)[1:-1]
                                           if len(path.coords) >= 4
                                           else np.array(path.coords))]})

    regions, dropped = {}, []
    for u in units:
        g = base[u]
        if u == a.debug_unit:
            print(f"debug {u}: base {g.area:,.0f}; losses "
                  f"{[round(l.area) for l in loss[u]]}")
        if loss[u]:
            g = g.difference(unary_union(loss[u]))
            if u == a.debug_unit:
                print(f"debug {u}: after difference {g.geom_type} {g.area:,.0f}")
        if g.is_empty:
            continue
        # a difference can leave a notch attached to the ring at a single
        # point, which GEOS represents as a hole touching the exterior; a
        # 1 px opening turns every such contact into a proper notch, so it
        # cannot come back as double ownership (77|84, 1.9M px2, first run).
        g = g.buffer(-1.0).buffer(1.0)
        if g.geom_type != "Polygon":
            parts = sorted(g.geoms, key=lambda p: -p.area)
            g = parts[0]
            dropped += [(u, round(p.area)) for p in parts[1:] if p.area > MIN_OVERLAP]
        assert g.is_valid, u
        regions[u] = g

    print(f"seams: {stats['control']} on a control, {stats['lattice']} on the "
          f"plates' lattice, {stats['midpoint']} at the overlap midpoint "
          f"(corner contacts); {stats['dp']} cut on a min-ink path; "
          f"{stats['core-core']} core-core pairs kept the master's cuts", flush=True)
    res = [s["lattice_disagreement_ft"] for s in seams if s["lattice_disagreement_ft"] is not None]
    if res:
        print(f"lattice seams: the two plates' readings of the shared corridor "
              f"disagree by median {np.median(res):.1f} ft, 90th "
              f"{np.percentile(res, 90):.1f}, max {max(res):.1f}")
        for s in sorted(seams, key=lambda s: -(s["lattice_disagreement_ft"] or 0))[:8]:
            if s["lattice_disagreement_ft"]:
                print(f"    {s['pair'][0]}|{s['pair'][1]} {s['axis']} "
                      f"{s['lattice_disagreement_ft']:.0f} ft")
    if dropped:
        print(f"detached slivers dropped (become gaps for fillgaps): {dropped}")
    nb = [s_ for s_ in seams if s_.get("blank_band")]
    print(f"blank-band rule: {'off' if not BLANK_BAND else 'on'}, fired on "
          f"{len(nb)} of {stats['dp']} min-ink seams"
          + ("" if not nb else ": " + ", ".join(
              f"{s_['pair'][0]}|{s_['pair'][1]}->{s_['blank_band']['winner']}"
              f" ({s_['blank_band']['ink_ratio']:.2f})" for s_ in nb)))
    if a.dump_cuts:
        json.dump({"generated_by": "tools/streetcut.py --dump-cuts",
                   "blank_band_rule": BLANK_BAND,
                   "note": ("one entry per pair cut on a min-ink path; `line` is the "
                            "path in mosaic px BEFORE the straight extension at both "
                            "ends; diff two dumps with tools/cutdiff.py"),
                   "cuts": cutlines}, open(a.dump_cuts, "w"), indent=1)
        print(f"wrote {a.dump_cuts} ({len(cutlines)} cut lines)")
    if a.cand_dump:
        json.dump({"generated_by": "tools/streetcut.py --cand-dump",
                   "options": {"line_avoid": LINE_AVOID, "line_avoid_k": LINE_AVOID_K,
                               "pick_best": PICK_BEST,
                               "band_furniture_free": BAND_FURNITURE_FREE,
                               "min_band_span": MIN_BAND_SPAN,
                               "blank_band": BLANK_BAND},
                   "note": ("one row per min-ink seam: the three (or four) DP "
                            "candidates with the ink each leaves VISIBLE in the "
                            "band, the ink the path CROSSES, and what it pays for "
                            "running ALONG either plate's ink"),
                   "seams": cand_rows}, open(a.cand_dump, "w"), indent=1)
        print(f"wrote {a.cand_dump} ({len(cand_rows)} candidate rows)")

    un = unary_union(list(regions.values()))
    s = sum(g.area for g in regions.values())
    holes = sum(1 for p in getattr(un, "geoms", [un]) for _ in p.interiors)
    print(f"{len(regions)} regions; union {un.area:,.0f} px2, "
          f"overlap {s-un.area:,.0f} px2 ({(s-un.area)/un.area*100:.4f}%), "
          f"pieces {len(getattr(un,'geoms',[un]))}, interior rings {holes}")

    doc = {"convention": "polygon_mosaic.exterior (and .interiors, the ground the unit does not own inside its own ring -- a furniture box a neighbour supplies) in mosaic pixels",
           "generated_by": "tools/streetcut.py",
           "note": ("core = the master's DP masks; ring seams on the control's "
                    "corridor, else on the plates' lattice corridor, else the "
                    "overlap midpoint; each sheet trimmed only inside its "
                    "overlap with the neighbour (§2.5)"),
           "seams": seams,
           "regions": [{"unit": u,
                        "source": "master DP mask" if u in core else "street-centreline cut",
                        "polygon_mosaic": {
                            "exterior": [[round(x, 3), round(y, 3)] for x, y in g.exterior.coords],
                            "interiors": [[[round(x, 3), round(y, 3)] for x, y in r_.coords]
                                          for r_ in g.interiors]}}
                       for u, g in sorted(regions.items(),
                                          key=lambda kv: (int("".join(c for c in kv[0] if c.isdigit())), kv[0]))]}
    p = a.out or os.path.join(r.dir, "seams", "ownership_streetcut.json")
    json.dump(doc, open(p, "w"), indent=1)
    print(f"wrote {p}")
    if a.apply:
        tgt = os.path.join(r.dir, "seams", "ownership_city.json")
        json.dump(doc, open(tgt, "w"), indent=1)
        print(f"applied to {tgt}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
