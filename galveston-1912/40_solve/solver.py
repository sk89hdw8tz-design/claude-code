#!/usr/bin/env python3
"""Diagnostic network solver for the Galveston 1912 Sanborn 12-sheet block.

Model
-----
Per-sheet 2D similarity, linear parameterization:

    p_mosaic = [[a, -b], [b, a]] (p_sheet - c) + (tx, ty),   c = (3326, 3898)

with a = s*cos(theta), b = s*sin(theta).  Sheet coordinates are RECENTERED by
subtracting the plate center c before the normal equations are built (documented
in transforms.json; the raw-pixel composed transform is also stored there).

Datum (gauge): sheet 10 fixed to the identity, so the mosaic frame is sheet 10's
centered pixel frame.  One global nuisance parameter kappa (mosaic px per foot)
carries a Gaussian prior kappa ~ 6.07 +- 0.15; it is used only by across-seam
constraints.  The solved kappa should be compared with per-plate drafted widths.

Observations (from ACCEPTED anchors in 30_controls/verified/pair_*.json):

1. ALONG-seam coincidence (2 per anchor, one per face): residual
       r = (T_A(mid_A) - T_B(mid_B)) . u_along
   with u_along = (0,1) for vertical seams, (1,0) for horizontal ones.  This is
   a LINEARIZATION valid for near-axis-aligned solutions (rotations here are
   sub-degree, so the along-seam unit vector is taken as an axis unit vector in
   the mosaic frame rather than a per-seam solved direction).
   Weight = 1 / (sigma_A^2 + sigma_B^2) from each side's sigma_along_px.

2. ACROSS-seam constructed separation (1 per anchor, face1 only, to avoid
   double counting): near-seam endpoints of face1 on each plate approximate the
   block corners of each plate's own frontage of the seam street.  Residual
       r = (T_B(pB) - T_A(pA)) . u_across - W_ft * kappa
   with u_across = (1,0) for vertical seams (A left of B), (0,1) for horizontal
   (A above B).  sigma_across = max(12 px, |drafted_width_px.A - .B| / 2).

3. STRAIGHT-STREET COLLINEARITY (--collinearity, off by default): the through
   streets crossing the seams are platted straight, so the face lines measured
   for the same street on multiple sheets are segments of one drafted straight
   line.  Streets are grouped exactly as in the collinearity DIAGNOSTIC (by
   anchor name + seam axis); each street contributes TWO lines, one per face
   -- faces are never mixed into one line.  Face membership is canonicalized
   by the pass-1 mosaic perpendicular coordinate (low/high), immune to
   face1/face2 labeling differences across control files.  Each used line adds
   two unknowns (c, m) for
       perp = c + m * (along - mean_along_of_line)
   i.e. y = c + m*x for streets crossing vertical seams (near-horizontal face
   lines in the mosaic) and x = c + m*y for streets crossing horizontal seams.
   m stays a FREE per-line parameter: no street direction is assumed, only
   straightness.  One row per face midpoint p measured on sheet i:
       r = u_perp . T_i(p) - c - m * (along0 - mean_along)
   where along0 is the point's approximate mosaic along-coordinate taken from
   a FIRST-PASS solve without collinearity (two-stage solve: pass 1 = current
   model, pass 2 adds the collinearity rows built from pass-1 coordinates;
   the bilinear m * T_i(p) term is linearized at m = 0, along = along0).
   sigma_perp = 6 px by default (drafting scatter; --collinearity-sigma).
   Collinearity rows are data-class constraints and ARE Huber-subject.
   Guard: a line whose points all come from a single sheet -- or with < 3
   points, which its own 2 unknowns fit exactly -- contributes nothing and is
   skipped with a log line.  Used lines are counted and reported.

Robust fitting: weighted linear least squares + IRLS with Huber (delta = 2.5,
in units of sigma), 10 iterations.  Every down-weighted observation is logged.

Outputs (40_solve/output/): transforms.json, residuals.json, covariance.json,
diagnostics.md.  Diagnostics: per-sheet marginal std of theta/s (flag rotation
std > 1.5 mrad), leave-one-seam-out (--loso), through-street collinearity with
the Ave I kink check.

Usage:
    /home/user/g1912/venv/bin/python solver.py [--controls DIR] [--out DIR]
        [--loso] [--adjacency PATH] [--rot-prior-mrad MRAD]
        [--collinearity] [--collinearity-sigma PX]
"""

from __future__ import annotations

import argparse
import glob
import json
import math
import os
import re
import sys

import numpy as np

# ----------------------------------------------------------------------------
# Constants
# ----------------------------------------------------------------------------

SHEETS = [7, 8, 9, 10, 11, 12, 39, 40, 43, 44, 49, 50]
DATUM_SHEET = 10
CENTER = np.array([3326.0, 3898.0])           # plate recentring (all 6653x7795)
KAPPA_PRIOR = 6.07                            # mosaic px per foot
KAPPA_PRIOR_SIGMA = 0.15
SIGMA_ACROSS_FLOOR_PX = 12.0                  # binding floor (protocol amendment 5)
SIGMA_ALONG_FALLBACK_PX = 2.0                 # used only if a record omits sigma
HUBER_DELTA = 2.5                             # in units of normalized residual
IRLS_ITERATIONS = 10
ROT_FLAG_MRAD = 1.5
COLLIN_SIGMA_DEFAULT_PX = 6.0                 # face-line drafting scatter (perp)

# Default drafted seam-street widths (ft); may be overridden per seam by
# consistent drafted evidence in the control records (logged, never silent).
DEFAULT_WIDTH_FT = {
    "ave_c": 70.0,   # Ave C (Mechanic)
    "ave_f": 70.0,   # Ave F (Church)
    "ave_i": 80.0,   # Ave I (Sealy)
    "21st": 80.0,    # 21st / Center St
    "24th": 80.0,    # 24th St
}

BOUNDARY_LABEL = {
    "ave_c": "Ave C (Mechanic)",
    "ave_f": "Ave F (Church)",
    "ave_i": "Ave I (Sealy)",
    "21st": "21st (Center) St",
    "24th": "24th St",
}

# Grid position of each sheet (row 1 = top band 18th-21st; col 1 = bayside).
SHEET_COL = {7: 1, 9: 1, 11: 1, 8: 2, 10: 2, 12: 2,
             39: 3, 43: 3, 49: 3, 40: 4, 44: 4, 50: 4}
SHEET_ROW = {7: 1, 8: 1, 39: 1, 40: 1, 9: 2, 10: 2, 43: 2, 44: 2,
             11: 3, 12: 3, 49: 3, 50: 3}


# ----------------------------------------------------------------------------
# Small helpers
# ----------------------------------------------------------------------------

def canonical_boundary(text):
    """Map a boundary/seam description string to a canonical width key."""
    if not text:
        return None
    t = text.lower()
    if "mechanic" in t or re.search(r"ave\.?\s*c\b", t):
        return "ave_c"
    if "church" in t or re.search(r"ave\.?\s*f\b", t):
        return "ave_f"
    if "sealy" in t or re.search(r"ave\.?\s*i\b", t):
        return "ave_i"
    if "21st" in t or "center" in t:
        return "21st"
    if "24th" in t:
        return "24th"
    return None


def apply_T(params, q):
    """Apply centered similarity (a, b, tx, ty) to centered point q."""
    a, b, tx, ty = params
    return np.array([a * q[0] - b * q[1] + tx, b * q[0] + a * q[1] + ty])


def row_coeffs(u, q):
    """d(u . T(q))/d(a, b, tx, ty)."""
    return np.array([u[0] * q[0] + u[1] * q[1],
                     -u[0] * q[1] + u[1] * q[0],
                     u[0], u[1]])


