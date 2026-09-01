#!/usr/bin/env python3
"""Find each plate's neatline (border rule) so footprints cover map area only.

    python3 tools/neatline.py --year 1912 [--apply] [--units 57 58]

A Sanborn plate prints its map inside a thin border rule; outside it sit the
adjoining-sheet brackets, plate furniture and bare paper. The city footprints
used the whole scan minus 40 px, so wherever a centreline cut landed near a
plate edge, that plate's margin -- rule, brackets, numbers -- entered the
mosaic (HQ-19 defect 1). This measures the rule on all four sides of every
working image and records the inner edge as the unit's `extent`; the old
extent is kept as `extent_scan`. Geometry only; no pixel is altered.

Method per side: dark-pixel fraction per column (or row) over the middle 60%
of the plate, within the outer band. The rule is the innermost column whose
dark fraction says it runs nearly the whole plate; +INSET px puts the extent
just inside it. Sides where no rule is found keep the old value and are
listed, so they can be checked by eye.
"""
import argparse, json, os, sys
import numpy as np
import cv2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from reciplib import Recipe  # noqa: E402

BAND = 180        # px from the scan edge to search
MINFRAC = 0.55    # a rule spans at least this fraction of the mid-plate
INSET = 4         # px inside the rule's inner edge
MAXIN = 95        # a rule further in than this from the paper edge is not the rule
FALLBACK = 50     # paper edge + this where the rule is faint or absent
DARK = 140        # grey level below which a pixel is ink


NSEG = 12         # segments along each side (handles a few px of skew)
SEGFRAC = 0.6     # a rule fills at least this much of a segment
MINHITS = 0.6    # ... in at least this fraction of the segments


def find_rule(gray, side):
    """Inner edge of the border rule on one side (px from that scan edge), or None.

    The scan carries a grey scanner border, the paper edge, ~40 px of bare
    paper, then the thin rule. The rule wobbles a few px along its length
    (paper, not skew), so it is found per segment and chained with a
    tolerance; the extent takes the innermost position so the footprint is
    inside the rule everywhere. Brackets and numerals sit inside the rule and
    are short, so a chain that runs most of the side is the rule, not them.
    """
    if side == "right":
        gray = gray[:, ::-1]
    elif side == "bottom":
        gray = gray[::-1, :]
    if side in ("top", "bottom"):
        gray = gray.T
    H, W = gray.shape
    lo, hi = int(H * .1), int(H * .9)
    band = gray[lo:hi, :BAND + 60]
    # the scanner border is near-black; stained paper can sit at ~130, so
    # the edge walk uses a border threshold and ink is judged against the
    # paper level found beyond it
    scan = (band < 115).mean(axis=0)
    edge = 0
    while edge < len(scan) and scan[edge] >= 0.5:
        edge += 1                              # scanner border ends
    paper = float(np.median(band[:, edge + 10:edge + 60])) if edge + 60 < band.shape[1] else 200.0
    dark = band < min(DARK, paper - 45)
    full = dark.mean(axis=0)
    start = edge + 15                          # skip the paper-edge shadow
    profs = [s.mean(axis=0) for s in np.array_split(dark, NSEG, axis=0)]
    cands = []
    for p in profs:
        cs = [c for c in range(start, min(start + BAND, len(p))) if p[c] >= SEGFRAC]
        cands.append(cs)
    best = None
    for c0 in sorted({c for cs in cands for c in cs}):
        pos, prev = [], c0
        for cs in cands:
            near = [c for c in cs if abs(c - prev) <= 8]
            if near:
                prev = min(near, key=lambda c: abs(c - prev)); pos.append(prev)
            else:
                pos.append(None)
        hits = sum(p is not None for p in pos)
        if hits >= MINHITS * NSEG:
            best = pos
            break                              # outermost qualifying chain
    if best is None:
        return None
    xs = [p for p in best if p is not None]
    inner = max(xs)
    thick = 1
    while inner + thick < len(full) and thick < 12 and full[inner + thick] >= 0.15:
        thick += 1
    return {"inner": int(inner + thick + INSET), "hits": len(xs),
            "wobble": int(max(xs) - min(xs)), "edge": int(edge)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", required=True, choices=["1912"])
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--units", nargs="*")
    a = ap.parse_args()
    r = Recipe(int(a.year))
    units = a.units or sorted(r.units, key=lambda u: (len(u), u))
    res, missing = {}, []
    for u in units:
        info = r.units[u]
        if info.get("region"):             # panels are handled by their own tool
            continue
        img = cv2.imread(r.fetch(r.sheet_file(u)), cv2.IMREAD_GRAYSCALE)
        H, W = img.shape
        got = {s: find_rule(img, s) for s in ("left", "top", "right", "bottom")}
        old = info.get("extent_scan") or info["extent"]
        # A rule that is faint or absent falls back to the paper edge plus the
        # margin the rule always keeps (~45 px); a "rule" much further in is
        # a block-face line along an edge street, not the border, so the same
        # fallback applies. Both are recorded so they can be checked by eye.
        def side(s):
            v = got[s]
            if v is None:
                return None
            return v["inner"] if v["inner"] <= v["edge"] + MAXIN else v["edge"] + FALLBACK
        def edge_of(gray, s):
            g2 = {"left": gray, "right": gray[:, ::-1], "top": gray.T,
                  "bottom": gray[::-1, :].T}[s]
            f = (g2[int(g2.shape[0]*.1):int(g2.shape[0]*.9), :BAND] < 115).mean(axis=0)
            e = 0
            while e < len(f) and f[e] >= 0.5:
                e += 1
            return e + FALLBACK
        vals = {s: (side(s) if got[s] else edge_of(img, s)) for s in got}
        fell = [s for s in got if got[s] is None or got[s]["inner"] > got[s]["edge"] + MAXIN]
        ext = [vals["left"], vals["top"], W - 1 - vals["right"], H - 1 - vals["bottom"]]
        miss = fell
        if miss:
            missing.append((u, miss))
        res[u] = {"extent": [int(v) for v in ext], "size": [W, H], "missing": miss,
                  "wobble": [got[s]["wobble"] if got[s] else None
                             for s in ("left", "top", "right", "bottom")]}
        print(f"unit {u:>3}: {ext} wobble {res[u]['wobble']}"
              f"  {'FALLBACK ' + ','.join(miss) if miss else ''}", flush=True)
    if missing:
        print(f"\n{len(missing)} units with a side not found: {missing}")
    if a.apply:
        path = os.path.join(r.dir, "units.json")
        doc = json.load(open(path))
        for u, v in res.items():
            d = doc["units"][u]
            d.setdefault("extent_scan", d["extent"])
            d["extent"] = v["extent"]
            d["extent_source"] = "tools/neatline.py: inner edge of the border rule"
            d["extent_fallback_sides"] = v["missing"]
        json.dump(doc, open(path, "w"), indent=1)
        print(f"wrote {path}")


if __name__ == "__main__":
    main()
