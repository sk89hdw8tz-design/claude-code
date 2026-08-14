"""Tie points and control points: storage, refinement, and overlap search.

A tie point is one physical feature -- a street-centreline crossing, a block
corner, a wharf head -- identified on two sheets.  Giving that feature a single
identity is what mathematically forces the two sheets to meet, so tie points,
not image similarity, are the backbone of the reconstruction.

Refinement here is deliberately *predictive*: it never searches blindly for a
match.  It takes the current estimate of how the two sheets relate, warps a
patch of one into the other's frame, and only then correlates.  That keeps
matching honest on cartographic sheets, where a blind search happily locks onto
the wrong one of fifty near-identical city blocks.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import cv2
import numpy as np

from . import geometry as G

GCP_FIELDS = [
    "point_id", "sheet", "region", "role",
    "src_x", "src_y",
    "ref_x", "ref_y", "ref_lon", "ref_lat",
    "street_a", "street_b", "feature",
    "method", "confidence", "selected_by",
    "residual_px", "accepted", "note",
]


# --------------------------------------------------------------------------
# storage
# --------------------------------------------------------------------------
def write_gcp_csv(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        # lineterminator="\n": the csv module defaults to CRLF, which makes
        # these files churn in version control on non-Windows checkouts.
        w = csv.DictWriter(fh, fieldnames=GCP_FIELDS, extrasaction="ignore",
                           lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in GCP_FIELDS})
    return path


def read_gcp_csv(path):
    with Path(path).open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    for r in rows:
        for k in ("src_x", "src_y", "ref_x", "ref_y", "ref_lon", "ref_lat", "residual_px"):
            if r.get(k) not in (None, ""):
                r[k] = float(r[k])
        r["accepted"] = str(r.get("accepted", "true")).strip().lower() not in ("false", "0", "no")
    return rows


def write_gcp_geojson(path, rows, pixel_space=True):
    """Companion GeoJSON for viewing control points in QGIS.

    Written in source-pixel space by default, matching the mask convention, so
    points and masks can be inspected in the same view.
    """
    feats = []
    for r in rows:
        if pixel_space:
            xy = [float(r["src_x"]), float(r["src_y"])]
        else:
            if r.get("ref_lon") in (None, ""):
                continue
            xy = [float(r["ref_lon"]), float(r["ref_lat"])]
        feats.append({"type": "Feature",
                      "geometry": {"type": "Point", "coordinates": xy},
                      "properties": {k: r.get(k, "") for k in GCP_FIELDS}})
    doc = {"type": "FeatureCollection",
           "space": "source_pixels(x,y down)" if pixel_space else "EPSG:4326",
           "features": feats}
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    return path


def ties_from_rows(rows, min_confidence=None):
    """Group control rows sharing a point_id into TiePoint observations.

    Two sheets recording the same `point_id` is exactly the statement "this is
    the same feature", which is where the sheet-to-sheet constraint comes from.
    """
    by_id = {}
    for r in rows:
        if not r.get("accepted", True):
            continue
        by_id.setdefault(r["point_id"], []).append(r)
    ties = []
    for pid, obs in by_id.items():
        if len(obs) < 2:
            continue
        for i in range(len(obs)):
            for j in range(i + 1, len(obs)):
                a, b = obs[i], obs[j]
                if a["region"] == b["region"]:
                    continue
                w = min(_conf_weight(a.get("confidence")), _conf_weight(b.get("confidence")))
                ties.append(G.TiePoint(a["region"], (a["src_x"], a["src_y"]),
                                       b["region"], (b["src_x"], b["src_y"]),
                                       weight=w, label=pid))
    return ties


def _conf_weight(c):
    return {"high": 1.0, "medium": 0.5, "low": 0.2}.get(str(c or "").strip().lower(), 1.0)


# --------------------------------------------------------------------------
# refinement
# --------------------------------------------------------------------------
def _subpixel_peak(resp, iy, ix):
    """Parabolic fit around the correlation peak for sub-pixel location."""
    dy = dx = 0.0
    if 0 < ix < resp.shape[1] - 1:
        l, c, r = float(resp[iy, ix - 1]), float(resp[iy, ix]), float(resp[iy, ix + 1])
        den = (l - 2 * c + r)
        if abs(den) > 1e-12:
            dx = 0.5 * (l - r) / den
    if 0 < iy < resp.shape[0] - 1:
        u, c, d = float(resp[iy - 1, ix]), float(resp[iy, ix]), float(resp[iy + 1, ix])
        den = (u - 2 * c + d)
        if abs(den) > 1e-12:
            dy = 0.5 * (u - d) / den
    return float(np.clip(dx, -1, 1)), float(np.clip(dy, -1, 1))


def _patch(img, centre, half, H=None, out_half=None):
    """Sample a square patch centred on `centre`.

    With `H` (a source->target map) the patch is resampled so it appears in the
    target frame, which is what makes two sheets at different rotations and
    scales directly comparable.
    """
    out_half = out_half or half
    size = 2 * out_half + 1
    cx, cy = float(centre[0]), float(centre[1])
    if H is None:
        xs = np.arange(size, dtype=np.float32) - out_half + cx
        ys = np.arange(size, dtype=np.float32) - out_half + cy
        mx, my = np.meshgrid(xs, ys)
    else:
        Hinv = np.linalg.inv(H)
        tx, ty = G.apply(H, [(cx, cy)])[0]
        xs = np.arange(size, dtype=np.float64) - out_half + tx
        ys = np.arange(size, dtype=np.float64) - out_half + ty
        U, V = np.meshgrid(xs, ys)
        den = Hinv[2, 0] * U + Hinv[2, 1] * V + Hinv[2, 2]
        den = np.where(np.abs(den) < 1e-12, 1e-12, den)
        mx = ((Hinv[0, 0] * U + Hinv[0, 1] * V + Hinv[0, 2]) / den).astype(np.float32)
        my = ((Hinv[1, 0] * U + Hinv[1, 1] * V + Hinv[1, 2]) / den).astype(np.float32)
    return cv2.remap(img, mx.astype(np.float32), my.astype(np.float32),
                     cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT,
                     borderValue=0)


def _gray(img):
    if img.ndim == 3:
        return cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    return img


def refine_pair(img_a, pt_a, img_b, pt_b, H_a=None, H_b=None,
                patch=48, search=24, min_score=0.35):
    """Refine `pt_b` so the feature at `pt_a` lands on it.

    `H_a`/`H_b` are the current sheet transforms into the common plane; when
    given, both patches are compared in that plane so differing rotation and
    scale between the sheets stop mattering.

    Returns dict(dx, dy, score, refined) with the correction expressed in
    sheet-B source pixels, or score=None when correlation is too weak to trust.
    """
    ga, gb = _gray(img_a), _gray(img_b)
    if H_a is not None and H_b is not None:
        # Compare both sheets in sheet-B's frame: map A -> plane -> B.
        A_to_B = np.linalg.inv(H_b) @ H_a
        tmpl = _patch(ga, pt_a, patch, H=A_to_B)
    else:
        tmpl = _patch(ga, pt_a, patch)
    win = _patch(gb, pt_b, patch + search)
    if tmpl.std() < 3.0 or win.std() < 3.0:
        return {"dx": 0.0, "dy": 0.0, "score": None, "refined": tuple(pt_b),
                "reason": "flat patch - no usable structure"}
    resp = cv2.matchTemplate(win.astype(np.float32), tmpl.astype(np.float32),
                             cv2.TM_CCOEFF_NORMED)
    _, maxv, _, maxloc = cv2.minMaxLoc(resp)
    ix, iy = maxloc
    sx, sy = _subpixel_peak(resp, iy, ix)
    dx = (ix + sx) - search
    dy = (iy + sy) - search
    if maxv < min_score:
        return {"dx": 0.0, "dy": 0.0, "score": float(maxv), "refined": tuple(pt_b),
                "reason": f"correlation {maxv:.2f} below {min_score}"}
    return {"dx": float(dx), "dy": float(dy), "score": float(maxv),
            "refined": (float(pt_b[0] + dx), float(pt_b[1] + dy)), "reason": ""}


def auto_tiepoints_in_overlap(img_a, img_b, H_a, H_b, plane_polygon,
                              grid=6, patch=48, search=20, min_score=0.5,
                              margin=60):
    """Propose tie points where two sheets genuinely overlap.

    Supplementary only: it needs a usable prior (H_a, H_b) and real shared
    content.  On sheets that merely abut it will find nothing, which is the
    correct outcome rather than a failure.
    """
    poly = np.asarray(plane_polygon, dtype=float)
    if len(poly) < 3:
        return []
    x0, y0 = poly[:, 0].min(), poly[:, 1].min()
    x1, y1 = poly[:, 0].max(), poly[:, 1].max()
    ha, wa = img_a.shape[:2]
    hb, wb = img_b.shape[:2]
    Ainv, Binv = np.linalg.inv(H_a), np.linalg.inv(H_b)
    out = []
    for gy in range(grid):
        for gx in range(grid):
            u = x0 + (x1 - x0) * (gx + 0.5) / grid
            v = y0 + (y1 - y0) * (gy + 0.5) / grid
            pa = G.apply(Ainv, [(u, v)])[0]
            pb = G.apply(Binv, [(u, v)])[0]
            if not (margin < pa[0] < wa - margin and margin < pa[1] < ha - margin):
                continue
            if not (margin < pb[0] < wb - margin and margin < pb[1] < hb - margin):
                continue
            r = refine_pair(img_a, pa, img_b, pb, H_a, H_b, patch, search, min_score)
            if r["score"] is None or r["score"] < min_score:
                continue
            out.append({"pa": (float(pa[0]), float(pa[1])), "pb": r["refined"],
                        "score": r["score"], "plane": (float(u), float(v))})
    return out
