"""Transform models and block adjustment for multi-sheet map reconstruction.

Coordinate conventions
----------------------
Source pixel space : (x, y), x to the right, y DOWN, origin at the top-left
                     corner of the *original, unmodified* scan.
Reconstruction plane : (u, v), also y-DOWN, so the assembled master is an
                     ordinary image.  Units are the pixels of the anchor
                     sheet, which is why residuals reported by this module are
                     directly readable as "original scan pixels".
World space        : (X, Y) in a projected CRS, y-UP.  Only ever reached by a
                     single global transform applied to the finished
                     reconstruction (see `scripts/12_export_final.py`), never
                     per sheet -- that is what keeps the historical geometry
                     from being rewritten by modern data.

Every transform is carried as a 3x3 homogeneous matrix so that similarity,
affine and projective models are interchangeable downstream.  Only the
*parameterisation* used during fitting differs.
"""

from __future__ import annotations

import numpy as np

KINDS = ("similarity", "affine", "projective")
NPARAMS = {"similarity": 4, "affine": 6, "projective": 8}
# Minimum tie/control points a sheet needs before its model is determined.
MIN_POINTS = {"similarity": 2, "affine": 3, "projective": 4}


# --------------------------------------------------------------------------
# parameter vector  <->  3x3 matrix
# --------------------------------------------------------------------------
def params_to_matrix(kind: str, p: np.ndarray) -> np.ndarray:
    p = np.asarray(p, dtype=float)
    if kind == "similarity":
        a, b, tx, ty = p
        return np.array([[a, -b, tx], [b, a, ty], [0.0, 0.0, 1.0]])
    if kind == "affine":
        a, b, tx, c, d, ty = p
        return np.array([[a, b, tx], [c, d, ty], [0.0, 0.0, 1.0]])
    if kind == "projective":
        return np.array([[p[0], p[1], p[2]], [p[3], p[4], p[5]], [p[6], p[7], 1.0]])
    raise ValueError(f"unknown transform kind {kind!r}")


def matrix_to_params(kind: str, H: np.ndarray) -> np.ndarray:
    H = np.asarray(H, dtype=float)
    H = H / H[2, 2]
    if kind == "similarity":
        # Project onto the conformal subspace: a = (h00+h11)/2, b = (h10-h01)/2
        a = 0.5 * (H[0, 0] + H[1, 1])
        b = 0.5 * (H[1, 0] - H[0, 1])
        return np.array([a, b, H[0, 2], H[1, 2]])
    if kind == "affine":
        return np.array([H[0, 0], H[0, 1], H[0, 2], H[1, 0], H[1, 1], H[1, 2]])
    if kind == "projective":
        return np.array([H[0, 0], H[0, 1], H[0, 2], H[1, 0], H[1, 1], H[1, 2], H[2, 0], H[2, 1]])
    raise ValueError(f"unknown transform kind {kind!r}")


def identity_params(kind: str) -> np.ndarray:
    return matrix_to_params(kind, np.eye(3))


def apply(H: np.ndarray, pts: np.ndarray) -> np.ndarray:
    """Apply a 3x3 homography to an (N,2) array of points."""
    pts = np.atleast_2d(np.asarray(pts, dtype=float))
    ones = np.ones((pts.shape[0], 1))
    q = np.hstack([pts, ones]) @ np.asarray(H, dtype=float).T
    w = q[:, 2:3]
    # A well-conditioned map never produces w==0 inside the image; guard anyway.
    w = np.where(np.abs(w) < 1e-12, np.sign(w) * 1e-12 + 1e-12, w)
    return q[:, :2] / w


def decompose_affine(H: np.ndarray) -> dict:
    """Human-readable description of the linear part, for QC reporting."""
    A = np.asarray(H, dtype=float)[:2, :2]
    scale_x = float(np.hypot(A[0, 0], A[1, 0]))
    scale_y = float(np.hypot(A[0, 1], A[1, 1]))
    rot = float(np.degrees(np.arctan2(A[1, 0], A[0, 0])))
    det = float(np.linalg.det(A))
    # Shear as the departure from orthogonality of the two column vectors.
    c0, c1 = A[:, 0], A[:, 1]
    denom = (np.linalg.norm(c0) * np.linalg.norm(c1)) or 1.0
    shear = float(np.degrees(np.arcsin(np.clip(np.dot(c0, c1) / denom, -1.0, 1.0))))
    # Anisotropy: 0 for a pure similarity.
    aniso = float(abs(scale_x - scale_y) / max(scale_x, scale_y, 1e-12))
    return {
        "scale_x": scale_x,
        "scale_y": scale_y,
        "rotation_deg": rot,
        "shear_deg": shear,
        "determinant": det,
        "anisotropy": aniso,
        "flips": bool(det < 0),
    }


