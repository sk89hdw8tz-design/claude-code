#!/usr/bin/env python3
"""Sheet-5 two-panel similarity fit against the frozen block (Galveston 1912).

Sheet 5 (scan 6653x7795) carries TWO drafted panels: 5A page-left and 5B
page-right of the drafted divider rule (centerline ~ x = 3789 + 0.0099*y;
polygons in fable_review/sheet05_candidate_regions.geojson).  Each panel gets
its OWN 4-parameter similarity into the mosaic frame, fitted against the
FROZEN block-sheet transforms read from 40_solve/output/transforms.json
(never refitted here).  Sheet 5 is drafted at 100 ft/in vs the block's
50 ft/in, so panel scale is expected ~2x the block sheets'; scale AND
rotation are left free per panel.

Model (per panel):

    p_mosaic = [[a, -b], [b, a]] @ (p_sheet5_raw - center_panel) + (tx, ty)

center_panel = area centroid of the panel polygon (regions A / B of the
candidate-regions GeoJSON); the composed raw-pixel transform
(raw.t = t - R @ center_panel) is also written -- downstream raster code
must use the raw block.

Observations (ACCEPTED anchors only; block side held fixed):

* along -- per anchor per face: the face-segment midpoints on the two plates
  are corresponding-LINE observations; residual is the component of
  T_5(mid_5) - T_block(mid_block) along the seam direction u_along, where
  u_along is the frozen block sheet's page-y axis mapped to the mosaic.
  Along-frontage is page-y on BOTH sides (D-008); this is VERIFIED from the
  control geometry at load time (anchor spread must be dominated by page-y on
  both sides), not assumed.
* across -- per anchor, one row (the face with the best combined sigma,
  mirroring the block solver's one-across-per-anchor rule): both plates'
  face segments terminate at the SAME drafted corner -- the Ave A east-face
  corner, the smaller-x endpoint on both sides since both plates are drafted
  bay-page-left (checked against the recorded `measured_at`/orientation
  geometry).  Residual is the u_across component of
  T_5(corner_5) - T_block(corner_block) with a ZERO constructed offset: the
  plates draft the same corner line, so no street-width x kappa term is
  needed (kappa does not enter this fit at all).  The recorded drafted
  widths feed the scale diagnostics and the across sigma floor, not offsets.
* pp_along / pp_across -- where the record's evidence marks genuine
  duplicated / overlapping ground (the 5A-7 bay strip; detected from the
  record notes via the word "overlap"), DIRECT point-to-point residuals in
  both components at the corresponding corner endpoints of BOTH faces
  replace the along+across scheme.  Midpoints are NOT used as pp points:
  the two plates' segments span different lengths of the same face line, so
  only the corner endpoints correspond.

Weighting: recorded `sigma_along_px` per side, with face-specific overrides
parsed from `sigma_basis` prose ("sigma N for that face").  Native-px sigmas
are propagated to mosaic px with the frozen block scale and the CURRENT
panel scale inside the IRLS loop (seeded at 2.0); across-type rows carry a
12 px mosaic floor (mirrors the block solver's amendment-5 floor).  Huber
(delta 2.5 on normalized residuals) IRLS; downweights are logged, never
dropped.  Covariance = (J^T W J)^-1 scaled by the robust variance factor
s0^2 = sum(w_h r_n^2) / dof, as in the block solver.

Fitted with NOTHING from: pair_05B_13.json (CONTEXT_ONLY attachment) and
cross_panel_05.json.  Both are evaluated under the solved transforms and
reported.  Sheet 13 has no frozen transform (it is outside the 12-sheet
block), so the 5B-13 report is translation-free: relative anchor-separation
comparison + drafted width ratios; if a future freeze adds sheet 13 to
transforms.json, this code automatically produces the full residual table
instead.

RERUN: this fit is strictly downstream of the block freeze.  After any block
re-solve (new transforms.json) rerun:

    /home/user/g1912/venv/bin/python 40_solve/fit_sheet5.py

Outputs (40_solve/output_sheet5/) record the sha256 of the transforms.json
actually used, so a stale fit is detectable.
"""

import argparse
import glob
import hashlib
import json
import math
import os
import re
import sys

import numpy as np

# ----------------------------------------------------------------------------
# Constants
# ----------------------------------------------------------------------------

HUBER_DELTA = 2.5                 # normalized-residual units (block solver)
IRLS_ITERATIONS = 12
SIGMA_ACROSS_FLOOR_PX = 12.0      # mosaic px; mirrors block amendment-5 floor
SIGMA_ALONG_FALLBACK_PX = 4.0     # only if a record omits sigma_along_px
PANEL_SCALE_INIT = 2.0            # 100 ft/in vs 50 ft/in
PANEL_NATIVE_PX_PER_FT = 3.09     # ~309 px / 100 ft (recorded plate scale)
BLOCK_NATIVE_PX_PER_FT = 6.18     # ~618 px / 100 ft
CROSS_PANEL_FLAG_PX = 30.0        # mosaic px (~5 ft); flags cross-panel pairs
PANEL_IDS = ("5A", "5B")

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_THIS_DIR)
DEFAULT_CONTROLS = os.path.join(_REPO, "30_controls", "verified")
DEFAULT_TRANSFORMS = os.path.join(_THIS_DIR, "output", "transforms.json")
DEFAULT_REGIONS = os.path.join(_REPO, "fable_review",
                               "sheet05_candidate_regions.geojson")
DEFAULT_OUT = os.path.join(_THIS_DIR, "output_sheet5")


# ----------------------------------------------------------------------------
# Small helpers
# ----------------------------------------------------------------------------

def rot(a, b):
    return np.array([[a, -b], [b, a]], dtype=float)


def apply_raw(T, p):
    """Apply a raw-pixel similarity dict {a,b,tx,ty} to point p."""
    return rot(T["a"], T["b"]) @ np.asarray(p, float) + np.array([T["tx"],
                                                                 T["ty"]])


