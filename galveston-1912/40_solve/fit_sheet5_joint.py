#!/usr/bin/env python3
"""Joint two-panel fit for sheet 5, coupled by the duplicated drafted ground.

WHY THIS EXISTS
---------------
`fit_sheet5.py` solves each wharf panel INDEPENDENTLY against the frozen block.
Nothing in that model ties panel A to panel B, so each panel's rotation is set
only by its own land-side attachments -- which are few, noisy (s0^2 ~ 6.5), and
have a short lever arm compared with the wharf's length. The independent fit
produced theta_A = -1.243 deg and theta_B = +0.087 deg: a 1.33 deg RELATIVE
rotation between two panels drafted on one page, by one hand, at one scale.
Propagated along the frontage that is ~350 px (~57 ft) of divergence, which was
mistakenly recorded as an original drafting disagreement in the pier ground.

It is not drafting disagreement. Two panels of one continuous frontage on one
sheet must be mutually consistent to within drafting precision, and the sheet
itself proves it: the ground around Pier 22 / 22nd St is drawn TWICE, once at
the bottom of panel A and once at the top of panel B. Those duplicated features
(shed corners, track frogs, slip and bulkhead corners) are direct observations
of the panels' RELATIVE geometry, and they are far stronger than the land-side
attachments for that purpose.

MODEL
-----
Eight unknowns: (a,b,tx,ty) per panel, on each panel's centred frame (centres =
panel polygon centroids, as in fit_sheet5.py).

Observations:
  1. BLOCK ATTACHMENT rows, reused verbatim from fit_sheet5.build_rows(), which
     tie each panel to the frozen block sheets (7, 9, 11). These fix WHERE the
     wharf sits against the land and carry their measured sigmas.
  2. CROSS-PANEL rows, new: for each duplicated feature with panel-A coordinate
     pA and panel-B coordinate pB,
         T_A(pA) - T_B(pB) = 0      (both components)
     weighted by the measurement sigma of the correspondence. These fix the
     panels' geometry RELATIVE to each other.

Robust IRLS (Huber) as in the block solver; every down-weight logged. Full 8x8
covariance is reported, plus the marginal relative rotation between panels --
the quantity the independent fit could not constrain at all.

The archival scan is never modified; this reads control JSON and writes only
into 40_solve/output_sheet5_joint/.
"""

from __future__ import annotations

import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import fit_sheet5 as F5  # noqa: E402  (reuse its parsing and row builders)

ROOT = os.path.dirname(HERE)
OUT_DIR = os.path.join(HERE, "output_sheet5_joint")
XPANEL_V2 = os.path.join(ROOT, "30_controls", "verified", "cross_panel_05_v2.json")
XPANEL_V1 = os.path.join(ROOT, "30_controls", "verified", "cross_panel_05.json")
HUBER_DELTA = 2.5
IRLS_ITERATIONS = 12
PANEL_IDS = ("5A", "5B")
IDX = {"5A": 0, "5B": 4}


def load_cross_panel(log):
    """Correspondences: [(pA, pB, sigma, label)]. Prefers the v2 measurement."""
    out = []
    path = XPANEL_V2 if os.path.exists(XPANEL_V2) else XPANEL_V1
    if not os.path.exists(path):
        log.append("[xpanel] no cross-panel file found; panels stay uncoupled")
        return out, None
    with open(path) as fh:
        data = json.load(fh)
    items = data.get("correspondences") or data.get("point_pairs") or data.get("pairs") or []
    for i, it in enumerate(items):
        a = it.get("A") or it.get("a") or it.get("panel_A") or it.get("5A")
        b = it.get("B") or it.get("b") or it.get("panel_B") or it.get("5B")
        if a is None or b is None:
            continue
        a = [float(a[0]), float(a[1])]
        b = [float(b[0]), float(b[1])]
        sig = float(it.get("sigma_px", it.get("sigma", 4.0)) or 4.0)
        lab = it.get("feature") or it.get("label") or f"pair{i+1}"
        out.append((a, b, max(sig, 1.0), lab))
    log.append(f"[xpanel] {len(out)} correspondences from {os.path.basename(path)}")
    return out, path