# --------------------------------------------------------------------------
# single-transform fitting (used for the modern-georeferencing stage)
# --------------------------------------------------------------------------
def fit_single(kind: str, src: np.ndarray, dst: np.ndarray,
               weights: np.ndarray | None = None) -> np.ndarray:
    """Least-squares fit of one transform mapping src -> dst."""
    src = np.atleast_2d(np.asarray(src, dtype=float))
    dst = np.atleast_2d(np.asarray(dst, dtype=float))
    if src.shape != dst.shape:
        raise ValueError("src and dst must have the same shape")
    n = src.shape[0]
    if n < MIN_POINTS[kind]:
        raise ValueError(f"{kind} needs >= {MIN_POINTS[kind]} points, got {n}")
    w = np.ones(n) if weights is None else np.asarray(weights, dtype=float)

    if kind == "projective":
        return _gauss_newton_projective(fit_single("affine", src, dst, w), src, dst, w)

    A, b = _linear_rows(kind, src, dst, w)
    sol, *_ = np.linalg.lstsq(A, b, rcond=None)
    return params_to_matrix(kind, sol)


def _linear_rows(kind, src, dst, w):
    """Design matrix for the linear (similarity/affine) models."""
    x, y = src[:, 0], src[:, 1]
    u, v = dst[:, 0], dst[:, 1]
    sw = np.sqrt(w)
    n = len(x)
    if kind == "similarity":
        A = np.zeros((2 * n, 4))
        A[0::2, 0], A[0::2, 1], A[0::2, 2] = x, -y, 1.0
        A[1::2, 0], A[1::2, 1], A[1::2, 3] = y, x, 1.0
    elif kind == "affine":
        A = np.zeros((2 * n, 6))
        A[0::2, 0], A[0::2, 1], A[0::2, 2] = x, y, 1.0
        A[1::2, 3], A[1::2, 4], A[1::2, 5] = x, y, 1.0
    else:
        raise ValueError(kind)
    b = np.empty(2 * n)
    b[0::2], b[1::2] = u, v
    scale = np.repeat(sw, 2)
    return A * scale[:, None], b * scale


def _gauss_newton_projective(H0, src, dst, w, iters=60, tol=1e-12):
    p = matrix_to_params("projective", H0)
    x, y = src[:, 0], src[:, 1]
    sw = np.sqrt(np.repeat(w, 2))
    prev = np.inf
    for _ in range(iters):
        den = p[6] * x + p[7] * y + 1.0
        den = np.where(np.abs(den) < 1e-12, 1e-12, den)
        ux = (p[0] * x + p[1] * y + p[2]) / den
        vy = (p[3] * x + p[4] * y + p[5]) / den
        r = np.empty(2 * len(x))
        r[0::2] = ux - dst[:, 0]
        r[1::2] = vy - dst[:, 1]
        J = np.zeros((2 * len(x), 8))
        J[0::2, 0], J[0::2, 1], J[0::2, 2] = x / den, y / den, 1.0 / den
        J[0::2, 6], J[0::2, 7] = -ux * x / den, -ux * y / den
        J[1::2, 3], J[1::2, 4], J[1::2, 5] = x / den, y / den, 1.0 / den
        J[1::2, 6], J[1::2, 7] = -vy * x / den, -vy * y / den
        dp, *_ = np.linalg.lstsq(J * sw[:, None], -r * sw, rcond=None)
        p = p + dp
        cost = float(np.sum((r * sw) ** 2))
        if abs(prev - cost) < tol * max(cost, 1.0):
            break
        prev = cost
    return params_to_matrix("projective", p)