def row_coeffs(u, q):
    """d(u . (R q + t)) / d(a, b, tx, ty) for centered point q."""
    return np.array([u[0] * q[0] + u[1] * q[1],
                     -u[0] * q[1] + u[1] * q[0],
                     u[0], u[1]])


def polygon_centroid(coords):
    P = np.asarray(coords, dtype=float)
    if np.allclose(P[0], P[-1]):
        P = P[:-1]
    x, y = P[:, 0], P[:, 1]
    xn, yn = np.roll(x, -1), np.roll(y, -1)
    cr = x * yn - xn * y
    area2 = cr.sum()
    if abs(area2) < 1e-9:
        raise ValueError("degenerate panel polygon")
    cx = ((x + xn) * cr).sum() / (3.0 * area2)
    cy = ((y + yn) * cr).sum() / (3.0 * area2)
    return np.array([cx, cy])


def point_in_polygon(pt, coords):
    P = np.asarray(coords, dtype=float)
    if np.allclose(P[0], P[-1]):
        P = P[:-1]
    x, y = float(pt[0]), float(pt[1])
    inside = False
    n = len(P)
    for i in range(n):
        x1, y1 = P[i]
        x2, y2 = P[(i + 1) % n]
        if (y1 > y) != (y2 > y):
            xin = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
            if x < xin:
                inside = not inside
    return inside


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def rms(vals):
    v = np.asarray(vals, dtype=float)
    return float(np.sqrt(np.mean(v ** 2))) if v.size else float("nan")


# ----------------------------------------------------------------------------
# Loading: frozen block transforms, panel regions
# ----------------------------------------------------------------------------

def load_block_transforms(path):
    """Read the frozen block solve.  Returns ({sheet_int: raw transform dict},
    meta).  Prefers the composed `raw` block; falls back to composing it from
    centered params + the convention center."""
    with open(path) as fh:
        data = json.load(fh)
    center = np.asarray(data.get("convention", {}).get("center", [0.0, 0.0]),
                        dtype=float)
    sheets = {}
    for key, rec in data.get("sheets", {}).items():
        a, b = float(rec["a"]), float(rec["b"])
        if isinstance(rec.get("raw"), dict):
            tx, ty = float(rec["raw"]["tx"]), float(rec["raw"]["ty"])
        else:  # compose raw from centered: raw.t = t - R @ center
            t = np.array([float(rec["tx"]), float(rec["ty"])])
            traw = t - rot(a, b) @ center
            tx, ty = float(traw[0]), float(traw[1])
        sheets[int(key)] = {
            "a": a, "b": b, "tx": tx, "ty": ty,
            "s": math.hypot(a, b),
            "theta_deg": math.degrees(math.atan2(b, a)),
        }
    meta = {
        "path": os.path.abspath(path),
        "sha256": sha256_of(path),
        "kappa_px_per_ft": data.get("kappa_px_per_ft"),
        "kappa_prior_dominated": data.get("kappa_prior_dominated"),
        "sheets_available": sorted(sheets),
    }
    return sheets, meta


def load_regions(path):
    """Panel polygons + centroids from the candidate-regions GeoJSON.
    Region ids 'A'/'B' map to panels '5A'/'5B'."""
    with open(path) as fh:
        gj = json.load(fh)
    panels = {}
    divider = None
    for feat in gj.get("features", []):
        rid = str(feat.get("properties", {}).get("region_id", ""))
        geom = feat.get("geometry", {})
        if rid in ("A", "B") and geom.get("type") == "Polygon":
            ring = geom["coordinates"][0]
            panels["5" + rid] = {
                "polygon": [list(map(float, p)) for p in ring],
                "center": polygon_centroid(ring),
            }
        elif rid == "BREAK_RULE":
            divider = geom.get("coordinates")
    missing = [p for p in PANEL_IDS if p not in panels]
    if missing:
        raise ValueError(f"{path}: missing panel region(s) {missing}")
    return panels, divider


# ----------------------------------------------------------------------------
# Control-file parsing (robust to string/int mix and reversed sides)
# ----------------------------------------------------------------------------

_PANEL_RE = re.compile(r"^0*5\s*([AB])$", re.IGNORECASE)
_OVERLAP_RE = re.compile(r"overlap", re.IGNORECASE)
_SIGMA_FOR_FACE_RE = re.compile(r"sigma\s+(\d+(?:\.\d+)?)\s+for that face",
                                re.IGNORECASE)
_FACE_TAG_RE = re.compile(r"face\s*([12])", re.IGNORECASE)


def _norm_panel(v):
    m = _PANEL_RE.match(str(v).strip())
    return ("5" + m.group(1).upper()) if m else None


def _norm_block(v):
    s = str(v).strip()
    return int(s) if re.fullmatch(r"[0-9]+", s) else None


def _seg(v, where):
    arr = np.asarray(v, dtype=float)
    if arr.shape != (2, 2) or not np.all(np.isfinite(arr)):
        raise ValueError(f"{where}: bad face segment {v!r}")
    return arr


def _face_sigmas(side_rec, where, log):
    """Per-face along sigma: structured sigma_along_px, with face-specific
    overrides parsed from sigma_basis prose ('sigma N for that face')."""
    base = side_rec.get("sigma_along_px", None)
    if base is None:
        log.append(f"[parse] {where}: no sigma_along_px; fallback "
                   f"{SIGMA_ALONG_FALLBACK_PX} px")
        base = SIGMA_ALONG_FALLBACK_PX
    base = float(base)
    out = {1: base, 2: base}
    basis = str(side_rec.get("sigma_basis", "") or "")
    for chunk in basis.split(";"):
        fm = _FACE_TAG_RE.search(chunk)
        sm = _SIGMA_FOR_FACE_RE.search(chunk)
        if fm and sm:
            face = int(fm.group(1))
            out[face] = float(sm.group(1))
            log.append(f"[parse] {where}: face{face} sigma override "
                       f"{out[face]:g} px (from sigma_basis prose)")
    return out


