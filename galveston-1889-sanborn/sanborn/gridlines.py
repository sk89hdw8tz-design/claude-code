"""Street-grid centreline detection for Sanborn sheets.

WHY CENTRELINES RATHER THAN CORNERS
    Adjacent Sanborn sheets abut along a street. Each sheet draws that street's
    dash-dot CENTRELINE, the crossing avenue centrelines, and the width
    annotation -- but the physical block corners near the join belong to
    whichever sheet owns that block, so a corner is often drawn on only one of
    the two sheets. Centrelines are drawn on both.

    So the tie point used here is the INTERSECTION OF TWO CENTRELINES. It is
    constructible on both sheets even where neither draws the corner, it is
    defined by long straight features rather than one small mark, and fitting a
    line to hundreds of pixels locates it far more precisely than clicking a
    corner ever could.

    This also sidesteps the accuracy ceiling of UT's detector-based approach:
    their 320x320 whole-sheet SSD can only place an intersection to within
    16-28 scan pixels, whereas a least-squares line intersection here is good
    to a fraction of a pixel.

METHOD
    Sanborn centrelines are long, thin, nearly-axis-aligned dash-dot rules. The
    dashes are reconnected with a directional morphological closing, isolated
    with a long directional opening (which removes building outlines, lot lines
    and text, none of which run unbroken across a whole sheet), and the
    surviving pixels are grouped into lines and fitted by total least squares.
"""

from __future__ import annotations

import cv2
import numpy as np


def ink_mask(img, block=51, C=12):
    """Dark-ink mask, robust to the uneven paper tone of an archival scan."""
    g = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY) if img.ndim == 3 else img
    g = cv2.GaussianBlur(g, (3, 3), 0)
    return cv2.adaptiveThreshold(g, 255, cv2.ADAPTIVE_THRESH_MEAN_C,
                                 cv2.THRESH_BINARY_INV, block | 1, C)


def _directional(mask, horizontal, close_len, open_len):
    k_close = cv2.getStructuringElement(
        cv2.MORPH_RECT, (close_len, 1) if horizontal else (1, close_len))
    k_open = cv2.getStructuringElement(
        cv2.MORPH_RECT, (open_len, 1) if horizontal else (1, open_len))
    m = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, k_close)   # rejoin the dashes
    return cv2.morphologyEx(m, cv2.MORPH_OPEN, k_open)     # keep only long runs


def _fit_line(pts, horizontal):
    """Total-least-squares line through points; returns (offset, slope).

    For a horizontal line, y = offset + slope * x (slope ~ 0).
    For a vertical line, x = offset + slope * y.
    """
    p = np.asarray(pts, dtype=float)
    u = p[:, 0] if horizontal else p[:, 1]     # along the line
    v = p[:, 1] if horizontal else p[:, 0]     # across the line
    A = np.column_stack([np.ones_like(u), u])
    sol, *_ = np.linalg.lstsq(A, v, rcond=None)
    resid = v - A @ sol
    return float(sol[0]), float(sol[1]), float(np.sqrt(np.mean(resid ** 2)))


