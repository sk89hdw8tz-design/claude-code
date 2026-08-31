#!/usr/bin/env python3
"""Sheet-to-sheet registration from shared ground, the way the master was built.

    python3 tools/pairfit.py --year 1912 --pair 75 76
    python3 tools/pairfit.py --year 1912 --all [--apply]

The accepted 1912 core was not solved against a global lattice. It was solved
pair by pair: for each adjacent pair a corridor was identified on both sheets,
its identity justified against printed address runs (see recipe/controls/,
field `why_not_one_block_off`), and the two sheets constrained to agree on it.

This reproduces that constraint without OCR. The key map says which streets
and avenues each sheet depicts, so it says which band two neighbours share.
We warp both sheets into that band and search the translation that makes their
ink agree, then accept only if the winning peak is clearly better than the
runner-up — the automatic stand-in for the original's "acceptance decided by
eye". A pair whose peak is not decisive is reported, never guessed.

Transforms only. No pixel is altered.
"""
import argparse
import json
import glob
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from reciplib import Recipe, px_per_ft            # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEARCH_FT = 260.0        # a bit under one block pitch: enough for real error,
                         # not enough to land a whole block wrong
STEP_FT = 2.0
MIN_PEAK = 0.10          # correlation floor
MIN_MARGIN = 1.25        # winner must beat the best rival this many times over


def keymap(year):
    km = {}
    for f in glob.glob(os.path.join(REPO, "rebuild_1899", "out",
                                    f"keymap_{year}_*.json")):
        for e in json.load(open(f)).get("results", []):
            km[str(e["sheet"])] = e
    return km


