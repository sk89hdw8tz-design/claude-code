#!/usr/bin/env python3
"""Independent seam-QC sweep for the 1912 city-wide placement.

For every pair of units whose placed footprints overlap in the mosaic frame,
warp both units' ink masks into the overlap box at 1/4 frame scale and measure
the residual displacement between them by normalized cross-correlation
(cv2.matchTemplate, TM_CCOEFF_NORMED) over a +/-160 frame-px search.

Adjacency is derived from footprint overlap only (the network's `pairs` list is
ignored), so this is an independent check of the placement.

Frame convention: p_frame = m @ p_native + t, native = px in the unit's working
image (work/sheets/1912w/uNN.jpg).

Outputs (under --out-prefix, default outputs/1912/recipe/qc):
  seam_matrix_city.json, seam_matrix_city.md, proof_city/seam_A_B.png
"""
import argparse
import json
import math
import os
import sys
import time
from collections import OrderedDict

import cv2
import numpy as np
from shapely.affinity import affine_transform
from shapely.geometry import MultiPolygon, Polygon, box

SCALE = 0.25            # QC working scale relative to frame px
SEARCH = 40             # +/- px at QC scale  (= 160 frame px)
MIN_OVERLAP = 200 * 200  # frame px^2
INK_DELTA = 40          # ink = gray < median - 40
BLANK_FRAC = 0.005
OK_DIST = 40.0          # frame px
OK_PEAK = 0.25
OK_RATIO = 1.15
N_PROOF = 16
PROOF_MAX_BYTES = int(1.5 * 1024 * 1024)


def load_json(path):
    with open(path) as fh:
        return json.load(fh)


def pick(path, fallback):
    if path and os.path.exists(path):
        return path
    if fallback and os.path.exists(fallback):
        print(f"[qc] {path} missing, falling back to {fallback}")
        return fallback
    raise SystemExit(f"neither {path} nor {fallback} exists")


class GrayCache:
    """LRU cache of working images: full-res gray + ink threshold + half-res gray."""

    def __init__(self, root, cap=12):
        self.root = root
        self.cap = cap
        self.d = OrderedDict()

    def get(self, rel):
        if rel in self.d:
            self.d.move_to_end(rel)
            return self.d[rel]
        path = os.path.join(self.root, rel)
        g = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
        if g is None:
            raise FileNotFoundError(path)
        med = float(np.median(g))
        # Frame scale of the placement is ~2x native; at SCALE=1/4 the warp is
        # ~0.5x native, so pre-shrink with INTER_AREA and warp from that.
        half = cv2.resize(g, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA)
        ent = {"half": half, "median": med, "shape": g.shape}
        self.d[rel] = ent
        if len(self.d) > self.cap:
            self.d.popitem(last=False)
        return ent


def rect_poly(r):
    return box(r[0], r[1], r[2], r[3])


def unit_footprint(unit, sheet, inset=0):
    """Placed footprint (frame px). `inset` shrinks the native extent by that many
    native px on every side, which drops the printed sheet-border rule."""
    a, b = sheet["m"][0]
    c, d = sheet["m"][1]
    tx, ty = sheet["t"]
    params = [a, b, c, d, tx, ty]
    e = unit["extent"]
    fp = affine_transform(rect_poly([e[0] + inset, e[1] + inset, e[2] - inset, e[3] - inset]), params)
    if unit.get("hole"):
        fp = fp.difference(affine_transform(rect_poly(unit["hole"]), params))
    return fp


def poly_mask(poly, x0, y0, w, h, s):
    """Rasterize a shapely (Multi)Polygon into a uint8 mask at scale s."""
    m = np.zeros((h, w), np.uint8)
    geoms = poly.geoms if isinstance(poly, MultiPolygon) else [poly]
    for g in geoms:
        if g.is_empty or not isinstance(g, Polygon):
            continue
        ext = np.array([((x - x0) * s, (y - y0) * s) for x, y in g.exterior.coords], np.float32)
        cv2.fillPoly(m, [np.round(ext).astype(np.int32)], 1)
        for ring in g.interiors:
            hole = np.array([((x - x0) * s, (y - y0) * s) for x, y in ring.coords], np.float32)
            cv2.fillPoly(m, [np.round(hole).astype(np.int32)], 0)
    return m