def detect_lines(img, horizontal=True, min_extent_frac=0.55, close_frac=0.02,
                 open_frac=0.10, merge_px=14, min_pixels=2000, work_width=1700):
    """Detect long near-axis-aligned centrelines.

    Returns a list of dicts with `offset`, `slope`, `rms`, `extent` (fraction of
    the sheet the line spans) and `n` (supporting pixels), in FULL-RESOLUTION
    coordinates. `min_extent_frac` is what rejects lot lines and building
    edges: only a street runs most of the way across a sheet.
    """
    h, w = img.shape[:2]
    scale = min(1.0, work_width / float(w))
    small = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
    sh, sw = small.shape[:2]
    mask = ink_mask(small)

    span = sw if horizontal else sh
    m = _directional(mask, horizontal,
                     max(3, int(span * close_frac)),
                     max(9, int(span * open_frac)))

    n, labels, stats, _ = cv2.connectedComponentsWithStats(m, 8)
    cand = []
    for i in range(1, n):
        x, y, bw, bh, area = stats[i]
        extent = (bw / sw) if horizontal else (bh / sh)
        if extent < min_extent_frac:
            continue
        thick = bh if horizontal else bw
        if thick > 0.03 * (sh if horizontal else sw):
            continue                    # a blob, not a rule
        ys, xs = np.where(labels == i)
        if xs.size < 30:
            continue
        off, slope, rms = _fit_line(np.column_stack([xs, ys]), horizontal)
        cand.append({"offset": off / scale, "slope": slope, "rms": rms / scale,
                     "extent": float(extent), "n": int(xs.size / (scale ** 2)),
                     "_off_small": off})

    # Merge duplicates: the two casings of one street, or a rule split by text.
    cand.sort(key=lambda d: d["offset"])
    merged = []
    for c in cand:
        if merged and abs(c["offset"] - merged[-1]["offset"]) < merge_px:
            a = merged[-1]
            tot = a["n"] + c["n"]
            a["offset"] = (a["offset"] * a["n"] + c["offset"] * c["n"]) / tot
            a["slope"] = (a["slope"] * a["n"] + c["slope"] * c["n"]) / tot
            a["extent"] = max(a["extent"], c["extent"])
            a["n"] = tot
        else:
            merged.append(dict(c))
    return [m for m in merged if m["n"] >= min_pixels]


def line_point(line, along, horizontal):
    """Point on a fitted line at the given along-line coordinate."""
    across = line["offset"] + line["slope"] * along
    return (along, across) if horizontal else (across, along)


def intersect(hline, vline):
    """Intersection of a horizontal-ish and a vertical-ish fitted line.

    Solving the pair exactly rather than assuming perpendicularity keeps the
    result honest on a scan that is slightly rotated or trapezoidal.
        horizontal:  y = a + b x
        vertical:    x = c + d y
    """
    a, b = hline["offset"], hline["slope"]
    c, d = vline["offset"], vline["slope"]
    den = 1.0 - b * d
    if abs(den) < 1e-9:
        return None
    x = (c + d * a) / den
    y = a + b * x
    return (float(x), float(y))