# --------------------------------------------------------------------------
# block adjustment
# --------------------------------------------------------------------------
class TiePoint:
    """One physical feature seen on two sheets.

    `a`/`b` are sheet ids, `pa`/`pb` the observed source-pixel coordinates on
    each.  Adjustment drives T_a(pa) - T_b(pb) to zero, which is exactly the
    requirement that the two sheets meet on the ground.
    """

    __slots__ = ("a", "pa", "b", "pb", "weight", "label", "kind", "wx", "wy")

    def __init__(self, a, pa, b, pb, weight=1.0, label="", kind="tie",
                 weight_xy=None):
        self.a, self.pa = a, (float(pa[0]), float(pa[1]))
        self.b, self.pb = b, (float(pb[0]), float(pb[1]))
        self.weight, self.label, self.kind = float(weight), label, kind
        # Per-axis weights. Sheets that abut along an avenue share no inked
        # ground point -- each draws only its own frontage -- so the tie's
        # ACROSS-seam coordinate is constructed by stepping half the printed
        # street width inward, while its ALONG-seam coordinate is measured
        # directly. Those deserve different sigmas: the plates are observed to
        # disagree about an avenue's drawn width by up to 9 px. Defaults to
        # isotropic, so existing callers are unaffected.
        if weight_xy is None:
            self.wx = self.wy = float(weight)
        else:
            self.wx, self.wy = float(weight_xy[0]), float(weight_xy[1])


class Anchor:
    """An absolute observation: sheet `s` pixel `p` should land on `target`."""

    __slots__ = ("s", "p", "target", "weight", "label")

    def __init__(self, s, p, target, weight=1.0, label=""):
        self.s, self.p = s, (float(p[0]), float(p[1]))
        self.target = (float(target[0]), float(target[1]))
        self.weight, self.label = float(weight), label


def _huber_weights(resid_norm: np.ndarray, delta: float) -> np.ndarray:
    """IRLS weights for the Huber loss (1 inside delta, delta/r outside)."""
    r = np.maximum(resid_norm, 1e-12)
    return np.where(r <= delta, 1.0, delta / r)