def warp_unit(cache, unit, sheet, x0, y0, w, h, s):
    """Warp unit's working image into the (w,h) QC box. Returns gray, ink, valid."""
    ent = cache.get(unit["working"])
    m = np.array(sheet["m"], float)
    t = np.array(sheet["t"], float)
    # out = s*(m @ native + t - o); native = 2 * half_px
    A = np.zeros((2, 3), np.float64)
    A[:, :2] = s * m * 2.0
    A[:, 2] = s * (t - np.array([x0, y0], float))
    med = ent["median"]
    gray = cv2.warpAffine(ent["half"], A, (w, h), flags=cv2.INTER_LINEAR,
                          borderMode=cv2.BORDER_CONSTANT, borderValue=int(med))
    ones = np.ones(ent["half"].shape, np.uint8)
    valid = cv2.warpAffine(ones, A, (w, h), flags=cv2.INTER_NEAREST,
                           borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    ink = ((gray < med - INK_DELTA) & (valid > 0)).astype(np.uint8)
    return gray, ink, valid


def measure_shift(ink_a, ink_b, region):
    """NCC of A's blurred ink against B's, searching +/-SEARCH px.

    Returns (dx, dy, peak, ratio) at QC scale; d = position in B - position in A.
    """
    fa = cv2.GaussianBlur(ink_a.astype(np.float32) * region, (0, 0), 1.5)
    fb = cv2.GaussianBlur(ink_b.astype(np.float32) * region, (0, 0), 1.5)
    pad = SEARCH
    fb_p = cv2.copyMakeBorder(fb, pad, pad, pad, pad, cv2.BORDER_CONSTANT, value=0)
    if fa.std() < 1e-6 or fb.std() < 1e-6:
        return 0.0, 0.0, 0.0, 1.0
    res = cv2.matchTemplate(fb_p, fa, cv2.TM_CCOEFF_NORMED)
    res = np.nan_to_num(res, nan=-1.0)
    _, peak, _, loc = cv2.minMaxLoc(res)
    if peak <= 1e-6:  # flat / degenerate surface: no evidence, not a shift
        return 0.0, 0.0, 0.0, 1.0
    px, py = loc
    dx, dy = px - pad, py - pad
    r2 = res.copy()
    yy, xx = np.ogrid[:r2.shape[0], :r2.shape[1]]
    r2[(yy - py) ** 2 + (xx - px) ** 2 <= 9] = -np.inf
    second = float(r2.max()) if np.isfinite(r2).any() else -1.0
    if peak <= 0:
        ratio = 1.0
    elif second <= 1e-6:
        ratio = 99.0
    else:
        ratio = min(99.0, peak / second)
    return float(dx), float(dy), float(peak), float(ratio)


def classify(ink_a, ink_b, dist, peak, ratio, ok_peak=OK_PEAK, ok_ratio=OK_RATIO, ok_dist=OK_DIST):
    if ink_a < BLANK_FRAC or ink_b < BLANK_FRAC:
        return "blank"
    if peak < ok_peak or ratio < ok_ratio:
        return "WEAK"
    if dist <= ok_dist:
        return "OK"
    return "SHIFT"


def proof_panel(path, gray_a, ink_a, ink_b, region, caption):
    h, w = ink_a.shape
    a = (ink_a * region).astype(bool)
    b = (ink_b * region).astype(bool)
    img = np.full((h, w, 3), 255, np.uint8)
    # A ink removes G,B -> red ; B ink removes R -> cyan ; both -> black
    img[a, 1] = 0
    img[a, 2] = 0
    img[b, 0] = 0
    # dim the area outside the overlap polygon
    outside = region == 0
    img[outside] = (img[outside] * 0.6 + 40).astype(np.uint8)
    # swap channels to BGR ordering for cv2: red ink = (0,0,255) BGR
    img = img[:, :, ::-1].copy()
    strip = np.full((28, w, 3), 255, np.uint8)
    img = np.vstack([strip, img])
    for _ in range(4):
        out = img.copy()
        fs = max(0.35, min(0.6, out.shape[1] / 1400.0))
        cv2.putText(out, caption, (5, 19), cv2.FONT_HERSHEY_SIMPLEX, fs, (0, 0, 0), 1, cv2.LINE_AA)
        ok, buf = cv2.imencode(".png", out, [cv2.IMWRITE_PNG_COMPRESSION, 9])
        if ok and len(buf) <= PROOF_MAX_BYTES:
            break
        img = cv2.resize(img, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA)
    with open(path, "wb") as fh:
        fh.write(buf.tobytes())


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--placement", default="rebuild_1899/out/grid_place_1912.json")
    ap.add_argument("--network", default="rebuild_1899/out/network_1912_v2.json")
    ap.add_argument("--root", default=".", help="repo root that `working` paths are relative to")
    ap.add_argument("--out-prefix", default="outputs/1912/recipe/qc")
    ap.add_argument("--limit", type=int, default=0, help="process only the first N pairs")
    ap.add_argument("--n-proof", type=int, default=N_PROOF)
    ap.add_argument("--ok-peak", type=float, default=OK_PEAK, help="min NCC peak for OK/SHIFT (else WEAK)")
    ap.add_argument("--ok-ratio", type=float, default=OK_RATIO, help="min peak/second-peak ratio (else WEAK)")
    ap.add_argument("--ok-dist", type=float, default=OK_DIST, help="max |d| frame px for OK")
    ap.add_argument("--ink-inset", type=float, default=40.0,
                    help="native px trimmed from each extent edge for ink evidence (drops the border rule; "
                         "adjacency still uses the full extent)")
    args = ap.parse_args()

    placement_path = pick(args.placement, "rebuild_1899/out/affine_city_1912.json")
    network_path = pick(args.network, "rebuild_1899/out/network_1912.json")
    placement = load_json(placement_path)["sheets"]
    units = load_json(network_path)["units"]

    ids = [u for u in units if u in placement]
    missing = sorted(set(units) - set(placement))
    if missing:
        print(f"[qc] {len(missing)} network units have no placement, skipped: {missing}")

    def sort_key(u):
        n = "".join(ch for ch in u if ch.isdigit())
        return (int(n) if n else 0, u)

    ids.sort(key=sort_key)
    fps = {u: unit_footprint(units[u], placement[u]) for u in ids}
    fps_in = {u: unit_footprint(units[u], placement[u], args.ink_inset) for u in ids}

    pairs = []
    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            if not fps[a].intersects(fps[b]):
                continue
            ov = fps[a].intersection(fps[b])
            if ov.area <= 0:
                continue
            pairs.append((a, b, ov))
    print(f"[qc] {len(ids)} units, {len(pairs)} overlapping pairs "
          f"({sum(1 for p in pairs if p[2].area >= MIN_OVERLAP)} with area >= {MIN_OVERLAP})")
    if args.limit:
        pairs = pairs[:args.limit]

    os.makedirs(args.out_prefix, exist_ok=True)
    proof_dir = os.path.join(args.out_prefix, "proof_city")
    os.makedirs(proof_dir, exist_ok=True)
    for fn in os.listdir(proof_dir):
        if fn.startswith("seam_") and fn.endswith(".png"):
            os.remove(os.path.join(proof_dir, fn))

    cache = GrayCache(args.root, cap=12)
    rows = []
    panels = {}  # (a,b) -> data needed for proof
    t0 = time.time()
    for n, (a, b, ov_full) in enumerate(pairs, 1):
        # measure on the inset footprints (border rule excluded); report the full overlap area
        ov = fps_in[a].intersection(fps_in[b]) if args.ink_inset else ov_full
        if ov.area < MIN_OVERLAP:
            ov = ov_full
            rows.append({"a": a, "b": b, "overlap_area": round(ov.area), "dx": None, "dy": None,
                         "dist": None, "peak": None, "ratio": None, "ink_a": None, "ink_b": None,
                         "verdict": "skipped-small"})
            continue
        x0, y0, x1, y1 = ov.bounds
        x0, y0 = math.floor(x0), math.floor(y0)
        w = max(8, int(math.ceil((x1 - x0) * SCALE)))
        h = max(8, int(math.ceil((y1 - y0) * SCALE)))
        region = poly_mask(ov, x0, y0, w, h, SCALE)
        ga, ia, va = warp_unit(cache, units[a], placement[a], x0, y0, w, h, SCALE)
        gb, ib, vb = warp_unit(cache, units[b], placement[b], x0, y0, w, h, SCALE)
        region = region * (va > 0) * (vb > 0)
        npix = int(region.sum())
        if npix == 0:
            ink_a = ink_b = 0.0
        else:
            ink_a = float((ia * region).sum()) / npix
            ink_b = float((ib * region).sum()) / npix
        dx, dy, peak, ratio = measure_shift(ia, ib, region)
        dxf, dyf = dx / SCALE, dy / SCALE
        dist = math.hypot(dxf, dyf)
        verdict = classify(ink_a, ink_b, dist, peak, ratio, args.ok_peak, args.ok_ratio, args.ok_dist)
        at_edge = max(abs(dx), abs(dy)) >= SEARCH  # peak on the search boundary: d is a lower bound
        rows.append({"a": a, "b": b, "overlap_area": round(ov.area),
                     "dx": round(dxf, 1), "dy": round(dyf, 1), "dist": round(dist, 1),
                     "peak": round(peak, 3), "ratio": round(ratio, 3),
                     "ink_a": round(ink_a, 4), "ink_b": round(ink_b, 4), "verdict": verdict,
                     "at_edge": bool(at_edge)})
        if verdict != "blank":
            panels[(a, b)] = (ga, ia, ib, region)
        if n % 20 == 0:
            print(f"[qc] {n}/{len(pairs)} pairs  {time.time() - t0:.0f}s")

    # rank: worst first = largest dist, then lowest peak; blank / skipped last
    def worst_key(r):
        if r["verdict"] in ("blank", "skipped-small"):
            return (1, 0, 0)
        return (0, -r["dist"], r["peak"])

    rows_sorted = sorted(rows, key=worst_key)

    # proof panels for worst N non-blank seams
    n_written = 0
    for r in rows_sorted:
        if n_written >= args.n_proof:
            break
        key = (r["a"], r["b"])
        if key not in panels:
            continue
        ga, ia, ib, region = panels[key]
        cap = (f"A={r['a']} (red)  B={r['b']} (cyan)  dx={r['dx']:+.0f} dy={r['dy']:+.0f} "
               f"dist={r['dist']:.0f}fpx  peak={r['peak']:.2f} ratio={r['ratio']:.2f}  "
               f"ink={r['ink_a']*100:.1f}%/{r['ink_b']*100:.1f}%  {r['verdict']}  [1/4 scale]")
        proof_panel(os.path.join(proof_dir, f"seam_{r['a']}_{r['b']}.png"), ga, ia, ib, region, cap)
        n_written += 1
    panels.clear()

    counts = {}
    for r in rows:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
    dists = [r["dist"] for r in rows if r["verdict"] in ("OK", "SHIFT")]
    summary = {
        "n_units": len(ids), "n_pairs": len(rows), "counts": counts,
        "median_dist_ok_shift": round(float(np.median(dists)), 1) if dists else None,
        "p90_dist_ok_shift": round(float(np.percentile(dists, 90)), 1) if dists else None,
        "max_dist_ok_shift": round(float(max(dists)), 1) if dists else None,
        "proof_panels": n_written, "seconds": round(time.time() - t0, 1),
    }
    out = {"placement": placement_path, "network": network_path,
           "params": {"scale": SCALE, "search_frame_px": SEARCH / SCALE, "min_overlap": MIN_OVERLAP,
                      "ink_delta": INK_DELTA, "blank_frac": BLANK_FRAC, "ink_inset_native_px": args.ink_inset,
                      "ok_peak": args.ok_peak, "ok_ratio": args.ok_ratio, "ok_dist": args.ok_dist,
                      "d_sign": "d = position of feature in B minus position in A (frame px)"},
           "pairs": rows_sorted, "summary": summary}
    # note: overlap_area is the full-extent overlap; the measurement region is the inset overlap
    jpath = os.path.join(args.out_prefix, "seam_matrix_city.json")
    with open(jpath, "w") as fh:
        json.dump(out, fh, indent=1)

    md = [f"# 1912 city seam matrix", "",
          f"placement: `{placement_path}`  network: `{network_path}`", "",
          f"units: {len(ids)}  pairs: {len(rows)}  counts: {counts}  "
          f"median dist (OK+SHIFT): {summary['median_dist_ok_shift']}  p90: {summary['p90_dist_ok_shift']}", "",
          "d = feature position in B minus A, frame px. Sorted worst first. edge=* means the NCC peak sat on the "
          f"search boundary (+/-{SEARCH / SCALE:.0f} frame px), so d is a lower bound.", "",
          "| a | b | overlap | dx | dy | dist | peak | ratio | ink_a | ink_b | verdict | edge |",
          "|---|---|--:|--:|--:|--:|--:|--:|--:|--:|---|---|"]
    for r in rows_sorted:
        f = lambda v, fmt: ("" if v is None else format(v, fmt))
        md.append(f"| {r['a']} | {r['b']} | {r['overlap_area']} | {f(r['dx'], '+.0f')} | {f(r['dy'], '+.0f')} | "
                  f"{f(r['dist'], '.0f')} | {f(r['peak'], '.2f')} | {f(r['ratio'], '.2f')} | "
                  f"{f(r['ink_a'], '.3f')} | {f(r['ink_b'], '.3f')} | {r['verdict']} | "
                  f"{'*' if r.get('at_edge') else ''} |")
    with open(os.path.join(args.out_prefix, "seam_matrix_city.md"), "w") as fh:
        fh.write("\n".join(md) + "\n")
    print(f"[qc] done: {summary}")
    print(f"[qc] wrote {jpath}")


if __name__ == "__main__":
    main()