def detect_bands(img, horizontal=True, work_width=1400, density_frac=0.018,
                 low_quantile=0.30, min_extent_frac=0.55, min_width_frac=0.006,
                 max_width_frac=0.075, margin_frac=0.02):
    """Detect street/avenue centrelines as low-ink BANDS.

    On these sheets a street is not a drawn rule -- it is a wide band of bare
    paper between two rows of blocks, carrying only a dash-dot centre mark, a
    width figure and the street's name. The blocks either side are dense with
    building outlines, hatching and lot lines. So the reliable signal is the
    ABSENCE of ink over a band that runs the full width of the sheet, not the
    presence of a line: a thin dashed rule is easily lost among lot lines,
    whereas nothing else on the sheet is both empty and full-length.

    Working from the band also puts the fitted centreline down the middle of
    the roadway, which is the feature two adjoining sheets actually share.
    """
    h, w = img.shape[:2]
    scale = min(1.0, work_width / float(w))
    small = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
    sh, sw = small.shape[:2]
    # Density averaged over a window ELONGATED ALONG the band. A street carries
    # its own name and a width figure, so an isotropic window sees those letters
    # as ink and breaks the band; averaging along the street instead lets the
    # lettering wash out against the bare paper either side of it, while the
    # dense blocks above and below stay dense.
    ink = (ink_mask(small) > 0).astype(np.float32)
    long_k = max(9, int((sw if horizontal else sh) * 0.10)) | 1
    short_k = max(3, int((sh if horizontal else sw) * 0.004)) | 1
    dens = cv2.boxFilter(ink, -1, (long_k, short_k) if horizontal else (short_k, long_k))

    # Ignore the outer margin: the paper collar is empty everywhere and would
    # otherwise register as the widest "street" on the sheet.
    mx, my = int(sw * margin_frac), int(sh * margin_frac)
    core = dens[my:sh - my, mx:sw - mx]
    thr = float(np.quantile(core, low_quantile))
    low = (dens <= thr).astype(np.uint8) * 255
    low[:my, :] = 0; low[sh - my:, :] = 0
    low[:, :mx] = 0; low[:, sw - mx:] = 0

    span = sw if horizontal else sh
    # Bridge short interruptions (a cross-street, a pipe note) before demanding
    # that a band run the length of the sheet.
    C = max(5, int(span * 0.05))
    kc = cv2.getStructuringElement(cv2.MORPH_RECT, (C, 1) if horizontal else (1, C))
    low = cv2.morphologyEx(low, cv2.MORPH_CLOSE, kc)
    L = max(9, int(span * min_extent_frac))
    k = cv2.getStructuringElement(cv2.MORPH_RECT, (L, 1) if horizontal else (1, L))
    bands = cv2.morphologyEx(low, cv2.MORPH_OPEN, k)

    n, labels, stats, _ = cv2.connectedComponentsWithStats(bands, 8)
    across_span = sh if horizontal else sw
    out = []
    for i in range(1, n):
        x, y, bw, bh, area = stats[i]
        extent = (bw / sw) if horizontal else (bh / sh)
        width = bh if horizontal else bw
        if extent < min_extent_frac:
            continue
        if not (across_span * min_width_frac <= width <= across_span * max_width_frac):
            continue
        ys, xs = np.where(labels == i)
        # centreline = mean across-coordinate at each along-coordinate
        along = xs if horizontal else ys
        across = ys if horizontal else xs
        order = np.argsort(along)
        along, across = along[order], across[order]
        uniq, idx = np.unique(along, return_index=True)
        means = np.array([across[a:b].mean() for a, b in
                          zip(idx, list(idx[1:]) + [len(across)])])
        if uniq.size < 20:
            continue
        A = np.column_stack([np.ones_like(uniq, dtype=float), uniq.astype(float)])
        sol, *_ = np.linalg.lstsq(A, means, rcond=None)
        rms = float(np.sqrt(np.mean((means - A @ sol) ** 2)))
        out.append({"offset": float(sol[0]) / scale, "slope": float(sol[1]),
                    "rms": rms / scale, "extent": float(extent),
                    "width_px": float(width / scale),
                    "n": int(ys.size / (scale ** 2))})
    out.sort(key=lambda d: d["offset"])
    return out


def fit_regular(lines, tol=60.0, min_spacing=250.0, expected=None):
    """Fit a regular spacing model to detected band centres.

    Galveston is a planned grid: blocks are laid out at a near-constant pitch,
    so the true street centrelines satisfy offset(k) = a + b*k for integer k.
    Detected candidates do not: the detector emits the occasional page margin,
    splits one wide street into two, or misses a street crossed by a railway.

    Fitting the periodic model by exhaustive search over candidate pairs (a
    small RANSAC) recovers the real grid, discards anything off-lattice, and
    lets a missing street be interpolated at its correct position instead of
    leaving a hole. Returns the inliers with their lattice index `k`, plus the
    fitted pitch -- a pitch wildly different from its neighbours' is itself a
    useful warning that a sheet was misread.
    """
    if len(lines) < 2:
        return {"lines": [], "a": None, "b": None, "inliers": 0,
                "note": "too few candidates"}
    offs = np.array([l["offset"] for l in lines], dtype=float)
    best = None
    for i in range(len(offs)):
        for j in range(i + 1, len(offs)):
            gap = abs(offs[j] - offs[i])
            if gap < min_spacing:
                continue
            # the pair might span several lattice steps
            for steps in range(1, 6):
                b = gap / steps
                if b < min_spacing:
                    continue
                a = min(offs[i], offs[j])
                k = np.round((offs - a) / b)
                pred = a + k * b
                err = np.abs(offs - pred)
                inl = err <= tol
                score = (int(inl.sum()), -float(err[inl].sum()))
                if best is None or score > best[0]:
                    best = (score, a, b, inl.copy(), k.copy())
    if best is None:
        return {"lines": [], "a": None, "b": None, "inliers": 0,
                "note": "no consistent spacing found"}
    _, a, b, inl, k = best
    # refit on inliers
    kk, oo = k[inl], offs[inl]
    A = np.column_stack([np.ones_like(kk), kk])
    sol, *_ = np.linalg.lstsq(A, oo, rcond=None)
    a, b = float(sol[0]), float(sol[1])
    out = []
    for idx in np.where(inl)[0]:
        d = dict(lines[idx])
        d["k"] = int(k[idx])
        d["grid_offset"] = a + k[idx] * b
        d["grid_residual"] = float(abs(d["offset"] - d["grid_offset"]))
        out.append(d)
    out.sort(key=lambda d: d["k"])
    return {"lines": out, "a": a, "b": b, "inliers": int(inl.sum()),
            "rejected": [dict(lines[i]) for i in np.where(~inl)[0]],
            "note": ""}


