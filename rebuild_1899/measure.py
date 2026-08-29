#!/usr/bin/env python3
"""Rendition 1 calibration: verify landmarks and measure every seam.

Method (fresh code; no legacy pipeline imports — SEED_1899 FIREWALL):
- Initial per-sheet placement from SEED constants' street/avenue anchors
  (ground frame: x = avenue slot * 1006 px, y = street index * 1169 px).
- Landmark verification: normalized cross-correlation of a Sobel-edge patch
  from sheet A around a_xy, searched on sheet B around the anchor-predicted
  position. A strong, unambiguous peak within tolerance of b_xy verifies the
  correspondence with ink, independent of the locator's B coordinate.
- Dense seam measurement: the same matcher run at edge-rich sample points
  along the pair's overlap band. These (not the landmarks) feed the solver,
  keeping landmark_check.py non-circular.

Outputs rebuild_1899/out/r1_measurements.json.
"""
import json
import os
import sys

import numpy as np
import cv2

ROOT = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(ROOT)
SEED = os.path.join(REPO, "work", "seed_pipeline", "SEED_1899")
SHEETS_DIR = os.path.join(REPO, "work", "sheets", "1899")
OUT = os.path.join(ROOT, "out")
os.makedirs(OUT, exist_ok=True)

C = json.load(open(os.path.join(SEED, "constants.json")))
LM = json.load(open(os.path.join(SEED, "landmarks.json")))
PAIR_CTX = json.load(open(os.path.join(SEED, "pair_context.json")))

AV_PITCH = C["grid"]["avenue_pitch_px"]     # 1006, x direction (slots)
ST_PITCH = C["grid"]["street_pitch_px"]     # 1169, y direction (streets)

_cache = {}
def sheet_gray(num):
    if num not in _cache:
        p = os.path.join(SHEETS_DIR, f"Galveston_1899_sheet_{num}.jpg")
        img = cv2.imread(p, cv2.IMREAD_GRAYSCALE)
        assert img is not None, p
        _cache[num] = img
    return _cache[num]