def adjust(
    sheets,
    ties,
    anchors=None,
    kind="affine",
    anchor_sheet=None,
    conformal_weight=0.0,
    robust=True,
    huber_delta=6.0,
    iterations=12,
    init=None,
):
    """Jointly solve every sheet transform from tie points (+ optional anchors).

    Parameters
    ----------
    sheets : ordered ids of the mapped regions being solved.
    ties   : list[TiePoint] linking pairs of sheets.
    anchors: list[Anchor] pinning sheet pixels to reconstruction coordinates.
    kind   : "similarity" | "affine" | "projective".
    anchor_sheet : id whose transform is held at identity to fix the gauge.
        Tie points alone determine the solution only up to a global transform;
        holding one sheet fixed removes that freedom and makes the
        reconstruction plane equal to that sheet's own pixel grid.  Ignored
        when `anchors` are supplied, since those fix the datum themselves.
    conformal_weight : penalty pulling the affine linear part toward a
        similarity (a==d, b==-c).  This is the knob that stops the adjustment
        from shearing 1889 survey geometry to absorb tie-point noise.  0
        disables it.
    robust : IRLS with a Huber loss so a single mis-picked tie point cannot
        drag the whole network.
    huber_delta : residual (in reconstruction units) beyond which a tie point
        starts being down-weighted.

    Returns
    -------
    dict with keys: transforms, residuals, stats, kind, free_sheets.
    """
    if kind not in KINDS:
        raise ValueError(f"unknown kind {kind!r}")
    anchors = list(anchors or [])
    ties = list(ties)
    sheets = list(sheets)

    if kind == "projective":
        # Start from the linear solution, then refine; a cold start on a
        # homography network is where these adjustments usually diverge.
        seed = adjust(sheets, ties, anchors, "affine", anchor_sheet,
                      conformal_weight, robust, huber_delta, iterations, init)
        return _adjust_projective(sheets, ties, anchors, anchor_sheet,
                                  seed["transforms"], robust, huber_delta, iterations)

    np_ = NPARAMS[kind]
    fixed = {}
    if not anchors:
        if anchor_sheet is None:
            anchor_sheet = sheets[0]
        if anchor_sheet not in sheets:
            raise ValueError(f"anchor_sheet {anchor_sheet!r} not among sheets")
        fixed[anchor_sheet] = identity_params(kind)

    free = [s for s in sheets if s not in fixed]
    idx = {s: i * np_ for i, s in enumerate(free)}
    ncol = np_ * len(free)
    if ncol == 0:
        transforms = {s: params_to_matrix(kind, fixed[s]) for s in fixed}
        return {"transforms": transforms, "residuals": [], "kind": kind,
                "free_sheets": [], "stats": _stats([])}

    def block(p, sign):
        """Rows of d(T(p))/d(params) for one point, scaled by +/-1."""
        x, y = p
        if kind == "similarity":
            return sign * np.array([[x, -y, 1.0, 0.0], [y, x, 0.0, 1.0]])
        return sign * np.array([[x, y, 1.0, 0, 0, 0], [0, 0, 0, x, y, 1.0]])

    def const(p, params):
        return apply(params_to_matrix(kind, params), [p])[0]

    w_iter = np.ones(len(ties) + len(anchors))
    result = None
    for _ in range(max(1, iterations) if robust else 1):
        rows, rhs, wts = [], [], []
        for k, t in enumerate(ties):
            row = np.zeros((2, ncol))
            r = np.zeros(2)
            if t.a in idx:
                row[:, idx[t.a]:idx[t.a] + np_] += block(t.pa, +1)
            else:
                r -= const(t.pa, fixed[t.a])
            if t.b in idx:
                row[:, idx[t.b]:idx[t.b] + np_] += block(t.pb, -1)
            else:
                r += const(t.pb, fixed[t.b])
            rows.append(row)
            rhs.append(r)
            wts.append((t.wx * w_iter[k], t.wy * w_iter[k]))
        for j, a in enumerate(anchors):
            row = np.zeros((2, ncol))
            r = np.array(a.target, dtype=float)
            if a.s in idx:
                row[:, idx[a.s]:idx[a.s] + np_] += block(a.p, +1)
            else:
                r -= const(a.p, fixed[a.s])
            rows.append(row)
            rhs.append(r)
            wts.append((a.weight * w_iter[len(ties) + j],) * 2)

        if conformal_weight > 0 and kind == "affine":
            # Two soft equations per free sheet: (a - d) = 0 and (b + c) = 0.
            for s in free:
                row = np.zeros((2, ncol))
                o = idx[s]
                row[0, o + 0], row[0, o + 4] = 1.0, -1.0   # a - d
                row[1, o + 1], row[1, o + 3] = 1.0, 1.0    # b + c
                rows.append(row)
                rhs.append(np.zeros(2))
                wts.append((conformal_weight, conformal_weight))

        A = np.vstack(rows)
        b = np.concatenate(rhs)
        sw = np.sqrt(np.asarray(wts, dtype=float).reshape(-1))
        sol, *_ = np.linalg.lstsq(A * sw[:, None], b * sw, rcond=None)

        transforms = {s: params_to_matrix(kind, fixed[s]) for s in fixed}
        for s in free:
            transforms[s] = params_to_matrix(kind, sol[idx[s]:idx[s] + np_])

        residuals = _residuals(transforms, ties, anchors)
        if robust and residuals:
            # Huber on the WEIGHT-NORMALISED residual (r/sigma), not the raw one.
            # With heterogeneous uncertainties, judging outliers on raw pixels
            # would down-weight exactly the loose-but-honest observations and
            # leave a tight-but-wrong one untouched. Identical to the old
            # behaviour when every weight is 1.
            rn = np.array([r["normalized"] for r in residuals])
            w_iter = _huber_weights(rn, huber_delta)
        result = {"transforms": transforms, "residuals": residuals, "kind": kind,
                  "free_sheets": free, "stats": _stats(residuals)}
        if not robust:
            break
    return result