def refine_band(img, approx_offset, horizontal=True, window=170, segments=9,
                work_width=1700, along_frac=0.06, trim=0.10, min_segments=4,
                bounds=None):
    """Locate ONE street/avenue centreline precisely, given a rough position.

    Global grid detection on a Sanborn sheet is unreliable -- railways, parks,
    wharves and irregular blocks all break the lattice, and a detector tuned to
    find every street on one sheet finds phantom ones on the next. Locating a
    single band whose approximate position is already known is a far
    better-conditioned problem, and it is the one actually worth solving: the
    street's IDENTITY comes from the label printed beside it, which a human (or
    an agent) reads once, and only its PRECISE position needs measuring.

    The band centre is measured independently in several segments along the
    street and a line is fitted through those measurements, so the result
    carries the sheet's small rotation rather than assuming the scan is square.
    Segments whose profile has no clear minimum are dropped, and the fit is
    reported with its RMS so a bad measurement is visible rather than silent.
    """
    h, w = img.shape[:2]
    scale = min(1.0, work_width / float(w))
    small = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
    sh, sw = small.shape[:2]
    ink = (ink_mask(small) > 0).astype(np.float32)

    off_s = approx_offset * scale
    win_s = window * scale
    # Clip the search to the drawn map area. A boundary street sits close to the
    # sheet edge, so an unclipped window reaches the blank collar between the map
    # and the paper edge -- which is just as ink-free as a street and wins. These
    # boundary streets are precisely the ones shared with the neighbouring sheet,
    # so losing them costs the tie points that matter most.
    lo_lim, hi_lim = 0.0, float(sh if horizontal else sw)
    if bounds is not None:
        lo_lim = max(lo_lim, bounds[0] * scale)
        hi_lim = min(hi_lim, bounds[1] * scale)
    span = sw if horizontal else sh
    seg_len = span / segments
    smooth = max(3, int(span * along_frac)) | 1

    measures = []
    for s in range(segments):
        a0, a1 = int(s * seg_len), int((s + 1) * seg_len)
        if a1 - a0 < 8:
            continue
        lo = int(max(lo_lim, off_s - win_s))
        hi = int(min(hi_lim, off_s + win_s))
        if hi - lo < 8:
            continue
        block = ink[lo:hi, a0:a1] if horizontal else ink[a0:a1, lo:hi]
        prof = block.mean(axis=1 if horizontal else 0)
        if prof.size < 8:
            continue
        prof = cv2.blur(prof.reshape(-1, 1), (1, 5)).ravel()
        # The band is the darkest-free (lowest ink) run; take a trimmed centroid
        # of the low part so a bright building edge cannot pull the centre.
        thr = prof.min() + trim * (prof.max() - prof.min())
        idx = np.where(prof <= thr)[0]
        if idx.size < 3:
            continue
        # keep the run containing the global minimum
        gmin = int(np.argmin(prof))
        keep, cur = [], [idx[0]]
        for a, b in zip(idx, idx[1:]):
            if b - a <= 2:
                cur.append(b)
            else:
                keep.append(cur); cur = [b]
        keep.append(cur)
        run = next((r for r in keep if r[0] <= gmin <= r[-1]), max(keep, key=len))
        wgt = (thr - prof[run]) + 1e-6
        centre = float(np.sum(np.array(run) * wgt) / np.sum(wgt))
        measures.append(((a0 + a1) / 2.0, lo + centre, len(run)))

    if len(measures) < min_segments:
        return None
    m = np.array(measures, dtype=float)
    A = np.column_stack([np.ones(len(m)), m[:, 0]])
    sol, *_ = np.linalg.lstsq(A, m[:, 1], rcond=None)
    resid = m[:, 1] - A @ sol
    # one robust pass: drop segments that disagree with the line
    good = np.abs(resid) <= max(3.0, 2.5 * np.std(resid))
    if good.sum() >= min_segments:
        sol, *_ = np.linalg.lstsq(A[good], m[good, 1], rcond=None)
        resid = m[good, 1] - A[good] @ sol
    off_small = float(sol[0]) + float(sol[1]) * (span / 2.0)

    # A street has DEVELOPED BLOCKS ON BOTH SIDES. The blank paper collar at the
    # edge of the sheet is just as ink-free as a street and just as long, so a
    # band search whose window reaches the margin will happily lock onto it --
    # and report a suspiciously perfect fit, because blank paper is perfectly
    # flat. Requiring ink on both flanks is what tells a street from the edge of
    # the page.
    half = max(6, int(np.median(m[:, 2]) * 0.75))
    def flank(sign):
        lo = int(off_small + sign * half)
        hi = int(off_small + sign * (half + 3 * half))
        lo, hi = (lo, hi) if lo < hi else (hi, lo)
        lo = max(0, lo); hi = min(sh if horizontal else sw, hi)
        if hi - lo < 3:
            return 0.0
        blk = ink[lo:hi, :] if horizontal else ink[:, lo:hi]
        return float(blk.mean())

    return {"offset": float(sol[0]) / scale, "slope": float(sol[1]),
            "rms": float(np.sqrt(np.mean(resid ** 2))) / scale,
            "segments": int(good.sum()), "width_px": float(np.median(m[:, 2]) / scale),
            "flank_min": float(min(flank(+1), flank(-1))),
            "flank_max": float(max(flank(+1), flank(-1)))}