def build_joint(fit_atts, block_T, panels, xpairs, log):
    """Design matrix (n x 8), targets, sigmas, and row provenance."""
    rows_J, rows_t, rows_s, prov = [], [], [], []

    # 1. block attachment rows (per panel, reused from fit_sheet5)
    for pid in PANEL_IDS:
        c = panels[pid]["center"]
        col = IDX[pid]
        for att in fit_atts:
            if att["panel"] != pid:
                continue
            for r in F5.build_rows(att, block_T, c, log):
                J = np.zeros(8)
                J[col:col + 4] = r["coeff"]
                rows_J.append(J)
                rows_t.append(r["target"])
                rows_s.append(F5._row_sigmas([r], F5.PANEL_SCALE_INIT)[0])
                prov.append({"kind": "block", "panel": pid,
                             "seam": att["seam"], "anchor": r.get("anchor", "")})

    # 2. cross-panel rows: T_A(pA) - T_B(pB) = 0, per component
    cA, cB = panels["5A"]["center"], panels["5B"]["center"]
    for (pA, pB, sig, lab) in xpairs:
        qA = np.array([pA[0] - cA[0], pA[1] - cA[1]])
        qB = np.array([pB[0] - cB[0], pB[1] - cB[1]])
        for u in ((1.0, 0.0), (0.0, 1.0)):
            u = np.array(u)
            J = np.zeros(8)
            J[0:4] = F5.row_coeffs(u, qA)
            J[4:8] = -F5.row_coeffs(u, qB)
            rows_J.append(J)
            rows_t.append(0.0)
            rows_s.append(sig)
            prov.append({"kind": "xpanel", "feature": lab,
                         "axis": "x" if u[0] else "y"})
    return np.array(rows_J), np.array(rows_t), np.array(rows_s), prov


def solve_joint(J, tgt, sig, prov, log):
    m = len(tgt)
    inv = 1.0 / sig
    wh = np.ones(m)
    x = np.zeros(8)
    for _ in range(IRLS_ITERATIONS):
        sw = inv * np.sqrt(wh)
        x, *_ = np.linalg.lstsq(J * sw[:, None], tgt * sw, rcond=None)
        rn = (J @ x - tgt) * inv
        wh = np.where(np.abs(rn) > HUBER_DELTA,
                      HUBER_DELTA / np.maximum(np.abs(rn), 1e-12), 1.0)

    res = J @ x - tgt
    rn = res * inv
    Jw = J * (inv * np.sqrt(wh))[:, None]
    N = Jw.T @ Jw
    rank = int(np.linalg.matrix_rank(N))
    Ninv = np.linalg.pinv(N) if rank < 8 else np.linalg.inv(N)
    dof = max(m - rank, 1)
    s0_sq = float(np.sum(wh * rn ** 2) / dof)
    cov = Ninv * s0_sq

    for i, w in enumerate(wh):
        if w < 0.999:
            p = prov[i]
            log.append(f"[huber] {p.get('kind')} {p.get('feature', p.get('anchor',''))} "
                       f"{p.get('axis','')}: resid {res[i]:+.1f} px, w={w:.3f}")
    return x, cov, res, wh, s0_sq, rank, dof


def panel_params(x, cov, pid, center):
    i = IDX[pid]
    a, b, tx, ty = x[i:i + 4]
    s = math.hypot(a, b)
    th = math.degrees(math.atan2(b, a))
    # raw (uncentred) translation
    A = np.array([[a, -b], [b, a]])
    raw_t = np.array([tx, ty]) - A @ np.array(center)
    C = cov[i:i + 4, i:i + 4]
    # d(theta)/d(a,b) = (-b, a)/s^2 ; d(s)/d(a,b) = (a, b)/s
    g_th = np.array([-b, a, 0, 0]) / (s * s)
    g_s = np.array([a, b, 0, 0]) / s
    return {
        "a": float(a), "b": float(b), "tx": float(tx), "ty": float(ty),
        "s": float(s), "theta_deg": float(th),
        "theta_std_mrad": float(math.sqrt(max(g_th @ C @ g_th, 0)) * 1000.0),
        "s_std": float(math.sqrt(max(g_s @ C @ g_s, 0))),
        "center": [float(center[0]), float(center[1])],
        "raw": {"a": float(a), "b": float(b),
                "tx": float(raw_t[0]), "ty": float(raw_t[1])},
    }