def tls_line_deviations(points):
    """Total-least-squares line fit; returns signed perpendicular deviations."""
    P = np.asarray(points, dtype=float)
    c = P.mean(axis=0)
    _, _, vt = np.linalg.svd(P - c, full_matrices=False)
    normal = vt[-1]
    return (P - c) @ normal


# ----------------------------------------------------------------------------
# Adjacency
# ----------------------------------------------------------------------------

def load_adjacency(path):
    """Return {frozenset(pair): {'axis', 'first', 'second', 'feature'}} for the
    12-sheet internal pairs.  'first' is the left (vertical) / top (horizontal)
    sheet."""
    with open(path) as fh:
        adj = json.load(fh)
    info = {}
    for entry in adj.get("internal_pairs", []):
        a, b = entry["sheets"]
        if a not in SHEETS or b not in SHEETS:
            continue  # e.g. sheet 5 pairs (deferred)
        axis = "vertical" if "vertical" in entry.get("orientation", "") else "horizontal"
        first = second = None
        ea = adj["edges"].get(str(a), {})
        eb = adj["edges"].get(str(b), {})

        def neighbour(edges, side):
            v = edges.get(side)
            if isinstance(v, list) and v and isinstance(v[0], int):
                return v[0]
            return None

        if axis == "vertical":
            if neighbour(ea, "right") == b:
                first, second = a, b
            elif neighbour(eb, "right") == a:
                first, second = b, a
        else:
            if neighbour(ea, "bottom") == b:
                first, second = a, b
            elif neighbour(eb, "bottom") == a:
                first, second = b, a
        if first is None:
            first, second = a, b  # fall back to listed order
        info[frozenset((a, b))] = {
            "axis": axis, "first": first, "second": second,
            "feature": entry.get("shared_feature", ""),
        }
    return info


# ----------------------------------------------------------------------------
# Control-file parsing
# ----------------------------------------------------------------------------

def _seg(v):
    """Validate a segment [[x,y],[x,y]] -> 2x2 float array or None."""
    try:
        arr = np.asarray(v, dtype=float)
    except (TypeError, ValueError):
        return None
    if arr.shape != (2, 2) or not np.all(np.isfinite(arr)):
        return None
    return arr


