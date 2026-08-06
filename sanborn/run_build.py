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
    pad = round(0.25 * ed["pitch_av"])
    width = round((a1 - a0) * ed["pitch_av"]) + 2 * pad
    height = round((s1 - s0) * ed["pitch_st"]) + 2 * pad
    ox = a0 * ed["pitch_av"] - pad
    oy = (s0 - config.STREET_ORIGIN) * ed["pitch_st"] - pad
    log(f"{year} canvas {width} x {height} ({width*height/1e6:.0f} MP)")

    canvas, weight = comp.new_canvas(width, height, ed["paper_bgr"])

    native_w = ed["native_size"][0]
    shift = config.CLIP_SHIFT_3400 * native_w / config.DETECT_WIDTH
    feather = round(config.FEATHER_3400 * native_w / config.DETECT_WIDTH)
    ext = shift

    usable = {k: r for k, r in registration.items() if r.get("status") == "ok"}

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
    CORRIDOR_W = 460.0
    frames_native = {}
    corrected = {}
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

        def fix_lo(d, f):
            return 2 * d - f - CORRIDOR_W / 2 if f > d - CORRIDOR_W / 2 else d

        def fix_hi(d, f):
            return 2 * d - f + CORRIDOR_W / 2 if f < d + CORRIDOR_W / 2 else d

        v2 = list(v)
        h2 = list(h)
        v2[0] = fix_lo(v[0], fr[0])
        v2[-1] = fix_hi(v[-1], fr[2])
        h2[0] = fix_lo(h[0], fr[1])
        h2[-1] = fix_hi(h[-1], fr[3])
        moved = {i: round(b - a, 1) for i, (a, b) in enumerate(zip(v + h, v2 + h2)) if abs(b - a) > 5}
        if moved:
            log(f"unit {key}: edge-knot corridor correction {moved}")
        corrected[key] = (v2, h2)

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
        frame = frames_native[key]
        # Piecewise-linear knots: every corrected line maps EXACTLY to its
        # consensus global position, so neighbors agree at every shared line.
        xkn, xkg = v, [X[a] for a in avs]
        ykn, ykg = h, [Y[s] for s in sts]
        fx0, fx1 = comp.pw_fwd([frame[0], frame[2]], xkn, xkg)
        fy0, fy1 = comp.pw_fwd([frame[1], frame[3]], ykn, ykg)
        img_s = cv2.imread(sheet_path(year, unit["file"]), cv2.IMREAD_GRAYSCALE)
        small = cv2.resize(img_s, (img_s.shape[1] // 4, img_s.shape[0] // 4),
                           interpolation=cv2.INTER_AREA)
        del img_s
        geo[key] = {"fit": fit, "gv": v, "gh": h,
                    "xkn": xkn, "xkg": xkg, "ykn": ykn, "ykg": ykg,
                    "frame_g": (fx0, fy0, fx1, fy1), "avs": avs, "sts": sts,
                    "gray4": small}
        log(f"unit {key}: joint sx={sx:.4f} sy={sy:.4f} (affine gate only; warp is piecewise-exact)")

    with open(os.path.join(config.BUILD_DIR, year, "registration.json"), "w") as f:
        json.dump({"units": usable, "consensus_av": X, "consensus_st": Y},
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
        """Mean darkness (0..1) of unit `key` along the seam-parallel span
        [lo,hi] (global, cross axis) at each global position in gpos."""
        g = geo[key]
        if axis == "v":
            nat = comp.pw_inv(gpos, g["xkn"], g["xkg"])
            span = comp.pw_inv(np.linspace(lo, hi, 160), g["ykn"], g["ykg"])
            sm = g["gray4"]
            cols = np.clip((nat / 4).astype(int), 0, sm.shape[1] - 1)
            rows = np.clip((span / 4).astype(int), 0, sm.shape[0] - 1)
            return 1.0 - sm[np.ix_(rows, cols)].mean(axis=0) / 255.0
        nat = comp.pw_inv(gpos, g["ykn"], g["ykg"])
        span = comp.pw_inv(np.linspace(lo, hi, 160), g["xkn"], g["xkg"])
        sm = g["gray4"]
        rows = np.clip((nat / 4).astype(int), 0, sm.shape[0] - 1)
        cols = np.clip((span / 4).astype(int), 0, sm.shape[1] - 1)
        return 1.0 - sm[np.ix_(rows, cols)].mean(axis=1) / 255.0

    def best_cut(axis, center, owner, nbr):
        """Whitest cut position in [center+90, center+300]: avoids slicing
        street labels (which can extend far past the centerline) by cutting
        through the empty paper between label bottom and block faces."""
        ao, so = geo[owner]["avs"], geo[owner]["sts"]
        an, sn = geo[nbr]["avs"], geo[nbr]["sts"]
        if axis == "v":
            lo = Y[max(min(so), min(sn))] + 200
            hi = Y[min(max(so), max(sn))] - 200
        else:
            lo = X[max(min(ao), min(an))] + 200
            hi = X[min(max(ao), max(an))] - 200
        gpos = np.arange(center + 90, center + 301, 4.0)
        d = darkness(owner, axis, gpos, lo, hi) + darkness(nbr, axis, gpos, lo, hi)
        k = 9
        dsm = np.convolve(d, np.ones(k) / k, mode="same")
        return float(gpos[int(np.argmin(dsm[k:-k])) + k])

    for axis, idx, owner, nbr in cov.neighbors(year):
        if owner not in geo or nbr not in geo:
            continue
        if axis == "v":
            center = X[idx]
            cut = best_cut("v", center, owner, nbr)
            bound = min(geo[owner]["frame_g"][2], cut)
            nbr_lo = geo[nbr]["frame_g"][0]
            if nbr_lo > bound + feather:
                log(f"seam v{idx} {owner}|{nbr}: print gap {nbr_lo-bound:.0f}px (frames do not tile)")
            sides[owner]["right"] = min(max(sides[owner]["right"], bound + feather),
                                        geo[owner]["frame_g"][2])
            sides[nbr]["left"] = max(min(sides[nbr]["left"], bound - feather),
                                     geo[nbr]["frame_g"][0])
        else:
            center = Y[idx]
            cut = best_cut("h", center, owner, nbr)
            bound = min(geo[owner]["frame_g"][3], cut)
            nbr_lo = geo[nbr]["frame_g"][1]
            if nbr_lo > bound + feather:
                log(f"seam h{idx} {owner}|{nbr}: print gap {nbr_lo-bound:.0f}px (frames do not tile)")
            sides[owner]["bottom"] = min(max(sides[owner]["bottom"], bound + feather),
                                         geo[owner]["frame_g"][3])
            sides[nbr]["top"] = max(min(sides[nbr]["top"], bound - feather),
                                    geo[nbr]["frame_g"][1])

    # Tonal reference (panel region only)
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

    for key, r in usable.items():
        unit = cov.COVERAGE[year][key]
        g = geo[key]
        sd = sides[key]
        cx0, cx1 = comp.pw_inv([sd["left"], sd["right"]], g["xkn"], g["xkg"])
        cy0, cy1 = comp.pw_inv([sd["top"], sd["bottom"]], g["ykn"], g["ykg"])
        if unit["region"]:
            rx0, ry0, rx1, ry1 = unit["region"]
            cx0, cy0 = max(cx0, rx0), max(cy0, ry0)
            cx1, cy1 = min(cx1, rx1), min(cy1, ry1)
        clip = (cx0, cy0, cx1, cy1)
        gains = comp.channel_gains(tones[key], target_tone)
        # knots shifted into canvas coordinates (global minus canvas origin)
        xkg_c = [x - ox for x in g["xkg"]]
        ykg_c = [y - oy for y in g["ykg"]]
        img = cv2.imread(sheet_path(year, unit["file"]), cv2.IMREAD_COLOR)
        # limit contribution to the clip: black out outside via mask by
        # passing the clip through to the warp (it derives ROI from clip)
        comp.warp_sheet_piecewise(canvas, weight, img, g["xkn"], xkg_c,
                                  g["ykn"], ykg_c, clip, gains, feather)
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