def refine_grid(img, approx_streets, approx_avenues, window=170,
                street_bounds=None, avenue_bounds=None, **kw):
    """Refine a whole sheet's grid, forcing ONE rotation for the sheet.

    A scan has a single rotation. Measuring each street's slope independently
    therefore over-fits: paper cockling and lettering push individual estimates
    around, and a street that runs along the sheet edge (beside a railway or a
    wharf, where the profile is confused) can come out visibly tilted relative
    to its neighbours.

    So the slopes are pooled -- median across streets, and separately across
    avenues -- and every band is then re-fitted with that shared slope held
    fixed, leaving only its offset free. This removes the failure mode outright
    and makes a band that still disagrees stand out as a genuine outlier worth
    a human's attention rather than being quietly absorbed.

    `approx_streets` / `approx_avenues` map a label to a rough pixel position,
    normally read off the printed street names.
    """
    def measure(approx, horizontal, bounds):
        out = {}
        for label, a in approx.items():
            r = refine_band(img, a, horizontal, window=window, bounds=bounds, **kw)
            if r:
                r["approx"] = float(a)
                r["moved"] = abs(r["offset"] - float(a))
                out[label] = r
        return out

    H = measure(approx_streets, True, street_bounds)
    V = measure(approx_avenues, False, avenue_bounds)

    def pooled(bands, horizontal):
        if not bands:
            return bands, None
        slopes = np.array([b["slope"] for b in bands.values()])
        # weight by how well each band fitted; median is enough and is robust
        shared = float(np.median(slopes))
        for label, b in bands.items():
            # re-fit offset with the slope fixed: shift the band so the fitted
            # line passes through the same measured centre at mid-sheet
            mid = (img.shape[1] if horizontal else img.shape[0]) / 2.0
            centre = b["offset"] + b["slope"] * mid
            b["slope_individual"] = b["slope"]
            b["slope"] = shared
            b["offset"] = centre - shared * mid
            b["slope_deviation"] = abs(b["slope_individual"] - shared)
        return bands, shared

    H, hs = pooled(H, True)
    V, vs = pooled(V, False)
    return {"streets": H, "avenues": V,
            "shared_slope_streets": hs, "shared_slope_avenues": vs,
            "rotation_deg_streets": None if hs is None else float(np.degrees(np.arctan(hs))),
            "rotation_deg_avenues": None if vs is None else float(np.degrees(np.arctan(vs)))}