def parse_pair_file(path, log):
    """Parse one pair_*.json.  Returns an attachment dict for sheet-5 pairs,
    or None for block-block pairs.  The panel/block side of each control is
    identified from the record's own `sheet` fields (never assumed from the
    A/B labels); reversed records are handled and logged."""
    with open(path) as fh:
        rec = json.load(fh)
    pair = rec.get("pair")
    if not isinstance(pair, (list, tuple)) or len(pair) != 2:
        return None
    panel = block = None
    for el in pair:
        p = _norm_panel(el)
        if p is not None and panel is None:
            panel = p
            continue
        b = _norm_block(el)
        if b is not None and block is None:
            block = b
    if panel is None:
        return None  # ordinary block-block pair; not ours
    if block is None:
        raise ValueError(f"{path}: pair {pair!r} lacks a block sheet id")

    name = os.path.basename(path)
    context_only = "CONTEXT_ONLY" in str(rec.get("attachment_class", "")).upper()
    prose = [str(rec.get(k, "")) for k in ("notes", "axis", "boundary")]
    prose += [str(c.get("notes", "")) for c in rec.get("controls", [])]
    overlap = bool(_OVERLAP_RE.search(" ".join(prose)))

    anchors = []
    reversed_sides = False
    for c in rec.get("controls", []):
        aname = str(c.get("anchor", "?"))
        where = f"{name}:{aname}"
        side_panel = side_block = None
        for key in ("A", "B"):
            side = c.get(key)
            if not isinstance(side, dict):
                continue
            sp = _norm_panel(side.get("sheet"))
            sb = _norm_block(side.get("sheet"))
            if sp is not None:
                if sp != panel:
                    raise ValueError(f"{where}: side {key} sheet {sp} != pair "
                                     f"panel {panel}")
                side_panel = (key, side)
            elif sb is not None:
                if sb != block:
                    raise ValueError(f"{where}: side {key} sheet {sb} != pair "
                                     f"block {block}")
                side_block = (key, side)
        if side_panel is None or side_block is None:
            raise ValueError(f"{where}: cannot identify panel/block sides "
                             f"from the records' sheet fields")
        if side_panel[0] != "A":
            reversed_sides = True
        pkey, pside = side_panel
        bkey, bside = side_block
        dw = c.get("drafted_width_px") or {}
        anchors.append({
            "name": aname,
            "status": str(c.get("status", "")).upper(),
            "panel_segs": {1: _seg(pside["face1_seg"], where),
                           2: _seg(pside["face2_seg"], where)},
            "block_segs": {1: _seg(bside["face1_seg"], where),
                           2: _seg(bside["face2_seg"], where)},
            "panel_sigma": _face_sigmas(pside, where + f" panel({pkey})", log),
            "block_sigma": _face_sigmas(bside, where + f" block({bkey})", log),
            "width_panel_px": dw.get(pkey),
            "width_block_px": dw.get(bkey),
            "width_annotation": str(dw.get("annotation", "")),
            "notes": str(c.get("notes", "")),
        })
    att = {
        "path": os.path.abspath(path),
        "file": name,
        "panel": panel,
        "block": block,
        "seam": f"{panel}-{block}",
        "context_only": context_only,
        "reversed_sides": reversed_sides,
        "overlap": overlap,
        "boundary": str(rec.get("boundary", "")),
        "anchors": anchors,
    }
    if reversed_sides:
        log.append(f"[parse] {name}: record sides reversed (panel not on "
                   f"'A'); handled via sheet-field identification")
    log.append(f"[parse] {name}: seam {att['seam']}, {len(anchors)} anchors, "
               f"context_only={context_only}, overlap={overlap}")
    return att


def discover_attachments(controls_dir, log):
    atts = []
    for path in sorted(glob.glob(os.path.join(controls_dir, "pair_*.json"))):
        att = parse_pair_file(path, log)
        if att is not None:
            atts.append(att)
    return atts


# ----------------------------------------------------------------------------
# Geometry verification (axis mapping is checked, not assumed)
# ----------------------------------------------------------------------------

def verify_axes(att, log):
    """Assert from the control geometry that along-frontage is page-y on both
    sides: the anchor spread must be dominated by y.  Also log whether the
    two sides run the same page-y direction."""
    if len(att["anchors"]) < 2:
        log.append(f"[axes] {att['seam']}: single anchor; axis check skipped")
        return
    for side in ("panel", "block"):
        mids = np.array([a[f"{side}_segs"][f].mean(axis=0)
                         for a in att["anchors"] for f in (1, 2)])
        spread = mids.max(axis=0) - mids.min(axis=0)
        if not spread[1] > spread[0]:
            raise ValueError(
                f"{att['seam']}: along-frontage axis on the {side} side is "
                f"not page-y (spread x={spread[0]:.0f} px vs y={spread[1]:.0f}"
                f" px); the along/across observation model would be invalid")
        log.append(f"[axes] {att['seam']} {side}: along=page-y verified "
                   f"(anchor spread y {spread[1]:.0f} px vs x {spread[0]:.0f}"
                   f" px)")
    ys_p = [a["panel_segs"][1][:, 1].mean() for a in att["anchors"]]
    ys_b = [a["block_segs"][1][:, 1].mean() for a in att["anchors"]]
    order = np.argsort(ys_p)
    same = bool(np.all(np.diff(np.asarray(ys_b)[order]) > 0))
    log.append(f"[axes] {att['seam']}: page-y runs the "
               f"{'same' if same else 'OPPOSITE'} direction on both sides"
               + ("" if same else " (expect ~180 deg panel rotation)"))


def verify_points_in_panel(att, panels, log):
    poly = panels[att["panel"]]["polygon"]
    bad = []
    for a in att["anchors"]:
        for f in (1, 2):
            for pt in a["panel_segs"][f]:
                if not point_in_polygon(pt, poly):
                    bad.append((a["name"], f, [float(pt[0]), float(pt[1])]))
    if bad:
        log.append(f"[regions] WARNING {att['seam']}: {len(bad)} panel-side "
                   f"points outside the {att['panel']} polygon: {bad}")
    else:
        log.append(f"[regions] {att['seam']}: all panel-side points inside "
                   f"the {att['panel']} polygon")