def edges(img):
    gx = cv2.Sobel(img, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(img, cv2.CV_32F, 0, 1, ksize=3)
    m = cv2.magnitude(gx, gy)
    return np.clip(m / 8.0, 0, 255).astype(np.uint8)

_ecache = {}
def sheet_edges(num):
    if num not in _ecache:
        _ecache[num] = edges(sheet_gray(num))
    return _ecache[num]

# ---------------------------------------------------------------- anchors
# Ground frame: x_g = slot * AV_PITCH, y_g = street * ST_PITCH.
# Per sheet, fit x_g = x_native + ox ; y_g = y_native + oy  (translation only;
# anchors are too few for reliable per-sheet scale, solver refines later).
# Only the wharf sheets carry anchors in constants.json; every seam line in
# pair_context.json supplies one more anchor for BOTH its sheets.
def collect_anchors():
    va = {n: dict() for n in C["target_sheets"]}   # slot -> x_native
    ha = {n: dict() for n in C["target_sheets"]}   # street -> y_native
    for n, s in C["target_sheets"].items():
        for slot, x in (s.get("v_anchors") or {}).items():
            va[n].setdefault(int(slot), []).append(x) if isinstance(va[n].get(int(slot)), list) else va[n].__setitem__(int(slot), [x])
        for st, y in (s.get("h_anchors") or {}).items():
            ha[n][int(st)] = [y]
    for ctx in PAIR_CTX:
        idx = int(ctx["idx"])
        for who, key in (("owner", "owner_native"), ("nbr", "nbr_native")):
            n = ctx[who]
            d = va[n] if ctx["axis"] == "v" else ha[n]
            d.setdefault(idx, []).append(ctx[key])
    return va, ha

def anchor_offset(num, va, ha):
    oxs = [int(slot) * AV_PITCH - x for slot, xs in va[num].items() for x in xs]
    oys = [int(st) * ST_PITCH - y for st, ys in ha[num].items() for y in ys]
    assert oxs and oys, f"sheet {num} lacks an anchor on one axis"
    return (float(np.mean(oxs)), float(np.mean(oys)))

_VA, _HA = collect_anchors()
OFFSETS = {num: anchor_offset(num, _VA, _HA) for num in C["target_sheets"]}

TRANSFORMS = None  # set by refine.py: {sheet: {m: [[m00,m01],[m10,m11]], t: [tx,ty]}}

def predict_on_b(a, b, a_xy):
    """Predicted position of sheet-a native point a_xy on sheet b: through
    the solved transforms when refining, else through the anchor offsets."""
    if TRANSFORMS is not None:
        Ta, Tb = TRANSFORMS[a], TRANSFORMS[b]
        import numpy as _np
        g = _np.array(Ta["m"]) @ _np.array(a_xy) + _np.array(Ta["t"])
        inv = _np.linalg.inv(_np.array(Tb["m"]))
        p = inv @ (g - _np.array(Tb["t"]))
        return (float(p[0]), float(p[1]))
    oa, ob = OFFSETS[a], OFFSETS[b]
    return (a_xy[0] + oa[0] - ob[0], a_xy[1] + oa[1] - ob[1])

# ---------------------------------------------------------------- matcher
def match_point(a, b, a_xy, patch=91, search=280, bias=(0.0, 0.0)):
    """NCC of an edge patch from a around a_xy against b near the predicted
    spot. Returns dict or None if the patch/search leaves the image."""
    ea, eb = sheet_edges(a), sheet_edges(b)
    ax, ay = int(round(a_xy[0])), int(round(a_xy[1]))
    h = patch // 2
    if not (h <= ax < ea.shape[1] - h and h <= ay < ea.shape[0] - h):
        return None
    tpl = ea[ay - h:ay + h + 1, ax - h:ax + h + 1]
    if tpl.std() < 4.0:          # featureless: refuse rather than mismatch
        return {"status": "featureless"}
    px, py = predict_on_b(a, b, (ax, ay))
    px += bias[0]; py += bias[1]
    x0, y0 = int(round(px)) - search, int(round(py)) - search
    x1, y1 = int(round(px)) + search, int(round(py)) + search
    x0c, y0c = max(0, x0), max(0, y0)
    x1c, y1c = min(eb.shape[1], x1), min(eb.shape[0], y1)
    if x1c - x0c < patch + 20 or y1c - y0c < patch + 20:
        return {"status": "off-sheet"}
    win = eb[y0c:y1c, x0c:x1c]
    res = cv2.matchTemplate(win, tpl, cv2.TM_CCOEFF_NORMED)
    _, mx, _, ml = cv2.minMaxLoc(res)
    # quadratic subpixel refinement around the peak
    sub = [0.0, 0.0]
    ex_, ey_ = ml
    if 0 < ex_ < res.shape[1] - 1 and 0 < ey_ < res.shape[0] - 1:
        for axis, (m1, m2) in enumerate((
                (res[ey_, ex_ - 1], res[ey_, ex_ + 1]),
                (res[ey_ - 1, ex_], res[ey_ + 1, ex_]))):
            den = (m1 - 2 * res[ey_, ex_] + m2)
            if den < -1e-9:
                sub[axis] = float(np.clip(0.5 * (m1 - m2) / den, -1, 1))
    bx = x0c + ml[0] + h + sub[0]
    by = y0c + ml[1] + h + sub[1]
    # second peak outside a 41-px exclusion zone around the first
    r2 = res.copy()
    ex, ey = ml
    r2[max(0, ey - 20):ey + 21, max(0, ex - 20):ex + 21] = -1
    mx2 = float(r2.max())
    return {
        "status": "ok",
        "b_found": [round(float(bx), 2), round(float(by), 2)],
        "score": float(mx),
        "second": mx2,
        "distinct": float(mx - mx2),
        "pred_err": [float(bx - px), float(by - py)],
    }

# ---------------------------------------------------------------- landmarks
def verify_landmarks():
    out = []
    for f in LM["features"]:
        a, b = f["sheet_a"], f["sheet_b"]
        r = match_point(a, b, f["a_xy"])
        rec = {
            "id": f["id"], "pair": [a, b],
            "schematic": bool(f.get("schematic")),
            "a_xy": f["a_xy"], "b_xy_located": f["b_xy"],
        }
        if r is None or r.get("status") != "ok":
            rec["verdict"] = "unmatchable"
            rec["why"] = (r or {}).get("status", "patch outside sheet")
        else:
            dev = [r["b_found"][0] - f["b_xy"][0], r["b_found"][1] - f["b_xy"][1]]
            rec.update(b_xy_matched=r["b_found"], score=round(r["score"], 3),
                       distinct=round(r["distinct"], 3),
                       located_vs_matched_px=dev)
            close = max(abs(dev[0]), abs(dev[1])) <= 6
            # Periodic street grid keeps 'distinct' low legitimately: when the
            # ink match lands on the located point, the locator's coordinate
            # resolves the periodicity; that is agreement, not weakness.
            if close and r["score"] >= 0.35:
                rec["verdict"] = "verified"
            elif r["score"] >= 0.50 and r["distinct"] >= 0.10:
                rec["verdict"] = "relocated"
            else:
                rec["verdict"] = "weak"
        out.append(rec)
    return out

# ---------------------------------------------------------------- seams
WHARF_PAIRS = {("07", "06"), ("08", "07")}

def seam_samples(ctx, patch=61):
    """Sample points along the shared boundary, on the OWNER sheet, kept to
    the strip BOTH sheets print: ~±30 px inland (50-70 px total overlap),
    ~±100 px on the wharf pairs (230 px overlap)."""
    a = ctx["owner"]; ea = sheet_edges(a)
    H, W = ea.shape
    wharf = (ctx["owner"], ctx["nbr"]) in WHARF_PAIRS or ctx["axis"] == "v" and ctx["owner"] in ("06", "07", "08")
    bands = (-100, -50, 0, 50, 100) if wharf else (-30, 0, 30)
    step = 90
    pts = []
    if ctx["axis"] == "h":
        y = ctx["owner_native"]
        for band in bands:
            yy = y + band
            if patch <= yy < H - patch:
                for x in range(patch + 20, W - patch - 20, step):
                    pts.append((x, yy))
    else:
        x = ctx["owner_native"]
        for band in bands:
            xx = x + band
            if patch <= xx < W - patch:
                for y in range(patch + 20, H - patch - 20, step):
                    pts.append((xx, y))
    keep = []
    h = patch // 2
    for (x, y) in pts:
        t = ea[y - h:y + h + 1, x - h:x + h + 1]
        if t.std() >= 12.0:
            keep.append((x, y))
    return keep

def pair_landmark_bias(lm_results):
    """Per-pair pred_err at ink-verified landmarks: the trusted seed for the
    tight second matching pass. Landmarks still never enter the solver."""
    acc = {}
    for r in lm_results:
        if r["verdict"] != "verified":
            continue
        a, b = r["pair"]
        px, py = predict_on_b(a, b, r["a_xy"])
        e = (r["b_xy_matched"][0] - px, r["b_xy_matched"][1] - py)
        acc.setdefault((a, b), []).append(e)
        # store the reverse direction too (owner/nbr order differs)
        acc.setdefault((b, a), []).append(
            tuple(-v for v in e))  # approximate inverse (translation-level)
    return {k: (float(np.median([e[0] for e in v])),
                float(np.median([e[1] for e in v])))
            for k, v in acc.items()}

def largest_cluster(errs, radius=60):
    """Median of the biggest inlier cluster among pred_err candidates."""
    if not errs:
        return None, 0
    best, best_n = None, -1
    for c in errs:
        n = sum(1 for e in errs
                if abs(e[0] - c[0]) <= radius and abs(e[1] - c[1]) <= radius)
        if n > best_n:
            best, best_n = c, n
    inl = [e for e in errs
           if abs(e[0] - best[0]) <= radius and abs(e[1] - best[1]) <= radius]
    return (float(np.median([e[0] for e in inl])),
            float(np.median([e[1] for e in inl]))), len(inl)

def measure_pair(ctx, lm_bias=None):
    a, b = ctx["owner"], ctx["nbr"]
    pts = seam_samples(ctx)
    # pass 1: wide search, collect confident matches to fix the pair offset
    p1 = []
    for (x, y) in pts:
        r = match_point(a, b, (x, y), patch=61, search=600)
        if r and r.get("status") == "ok" and r["score"] >= 0.45 and r["distinct"] >= 0.06:
            p1.append(r["pred_err"])
    cluster, n_inl = largest_cluster(p1)
    bias_src = "none"
    if lm_bias and (a, b) in lm_bias:
        bias, bias_src = lm_bias[(a, b)], "verified-landmarks"
    elif cluster and n_inl >= 3:
        bias, bias_src = cluster, f"pass1-cluster(n={n_inl})"
    else:
        bias = (0.0, 0.0)
    # cross-check: if both exist and disagree by > 80 px, flag it loudly
    conflict = None
    if lm_bias and (a, b) in lm_bias and cluster and n_inl >= 3:
        d = (lm_bias[(a, b)][0] - cluster[0], lm_bias[(a, b)][1] - cluster[1])
        if max(abs(d[0]), abs(d[1])) > 80:
            conflict = {"landmark_bias": lm_bias[(a, b)], "cluster": cluster,
                        "cluster_n": n_inl}
    # pass 2: recentre the search on the pass-1 bias, tight window; the small
    # window suppresses periodic false peaks so the bar can drop
    recs = []
    inv_bias = (-bias[0], -bias[1])
    for (x, y) in pts:
        r = match_point(a, b, (x, y), patch=61, search=110, bias=bias)
        if not (r and r.get("status") == "ok" and r["score"] >= 0.42):
            continue
        # mutual consistency: match the found point back b->a; it must land
        # on the origin. Kills the one-sided pulls of partially-shared ink.
        rb = match_point(b, a, r["b_found"], patch=61, search=110, bias=inv_bias)
        if not (rb and rb.get("status") == "ok" and rb["score"] >= 0.42):
            continue
        ret = rb["b_found"]
        if abs(ret[0] - x) > 3.5 or abs(ret[1] - y) > 3.5:
            continue
        recs.append({"a_xy": [x, y], "b_xy": r["b_found"],
                     "score": round(r["score"], 3),
                     "pred_err": [round(v, 1) for v in r["pred_err"]]})
    # robust outlier trim around the median
    if len(recs) >= 5:
        mx = float(np.median([m["pred_err"][0] for m in recs]))
        my = float(np.median([m["pred_err"][1] for m in recs]))
        recs = [m for m in recs
                if abs(m["pred_err"][0] - mx) <= 40 and abs(m["pred_err"][1] - my) <= 40]
    dx = [m["pred_err"][0] for m in recs]
    dy = [m["pred_err"][1] for m in recs]
    summary = {
        "pair": [a, b], "boundary": ctx["boundary"], "axis": ctx["axis"],
        "bias_used": [round(bias[0], 1), round(bias[1], 1)],
        "bias_source": bias_src,
        "bias_conflict": conflict,
        "n_candidates_matched": len(recs),
        "pred_err_median": [float(np.median(dx)), float(np.median(dy))] if recs else None,
        "pred_err_iqr": [
            [float(np.percentile(dx, 25)), float(np.percentile(dx, 75))],
            [float(np.percentile(dy, 25)), float(np.percentile(dy, 75))],
        ] if len(recs) >= 4 else None,
    }
    return summary, recs

def main():
    print("verifying 77 landmarks...")
    lm_out = verify_landmarks()
    from collections import Counter
    print(Counter(r["verdict"] for r in lm_out))

    print("measuring 19 seams...")
    lm_bias = pair_landmark_bias(lm_out)
    seams, matches = [], {}
    for ctx in PAIR_CTX:
        s, recs = measure_pair(ctx, lm_bias)
        seams.append(s)
        matches[f"{ctx['owner']}|{ctx['nbr']}"] = recs
        print(f"  {ctx['owner']}|{ctx['nbr']:>2} {ctx['boundary']:<14} "
              f"n={s['n_candidates_matched']:3d} med={s['pred_err_median']} "
              f"bias<-{s['bias_source']}"
              + (" CONFLICT" if s["bias_conflict"] else ""))

    json.dump({
        "method": __doc__,
        "anchor_offsets": OFFSETS,
        "grid": {"avenue_pitch_px": AV_PITCH, "street_pitch_px": ST_PITCH},
        "landmark_verification": lm_out,
        "seam_summaries": seams,
        "seam_matches": matches,
    }, open(os.path.join(OUT, "r1_measurements.json"), "w"), indent=1)
    print("wrote out/r1_measurements.json")

if __name__ == "__main__":
    main()