def _adjust_projective(sheets, ties, anchors, anchor_sheet, seed, robust,
                       huber_delta, iterations):
    fixed = {}
    if not anchors:
        anchor_sheet = anchor_sheet or sheets[0]
        fixed[anchor_sheet] = identity_params("projective")
    free = [s for s in sheets if s not in fixed]
    idx = {s: i * 8 for i, s in enumerate(free)}
    ncol = 8 * len(free)
    P = {s: matrix_to_params("projective", seed[s]) for s in sheets}
    for s in fixed:
        P[s] = fixed[s]
    if ncol == 0:
        transforms = {s: params_to_matrix("projective", P[s]) for s in sheets}
        return {"transforms": transforms, "residuals": _residuals(transforms, ties, anchors),
                "kind": "projective", "free_sheets": [], "stats": _stats([])}

    def fwd_and_jac(p, pt):
        x, y = pt
        den = p[6] * x + p[7] * y + 1.0
        den = den if abs(den) > 1e-12 else 1e-12
        ux = (p[0] * x + p[1] * y + p[2]) / den
        vy = (p[3] * x + p[4] * y + p[5]) / den
        J = np.zeros((2, 8))
        J[0, 0], J[0, 1], J[0, 2] = x / den, y / den, 1.0 / den
        J[0, 6], J[0, 7] = -ux * x / den, -ux * y / den
        J[1, 3], J[1, 4], J[1, 5] = x / den, y / den, 1.0 / den
        J[1, 6], J[1, 7] = -vy * x / den, -vy * y / den
        return np.array([ux, vy]), J

    w_iter = np.ones(len(ties) + len(anchors))
    result = None
    for _ in range(max(3, iterations)):
        rows, rhs, wts = [], [], []
        for k, t in enumerate(ties):
            fa, Ja = fwd_and_jac(P[t.a], t.pa)
            fb, Jb = fwd_and_jac(P[t.b], t.pb)
            row = np.zeros((2, ncol))
            if t.a in idx:
                row[:, idx[t.a]:idx[t.a] + 8] += Ja
            if t.b in idx:
                row[:, idx[t.b]:idx[t.b] + 8] -= Jb
            rows.append(row)
            rhs.append(-(fa - fb))
            wts.append(t.weight * w_iter[k])
        for j, a in enumerate(anchors):
            fa, Ja = fwd_and_jac(P[a.s], a.p)
            row = np.zeros((2, ncol))
            if a.s in idx:
                row[:, idx[a.s]:idx[a.s] + 8] += Ja
            rows.append(row)
            rhs.append(np.array(a.target) - fa)
            wts.append(a.weight * w_iter[len(ties) + j])

        A = np.vstack(rows)
        b = np.concatenate(rhs)
        sw = np.sqrt(np.repeat(np.asarray(wts, dtype=float), 2))
        dp, *_ = np.linalg.lstsq(A * sw[:, None], b * sw, rcond=None)
        for s in free:
            P[s] = P[s] + dp[idx[s]:idx[s] + 8]

        transforms = {s: params_to_matrix("projective", P[s]) for s in sheets}
        residuals = _residuals(transforms, ties, anchors)
        if robust and residuals:
            # Huber on the WEIGHT-NORMALISED residual (r/sigma), not the raw one.
            # With heterogeneous uncertainties, judging outliers on raw pixels
            # would down-weight exactly the loose-but-honest observations and
            # leave a tight-but-wrong one untouched. Identical to the old
            # behaviour when every weight is 1.
            rn = np.array([r["normalized"] for r in residuals])
            w_iter = _huber_weights(rn, huber_delta)
        result = {"transforms": transforms, "residuals": residuals,
                  "kind": "projective", "free_sheets": free,
                  "stats": _stats(residuals)}
        if np.max(np.abs(dp)) < 1e-12:
            break
    return result


def _residuals(transforms, ties, anchors):
    out = []
    for t in ties:
        pa = apply(transforms[t.a], [t.pa])[0]
        pb = apply(transforms[t.b], [t.pb])[0]
        d = pa - pb
        out.append({
            "kind": "tie", "label": t.label, "sheet_a": t.a, "sheet_b": t.b,
            "dx": float(d[0]), "dy": float(d[1]),
            "residual": float(np.hypot(*d)), "weight": t.weight,
            "normalized": float(np.sqrt(t.wx * d[0] ** 2 + t.wy * d[1] ** 2)),
        })
    for a in anchors:
        p = apply(transforms[a.s], [a.p])[0]
        d = p - np.array(a.target)
        out.append({
            "kind": "anchor", "label": a.label, "sheet_a": a.s, "sheet_b": None,
            "dx": float(d[0]), "dy": float(d[1]),
            "residual": float(np.hypot(*d)), "weight": a.weight,
            "normalized": float(np.hypot(*d) * np.sqrt(a.weight)),
        })
    return out


def _stats(residuals):
    if not residuals:
        return {"n": 0, "median": None, "mean": None, "rms": None,
                "p90": None, "max": None}
    r = np.array([x["residual"] for x in residuals], dtype=float)
    return {
        "n": int(r.size),
        "median": float(np.median(r)),
        "mean": float(np.mean(r)),
        "rms": float(np.sqrt(np.mean(r ** 2))),
        "p90": float(np.percentile(r, 90)),
        "max": float(np.max(r)),
    }