# ----------------------------------------------------------------------------
# Observation building
# ----------------------------------------------------------------------------

def _corner(seg):
    """The Ave A east-face corner endpoint = smaller-x endpoint (both sides
    drafted bay-page-left; the landward face segments start at the Ave A
    corner and extend landward, i.e. +x)."""
    return seg[int(np.argmin(seg[:, 0]))]


def _mk_row(att, anc, face, typ, u, q, target, sp, sb, s_block, floor):
    return {
        "seam": att["seam"], "anchor": anc["name"], "face": face,
        "type": typ,
        "u": np.asarray(u, float),
        "q": np.asarray(q, float),
        "coeff": row_coeffs(u, q),
        "target": float(target),
        "sigma_panel_native": float(sp),
        "sigma_block_native": float(sb),
        "s_block": float(s_block),
        "floor": bool(floor),
    }


def build_rows(att, block_T, center, log, statuses=("ACCEPTED",)):
    """Observation rows for one attachment.  Non-overlap seams: 2 along rows
    (face midpoints) + 1 across row (best-sigma face corner, zero offset) per
    anchor.  Overlap seams (5A-7): direct pp rows (both components) at both
    faces' corner endpoints."""
    bt = block_T[att["block"]]
    Rb = rot(bt["a"], bt["b"])
    tb = np.array([bt["tx"], bt["ty"]])
    u_along = Rb @ np.array([0.0, 1.0])
    u_along = u_along / np.linalg.norm(u_along)
    u_across = np.array([u_along[1], -u_along[0]])
    rows = []
    for anc in att["anchors"]:
        if statuses is not None and anc["status"] not in statuses:
            log.append(f"[obs] {att['seam']} {anc['name']}: status "
                       f"{anc['status']}; excluded from the fit")
            continue
        for face in (1, 2):
            sp = anc["panel_sigma"][face]
            sb = anc["block_sigma"][face]
            seg_p, seg_b = anc["panel_segs"][face], anc["block_segs"][face]
            if att["overlap"]:
                cp, cb = _corner(seg_p), _corner(seg_b)
                tgt = Rb @ cb + tb
                rows.append(_mk_row(att, anc, face, "pp_along", u_along,
                                    cp - center, u_along @ tgt, sp, sb,
                                    bt["s"], floor=False))
                rows.append(_mk_row(att, anc, face, "pp_across", u_across,
                                    cp - center, u_across @ tgt, sp, sb,
                                    bt["s"], floor=True))
            else:
                mp, mb = seg_p.mean(axis=0), seg_b.mean(axis=0)
                rows.append(_mk_row(att, anc, face, "along", u_along,
                                    mp - center, u_along @ (Rb @ mb + tb),
                                    sp, sb, bt["s"], floor=False))
        if not att["overlap"]:
            best = min((1, 2), key=lambda f: anc["panel_sigma"][f] ** 2
                       + anc["block_sigma"][f] ** 2)
            seg_p, seg_b = anc["panel_segs"][best], anc["block_segs"][best]
            cp, cb = _corner(seg_p), _corner(seg_b)
            rows.append(_mk_row(att, anc, best, "across", u_across,
                                cp - center, u_across @ (Rb @ cb + tb),
                                anc["panel_sigma"][best],
                                anc["block_sigma"][best], bt["s"],
                                floor=True))
    kind = "pp (duplicated ground)" if att["overlap"] else "along+across"
    log.append(f"[obs] {att['seam']}: {len(rows)} rows ({kind})")
    return rows


def _row_sigmas(rows, s_panel):
    out = np.empty(len(rows))
    for i, r in enumerate(rows):
        s = math.hypot(s_panel * r["sigma_panel_native"],
                       r["s_block"] * r["sigma_block_native"])
        if r["floor"]:
            s = max(s, SIGMA_ACROSS_FLOOR_PX)
        out[i] = s
    return out


# ----------------------------------------------------------------------------
# Per-panel robust least squares
# ----------------------------------------------------------------------------

def solve_panel(panel_id, rows, center, log):
    m = len(rows)
    if m < 6:
        log.append(f"[solve] {panel_id}: only {m} rows for 4 parameters -- "
                   f"weakly determined")
    J = np.array([r["coeff"] for r in rows])
    tgt = np.array([r["target"] for r in rows])
    s_panel = PANEL_SCALE_INIT
    wh = np.ones(m)
    x = None
    for _ in range(IRLS_ITERATIONS):
        sig = _row_sigmas(rows, s_panel)
        inv = 1.0 / sig
        sw = inv * np.sqrt(wh)
        x, *_ = np.linalg.lstsq(J * sw[:, None], tgt * sw, rcond=None)
        rn = (J @ x - tgt) * inv
        wh = np.where(np.abs(rn) > HUBER_DELTA,
                      HUBER_DELTA / np.maximum(np.abs(rn), 1e-12), 1.0)
        s_panel = float(math.hypot(x[0], x[1]))

    sig = _row_sigmas(rows, s_panel)
    inv = 1.0 / sig
    res = J @ x - tgt
    rn = res * inv
    wh = np.where(np.abs(rn) > HUBER_DELTA,
                  HUBER_DELTA / np.maximum(np.abs(rn), 1e-12), 1.0)

    Jw = J * (inv * np.sqrt(wh))[:, None]
    N = Jw.T @ Jw
    rank = int(np.linalg.matrix_rank(N))
    if rank < 4:
        log.append(f"[solve] {panel_id}: normal matrix rank {rank} < 4; "
                   f"pseudo-inverse used -- parameters NOT trustworthy")
        Ninv = np.linalg.pinv(N)
    else:
        Ninv = np.linalg.inv(N)
    dof = m - rank
    s0_sq = float(np.sum(wh * rn ** 2) / dof) if dof > 0 else 1.0
    cov = Ninv * s0_sq

    a, b, tx, ty = (float(v) for v in x)
    s = math.hypot(a, b)
    theta = math.atan2(b, a)
    # Propagated stds for s and theta
    g_s = np.array([a / s, b / s, 0.0, 0.0])
    g_t = np.array([-b / s ** 2, a / s ** 2, 0.0, 0.0])
    s_std = float(math.sqrt(max(g_s @ cov @ g_s, 0.0)))
    theta_std = float(math.sqrt(max(g_t @ cov @ g_t, 0.0)))
    R = rot(a, b)
    traw = np.array([tx, ty]) - R @ center

    for i, r in enumerate(rows):
        r["sigma_mosaic"] = float(sig[i])
        r["residual_px"] = float(res[i])
        r["normalized"] = float(rn[i])
        r["huber_weight"] = float(wh[i])

    n_down = int(np.sum(wh < 1.0))
    log.append(f"[solve] {panel_id}: {m} rows, dof {dof}, s0^2 {s0_sq:.3f}, "
               f"{n_down} Huber-downweighted; s={s:.6f}, "
               f"theta={math.degrees(theta):.4f} deg")
    return {
        "params": np.array([a, b, tx, ty]),
        "a": a, "b": b, "tx": tx, "ty": ty,
        "s": s, "s_std": s_std,
        "theta_deg": math.degrees(theta),
        "theta_std_mrad": theta_std * 1000.0,
        "center": [float(center[0]), float(center[1])],
        "raw": {"a": a, "b": b, "tx": float(traw[0]), "ty": float(traw[1])},
        "covariance": cov.tolist(),
        "param_order": ["a", "b", "tx", "ty"],
        "param_std": {k: float(math.sqrt(max(cov[i, i], 0.0)))
                      for i, k in enumerate(["a", "b", "tx", "ty"])},
        "n_obs": m, "dof": dof, "rank": rank, "s0_sq": s0_sq,
        "rows": rows,
    }


