"""Quality control: residuals, cross-validation, and seam inspection.

Two ideas do the real work here.

*Held-out check points.*  Residuals at the points a transform was fitted to
always look good; they are what the fit minimised.  So the adjustment is also
run with a fraction of tie points withheld, and the error is measured at those
unseen points.  That is the number worth quoting, and it is what
`crossvalidate` produces.

*Seam panels.*  Every junction is cropped at full resolution and rendered three
ways -- sheet A alone, sheet B alone, and the merged mosaic -- so a human can
see whether a street actually runs through or merely appears to because one
sheet is painted over the other's error.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np
import rasterio
from rasterio.windows import Window

from . import geometry as G


# --------------------------------------------------------------------------
# residual analysis
# --------------------------------------------------------------------------
def residual_report(residuals, thresholds=(5.0, 15.0)):
    """Summarise residuals overall and per sheet pair."""
    good, gross = thresholds
    by_pair = defaultdict(list)
    for r in residuals:
        key = "|".join(sorted([str(r["sheet_a"]), str(r.get("sheet_b") or "ANCHOR")]))
        by_pair[key].append(r["residual"])

    def stat(vals):
        a = np.asarray(vals, dtype=float)
        if a.size == 0:
            return None
        return {"n": int(a.size), "median": float(np.median(a)),
                "mean": float(a.mean()), "rms": float(np.sqrt((a ** 2).mean())),
                "p90": float(np.percentile(a, 90)), "max": float(a.max()),
                "over_good": int((a > good).sum()), "over_gross": int((a > gross).sum())}

    allv = [r["residual"] for r in residuals]
    return {
        "thresholds": {"good_px": good, "gross_px": gross},
        "overall": stat(allv),
        "by_pair": {k: stat(v) for k, v in sorted(by_pair.items())},
        "worst": sorted(
            ({"label": r["label"], "sheets": [r["sheet_a"], r.get("sheet_b")],
              "residual": r["residual"], "dx": r["dx"], "dy": r["dy"]}
             for r in residuals), key=lambda d: -d["residual"])[:20],
    }


def crossvalidate(sheets, ties, anchors=None, kind="affine", folds=5, seed=0, **kw):
    """K-fold cross-validation over tie points.

    Each fold refits with a slice of the ties removed and measures the error
    where those removed points land.  This is the only residual number that
    cannot be improved by simply adding more free parameters, so it is the
    honest basis for choosing between similarity, affine and projective.
    """
    ties = list(ties)
    if len(ties) < folds * 2:
        folds = max(2, len(ties) // 2) if len(ties) >= 4 else 0
    if folds < 2:
        return {"folds": 0, "note": "too few tie points to cross-validate",
                "held_out": None}
    rng = np.random.default_rng(seed)
    order = rng.permutation(len(ties))
    held = []
    for f in range(folds):
        test_idx = set(order[f::folds].tolist())
        train = [t for i, t in enumerate(ties) if i not in test_idx]
        test = [t for i, t in enumerate(ties) if i in test_idx]
        if not train or not test:
            continue
        try:
            res = G.adjust(sheets, train, anchors, kind=kind, **kw)
        except Exception as exc:                      # pragma: no cover
            return {"folds": folds, "error": str(exc), "held_out": None}
        T = res["transforms"]
        for t in test:
            if t.a not in T or t.b not in T:
                continue
            d = G.apply(T[t.a], [t.pa])[0] - G.apply(T[t.b], [t.pb])[0]
            held.append({"label": t.label, "sheet_a": t.a, "sheet_b": t.b,
                         "dx": float(d[0]), "dy": float(d[1]),
                         "residual": float(np.hypot(*d)), "weight": t.weight})
    if not held:
        return {"folds": folds, "held_out": None, "note": "no held-out points evaluated"}
    return {"folds": folds, "n": len(held), "held_out": G._stats(held),
            "detail": held}


def select_transform(sheets, ties, anchors=None, candidates=("similarity", "affine", "projective"),
                     conformal_weight=0.0, folds=5, seed=0, tolerance=0.9,
                     plausible_limits=None, **kw):
    """Choose the least deformable model that measurably earns its freedom.

    Order of preference is fixed (similarity, then affine, then projective) and
    a richer model is only accepted if it improves HELD-OUT error by more than
    `tolerance`.

    Three gates run before any residual is compared, and each can disqualify a
    model outright:

      * rank -- an adjustment that is rank deficient for the observations
        available has residuals that mean nothing (abutting sheets give only
        collinear ties, which per-sheet affine cannot resolve);
      * determinacy -- a sheet with fewer points than the model has freedom;
      * plausibility -- a solved sheet rotated 90 degrees, mirrored, or scaled
        by half is not a distorted scan. This gate matters most for the richest
        model, which can always drive fitting error down by folding sheets in
        ways no scanner produced. Residual quality is never allowed to
        outrank physical possibility.
    """
    results = []
    for kind in candidates:
        rank = G.design_rank_report(sheets, ties, anchors, kind=kind,
                                    conformal_weight=conformal_weight)
        entry = {"kind": kind, "rank": rank, "usable": rank["ok"]}
        if not rank["ok"]:
            entry["reason"] = rank.get("note", "rank deficient")
            results.append(entry)
            continue
        det = G.check_determinacy(sheets, ties, anchors, kind=kind)
        if det["underdetermined"]:
            entry["usable"] = False
            entry["reason"] = f"sheets with too few points: {det['underdetermined']}"
            results.append(entry)
            continue
        cv = crossvalidate(sheets, ties, anchors, kind=kind, folds=folds, seed=seed,
                           conformal_weight=conformal_weight, **kw)
        fit = G.adjust(sheets, ties, anchors, kind=kind,
                       conformal_weight=conformal_weight, **kw)
        entry["crossval"] = cv
        entry["fit_stats"] = fit["stats"]
        entry["score"] = (cv["held_out"] or {}).get("median")

        implausible = {s: G.plausibility_flags(H, plausible_limits)
                       for s, H in fit["transforms"].items()}
        implausible = {s: f for s, f in implausible.items() if f}
        entry["implausible"] = implausible
        if implausible:
            entry["usable"] = False
            entry["reason"] = (
                "physically implausible sheet geometry: "
                + ", ".join(f"{s}({'/'.join(f)})" for s, f in sorted(implausible.items())))
        results.append(entry)

    usable = [r for r in results if r.get("usable") and r.get("score") is not None]
    chosen = None
    for r in usable:
        if chosen is None:
            chosen = r
        elif r["score"] < chosen["score"] * tolerance:
            chosen = r
    if chosen is None and usable:
        chosen = usable[0]
    return {"chosen": chosen["kind"] if chosen else None, "candidates": results}


# --------------------------------------------------------------------------
# seam geometry
# --------------------------------------------------------------------------
def contact_type(ring_a, ring_b, corner_fraction=0.15):
    """Whether two regions share an edge or merely touch at a corner.

    Diagonal neighbours in a sheet grid overlap only near a corner. Such a pair
    carries very few tie points and is the least-constrained part of the
    network, so a larger mismatch there is expected and is not evidence that
    the mosaic is wrong. Reporting it next to a true edge seam, without saying
    which is which, invites exactly the wrong conclusion.
    """
    from shapely.geometry import Polygon

    pa, pb = Polygon(ring_a).buffer(0), Polygon(ring_b).buffer(0)
    inter = pa.intersection(pb)
    if inter.is_empty:
        return {"contact": "none", "overlap_area": 0.0, "extent_ratio": 0.0}
    # Compare the overlap's long side against the smaller sheet's long side.
    ix0, iy0, ix1, iy1 = inter.bounds
    ax0, ay0, ax1, ay1 = pa.bounds
    bx0, by0, bx1, by1 = pb.bounds
    ext = max(ix1 - ix0, iy1 - iy0)
    ref = min(max(ax1 - ax0, ay1 - ay0), max(bx1 - bx0, by1 - by0))
    ratio = float(ext / ref) if ref > 0 else 0.0
    return {"contact": "corner" if ratio < corner_fraction else "edge",
            "overlap_area": float(inter.area), "extent_ratio": ratio}


def shared_boundary_points(ring_a, ring_b, samples=5, tol=3.0):
    """Sample points where two mapped regions meet in the plane.

    Uses the intersection of the two polygons when they overlap, and otherwise
    the closest approach between their edges -- so it works for sheets that
    abut as well as sheets that overlap.
    """
    from shapely.geometry import Polygon

    pa, pb = Polygon(ring_a), Polygon(ring_b)
    if not pa.is_valid:
        pa = pa.buffer(0)
    if not pb.is_valid:
        pb = pb.buffer(0)
    inter = pa.intersection(pb)
    geom = None
    if not inter.is_empty and inter.area > 1.0:
        geom = inter.exterior if hasattr(inter, "exterior") else None
        line = pa.exterior.intersection(pb.buffer(tol))
    else:
        line = pa.exterior.intersection(pb.buffer(max(tol, 6.0)))
    if line.is_empty:
        return []
    geoms = list(getattr(line, "geoms", [line]))
    pts = []
    total = sum(g.length for g in geoms if hasattr(g, "length")) or 1.0
    for g in geoms:
        if not hasattr(g, "interpolate") or g.length <= 0:
            continue
        n = max(1, int(round(samples * g.length / total)))
        for i in range(n):
            f = (i + 0.5) / n
            p = g.interpolate(f, normalized=True)
            pts.append((float(p.x), float(p.y)))
    return pts


def read_crop(path, col, row, size):
    """Read a `size` square centred on (col,row); returns RGBA or None.

    The read is BOUNDLESS and pads with zeros (transparent) outside the
    raster.  It must never slide the window back inside instead.  Each warped
    region is stored windowed to its own footprint, so a crop centred on a
    seam always overruns the edge of at least one contributor -- that is what
    a seam IS.  Clamping the window to fit silently returned a view up to half
    a crop away from the requested point, so the "A only", "B only" and
    "merged" tiles of a seam panel showed three different places while looking
    like an aligned comparison.  Padding shows the truth: the contributor
    stops here, and its absence is visible as blank rather than disguised as
    content.
    """
    half = size // 2
    with rasterio.open(path) as ds:
        c0, r0 = int(col) - half, int(row) - half
        arr = ds.read(window=Window(c0, r0, size, size),
                      boundless=True, fill_value=0)
    return np.transpose(arr, (1, 2, 0))


def flatten_rgba(arr, bg=(255, 255, 255)):
    rgb = arr[..., :3].astype(np.float32)
    if arr.shape[2] >= 4:
        a = arr[..., 3:4].astype(np.float32) / 255.0
        rgb = rgb * a + np.array(bg, dtype=np.float32) * (1 - a)
    return np.clip(rgb, 0, 255).astype(np.uint8)


def label_image(img, text, height=26):
    """Caption strip above an image tile."""
    h, w = img.shape[:2]
    bar = np.full((height, w, 3), 28, dtype=np.uint8)
    cv2.putText(bar, text[:120], (6, height - 8), cv2.FONT_HERSHEY_SIMPLEX,
                0.5, (235, 235, 235), 1, cv2.LINE_AA)
    return np.vstack([bar, img])


def seam_panel(mosaic_path, warped_paths, plane_pt, grid, size=520, zoom=2,
               labels=("A", "B"), title=""):
    """A single junction rendered as: sheet A only | sheet B only | merged.

    Seeing each contributor alone is what distinguishes a street that truly
    continues from one that only looks continuous because the upper sheet hides
    the lower sheet's misalignment.
    """
    col, row = grid.plane_to_pixel([plane_pt])[0]
    tiles = []
    for path, lab in zip(warped_paths, labels):
        with rasterio.open(path) as ds:
            gt = ds.transform
            c = (plane_pt[0] - gt.c) / gt.a
            r = (plane_pt[1] - gt.f) / gt.e
        crop = read_crop(path, c, r, size)
        if crop is None:
            crop = np.zeros((size, size, 4), dtype=np.uint8)
        tiles.append(label_image(flatten_rgba(crop), f"{lab} only"))
    merged = read_crop(mosaic_path, col, row, size)
    if merged is None:
        merged = np.zeros((size, size, 4), dtype=np.uint8)
    tiles.append(label_image(flatten_rgba(merged), "merged mosaic"))

    panel = np.hstack(tiles)
    if zoom != 1:
        panel = cv2.resize(panel, None, fx=zoom, fy=zoom, interpolation=cv2.INTER_NEAREST)
    if title:
        panel = label_image(panel, title, height=32)
    return panel


def seam_discontinuity(mosaic_path, grid, plane_pt, seam_dir, size=256):
    """Measure how much the image jumps across a seam.

    Compares mean absolute pixel difference between the two columns adjacent to
    the seam against the same statistic taken elsewhere in the crop.  A ratio
    near 1 means the join is invisible at pixel level; a large ratio means a
    genuine step.  Reported as a diagnostic, never as a pass/fail on its own --
    a real 1889 drafting discrepancy will also show up here.
    """
    col, row = grid.plane_to_pixel([plane_pt])[0]
    crop = read_crop(mosaic_path, col, row, size)
    if crop is None:
        return None
    # Skip samples that include the mosaic's outer edge.  Transparent pixels
    # flatten to the background colour, and the resulting step against real map
    # content is enormous -- but it is the edge of the map, not a bad join.
    # Measuring it anyway produces alarming ratios for a seam that is fine.
    if crop.shape[2] >= 4:
        transparent = float((crop[..., 3] == 0).mean())
        if transparent > 0.02:
            return {"across_seam": None, "typical_adjacent": None, "ratio": None,
                    "skipped": "sample touches the mosaic edge (transparent area)",
                    "transparent_fraction": transparent}
    img = cv2.cvtColor(flatten_rgba(crop), cv2.COLOR_RGB2GRAY).astype(np.float32)
    d = np.asarray(seam_dir, dtype=float)
    n = np.hypot(*d)
    if n < 1e-9:
        return None
    # Rotate so the seam runs vertically, then compare across the centre column.
    ang = np.degrees(np.arctan2(d[1], d[0]))
    M = cv2.getRotationMatrix2D((size / 2, size / 2), ang - 90.0, 1.0)
    rot = cv2.warpAffine(img, M, (size, size), flags=cv2.INTER_LINEAR,
                         borderMode=cv2.BORDER_REFLECT)
    mid = size // 2
    band = rot[size // 4: 3 * size // 4]

    # Separate the two things that can differ across a seam.
    #
    # TONE OFFSET: the two sheets were scanned on different days and their paper
    # reads slightly differently. That is real archival information and this
    # project deliberately preserves it -- no exposure matching is applied. It
    # must therefore be reported, not counted as a defect.
    #
    # STRUCTURAL BREAK: linework that does not line up. That is the actual
    # failure we are hunting.
    #
    # Measuring raw intensity conflates the two: a uniform tone difference in
    # blank paper produces a large "step" with nothing structurally wrong. So
    # each side is centred on its own median first, which cancels tone and
    # leaves geometry.
    left, right = band[:, :mid], band[:, mid:]
    tone = float(np.median(right) - np.median(left))
    lc = left - np.median(left)
    rc = right - np.median(right)
    centred = np.hstack([lc, rc])

    across = float(np.mean(np.abs(centred[:, mid] - centred[:, mid - 1])))
    others = [float(np.mean(np.abs(centred[:, c] - centred[:, c - 1])))
              for c in range(size // 4, 3 * size // 4) if abs(c - mid) > 3]
    typical = float(np.median(others)) if others else 0.0

    out = {"across_seam": across, "typical_adjacent": typical,
           "tone_offset": tone, "ratio": None}
    # The ratio needs something to normalise against. Over near-blank paper the
    # denominator collapses and any tiny difference reports as a huge multiple,
    # which is noise dressed as a finding.
    if typical < 0.5 or across < 2.0:
        out["skipped"] = (f"uninformative sample: structural step {across:.2f} "
                          f"grey levels against local variation {typical:.2f} "
                          f"(tone offset {tone:+.1f}) -- too little content here "
                          f"to judge")
        return out
    out["ratio"] = float(across / typical)
    return out


def write_json(path, obj):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, default=float) + "\n", encoding="utf-8")
    return p
