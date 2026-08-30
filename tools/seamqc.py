#!/usr/bin/env python3
"""Automated seam QC for the city mosaics: do adjacent sheets agree?

    python3 tools/seamqc.py --year 1912 [--crops 12]

For every pair of ownership regions that share a boundary, sample windows
along that boundary, warp BOTH sheets into the same mosaic-frame window, and
measure how far one would have to shift to line up with the other
(phase correlation) plus how well they correlate once shifted.

This is Stage 5's automated metric, not a grade: it ranks seams worst-first
so a human (or a grader agent) looks at the ones that matter. Nothing here
modifies pixels.

Writes outputs/{year}/qc/seams/seam_metrics.{json,csv} and, for the worst
--crops seams, 100% and 50% renders of the seam window.
"""
import argparse
import csv
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from reciplib import Recipe                      # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WIN = 384          # sample window, mosaic px
MIN_BOUNDARY = 200  # ignore pairs that merely touch at a corner
MAX_SAMPLES = 9     # windows per seam
MIN_RESPONSE = 0.06  # below this the correlation peak is not a measurement
MARGIN_INSET = 160   # native px trimmed off a sheet's printed extent: the
                     # neatline and 'SEE SHEET n' notes are not shared ground


def warp(img, M, t, x0, y0, w, h):
    """Sheet warped into a mosaic window, plus the mask of where the scan
    actually reaches (outside it the warp is white padding, which would
    otherwise correlate as a strong content/blank edge)."""
    import cv2
    A = np.hstack([M, (t - np.array([x0, y0], float)).reshape(2, 1)])
    out = cv2.warpAffine(img, A, (w, h), flags=cv2.INTER_AREA,
                         borderValue=(255, 255, 255))
    valid = cv2.warpAffine(np.full(img.shape[:2], 255, np.uint8), A, (w, h),
                           flags=cv2.INTER_NEAREST, borderValue=(0,))
    return out, valid


def informative(gray):
    """Reject blank paper: it correlates meaninglessly."""
    return gray.std() > 12.0 and (gray < 200).mean() > 0.02