def apply_panel(sol, p):
    """Map a raw sheet-5 pixel through a solved panel transform."""
    return apply_raw(sol["raw"], p)


# ----------------------------------------------------------------------------
# CONTEXT_ONLY report (5B-13): fit nothing, report consistency
# ----------------------------------------------------------------------------

def context_report(att, block_T, solutions, panels, log):
    rep = {"seam": att["seam"], "file": att["file"], "mode": None,
           "note": "", "anchors": [], "separations": []}
    sol = solutions.get(att["panel"])
    if sol is None:
        rep["mode"] = "unavailable"
        rep["note"] = f"panel {att['panel']} was not solved"
        return rep

    if att["block"] in block_T:
        # Full residual table under the solved panel transform (no fitting).
        rep["mode"] = "full_residuals"
        rep["note"] = (f"sheet {att['block']} present in the frozen block "
                       f"transforms; residuals evaluated under the solved "
                       f"{att['panel']} transform, nothing fitted")
        rows = build_rows(att, block_T, np.asarray(sol["center"]), log,
                          statuses=None)
        sig = _row_sigmas(rows, sol["s"])
        for i, r in enumerate(rows):
            res = float(r["coeff"] @ sol["params"] - r["target"])
            rep["anchors"].append({
                "anchor": r["anchor"], "face": r["face"], "type": r["type"],
                "residual_px": res, "sigma_mosaic": float(sig[i]),
                "normalized": res / float(sig[i]),
            })
        return rep

    # Sheet not in the frozen block (the real 5B-13 case): the only
    # transform-free consistencies are RELATIVE ones.
    rep["mode"] = "relative"
    rep["note"] = (
        f"sheet {att['block']} has no frozen transform (outside the block "
        f"solve), so two-sided point residuals are not computable; report "
        f"compares relative anchor separations (translation-free) and "
        f"drafted width ratios instead.  Block-side native px are converted "
        f"at the drafted 50 ft/in ({BLOCK_NATIVE_PX_PER_FT} px/ft); the "
        f"direction comparison assumes sheet {att['block']} is drafted "
        f"axis-aligned like its frozen neighbours (all block rotations "
        f"< 0.5 deg).")
    anchors = sorted(att["anchors"],
                     key=lambda a: float(_corner(a["panel_segs"][1])[1]))
    s_panel = sol["s"]
    for a in anchors:
        wp, wb = a["width_panel_px"], a["width_block_px"]
        ratio = (float(wb) / float(wp)) if wp and wb else None
        cp = _corner(a["panel_segs"][1])
        mos = apply_panel(sol, cp)
        rep["anchors"].append({
            "anchor": a["name"], "status": a["status"],
            "panel_corner_mosaic": [float(mos[0]), float(mos[1])],
            "width_ratio_block_over_panel": ratio,
        })
    for a1, a2 in zip(anchors, anchors[1:]):
        cp1, cp2 = (_corner(a1["panel_segs"][1]), _corner(a2["panel_segs"][1]))
        cb1, cb2 = (_corner(a1["block_segs"][1]), _corner(a2["block_segs"][1]))
        d_panel = apply_panel(sol, cp2) - apply_panel(sol, cp1)
        d_block = np.asarray(cb2, float) - np.asarray(cb1, float)
        sep_p_ft = float(np.linalg.norm(d_panel)) / (s_panel *
                                                     PANEL_NATIVE_PX_PER_FT)
        sep_b_ft = float(np.linalg.norm(d_block)) / BLOCK_NATIVE_PX_PER_FT
        ang_p = math.degrees(math.atan2(d_panel[1], d_panel[0]))
        ang_b = math.degrees(math.atan2(d_block[1], d_block[0]))
        rep["separations"].append({
            "from": a1["name"], "to": a2["name"],
            "panel_separation_ft": sep_p_ft,
            "block_separation_ft": sep_b_ft,
            "difference_ft": sep_p_ft - sep_b_ft,
            "direction_diff_deg": ang_p - ang_b,
        })
    log.append(f"[context] {att['seam']}: relative consistency report "
               f"({len(rep['separations'])} separation pair(s)); nothing "
               f"fitted")
    return rep


# ----------------------------------------------------------------------------
# Cross-panel consistency (nothing enters the fit)
# ----------------------------------------------------------------------------

