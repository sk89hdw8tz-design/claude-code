"""Closed-loop seam correction.

Renders each unit ALONE (quarter res), measures where its block face
actually lands at every boundary street relative to the consensus line,
and writes per-unit edge-knot corrections (native px) that run_build
applies before the joint solve. Iterating build -> measure -> correct
converges on the exact quantity QC measures (corridor width at seams).

Usage: python3 iterate_seams.py 1885   (after a run_build pass)
Writes build/1885/edge_corrections.json
"""

import json
import os
import sys

import numpy as np

os.environ.setdefault("OPENCV_IO_MAX_IMAGE_PIXELS", str(2**40))
import cv2

import config
import coverage_prior as cov
import registration as reg
import run_build

Q = 4  # measurement scale divisor


def render_unit_alone(year, key, fit, region, canvas_wh):
    """Quarter-res render of one unit on black background."""
    img = cv2.imread(run_build.sheet_path(year, cov.COVERAGE[year][key]["file"]),
                     cv2.IMREAD_COLOR)
    if region:
        x0, y0, x1, y1 = region
        m = np.zeros(img.shape[:2], np.uint8)
        m[y0:y1, x0:x1] = 1
        img = img * m[:, :, None]
    M = np.array([[fit["sx"] / Q, 0, fit["tx"] / Q],
                  [0, fit["sy"] / Q, fit["ty"] / Q]], np.float64)
    out = cv2.warpAffine(img, M, (canvas_wh[0] // Q, canvas_wh[1] // Q),
                         flags=cv2.INTER_AREA, borderMode=cv2.BORDER_CONSTANT,
                         borderValue=0)
    del img
    return out


def ink_and_printed(render):
    g = render.astype(np.float32) / 255.0
    printed = g.max(axis=2) > 0.05
    mx = g.max(axis=2)
    mn = g.min(axis=2)
    white = g.mean(axis=2) - 2.2 * (mx - mn)
    ink = printed & (white < 0.45)
    return ink, printed


def measure_face(ink, printed, axis, line_q, span, toward, max_scan=140):
    """Distance (q px, signed away from line toward unit interior) of the
    first sustained ink face scanning from the line toward the interior.
    toward = +1 scan increasing coordinate, -1 decreasing."""
    hits = []
    DENS_WIN = 30      # q px (~120 native) of block interior behind a face
    DENS_MIN = 0.22    # dashes/labels leave paper behind them; buildings don't
    for t in span:
        t = int(t)
        for d in range(-30, max_scan):   # allow faces that CROSS the line
            pos = int(line_q + toward * d)
            if axis == "v":
                y, x = t, pos
            else:
                y, x = pos, t
            if y < 0 or x < 0 or y >= ink.shape[0] or x >= ink.shape[1]:
                break
            if not printed[y, x] or not ink[y, x]:
                continue
            ps = [int(line_q + toward * (d + dd)) for dd in range(DENS_WIN)]
            if axis == "v":
                ys = np.full(len(ps), t)
                xs = np.array(ps)
            else:
                ys = np.array(ps)
                xs = np.full(len(ps), t)
            ok = (ys >= 0) & (xs >= 0) & (ys < ink.shape[0]) & (xs < ink.shape[1])
            if ok.sum() < DENS_WIN // 2:
                break
            if ink[ys[ok], xs[ok]].mean() >= DENS_MIN:
                hits.append(d)
                break
    return float(np.median(hits)) if len(hits) >= 8 else None


def main():
    year = sys.argv[1] if len(sys.argv) > 1 else "1885"
    B = os.path.join(config.BUILD_DIR, year)
    regj = json.load(open(os.path.join(B, "registration.json")))
    X = {int(k): v for k, v in regj["consensus_av"].items()}
    Y = {int(k): v for k, v in regj["consensus_st"].items()}
    fits = {k: u["fit_consensus"] for k, u in regj["units"].items()}

    ed = config.EDITIONS[year]
    a0, a1, s0, s1 = cov.composite_extent(year)
    pad = round(0.25 * ed["pitch_av"])
    W = round((a1 - a0) * ed["pitch_av"]) + 2 * pad
    H = round((s1 - s0) * ed["pitch_st"]) + 2 * pad
    ox = a0 * ed["pitch_av"] - pad
    oy = (s0 - config.STREET_ORIGIN) * ed["pitch_st"] - pad

    prev_path = os.path.join(B, "edge_corrections.json")
    prev = json.load(open(prev_path)) if os.path.exists(prev_path) else {}

    corrections = {}
    for key in cov.COVERAGE[year]:
        if key not in fits:
            continue
        unit = cov.COVERAGE[year][key]
        fit = dict(fits[key])
        fit = {"sx": fit["sx"], "sy": fit["sy"],
               "tx": fit["tx"] - ox, "ty": fit["ty"] - oy}
        rend = render_unit_alone(year, key, fit, unit["region"], (W, H))
        ink, printed = ink_and_printed(rend)
        avs, sts = cov.expected_lines(year, key)
        cor = {"v": {}, "h": {}}
        # Self-calibrated: reference face distance measured at this unit's
        # INTERIOR lines (placement proven good), both directions.
        meas = {"v": {}, "h": {}}
        refs = {"v": [], "h": []}
        for axis, idents, Gpos, goff, span_ids, Spos, soff in (
            ("v", avs, X, ox, sts, Y, oy),
            ("h", sts, Y, oy, avs, X, ox),
        ):
            lo = (Spos[min(span_ids)] - soff) / Q + 60
            hi = (Spos[max(span_ids)] - soff) / Q - 60
            span = np.linspace(lo, hi, 25)
            n = len(idents)
            for i, ident in enumerate(idents):
                line_q = (Gpos[ident] - goff) / Q
                if 0 < i < n - 1:
                    for toward in (+1, -1):
                        d = measure_face(ink, printed, axis, line_q, span, toward)
                        if d is not None:
                            refs[axis].append(d)
                else:
                    toward = +1 if i == 0 else -1
                    d = measure_face(ink, printed, axis, line_q, span, toward)
                    if d is not None:
                        meas[axis][i] = d
        for axis in ("v", "h"):
            if not refs[axis]:
                continue
            d_ref = float(np.median(refs[axis]))
            for i, d in meas[axis].items():
                cor[axis][str(i)] = round((d_ref - d) * Q, 1)
        del rend, ink, printed
        # accumulate with previous corrections
        pv = prev.get(key, {"v": {}, "h": {}})
        for ax in ("v", "h"):
            for i, e in cor[ax].items():
                cor[ax][i] = round(e + pv.get(ax, {}).get(i, 0.0), 1)
            for i, e in pv.get(ax, {}).items():
                cor[ax].setdefault(i, e)
        corrections[key] = cor
        print(f"[iterate] unit {key}: v={cor['v']} h={cor['h']}", flush=True)

    with open(prev_path, "w") as f:
        json.dump(corrections, f, indent=1)
    print(f"[iterate] wrote {prev_path}")


if __name__ == "__main__":
    main()
