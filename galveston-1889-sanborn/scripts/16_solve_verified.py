#!/usr/bin/env python3
"""16 -- Solve the sheet network from the verified, uncertainty-weighted control.

WHAT IS DIFFERENT FROM SCRIPT 07
    07 solved from automatically detected street-band intersections, whose
    measurement error was later shown to be several percent of a block -- large
    enough that the residuals it reported were dominated by the detector, not
    by the geometry.  This script solves from `gcps/tiepoints_verified.csv`
    only: features identified SEMANTICALLY from printed evidence and then
    measured by hand, each carrying an honest sigma.

WEIGHTING
    Every observation enters with weight 1/sigma^2, so the quantity minimised
    is the sum of squared NORMALISED residuals (r/sigma).  Two numbers are
    therefore reported for every seam and both matter:

      raw residual        how far apart the two sheets place the same feature,
                          in original scan pixels -- the user-facing number,
                          and the one the acceptance targets are written in;
      normalised residual raw/sigma -- whether the disagreement is larger than
                          the observer said it should be.  A 6 px raw residual
                          on a hydrant symbol placed by eye at +/-20 px is a
                          perfectly good fit; the same 6 px on a lettered block
                          corner measured at +/-3 px is a real defect.

    Robust reweighting (Huber) also runs on the normalised residual, so an
    honestly-loose observation is never mistaken for an outlier.

Outputs
    working/transforms_verified.json
    output/qc/seam_residuals_verified.csv
    output/qc/transform_summary.csv
    output/qc/solve_verified.json
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import pathlib
import sys
from collections import defaultdict

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from sanborn import geometry as G
from sanborn import qc as QC
from sanborn.config import load_config, paths, setup_logging, utcnow

ROOT = pathlib.Path(__file__).resolve().parent.parent

# An observation whose own declared sigma exceeds the seam max gate (15 px)
# cannot inform that gate. Graded control must be at least as precise as the
# threshold it is being judged against.
LOOSE_SIGMA_PX = 15.0


def load_verified(path: pathlib.Path):
    """Pair the two rows of every point_id into a TiePoint."""
    by_id: dict[str, list[dict]] = defaultdict(list)
    with path.open(newline="") as fh:
        for row in csv.DictReader(fh):
            if row.get("accepted", "true").lower() not in ("true", "1", "yes"):
                continue
            by_id[row["point_id"]].append(row)

    ties, skipped, meta = [], [], {}
    for pid, rows in sorted(by_id.items()):
        if len(rows) != 2:
            skipped.append((pid, f"{len(rows)} rows, expected 2"))
            continue
        a, b = rows
        sigma = max(float(a["uncertainty_px"] or 8.0),
                    float(b["uncertainty_px"] or 8.0))
        sigma = max(sigma, 0.5)                     # no observation is perfect
        sx = max(float(a.get("sigma_x_px") or sigma), 0.5)
        sy = max(float(a.get("sigma_y_px") or sigma), 0.5)
        ties.append(G.TiePoint(
            a=a["region"], pa=(float(a["src_x"]), float(a["src_y"])),
            b=b["region"], pb=(float(b["src_x"]), float(b["src_y"])),
            weight=1.0 / (sigma * sigma), label=pid,
            weight_xy=(1.0 / (sx * sx), 1.0 / (sy * sy))))
        # TiePoint uses __slots__, so per-point provenance rides alongside.
        meta[pid] = {"sigma": sigma, "sigma_x": sx, "sigma_y": sy,
                     "feature": a.get("feature", ""),
                     "confidence": a.get("confidence", ""),
                     "category": a.get("category", ""),
                     "control_class": a.get("control_class", "geometric")}
    return ties, skipped, meta


def connected_components(regions, ties):
    parent = {r: r for r in regions}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for t in ties:
        if t.a in parent and t.b in parent:
            ra, rb = find(t.a), find(t.b)
            if ra != rb:
                parent[ra] = rb
    groups: dict[str, list[str]] = defaultdict(list)
    for r in regions:
        groups[find(r)].append(r)
    return sorted(groups.values(), key=len, reverse=True)


def seam_table(residuals, meta):
    per: dict[tuple, list[dict]] = defaultdict(list)
    for r in residuals:
        if r["kind"] != "tie":
            continue
        key = tuple(sorted((r["sheet_a"], r["sheet_b"])))
        m = meta.get(r["label"], {})
        per[key].append({
            "label": r["label"], "raw": r["residual"], "norm": r["normalized"],
            "sigma": m.get("sigma", float("nan")),
            "confidence": m.get("confidence", ""), "feature": m.get("feature", ""),
            "category": m.get("category", ""),
            "control_class": m.get("control_class", "geometric"),
        })
    out = []
    for key, items in sorted(per.items()):
        # Grade on PRECISE GEOMETRIC control only.
        #
        # Two kinds of observation are reported but never graded:
        #
        #   symbol  fire plugs, hydrants, valve discs -- placed by eye by the
        #           draughtsman, and the same plug is drawn up to 46 px apart
        #           on two plates of one edition;
        #   loose   anything, of any category, whose observer declared a sigma
        #           larger than the grading gate itself. A water-main tee
        #           offered at +/-45 px because sheet 8 runs the 22nd St main
        #           143 px south of the kerb where sheet 10 runs it 99 px is a
        #           semantic confirmation of WHICH crossing it is, not a claim
        #           about position. Letting it decide a 15 px max gate would be
        #           grading a measurement against a precision it never asserted.
        #
        # Both stay in the solve at their honest sigma, where 1/sigma^2 makes
        # them nearly weightless.
        geo = [i for i in items
               if i["control_class"] == "geometric" and i["sigma"] <= LOOSE_SIGMA_PX]
        sym = [i for i in items
               if i["control_class"] == "symbol" or i["sigma"] > LOOSE_SIGMA_PX]
        if not geo:
            continue
        raw = np.array([i["raw"] for i in geo])
        nrm = np.array([i["norm"] for i in geo])
        entry = {
            "region_a": key[0], "region_b": key[1], "n": len(geo),
            "n_symbol": len(sym),
            "raw_median": float(np.median(raw)), "raw_rms": float(np.sqrt(np.mean(raw ** 2))),
            "raw_p95": float(np.percentile(raw, 95)), "raw_max": float(raw.max()),
            "norm_median": float(np.median(nrm)), "norm_max": float(nrm.max()),
            "worst_point": max(geo, key=lambda i: i["norm"]),
            "points": items,
        }
        if sym:
            sr = np.array([i["raw"] for i in sym])
            entry["symbol_scatter_median_px"] = float(np.median(sr))
            entry["symbol_scatter_max_px"] = float(sr.max())
        out.append(entry)
    return out


def _sim_block(pt, sign):
    x, y = pt
    return sign * np.array([[x, -y, 1.0, 0.0], [y, x, 0.0, 1.0]])


def normal_matrix(regions, ties, anchor, kind, residuals):
    """Inverse normal matrix and unit-weight variance of a similarity solve.

    Shared by the per-region formal errors and by the leave-one-seam-out test,
    which needs the FULL inverse rather than per-region blocks: the two sheets
    of a predicted seam are strongly correlated through the rest of the
    network, and ignoring that cross-covariance would overstate the predicted
    uncertainty considerably.
    """
    if kind != "similarity":
        return None
    free = [r for r in regions if r != anchor]
    if not free:
        return None
    idx = {r: i * 4 for i, r in enumerate(free)}
    ncol = 4 * len(free)
    rows, wts = [], []
    for t in ties:
        row = np.zeros((2, ncol))
        if t.a in idx:
            row[:, idx[t.a]:idx[t.a] + 4] += _sim_block(t.pa, +1)
        if t.b in idx:
            row[:, idx[t.b]:idx[t.b] + 4] += _sim_block(t.pb, -1)
        rows.append(row)
        wts.append((t.wx, t.wy))
    if not rows:
        return None
    A = np.vstack(rows)
    sw = np.sqrt(np.asarray(wts, float).reshape(-1))
    Aw = A * sw[:, None]
    try:
        Ninv = np.linalg.inv(Aw.T @ Aw)
    except np.linalg.LinAlgError:
        return None
    ssr = sum(r["normalized"] ** 2 for r in residuals if r["kind"] == "tie")
    redundancy = max(1, 2 * len(ties) - ncol)
    return {"Ninv": Ninv, "idx": idx, "ncol": ncol,
            "sigma0_sq": ssr / redundancy}


def predicted_sigma(nm, region_a, pa, region_b, pb):
    """1-sigma radial uncertainty of T_a(pa) - T_b(pb) under a given solve.

    A similarity is linear in its parameters, so the displacement is M.theta
    and its covariance is M.Cov(theta).M^T exactly -- no linearisation error.
    """
    if nm is None:
        return None
    idx, ncol = nm["idx"], nm["ncol"]
    M = np.zeros((2, ncol))
    if region_a in idx:
        M[:, idx[region_a]:idx[region_a] + 4] += _sim_block(pa, +1)
    if region_b in idx:
        M[:, idx[region_b]:idx[region_b] + 4] += _sim_block(pb, -1)
    C = nm["sigma0_sq"] * (M @ nm["Ninv"] @ M.T)
    return float(np.sqrt(max(0.0, np.trace(C))))


def leave_one_seam_out(regions, ties, anchor, kind, huber, meta):
    """Drop a whole seam's control, re-solve, and see where that seam lands.

    K-fold over individual POINTS is nearly useless here: with 6-16 points on
    a seam, removing a fifth of them leaves the seam itself fully constrained,
    so the held-out points are predicted by their own neighbours rather than
    by the rest of the network.

    Dropping an ENTIRE seam is the real test.  That seam's geometry then has
    to be predicted by going the long way round the network, so the number it
    produces is a genuine loop closure -- unlike composing transforms around a
    cycle of a global solve, which returns 0.000 px by construction because
    every sheet has exactly one absolute transform.

    It also probes the one systematic this control set cannot see from the
    inside.  Sheets abutting along an avenue share NO inked ground point: each
    draws only its own frontage, and the tie is constructed by stepping half
    the printed 70 ft width inward.  A wrong width biases that seam's
    across-seam offset by width_error x px_per_ft, identically for every point
    on it, so it cannot show up in that seam's own residuals.  Predicting the
    seam from elsewhere is what exposes it.
    """
    seams = sorted({tuple(sorted((t.a, t.b))) for t in ties})
    out = []
    for a, b in seams:
        kept = [t for t in ties if tuple(sorted((t.a, t.b))) != (a, b)]
        held = [t for t in ties if tuple(sorted((t.a, t.b))) == (a, b)
                and meta.get(t.label, {}).get("control_class") != "symbol"]
        if not held:
            continue
        reach = connected_components(regions, kept)
        if len(reach) > 1:
            out.append({"seam": f"{a}|{b}", "n_held": len(held),
                        "status": "DISCONNECTS",
                        "note": "the network falls apart without this seam -- "
                                "it is a bridge, and nothing independent "
                                "predicts it"})
            continue
        try:
            res = G.adjust(regions, kept, None, kind=kind, anchor_sheet=anchor,
                           robust=True, huber_delta=huber, iterations=30)
        except Exception as exc:
            out.append({"seam": f"{a}|{b}", "n_held": len(held),
                        "status": "ERROR", "note": str(exc)})
            continue
        T2 = res["transforms"]
        nm2 = normal_matrix(regions, kept, anchor, kind, res["residuals"])
        sig = [predicted_sigma(nm2, t.a, t.pa, t.b, t.pb) for t in held]
        sig = [v for v in sig if v is not None]
        d = np.array([G.apply(T2[t.a], [t.pa])[0] - G.apply(T2[t.b], [t.pb])[0]
                      for t in held])
        r = np.hypot(d[:, 0], d[:, 1])
        # Split the prediction error into the part shared by every point on
        # the seam (a rigid offset, which is what a bad avenue width looks
        # like) and the part that varies point to point.
        bias = d.mean(axis=0)
        scatter = d - bias
        out.append({
            "seam": f"{a}|{b}", "n_held": len(held), "status": "predicted",
            "median_px": float(np.median(r)), "max_px": float(r.max()),
            "systematic_offset_px": float(np.hypot(*bias)),
            "systematic_dx_px": float(bias[0]), "systematic_dy_px": float(bias[1]),
            "residual_scatter_px": float(np.sqrt((scatter ** 2).sum(axis=1).mean())),
            "predicted_sigma_px": float(np.mean(sig)) if sig else None,
            "sigma_ratio": (float(np.median(r) / np.mean(sig))
                            if sig and np.mean(sig) > 0 else None),
        })
    return out


def parameter_covariance(regions, ties, anchor, kind, T, residuals):
    """1-sigma formal errors on each free region's scale and rotation.

    Rebuilds the weighted design matrix of the converged solution, inverts the
    normal matrix, scales it by the unit-weight variance (weighted SSR over
    redundancy), then propagates from the parameterisation (a, b, tx, ty) to
    the quantities a reader cares about:

        s     = hypot(a, b)          ds/da =  a/s     ds/db =  b/s
        theta = atan2(b, a)          dth/da = -b/s^2  dth/db =  a/s^2

    Returns {} for anything but a similarity, where that algebra applies.
    """
    nm = normal_matrix(regions, ties, anchor, kind, residuals)
    if nm is None:
        return {}
    Ninv, idx, sigma0_sq = nm["Ninv"], nm["idx"], nm["sigma0_sq"]

    out = {}
    for r in regions:
        if r == anchor:
            out[r] = {"sigma_scale": 0.0, "sigma_rotation_deg": 0.0}
            continue
        o = idx[r]
        C = sigma0_sq * Ninv[o:o + 2, o:o + 2]       # covariance of (a, b)
        a, b = T[r][0, 0], T[r][1, 0]
        s2 = a * a + b * b
        s = math.sqrt(s2)
        Js = np.array([a / s, b / s])
        Jt = np.array([-b / s2, a / s2])
        out[r] = {
            "sigma_scale": float(math.sqrt(max(0.0, Js @ C @ Js))),
            "sigma_rotation_deg": float(math.degrees(math.sqrt(max(0.0, Jt @ C @ Jt)))),
        }
    return out


def grade(raw_median, raw_max, norm_median):
    """Acceptance grade. Both the absolute and the normalised view must agree."""
    if raw_median <= 3.0 and raw_max <= 12.0 and norm_median <= 1.5:
        return "PASS", "median <=3px (excellent), max <=12px, within stated uncertainty"
    if raw_median <= 5.0 and raw_max <= 15.0 and norm_median <= 2.0:
        return "PASS", "median <=5px (good), max <=15px, within stated uncertainty"
    reasons = []
    if raw_median > 10.0:
        reasons.append(f"median {raw_median:.1f}px above 10px")
    elif raw_median > 5.0:
        reasons.append(f"median {raw_median:.1f}px in the 5-10px review band")
    if raw_max > 15.0:
        reasons.append(f"max {raw_max:.1f}px exceeds 15px")
    if norm_median > 2.0:
        reasons.append(f"median {norm_median:.1f}x the stated uncertainty")
    verdict = "FAIL" if (raw_median > 10.0 or raw_max > 25.0) else "REVIEW"
    return verdict, "; ".join(reasons) or "outside target"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", default="galveston1889")
    ap.add_argument("--kind", default="similarity")
    ap.add_argument("--huber", type=float, default=2.5,
                    help="Huber delta in NORMALISED units (sigmas)")
    ap.add_argument("--allow-partial", action="store_true",
                    help="solve the largest connected component instead of failing")
    ap.add_argument("--loso", action="store_true",
                    help="leave-one-seam-out prediction test (the honest loop closure)")
    ap.add_argument("--publish", action="store_true",
                    help="also write working/transforms.json and gcps/residuals.json, "
                         "i.e. ACCEPT this solve as the one the rest of the "
                         "pipeline (warp, mosaic, seam matrix) will use")
    args = ap.parse_args()

    cfg = load_config(args.profile)
    p = paths().ensure()
    log = setup_logging("16_solve_verified")

    regions = [r["id"] for s in cfg["sheets"] for r in s["regions"] if r.get("keep")]
    anchor = cfg["geometry"]["anchor_region"]

    csv_path = p.gcps / "tiepoints_verified.csv"
    if not csv_path.exists():
        log.error("no %s -- run 15_ingest_manual_control.py first", csv_path)
        return 2
    ties, skipped, meta = load_verified(csv_path)
    for pid, why in skipped:
        log.warning("skipped %s: %s", pid, why)
    if not ties:
        log.error("no usable verified tie points")
        return 2

    comps = connected_components(regions, ties)
    if len(comps) > 1:
        log.error("control network is NOT connected: %s",
                  " | ".join("+".join(sorted(c)) for c in comps))
        if not args.allow_partial:
            log.error("every region must be reachable from the anchor before a "
                      "joint solve means anything -- rerun with --allow-partial "
                      "only to inspect an intermediate state")
            return 3
        solved = [c for c in comps if anchor in c][0]
        log.warning("solving the anchor's component only: %s", "+".join(sorted(solved)))
        regions = solved
        ties = [t for t in ties if t.a in solved and t.b in solved]

    log.info("%d verified correspondences over %d regions, anchor %s",
             len(ties), len(regions), anchor)

    # ---- gates ----------------------------------------------------------
    rank = G.design_rank_report(regions, ties, None, kind=args.kind,
                                anchor_sheet=anchor)
    det = G.check_determinacy(regions, ties, None, kind=args.kind)
    log.info("rank check (%s): ok=%s nullity=%s", args.kind, rank["ok"],
             rank.get("nullity"))
    if not rank["ok"]:
        log.error("rank deficient: %s", rank.get("note"))
        return 4
    if det["underdetermined"]:
        log.error("underdetermined regions: %s", det["underdetermined"])
        return 4

    # ---- solve ----------------------------------------------------------
    fit = G.adjust(regions, ties, None, kind=args.kind, anchor_sheet=anchor,
                   robust=True, huber_delta=args.huber, iterations=30)
    T = fit["transforms"]

    seams = seam_table(fit["residuals"], meta)
    for s in seams:
        s["verdict"], s["why"] = grade(s["raw_median"], s["raw_max"], s["norm_median"])

    # ---- how well is each parameter actually DETERMINED? ----------------
    # Residuals say how well the solution fits. They do not say whether the
    # data could have pinned the parameter down at all. Seams where two sheets
    # abut along one street give collinear control, and a single such seam
    # constrains rotation only through the spread of points ALONG the line --
    # on S8|S29 the along-line family says -0.81 deg and the crossing street
    # lines say -0.29 deg. What rescues it is the joint solve: a region in
    # three seams facing different directions is determined even where no one
    # seam determines it. This block measures that, rather than asserting it.
    cov = parameter_covariance(regions, ties, anchor, args.kind, T, fit["residuals"])

    # ---- per-region geometry, and is it physically possible -------------
    summary = []
    for r in sorted(T):
        d = G.decompose_affine(T[r])
        flags = G.plausibility_flags(T[r])
        c = cov.get(r, {})
        summary.append({"region": r, "anchor": r == anchor,
                        "scale": round(d["scale_x"], 5),
                        "sigma_scale_pct": ("" if c.get("sigma_scale") is None
                                            else round(100.0 * c["sigma_scale"], 4)),
                        "rotation_deg": round(d["rotation_deg"], 4),
                        "sigma_rotation_deg": ("" if c.get("sigma_rotation_deg") is None
                                               else round(c["sigma_rotation_deg"], 4)),
                        "shear_deg": round(d["shear_deg"], 4),
                        "anisotropy": round(d["anisotropy"], 5),
                        "tx": round(float(T[r][0, 2]), 2),
                        "ty": round(float(T[r][1, 2]), 2),
                        "plausibility": ",".join(flags) if flags else "ok"})
    scales = [s["scale"] for s in summary]
    rots = [s["rotation_deg"] for s in summary]
    spread = {"scale_spread_pct": 100.0 * (max(scales) - min(scales)) / float(np.mean(scales)),
              "rotation_spread_deg": max(rots) - min(rots)}

    # ---- held-out error -------------------------------------------------
    cv = QC.crossvalidate(regions, ties, None, kind=args.kind, folds=5,
                          anchor_sheet=anchor, robust=True, huber_delta=args.huber)
    if cv.get("detail"):
        nrm = np.array([d["residual"] * math.sqrt(d["weight"]) for d in cv["detail"]])
        cv["held_out_normalised"] = {"median": float(np.median(nrm)),
                                     "max": float(nrm.max())}
        cv.pop("detail")

    loso = leave_one_seam_out(regions, ties, anchor, args.kind, args.huber,
                              meta) if args.loso else []

    # ---- write ----------------------------------------------------------
    (p.working / "transforms_verified.json").write_text(json.dumps({
        "profile": args.profile, "kind": args.kind, "anchor_region": anchor,
        "generated": utcnow(), "source": "gcps/tiepoints_verified.csv",
        "transforms": {r: T[r].tolist() for r in sorted(T)}}, indent=1))

    qcdir = p.output / "qc"
    qcdir.mkdir(parents=True, exist_ok=True)
    with (qcdir / "seam_residuals_verified.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["region_a", "region_b", "n_geometric", "raw_median_px",
                    "raw_rms_px", "raw_p95_px", "raw_max_px", "norm_median",
                    "norm_max", "verdict", "why", "worst_point", "worst_feature",
                    "n_symbol", "symbol_scatter_median_px", "symbol_scatter_max_px"])
        for s in seams:
            w.writerow([s["region_a"], s["region_b"], s["n"],
                        round(s["raw_median"], 2), round(s["raw_rms"], 2),
                        round(s["raw_p95"], 2), round(s["raw_max"], 2),
                        round(s["norm_median"], 2), round(s["norm_max"], 2),
                        s["verdict"], s["why"], s["worst_point"]["label"],
                        s["worst_point"]["feature"][:80], s["n_symbol"],
                        round(s.get("symbol_scatter_median_px", float("nan")), 2)
                        if s["n_symbol"] else "",
                        round(s.get("symbol_scatter_max_px", float("nan")), 2)
                        if s["n_symbol"] else ""])
    with (qcdir / "transform_summary.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(summary[0].keys()))
        w.writeheader()
        w.writerows(summary)

    keep = [r for r in fit["residuals"]
            if meta.get(r["label"], {}).get("control_class", "geometric") == "geometric"
            and (meta.get(r["label"], {}).get("sigma") or 99) <= LOOSE_SIGMA_PX]
    raw = np.array([r["residual"] for r in keep])
    nrm = np.array([r["normalized"] for r in keep])
    overall = {"n": len(raw), "raw_median": float(np.median(raw)),
               "raw_rms": float(np.sqrt(np.mean(raw ** 2))),
               "raw_p95": float(np.percentile(raw, 95)), "raw_max": float(raw.max()),
               "norm_median": float(np.median(nrm)), "norm_max": float(nrm.max())}
    (qcdir / "solve_verified.json").write_text(json.dumps(
        {"generated": utcnow(), "kind": args.kind, "anchor": anchor,
         "regions": sorted(T), "overall": overall, "spread": spread,
         "rank": rank, "crossval": cv, "leave_one_seam_out": loso,
         "transforms_summary": summary,
         "seams": [{k: v for k, v in s.items() if k != "points"} for s in seams]},
        indent=1, default=str))

    if args.publish:
        if len(comps) > 1:
            log.error("refusing to publish a partial solve: %d disconnected "
                      "components", len(comps))
            return 5
        (p.working / "transforms.json").write_text(json.dumps({
            "profile": args.profile, "kind": args.kind, "anchor_region": anchor,
            "generated": utcnow(),
            "source": "gcps/tiepoints_verified.csv (semantic identification, "
                      "uncertainty-weighted)",
            "transforms": {r: T[r].tolist() for r in sorted(T)}}, indent=1))
        (p.gcps / "residuals.json").write_text(json.dumps({
            "generated": utcnow(), "kind": args.kind, "anchor": anchor,
            "source": "16_solve_verified.py",
            "residuals": [dict(r, control_class=meta.get(r["label"], {})
                               .get("control_class", "geometric"),
                               sigma=meta.get(r["label"], {}).get("sigma"))
                          for r in fit["residuals"]]}, indent=1))
        log.info("published working/transforms.json and gcps/residuals.json")

    # ---- report ---------------------------------------------------------
    n_sym = sum(1 for t in ties
                if meta[t.label]["control_class"] == "symbol"
                or meta[t.label]["sigma"] > LOOSE_SIGMA_PX)
    print(f"\n{args.kind} solve, anchor {anchor}, {len(ties)} verified "
          f"correspondences ({len(ties) - n_sym} graded + {n_sym} ungraded), "
          f"{len(regions)} regions")
    print(f"  (graded on geometric control with sigma <= {LOOSE_SIGMA_PX:.0f} px; "
          "symbols and loose points are reported as scatter)")
    print(f"  overall raw   median {overall['raw_median']:6.2f}px  "
          f"p95 {overall['raw_p95']:6.2f}px  max {overall['raw_max']:6.2f}px")
    print(f"  overall norm  median {overall['norm_median']:6.2f}s   "
          f"max {overall['norm_max']:6.2f}s")
    ho = cv.get("held_out") or {}
    if ho:
        print(f"  held-out (5-fold) median {ho.get('median', float('nan')):.2f}px")
    print(f"  scale spread {spread['scale_spread_pct']:.2f}%   "
          f"rotation spread {spread['rotation_spread_deg']:.2f} deg")
    print(f"\n  {'seam':<20} {'n':>3} {'med':>7} {'max':>7} {'n/sig':>6}  verdict")
    for s in seams:
        tail = f"  ({s['why']})" if s["verdict"] != "PASS" else ""
        if s["n_symbol"]:
            tail += (f"   [+{s['n_symbol']} ungraded, scatter "
                     f"{s['symbol_scatter_median_px']:.0f}/"
                     f"{s['symbol_scatter_max_px']:.0f}px]")
        print(f"  {s['region_a'] + ' | ' + s['region_b']:<20} {s['n']:>3} "
              f"{s['raw_median']:>6.2f}p {s['raw_max']:>6.2f}p "
              f"{s['norm_median']:>5.2f}s  {s['verdict']}" + tail)
    if loso:
        print(f"\n  leave-one-seam-out prediction (the seam is removed entirely and "
              f"predicted\n  by the rest of the network -- a real loop closure):")
        print(f"  {'seam':<20} {'n':>3} {'med':>8} {'max':>8} {'bias':>8} "
              f"{'scatter':>8} {'pred 1sig':>10} {'obs/pred':>9}")
        for e in loso:
            if e["status"] != "predicted":
                print(f"  {e['seam']:<20} {e['n_held']:>3} {e['status']:>8}"
                      f"   {e.get('note', '')[:60]}")
                continue
            ps = (f"{e['predicted_sigma_px']:>9.2f}p"
                  if e.get("predicted_sigma_px") else f"{'-':>10}")
            rt = (f"{e['sigma_ratio']:>9.2f}" if e.get("sigma_ratio")
                  else f"{'-':>9}")
            print(f"  {e['seam']:<20} {e['n_held']:>3} {e['median_px']:>7.2f}p "
                  f"{e['max_px']:>7.2f}p {e['systematic_offset_px']:>7.2f}p "
                  f"{e['residual_scatter_px']:>7.2f}p {ps} {rt}")
        print("  bias    = offset shared by every point on the seam -- what a wrong "
              "printed\n            avenue width would look like")
        print("  scatter = the part that varies point to point")
        print("  obs/pred= misclosure over what the REDUCED network could predict. "
              "Around 1\n            means the network is self-consistent and merely "
              "thin; well above 2\n            means a systematic the control cannot "
              "see from the inside.")

    print(f"\n  {'region':<10} {'scale':>9} {'+/-%':>7} {'rot deg':>9} {'+/-deg':>8} "
          f"{'plausible':>10}")
    for s in summary:
        ss = f"{s['sigma_scale_pct']:>7.3f}" if s["sigma_scale_pct"] != "" else f"{'-':>7}"
        sr = f"{s['sigma_rotation_deg']:>8.3f}" if s["sigma_rotation_deg"] != "" else f"{'-':>8}"
        print(f"  {s['region']:<10} {s['scale']:>9.5f} {ss} {s['rotation_deg']:>9.4f} "
              f"{sr} {s['plausibility']:>10}" + ("   [anchor]" if s["anchor"] else ""))
    print("  (+/- are 1-sigma formal errors from the normal equations, scaled by "
          "the unit-weight variance; they say whether the DATA could pin the "
          "parameter down, which residuals cannot)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