def cross_panel_report(path, solutions, log):
    if not os.path.exists(path):
        log.append(f"[cross] {path} not found; cross-panel check skipped")
        return None
    with open(path) as fh:
        data = json.load(fh)
    solA, solB = solutions.get("5A"), solutions.get("5B")
    if solA is None or solB is None:
        log.append("[cross] both panels not solved; cross-panel check skipped")
        return None
    px_per_ft = 0.5 * (solA["s"] + solB["s"]) * PANEL_NATIVE_PX_PER_FT
    pairs = []
    for p in data.get("point_pairs", []):
        pid = str(p.get("id", "?"))
        gA = apply_panel(solA, np.asarray(p["panel_A"], float))
        gB = apply_panel(solB, np.asarray(p["panel_B"], float))
        d = gB - gA
        norm = float(np.linalg.norm(d))
        group = "pier" if "pier" in pid.lower() else "street"
        pairs.append({
            "id": pid, "group": group,
            "mosaic_A": [float(gA[0]), float(gA[1])],
            "mosaic_B": [float(gB[0]), float(gB[1])],
            "delta_px": [float(d[0]), float(d[1])],
            "norm_px": norm,
            "approx_ft": norm / px_per_ft,
            "flagged": bool(norm > CROSS_PANEL_FLAG_PX),
        })
    groups = {}
    for g in ("street", "pier"):
        sel = [p["norm_px"] for p in pairs if p["group"] == g]
        if sel:
            groups[g] = {"n": len(sel), "mean_px": float(np.mean(sel)),
                         "max_px": float(np.max(sel))}
    rep = {
        "source": os.path.abspath(path),
        "flag_threshold_px": CROSS_PANEL_FLAG_PX,
        "px_per_ft_used": px_per_ft,
        "pairs": pairs,
        "groups": groups,
        "flagged_ids": [p["id"] for p in pairs if p["flagged"]],
        "note": ("Street-corner pairs are the meaningful check; the "
                 "pier-ground pairs are a recorded drafted disagreement "
                 "(~55 ft) -- reported, never constrained.  Nothing here "
                 "entered the fit."),
    }
    log.append(f"[cross] {len(pairs)} pairs; flagged (> "
               f"{CROSS_PANEL_FLAG_PX:g} px): {rep['flagged_ids']}")
    return rep


# ----------------------------------------------------------------------------
# Diagnostics / outputs
# ----------------------------------------------------------------------------

def _fmt(v, nd=2):
    return "n/a" if v is None else f"{v:.{nd}f}"


def scale_comparison(att_list, solutions, block_T, block_meta):
    out = []
    for att in att_list:
        sol = solutions.get(att["panel"])
        bt = block_T.get(att["block"])
        if sol is None or bt is None:
            continue
        ratios = []
        for a in att["anchors"]:
            wp, wb = a["width_panel_px"], a["width_block_px"]
            if wp and wb:
                ratios.append(float(wb) / float(wp))
        out.append({
            "seam": att["seam"],
            "solved_scale_ratio": sol["s"] / bt["s"],
            "drafted_width_ratio_mean": float(np.mean(ratios)) if ratios
            else None,
            "drafted_width_ratios": ratios,
            "expectation": 2.0,
        })
    return out


def write_outputs(out_dir, payload, log):
    os.makedirs(out_dir, exist_ok=True)
    tpath = os.path.join(out_dir, "transforms_sheet5.json")

    def clean(o):
        if isinstance(o, dict):
            return {k: clean(v) for k, v in o.items()
                    if k not in ("u", "q", "coeff", "params")}
        if isinstance(o, (list, tuple)):
            return [clean(v) for v in o]
        if isinstance(o, np.ndarray):
            return o.tolist()
        if isinstance(o, (np.floating, np.integer)):
            return o.item()
        if isinstance(o, (np.bool_,)):
            return bool(o)
        return o

    with open(tpath, "w") as fh:
        json.dump(clean(payload), fh, indent=1)
    dpath = os.path.join(out_dir, "diagnostics.md")
    with open(dpath, "w") as fh:
        fh.write(render_diagnostics(payload, log))
    return tpath, dpath


