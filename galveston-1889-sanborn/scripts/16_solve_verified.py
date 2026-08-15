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
        ties.append(G.TiePoint(
            a=a["region"], pa=(float(a["src_x"]), float(a["src_y"])),
            b=b["region"], pb=(float(b["src_x"]), float(b["src_y"])),
            weight=1.0 / (sigma * sigma), label=pid))
        # TiePoint uses __slots__, so per-point provenance rides alongside.
        meta[pid] = {"sigma": sigma, "feature": a.get("feature", ""),
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
        # Grade on GEOMETRIC control only. Symbols (fire plugs, valve discs)
        # were placed by eye by the draftsman and differ between plates of the
        # same edition by up to 45 px; they are reported, never graded.
        geo = [i for i in items if i["control_class"] == "geometric"]
        sym = [i for i in items if i["control_class"] == "symbol"]
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

    # ---- per-region geometry, and is it physically possible -------------
    summary = []
    for r in sorted(T):
        d = G.decompose_affine(T[r])
        flags = G.plausibility_flags(T[r])
        summary.append({"region": r, "anchor": r == anchor,
                        "scale": round(d["scale_x"], 5),
                        "rotation_deg": round(d["rotation_deg"], 4),
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
            if meta.get(r["label"], {}).get("control_class", "geometric") == "geometric"]
    raw = np.array([r["residual"] for r in keep])
    nrm = np.array([r["normalized"] for r in keep])
    overall = {"n": len(raw), "raw_median": float(np.median(raw)),
               "raw_rms": float(np.sqrt(np.mean(raw ** 2))),
               "raw_p95": float(np.percentile(raw, 95)), "raw_max": float(raw.max()),
               "norm_median": float(np.median(nrm)), "norm_max": float(nrm.max())}
    (qcdir / "solve_verified.json").write_text(json.dumps(
        {"generated": utcnow(), "kind": args.kind, "anchor": anchor,
         "regions": sorted(T), "overall": overall, "spread": spread,
         "rank": rank, "crossval": cv, "transforms_summary": summary,
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
                if meta[t.label]["control_class"] == "symbol")
    print(f"\n{args.kind} solve, anchor {anchor}, {len(ties)} verified "
          f"correspondences ({len(ties) - n_sym} geometric + {n_sym} symbol), "
          f"{len(regions)} regions")
    print("  (graded on geometric control only; symbols are drafting scatter)")
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
            tail += (f"   [+{s['n_symbol']} symbol, scatter "
                     f"{s['symbol_scatter_median_px']:.0f}/"
                     f"{s['symbol_scatter_max_px']:.0f}px]")
        print(f"  {s['region_a'] + ' | ' + s['region_b']:<20} {s['n']:>3} "
              f"{s['raw_median']:>6.2f}p {s['raw_max']:>6.2f}p "
              f"{s['norm_median']:>5.2f}s  {s['verdict']}" + tail)
    print(f"\n  {'region':<10} {'scale':>9} {'rot deg':>9} {'plausibility':>14}")
    for s in summary:
        print(f"  {s['region']:<10} {s['scale']:>9.5f} {s['rotation_deg']:>9.4f} "
              f"{s['plausibility']:>14}" + ("   [anchor]" if s["anchor"] else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
