#!/usr/bin/env python3
"""06c -- Find genuine shared features in the overlap between adjoining sheets.

WHY THIS EXISTS
    Control from street/avenue centrelines (06b) ties sheets along the street
    they share. For most of this block that is enough. It is NOT enough for the
    two waterfront sheets: sheets 1 and 2 each print only ONE avenue (Av. A or
    Water E.), so every control point on them lies on a single straight line.
    A similarity is still determined by collinear points, but only just -- the
    sheet is free to pivot about that line in the sense that nothing measures
    how far its wharves and rail yards extend away from it. That is the direct
    cause of the visible waterfront seam and the white wedge beside it.

    The cure is correspondences that are NOT on that line. They exist: a Sanborn
    sheet does not stop dead at its boundary street. Sheet 9 draws the rail
    strip and basin WEST of Avenue A; sheet 1 draws the same ground EAST of it.
    That shared band is real, and it contains railroad tracks, basin edges,
    wharf outlines and warehouse footprints -- exactly the "same physical
    feature on two sheets" the brief ranks above any modern GIS point.

    NOTE the overlap must be computed from the FULL sheet extents, not from the
    rendering masks. Those masks are deliberately cut at the shared centreline
    so the sheets butt without their paper collars colliding, which leaves them
    with no overlap at all. The pixels are still there in the scans.

METHOD (predictive, never blind)
    A city grid is full of near-identical blocks, so an unconstrained matcher
    will confidently pair the wrong corner. Every match here is therefore
    PREDICTED first: the current transform estimate says where a point on sheet
    A should fall on sheet B, a patch of A is resampled into B's frame so that
    rotation and scale differences stop mattering, and normalised
    cross-correlation only refines within a small window around that
    prediction. Matches are then filtered by correlation score and by a RANSAC
    similarity fit, so a cluster of mutually consistent matches survives and
    one-off coincidences do not.

Outputs
    gcps/shared_edges/<A>__<B>.geojson    correspondence catalogue per adjacency
    gcps/tiepoints_overlap.csv            appended control, ready for 06
    output/qc/overlap/<A>__<B>.png        what was matched, drawn on both sheets
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sanborn import geometry as G
from sanborn import masks as M
from sanborn.config import load_config, paths, read_json, setup_logging, write_json
from sanborn.render import read_image
from sanborn.tiepoints import refine_pair, write_gcp_csv

OPP = {"north": "south", "south": "north", "east": "west", "west": "east"}


def paper_ring(img, inset=10, clip_x=None):
    """Full drawn extent of a sheet: the cream paper, not the cut mask."""
    g = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    nz = (g < 238).astype(np.uint8)
    nz = cv2.morphologyEx(nz, cv2.MORPH_OPEN,
                          cv2.getStructuringElement(cv2.MORPH_RECT, (25, 25)))
    n, lab, stats, _ = cv2.connectedComponentsWithStats(nz, 8)
    i = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    x, y, w, h, _ = stats[i]
    x0, y0, x1, y1 = x + inset, y + inset, x + w - inset, y + h - inset
    if clip_x:
        x0, x1 = max(x0, clip_x[0]), min(x1, clip_x[1])
    return np.array(M.rect_ring(x0, y0, x1, y1), dtype=float)


def ransac_similarity(pa, pb, thresh=12.0, iters=400, seed=0):
    """Keep the largest mutually consistent set of matches."""
    pa, pb = np.asarray(pa, float), np.asarray(pb, float)
    n = len(pa)
    if n < 3:
        return np.ones(n, dtype=bool), None
    rng = np.random.default_rng(seed)
    best, bestH = np.zeros(n, dtype=bool), None
    for _ in range(iters):
        idx = rng.choice(n, 2, replace=False)
        if np.linalg.norm(pa[idx[0]] - pa[idx[1]]) < 50:
            continue
        try:
            H = G.fit_single("similarity", pa[idx], pb[idx])
        except Exception:
            continue
        err = np.linalg.norm(G.apply(H, pa) - pb, axis=1)
        inl = err <= thresh
        if inl.sum() > best.sum():
            best, bestH = inl, H
    if best.sum() >= 3:
        bestH = G.fit_single("similarity", pa[best], pb[best])
    return best, bestH


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--profile", default="galveston1889")
    ap.add_argument("--grid", type=int, default=14, help="candidate points per axis")
    ap.add_argument("--patch", type=int, default=60)
    ap.add_argument("--search", type=int, default=34)
    ap.add_argument("--min-score", type=float, default=0.45)
    ap.add_argument("--ransac-px", type=float, default=14.0)
    ap.add_argument("--max-rot-disagree", type=float, default=1.2,
                    help="max rotation disagreement (deg) with the centreline solution")
    ap.add_argument("--max-scale-disagree", type=float, default=0.025,
                    help="max scale disagreement (fraction) with the centreline solution")
    args = ap.parse_args()

    cfg = load_config(args.profile)
    p = paths().ensure()
    log = setup_logging("06c_overlap_correspondences")
    root = Path(cfg["_root"])
    src_dir = root / ((cfg.get("paths") or {}).get("original_dir") or "data/original")
    (p.gcps / "shared_edges").mkdir(parents=True, exist_ok=True)
    (p.qc / "overlap").mkdir(parents=True, exist_ok=True)

    tdoc = read_json(p.working / "transforms.json")
    T = {k: np.asarray(v, float) for k, v in tdoc["transforms"].items()}

    # full extents, per retained region (sheet 1 clipped to its retained panel)
    files, clip, region_of = {}, {}, {}
    for sh in cfg.get("sheets", []):
        for reg in sh.get("regions", []):
            if not reg.get("keep", True):
                continue
            rid = reg["id"]
            files[rid] = src_dir / sh["file"]
            region_of[str(sh["id"])] = rid
            if str(sh["id"]) == "1":
                doc = M.read_mask(root / reg["mask"])
                for r, ring, _ in M.regions(doc, keep_only=False):
                    if r == rid:
                        bx0, _, bx1, _ = M.ring_bounds(ring)
                        clip[rid] = (bx0 - 400, bx1 + 60)   # keep the shared strip
    images, rings = {}, {}

    def img_of(rid):
        if rid not in images:
            images[rid] = read_image(files[rid])
            rings[rid] = paper_ring(images[rid], clip_x=clip.get(rid))
        return images[rid]

    pairs = []
    for t in cfg.get("topology", []):
        a, b = t["region"], t["neighbour"]
        if a in files and b in files:
            pairs.append((a, b, t.get("direction", "")))

    from shapely.geometry import Polygon
    all_rows, catalogue = [], {}
    for a, b, direction in pairs:
        ia, ib = img_of(a), img_of(b)
        if a not in T or b not in T:
            continue
        pa_ring, pb_ring = G.apply(T[a], rings[a]), G.apply(T[b], rings[b])
        inter = Polygon(pa_ring).buffer(0).intersection(Polygon(pb_ring).buffer(0))
        if inter.is_empty or inter.area < 20000:
            log.warning("%s|%s: no usable overlap in the full sheet extents "
                        "(area %.0f px^2) -- nothing to match", a, b,
                        0.0 if inter.is_empty else inter.area)
            continue
        x0, y0, x1, y1 = inter.bounds
        log.info("%s|%s (%s): overlap %.0f x %.0f px, %.2f Mpx",
                 a, b, direction, x1 - x0, y1 - y0, inter.area / 1e6)

        Ai, Bi = np.linalg.inv(T[a]), np.linalg.inv(T[b])
        ha, wa = ia.shape[:2]
        hb, wb = ib.shape[:2]
        cand = []
        margin = args.patch + args.search + 12
        for gy in range(args.grid):
            for gx in range(args.grid):
                u = x0 + (x1 - x0) * (gx + 0.5) / args.grid
                v = y0 + (y1 - y0) * (gy + 0.5) / args.grid
                if not inter.contains(Polygon([(u - 1, v - 1), (u + 1, v - 1),
                                               (u + 1, v + 1), (u - 1, v + 1)])):
                    continue
                qa = G.apply(Ai, [(u, v)])[0]
                qb = G.apply(Bi, [(u, v)])[0]
                if not (margin < qa[0] < wa - margin and margin < qa[1] < ha - margin):
                    continue
                if not (margin < qb[0] < wb - margin and margin < qb[1] < hb - margin):
                    continue
                r = refine_pair(ia, qa, ib, qb, T[a], T[b],
                                patch=args.patch, search=args.search,
                                min_score=args.min_score)
                if r["score"] is None or r["score"] < args.min_score:
                    continue
                cand.append({"pa": (float(qa[0]), float(qa[1])),
                             "pb": r["refined"], "score": r["score"]})
        if len(cand) < 3:
            log.warning("   only %d candidate match(es); skipping this pair", len(cand))
            continue
        inl, H = ransac_similarity([c["pa"] for c in cand], [c["pb"] for c in cand],
                                   thresh=args.ransac_px)
        kept = [c for c, k in zip(cand, inl) if k]
        log.info("   %d candidate(s) -> %d consistent after RANSAC (median score %.2f)",
                 len(cand), len(kept), float(np.median([c["score"] for c in kept]))
                 if kept else 0.0)
        if len(kept) < 3:
            log.warning("   too few consistent matches; pair contributes nothing")
            continue

        # CROSS-CHECK against the independent centreline solution.
        # RANSAC guarantees internal consistency, not correctness: on a city
        # grid of near-identical blocks a whole cluster of matches can agree
        # with each other while being one block out. Such a set is
        # indistinguishable from a good one by score or inlier count -- but it
        # implies a sheet-to-sheet transform that disagrees with the one the
        # printed street centrelines already gave us. That is the test.
        prior = np.linalg.inv(T[b]) @ T[a]
        dp, dh = G.decompose_affine(prior), G.decompose_affine(H)
        drot = abs(dh["rotation_deg"] - dp["rotation_deg"])
        dscale = abs(dh["scale_x"] / max(dp["scale_x"], 1e-9) - 1.0)
        if drot > args.max_rot_disagree or dscale > args.max_scale_disagree:
            log.warning("   REJECTED: implied transform disagrees with the "
                        "centreline solution by %.2f deg / %.2f%% "
                        "(limits %.2f deg / %.2f%%). These matches are "
                        "internally consistent but almost certainly locked onto "
                        "the wrong block.", drot, 100 * dscale,
                        args.max_rot_disagree, 100 * args.max_scale_disagree)
            catalogue[f"{a}|{b}"] = {"candidates": len(cand), "kept": 0,
                                     "rejected_reason": f"disagrees with prior by "
                                     f"{drot:.2f} deg / {100*dscale:.2f}%"}
            continue
        log.info("   agrees with the centreline solution to %.2f deg / %.2f%%",
                 drot, 100 * dscale)

        feats = []
        for k, c in enumerate(kept):
            pid = f"OVL_{a}_{b}_{k:03d}"
            for rid, pt in ((a, c["pa"]), (b, c["pb"])):
                all_rows.append({
                    "point_id": pid, "sheet": rid, "region": rid, "role": "tie",
                    "src_x": round(pt[0], 2), "src_y": round(pt[1], 2),
                    "feature": "shared detail in sheet overlap",
                    "method": "predictive NCC + RANSAC similarity",
                    "confidence": "high" if c["score"] > 0.65 else "medium",
                    "selected_by": "06c_overlap_correspondences.py",
                    "accepted": "true", "note": f"ncc={c['score']:.3f}"})
            feats.append({"type": "Feature",
                          "geometry": {"type": "Point", "coordinates": list(c["pa"])},
                          "properties": {"point_id": pid, "sheet_a": a, "sheet_b": b,
                                         "a_x": c["pa"][0], "a_y": c["pa"][1],
                                         "b_x": c["pb"][0], "b_y": c["pb"][1],
                                         "ncc": c["score"], "crosses_boundary": True,
                                         "feature_type": "image detail",
                                         "confidence": "HIST_SHARED_HIGH"
                                         if c["score"] > 0.65 else "HIST_SHARED_MEDIUM"}})
        out = p.gcps / "shared_edges" / f"{a}__{b}.geojson"
        out.write_text(json.dumps({"type": "FeatureCollection",
                                   "space": "source pixels of sheet A",
                                   "pair": [a, b], "direction": direction,
                                   "features": feats}, indent=2), encoding="utf-8")
        catalogue[f"{a}|{b}"] = {"candidates": len(cand), "kept": len(kept),
                                 "overlap_mpx": inter.area / 1e6}

        vis = []
        for rid, key in ((a, "pa"), (b, "pb")):
            im = img_of(rid).copy()
            for c in kept:
                q = c[key]
                cv2.circle(im, (int(q[0]), int(q[1])), 26, (220, 30, 30), 7, cv2.LINE_AA)
            s = 900 / max(im.shape[:2])
            vis.append(cv2.resize(im, None, fx=s, fy=s, interpolation=cv2.INTER_AREA))
        hgt = max(v.shape[0] for v in vis)
        vis = [cv2.copyMakeBorder(v, 0, hgt - v.shape[0], 0, 0,
                                  cv2.BORDER_CONSTANT, value=(255, 255, 255)) for v in vis]
        cv2.imwrite(str(p.qc / "overlap" / f"{a}__{b}.png"),
                    cv2.cvtColor(np.hstack(vis), cv2.COLOR_RGB2BGR))

    if all_rows:
        write_gcp_csv(p.gcps / "tiepoints_overlap.csv", all_rows)
        log.info("wrote %d overlap observation(s) across %d pair(s)",
                 len(all_rows), len(catalogue))
    else:
        log.warning("no overlap correspondences found at all")
    write_json(p.qc / "overlap_summary.json", catalogue)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
