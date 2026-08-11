"""Edge-line re-anchoring for boundary streets.

Problem (QC rev-4 root cause): a unit's detection of its own BOUNDARY
street is biased 76-153 px toward the unit interior — the comb+CoM
refinement window (±80 px) cannot reach the true corridor center when
real spacing non-uniformity puts it further out. Both neighbors encroach
and the shared corridor crushes.

Fix: anchor each edge line to the corridor's INTERIOR-side block face —
a crisp, fully-printed feature — and place the centerline at
face ± W/2, where W is the corridor width measured where that street
runs through some unit's interior (fallback: per-axis median).
"""

import numpy as np
import cv2

import config
import coverage_prior as cov
import registration as reg


def whiteness_profiles(path, region):
    """Quarter-res whiteness row/col profiles over the map interior."""
    img = cv2.imread(path, cv2.IMREAD_COLOR)
    if region:
        x0, y0, x1, y1 = region
        img = img[y0:y1, x0:x1]
        base = (x0, y0)
    else:
        base = (0, 0)
    q = cv2.resize(img, (img.shape[1] // 4, img.shape[0] // 4),
                   interpolation=cv2.INTER_AREA).astype(np.float32) / 255.0
    del img
    w = reg.whiteness(q)
    h4, w4 = w.shape
    iy, ix = round(h4 * 0.075), round(w4 * 0.075)
    interior = w[iy:h4 - iy, ix:w4 - ix]
    col = interior.mean(axis=0)   # vertical lines (x)
    row = interior.mean(axis=1)   # horizontal lines (y)
    # returns profiles in QUARTER-res coords with their offsets (quarter)
    return (row, iy, base[1] / 4.0), (col, ix, base[0] / 4.0)


def bright_run(profile, center_q, thresh):
    """Contiguous bright run containing (or nearest) center_q. Returns
    (lo, hi) in profile coords or None."""
    bright = profile >= thresh
    n = len(profile)
    c = int(round(center_q))
    c = max(0, min(n - 1, c))
    if not bright[c]:
        # search nearest bright within 60 q-px (240 native)
        for d in range(1, 61):
            if c - d >= 0 and bright[c - d]:
                c = c - d
                break
            if c + d < n and bright[c + d]:
                c = c + d
                break
        else:
            return None
    lo = c
    while lo > 0 and bright[lo - 1]:
        lo -= 1
    hi = c
    while hi < n - 1 and bright[hi + 1]:
        hi += 1
    return lo, hi


def analyze(year):
    """For every unit: corridor runs at each grid line. Returns
    runs[key] = {"v": [(lo,hi) native or None per line], "h": [...]},
    widths[axis][line_ident] = [native widths from units where interior].
    """
    runs, widths = {}, {"v": {}, "h": {}}
    for key, unit in cov.COVERAGE[year].items():
        import run_build
        path = run_build.sheet_path(year, unit["file"])
        det = reg.detect_sheet_grid(path, region=unit["region"])
        avs, sts = cov.expected_lines(year, key)
        v = sorted(det["v_lines_native"])
        h = sorted(det["h_lines_native"])
        if len(v) != len(avs) or len(h) != len(sts):
            runs[key] = None
            continue
        (rowp, roff, rbase), (colp, coff, cbase) = whiteness_profiles(path, unit["region"])
        out = {"v": [], "h": [], "lines_v": v, "lines_h": h}
        for axis, prof, off, qbase, lines, idents in (
            ("v", colp, coff, cbase, v, avs),
            ("h", rowp, roff, rbase, h, sts),
        ):
            thresh = np.percentile(prof, 85) * 0.8
            for i, (p, ident) in enumerate(zip(lines, idents)):
                cq = p / 4.0 - qbase - off
                r = bright_run(prof, cq, thresh)
                if r is None:
                    out[axis].append(None)
                    continue
                lo_n = (r[0] + off + qbase) * 4.0
                hi_n = (r[1] + 1 + off + qbase) * 4.0
                out[axis].append((lo_n, hi_n))
                if 0 < i < len(lines) - 1:   # interior: full corridor printed
                    widths[axis].setdefault(ident, []).append(hi_n - lo_n)
        runs[key] = out
    return runs, widths


def corrected_lines(year, runs, widths):
    """Edge lines re-anchored to interior-side face + W/2."""
    med_axis = {a: float(np.median([w for ws in widths[a].values() for w in ws]))
                if widths[a] else 440.0 for a in ("v", "h")}

    def W(axis, ident):
        ws = widths[axis].get(ident)
        return float(np.median(ws)) if ws else med_axis[axis]

    out = {}
    for key in cov.COVERAGE[year]:
        r = runs.get(key)
        if r is None:
            out[key] = None
            continue
        avs, sts = cov.expected_lines(year, key)
        res = {}
        for axis, lines, idents in (("v", r["lines_v"], avs), ("h", r["lines_h"], sts)):
            fixed = list(lines)
            n = len(lines)
            for i in (0, n - 1):
                ident = idents[i]
                run = r[axis][i]
                if run is None:
                    continue
                lo, hi = run
                if i == 0:
                    # low-side edge: unit interior is on the HIGH side; the
                    # interior-side face is the run's high boundary
                    fixed[i] = hi - W(axis, ident) / 2.0
                else:
                    fixed[i] = lo + W(axis, ident) / 2.0
            res[axis] = fixed
        out[key] = (res["v"], res["h"])
    return out, med_axis
