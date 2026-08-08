"""Phases B+C driver for one edition: detect -> gate -> identify -> fit ->
composite. Registration/compositing units are rectangular on-grid panels
from coverage_prior.COVERAGE (a physical sheet may contribute several).

Usage: python3 run_build.py 1885|1877

Seam model: every shared boundary line gets ONE global cut position,
bound = min(owner_frame, centerline + SHIFT) where the owner is the
left/top unit. The owner draws up to bound (+feather), the neighbor starts
at bound (-feather) — windows overlap by 2*feather so blending cross-fades
sheet to sheet rather than sheet-paper-sheet. This closes the paper bands
a fixed independent shift leaves when a sheet's printed frame ends before
centerline+SHIFT.
"""

import json
import os
import sys

import numpy as np

import config
import coverage_prior as cov
import registration as reg
import composite as comp


def log(msg):
    print(f"[build] {msg}", flush=True)


def sheet_path(year, filenum):
    d = os.path.join(config.SOURCES_DIR, year)
    candidates = [
        os.path.join(d, f"Galveston_{year}_sheet_{filenum:02d}.jpg"),
        os.path.join(d, f"08539_{year}-{filenum:04d}.tif"),
        os.path.join(d, f"txu-sanborn-galveston-{year}-{filenum:02d}.jpg"),
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return candidates[0]


def assign_identities(detected, year, key):
    avs, sts = cov.expected_lines(year, key)
    v, h = detected["v_lines_native"], detected["h_lines_native"]
    if len(v) != len(avs) or len(h) != len(sts):
        return None, (
            f"line count mismatch: detected {len(v)}v/{len(h)}h, "
            f"expected {len(avs)} avenues/{len(sts)} streets"
        )
    controls = [
        {"axis": "x", "native": x, "identity": a} for x, a in zip(sorted(v), avs)
    ] + [
        {"axis": "y", "native": y, "identity": s} for y, s in zip(sorted(h), sts)
    ]
    return controls, None


def fit_sheet(controls, year):
    """Per-axis fit, edge-bias aware (edge grid lines sit on half-streets and
    refine inward): >=2 interior lines -> scale+translation on interior only;
    ==1 -> scale locked, translation from that line; 0 -> scale locked,
    translation from the mean of all lines (symmetric biases cancel)."""
    ed = config.EDITIONS[year]
    out = {}
    for axis, pitch, origin in (("x", ed["pitch_av"], 0), ("y", ed["pitch_st"], config.STREET_ORIGIN)):
        pts = sorted((c for c in controls if c["axis"] == axis), key=lambda c: c["native"])
        interior = pts[1:-1]
        src_all = np.array([c["native"] for c in pts])
        dst_all = np.array([(c["identity"] - origin) * pitch for c in pts])
        if len(interior) >= 2:
            src = np.array([c["native"] for c in interior])
            dst = np.array([(c["identity"] - origin) * pitch for c in interior])
            A = np.vstack([src, np.ones_like(src)]).T
            (s, t), *_ = np.linalg.lstsq(A, dst, rcond=None)
            mode = f"interior({len(interior)})"
        elif len(interior) == 1:
            s = 1.0
            c = interior[0]
            t = float((c["identity"] - origin) * pitch - c["native"])
            mode = "translation-1interior"
        else:
            s = 1.0
            t = float(np.mean(dst_all - src_all))
            mode = f"translation-only({len(pts)})"
        resid = dst_all - (s * src_all + t)
        dev = abs(s - 1.0)
        flag = "FAIL" if dev > config.SCALE_FAIL else "WARN" if dev > config.SCALE_WARN else "OK"
        out[f"s{axis}"] = float(s)
        out[f"t{axis}"] = float(t)
        out[f"mode_{axis}"] = mode
        out[f"flag_{axis}"] = flag
        out[f"resid_{axis}"] = [round(float(r), 1) for r in resid]
    return out


def spacing_gate(detected, year, tolerance=0.06):
    """Off-scale check on interior line spacings (median vs edition pitch)."""
    ed = config.EDITIONS[year]
    devs = {}
    for k, pitch in (("v_lines_native", ed["pitch_av"]), ("h_lines_native", ed["pitch_st"])):
        lines = detected[k]
        if len(lines) < 3:
            continue
        sp = [b - a for a, b in zip(lines, lines[1:])]
        if len(lines) >= 4:
            sp = sp[1:-1]
        devs[k] = round(float(np.median(sp)) / pitch - 1, 4)
    bad = any(abs(d) > tolerance for d in devs.values())
    return bad, devs


def register_edition(year):
    results = {}
    for key, unit in cov.COVERAGE[year].items():
        path = sheet_path(year, unit["file"])
        if not os.path.exists(path):
            results[key] = {"status": "missing-source"}
            log(f"unit {key}: source missing")
            continue
        det = reg.detect_sheet_grid(path, region=unit["region"])
        det["panel_region"] = unit["region"]
        bad, devs = spacing_gate(det, year)
        if bad:
            results[key] = {"status": "off-scale", "spacing_dev": devs,
                            "note": "median interior spacing deviates >6% — excluded, disclosed"}
            log(f"unit {key}: OFF-SCALE {devs} — excluded")
            continue
        controls, err = assign_identities(det, year, key)
        if err:
            results[key] = {"status": "needs-review", "detail": err, "detected": det}
            log(f"unit {key}: NEEDS REVIEW — {err}")
            continue
        fit = fit_sheet(controls, year)
        status = "ok" if all(fit[f"flag_{a}"] in ("OK", "WARN") for a in "xy") else "scale-fail"
        results[key] = {"status": status, "fit": fit, "detected": det, "controls": controls}
        log(f"unit {key}: sx={fit['sx']:.4f} {fit['mode_x']} ({fit['flag_x']}) "
            f"resid={fit['resid_x']} | sy={fit['sy']:.4f} {fit['mode_y']} "
            f"({fit['flag_y']}) resid={fit['resid_y']}")
    outdir = os.path.join(config.BUILD_DIR, year)
    os.makedirs(outdir, exist_ok=True)
    with open(os.path.join(outdir, "registration.json"), "w") as f:
        json.dump(results, f, indent=1, default=list)
    return results


def global_frame(fit, frame_native):
    fx0, fy0, fx1, fy1 = frame_native
    return (fx0 * fit["sx"] + fit["tx"], fy0 * fit["sy"] + fit["ty"],
            fx1 * fit["sx"] + fit["tx"], fy1 * fit["sy"] + fit["ty"])


def composite_edition(year, registration):
    import cv2

    ed = config.EDITIONS[year]
    a0, a1, s0, s1 = cov.composite_extent(year)
    # pad must fit the retained exterior margins: frame overhang past the
    # outermost street line (~150) + margin band (0.28 pitch) + slack
    pad = round(0.40 * ed["pitch_av"])
    width = round((a1 - a0) * ed["pitch_av"]) + 2 * pad
    height = round((s1 - s0) * ed["pitch_st"]) + 2 * pad
    ox = a0 * ed["pitch_av"] - pad
    oy = (s0 - config.STREET_ORIGIN) * ed["pitch_st"] - pad
    log(f"{year} canvas {width} x {height} ({width*height/1e6:.0f} MP)")

    native_w = ed["native_size"][0]
    shift = config.CLIP_SHIFT_3400 * native_w / config.DETECT_WIDTH
    feather = round(config.FEATHER_3400 * native_w / config.DETECT_WIDTH)
    ext = shift

    usable = {k: r for k, r in registration.items() if r.get("status") == "ok"}

    # Tonal reference (panel region only) — computed BEFORE the canvas so
    # the flat gap fill uses the MEASURED edition paper tone; the old
    # paper_bgr constant sat ~40/28/19 below the real retained-margin
    # paper and read as a hard step wherever fill met margin (QC v3-1)
    tones = {}
    for key, r in usable.items():
        unit = cov.COVERAGE[year][key]
        img = cv2.imread(sheet_path(year, unit["file"]), cv2.IMREAD_COLOR)
        if unit["region"]:
            x0, y0, x1, y1 = unit["region"]
            img = img[y0:y1, x0:x1]
        tones[key] = comp.paper_tone(img)
        del img
    target_tone = np.mean(list(tones.values()), axis=0)
    log(f"edition mean paper tone (BGR): {np.round(target_tone,1)}")

    canvas, weight = comp.new_canvas(width, height,
                                     tuple(int(round(v)) for v in target_tone))

    # ---- Consensus grid: real street spacing is non-uniform (spec §5.2), so
    # a uniform ideal grid makes independently-fitted sheets disagree about
    # where their SHARED boundary street sits (observed up to 274 px). Fix:
    # each grid line's global position = median over all units' initial-fit
    # placements of their DETECTED line; then re-anchor each unit's per-axis
    # affine exactly through its two outermost detected lines mapped to the
    # consensus positions. Neighbors then place the shared street at the
    # identical global coordinate — zero structural seam offset.
    # Frames first: needed to correct edge-knot bias. A unit whose printed
    # frame falls INSIDE a boundary street corridor prints only a sliver of
    # it, so its whiteness-CoM "line" measures the sliver center, not the
    # corridor center (observed ~180 px off on sheet 14's top). Recover the
    # center from strip center d, frame f and corridor width W (~460 px):
    #   frame on the low side  (top/left):  c = 2d - f - W/2  if f > d - W/2
    #   frame on the high side (bottom/right): c = 2d - f + W/2  if f < d + W/2
    frames_native = {}
    corrected = {}
    corr_path = os.path.join(config.BUILD_DIR, year, "edge_corrections.json")
    measured = json.load(open(corr_path)) if os.path.exists(corr_path) else {}
    md_path = os.path.join(config.BUILD_DIR, year, "manual_knot_deltas.json")
    manual_deltas = json.load(open(md_path)) if os.path.exists(md_path) else {}
    if manual_deltas:
        log(f"applying manual knot deltas for units {list(manual_deltas)}")
    if measured:
        log(f"applying measured edge corrections from {corr_path}")
    for key, r in usable.items():
        unit = cov.COVERAGE[year][key]
        det = r["detected"]
        v = sorted(det["v_lines_native"])
        h = sorted(det["h_lines_native"])
        img = cv2.imread(sheet_path(year, unit["file"]), cv2.IMREAD_COLOR)
        img01 = img.astype(np.float32) / 255.0
        fr = comp.frame_bounds(img01, v, h, region=unit["region"])
        del img, img01
        frames_native[key] = fr
        m = measured.get(key, {})
        for axis, lines in (("v", v), ("h", h)):
            for si, err in m.get(axis, {}).items():
                i = int(si)
                if i == 0:
                    lines[i] -= err     # push rendered edge content inward-away
                else:
                    lines[i] += err
        mk = manual_deltas.get(key, {})
        for axis, lines in (("v", v), ("h", h)):
            for si, delta in mk.get(axis, {}).items():
                lines[int(si)] += delta
        corrected[key] = (v, h)
    # Same-sheet panels must agree where their shared avenue sits on the
    # shared scan: unify 11b's Avenue H knot with 11a's (one physical line,
    # one native coordinate) so their mappings are continuous at H.
    if year == "1885" and "11a" in corrected and "11b" in corrected:
        corrected["11b"][0][0] = corrected["11a"][0][-1]

    def joint_solve(axis):
        """Alternating LSQ: grid-line globals X_l and per-unit (s,t) jointly.
        Corridor-corrected lines all measure the true street center; a scale
        prior keeps s near 1 so line noise lands in the grid, not in
        stretching. Weak uniform prior fixes the gauge."""
        pitch = ed["pitch_av"] if axis == "v" else ed["pitch_st"]
        origin = 0 if axis == "v" else config.STREET_ORIGIN
        obs = {}   # key -> (identities, native positions)
        for key, r in usable.items():
            avs, sts = cov.expected_lines(year, key)
            idents = avs if axis == "v" else sts
            lines = corrected[key][0] if axis == "v" else corrected[key][1]
            obs[key] = (idents, np.array(lines, float))
        fits = {k: (r["fit"]["sx"], r["fit"]["tx"]) if axis == "v" else (r["fit"]["sy"], r["fit"]["ty"])
                for k, r in usable.items()}
        W_SCALE = 3000.0    # 1% scale deviation costs like a 30 px residual
        W_PRIOR = 0.05      # weak pull of grid lines toward the uniform grid
        for _ in range(20):
            votes = {}
            for key, (idents, lines) in obs.items():
                s, t = fits[key]
                for ident, p in zip(idents, lines):
                    votes.setdefault(ident, []).append(s * p + t)
            G = {}
            for ident, v in votes.items():
                uni = (ident - origin) * pitch
                G[ident] = (np.sum(v) + W_PRIOR * uni) / (len(v) + W_PRIOR)
            for key, (idents, lines) in obs.items():
                dst = np.array([G[i] for i in idents])
                A = np.vstack([np.append(lines, W_SCALE),
                               np.append(np.ones_like(lines), 0.0)]).T
                b = np.append(dst, W_SCALE * 1.0)
                (s, t), *_ = np.linalg.lstsq(A, b, rcond=None)
                fits[key] = (float(s), float(t))
        return G, fits

    X, fx = joint_solve("v")
    Y, fy = joint_solve("h")
    log("grid avenue offsets from uniform: " +
        str({a: round(X[a] - a * ed["pitch_av"]) for a in sorted(X)}))
    log("grid street offsets from uniform: " +
        str({s: round(Y[s] - (s - config.STREET_ORIGIN) * ed["pitch_st"]) for s in sorted(Y)}))

    geo = {}
    for key, r in usable.items():
        unit = cov.COVERAGE[year][key]
        avs, sts = cov.expected_lines(year, key)
        v, h = corrected[key]
        sx, tx = fx[key]
        sy, ty = fy[key]
        seam_res_x = [round(X[a] - (sx * p + tx), 1) for a, p in zip(avs, v)]
        seam_res_y = [round(Y[s] - (sy * p + ty), 1) for s, p in zip(sts, h)]
        for name, s in (("sx", sx), ("sy", sy)):
            if abs(s - 1.0) > config.SCALE_FAIL:
                log(f"unit {key}: joint fit {name}={s:.4f} exceeds ±2% — check line identity")
        fit = {"sx": sx, "tx": tx, "sy": sy, "ty": ty}
        r["fit_consensus"] = {**fit, "line_resid_x": seam_res_x, "line_resid_y": seam_res_y}
        r["knots"] = {"xkn": list(map(float, v)), "xkg": [float(X[a]) for a in avs],
                      "ykn": list(map(float, h)), "ykg": [float(Y[s]) for s in sts]}
        frame = frames_native[key]
        img_s = cv2.imread(sheet_path(year, unit["file"]), cv2.IMREAD_GRAYSCALE)
        small = cv2.resize(img_s, (img_s.shape[1] // 4, img_s.shape[0] // 4),
                           interpolation=cv2.INTER_AREA)
        del img_s
        xkn, xkg = v, [X[a] for a in avs]
        ykn, ykg = h, [Y[s] for s in sts]
        fx0, fx1 = comp.pw_fwd([frame[0], frame[2]], xkn, xkg)
        fy0, fy1 = comp.pw_fwd([frame[1], frame[3]], ykn, ykg)
        geo[key] = {"fit": fit, "gv": v, "gh": h,
                    "xkn": xkn, "xkg": xkg, "ykn": ykn, "ykg": ykg,
                    "frame_g": (float(fx0), float(fy0), float(fx1), float(fy1)),
                    "avs": avs, "sts": sts, "gray4": small}
        log(f"unit {key}: piecewise knots (affine sanity sx={sx:.4f} sy={sy:.4f})")

    # ---- Content-level seam refinement: both sheets print the shared street
    # corridor, so phase-correlating the two units' corridor bands measures
    # the ACTUAL content offset at each seam (line detections carry ±40 px
    # noise; content matching gets to ~10 px). Solve per-unit translation
    # corrections by network least squares over all seam measurements.
    def band_patch(key, gx0, gx1, gy0, gy1, out_w, out_h):
        f = geo[key]["fit"]
        nx0 = (gx0 - f["tx"]) / f["sx"] / 4.0
        nx1 = (gx1 - f["tx"]) / f["sx"] / 4.0
        ny0 = (gy0 - f["ty"]) / f["sy"] / 4.0
        ny1 = (gy1 - f["ty"]) / f["sy"] / 4.0
        sm = geo[key]["gray4"]
        x0, x1 = int(max(0, nx0)), int(min(sm.shape[1], nx1))
        y0, y1 = int(max(0, ny0)), int(min(sm.shape[0], ny1))
        if x1 - x0 < 8 or y1 - y0 < 8:
            return None
        return cv2.resize(sm[y0:y1, x0:x1].astype(np.float32), (out_w, out_h))

    seam_meas = []   # (owner, nbr, dx_global, dy_global, weight)
    prop = {}
    for axis, idx, owner, nbr in cov.neighbors(year):
        if owner not in geo or nbr not in geo:
            continue
        ao, so = geo[owner]["avs"], geo[owner]["sts"]
        an, sn = geo[nbr]["avs"], geo[nbr]["sts"]
        if axis == "v":
            c = X[idx]
            lo = Y[max(min(so), min(sn))] + 100
            hi = Y[min(max(so), max(sn))] - 100
            g = (c - 260, c + 260, lo, hi)
            out_w, out_h = 130, max(64, int((hi - lo) / 16))
        else:
            c = Y[idx]
            lo = X[max(min(ao), min(an))] + 100
            hi = X[min(max(ao), max(an))] - 100
            g = (lo, hi, c - 260, c + 260)
            out_w, out_h = max(64, int((hi - lo) / 16)), 130
        pa = band_patch(owner, *g, out_w, out_h)
        pb = band_patch(nbr, *g, out_w, out_h)
        if pa is None or pb is None:
            continue
        win = cv2.createHanningWindow((out_w, out_h), cv2.CV_32F)
        (dx, dy), resp = cv2.phaseCorrelate(pa, pb, win)
        # patch px -> global px
        gxs = (g[1] - g[0]) / out_w
        gys = (g[3] - g[2]) / out_h
        if resp > 0.55 and abs(dx * gxs) < 200 and abs(dy * gys) < 200:  # cross-sheet corr unreliable (different drawings); diagnostics only
            seam_meas.append((owner, nbr, dx * gxs, dy * gys, resp))
            log(f"seam {axis}{idx} {owner}|{nbr}: content offset "
                f"({dx*gxs:+.0f},{dy*gys:+.0f})px resp={resp:.2f}")

    keys = list(geo)
    ki = {k: i for i, k in enumerate(keys)}
    for comp_axis in (0, 1):   # 0 = x corrections, 1 = y corrections
        rows, rhs, wts = [], [], []
        for owner, nbr, dxg, dyg, wgt in seam_meas:
            d = dxg if comp_axis == 0 else dyg
            row = np.zeros(len(keys))
            # patch B appears shifted by +d relative to A means B's content
            # sits d px later; shifting B by -d aligns them: t_B - t_A = -d
            row[ki[nbr]] = 1.0
            row[ki[owner]] = -1.0
            rows.append(row)
            rhs.append(-d)
            wts.append(wgt)
        for k in keys:   # weak prior: corrections near zero
            row = np.zeros(len(keys))
            row[ki[k]] = 1.0
            rows.append(row)
            rhs.append(0.0)
            wts.append(0.25)
        A = np.array(rows) * np.sqrt(np.array(wts))[:, None]
        b = np.array(rhs) * np.sqrt(np.array(wts))
        corr, *_ = np.linalg.lstsq(A, b, rcond=None)
        for k in keys:
            key_t = "tx" if comp_axis == 0 else "ty"
            geo[k]["fit"][key_t] += float(corr[ki[k]])
        log(("x" if comp_axis == 0 else "y") + " translation corrections: " +
            str({k: round(float(corr[ki[k]])) for k in keys}))
    # frames move with the corrected fits
    for k in keys:
        geo[k]["frame_g"] = global_frame(geo[k]["fit"], frames_native[k])

    with open(os.path.join(config.BUILD_DIR, year, "registration.json"), "w") as f:
        json.dump({"units": usable, "consensus_av": X, "consensus_st": Y,
                   "seam_content_offsets": [(o, n, round(dx, 1), round(dy, 1), round(w, 2))
                                            for o, n, dx, dy, w in seam_meas]},
                  f, indent=1, default=list)

    # Global side bounds per unit: rim default (frame ∩ line±ext), then seams
    sides = {}
    for key, g in geo.items():
        fx0, fy0, fx1, fy1 = g["frame_g"]
        sides[key] = {
            "left":   max(fx0, X[min(g["avs"])] - ext),
            "right":  min(fx1, X[max(g["avs"])] + ext),
            "top":    max(fy0, Y[min(g["sts"])] - ext),
            "bottom": min(fy1, Y[max(g["sts"])] + ext),
        }
    def darkness(key, axis, gpos, lo, hi):
        """Darkness grid (0..1) of unit `key`: rows sample the seam-parallel
        span [lo,hi] (global, cross axis), columns the candidate cut
        positions in gpos."""
        g = geo[key]
        if axis == "v":
            nat = comp.pw_inv(gpos, g["xkn"], g["xkg"])
            span = comp.pw_inv(np.linspace(lo, hi, 160), g["ykn"], g["ykg"])
            sm = g["gray4"]
            cols = np.clip((nat / 4).astype(int), 0, sm.shape[1] - 1)
            rows = np.clip((span / 4).astype(int), 0, sm.shape[0] - 1)
            return 1.0 - sm[np.ix_(rows, cols)] / 255.0
        nat = comp.pw_inv(gpos, g["ykn"], g["ykg"])
        span = comp.pw_inv(np.linspace(lo, hi, 160), g["xkn"], g["xkg"])
        sm = g["gray4"]
        rows = np.clip((nat / 4).astype(int), 0, sm.shape[0] - 1)
        cols = np.clip((span / 4).astype(int), 0, sm.shape[1] - 1)
        return (1.0 - sm[np.ix_(rows, cols)] / 255.0).T

    def best_cut(axis, center, owner, nbr, flip=False):
        """Cut position in [center+40, center+680] minimizing mean ink AND
        localized ink clusters. Mean darkness alone dilutes a giant street
        numeral over the whole corridor span — a cut can score 'white' while
        slicing straight through '25TH' (observed at 25th/Ave G). The p97 of
        span-locally-averaged darkness makes any glyph cluster on the cut
        line expensive. flip=True mirrors the band to [center-680,
        center-40] for flipped-ownership seams, with the 3x duplicate
        weight moved onto the unit whose label copy must fall beyond the
        cut (the default owner)."""
        ao, so = geo[owner]["avs"], geo[owner]["sts"]
        an, sn = geo[nbr]["avs"], geo[nbr]["sts"]
        if axis == "v":
            lo = Y[max(min(so), min(sn))] + 200
            hi = Y[min(max(so), max(sn))] - 200
        else:
            lo = X[max(min(ao), min(an))] + 200
            hi = X[min(max(ao), max(an))] - 200
        if flip:
            gpos = np.arange(center - 680, center - 39, 4.0)
            w_own, w_nbr = 3.0, 1.0
        else:
            gpos = np.arange(center + 40, center + 681, 4.0)
            # weight the neighbor 3x: its label copies must fall above the
            # cut, or they render as duplicates below it
            w_own, w_nbr = 1.0, 3.0
        go = darkness(owner, axis, gpos, lo, hi)
        grid = w_own * go + w_nbr * darkness(nbr, axis, gpos, lo, hi)
        kk = np.ones(5) / 5
        loc = np.apply_along_axis(np.convolve, 0, grid, kk, "same")
        d = grid.mean(axis=0) + 1.5 * np.percentile(loc, 97, axis=0)
        k = 9
        dsm = np.convolve(d, np.ones(k) / k, mode="same")
        lo_i, hi_i = k, len(dsm) - k
        if flip:
            # the owner renders on the far side of the cut — any owner ink
            # closer to the line than the cut renders as a duplicate label.
            # Whitest-row alone put the cut in the clean paper BELOW 11a's
            # label (v3.2: cut -164, label at ~-300..-190, still doubled).
            # Restrict to strictly beyond the owner's ink cluster nearest
            # the line.
            oloc = np.apply_along_axis(np.convolve, 0, go, kk, "same")
            oprof = np.percentile(oloc, 97, axis=0)
            inked = np.where(oprof > 0.12)[0]
            if len(inked):
                # walk back through the cluster, bridging gaps <= 6 samples
                run_lo = inked[-1]
                for j in reversed(inked[:-1]):
                    if run_lo - j <= 6:
                        run_lo = j
                    else:
                        break
                hi_i = min(hi_i, max(run_lo - 8, lo_i + 1))
        return float(gpos[int(np.argmin(dsm[lo_i:hi_i])) + lo_i])

    # Border-connected scan-junk projections per unit (QC v3-2): a seam cut
    # that reaches past the owner's paper edge renders the owner's scanner
    # rule / backing strip OVER the neighbor's real content (the solid black
    # bar in the 19th St corridor covered 18k px of sheet 7's map ink). The
    # region/native print_end cap cannot see this — it caps at the SCAN
    # extent, junk included. Same border-connectivity criterion as the
    # exterior margin trim: junk touches the scan edge, print never does.
    junk_rows, junk_cols, junk_org = {}, {}, {}
    for key in usable:
        unit = cov.COVERAGE[year][key]
        im = cv2.imread(sheet_path(year, unit["file"]), cv2.IMREAD_COLOR)
        # region-scoped: on multi-panel sheets a full-sheet projection sees
        # the OTHER panel's dark edges and falsely caps seams (the 11a|11b
        # cap re-clipped the Avenue H label the 2040 split had just saved)
        if unit["region"]:
            x0r, y0r, x1r, y1r = unit["region"]
            im = im[y0r:y1r, x0r:x1r]
            junk_org[key] = (x0r, y0r)
        else:
            junk_org[key] = (0, 0)
        sub = im[::4, ::4].astype(np.int16)
        del im
        bad = ((sub.max(axis=2) < 60) |
               ((sub[..., 0] - sub[..., 2]) > 6)).astype(np.uint8)
        bad = cv2.morphologyEx(bad, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        _, lab = cv2.connectedComponents(bad, connectivity=8)
        # seed only from TRUE scan edges: a region border that is interior
        # (a panel divider) must not make ordinary ink 'border-connected'
        nw_, nh_ = ed["native_size"]
        x0r, y0r, x1r, y1r = unit["region"] or (0, 0, nw_, nh_)
        seeds = []
        if y0r <= 0:
            seeds.append(lab[0])
        if y1r >= nh_:
            seeds.append(lab[-1])
        if x0r <= 0:
            seeds.append(lab[:, 0])
        if x1r >= nw_:
            seeds.append(lab[:, -1])
        eid = (np.unique(np.concatenate(seeds)) if seeds
               else np.zeros(0, dtype=lab.dtype))
        bbm = np.isin(lab, eid[eid > 0])
        junk_rows[key] = bbm.any(axis=1)
        junk_cols[key] = bbm.any(axis=0)
        del sub, bad, lab, bbm

    def junk_cap(key, axis, center):
        """Global coordinate of the owner's first border-connected junk
        at/after the seam line, or None."""
        g = geo[key]
        if axis == "v":
            nat = comp.pw_inv([center], g["xkn"], g["xkg"])[0]
            proj, kn, kg = junk_cols[key], g["xkn"], g["xkg"]
            org = junk_org[key][0]
        else:
            nat = comp.pw_inv([center], g["ykn"], g["ykg"])[0]
            proj, kn, kg = junk_rows[key], g["ykn"], g["ykg"]
            org = junk_org[key][1]
        i0 = min(max((int(nat) - org) // 4, 0), len(proj) - 1)
        hits = np.where(proj[i0:])[0]
        if not len(hits):
            return None
        return comp.pw_fwd([(i0 + hits[0]) * 4 - 8 + org], kn, kg)[0]

    prop = {}
    for axis, idx, owner, nbr in cov.neighbors(year):
        if owner not in geo or nbr not in geo:
            continue
        # No frame caps at seams (mapped frame estimates punched holes), and
        # seam sides are ASSIGNED, never min/max-merged with rim defaults —
        # merging let default extents reach past the cut and double-render
        # 150-250 px bands at 50% (grey ghost labels).
        g_own = geo[owner]
        nw, nh = ed["native_size"]
        reg_own = cov.COVERAGE[year][owner]["region"] or (0, 0, nw, nh)
        # Panel pairs with DISJOINT clip_regions (same physical sheet split
        # into units): the clip_regions ARE the boundary. A prop-driven cut
        # maps through two different unit registrations and re-opens the
        # very gap/slice the split placement was tuned to avoid (the v3.2a
        # junk-capped cut pushed 11b's start to 2097, re-beheading the
        # AV. H label).
        c_own = cov.COVERAGE[year][owner].get("clip_region")
        c_nbr = cov.COVERAGE[year][nbr].get("clip_region")
        if c_own and c_nbr:
            dj = ((axis == "v" and (c_own[2] <= c_nbr[0] or c_nbr[2] <= c_own[0]))
                  or (axis == "h" and (c_own[3] <= c_nbr[1] or c_nbr[3] <= c_own[1])))
            if dj:
                log(f"seam {axis}{idx} {owner}|{nbr}: boundary owned by "
                    "disjoint clip_regions; no prop cut")
                continue
        flip = (axis, idx, frozenset({owner, nbr})) in cov.SEAM_FLIPS
        if axis == "v":
            center = X[idx]
            cut = best_cut("v", center, owner, nbr, flip=flip)
            if flip:
                owner_end = max(min(cut, center - 40), center - 680)
                # the neighbor's clip must not rise above its own printed
                # frame: its frame rule + margin would render mid-corridor
                nbr_start = max(owner_end - feather,
                                geo[nbr]["frame_g"][0] + 6)
                log(f"seam v{idx} {owner}|{nbr}: FLIPPED cut at "
                    f"{owner_end - center:+.0f} rel to line")
                prop.setdefault((owner, "right"), []).append(owner_end)
                prop.setdefault((nbr, "left"), []).append(nbr_start)
                continue
            else:
                print_end = comp.pw_fwd([min(reg_own[2], nw)], g_own["xkn"], g_own["xkg"])[0]
                jc = junk_cap(owner, "v", center)
                if jc is not None and jc < print_end:
                    log(f"seam v{idx} {owner}|{nbr}: junk cap {print_end - jc:.0f}px "
                        "inside print extent")
                    print_end = jc
                owner_end = min(max(cut, center + 40), print_end - 4)
            prop.setdefault((owner, "right"), []).append(owner_end)
            prop.setdefault((nbr, "left"), []).append(owner_end - feather)
        else:
            center = Y[idx]
            cut = best_cut("h", center, owner, nbr, flip=flip)
            if flip:
                owner_end = max(min(cut, center - 40), center - 680)
                nbr_start = max(owner_end - feather,
                                geo[nbr]["frame_g"][1] + 6)
                log(f"seam h{idx} {owner}|{nbr}: FLIPPED cut at "
                    f"{owner_end - center:+.0f} rel to line")
                prop.setdefault((owner, "bottom"), []).append(owner_end)
                prop.setdefault((nbr, "top"), []).append(nbr_start)
                continue
            else:
                print_end = comp.pw_fwd([min(reg_own[3], nh)], g_own["ykn"], g_own["ykg"])[0]
                jc = junk_cap(owner, "h", center)
                if jc is not None and jc < print_end:
                    log(f"seam h{idx} {owner}|{nbr}: junk cap {print_end - jc:.0f}px "
                        "inside print extent")
                    print_end = jc
                owner_end = min(max(cut, center + 40), print_end - 4)
            prop.setdefault((owner, "bottom"), []).append(owner_end)
            prop.setdefault((nbr, "top"), []).append(owner_end - feather)

    for (key, side), vals in prop.items():
        if side in ("right", "bottom"):
            sides[key][side] = max(vals)
        else:
            sides[key][side] = min(vals)

    # ---- Retain sheet margins on EXTERIOR sides (v3). A side is exterior
    # when it has no seam and every block-cell just across it is uncovered
    # (map edge or disclosed gap) — extending the clip there can overlap no
    # other unit's content. This keeps the original margin annotations the
    # tight frame crop was discarding: "16TH ST." headers, GALVESTON oval
    # stamps, scale bars. The band is bounded (frame + ~0.28 pitch) and the
    # per-sheet paper-extent trim below keeps scanner borders out.
    covered = set()
    for g2 in geo.values():
        for a in range(min(g2["avs"]), max(g2["avs"])):
            for s in range(min(g2["sts"]), max(g2["sts"])):
                covered.add((a, s))
    margin_g = round(0.28 * ed["pitch_av"])
    ext_sides = {}
    for key, g in geo.items():
        a0k, a1k = min(g["avs"]), max(g["avs"])
        s0k, s1k = min(g["sts"]), max(g["sts"])
        fx0, fy0, fx1, fy1 = g["frame_g"]
        edges = {
            "left":   (fx0 - margin_g, [(a0k - 1, s) for s in range(s0k, s1k)]),
            "right":  (fx1 + margin_g, [(a1k, s) for s in range(s0k, s1k)]),
            "top":    (fy0 - margin_g, [(a, s0k - 1) for a in range(a0k, a1k)]),
            "bottom": (fy1 + margin_g, [(a, s1k) for a in range(a0k, a1k)]),
        }
        for side, (pos, cells) in edges.items():
            if (key, side) not in prop and not any(c in covered for c in cells):
                sides[key][side] = pos
                ext_sides.setdefault(key, set()).add(side)
                log(f"unit {key}: exterior {side} margin retained")

    for key, r in usable.items():
        unit = cov.COVERAGE[year][key]
        g = geo[key]
        sd = sides[key]
        cx0, cx1 = comp.pw_inv([sd["left"], sd["right"]], g["xkn"], g["xkg"])
        cy0, cy1 = comp.pw_inv([sd["top"], sd["bottom"]], g["ykn"], g["ykg"])
        creg = unit.get("clip_region") or unit["region"]
        if creg:
            rx0, ry0, rx1, ry1 = creg
            cx0, cy0 = max(cx0, rx0), max(cy0, ry0)
            cx1, cy1 = min(cx1, rx1), min(cy1, ry1)
        nw, nh = ed["native_size"]
        cx0, cy0 = max(cx0, 0), max(cy0, 0)
        cx1, cy1 = min(cx1, nw), min(cy1, nh)
        img = cv2.imread(sheet_path(year, unit["file"]), cv2.IMREAD_COLOR)
        # Scan-bed trim on exterior-extended sides only (QC v3-1). Dark-row
        # statistics cannot tell margin TEXT from scanner bed — both are
        # dark — and missed partial bands outright. The reliable separator
        # is border-connectivity: bed black and blue-white backing strips
        # always touch the scan's outer edge; genuine margin annotations
        # never do. Clip each extended side just inside the innermost
        # border-connected bad pixel (near-black, or cool: B > R + 6 where
        # paper is warm at R - B ~ +17).
        es = ext_sides.get(key, set())
        if es:
            sub = img[::4, ::4].astype(np.int16)
            bad = ((sub.max(axis=2) < 60) |
                   ((sub[..., 0] - sub[..., 2]) > 6)).astype(np.uint8)
            bad = cv2.morphologyEx(bad, cv2.MORPH_OPEN,
                                   np.ones((3, 3), np.uint8))
            _, lab = cv2.connectedComponents(bad, connectivity=8)
            edge_ids = np.unique(np.concatenate(
                [lab[0], lab[-1], lab[:, 0], lab[:, -1]]))
            bb = np.isin(lab, edge_ids[edge_ids > 0])
            fx0n, fy0n, fx1n, fy1n = [int(v) // 4 for v in frames_native[key]]
            j0, j1 = int(cx0) // 4, max(int(cx0) // 4 + 1, int(cx1) // 4)
            i0, i1 = int(cy0) // 4, max(int(cy0) // 4 + 1, int(cy1) // 4)
            rows_bb = bb[:, j0:j1].any(axis=1)
            cols_bb = bb[i0:i1, :].any(axis=0)
            if "top" in es:
                hits = np.where(rows_bb[:max(fy0n, 0)])[0]
                if len(hits):
                    cy0 = max(cy0, (hits[-1] + 2) * 4)
            if "bottom" in es:
                hits = np.where(rows_bb[min(fy1n, len(rows_bb)):])[0]
                if len(hits):
                    cy1 = min(cy1, (min(fy1n, len(rows_bb)) + hits[0] - 2) * 4)
            if "left" in es:
                hits = np.where(cols_bb[:max(fx0n, 0)])[0]
                if len(hits):
                    cx0 = max(cx0, (hits[-1] + 2) * 4)
            if "right" in es:
                hits = np.where(cols_bb[min(fx1n, len(cols_bb)):])[0]
                if len(hits):
                    cx1 = min(cx1, (min(fx1n, len(cols_bb)) + hits[0] - 2) * 4)
        clip = (cx0, cy0, cx1, cy1)
        xkg_c = [x - ox for x in g["xkg"]]
        ykg_c = [y - oy for y in g["ykg"]]
        sh = measured.get(key, {}).get("shear", (0.0, 0.0))
        gains = comp.channel_gains(tones[key], target_tone)
        # highlight-safe ceiling: never drive any channel into hard clip
        # (QC pass 2: sheet 9's gain clipped green over 1.62% of its area
        # while the source had zero clipped pixels — irreversible loss)
        p999 = np.percentile(img[::8, ::8].reshape(-1, 3), 99.9, axis=0)
        s = min(1.0, float(254.0 / np.max(p999 * gains)))
        if s < 0.999:
            log(f"unit {key}: gain scaled x{s:.3f} to protect highlights")
        gains = gains * s
        comp.warp_sheet_piecewise(canvas, weight, img, g["xkn"], xkg_c,
                                  g["ykn"], ykg_c, clip, gains, feather,
                                  shear=tuple(sh),
                                  shear_pivot=(float(np.mean(g["xkn"])),
                                               float(np.mean(g["ykn"]))))
        log(f"unit {key}: composited clip={[round(float(v)) for v in clip]} gains={np.round(gains,3)}")
        del img

    out = os.path.join(config.BUILD_DIR, year, f"galveston_{year}_composite.tif")
    comp.save_tiff(canvas, out)
    cov_pct = 100.0 * (weight > 0).mean()
    log(f"{year}: wrote {out} ({os.path.getsize(out)>>20} MB), coverage {cov_pct:.1f}%")
    cv2.imwrite(os.path.join(config.BUILD_DIR, year, "coverage_mask.png"),
                (weight > 0).astype(np.uint8) * 255)
    return out


def main():
    year = sys.argv[1]
    registration = register_edition(year)
    blockers = {k: r["status"] for k, r in registration.items() if r["status"] != "ok"}
    if blockers:
        log(f"NOT compositing yet — unresolved units: {blockers}")
        return 1
    composite_edition(year, registration)
    return 0


if __name__ == "__main__":
    sys.exit(main())