_ANNOT_FT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(?:'|ft|feet)", re.IGNORECASE)


def decide_seam_width(boundary_key, entries, seam_key, log):
    """Choose W_ft for a seam.  Default comes from the width table; consistent
    drafted evidence in the controls (drafted_width_px backed by annotations)
    may override it.  Every choice and discrepancy is logged."""
    default = DEFAULT_WIDTH_FT[boundary_key]
    drafted = []
    annots = []
    for e in entries:
        dw = e.get("drafted_width_px") or {}
        for side in ("A", "B"):
            v = dw.get(side)
            if isinstance(v, (int, float)) and v > 0:
                drafted.append(float(v))
        ann = dw.get("annotation")
        if isinstance(ann, str):
            m = _ANNOT_FT_RE.search(ann)
            if m:
                annots.append(float(m.group(1)))

    chosen = default
    if drafted:
        implied_ft = float(np.mean(drafted)) / KAPPA_PRIOR
        scatter_ft = (max(drafted) - min(drafted)) / KAPPA_PRIOR if len(drafted) > 1 else 0.0
        consistent = scatter_ft <= 4.0
        if annots and len(set(annots)) == 1 and annots[0] != default:
            # Annotated width differs from the table: accept only if the drafted
            # px evidence supports the annotation better than the default
            # (annotations alone are never trusted -- Broadway precedent).
            if consistent and abs(implied_ft - annots[0]) < abs(implied_ft - default):
                chosen = annots[0]
                log.append(
                    f"[width] seam {seam_key}: overriding default {default:.0f} ft with "
                    f"annotated {chosen:.0f} ft (drafted evidence implies {implied_ft:.1f} ft, "
                    f"scatter {scatter_ft:.1f} ft)")
        elif consistent:
            cand = round(implied_ft / 10.0) * 10.0
            if cand != default and abs(implied_ft - cand) <= 3.0:
                chosen = cand
                log.append(
                    f"[width] seam {seam_key}: overriding default {default:.0f} ft with "
                    f"{cand:.0f} ft from consistent drafted evidence "
                    f"({implied_ft:.1f} ft implied at prior kappa, scatter {scatter_ft:.1f} ft)")
        if chosen == default and abs(implied_ft - default) > 5.0:
            log.append(
                f"[width] seam {seam_key}: drafted evidence implies {implied_ft:.1f} ft vs "
                f"table {default:.0f} ft (scatter {scatter_ft:.1f} ft) -- kept table value, "
                f"flagged for review")
    log.append(f"[width] seam {seam_key}: using W = {chosen:.0f} ft "
               f"({BOUNDARY_LABEL[boundary_key]})")
    return chosen


def load_controls(controls_dir, adjacency_info, log):
    """Parse all pair_*.json control files.

    Returns (observations, anchor_registry, seam_summaries).
    Tolerates missing files/seams and skips malformed anchors with a log line.
    """
    observations = []
    anchor_registry = []   # for collinearity: per (pair, sheet) face midpoints
    seam_summaries = {}

    paths = sorted(glob.glob(os.path.join(controls_dir, "pair_*.json")))
    if not paths:
        log.append(f"[load] no control files found in {controls_dir}")
        return observations, anchor_registry, seam_summaries

    for path in paths:
        name = os.path.basename(path)
        try:
            with open(path) as fh:
                data = json.load(fh)
        except (json.JSONDecodeError, OSError) as exc:
            log.append(f"[load] {name}: unreadable ({exc}); skipped")
            continue

        pair = data.get("pair")
        if not (isinstance(pair, list) and len(pair) == 2):
            log.append(f"[load] {name}: missing/invalid 'pair'; skipped")
            continue
        try:
            pair = tuple(int(p) for p in pair)
        except (TypeError, ValueError):
            # Sheet-5 panel attachments carry region ids like "5A"/"5B"; they are
            # fitted against the frozen block in a later stage, never in this solve.
            log.append(f"[load] {name}: non-block pair {pair} (sheet-5 attachment); "
                       f"set aside for the panel-fit stage")
            continue
        if any(p not in SHEETS for p in pair):
            log.append(f"[load] {name}: pair {pair} outside the 12-sheet block "
                       f"(e.g. sheet 5 deferred); skipped")
            continue
        key = frozenset(pair)
        if key not in adjacency_info:
            log.append(f"[load] {name}: pair {pair} not an internal pair in "
                       f"adjacency.json; skipped")
            continue
        adj = adjacency_info[key]
        axis = adj["axis"]
        file_axis = data.get("axis")
        if file_axis and file_axis != axis:
            log.append(f"[load] {name}: axis '{file_axis}' contradicts adjacency "
                       f"('{axis}'); trusting adjacency")
        first, second = adj["first"], adj["second"]   # left/top, right/bottom
        seam_key = f"{first}-{second}"

        boundary_key = canonical_boundary(data.get("boundary") or data.get("seam")) \
            or canonical_boundary(adj["feature"])
        if boundary_key is None:
            log.append(f"[load] {name}: cannot identify boundary street; skipped")
            continue

        entries = []
        n_rejected = 0
        n_context = 0
        for ctl in data.get("controls", []):
            status = str(ctl.get("status", "")).upper()
            anchor = ctl.get("anchor", "?")
            if status != "ACCEPTED":
                if status == "REJECTED":
                    n_rejected += 1
                else:
                    n_context += 1
                continue
            sides = {}
            ok = True
            for label in ("A", "B"):
                rec = ctl.get(label)
                if not isinstance(rec, dict):
                    log.append(f"[load] {name}/{anchor}: missing side '{label}'; anchor skipped")
                    ok = False
                    break
                sheet = rec.get("sheet")
                f1 = _seg(rec.get("face1_seg"))
                f2 = _seg(rec.get("face2_seg"))
                if sheet not in pair or f1 is None or f2 is None:
                    log.append(f"[load] {name}/{anchor}: side '{label}' malformed "
                               f"(sheet={sheet}, segs valid={f1 is not None},{f2 is not None}); "
                               f"anchor skipped")
                    ok = False
                    break
                sig = rec.get("sigma_along_px")
                if not isinstance(sig, (int, float)) or sig <= 0:
                    log.append(f"[load] {name}/{anchor}: side '{label}' has no valid "
                               f"sigma_along_px; using fallback "
                               f"{SIGMA_ALONG_FALLBACK_PX} px")
                    sig = SIGMA_ALONG_FALLBACK_PX
                sides[sheet] = {"f1": f1, "f2": f2, "sigma": float(sig)}
            if not ok:
                continue
            if set(sides) != set(pair):
                log.append(f"[load] {name}/{anchor}: sides do not cover both sheets "
                           f"of {pair}; anchor skipped")
                continue
            entries.append({"anchor": anchor, "sides": sides,
                            "drafted_width_px": ctl.get("drafted_width_px") or {}})

        w_ft = decide_seam_width(boundary_key, entries, seam_key, log) if entries \
            else DEFAULT_WIDTH_FT[boundary_key]

        u_along = np.array([0.0, 1.0]) if axis == "vertical" else np.array([1.0, 0.0])
        u_across = np.array([1.0, 0.0]) if axis == "vertical" else np.array([0.0, 1.0])
        near_axis = 0 if axis == "vertical" else 1   # coordinate used to pick corner

        for e in entries:
            anchor = e["anchor"]
            sf, ss = e["sides"][first], e["sides"][second]

            # -- along-seam coincidence, one obs per face --------------------
            sigma_along = math.sqrt(sf["sigma"] ** 2 + ss["sigma"] ** 2)
            for face, fk in ((1, "f1"), (2, "f2")):
                mid_f = sf[fk].mean(axis=0) - CENTER
                mid_s = ss[fk].mean(axis=0) - CENTER
                observations.append({
                    "kind": "along", "seam": seam_key, "pair": (first, second),
                    "anchor": anchor, "face": face,
                    "plus": first, "q_plus": mid_f,
                    "minus": second, "q_minus": mid_s,
                    "u": u_along, "wft": 0.0, "sigma": sigma_along,
                })

            # -- across-seam constructed separation (face1 corner only) -----
            dw = e["drafted_width_px"]
            dwa, dwb = dw.get("A"), dw.get("B")
            if isinstance(dwa, (int, float)) and isinstance(dwb, (int, float)) \
                    and dwa > 0 and dwb > 0:
                sigma_across = max(SIGMA_ACROSS_FLOOR_PX, abs(dwa - dwb) / 2.0)
            else:
                sigma_across = SIGMA_ACROSS_FLOOR_PX
                log.append(f"[load] {seam_key}/{anchor}: drafted_width_px missing or "
                           f"invalid; sigma_across floor {SIGMA_ACROSS_FLOOR_PX} px used")
            # near-seam endpoint: first (left/top) sheet -> larger x (or y);
            # second (right/bottom) sheet -> smaller x (or y)
            pf = sf["f1"][np.argmax(sf["f1"][:, near_axis])] - CENTER
            ps = ss["f1"][np.argmin(ss["f1"][:, near_axis])] - CENTER
            observations.append({
                "kind": "across", "seam": seam_key, "pair": (first, second),
                "anchor": anchor, "face": 1,
                "plus": second, "q_plus": ps,      # r = u.(T_B - T_A) - W*kappa
                "minus": first, "q_minus": pf,
                "u": u_across, "wft": w_ft, "sigma": sigma_across,
            })

            # -- collinearity registry --------------------------------------
            for sheet in (first, second):
                sd = e["sides"][sheet]
                anchor_registry.append({
                    "anchor": anchor, "axis": axis, "seam": seam_key, "sheet": sheet,
                    "mid1_q": sd["f1"].mean(axis=0) - CENTER,
                    "mid2_q": sd["f2"].mean(axis=0) - CENTER,
                })

        seam_summaries[seam_key] = {
            "axis": axis, "boundary": BOUNDARY_LABEL[boundary_key],
            "w_ft": w_ft, "anchors_accepted": len(entries),
            "rejected": n_rejected, "context_only": n_context, "file": name,
        }
        log.append(f"[load] {name}: seam {seam_key} ({axis}, "
                   f"{BOUNDARY_LABEL[boundary_key]}): {len(entries)} accepted, "
                   f"{n_rejected} rejected, {n_context} context-only")

    return observations, anchor_registry, seam_summaries


# ----------------------------------------------------------------------------
# Straight-street collinearity observations (pass 2)
# ----------------------------------------------------------------------------

def build_collinearity_obs(anchor_registry, ref_result, sigma_perp, log):
    """Promote through-street face lines to observations.

    Groups the anchor registry exactly like the collinearity diagnostic (by
    anchor name + seam axis).  For each street with points on >= 2 sheets the
    TWO face lines are built SEPARATELY (never mixed): face membership is
    canonicalized by the PASS-1 mosaic perpendicular coordinate (low/high per
    registry entry), so inconsistent face1/face2 labeling across control files
    cannot mix faces.  Each returned point-observation carries the point's
    pass-1 mosaic along-coordinate ('coord0') used to linearize the bilinear
    m * T(p) term; m remains a free per-line unknown (no street direction
    assumed, only straightness).  Fine-grained guards (single-sheet lines,
    < 3 points) are applied inside solve_network so LOSO refits re-guard.
    """
    params = ref_result["params"]
    groups = {}
    n_off = 0
    for rec in anchor_registry:
        if rec["sheet"] not in params:
            n_off += 1
            continue
        groups.setdefault((rec["anchor"], rec["axis"]), []).append(rec)
    if n_off:
        log.append(f"[collin] {n_off} registry points on unsolved sheets ignored")

    obs = []
    for (street, axis), recs in sorted(groups.items()):
        sheets_on = sorted({r["sheet"] for r in recs})
        if len(sheets_on) < 2:
            log.append(f"[collin] street '{street}' ({axis} seams): all points "
                       f"on single sheet {sheets_on[0]}; no line built")
            continue
        # streets crossing vertical seams run near-horizontally in the mosaic
        # (face lines y ~ const): perp component = y, along = x.  Mirrored for
        # horizontal seams.
        perp = 1 if axis == "vertical" else 0
        along = 1 - perp
        u = np.zeros(2)
        u[perp] = 1.0
        n_face1_low = 0
        for r in recs:
            pms = (apply_T(params[r["sheet"]], r["mid1_q"]),
                   apply_T(params[r["sheet"]], r["mid2_q"]))
            order = (0, 1) if pms[0][perp] <= pms[1][perp] else (1, 0)
            if order[0] == 0:
                n_face1_low += 1
            for face_label, k in zip(("low", "high"), order):
                obs.append({
                    "line_key": (street, axis, face_label),
                    "street": street, "face": face_label, "axis": axis,
                    "sheet": r["sheet"], "seam": r["seam"], "anchor": r["anchor"],
                    "q": (r["mid1_q"], r["mid2_q"])[k], "u": u,
                    "coord0": float(pms[k][along]),
                    "sigma": float(sigma_perp),
                })
        if 0 < n_face1_low < len(recs):
            log.append(f"[collin] street '{street}' ({axis}): face1/face2 "
                       f"labeling inconsistent across files "
                       f"({n_face1_low}/{len(recs)} entries have face1 low); "
                       f"faces canonicalized by pass-1 perpendicular coordinate")
    return obs


# ----------------------------------------------------------------------------
# Network solve
# ----------------------------------------------------------------------------

def connected_sheets(observations):
    """Sheets reachable from the datum through observations."""
    graph = {}
    for o in observations:
        graph.setdefault(o["plus"], set()).add(o["minus"])
        graph.setdefault(o["minus"], set()).add(o["plus"])
    seen = set()
    stack = [DATUM_SHEET]
    while stack:
        s = stack.pop()
        if s in seen:
            continue
        seen.add(s)
        stack.extend(graph.get(s, ()))
    return seen


def solve_network(observations, log=None, rot_prior_sigma=None, collin=None):
    """Weighted linear LS + Huber IRLS.  Returns a result dict (or None if the
    datum sheet is unconstrained).  'collin' (optional) is the flat list of
    straight-street point-observations from build_collinearity_obs; each used
    face line appends two unknowns (c, m) after kappa, so sheet-parameter and
    kappa indices are unchanged."""
    if log is None:
        log = []
    collin = collin or []

    comp = connected_sheets(observations)
    usable = [o for o in observations if o["plus"] in comp and o["minus"] in comp]
    dropped_sheets = sorted({s for o in observations for s in (o["plus"], o["minus"])}
                            - comp)
    if dropped_sheets:
        n_drop = len(observations) - len(usable)
        log.append(f"[solve] sheets not connected to datum {DATUM_SHEET}: "
                   f"{dropped_sheets}; {n_drop} observations excluded")
    solved_sheets = sorted(comp & set(SHEETS))
    free_sheets = [s for s in solved_sheets if s != DATUM_SHEET]
    if not usable or not free_sheets:
        log.append("[solve] no usable observations connected to the datum; nothing to solve")
        return None

    index = {s: 4 * i for i, s in enumerate(free_sheets)}
    kappa_idx = 4 * len(free_sheets)

    # ---- collinearity lines: filter, group, guard ---------------------------
    collin_in = [c for c in collin if c["sheet"] in comp]
    if len(collin_in) != len(collin):
        log.append(f"[collin] {len(collin) - len(collin_in)} collinearity "
                   f"points on sheets disconnected from the datum; dropped")
    line_groups = {}
    for c in collin_in:
        line_groups.setdefault(c["line_key"], []).append(c)
    used_lines = []
    for lk in sorted(line_groups):
        pts = line_groups[lk]
        sheets_on = sorted({p["sheet"] for p in pts})
        if len(sheets_on) < 2:
            log.append(f"[collin] line {lk[0]}/{lk[2]}: all {len(pts)} point(s) "
                       f"from single sheet {sheets_on[0]}; contributes nothing, "
                       f"skipped")
            continue
        if len(pts) < 3:
            log.append(f"[collin] line {lk[0]}/{lk[2]}: only {len(pts)} points "
                       f"for 2 line unknowns (no redundancy); skipped")
            continue
        used_lines.append(lk)
    # line unknowns (c, m) appended AFTER kappa; along-coordinates are centered
    # per line so the (c, m) columns stay well conditioned and c is the line's
    # perp position at its mean along-coordinate.
    line_index = {lk: kappa_idx + 1 + 2 * j for j, lk in enumerate(used_lines)}
    line_center = {lk: float(np.mean([p["coord0"] for p in line_groups[lk]]))
                   for lk in used_lines}
    collin_rows = [p for lk in used_lines for p in line_groups[lk]]
    if used_lines:
        log.append(f"[collin] {len(used_lines)} straight-street face lines "
                   f"promoted to observations: {len(collin_rows)} rows, "
                   f"+{2 * len(used_lines)} line unknowns (c, m per line; "
                   f"m free -- straightness only, no direction assumed)")

    n_params = kappa_idx + 1 + 2 * len(used_lines)
    # Rotation priors (optional; rot_prior_sigma in RADIANS or None=off):
    # for the real plates, measured drafted-grid deviations from scan axes
    # are < 1.26 mrad on every sheet (20_plates/grid_orientation.json),
    # justifying b_i ~ 0 +- 2 mrad as a MEASURED-plate prior. Synthetic
    # tests use larger rotations and run with the prior off.
    n_rot_priors = len(free_sheets) if rot_prior_sigma else 0
    n_data = len(usable) + len(collin_rows)  # Huber-subject rows
    m = n_data + 1 + n_rot_priors  # + kappa prior + rotation priors

    # Design matrix (unweighted), rhs, per-row sigma
    J = np.zeros((m, n_params))
    rhs = np.zeros(m)
    sigmas = np.zeros(m)
    for i, o in enumerate(usable):
        u = o["u"]
        for sheet, q, sgn in ((o["plus"], o["q_plus"], 1.0),
                              (o["minus"], o["q_minus"], -1.0)):
            if sheet == DATUM_SHEET:
                rhs[i] -= sgn * (u[0] * q[0] + u[1] * q[1])
            else:
                J[i, index[sheet]:index[sheet] + 4] += sgn * row_coeffs(u, q)
        if o["wft"]:
            J[i, kappa_idx] = -o["wft"]
        sigmas[i] = o["sigma"]
    # collinearity rows: r = u_perp . T_i(q) - c - m * (along0 - line mean)
    for j, p in enumerate(collin_rows):
        i = len(usable) + j
        u, q = p["u"], p["q"]
        if p["sheet"] == DATUM_SHEET:
            rhs[i] -= u[0] * q[0] + u[1] * q[1]
        else:
            J[i, index[p["sheet"]]:index[p["sheet"]] + 4] = row_coeffs(u, q)
        li = line_index[p["line_key"]]
        J[i, li] = -1.0
        J[i, li + 1] = -(p["coord0"] - line_center[p["line_key"]])
        sigmas[i] = p["sigma"]
    # kappa prior row (never Huber-downweighted: it is a prior, not a datum obs)
    kappa_row = n_data
    J[kappa_row, kappa_idx] = 1.0
    rhs[kappa_row] = KAPPA_PRIOR
    sigmas[kappa_row] = KAPPA_PRIOR_SIGMA
    for k, s in enumerate(free_sheets if rot_prior_sigma else []):
        r = kappa_row + 1 + k
        J[r, index[s] + 1] = 1.0   # b parameter ~ theta for small rotations
        rhs[r] = 0.0
        sigmas[r] = rot_prior_sigma

    inv_sig = 1.0 / sigmas
    wh = np.ones(m)
    x = np.zeros(n_params)
    for _ in range(IRLS_ITERATIONS):
        sw = inv_sig * np.sqrt(wh)
        x, *_ = np.linalg.lstsq(J * sw[:, None], rhs * sw, rcond=None)
        rn = (J @ x - rhs) * inv_sig            # normalized residuals
        wh = np.where(np.abs(rn) > HUBER_DELTA,
                      HUBER_DELTA / np.maximum(np.abs(rn), 1e-12), 1.0)
        wh[n_data:] = 1.0                        # priors exempt from Huber

    # Final residuals / weights (from the last solution)
    raw_res = J @ x - rhs
    rn = raw_res * inv_sig
    wh = np.where(np.abs(rn) > HUBER_DELTA,
                  HUBER_DELTA / np.maximum(np.abs(rn), 1e-12), 1.0)
    wh[n_data:] = 1.0

    # Covariance: (J^T W J)^-1 scaled by the robust variance factor
    sw = inv_sig * np.sqrt(wh)
    Jw = J * sw[:, None]
    N = Jw.T @ Jw
    rank = int(np.linalg.matrix_rank(N))
    if rank < n_params:
        log.append(f"[solve] normal matrix rank {rank} < {n_params}: network is "
                   f"rank-deficient; pseudo-inverse used, deficient parameters "
                   f"are NOT trustworthy")
        Ninv = np.linalg.pinv(N)
    else:
        Ninv = np.linalg.inv(N)
    dof = int(m - rank)
    s0_sq = float(np.sum(wh * rn ** 2) / dof) if dof > 0 else 1.0
    if dof <= 0:
        log.append("[solve] no redundancy (dof <= 0); variance factor set to 1")
    cov = Ninv * s0_sq

    params = {DATUM_SHEET: np.array([1.0, 0.0, 0.0, 0.0])}
    for s in free_sheets:
        params[s] = x[index[s]:index[s] + 4].copy()
    kappa = float(x[kappa_idx])
    kappa_std = float(math.sqrt(max(cov[kappa_idx, kappa_idx], 0.0)))
    # Identifiability check: in this observation set any kappa change can be
    # absorbed exactly by sheet translations (across-seam loop contributions
    # cancel), so kappa is expected to be prior-determined.  Report the
    # UNSCALED marginal std so that can be seen (scaled-only reporting would
    # hide it whenever s0^2 < 1).
    kappa_unscaled_std = float(math.sqrt(max(Ninv[kappa_idx, kappa_idx], 0.0)))
    kappa_prior_dominated = kappa_unscaled_std > 0.9 * KAPPA_PRIOR_SIGMA
    if kappa_prior_dominated:
        log.append("[solve] kappa is prior-determined (unscaled marginal std "
                   f"{kappa_unscaled_std:.3f} vs prior {KAPPA_PRIOR_SIGMA}): the "
                   "across-seam network cancels kappa against sheet translations; "
                   "do not read the kappa posterior as a measurement -- compare "
                   "per-plate drafted widths directly")

    # Per-observation report
    obs_report = []
    downweighted = []
    for i, o in enumerate(usable):
        rec = {
            "pair": list(o["pair"]), "seam": o["seam"], "anchor": o["anchor"],
            "type": o["kind"], "face": o["face"],
            "residual_px": float(raw_res[i]),
            "sigma_px": float(sigmas[i]),
            "weight": float(inv_sig[i] ** 2),
            "huber_weight": float(wh[i]),
            "normalized_residual": float(rn[i]),
        }
        obs_report.append(rec)
        if wh[i] < 1.0:
            downweighted.append(rec)

    # Collinearity-row report (data-class; Huber-subject like seam obs)
    collin_report = []
    for j, p in enumerate(collin_rows):
        i = len(usable) + j
        rec = {
            "type": "collin", "seam": p["seam"], "anchor": p["anchor"],
            "street": p["street"], "face": p["face"], "axis": p["axis"],
            "sheet": p["sheet"],
            "residual_px": float(raw_res[i]),
            "sigma_px": float(sigmas[i]),
            "weight": float(inv_sig[i] ** 2),
            "huber_weight": float(wh[i]),
            "normalized_residual": float(rn[i]),
        }
        collin_report.append(rec)
        if wh[i] < 1.0:
            downweighted.append(rec)

    # Marginals
    marginals = {}
    for s in solved_sheets:
        if s == DATUM_SHEET:
            marginals[s] = {"theta_std_mrad": 0.0, "s_std_ppm": 0.0,
                            "tx_std_px": 0.0, "ty_std_px": 0.0,
                            "flag_rotation": False, "gauge": True}
            continue
        i = index[s]
        a, b = params[s][0], params[s][1]
        scale = math.hypot(a, b)
        Cab = cov[i:i + 2, i:i + 2]
        gs = np.array([a / scale, b / scale])
        gt = np.array([-b / scale ** 2, a / scale ** 2])
        var_s = float(gs @ Cab @ gs)
        var_t = float(gt @ Cab @ gt)
        theta_std_mrad = math.sqrt(max(var_t, 0.0)) * 1e3
        marginals[s] = {
            "theta_std_mrad": theta_std_mrad,
            "s_std_ppm": math.sqrt(max(var_s, 0.0)) / scale * 1e6,
            "tx_std_px": math.sqrt(max(cov[i + 2, i + 2], 0.0)),
            "ty_std_px": math.sqrt(max(cov[i + 3, i + 3], 0.0)),
            "flag_rotation": theta_std_mrad > ROT_FLAG_MRAD,
            "gauge": False,
        }

    return {
        "params": params, "kappa": kappa, "kappa_std": kappa_std,
        "kappa_unscaled_std": kappa_unscaled_std,
        "kappa_prior_dominated": kappa_prior_dominated,
        "marginals": marginals,
        "cov": cov, "index": index, "kappa_idx": kappa_idx,
        "free_sheets": free_sheets, "solved_sheets": solved_sheets,
        "unsolved_sheets": [s for s in SHEETS if s not in solved_sheets],
        "s0_sq": s0_sq, "dof": dof, "rank": rank, "n_params": n_params,
        "obs_report": obs_report, "downweighted": downweighted,
        "usable_obs": usable, "log": log,
        "collin_report": collin_report,
        "collin_lines_used": len(used_lines),
        "collin_used_line_keys": [list(lk) for lk in used_lines],
        "collin_rms_px": (float(np.sqrt(np.mean(
            [r["residual_px"] ** 2 for r in collin_report])))
            if collin_report else None),
    }


# ----------------------------------------------------------------------------
# Diagnostics
# ----------------------------------------------------------------------------

def collinearity_check(anchor_registry, result):
    """Through-street collinearity.  For each crossing feature measured in >= 2
    pairs (same axis), map the per-(pair, sheet) street CENTER point (mean of
    the two face midpoints -- immune to face1/face2 labeling differences across
    files) into the mosaic and TLS-fit a line.  For numbered streets (vertical
    seams) also report the Ave I kink: deviation of column-4 (sheets 40/44/50)
    points from the line fitted through columns 1-3 alone."""
    params = result["params"]
    groups = {}
    for rec in anchor_registry:
        if rec["sheet"] not in params:
            continue
        key = (rec["anchor"], rec["axis"])
        center_q = 0.5 * (rec["mid1_q"] + rec["mid2_q"])
        pm = apply_T(params[rec["sheet"]], center_q)
        groups.setdefault(key, []).append(
            {"sheet": rec["sheet"], "seam": rec["seam"], "pt": pm})

    out = []
    for (anchor, axis), pts in sorted(groups.items()):
        seams = sorted({p["seam"] for p in pts})
        if len(seams) < 2 or len(pts) < 3:
            continue
        P = np.array([p["pt"] for p in pts])
        dev = tls_line_deviations(P)
        entry = {
            "street": anchor, "axis": axis, "seams": seams,
            "n_points": len(pts),
            "max_perp_deviation_px": float(np.max(np.abs(dev))),
            "rms_perp_deviation_px": float(np.sqrt(np.mean(dev ** 2))),
        }
        if axis == "vertical":  # numbered street: Ave I kink check
            p123 = [p for p in pts if SHEET_COL[p["sheet"]] <= 3]
            p4 = [p for p in pts if SHEET_COL[p["sheet"]] == 4]
            if len(p123) >= 2 and p4:
                P123 = np.array([p["pt"] for p in p123])
                c = P123.mean(axis=0)
                _, _, vt = np.linalg.svd(P123 - c, full_matrices=False)
                normal = vt[-1]
                devs4 = [float((p["pt"] - c) @ normal) for p in p4]
                entry["ave_i_kink"] = {
                    "col123_points": len(p123), "col4_points": len(p4),
                    "col4_sheets": sorted({p["sheet"] for p in p4}),
                    "col4_deviation_px": devs4,
                    "max_abs_col4_deviation_px": float(max(abs(d) for d in devs4)),
                }
        out.append(entry)
    return out


def leave_one_seam_out(observations, log=None, rot_prior_sigma=None, collin=None):
    """Refit without each seam; report prediction error of the left-out
    ALONG-seam residuals under the refit parameters.  When collinearity is
    enabled the refits keep the collinearity rows EXCEPT the points measured
    on the held-out seam's control file (those are held-out data too); line
    guards are re-applied per refit inside solve_network."""
    if log is None:
        log = []
    seams = sorted({o["seam"] for o in observations})
    results = []
    for seam in seams:
        keep = [o for o in observations if o["seam"] != seam]
        held = [o for o in observations if o["seam"] == seam and o["kind"] == "along"]
        ckeep = [c for c in collin if c["seam"] != seam] if collin else None
        sub = solve_network(keep, log=[], collin=ckeep)
        if sub is None:
            results.append({"seam": seam, "status": "refit impossible (network "
                            "collapses without this seam)"})
            continue
        preds = []
        skipped = 0
        for o in held:
            if o["plus"] in sub["params"] and o["minus"] in sub["params"]:
                tp = apply_T(sub["params"][o["plus"]], o["q_plus"])
                tm = apply_T(sub["params"][o["minus"]], o["q_minus"])
                preds.append(float(o["u"] @ (tp - tm)))
            else:
                skipped += 1
        if preds:
            arr = np.array(preds)
            results.append({
                "seam": seam, "status": "ok", "n_predicted": len(preds),
                "n_skipped_disconnected": skipped,
                "pred_rms_px": float(np.sqrt(np.mean(arr ** 2))),
                "pred_max_px": float(np.max(np.abs(arr))),
            })
        else:
            results.append({"seam": seam,
                            "status": "sheet(s) disconnected without this seam; "
                                      "no prediction possible",
                            "n_skipped_disconnected": skipped})
    return results


# ----------------------------------------------------------------------------
# Output writing
# ----------------------------------------------------------------------------

def _transforms_payload(result):
    sheets = {}
    for s in sorted(result["params"]):
        a, b, tx, ty = (float(v) for v in result["params"][s])
        scale = math.hypot(a, b)
        theta = math.atan2(b, a)
        cx, cy = CENTER
        sheets[str(s)] = {
            "a": a, "b": b, "tx": tx, "ty": ty,
            "s": scale, "theta_deg": math.degrees(theta),
            "raw": {"a": a, "b": b,
                    "tx": tx - (a * cx - b * cy),
                    "ty": ty - (b * cx + a * cy)},
            "is_datum": s == DATUM_SHEET,
        }
    return {
        "convention": {
            "centered": "p_mosaic = [[a,-b],[b,a]] @ (p_sheet - center) + (tx, ty)",
            "raw": "p_mosaic = [[a,-b],[b,a]] @ p_sheet + (raw.tx, raw.ty)  "
                   "(same rotation/scale; translation composed with the recentring "
                   "-- use THIS for raw sheet-pixel coordinates)",
            "center": [float(CENTER[0]), float(CENTER[1])],
            "axes": "raster pixels, origin top-left, x right, y down",
            "gauge": f"sheet {DATUM_SHEET} fixed to identity; mosaic frame = "
                     f"sheet {DATUM_SHEET} centered pixel frame",
        },
        "kappa_px_per_ft": result["kappa"],
        "kappa_std": result["kappa_std"],
        "kappa_unscaled_std": result["kappa_unscaled_std"],
        "kappa_prior_dominated": result["kappa_prior_dominated"],
        "kappa_prior": {"mean": KAPPA_PRIOR, "sigma": KAPPA_PRIOR_SIGMA},
        "kappa_note": "kappa is a nuisance parameter used only by across-seam "
                      "constraints; the network structure cancels kappa against "
                      "sheet translations, so when kappa_prior_dominated is true "
                      "the value is the prior, not a measurement -- compare "
                      "per-plate drafted street widths directly before reusing "
                      "it downstream",
        "sheets": sheets,
        "unsolved_sheets": result["unsolved_sheets"],
        "collinearity": {
            "enabled": bool(result.get("collinearity_enabled")),
            "sigma_perp_px": result.get("collinearity_sigma_px"),
            "n_face_lines_used": result.get("collin_lines_used", 0),
            "note": "straight-street face-line constraints; m free per line "
                    "(straightness only, no street direction assumed); "
                    "linearized at pass-1 mosaic coordinates",
        },
    }


def _covariance_payload(result):
    order = []
    for s in result["free_sheets"]:
        order += [f"{s}.a", f"{s}.b", f"{s}.tx", f"{s}.ty"]
    order.append("kappa")
    for lk in result.get("collin_used_line_keys", []):
        street, _axis, face = lk
        order += [f"line:{street}/{face}.c", f"line:{street}/{face}.m"]
    marg = {str(s): result["marginals"][s] for s in result["marginals"]}
    return {
        "parameter_order": order,
        "gauge_note": f"sheet {DATUM_SHEET} is the datum (identity); it carries "
                      f"zero variance by construction",
        "robust_variance_factor_s0_sq": result["s0_sq"],
        "dof": result["dof"], "rank": result["rank"],
        "n_params": result["n_params"],
        "rotation_flag_threshold_mrad": ROT_FLAG_MRAD,
        "per_sheet_marginals": marg,
        "kappa_std": result["kappa_std"],
        "kappa_unscaled_std": result["kappa_unscaled_std"],
        "kappa_prior_dominated": result["kappa_prior_dominated"],
        "covariance": [[float(v) for v in row] for row in result["cov"]],
    }


def _rms(vals):
    return float(np.sqrt(np.mean(np.square(vals)))) if len(vals) else float("nan")


def write_diagnostics_md(path, result, seam_summaries, collin, loso, log):
    lines = []
    lines.append("# Solve diagnostics -- Galveston 1912 12-sheet block\n")
    lines.append(f"- Gauge: sheet {DATUM_SHEET} fixed to identity (mosaic frame = "
                 f"sheet {DATUM_SHEET} centered pixel frame). Its zero covariance "
                 f"is a gauge artefact, not precision.")
    lines.append(f"- Along-seam direction linearized to axis unit vectors "
                 f"(near-axis-aligned assumption; rotations are sub-degree).")
    lines.append(f"- Solved sheets: {result['solved_sheets']}")
    if result["unsolved_sheets"]:
        lines.append(f"- **Unsolved sheets (no path of observations to the datum):** "
                     f"{result['unsolved_sheets']}")
    n_collin_rows = len(result.get("collin_report", []))
    collin_note = (f" + {n_collin_rows} collinearity rows"
                   if n_collin_rows else "")
    lines.append(f"- Observations used: {len(result['obs_report'])} seam obs"
                 f"{collin_note} (+ kappa prior); parameters: "
                 f"{result['n_params']}; rank {result['rank']}; "
                 f"dof {result['dof']}")
    if result.get("collinearity_enabled"):
        lines.append(f"- Straight-street collinearity ON: "
                     f"{result['collin_lines_used']} face lines "
                     f"(+{2 * result['collin_lines_used']} line unknowns c, m; "
                     f"m free per line -- straightness only, no direction "
                     f"assumed), sigma_perp = "
                     f"{result.get('collinearity_sigma_px'):g} px, residual "
                     f"RMS {result['collin_rms_px']:.2f} px; rows linearized "
                     f"at pass-1 mosaic coordinates (two-stage solve)")
    lines.append(f"- Robust variance factor s0^2 = {result['s0_sq']:.3f}")
    lines.append(f"- Kappa posterior: {result['kappa']:.4f} +- "
                 f"{result['kappa_std']:.4f} px/ft (prior {KAPPA_PRIOR} +- "
                 f"{KAPPA_PRIOR_SIGMA}; unscaled marginal std "
                 f"{result['kappa_unscaled_std']:.4f}). Compare with per-plate "
                 f"drafted widths before reuse.")
    if result["kappa_prior_dominated"]:
        lines.append("- **Kappa is prior-determined, not measured**: the "
                     "across-seam loop structure cancels kappa against sheet "
                     "translations exactly, so the data cannot constrain it. "
                     "The across constraints therefore enforce W_ft x prior "
                     "kappa; validate kappa against per-plate drafted widths "
                     "directly.")
    lines.append("")

    lines.append("## Seams loaded\n")
    if seam_summaries:
        lines.append("| seam | axis | boundary | W (ft) | accepted | rejected | context |")
        lines.append("|---|---|---|---|---|---|---|")
        for k in sorted(seam_summaries):
            s = seam_summaries[k]
            lines.append(f"| {k} | {s['axis']} | {s['boundary']} | {s['w_ft']:.0f} "
                         f"| {s['anchors_accepted']} | {s['rejected']} "
                         f"| {s['context_only']} |")
    else:
        lines.append("No control files loaded.")
    lines.append("")

    lines.append("## Residual RMS\n")
    by_type = {}
    by_seam = {}
    for r in result["obs_report"]:
        by_type.setdefault(r["type"], []).append(r["residual_px"])
        by_seam.setdefault(r["seam"], []).append(r["residual_px"])
    lines.append("By type:")
    for t in sorted(by_type):
        lines.append(f"- {t}: RMS {_rms(by_type[t]):.2f} px (n={len(by_type[t])})")
    lines.append("\nBy seam:")
    lines.append("| seam | n | RMS (px) | max |abs| (px) |")
    lines.append("|---|---|---|---|")
    for k in sorted(by_seam):
        v = by_seam[k]
        lines.append(f"| {k} | {len(v)} | {_rms(v):.2f} | "
                     f"{max(abs(x) for x in v):.2f} |")
    lines.append("")

    lines.append("## Per-sheet marginal uncertainty (theta, s)\n")
    lines.append("| sheet | theta std (mrad) | s std (ppm) | tx std (px) | "
                 "ty std (px) | flag |")
    lines.append("|---|---|---|---|---|---|")
    flagged = []
    for s in sorted(result["marginals"]):
        m = result["marginals"][s]
        flag = "GAUGE" if m.get("gauge") else ("**ROTATION > 1.5 mrad**"
                                               if m["flag_rotation"] else "")
        if m["flag_rotation"]:
            flagged.append(s)
        lines.append(f"| {s} | {m['theta_std_mrad']:.3f} | {m['s_std_ppm']:.1f} "
                     f"| {m['tx_std_px']:.2f} | {m['ty_std_px']:.2f} | {flag} |")
    lines.append("")
    if flagged:
        lines.append(f"Flagged sheets (rotation std > {ROT_FLAG_MRAD} mrad): "
                     f"**{flagged}**")
    else:
        lines.append(f"No sheet exceeds the {ROT_FLAG_MRAD} mrad rotation-std flag. "
                     f"Per SOLVE_REQUIREMENTS, the absence of expected flags "
                     f"(40, 50, 7) on a first full solve is a tooling question "
                     f"before it is reassurance.")
    lines.append("")

    if result.get("collinearity_enabled"):
        lines.append("## Straight-street collinearity constraints (pass 2)\n")
        lines.append("Each through-street face line measured on >= 2 sheets is "
                     "one drafted straight line; faces are canonicalized "
                     "low/high by pass-1 perpendicular coordinate and NEVER "
                     "mixed. m is free per line (no direction assumed).")
        by_line = {}
        for r in result["collin_report"]:
            by_line.setdefault((r["street"], r["axis"], r["face"]), []).append(r)
        lines.append("| street | axis | face | points | sheets | RMS (px) "
                     "| max abs (px) | downweighted |")
        lines.append("|---|---|---|---|---|---|---|---|")
        for k in sorted(by_line):
            rows = by_line[k]
            res = [r["residual_px"] for r in rows]
            ndw = sum(1 for r in rows if r["huber_weight"] < 1.0)
            lines.append(f"| {k[0]} | {k[1]} | {k[2]} | {len(rows)} "
                         f"| {len({r['sheet'] for r in rows})} "
                         f"| {_rms(res):.2f} | {max(abs(v) for v in res):.2f} "
                         f"| {ndw} |")
        lines.append(f"\nOverall collinearity residual RMS: "
                     f"{result['collin_rms_px']:.2f} px "
                     f"(sigma_perp {result.get('collinearity_sigma_px'):g} px).")
        p1 = result.get("pass1_marginals")
        if p1:
            lines.append("\n### Rotation std, pass 1 (no collinearity) vs "
                         "pass 2 (with collinearity)\n")
            lines.append("| sheet | pass-1 theta std (mrad) "
                         "| pass-2 theta std (mrad) | ratio |")
            lines.append("|---|---|---|---|")
            for s in sorted(result["marginals"]):
                m1 = p1[s]["theta_std_mrad"]
                m2 = result["marginals"][s]["theta_std_mrad"]
                if p1[s].get("gauge"):
                    lines.append(f"| {s} | (gauge) | (gauge) | - |")
                else:
                    ratio = m1 / m2 if m2 > 0 else float("inf")
                    lines.append(f"| {s} | {m1:.3f} | {m2:.3f} | {ratio:.1f}x |")
        lines.append("")

    lines.append("## Down-weighted observations (Huber, delta = "
                 f"{HUBER_DELTA} sigma)\n")
    if result["downweighted"]:
        n_data_rows = len(result["obs_report"]) + len(result.get("collin_report", []))
        lines.append(f"{len(result['downweighted'])} of "
                     f"{n_data_rows} data rows (seam + collinearity) "
                     f"down-weighted (never dropped):")
        lines.append("| seam | anchor | type | face | residual (px) | "
                     "norm. resid | huber w |")
        lines.append("|---|---|---|---|---|---|---|")
        for r in result["downweighted"]:
            lines.append(f"| {r['seam']} | {r['anchor']} | {r['type']} "
                         f"| {r['face']} | {r['residual_px']:.2f} "
                         f"| {r['normalized_residual']:.2f} "
                         f"| {r['huber_weight']:.3f} |")
    else:
        lines.append("None.")
    lines.append("")

    lines.append("## Through-street collinearity\n")
    if collin:
        lines.append("Street center points (mean of the two face midpoints per "
                     "pair/sheet) mapped to the mosaic; TLS line per street.")
        lines.append("| street | axis | points | seams | max perp dev (px) | "
                     "RMS dev (px) |")
        lines.append("|---|---|---|---|---|---|")
        for c in collin:
            lines.append(f"| {c['street']} | {c['axis']} | {c['n_points']} "
                         f"| {', '.join(c['seams'])} "
                         f"| {c['max_perp_deviation_px']:.2f} "
                         f"| {c['rms_perp_deviation_px']:.2f} |")
        kinks = [c for c in collin if "ave_i_kink" in c]
        if kinks:
            lines.append("\n### Ave I (Sealy) kink check -- column-4 points vs "
                         "line through columns 1-3\n")
            lines.append("| street | col4 sheets | col4 deviations (px) | max |abs| |")
            lines.append("|---|---|---|---|")
            for c in kinks:
                k = c["ave_i_kink"]
                devs = ", ".join(f"{d:+.2f}" for d in k["col4_deviation_px"])
                lines.append(f"| {c['street']} | {k['col4_sheets']} | {devs} "
                             f"| {k['max_abs_col4_deviation_px']:.2f} |")
        else:
            lines.append("\nNo street had both column-1..3 and column-4 coverage; "
                         "Ave I kink check not possible with current data.")
    else:
        lines.append("No street measured in >= 2 pairs yet; collinearity check "
                     "not possible.")
    lines.append("")

    lines.append("## Leave-one-seam-out\n")
    if loso is None:
        lines.append("Not run (pass --loso).")
    elif loso:
        lines.append("| seam | status | n pred | pred RMS (px) | pred max (px) |")
        lines.append("|---|---|---|---|---|")
        for r in loso:
            if r["status"] == "ok":
                lines.append(f"| {r['seam']} | ok | {r['n_predicted']} "
                             f"| {r['pred_rms_px']:.2f} | {r['pred_max_px']:.2f} |")
            else:
                lines.append(f"| {r['seam']} | {r['status']} | - | - | - |")
    else:
        lines.append("No seams to test.")
    lines.append("")

    lines.append("## Load / solve log\n")
    for entry in log:
        lines.append(f"- {entry}")
    lines.append("")

    with open(path, "w") as fh:
        fh.write("\n".join(lines))


# ----------------------------------------------------------------------------
# Top-level driver
# ----------------------------------------------------------------------------

def run_solve(controls_dir, out_dir, adjacency_path, run_loso=False, rot_prior_sigma=None,
              write_outputs=True, collinearity=False,
              collinearity_sigma=COLLIN_SIGMA_DEFAULT_PX):
    """Load controls, solve, run diagnostics, write outputs.
    Returns the result dict (with 'marginals', 'collinearity', 'loso', ...)
    or None if nothing could be solved.  With collinearity=True a two-stage
    solve is run: pass 1 = current model (also provides the linearization
    coordinates), pass 2 adds the straight-street collinearity rows; the
    returned result is pass 2, with pass-1 marginals kept for comparison."""
    log = []
    adjacency_info = load_adjacency(adjacency_path)
    observations, anchor_registry, seam_summaries = load_controls(
        controls_dir, adjacency_info, log)

    result = solve_network(observations, log=log, rot_prior_sigma=rot_prior_sigma) if observations else None
    if result is None:
        log.append("[solve] SOLVE NOT POSSIBLE with current data (no observations "
                   "connected to the datum sheet)")
        if write_outputs:
            os.makedirs(out_dir, exist_ok=True)
            with open(os.path.join(out_dir, "diagnostics.md"), "w") as fh:
                fh.write("# Solve diagnostics\n\nSolve not possible: no "
                         "observations connected to the datum sheet "
                         f"({DATUM_SHEET}).\n\n## Log\n\n"
                         + "\n".join(f"- {e}" for e in log) + "\n")
        for entry in log:
            print(entry)
        return None

    collin_obs = None
    if collinearity:
        pass1_marginals = result["marginals"]
        log.append(f"[collin] two-stage solve: pass 1 done; building "
                   f"collinearity rows from pass-1 mosaic coordinates "
                   f"(sigma_perp = {collinearity_sigma:g} px)")
        collin_obs = build_collinearity_obs(
            anchor_registry, result, collinearity_sigma, log)
        result2 = solve_network(observations, log=log,
                                rot_prior_sigma=rot_prior_sigma,
                                collin=collin_obs)
        if result2 is None:
            log.append("[collin] pass-2 solve failed; keeping pass-1 result")
            collin_obs = None
        else:
            result2["pass1_marginals"] = pass1_marginals
            result = result2

    collin = collinearity_check(anchor_registry, result)
    loso = leave_one_seam_out(result["usable_obs"], log=log,
                              collin=collin_obs) if run_loso else None
    result["collinearity"] = collin
    result["loso"] = loso
    result["seam_summaries"] = seam_summaries
    result["collinearity_enabled"] = bool(collinearity and collin_obs is not None)
    result["collinearity_sigma_px"] = float(collinearity_sigma)

    if write_outputs:
        os.makedirs(out_dir, exist_ok=True)
        with open(os.path.join(out_dir, "transforms.json"), "w") as fh:
            json.dump(_transforms_payload(result), fh, indent=1)
        with open(os.path.join(out_dir, "residuals.json"), "w") as fh:
            json.dump({"observations": result["obs_report"],
                       "collinearity_observations": result.get("collin_report", []),
                       "downweighted_count": len(result["downweighted"])},
                      fh, indent=1)
        with open(os.path.join(out_dir, "covariance.json"), "w") as fh:
            json.dump(_covariance_payload(result), fh, indent=1)
        write_diagnostics_md(os.path.join(out_dir, "diagnostics.md"),
                             result, seam_summaries, collin, loso, log)
    return result


def main(argv=None):
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--controls",
                    default=os.path.join(base, "30_controls", "verified"))
    ap.add_argument("--adjacency",
                    default=os.path.join(base, "10_key", "adjacency.json"))
    ap.add_argument("--out",
                    default=os.path.join(base, "40_solve", "output"))
    ap.add_argument("--rot-prior-mrad", type=float, default=None,
                    help="rotation prior sigma in mrad (real plates: 2.0, from "
                         "measured drafted-grid deviations); default off")
    ap.add_argument("--loso", action="store_true",
                    help="run leave-one-seam-out diagnostic")
    ap.add_argument("--collinearity", action="store_true",
                    help="add straight-street face-line collinearity "
                         "constraints (two-stage solve; off by default)")
    ap.add_argument("--collinearity-sigma", type=float,
                    default=COLLIN_SIGMA_DEFAULT_PX,
                    help="perpendicular sigma for collinearity rows, px "
                         f"(drafting scatter; default "
                         f"{COLLIN_SIGMA_DEFAULT_PX:g})")
    args = ap.parse_args(argv)

    rp = args.rot_prior_mrad / 1000.0 if args.rot_prior_mrad else None
    result = run_solve(args.controls, args.out, args.adjacency, rot_prior_sigma=rp,
                       run_loso=args.loso, collinearity=args.collinearity,
                       collinearity_sigma=args.collinearity_sigma)
    if result is None:
        print("No solve produced (see diagnostics.md).")
        return 1
    print(f"Solved {len(result['solved_sheets'])} sheets "
          f"(unsolved: {result['unsolved_sheets'] or 'none'}); "
          f"kappa = {result['kappa']:.4f} +- {result['kappa_std']:.4f} px/ft; "
          f"s0^2 = {result['s0_sq']:.3f}; "
          f"{len(result['downweighted'])} obs down-weighted.")
    if result.get("collinearity_enabled"):
        print(f"Collinearity: {result['collin_lines_used']} face lines "
              f"({len(result['collin_report'])} rows, sigma_perp "
              f"{result['collinearity_sigma_px']:g} px), residual RMS "
              f"{result['collin_rms_px']:.2f} px.")
    flagged = [s for s, m in result["marginals"].items()
               if m.get("flag_rotation")]
    if flagged:
        print(f"ROTATION FLAGS (> {ROT_FLAG_MRAD} mrad): {flagged}")
    print(f"Outputs written to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