def fit_pair(r, ua, ub, ppf, scale=0.25, verbose=True):
    """Translation (mosaic px) to apply to ub so it agrees with ua."""
    import cv2
    from shapely.geometry import Polygon

    own = dict(r.ownership())
    if ua not in own or ub not in own:
        return None
    pa, pb = Polygon(own[ua]), Polygon(own[ub])
    inter = pa.buffer(400).intersection(pb.buffer(400))
    if inter.is_empty:
        return None
    x0, y0, x1, y1 = inter.bounds
    pad = 1.2 * SEARCH_FT * ppf
    x0, y0, x1, y1 = x0 - pad, y0 - pad, x1 + pad, y1 + pad
    W = int((x1 - x0) * scale)
    H = int((y1 - y0) * scale)
    if W < 60 or H < 60 or W * H > 40e6:
        return None

    def warped(uid):
        img = cv2.imread(r.fetch(r.sheet_file(uid)), cv2.IMREAD_GRAYSCALE)
        M, t = r.sheet_matrix(uid)
        A = np.hstack([M * scale,
                       ((t - np.array([x0, y0])) * scale).reshape(2, 1)])
        g = cv2.warpAffine(img, A, (W, H), flags=cv2.INTER_AREA,
                           borderValue=(255,))
        v = cv2.warpAffine(np.full(img.shape[:2], 255, np.uint8), A, (W, H),
                           flags=cv2.INTER_NEAREST, borderValue=(0,))
        return g, v > 0

    ga, va = warped(ua)
    gb, vb = warped(ub)
    # keep only ground BOTH scans actually cover: a no-data region zeroed and
    # mean-shifted is a constant block, and constants correlate with anything,
    # which is what pins a naive peak to the search boundary
    both = va & vb
    if both.sum() < 400:
        return None
    ys, xs = np.where(both)
    ry0, ry1, rx0, rx1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    ga, gb = ga[ry0:ry1, rx0:rx1], gb[ry0:ry1, rx0:rx1]
    ia = (255 - ga.astype(np.float32)) / 255.0
    ib = (255 - gb.astype(np.float32)) / 255.0
    if ia.sum() < 500 or ib.sum() < 500:
        return None

    # normalised matched filter: a template from B, inset by the search
    # radius, slid over A. TM_CCOEFF_NORMED handles the normalisation that a
    # raw FFT correlation does not, which otherwise just peaks at the edge.
    rad = int(SEARCH_FT * ppf * scale)
    th, tw = ia.shape[0] - 2 * rad, ia.shape[1] - 2 * rad
    if th < 40 or tw < 40:
        return None
    tmpl = ib[rad:rad + th, rad:rad + tw]
    if float(np.abs(tmpl).sum()) < 200:
        return None
    surf = cv2.matchTemplate(ia.astype(np.float32), tmpl.astype(np.float32),
                             cv2.TM_CCOEFF_NORMED)
    scores = []
    flat = np.argsort(surf, axis=None)[::-1][:600]
    for idx in flat:
        yy, xx = np.unravel_index(idx, surf.shape)
        scores.append((float(surf[yy, xx]), int(xx - rad), int(yy - rad)))
    if not scores:
        return None
    best = scores[0]
    # runner-up must be a genuinely different placement, not the same peak
    rival = next((s for s in scores[1:]
                  if abs(s[1] - best[1]) + abs(s[2] - best[2]) > 3 * rad // 4), None)
    margin = best[0] / rival[0] if rival and rival[0] > 0 else float("inf")
    dx_mos, dy_mos = best[1] / scale, best[2] / scale
    res = {"pair": f"{ua}|{ub}", "peak": round(best[0], 4),
           "margin": round(margin, 3) if margin != float("inf") else None,
           "shift_px": [round(dx_mos, 1), round(dy_mos, 1)],
           "shift_ft": [round(dx_mos / ppf, 1), round(dy_mos / ppf, 1)],
           "accepted": bool(best[0] >= MIN_PEAK and margin >= MIN_MARGIN)}
    if verbose:
        print(f"  {res['pair']:<9} peak {res['peak']:.3f} margin "
              f"{res['margin']}  shift {res['shift_ft']} ft  "
              f"{'ACCEPT' if res['accepted'] else 'reject'}", flush=True)
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", required=True, choices=["1912", "1899"])
    ap.add_argument("--pair", nargs=2)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--scale", type=float, default=0.25)
    a = ap.parse_args()

    r = Recipe(int(a.year))
    ppf = px_per_ft(r)
    if a.pair:
        res = fit_pair(r, a.pair[0], a.pair[1], ppf, a.scale)
        print(json.dumps(res, indent=1) if res else "no overlap / not measurable")
        return 0

    from shapely.geometry import Polygon
    own = [(u, Polygon(p)) for u, p in r.ownership()]
    pairs = []
    for i in range(len(own)):
        for j in range(i + 1, len(own)):
            if own[i][1].intersects(own[j][1]):
                sh = own[i][1].boundary.intersection(own[j][1].boundary)
                if not sh.is_empty and sh.length > 200:
                    pairs.append((own[i][0], own[j][0]))
    print(f"{len(pairs)} adjacent pairs", flush=True)
    out = []
    for n, (ua, ub) in enumerate(pairs, 1):
        try:
            res = fit_pair(r, ua, ub, ppf, a.scale)
        except Exception as e:
            print(f"  {ua}|{ub}: {e}", flush=True)
            continue
        if res:
            out.append(res)
        if n % 20 == 0:
            print(f"  ... {n}/{len(pairs)}", flush=True)
    acc = [o for o in out if o["accepted"]]
    print(f"\nmeasured {len(out)} pairs, accepted {len(acc)}")
    if acc:
        mags = [float(np.hypot(*o["shift_ft"])) for o in acc]
        print(f"accepted shifts: median {np.median(mags):.0f} ft, "
              f"90th {np.percentile(mags, 90):.0f} ft, max {max(mags):.0f} ft")
    p = os.path.join(r.dir, "controls", "pairfit.json")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    json.dump({"method": "overlap ink correlation, key-map shared band, "
                         "peak must beat runner-up by %.2fx" % MIN_MARGIN,
               "search_ft": SEARCH_FT, "pairs": out}, open(p, "w"), indent=1)
    print(f"wrote {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
