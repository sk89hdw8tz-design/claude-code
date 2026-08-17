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

Robust fitting: weighted linear least squares + IRLS with Huber (delta = 2.5,
in units of sigma), 10 iterations.  Every down-weighted observation is logged.

Outputs (40_solve/output/): transforms.json, residuals.json, covariance.json,
diagnostics.md.  Diagnostics: per-sheet marginal std of theta/s (flag rotation
std > 1.5 mrad), leave-one-seam-out (--loso), through-street collinearity with
the Ave I kink check.

Usage:
    /home/user/g1912/venv/bin/python solver.py [--controls DIR] [--out DIR]
        [--loso] [--adjacency PATH]
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
        pair = tuple(int(p) for p in pair)
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


def solve_network(observations, log=None):
    """Weighted linear LS + Huber IRLS.  Returns a result dict (or None if the
    datum sheet is unconstrained)."""
    if log is None:
        log = []

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
    n_params = kappa_idx + 1
    m = len(usable) + 1  # + kappa prior

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
    # kappa prior row (never Huber-downweighted: it is a prior, not a datum obs)
    J[m - 1, kappa_idx] = 1.0
    rhs[m - 1] = KAPPA_PRIOR
    sigmas[m - 1] = KAPPA_PRIOR_SIGMA

    inv_sig = 1.0 / sigmas
    wh = np.ones(m)
    x = np.zeros(n_params)
    for _ in range(IRLS_ITERATIONS):
        sw = inv_sig * np.sqrt(wh)
        x, *_ = np.linalg.lstsq(J * sw[:, None], rhs * sw, rcond=None)
        rn = (J @ x - rhs) * inv_sig            # normalized residuals
        wh = np.where(np.abs(rn) > HUBER_DELTA,
                      HUBER_DELTA / np.maximum(np.abs(rn), 1e-12), 1.0)
        wh[m - 1] = 1.0                          # prior exempt from Huber

    # Final residuals / weights (from the last solution)
    raw_res = J @ x - rhs
    rn = raw_res * inv_sig
    wh = np.where(np.abs(rn) > HUBER_DELTA,
                  HUBER_DELTA / np.maximum(np.abs(rn), 1e-12), 1.0)
    wh[m - 1] = 1.0

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


def leave_one_seam_out(observations, log=None):
    """Refit without each seam; report prediction error of the left-out
    ALONG-seam residuals under the refit parameters."""
    if log is None:
        log = []
    seams = sorted({o["seam"] for o in observations})
    results = []
    for seam in seams:
        keep = [o for o in observations if o["seam"] != seam]
        held = [o for o in observations if o["seam"] == seam and o["kind"] == "along"]
        sub = solve_network(keep, log=[])
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
    }


def _covariance_payload(result):
    order = []
    for s in result["free_sheets"]:
        order += [f"{s}.a", f"{s}.b", f"{s}.tx", f"{s}.ty"]
    order.append("kappa")
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
    lines.append(f"- Observations used: {len(result['obs_report'])} "
                 f"(+ kappa prior); parameters: {result['n_params']}; "
                 f"rank {result['rank']}; dof {result['dof']}")
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

    lines.append("## Down-weighted observations (Huber, delta = "
                 f"{HUBER_DELTA} sigma)\n")
    if result["downweighted"]:
        lines.append(f"{len(result['downweighted'])} of "
                     f"{len(result['obs_report'])} observations down-weighted "
                     f"(never dropped):")
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

def run_solve(controls_dir, out_dir, adjacency_path, run_loso=False,
              write_outputs=True):
    """Load controls, solve, run diagnostics, write outputs.
    Returns the result dict (with 'marginals', 'collinearity', 'loso', ...)
    or None if nothing could be solved."""
    log = []
    adjacency_info = load_adjacency(adjacency_path)
    observations, anchor_registry, seam_summaries = load_controls(
        controls_dir, adjacency_info, log)

    result = solve_network(observations, log=log) if observations else None
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

    collin = collinearity_check(anchor_registry, result)
    loso = leave_one_seam_out(result["usable_obs"], log=log) if run_loso else None
    result["collinearity"] = collin
    result["loso"] = loso
    result["seam_summaries"] = seam_summaries

    if write_outputs:
        os.makedirs(out_dir, exist_ok=True)
        with open(os.path.join(out_dir, "transforms.json"), "w") as fh:
            json.dump(_transforms_payload(result), fh, indent=1)
        with open(os.path.join(out_dir, "residuals.json"), "w") as fh:
            json.dump({"observations": result["obs_report"],
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
    ap.add_argument("--loso", action="store_true",
                    help="run leave-one-seam-out diagnostic")
    args = ap.parse_args(argv)

    result = run_solve(args.controls, args.out, args.adjacency,
                       run_loso=args.loso)
    if result is None:
        print("No solve produced (see diagnostics.md).")
        return 1
    print(f"Solved {len(result['solved_sheets'])} sheets "
          f"(unsolved: {result['unsolved_sheets'] or 'none'}); "
          f"kappa = {result['kappa']:.4f} +- {result['kappa_std']:.4f} px/ft; "
          f"s0^2 = {result['s0_sq']:.3f}; "
          f"{len(result['downweighted'])} obs down-weighted.")
    flagged = [s for s, m in result["marginals"].items()
               if m.get("flag_rotation")]
    if flagged:
        print(f"ROTATION FLAGS (> {ROT_FLAG_MRAD} mrad): {flagged}")
    print(f"Outputs written to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