def render_diagnostics(payload, log):
    L = []
    L.append("# Sheet-5 two-panel fit -- diagnostics\n")
    L.append("**This fit is downstream of the frozen block.**  It must be "
             "re-run after any block re-freeze (new "
             "`40_solve/output/transforms.json`); the sha256 below "
             "identifies the freeze actually used.\n")
    bm = payload["block_source"]
    L.append(f"- block transforms: `{bm['path']}`")
    L.append(f"- sha256: `{bm['sha256']}`")
    L.append(f"- block sheets available: {bm['sheets_available']}")
    L.append(f"- block kappa (reference only, prior-dominated="
             f"{bm['kappa_prior_dominated']}): "
             f"{_fmt(bm['kappa_px_per_ft'], 3)} px/ft\n")

    L.append("## Panel solutions (mosaic frame; centered on panel-polygon "
             "centroids)\n")
    L.append("| panel | s | s std | theta (deg) | theta std (mrad) | tx | ty "
             "| center | n_obs | dof | s0^2 |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|")
    for pid in PANEL_IDS:
        sol = payload["panels"].get(pid)
        if sol is None:
            L.append(f"| {pid} | (not solved) |||||||||")
            continue
        L.append(f"| {pid} | {sol['s']:.6f} | {sol['s_std']:.6f} | "
                 f"{sol['theta_deg']:.4f} | {sol['theta_std_mrad']:.2f} | "
                 f"{sol['tx']:.1f} | {sol['ty']:.1f} | "
                 f"({sol['center'][0]:.1f}, {sol['center'][1]:.1f}) | "
                 f"{sol['n_obs']} | {sol['dof']} | {sol['s0_sq']:.2f} |")
    L.append("")
    L.append("Rotation was left fully free per panel (wharf plates are "
             "rotated relative to north-up; the similarity finds whatever "
             "rotation the controls demand -- the near-zero solved values "
             "are an outcome, not an assumption).\n")

    L.append("## Scale vs the block (~2x expectation: 100 ft/in vs "
             "50 ft/in)\n")
    L.append("| seam | solved s_panel/s_block | mean drafted width ratio "
             "(B/A) | expectation |")
    L.append("|---|---|---|---|")
    for row in payload["scale_comparison"]:
        L.append(f"| {row['seam']} | {row['solved_scale_ratio']:.4f} | "
                 f"{_fmt(row['drafted_width_ratio_mean'], 3)} | "
                 f"{row['expectation']:.2f} |")
    for pid in PANEL_IDS:
        sol = payload["panels"].get(pid)
        if sol:
            L.append(f"\nPanel {pid} implied mosaic scale: s x "
                     f"{PANEL_NATIVE_PX_PER_FT} = "
                     f"{sol['s'] * PANEL_NATIVE_PX_PER_FT:.3f} px/ft "
                     f"(block kappa is prior-dominated; drafted-width ratios "
                     f"above are the meaningful comparison).")
    L.append("")

    L.append("## Residual RMS per attachment\n")
    L.append("| seam | type | n | RMS (mosaic px) | max |n| |")
    L.append("|---|---|---|---|---|")
    for pid in PANEL_IDS:
        sol = payload["panels"].get(pid)
        if not sol:
            continue
        keys = sorted({(r["seam"], r["type"]) for r in sol["rows"]})
        for seam, typ in keys:
            sel = [r for r in sol["rows"]
                   if r["seam"] == seam and r["type"] == typ]
            L.append(f"| {seam} | {typ} | {len(sel)} | "
                     f"{rms([r['residual_px'] for r in sel]):.2f} | "
                     f"{max(abs(r['normalized']) for r in sel):.2f} |")
    L.append("")

    L.append("## Huber downweights (logged, never dropped)\n")
    any_dw = False
    L.append("| seam | anchor | face | type | residual (px) | normalized | "
             "weight |")
    L.append("|---|---|---|---|---|---|---|")
    for pid in PANEL_IDS:
        sol = payload["panels"].get(pid)
        if not sol:
            continue
        for r in sol["rows"]:
            if r["huber_weight"] < 1.0:
                any_dw = True
                L.append(f"| {r['seam']} | {r['anchor']} | {r['face']} | "
                         f"{r['type']} | {r['residual_px']:.1f} | "
                         f"{r['normalized']:.2f} | {r['huber_weight']:.3f} |")
    if not any_dw:
        L.append("| (none) | | | | | | |")
    L.append("")

    cp = payload.get("cross_panel")
    L.append("## Cross-panel consistency (5A vs 5B; NOT in the fit)\n")
    if cp is None:
        L.append("cross_panel_05.json not evaluated.\n")
    else:
        L.append(f"Flag threshold {cp['flag_threshold_px']:g} mosaic px; "
                 f"ft at {cp['px_per_ft_used']:.2f} px/ft.\n")
        L.append("| pair | group | dx (px) | dy (px) | |d| (px) | ~ft | "
                 "flagged |")
        L.append("|---|---|---|---|---|---|---|")
        for p in cp["pairs"]:
            L.append(f"| {p['id']} | {p['group']} | {p['delta_px'][0]:.1f} | "
                     f"{p['delta_px'][1]:.1f} | {p['norm_px']:.1f} | "
                     f"{p['approx_ft']:.1f} | "
                     f"{'YES' if p['flagged'] else 'no'} |")
        for g, s in cp["groups"].items():
            L.append(f"\n- {g} pairs: n={s['n']}, mean {s['mean_px']:.1f} px, "
                     f"max {s['max_px']:.1f} px")
        L.append(f"\n{cp['note']}\n")

    L.append("## 5B-13 CONTEXT_ONLY consistency report (fitted to "
             "nothing)\n")
    ctx = payload.get("context_reports", [])
    if not ctx:
        L.append("No CONTEXT_ONLY attachments found.\n")
    for rep in ctx:
        L.append(f"### {rep['seam']} ({rep['file']}) -- mode: "
                 f"{rep['mode']}\n")
        L.append(rep["note"] + "\n")
        if rep["mode"] == "full_residuals":
            L.append("| anchor | face | type | residual (px) | sigma | "
                     "normalized |")
            L.append("|---|---|---|---|---|---|")
            for a in rep["anchors"]:
                L.append(f"| {a['anchor']} | {a['face']} | {a['type']} | "
                         f"{a['residual_px']:.1f} | "
                         f"{a['sigma_mosaic']:.1f} | "
                         f"{a['normalized']:.2f} |")
        elif rep["mode"] == "relative":
            L.append("| anchor | width ratio (block/panel) |")
            L.append("|---|---|")
            for a in rep["anchors"]:
                L.append(f"| {a['anchor']} | "
                         f"{_fmt(a['width_ratio_block_over_panel'], 3)} |")
            L.append("")
            L.append("| span | panel sep (ft) | sheet-13 sep (ft) | diff "
                     "(ft) | direction diff (deg) |")
            L.append("|---|---|---|---|---|")
            for s in rep["separations"]:
                L.append(f"| {s['from']} -> {s['to']} | "
                         f"{s['panel_separation_ft']:.1f} | "
                         f"{s['block_separation_ft']:.1f} | "
                         f"{s['difference_ft']:+.1f} | "
                         f"{s['direction_diff_deg']:+.2f} |")
        L.append("")

    L.append("## Model decisions (documented)\n")
    L.append("- Observation basis: face midpoints as corresponding-line "
             "(along) observations; the shared Ave A east-face corner "
             "endpoints (smaller-x endpoint, both plates bay-page-left) as "
             "zero-offset across observations; direct 2-component "
             "point-to-point rows at those corners where the record marks "
             "genuine duplicated ground (5A-7 bay strip, per its notes).")
    L.append("- No kappa: both plates draft the same Ave A corner, so no "
             "street-width x kappa construction is needed anywhere in this "
             "fit; recorded drafted widths are used only for the scale "
             "diagnostics and sigma floors.")
    L.append(f"- Across sigma floor {SIGMA_ACROSS_FLOOR_PX:g} mosaic px "
             f"(block amendment-5 floor); native sigmas scaled into the "
             f"mosaic with the frozen block scales and the current panel "
             f"scale inside IRLS.")
    L.append("- Face-specific sigma overrides parsed from sigma_basis "
             "prose ('sigma N for that face'): see log lines below.")
    L.append("- Panel centers = area centroids of the region polygons "
             "(candidate-regions GeoJSON).")
    L.append("- Along-frontage = page-y on both sides was VERIFIED from "
             "the anchor geometry (see [axes] log lines), and panel "
             "rotation was solved, not assumed near zero.\n")

    L.append("## Log\n")
    L.append("```")
    L.extend(log)
    L.append("```")
    return "\n".join(L) + "\n"