def main():
    log = []
    os.makedirs(OUT_DIR, exist_ok=True)
    block_T, block_meta = F5.load_block_transforms(F5.DEFAULT_TRANSFORMS)
    panels, divider = F5.load_regions(F5.DEFAULT_REGIONS)
    atts = F5.discover_attachments(F5.DEFAULT_CONTROLS, log)

    fit_atts = []
    for att in atts:
        F5.verify_points_in_panel(att, panels, log)
        F5.verify_axes(att, log)
        if (not att["context_only"]
                and any(a["status"] == "ACCEPTED" for a in att["anchors"])
                and att["block"] in block_T):
            fit_atts.append(att)

    xpairs, xpath = load_cross_panel(log)
    if not xpairs:
        raise SystemExit("joint fit requires cross-panel correspondences")

    J, tgt, sig, prov = build_joint(fit_atts, block_T, panels, xpairs, log)
    n_blk = sum(1 for p in prov if p["kind"] == "block")
    n_xp = sum(1 for p in prov if p["kind"] == "xpanel")
    print(f"observations: {n_blk} block-attachment + {n_xp} cross-panel = {len(tgt)}")

    x, cov, res, wh, s0_sq, rank, dof = solve_joint(J, tgt, sig, prov, log)

    sol = {pid: panel_params(x, cov, pid, panels[pid]["center"]) for pid in PANEL_IDS}
    rel = sol["5B"]["theta_deg"] - sol["5A"]["theta_deg"]

    # residual summaries by class
    def rms_of(kind):
        v = [res[i] for i, p in enumerate(prov) if p["kind"] == kind]
        return float(np.sqrt(np.mean(np.square(v)))) if v else None

    payload = {
        "model": "joint two-panel similarity, coupled by duplicated drafted ground",
        "convention": {
            "centered": "p_mosaic = [[a,-b],[b,a]] @ (p_sheet5_raw - center) + (tx,ty)",
            "raw": "p_mosaic = [[a,-b],[b,a]] @ p_sheet5_raw + (raw.tx, raw.ty)",
            "centers": {p: sol[p]["center"] for p in PANEL_IDS},
        },
        "block_source": block_meta,
        "cross_panel_source": xpath,
        "panels": sol,
        "relative_rotation_deg": float(rel),
        "diagnostics": {
            "n_block_rows": n_blk, "n_xpanel_rows": n_xp,
            "rank": rank, "dof": dof, "s0_sq": s0_sq,
            "rms_block_px": rms_of("block"), "rms_xpanel_px": rms_of("xpanel"),
            "downweighted": int(np.sum(wh < 0.999)),
        },
        "log": log,
    }
    with open(os.path.join(OUT_DIR, "transforms_sheet5_joint.json"), "w") as fh:
        json.dump(payload, fh, indent=1)

    print(f"panel 5A: s={sol['5A']['s']:.4f} theta={sol['5A']['theta_deg']:+.4f} deg "
          f"(+-{sol['5A']['theta_std_mrad']:.2f} mrad)")
    print(f"panel 5B: s={sol['5B']['s']:.4f} theta={sol['5B']['theta_deg']:+.4f} deg "
          f"(+-{sol['5B']['theta_std_mrad']:.2f} mrad)")
    print(f"RELATIVE rotation B-A: {rel:+.4f} deg   (independent fit gave +1.3300)")
    print(f"residual RMS: block {rms_of('block'):.1f} px, cross-panel "
          f"{rms_of('xpanel'):.1f} px; s0^2={s0_sq:.2f}; "
          f"{int(np.sum(wh < 0.999))} down-weighted")
    print(f"wrote {OUT_DIR}/transforms_sheet5_joint.json")


if __name__ == "__main__":
    main()