def main():
    global WIN, MARGIN_INSET
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", required=True, choices=["1899", "1912"])
    ap.add_argument("--crops", type=int, default=12,
                    help="render seam crops for the N worst seams")
    ap.add_argument("--limit", type=int, default=0, help="debug: first N pairs")
    ap.add_argument("--win", type=int, default=WIN, help="sample window px")
    ap.add_argument("--inset", type=int, default=MARGIN_INSET,
                    help="native px trimmed off each sheet's printed extent")
    a = ap.parse_args()

    import cv2
    from shapely.geometry import Polygon

    WIN, MARGIN_INSET = a.win, a.inset

    r = Recipe(int(a.year))
    regions = [(u, Polygon(p)) for u, p in r.ownership()]
    print(f"{len(regions)} ownership regions", flush=True)

    pairs = []
    for i in range(len(regions)):
        for j in range(i + 1, len(regions)):
            ua, pa = regions[i]
            ub, pb = regions[j]
            if not pa.intersects(pb):
                continue
            shared = pa.boundary.intersection(pb.boundary)
            if shared.is_empty or shared.length < MIN_BOUNDARY:
                continue
            pairs.append((ua, ub, shared))
    pairs.sort(key=lambda p: (str(p[0]), str(p[1])))
    if a.limit:
        pairs = pairs[:a.limit]
    print(f"{len(pairs)} adjacent pairs with a shared boundary", flush=True)

    def inside_mapped(u, M, t, x0, y0, w, h):
        """Is this mosaic window inside unit u's mapped area?

        Sanborn sheets carry border furniture — neatline, title block, and the
        'SEE SHEET n' continuation notes that adjacent sheets each print
        DIFFERENTLY by design. Correlating there measures nothing, so require
        the whole window inside the unit's printed extent, inset past the
        margin band.
        """
        ext = (r.units.get(str(u)) or {}).get("extent")
        if not ext:
            return False
        Minv = np.linalg.inv(M)
        for cx, cy in ((x0, y0), (x0 + w, y0), (x0, y0 + h), (x0 + w, y0 + h)):
            nx, ny = Minv @ (np.array([cx, cy], float) - t)
            if not (ext[0] + MARGIN_INSET <= nx <= ext[2] - MARGIN_INSET
                    and ext[1] + MARGIN_INSET <= ny <= ext[3] - MARGIN_INSET):
                return False
        return True

    cache = {}

    def sheet(u):
        if u not in cache:
            img = cv2.imread(r.fetch(r.sheet_file(u)), cv2.IMREAD_GRAYSCALE)
            if img is None:
                raise RuntimeError(f"cannot decode source for unit {u}")
            cache[u] = (img, *r.sheet_matrix(u))
            if len(cache) > 14:                 # keep memory flat
                cache.pop(next(iter(cache)))
        return cache[u]

    out = []
    for n, (ua, ub, shared) in enumerate(pairs, 1):
        try:
            ia, Ma, ta = sheet(ua)
            ib, Mb, tb = sheet(ub)
        except Exception as e:
            print(f"  {ua}|{ub}: skipped ({e})", flush=True)
            continue

        L = shared.length
        ks = max(1, min(MAX_SAMPLES, int(L // WIN)))
        offs, corrs, used = [], [], 0
        for k in range(ks):
            pt = shared.interpolate((k + 0.5) * L / ks)
            x0, y0 = pt.x - WIN / 2, pt.y - WIN / 2
            if not (inside_mapped(ua, Ma, ta, x0, y0, WIN, WIN)
                    and inside_mapped(ub, Mb, tb, x0, y0, WIN, WIN)):
                continue          # margin furniture, not shared ground
            wa, va = warp(ia, Ma, ta, x0, y0, WIN, WIN)
            wb, vb = warp(ib, Mb, tb, x0, y0, WIN, WIN)
            # measure only where BOTH scans actually reach, and only on a
            # window that is mostly real overlap
            both = (va > 0) & (vb > 0)
            if both.mean() < 0.70:
                continue
            ys, xs = np.where(both)
            sl = (slice(ys.min(), ys.max() + 1), slice(xs.min(), xs.max() + 1))
            ca, cb = wa[sl], wb[sl]
            if min(ca.shape) < 64 or not (informative(ca) and informative(cb)):
                continue
            fa, fb = ca.astype(np.float32), cb.astype(np.float32)
            win = cv2.createHanningWindow((fa.shape[1], fa.shape[0]), cv2.CV_32F)
            (dx, dy), resp = cv2.phaseCorrelate(fa, fb, win)
            if resp < MIN_RESPONSE:      # no trustworthy peak; not a datum
                continue
            offs.append(float(np.hypot(dx, dy)))
            corrs.append(float(resp))
            used += 1
        if not offs:
            out.append({"seam": f"{ua}|{ub}", "a": ua, "b": ub,
                        "boundary_px": round(L, 1), "samples": 0,
                        "median_offset_px": None, "median_response": None,
                        "status": "no-signal"})
            continue
        out.append({"seam": f"{ua}|{ub}", "a": ua, "b": ub,
                    "boundary_px": round(L, 1), "samples": used,
                    "median_offset_px": round(float(np.median(offs)), 2),
                    "max_offset_px": round(float(np.max(offs)), 2),
                    "median_response": round(float(np.median(corrs)), 3),
                    "status": "measured"})
        if n % 20 == 0:
            print(f"  {n}/{len(pairs)} pairs", flush=True)

    qc = os.path.join(REPO, "outputs", a.year, "qc", "seams")
    os.makedirs(qc, exist_ok=True)

    measured = [o for o in out if o["status"] == "measured"]
    measured.sort(key=lambda o: -o["median_offset_px"])
    json.dump({"year": int(a.year), "window_px": WIN,
               "method": ("phase correlation between the two sheets warped "
                          "into the same mosaic window; offset is how far "
                          "they disagree, response is correlation confidence"),
               "pairs": out},
              open(os.path.join(qc, "seam_metrics.json"), "w"), indent=1)
    with open(os.path.join(qc, "seam_metrics.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["seam", "a", "b", "boundary_px",
                                          "samples", "median_offset_px",
                                          "max_offset_px", "median_response",
                                          "status"])
        w.writeheader()
        for o in out:
            w.writerow({k: o.get(k) for k in w.fieldnames})

    if measured:
        vals = [o["median_offset_px"] for o in measured]
        print(f"\nmeasured {len(measured)} seams "
              f"({len(out) - len(measured)} no-signal)")
        print(f"median offset across seams: {np.median(vals):.2f} px")
        print(f"95th percentile           : {np.percentile(vals, 95):.2f} px")
        print("\nworst seams:")
        for o in measured[:15]:
            print(f"  {o['seam']:<10} {o['median_offset_px']:>7.2f} px  "
                  f"(max {o['max_offset_px']:.1f}, n={o['samples']}, "
                  f"resp {o['median_response']:.2f})")

    # crops for the worst seams, at 100% and 50%, both sheets side by side
    for o in measured[:a.crops]:
        ua, ub = o["a"], o["b"]
        shared = next(s for x, y, s in pairs if x == ua and y == ub)
        pt = shared.interpolate(0.5, normalized=True)
        x0, y0 = pt.x - WIN / 2, pt.y - WIN / 2
        ia, Ma, ta = sheet(ua)
        ib, Mb, tb = sheet(ub)
        wa, _ = warp(ia, Ma, ta, x0, y0, WIN, WIN)
        wb, _ = warp(ib, Mb, tb, x0, y0, WIN, WIN)
        pair = np.hstack([wa, np.full((WIN, 4), 128, np.uint8), wb])
        name = f"{ua}-{ub}".replace("|", "-")
        cv2.imwrite(os.path.join(qc, f"seam_{name}_100.png"), pair)
        cv2.imwrite(os.path.join(qc, f"seam_{name}_50.png"),
                    cv2.resize(pair, None, fx=0.5, fy=0.5,
                               interpolation=cv2.INTER_AREA))
    print(f"\nwrote {qc}/seam_metrics.json + .csv"
          f" and crops for the worst {min(a.crops, len(measured))} seams")
    return 0


if __name__ == "__main__":
    sys.exit(main())