# ----------------------------------------------------------------------------
# Driver
# ----------------------------------------------------------------------------

def run_fit(controls_dir=DEFAULT_CONTROLS, transforms_path=DEFAULT_TRANSFORMS,
            regions_path=DEFAULT_REGIONS, out_dir=DEFAULT_OUT):
    log = []
    block_T, block_meta = load_block_transforms(transforms_path)
    log.append(f"[load] frozen block: {len(block_T)} sheets from "
               f"{transforms_path} (sha256 {block_meta['sha256'][:12]}...)")
    panels, divider = load_regions(regions_path)
    for pid in PANEL_IDS:
        c = panels[pid]["center"]
        log.append(f"[load] panel {pid} centroid ({c[0]:.1f}, {c[1]:.1f})")

    atts = discover_attachments(controls_dir, log)
    if not atts:
        raise SystemExit(f"no sheet-5 pair files found in {controls_dir}")

    fit_atts, ctx_atts = [], []
    for att in atts:
        verify_points_in_panel(att, panels, log)
        verify_axes(att, log)
        if att["context_only"] or all(a["status"] != "ACCEPTED"
                                      for a in att["anchors"]):
            ctx_atts.append(att)
            log.append(f"[class] {att['seam']}: CONTEXT_ONLY -- loaded, "
                       f"fitted to nothing, reported below")
        elif att["block"] not in block_T:
            ctx_atts.append(att)
            log.append(f"[class] {att['seam']}: block sheet {att['block']} "
                       f"missing from the frozen transforms -- excluded "
                       f"from the fit, context-reported")
        else:
            fit_atts.append(att)

    solutions = {}
    for pid in PANEL_IDS:
        rows = []
        for att in fit_atts:
            if att["panel"] == pid:
                rows.extend(build_rows(att, block_T, panels[pid]["center"],
                                       log))
        if not rows:
            log.append(f"[solve] panel {pid}: no observations; not solved")
            continue
        solutions[pid] = solve_panel(pid, rows, panels[pid]["center"], log)

    ctx_reports = [context_report(att, block_T, solutions, panels, log)
                   for att in ctx_atts]
    cross = cross_panel_report(os.path.join(controls_dir,
                                            "cross_panel_05.json"),
                               solutions, log)

    payload = {
        "convention": {
            "centered": "p_mosaic = [[a,-b],[b,a]] @ (p_sheet5_raw - "
                        "center_panel) + (tx, ty)",
            "raw": "p_mosaic = [[a,-b],[b,a]] @ p_sheet5_raw + (raw.tx, "
                   "raw.ty) -- use THIS for raw scan pixels",
            "centers": {pid: [float(panels[pid]["center"][0]),
                              float(panels[pid]["center"][1])]
                        for pid in PANEL_IDS},
            "center_definition": "area centroid of the panel polygon "
                                 "(regions A/B of the candidate-regions "
                                 "GeoJSON)",
            "axes": "raster pixels of the sheet 5 scan (6653x7795), origin "
                    "top-left, x right, y down",
            "frame": "mosaic frame of the frozen block transforms.json "
                     "(sheet 10 centered pixel frame)",
            "panel_divider": "x = 3789 + 0.0099*y (drafted BREAK_RULE "
                             "centerline)",
        },
        "block_source": block_meta,
        "panels": solutions,
        "attachments": {att["seam"]: {
            "file": att["file"], "panel": att["panel"],
            "block": att["block"], "overlap": att["overlap"],
            "context_only": att["context_only"],
            "reversed_sides": att["reversed_sides"],
            "n_anchors": len(att["anchors"]),
        } for att in atts},
        "scale_comparison": scale_comparison(fit_atts, solutions, block_T,
                                             block_meta),
        "context_reports": ctx_reports,
        "cross_panel": cross,
        "rerun_note": "Downstream of the block freeze: rerun fit_sheet5.py "
                      "whenever 40_solve/output/transforms.json changes "
                      "(sha256 above identifies the freeze used).",
    }
    tpath, dpath = write_outputs(out_dir, payload, log)
    payload["output_files"] = [tpath, dpath]
    payload["log"] = log
    return payload


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--controls", default=DEFAULT_CONTROLS)
    ap.add_argument("--transforms", default=DEFAULT_TRANSFORMS)
    ap.add_argument("--regions", default=DEFAULT_REGIONS)
    ap.add_argument("--out", default=DEFAULT_OUT)
    args = ap.parse_args(argv)
    payload = run_fit(args.controls, args.transforms, args.regions, args.out)
    for pid in PANEL_IDS:
        sol = payload["panels"].get(pid)
        if sol:
            print(f"{pid}: s={sol['s']:.6f} (+-{sol['s_std']:.6f}) "
                  f"theta={sol['theta_deg']:.4f} deg "
                  f"(+-{sol['theta_std_mrad']:.2f} mrad) "
                  f"raw t=({sol['raw']['tx']:.1f}, {sol['raw']['ty']:.1f}) "
                  f"n={sol['n_obs']} s0^2={sol['s0_sq']:.2f}")
        else:
            print(f"{pid}: not solved")
    cp = payload.get("cross_panel")
    if cp:
        print(f"cross-panel flagged: {cp['flagged_ids']}")
    print("outputs:", ", ".join(payload["output_files"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