def grid_intersections(refined):
    """All street x avenue intersections of a refined grid, labelled."""
    out = []
    for sname, hl in refined["streets"].items():
        for aname, vl in refined["avenues"].items():
            p = intersect(hl, vl)
            if p is None:
                continue
            out.append({"street": sname, "avenue": aname,
                        "x": p[0], "y": p[1],
                        "quality": max(hl["rms"], vl["rms"]),
                        "slope_dev": max(hl.get("slope_deviation", 0.0),
                                         vl.get("slope_deviation", 0.0))})
    return out


def detect_grid(img, method="bands", **kw):
    """Detect both families and every intersection between them."""
    fn = detect_bands if method == "bands" else detect_lines
    hs = fn(img, horizontal=True, **kw)
    vs = fn(img, horizontal=False, **kw)
    pts = []
    for i, hl in enumerate(hs):
        for j, vl in enumerate(vs):
            p = intersect(hl, vl)
            if p is None:
                continue
            if -50 <= p[0] <= img.shape[1] + 50 and -50 <= p[1] <= img.shape[0] + 50:
                pts.append({"h_index": i, "v_index": j, "x": p[0], "y": p[1]})
    return {"horizontal": hs, "vertical": vs, "intersections": pts}


def overlay(img, grid, max_dim=1600, labels_h=None, labels_v=None):
    """Draw detected lines and intersections for visual verification.

    The detector is never trusted on its numbers alone -- this is what a human
    looks at to confirm it locked onto streets and not onto lot lines.
    """
    h, w = img.shape[:2]
    vis = img.copy()
    for i, hl in enumerate(grid["horizontal"]):
        p0 = line_point(hl, 0, True)
        p1 = line_point(hl, w, True)
        cv2.line(vis, (int(p0[0]), int(p0[1])), (int(p1[0]), int(p1[1])),
                 (220, 30, 30), 5, cv2.LINE_AA)
        if labels_h and i < len(labels_h):
            cv2.putText(vis, str(labels_h[i]), (30, int(p0[1]) - 12),
                        cv2.FONT_HERSHEY_SIMPLEX, 2.0, (220, 30, 30), 5, cv2.LINE_AA)
    for j, vl in enumerate(grid["vertical"]):
        p0 = line_point(vl, 0, False)
        p1 = line_point(vl, h, False)
        cv2.line(vis, (int(p0[0]), int(p0[1])), (int(p1[0]), int(p1[1])),
                 (30, 90, 230), 5, cv2.LINE_AA)
        if labels_v and j < len(labels_v):
            cv2.putText(vis, str(labels_v[j]), (int(p0[0]) + 10, 70),
                        cv2.FONT_HERSHEY_SIMPLEX, 2.0, (30, 90, 230), 5, cv2.LINE_AA)
    for p in grid["intersections"]:
        cv2.circle(vis, (int(p["x"]), int(p["y"])), 18, (20, 160, 60), 6, cv2.LINE_AA)
    s = min(1.0, max_dim / max(h, w))
    return cv2.resize(vis, (int(w * s), int(h * s)), interpolation=cv2.INTER_AREA)