def design_rank_report(sheets, ties, anchors=None, kind="affine",
                       anchor_sheet=None, conformal_weight=0.0, tol=1e-10):
    """Rank/nullity of the adjustment, *before* trusting any solution.

    This exists because of a structural trap in map-sheet mosaicking.  Adjacent
    Sanborn sheets abut along a LINE and (often) share no 2-D overlap, so every
    tie point available between two sheets is collinear.  A per-sheet affine
    model is then rank deficient: for each pair of seams meeting at a corner
    there is an exact shear of the plane that fixes the seam lines pointwise
    while deforming everything else, so the residuals stay near zero while the
    sheets are silently sheared to nonsense.  Verified on a 2x2 test network:
    per-sheet affine gives nullity 4, per-sheet similarity nullity 0.

    A nonzero `nullity` here means DO NOT USE this model with these
    observations.  Fixes, in order of preference: use `similarity`; obtain
    genuine 2-D overlap or absolute GCPs spread across each sheet; or apply
    `conformal_weight` (which removes exactly the offending shear modes).
    """
    anchors = list(anchors or [])
    sheets = list(sheets)
    if kind == "projective":
        # A projective network must be measured with its OWN 8 parameters per
        # sheet, linearised about a working solution.  Substituting the affine
        # design here would be unsound in the direction that matters: affine
        # having full rank says nothing about the two extra parameters per
        # sheet that projective adds, and those are exactly the ones that let a
        # sheet fold over on itself while the residuals stay small.
        return _projective_rank_report(sheets, ties, anchors, anchor_sheet, tol)
    kind_eff = kind
    np_ = NPARAMS[kind_eff]
    fixed = set()
    if not anchors:
        fixed = {anchor_sheet or sheets[0]}
    free = [s for s in sheets if s not in fixed]
    idx = {s: i * np_ for i, s in enumerate(free)}
    ncol = np_ * len(free)
    if ncol == 0:
        return {"kind": kind, "ncol": 0, "rank": 0, "nullity": 0,
                "condition": None, "ok": True}

    def block(p, sign):
        x, y = p
        if kind_eff == "similarity":
            return sign * np.array([[x, -y, 1.0, 0.0], [y, x, 0.0, 1.0]])
        return sign * np.array([[x, y, 1.0, 0, 0, 0], [0, 0, 0, x, y, 1.0]])

    rows = []
    for t in ties:
        row = np.zeros((2, ncol))
        if t.a in idx:
            row[:, idx[t.a]:idx[t.a] + np_] += block(t.pa, +1)
        if t.b in idx:
            row[:, idx[t.b]:idx[t.b] + np_] += block(t.pb, -1)
        rows.append(row)
    for a in anchors:
        row = np.zeros((2, ncol))
        if a.s in idx:
            row[:, idx[a.s]:idx[a.s] + np_] += block(a.p, +1)
        rows.append(row)
    if conformal_weight > 0 and kind_eff == "affine":
        for s in free:
            row = np.zeros((2, ncol))
            o = idx[s]
            row[0, o + 0], row[0, o + 4] = 1.0, -1.0
            row[1, o + 1], row[1, o + 3] = 1.0, 1.0
            rows.append(row * conformal_weight)
    if not rows:
        return {"kind": kind, "ncol": ncol, "rank": 0, "nullity": ncol,
                "condition": None, "ok": False}

    A = np.vstack(rows)
    sv = np.linalg.svd(A, compute_uv=False)
    rank = int(np.sum(sv > sv[0] * tol)) if sv[0] > 0 else 0
    nullity = ncol - rank
    cond = float(sv[0] / sv[rank - 1]) if rank > 0 else float("inf")
    return {
        "kind": kind, "ncol": int(ncol), "rank": rank, "nullity": int(nullity),
        "condition": cond, "ok": nullity == 0,
        "note": ("rank deficient - collinear (seam-line-only) ties cannot "
                 "determine this model; use similarity, add 2-D spread "
                 "observations, or raise conformal_weight") if nullity else "",
    }


