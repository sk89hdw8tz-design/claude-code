"""Computer-vision assistance for finding mapped regions on a scanned page.

This is an *assistant*, never an authority. It proposes polygons; a human
compares them against the Key and the sheet and then commits them to a mask
file. That division matters most on Sheet 1, where getting the region split
wrong silently drags a geographically unrelated strip of city into the mosaic.

The detector works on "inkiness" -- local edge density -- rather than colour,
because Sanborn paper tone varies wildly between scans while the density of
drafted line work between mapped and blank areas does not.
"""

from __future__ import annotations

import cv2
import numpy as np


def content_mask(img, work_width=1400, blur=3, close_frac=0.02, open_frac=0.006,
                 density_frac=0.02):
    """Binary mask of drafted content, computed at reduced scale.

    Returns (mask, scale) where `scale` converts work coordinates back to full
    resolution by dividing.
    """
    h, w = img.shape[:2]
    scale = min(1.0, work_width / float(w))
    small = cv2.resize(img, (max(1, int(w * scale)), max(1, int(h * scale))),
                       interpolation=cv2.INTER_AREA)
    gray = cv2.cvtColor(small, cv2.COLOR_RGB2GRAY) if small.ndim == 3 else small
    gray = cv2.GaussianBlur(gray, (blur | 1, blur | 1), 0)

    gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    mag = cv2.magnitude(gx, gy)

    # Edge density over a neighbourhood: blank paper has near-zero density even
    # when it is dirty, while any drafted area has a lot.  The neighbourhood
    # must be SMALLER than the narrowest gap you need to resolve -- smoothing
    # over 33 px cannot see a 35 px corridor between two panels.
    k = max(3, int(round(min(small.shape[:2]) * density_frac)) | 1)
    dens = cv2.boxFilter(mag, cv2.CV_32F, (k, k))
    dens = cv2.normalize(dens, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
    _, binm = cv2.threshold(dens, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    ck = max(3, int(round(min(small.shape[:2]) * close_frac)) | 1)
    ok = max(3, int(round(min(small.shape[:2]) * open_frac)) | 1)
    binm = cv2.morphologyEx(binm, cv2.MORPH_CLOSE,
                            cv2.getStructuringElement(cv2.MORPH_RECT, (ck, ck)))
    binm = cv2.morphologyEx(binm, cv2.MORPH_OPEN,
                            cv2.getStructuringElement(cv2.MORPH_RECT, (ok, ok)))
    return binm, scale


def propose_regions(img, min_area_frac=0.02, max_regions=6, simplify=0.004,
                    border_trim=0.02, rectangles=True, close_frac=0.008,
                    open_frac=0.006):
    """Propose mapped-region polygons in FULL-RESOLUTION source pixels.

    `rectangles=True` returns the minimum-area rotated box of each blob, which
    is usually what a Sanborn mapped area actually is and is far easier for a
    human to sanity-check and edit than a ragged contour.
    """
    h, w = img.shape[:2]
    binm, scale = content_mask(img, close_frac=close_frac, open_frac=open_frac)

    # Drop a frame so the scanner edge and printed page border -- which run
    # continuously around everything -- cannot fuse separate mapped regions
    # into one blob. This is the failure that would quietly pull Sheet 1's
    # detached section back into the retained region.
    bt = max(1, int(round(min(binm.shape[:2]) * border_trim)))
    binm[:bt, :] = 0
    binm[-bt:, :] = 0
    binm[:, :bt] = 0
    binm[:, -bt:] = 0

    n, labels, stats, _ = cv2.connectedComponentsWithStats(binm, 8)
    total = binm.shape[0] * binm.shape[1]
    out = []
    for i in range(1, n):
        area = stats[i, cv2.CC_STAT_AREA]
        if area < min_area_frac * total:
            continue
        blob = (labels == i).astype(np.uint8)
        cnts, _ = cv2.findContours(blob, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not cnts:
            continue
        c = max(cnts, key=cv2.contourArea)
        if rectangles:
            box = cv2.boxPoints(cv2.minAreaRect(c))
            poly = box
        else:
            eps = simplify * cv2.arcLength(c, True)
            poly = cv2.approxPolyDP(c, eps, True).reshape(-1, 2).astype(float)
        poly = np.asarray(poly, dtype=float) / scale
        poly[:, 0] = np.clip(poly[:, 0], 0, w - 1)
        poly[:, 1] = np.clip(poly[:, 1], 0, h - 1)
        out.append({"polygon": poly,
                    "area_px": float(cv2.contourArea(c.astype(np.float32)) / (scale ** 2)),
                    "area_frac": float(area / total),
                    "centroid": [float(poly[:, 0].mean()), float(poly[:, 1].mean())]})
    out.sort(key=lambda d: -d["area_frac"])
    return out[:max_regions]


def split_by_gaps(img, min_gap_frac=0.008, content_thresh=0.06, border_trim=0.02,
                  min_panel_frac=0.05, work_width=1400, density_frac=0.004):
    """Split a page into panels along blank corridors (projection profiles).

    Morphology alone cannot separate two mapped regions printed close together:
    the page border runs around both and a closing kernel large enough to
    consolidate street grids also bridges the gap between panels. The classic
    document-layout answer is more reliable -- look for rows (then columns)
    whose content density collapses to near zero across the full span, and cut
    there.

    Returns a list of (x0, y0, x1, y1) boxes in full-resolution source pixels.
    A page with one mapped region returns one box; Sheet 1 should return two.
    """
    h, w = img.shape[:2]
    binm, scale = content_mask(img, close_frac=0.002, open_frac=0.002,
                               work_width=work_width, density_frac=density_frac)
    bt = max(1, int(round(min(binm.shape[:2]) * border_trim)))
    core = binm[bt:-bt, bt:-bt].astype(bool)
    if core.size == 0:
        return [(0, 0, w, h)]

    def runs_of_gap(profile, min_gap):
        thr = content_thresh
        gap = profile < thr
        out, start = [], None
        for i, g in enumerate(gap):
            if g and start is None:
                start = i
            elif not g and start is not None:
                if i - start >= min_gap:
                    out.append((start, i))
                start = None
        if start is not None and len(gap) - start >= min_gap:
            out.append((start, len(gap)))
        return out

    def cut(mask, axis):
        prof = mask.mean(axis=1 - axis)
        n = mask.shape[axis]
        gaps = runs_of_gap(prof, max(3, int(round(n * min_gap_frac))))
        edges, prev = [], 0
        for g0, g1 in gaps:
            if g0 > prev:
                edges.append((prev, g0))
            prev = g1
        if prev < n:
            edges.append((prev, n))
        return [e for e in edges if (e[1] - e[0]) >= n * min_panel_frac] or [(0, n)]

    boxes = []
    for r0, r1 in cut(core, 0):
        band = core[r0:r1]
        for c0, c1 in cut(band, 1):
            boxes.append((c0, r0, c1, r1))

    out = []
    for (c0, r0, c1, r1) in boxes:
        # tighten onto actual content inside the panel, then back to full res
        sub = core[r0:r1, c0:c1]
        ys, xs = np.where(sub)
        if ys.size == 0:
            continue
        x0 = (c0 + xs.min() + bt) / scale
        x1 = (c0 + xs.max() + bt) / scale
        y0 = (r0 + ys.min() + bt) / scale
        y1 = (r0 + ys.max() + bt) / scale
        if (x1 - x0) * (y1 - y0) < min_panel_frac * w * h * 0.5:
            continue
        out.append((float(x0), float(y0), float(x1), float(y1)))
    return out or [(0.0, 0.0, float(w), float(h))]


def order_ring(poly):
    """Order a quadrilateral's vertices clockwise from the top-left corner."""
    p = np.asarray(poly, dtype=float)
    c = p.mean(axis=0)
    ang = np.arctan2(p[:, 1] - c[1], p[:, 0] - c[0])
    p = p[np.argsort(ang)]
    start = int(np.argmin(p[:, 0] + p[:, 1]))
    p = np.roll(p, -start, axis=0)
    return np.vstack([p, p[:1]])


def shrink_ring(ring, inset):
    """Pull a ring inward by `inset` pixels, to keep a printed border out."""
    r = np.asarray(ring, dtype=float)
    closed = np.allclose(r[0], r[-1])
    pts = r[:-1] if closed else r
    c = pts.mean(axis=0)
    v = pts - c
    n = np.linalg.norm(v, axis=1, keepdims=True)
    n = np.where(n < 1e-9, 1.0, n)
    pts = pts - v / n * inset
    return np.vstack([pts, pts[:1]])


def preview(img, regions, keep_flags=None, max_dim=1600):
    """Annotated preview: kept regions in green, excluded ones in red."""
    h, w = img.shape[:2]
    s = min(1.0, max_dim / max(h, w))
    vis = cv2.resize(img, (int(w * s), int(h * s)), interpolation=cv2.INTER_AREA)
    overlay = vis.copy()
    for i, reg in enumerate(regions):
        poly = np.asarray(reg["polygon"] if isinstance(reg, dict) else reg, float) * s
        keep = True if keep_flags is None else bool(keep_flags[i])
        col = (40, 170, 60) if keep else (215, 45, 45)
        pts = np.round(poly).astype(np.int32)
        cv2.fillPoly(overlay, [pts], col)
        cv2.polylines(vis, [pts], True, col, 3, cv2.LINE_AA)
    vis = cv2.addWeighted(overlay, 0.22, vis, 0.78, 0)
    for i, reg in enumerate(regions):
        poly = np.asarray(reg["polygon"] if isinstance(reg, dict) else reg, float) * s
        keep = True if keep_flags is None else bool(keep_flags[i])
        label = reg.get("label", f"region {i}") if isinstance(reg, dict) else f"region {i}"
        txt = f"{label}: {'RETAINED' if keep else 'EXCLUDED'}"
        org = (int(poly[:, 0].min()) + 8, int(poly[:, 1].min()) + 26)
        cv2.putText(vis, txt, org, cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 4, cv2.LINE_AA)
        cv2.putText(vis, txt, org, cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                    (40, 140, 50) if keep else (200, 30, 30), 2, cv2.LINE_AA)
    return vis