def _projective_rank_report(sheets, ties, anchors, anchor_sheet, tol):
    """Rank of the projective network, linearised about the affine solution."""
    seed = adjust(sheets, ties, anchors, "affine", anchor_sheet,
                  conformal_weight=0.0, robust=False)["transforms"]
    fixed = set()
    if not anchors:
        fixed = {anchor_sheet or sheets[0]}
    free = [s for s in sheets if s not in fixed]
    idx = {s: i * 8 for i, s in enumerate(free)}
    ncol = 8 * len(free)
    if ncol == 0:
        return {"kind": "projective", "ncol": 0, "rank": 0, "nullity": 0,
                "condition": None, "ok": True}
    P = {s: matrix_to_params("projective", seed[s]) for s in sheets}

    def jac(p, pt):
        x, y = pt
        den = p[6] * x + p[7] * y + 1.0
        den = den if abs(den) > 1e-12 else 1e-12
        ux = (p[0] * x + p[1] * y + p[2]) / den
        vy = (p[3] * x + p[4] * y + p[5]) / den
        J = np.zeros((2, 8))
        J[0, 0], J[0, 1], J[0, 2] = x / den, y / den, 1.0 / den
        J[0, 6], J[0, 7] = -ux * x / den, -ux * y / den
        J[1, 3], J[1, 4], J[1, 5] = x / den, y / den, 1.0 / den
        J[1, 6], J[1, 7] = -vy * x / den, -vy * y / den
        return J

    rows = []
    for t in ties:
        row = np.zeros((2, ncol))
        if t.a in idx:
            row[:, idx[t.a]:idx[t.a] + 8] += jac(P[t.a], t.pa)
        if t.b in idx:
            row[:, idx[t.b]:idx[t.b] + 8] -= jac(P[t.b], t.pb)
        rows.append(row)
    for a in anchors:
        row = np.zeros((2, ncol))
        if a.s in idx:
            row[:, idx[a.s]:idx[a.s] + 8] += jac(P[a.s], a.p)
        rows.append(row)
    if not rows:
        return {"kind": "projective", "ncol": ncol, "rank": 0, "nullity": ncol,
                "condition": None, "ok": False}
    A = np.vstack(rows)
    sv = np.linalg.svd(A, compute_uv=False)
    rank = int(np.sum(sv > sv[0] * tol)) if sv[0] > 0 else 0
    nullity = ncol - rank
    return {"kind": "projective", "ncol": int(ncol), "rank": rank,
            "nullity": int(nullity),
            "condition": float(sv[0] / sv[rank - 1]) if rank else float("inf"),
            "ok": nullity == 0,
            "note": ("rank deficient - not enough well-spread observations to "
                     "determine 8 parameters per sheet") if nullity else ""}


# What a scanned, printed page can physically do.  A solved sheet outside these
# bounds is not a distorted scan, it is a broken solution -- however small its
# residuals are.  Residuals measure agreement at the control points only; these
# limits are what keep agreement from being bought with nonsense in between.
PLAUSIBLE_LIMITS = {
    "scale_lo": 0.80, "scale_hi": 1.25,
    "rotation_deg": 8.0, "shear_deg": 3.0, "anisotropy": 0.06,
}


def plausibility_flags(H, limits=None):
    """Names of the physical limits a solved transform violates ([] if none)."""
    lim = dict(PLAUSIBLE_LIMITS)
    lim.update(limits or {})
    d = decompose_affine(H)
    flags = []
    if not (lim["scale_lo"] <= d["scale_x"] <= lim["scale_hi"]) or \
       not (lim["scale_lo"] <= d["scale_y"] <= lim["scale_hi"]):
        flags.append("scale")
    if abs(d["rotation_deg"]) > lim["rotation_deg"]:
        flags.append("rotation")
    if abs(d["shear_deg"]) > lim["shear_deg"]:
        flags.append("shear")
    if d["anisotropy"] > lim["anisotropy"]:
        flags.append("anisotropy")
    if d["flips"]:
        flags.append("MIRRORED")
    return flags


def observation_counts(sheets, ties, anchors=None):
    """Points touching each sheet -- used to detect under-determined sheets."""
    counts = {s: 0 for s in sheets}
    for t in ties:
        if t.a in counts:
            counts[t.a] += 1
        if t.b in counts:
            counts[t.b] += 1
    for a in (anchors or []):
        if a.s in counts:
            counts[a.s] += 1
    return counts


def check_determinacy(sheets, ties, anchors=None, kind="affine"):
    """Report sheets with too few observations for the requested model."""
    counts = observation_counts(sheets, ties, anchors)
    need = MIN_POINTS[kind]
    return {
        "kind": kind,
        "required_points_per_sheet": need,
        "counts": counts,
        "underdetermined": sorted(s for s, c in counts.items() if c < need),
    }
