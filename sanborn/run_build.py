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


def _align_windows(lines, idents, pitch, tol=0.02):
    """All contiguous detected-line/identity alignments within scale tol,
    as (pairs, scale_dev, mean_resid). Used by the global-consistency pass
    when a sheet shows more bright corridors than it has identities."""
    lines = sorted(lines)
    m = min(len(lines), len(idents))
    out = []
    if m < 2:
        return out
    for dl in range(len(lines) - m + 1):
        for de in range(len(idents) - m + 1):
            src = np.array(lines[dl:dl + m])
            dst = np.array(idents[de:de + m], dtype=float) * pitch
            A = np.vstack([src, np.ones_like(src)]).T
            (s, t), *_ = np.linalg.lstsq(A, dst, rcond=None)
            dev = abs(s - 1.0)
            if dev > tol:
                continue
            resid = float(np.abs(dst - (s * src + t)).mean())
            out.append((list(zip(src.tolist(), idents[de:de + m])), dev, resid))
    return out


def _align_axis(lines, idents, pitch, center, tol=0.02):
    """Match sorted detected lines to identity slots. Equal counts zip
    directly. Otherwise slide the shorter list along the longer (comb slots
    can add a margin line or drop an edge line) and keep the contiguous
    alignment whose LSQ scale is nearest 1.0, tie-broken by how close the
    window centroid sits to the panel center (a one-slot shift moves the
    centroid ~pitch/2, the true window is near-centered); reject if the
    best still deviates more than tol. Returns (pairs, err)."""
    lines = sorted(lines)
    n_d, n_e = len(lines), len(idents)
    if n_e < 2:
        return None, f"axis needs >=2 identities to align (have {n_e})"
    if n_d == n_e:
        return list(zip(lines, idents)), None
    if n_d < 2:
        return None, f"only {n_d} detected lines for {n_e} identities"
    m = min(n_d, n_e)
    best = None
    for dl in range(n_d - m + 1):
        for de in range(n_e - m + 1):
            src = np.array(lines[dl : dl + m])
            dst = np.array(idents[de : de + m], dtype=float) * pitch
            A = np.vstack([src, np.ones_like(src)]).T
            (s, t), *_ = np.linalg.lstsq(A, dst, rcond=None)
            resid = float(np.abs(dst - (s * src + t)).mean())
            score = (round(abs(s - 1.0), 3), abs(float(src.mean()) - center), resid)
            if best is None or score < best[0]:
                best = (score, list(zip(src.tolist(), idents[de : de + m])))
    (sdev, cdist, resid), pairs = best
    if sdev > tol:
        return None, (
            f"no alignment of {n_d} detected to {n_e} expected within "
            f"scale tol (best dev {sdev:.3f}, resid {resid:.0f})"
        )
    return pairs, None


def assign_identities(detected, year, key):
    avs, sts = cov.expected_detect_lines(year, key)
    ed = config.EDITIONS[year]
    v, h = detected["v_lines_native"], detected["h_lines_native"]
    region = detected.get("panel_region")
    if region:
        cx, cy = (region[0] + region[2]) / 2, (region[1] + region[3]) / 2
    else:
        w, hh = ed["native_size"]
        cx, cy = w / 2, hh / 2
    if len(avs) == 1:
        # single-corridor axis (wharf hybrids: Avenue A only). Detection ran
        # inside the unit's region, so the corridor nearest the region
        # center is the labeled one; scale stays locked downstream.
        near = min(v, key=lambda x: abs(x - cx)) if v else None
        if near is None or abs(near - cx) > ed["pitch_av"] * 0.7:
            vp, verr = None, "no detected line near the single-avenue anchor"
        else:
            vp, verr = [(near, avs[0])], None
    else:
        vp, verr = _align_axis(v, avs, ed["pitch_av"], cx)
    hp, herr = _align_axis(h, sts, ed["pitch_st"], cy)
    if verr or herr:
        return None, (
            f"detected {len(v)}v/{len(h)}h vs expected {len(avs)} named "
            f"avenues/{len(sts)} streets — " + "; ".join(filter(None, [verr, herr]))
        )
    controls = [
        {"axis": "x", "native": x, "identity": a} for x, a in vp
    ] + [
        {"axis": "y", "native": y, "identity": s} for y, s in hp
    ]
    # axes where a window had to be chosen — reconcile_windows arbitrates
    ambiguous = set()
    if len(v) > len(avs) > 1:
        ambiguous.add("x")
    if len(h) > len(sts) > 1:
        ambiguous.add("y")
    return controls, None, ambiguous


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
        dreg = unit.get("detect_region") or unit["region"]
        want_v, want_h = cov.expected_detect_lines(year, key)
        det = reg.detect_sheet_grid(path, region=dreg,
                                    want_v=len(want_v), want_h=len(want_h))
        det["panel_region"] = dreg
        # manual corridor anchors (CoM-measured, label-verified): where the
        # comb locks onto non-corridor brightness, its output is replaced
        for akey, dkey in (("v_anchors", "v_lines_native"),
                           ("h_anchors", "h_lines_native")):
            if unit.get(akey):
                det[dkey] = [x for _, x in
                             sorted((int(s), x) for s, x in unit[akey].items())]
        bad, devs = spacing_gate(det, year)
        if bad:
            results[key] = {"status": "off-scale", "spacing_dev": devs,
                            "note": "median interior spacing deviates >6% — excluded, disclosed"}
            log(f"unit {key}: OFF-SCALE {devs} — excluded")
            continue
        controls, err, ambiguous = assign_identities(det, year, key)
        if err:
            results[key] = {"status": "needs-review", "detail": err, "detected": det}
            log(f"unit {key}: NEEDS REVIEW — {err}")
            continue
        # Per-line overrides: a sheet whose OUTERMOST corridor is cut by its
        # own paper edge shows only part of that corridor, and the comb
        # settles on the block frontage line bounding it instead of the
        # corridor centre. On the downtown sheets along Avenue A that put
        # the avenue centreline on the block frontage, so the buildings
        # started at the centreline and the east half of Water Street
        # vanished under them. Values are frontage minus the half-corridor
        # (122 px of the 245 px corridor measured on sheet 13).
        for axis, fixes in (unit.get("line_overrides") or {}).items():
            for ident, native in fixes.items():
                for c in controls:
                    if c["axis"] == axis and c["identity"] == int(ident):
                        log(f"unit {key}: {axis}-line {ident} override "
                            f"{c['native']:.0f} -> {native}")
                        c["native"] = float(native)
        # Drop a control whose corridor is CUT by the sheet's own paper edge.
        # The comb then has only part of the corridor to work with and settles
        # on the block frontage bounding it; substituting a measured centre is
        # no better, because the measurement picks a different feature on each
        # sheet (Avenue A came out -73/-139/-37 px on sheets 11/13/15), and
        # those differences displace whole rows against each other — the
        # 48-85 px eastward step across 24th Street. Fitting on the sheet's
        # interior lines only is both simpler and better conditioned.
        for axis, idents in (unit.get("drop_lines") or {}).items():
            before = len(controls)
            controls = [c for c in controls
                        if not (c["axis"] == axis and c["identity"] in idents)]
            if len(controls) != before:
                log(f"unit {key}: dropped {axis}-line(s) {idents} "
                    "(corridor cut by the paper edge; fitting on interior lines)")
        fit = fit_sheet(controls, year)
        status = "ok" if all(fit[f"flag_{a}"] in ("OK", "WARN") for a in "xy") else "scale-fail"
        results[key] = {"status": status, "fit": fit, "detected": det,
                        "controls": controls,
                        "window_ambiguous": sorted(ambiguous)}
        log(f"unit {key}: sx={fit['sx']:.4f} {fit['mode_x']} ({fit['flag_x']}) "
            f"resid={fit['resid_x']} | sy={fit['sy']:.4f} {fit['mode_y']} "
            f"({fit['flag_y']}) resid={fit['resid_y']}")
    reconcile_windows(results, year)
    outdir = os.path.join(config.BUILD_DIR, year)
    os.makedirs(outdir, exist_ok=True)
    with open(os.path.join(outdir, "registration.json"), "w") as f:
        json.dump(results, f, indent=1, default=list)
    return results


def reconcile_windows(results, year):
    """Global-consistency pass over units where the detected-line count
    exceeded the identity count, so alignment had to choose a WINDOW.

    Local cues cannot make that choice: every window fits at scale 1.000
    (the spacings are identical), so the pick rests on a weak centroid tie-
    break — which put sheet 75 one corridor too far east and sheet 76 one
    too far west (label fleet, group 5). Globally it is easy: units whose
    counts matched had no choice to make, and their fits agree on where
    each slot sits in global coordinates. Re-pick each ambiguous window as
    the one landing closest to that consensus.
    """
    ed = config.EDITIONS[year]
    ok = {k: r for k, r in results.items() if r.get("status") == "ok"}
    cons = {"x": {}, "y": {}}
    for key, r in ok.items():
        if r.get("window_ambiguous"):
            continue
        for axis in "xy":
            s, t = r["fit"][f"s{axis}"], r["fit"][f"t{axis}"]
            for c in r["controls"]:
                if c["axis"] == axis:
                    cons[axis].setdefault(c["identity"], []).append(
                        s * c["native"] + t)
    med = {a: {i: float(np.median(v)) for i, v in cons[a].items()} for a in "xy"}

    for key, r in ok.items():
        if not r.get("window_ambiguous"):
            continue
        avs, sts = cov.expected_detect_lines(year, key)
        det, changed = r["detected"], False
        for axis, idents, dkey, pitch, origin in (
                ("x", avs, "v_lines_native", ed["pitch_av"], 0),
                ("y", sts, "h_lines_native", ed["pitch_st"],
                 config.STREET_ORIGIN)):
            if axis not in r["window_ambiguous"]:
                continue
            best = None
            for pairs, dev, resid in _align_windows(det[dkey], idents, pitch):
                src = np.array([p for p, _ in pairs])
                dst = np.array([(i - origin) * pitch for _, i in pairs])
                A = np.vstack([src, np.ones_like(src)]).T
                (s, t), *_ = np.linalg.lstsq(A, dst, rcond=None)
                errs = [abs(s * p + t - med[axis][i])
                        for p, i in pairs if i in med[axis]]
                if not errs:
                    continue
                score = float(np.mean(errs))
                if best is None or score < best[0]:
                    best = (score, pairs)
            if best is None:
                log(f"unit {key}: axis {axis} window ambiguous and no "
                    "consensus slot to arbitrate — keeping local pick")
                continue
            score, pairs = best
            cur = sorted(c["native"] for c in r["controls"] if c["axis"] == axis)
            new = sorted(p for p, _ in pairs)
            if cur != new:
                changed = True
                log(f"unit {key}: axis {axis} window re-picked against the "
                    f"global grid (mean |err| {score:.0f} px): "
                    f"{[round(v) for v in cur]} -> {[round(v) for v in new]}")
            r["controls"] = [c for c in r["controls"] if c["axis"] != axis] + [
                {"axis": axis, "native": p, "identity": i} for p, i in pairs]
        if changed:
            r["fit"] = fit_sheet(r["controls"], year)


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
    # pad must fit whatever the units render outside their grid lines. The
    # 0.40-pitch default suits inland sheets; wharf sheets carry ~3000 px of
    # piers and bay west of Avenue A, so those builds set CANVAS_PAD.
    pad = getattr(config, "CANVAS_PAD", None) or round(0.40 * ed["pitch_av"])
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
    paper_native = {}
    corrected = {}
    corr_path = os.path.join(config.BUILD_DIR, year, "edge_corrections.json")
    measured = json.load(open(corr_path)) if os.path.exists(corr_path) else {}
    md_path = os.path.join(config.BUILD_DIR, year, "manual_knot_deltas.json")
    manual_deltas = json.load(open(md_path)) if os.path.exists(md_path) else {}
    if manual_deltas:
        log(f"applying manual knot deltas for units {list(manual_deltas)}")
    if measured:
        log(f"applying measured edge corrections from {corr_path}")
    line_ids = {}
    for key, r in usable.items():
        unit = cov.COVERAGE[year][key]
        # identity-matched control pairs, NOT raw detections: units whose
        # alignment used a window/subset (wharf hybrids, extra bay-side
        # corridors) carry detections with no identity, and zipping them
        # against expected_lines shifts every knot by a corridor
        ctr = sorted((c["native"], c["identity"]) for c in r["controls"]
                     if c["axis"] == "x")
        cth = sorted((c["native"], c["identity"]) for c in r["controls"]
                     if c["axis"] == "y")
        v = [p for p, _ in ctr]
        h = [p for p, _ in cth]
        line_ids[key] = ([i for _, i in ctr], [i for _, i in cth])
        img = cv2.imread(sheet_path(year, unit["file"]), cv2.IMREAD_COLOR)
        img01 = img.astype(np.float32) / 255.0
        fr = comp.frame_bounds(img01, v, h, region=unit["region"])
        pb = comp.paper_bounds(img)
        del img, img01
        frames_native[key] = fr
        paper_native[key] = pb
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
            idents = line_ids[key][0] if axis == "v" else line_ids[key][1]
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
    # fill consensus positions for identities inside some unit's extent but
    # observed by no unit (subset-aligned corridors): interpolate on the
    # known consensus, which already carries the shared non-uniformity
    def fill_grid(G, pitch, origin, all_ids):
        known = sorted(G)
        for i in sorted(all_ids):
            if i not in G:
                G[i] = float(np.interp(i, known, [G[k] for k in known]))
                if i < known[0] or i > known[-1]:
                    G[i] = (i - origin) * pitch  # outside: uniform
    ids_v, ids_h = set(), set()
    for key in usable:
        a, s = cov.expected_lines(year, key)
        ids_v |= set(a)
        ids_h |= set(s)
    fill_grid(X, ed["pitch_av"], 0, ids_v)
    fill_grid(Y, ed["pitch_st"], config.STREET_ORIGIN, ids_h)
    log("grid avenue offsets from uniform: " +
        str({a: round(X[a] - a * ed["pitch_av"]) for a in sorted(X)}))
    log("grid street offsets from uniform: " +
        str({s: round(Y[s] - (s - config.STREET_ORIGIN) * ed["pitch_st"]) for s in sorted(Y)}))

    geo = {}
    for key, r in usable.items():
        unit = cov.COVERAGE[year][key]
        avs, sts = cov.expected_lines(year, key)
        vids, hids = line_ids[key]
        v, h = corrected[key]
        sx, tx = fx[key]
        sy, ty = fy[key]
        seam_res_x = [round(X[a] - (sx * p + tx), 1) for a, p in zip(vids, v)]
        seam_res_y = [round(Y[s] - (sy * p + ty), 1) for s, p in zip(hids, h)]
        for name, s in (("sx", sx), ("sy", sy)):
            if abs(s - 1.0) > config.SCALE_FAIL:
                log(f"unit {key}: joint fit {name}={s:.4f} exceeds ±2% — check line identity")
        fit = {"sx": sx, "tx": tx, "sy": sy, "ty": ty}
        r["fit_consensus"] = {**fit, "line_resid_x": seam_res_x, "line_resid_y": seam_res_y}
        r["knots"] = {"xkn": list(map(float, v)), "xkg": [float(X[a]) for a in vids],
                      "ykn": list(map(float, h)), "ykg": [float(Y[s]) for s in hids]}
        frame = frames_native[key]
        img_s = cv2.imread(sheet_path(year, unit["file"]), cv2.IMREAD_GRAYSCALE)
        small = cv2.resize(img_s, (img_s.shape[1] // 4, img_s.shape[0] // 4),
                           interpolation=cv2.INTER_AREA)
        del img_s
        xkn, xkg = list(v), [X[a] for a in vids]
        ykn, ykg = list(h), [Y[s] for s in hids]
        # piecewise mapping needs >=2 knots per axis; a single-corridor axis
        # (wharf hybrids) extends affinely at the joint-fit scale
        if len(xkn) < 2:
            xkn = xkn + [xkn[0] + ed["pitch_av"]]
            xkg = xkg + [xkg[0] + ed["pitch_av"] * sx]
        if len(ykn) < 2:
            ykn = ykn + [ykn[0] + ed["pitch_st"]]
            ykg = ykg + [ykg[0] + ed["pitch_st"] * sy]
        fx0, fx1 = comp.pw_fwd([frame[0], frame[2]], xkn, xkg)
        fy0, fy1 = comp.pw_fwd([frame[1], frame[3]], ykn, ykg)
        pnat = paper_native[key]
        px0, px1 = comp.pw_fwd([pnat[0], pnat[2]], xkn, xkg)
        py0, py1 = comp.pw_fwd([pnat[1], pnat[3]], ykn, ykg)
        geo[key] = {"fit": fit, "gv": v, "gh": h,
                    "paper_n": pnat,
                    "paper_g": (float(px0), float(py0), float(px1), float(py1)),
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
        # 1885 sheets ABUT — each draws different ground at the boundary, so
        # cross-sheet correlation is meaningless there and the 0.55 gate kept
        # it out. 1899 sheets OVERLAP by hundreds of px, drawing the same
        # street twice, so the correlation is real and is the only thing that
        # corrects ±40 px of line-detection noise. With the gate left at 0.55
        # not one seam qualified: seam_content_offsets came out empty and every
        # translation correction was zero, which is why rails stepped up to
        # +30 px across Avenue A and the rows stepped 48-85 px across 24th.
        gate = ed.get("seam_corr_gate", 0.55)
        log(f"seam {axis}{idx} {owner}|{nbr}: corr resp={resp:.2f} "
            f"offset ({dx*gxs:+.0f},{dy*gys:+.0f})px")
        if resp > gate and abs(dx * gxs) < 200 and abs(dy * gys) < 200:
            seam_meas.append((owner, nbr, dx * gxs, dy * gys, resp))

    # ---- Ground-truth landmark measurements (the repair path). The
    # phase-correlation above yields nothing usable on 1899 data (responses
    # 0.01-0.26, offsets mutually inconsistent by hundreds of px), so the
    # translation solver otherwise runs empty and the map rests on line
    # detection alone — which the landmark gate showed carries RIGID
    # per-pair offsets up to ~208 px. Landmarks are the same physical
    # object located on both sheets of a pair by reading the scans;
    # mapping each through its sheet's knots measures the pair's true
    # content offset directly. Features flagged schematic (wharf sheets'
    # outline-only east side, drawings disagreeing up to ~100 px) get 0.25
    # weight: too noisy to gate on, but they are the only link tying the
    # wharf trio to the downtown component — dropping them entirely would
    # let the two float apart.
    lm_fix = None
    if getattr(config, "LANDMARKS_PATH", None):
        # Solve per-sheet (tx, ty, sx, sy) from per-feature equations, with
        # scales HARD-BOUNDED to ±1% — the plausibility the spacing gates
        # established. Unbounded, the solver wants ±7% x-scale: it uses the
        # scale freedom to soak up drawing scatter and the wharf sheets'
        # schematic disagreement, visibly distorting building proportions
        # for a fake improvement in the numbers. Bounded, the worst
        # surveyed-pair mean comes out ~14 px vs ~36 for pure translations
        # — near the floor the drawings' own inconsistency permits
        # (loop-closure sums around 4-cycles run 16-35 px).
        # Rotation would help some pairs but cannot be expressed in the
        # separable piecewise warp; per-axis affine can.
        from scipy.optimize import lsq_linear
        lm = json.load(open(config.LANDMARKS_PATH))
        lkeys = sorted({f["sheet_a"] for f in lm["features"]}
                       | {f["sheet_b"] for f in lm["features"]})
        lkeys = [k for k in lkeys if k in geo]
        lki = {k: i for i, k in enumerate(lkeys)}
        pts = {k: [] for k in lkeys}
        lfeats = []
        jfeats = []
        for f in lm["features"]:
            a, b = f["sheet_a"], f["sheet_b"]
            if a not in geo or b not in geo:
                continue
            ga_, gb_ = geo[a], geo[b]
            pa = (comp.pw_fwd([f["a_xy"][0]], ga_["xkn"], ga_["xkg"])[0],
                  comp.pw_fwd([f["a_xy"][1]], ga_["ykn"], ga_["ykg"])[0])
            pb = (comp.pw_fwd([f["b_xy"][0]], gb_["xkn"], gb_["xkg"])[0],
                  comp.pw_fwd([f["b_xy"][1]], gb_["ykn"], gb_["ykg"])[0])
            if f.get("junction"):
                # Junction street furniture (pipes/hydrants drawn in the
                # Avenue A corridor itself) is visually binding, but letting
                # it pull inside the network solve drags the downtown sheets
                # toward the wharf's schematic geometry (measured: median
                # 23.5 -> 27.4 px, 11|12 dy -8 -> -30). Held out here; used
                # after the solve to place the wharf GROUP rigidly.
                jfeats.append((a, b, pa, pb, f.get("weight", 1.0)))
                continue
            w = 0.25 if f.get("schematic") else 1.0
            lfeats.append((a, b, pa, pb, w))
            pts[a].append(pa)
            pts[b].append(pb)
        cent = {k: (float(np.mean([p[0] for p in pts[k]])),
                    float(np.mean([p[1] for p in pts[k]]))) for k in lkeys}
        nlk = len(lkeys)
        # Iterate to convergence: the gauge-fixing zero prior on
        # translations shrinks a 150 px correction by ~10-20 px on the
        # first pass (its cost is proportional to the total translation);
        # re-solving on the residuals makes the prior's bite vanish —
        # by round 3 corrections are sub-px. Scales are bounded to the
        # TOTAL ±1% across rounds, and everything composes about the
        # fixed first-round centroids.
        tot = {k: {"tx": 0.0, "ty": 0.0, "sx": 0.0, "sy": 0.0} for k in lkeys}
        cur = [(a, b, list(pa), list(pb), w) for a, b, pa, pb, w in lfeats]
        for _round in range(3):
            rows, rhs, wts = [], [], []
            for a, b, pa, pb, w in cur:
                for axi in (0, 1):
                    v = np.zeros(4 * nlk)
                    v[4 * lki[b] + axi] = 1.0
                    v[4 * lki[b] + 2 + axi] = pb[axi] - cent[b][axi]
                    v[4 * lki[a] + axi] = -1.0
                    v[4 * lki[a] + 2 + axi] = -(pa[axi] - cent[a][axi])
                    rows.append(v)
                    rhs.append(-(pb[axi] - pa[axi]))
                    wts.append(w)
            for k in lkeys:   # weak zero prior fixes the gauge
                for axi in (0, 1):
                    v = np.zeros(4 * nlk)
                    v[4 * lki[k] + axi] = 1.0
                    rows.append(v)
                    rhs.append(0.0)
                    wts.append(0.05)
            Aw = np.array(rows) * np.sqrt(np.array(wts))[:, None]
            bw = np.array(rhs) * np.sqrt(np.array(wts))
            lob = np.full(4 * nlk, -np.inf)
            hib = np.full(4 * nlk, np.inf)
            for k, i in lki.items():
                # Wharf sheets: rigid (translation only). Their only
                # surveyed couplings are wharf|wharf pairs that translations
                # already satisfy to ±6 px; letting the schematic Avenue A
                # couplings push scale onto them distorted 07|06 by 19 px
                # as a side effect (Δsx of 1.7% over a ~1000 px lever).
                smax = 1e-9 if k in ("06", "07", "08") else 0.01
                lob[4 * i + 2] = min(-smax - tot[k]["sx"], -1e-9)
                hib[4 * i + 2] = max(smax - tot[k]["sx"], 1e-9)
                lob[4 * i + 3] = min(-smax - tot[k]["sy"], -1e-9)
                hib[4 * i + 3] = max(smax - tot[k]["sy"], 1e-9)
            sol = lsq_linear(Aw, bw, bounds=(lob, hib)).x
            step = 0.0
            for k, i in lki.items():
                t = tot[k]
                dtx, dty = float(sol[4 * i]), float(sol[4 * i + 1])
                dsx, dsy = float(sol[4 * i + 2]), float(sol[4 * i + 3])
                # compose about the fixed centroid
                t["tx"] = (1 + dsx) * t["tx"] + dtx
                t["ty"] = (1 + dsy) * t["ty"] + dty
                t["sx"] = (1 + dsx) * (1 + t["sx"]) - 1
                t["sy"] = (1 + dsy) * (1 + t["sy"]) - 1
                step = max(step, abs(dtx), abs(dty))
            for j, (a, b, pa, pb, w) in enumerate(cur):
                for p, k in ((pa, a), (pb, b)):
                    i = lki[k]
                    p[0] = cent[k][0] + (1 + sol[4*i+2]) * (p[0] - cent[k][0]) + sol[4*i]
                    p[1] = cent[k][1] + (1 + sol[4*i+3]) * (p[1] - cent[k][1]) + sol[4*i+1]
            log(f"landmark solve round {_round+1}: max step {step:.1f}px")
            if step < 0.5:
                break
        if jfeats:
            # Rigid wharf-group placement from the junction street furniture.
            # The downtown survey is authoritative east of Avenue A, so the
            # whole wharf trio moves by ONE common translation — the weighted
            # mean of (downtown - wharf) across the junction features. A
            # common shift cancels in every wharf|wharf pair, so 07|06 and
            # 08|07 keep their ±6 px; only the wharf's placement against
            # downtown changes, which is exactly the visible corridor jog.
            WHARF = ("06", "07", "08")

            def _jmap(k, p):
                t = tot[k]
                return (cent[k][0] + (1 + t["sx"]) * (p[0] - cent[k][0]) + t["tx"],
                        cent[k][1] + (1 + t["sy"]) * (p[1] - cent[k][1]) + t["ty"])

            num = np.zeros(2)
            den = 0.0
            jlog = []
            for a, b, pa, pb, w in jfeats:
                qa, qb = _jmap(a, pa), _jmap(b, pb)
                if a in WHARF:
                    d = (qb[0] - qa[0], qb[1] - qa[1])
                else:
                    d = (qa[0] - qb[0], qa[1] - qb[1])
                jlog.append((a, b, d, w))
                num += w * np.asarray(d)
                den += w
            shift = num / den
            for k in WHARF:
                if k in tot:
                    tot[k]["tx"] += float(shift[0])
                    tot[k]["ty"] += float(shift[1])
            log(f"junction wharf-group shift ({shift[0]:+.1f},{shift[1]:+.1f})px "
                f"from {len(jfeats)} street-furniture features")
            for a, b, d, w in jlog:
                log(f"  junction {a}|{b}: measured ({d[0]:+.1f},{d[1]:+.1f}) w={w} "
                    f"-> residual ({d[0]-shift[0]:+.1f},{d[1]-shift[1]:+.1f})")
            # Zero the wharf-internal pair MEANS. The network solve leaves
            # ~7 px of mean on 07|06 / 08|07 because the 0.25-weight
            # schematic couplings tug 06 and 08 toward downtown against
            # their own surveyed pairs — visible as a uniform step in pier
            # edges, slip water and rails at the wharf seams. 07 stays the
            # anchor; 06 and 08 take the residual. Only surveyed (w=1.0)
            # wharf|wharf features are used; scatter (±4 px) remains.
            for pa_, pb_ in (("07", "06"), ("08", "07")):
                ds = []
                for a, b, pa, pb, w in lfeats:
                    if {a, b} == {pa_, pb_} and w >= 1.0:
                        qa, qb = _jmap(a, pa), _jmap(b, pb)
                        d = (qb[0] - qa[0], qb[1] - qa[1])
                        ds.append((a, b, d))
                if not ds:
                    continue
                mx = float(np.mean([d[0] for _, _, d in ds]))
                my = float(np.mean([d[1] for _, _, d in ds]))
                # d is (b - a); move the non-07 sheet so the mean vanishes
                mover = pa_ if pa_ != "07" else pb_
                sgn = 0.0
                if all(b == mover for _, b, _ in ds):
                    sgn = -1.0     # mover is b: shift b by -d
                elif all(a == mover for a, _, _ in ds):
                    sgn = +1.0     # mover is a: shift a by +d
                else:
                    log(f"wharf pair {pa_}|{pb_}: mixed orientation, skipped")
                    continue
                tot[mover]["tx"] += sgn * mx
                tot[mover]["ty"] += sgn * my
                log(f"wharf pair mean zeroed: {mover} shifted "
                    f"({sgn*mx:+.1f},{sgn*my:+.1f}) from {len(ds)} features")
        lm_fix = {k: {"tx": tot[k]["tx"], "ty": tot[k]["ty"],
                      "sx": tot[k]["sx"], "sy": tot[k]["sy"],
                      "cx": cent[k][0], "cy": cent[k][1]}
                  for k in lkeys}
        for k in lkeys:
            f_ = lm_fix[k]
            log(f"landmark fix {k}: t=({f_['tx']:+.0f},{f_['ty']:+.0f})px "
                f"s=({f_['sx']*100:+.2f}%,{f_['sy']*100:+.2f}%)")

    keys = list(geo)
    ki = {k: i for i, k in enumerate(keys)}
    tcorr = {}
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
            tcorr.setdefault(k, [0.0, 0.0])[comp_axis] += float(corr[ki[k]])
        log(("x" if comp_axis == 0 else "y") + " translation corrections: " +
            str({k: round(float(corr[ki[k]])) for k in keys}))
    # frames move with the corrected fits. frame_gp keeps the PIECEWISE
    # mapping of the same frame (shifted by the same correction): the clip
    # loop maps sides through pw_inv, so a seam clamp built on the affine
    # estimate can miss the printed edge by ~30 px — enough to re-open the
    # margin the clamp exists to exclude.
    for k in keys:
        fgp = geo[k]["frame_g"]
        dx, dy = tcorr.get(k, (0.0, 0.0))
        geo[k]["frame_gp"] = (fgp[0] + dx, fgp[1] + dy,
                              fgp[2] + dx, fgp[3] + dy)
        pg = geo[k]["paper_g"]
        geo[k]["paper_g"] = (pg[0] + dx, pg[1] + dy, pg[2] + dx, pg[3] + dy)
        geo[k]["frame_g"] = global_frame(geo[k]["fit"], frames_native[k])
        # The warp renders through the KNOTS, not the fit — a correction
        # applied only to tx/ty is a silent no-op for the map itself.
        # Shift the knots, and the copy dumped to registration.json, so the
        # render and the landmark gate both see the corrected placement.
        geo[k]["xkg"] = [x + dx for x in geo[k]["xkg"]]
        geo[k]["ykg"] = [y + dy for y in geo[k]["ykg"]]
        kn = usable[k]["knots"]
        kn["xkg"] = [x + dx for x in kn["xkg"]]
        kn["ykg"] = [y + dy for y in kn["ykg"]]

    # Landmark-solved per-axis affine (bounded scale about the unit's own
    # landmark centroid). Applied to every geometry the pipeline consumes:
    # knots (the warp), the registration.json copy (the gate), fits (sides,
    # band sampling) and the frame/paper rectangles (seam clamps, margins).
    if lm_fix:
        for k in keys:
            f_ = lm_fix.get(k)
            if not f_:
                continue

            def axx(x, f=f_):
                return f["cx"] + (1 + f["sx"]) * (x - f["cx"]) + f["tx"]

            def ayy(y, f=f_):
                return f["cy"] + (1 + f["sy"]) * (y - f["cy"]) + f["ty"]

            geo[k]["xkg"] = [axx(x) for x in geo[k]["xkg"]]
            geo[k]["ykg"] = [ayy(y) for y in geo[k]["ykg"]]
            kn = usable[k]["knots"]
            kn["xkg"] = [axx(x) for x in kn["xkg"]]
            kn["ykg"] = [ayy(y) for y in kn["ykg"]]
            for rect in ("frame_g", "frame_gp", "paper_g"):
                x0, y0, x1, y1 = geo[k][rect]
                geo[k][rect] = (axx(x0), ayy(y0), axx(x1), ayy(y1))
            fit = geo[k]["fit"]
            fit["tx"] = (1 + f_["sx"]) * fit["tx"] - f_["sx"] * f_["cx"] + f_["tx"]
            fit["sx"] = (1 + f_["sx"]) * fit["sx"]
            fit["ty"] = (1 + f_["sy"]) * fit["ty"] - f_["sy"] * f_["cy"] + f_["ty"]
            fit["sy"] = (1 + f_["sy"]) * fit["sy"]

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
            pi, pj = 1, 3
        else:
            lo = X[max(min(ao), min(an))] + 200
            hi = X[min(max(ao), max(an))] - 200
            pi, pj = 0, 2
        if hi - lo < 400:
            # Grid lines cannot span this seam: a wharf unit holds a single
            # avenue, so the cross-axis extent collapses (lo ends up past
            # hi) and the cut would be scored on a 400 px strip beside
            # Avenue A rather than across the piers. Fall back to where both
            # sheets actually have paper.
            lo = max(geo[owner]["paper_g"][pi], geo[nbr]["paper_g"][pi]) + 100
            hi = min(geo[owner]["paper_g"][pj], geo[nbr]["paper_g"][pj]) - 100
        if flip:
            gpos = np.arange(center - 680, center - 39, 4.0)
            w_own, w_nbr = 3.0, 1.0
        else:
            # band reaches above the line so 'cut before both copies' is
            # available to the cluster costs when the copies straddle it
            gpos = np.arange(center - 240, center + 681, 4.0)
            w_own, w_nbr = 1.0, 3.0
        go = darkness(owner, axis, gpos, lo, hi)
        gn = darkness(nbr, axis, gpos, lo, hi)
        grid = w_own * go + w_nbr * gn
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

        # ---- Label-aware placement (QC v3.2-2 §5). The rendered corridor
        # = owner up to the cut + neighbor beyond it. Each unit's display
        # type (street names, notes, mains) forms ink CLUSTERS; a cluster
        # renders iff it falls on its own unit's side. A whitest-row cut is
        # blind to this: between the two copies of a street name it shows
        # BOTH (doubled 20TH/23RD/26TH); past an owner-only label it shows
        # NEITHER (destroyed 19TH ST.). Score candidates by duplicated +
        # lost clusters, then ink at the cut line.
        # clusters only make sense INSIDE the corridor (± ~230 of the
        # line); farther out every row crosses buildings and a fixed
        # threshold merges the whole band into one blob (v3.3's costs
        # cancelled out that way). Threshold adapts to the corridor's own
        # baseline so display type stands proud of linework noise. The
        # OWNER's window reaches +560: its corridor furniture (Scale of
        # Feet rulers live at ~+300..+450) is owner-only content the cut
        # should keep — v4.2 dropped five of v2's seven rulers by cutting
        # above them (QC v4.2-1).
        win_n = (gpos >= center - 230) & (gpos <= center + 230)
        win_o = (gpos >= center - 230) & (gpos <= center + 560)
        def clusters(g2, win):
            p = np.percentile(np.apply_along_axis(np.convolve, 0, g2, kk,
                                                  "same"), 97, axis=0)
            base = float(np.median(p[win_n])) if win_n.any() else 0.0
            on = (p > max(0.30, base + 0.12)) & win
            runs, s = [], None
            for i, v in enumerate(on):
                if v and s is None:
                    s = i
                elif not v and s is not None:
                    if i - s >= 3:
                        runs.append((s, i - 1, float(p[s:i].max())))
                    s = None
            if s is not None and len(on) - s >= 3:
                runs.append((s, len(on) - 1, float(p[s:].max())))
            return runs

        co, cn = clusters(go, win_o), clusters(gn, win_n)
        # frame RULES are full-span dark rows (mean darkness >> any label's
        # span-mean): they are not content to keep — a cut at or beyond one
        # renders a black rule across the corridor. Detected on the owner's
        # MEAN profile over the WHOLE band (rules sit outside the cluster
        # window); the neighbor's rule is excluded by its frame clamp on
        # the clip side.
        mo = np.convolve(go.mean(axis=0), kk, mode="same")
        rule_on = (mo > 0.15) & (gpos > center + 120)
        o_rules, s = [], None
        for i, vv in enumerate(rule_on):
            if vv and s is None:
                s = i
            elif not vv and s is not None:
                if i - s >= 2:
                    o_rules.append((s, i - 1))
                s = None
        if s is not None:
            o_rules.append((s, len(rule_on) - 1))
        co = [a for a in co if not any(r[0] <= a[0] <= r[1] for r in o_rules)]
        used = set()
        pairs, o_only, n_only = [], [], []
        for a in co:
            best, bj = None, None
            for j, b in enumerate(cn):
                if j in used:
                    continue
                da = abs((a[0] + a[1]) - (b[0] + b[1])) / 2
                if da < 90 and (best is None or da < best):
                    best, bj = da, j
            if bj is not None:
                used.add(bj)
                pairs.append((a, cn[bj]))
            else:
                o_only.append(a)
        n_only = [b for j, b in enumerate(cn) if j not in used]

        cand = np.arange(lo_i, hi_i)
        cost = dsm[cand].copy()
        W = 0.55   # each duplicated or lost cluster outweighs ink shading
        for a, b in pairs:
            # duplicated when the cut lies between the copies with the
            # owner's copy on the owner side; neither shown when inverted
            lo_c, hi_c = min(a[1], b[1]), max(a[0], b[0])
            both = (cand > a[1] + 2) & (cand < b[0] - 2)
            none = (cand > b[1] + 2) & (cand < a[0] - 2)
            cost[both | none] += W
        for a in o_only:      # owner-only content: lost if cut before it
            cost[cand < a[1] + 3] += W
        for b in n_only:      # neighbor-only content: lost if cut after it
            cost[cand > b[0] - 3] += W
        for r in o_rules:     # never render the owner's frame rule
            cost[cand > r[0] - 3] += 0.9
        return float(gpos[int(cand[np.argmin(cost)])])

    # Border-connected scan-junk projections per unit (QC v3-2): a seam cut
    # that reaches past the owner's paper edge renders the owner's scanner
    # rule / backing strip OVER the neighbor's real content (the solid black
    # bar in the 19th St corridor covered 18k px of sheet 7's map ink). The
    # region/native print_end cap cannot see this — it caps at the SCAN
    # extent, junk included. Same border-connectivity criterion as the
    # exterior margin trim: junk touches the scan edge, print never does.
    def legal_cut(axis, owner, nbr, cut, center):
        """Clamp a seam cut into the window where BOTH sheets have printed
        map: after the neighbour's frame starts, before the owner's frame
        ends. Outside it the composite renders sheet margin — unfilled
        canvas if the cut precedes the neighbour's paper, blank cream and
        torn scan edge if it runs past the owner's print.

        1899 sheets abut with only ~50-70 px of shared corridor (measured:
        sheet 13 prints to Ave D +43, sheet 14 starts at -16), far less
        overlap than 1885's, so an unclamped label-aware cut lands outside
        the window routinely — the beta tile showed both failure modes at
        the one junction.
        """
        i0, i1 = (0, 2) if axis == "v" else (1, 3)
        # Bound by PAPER as well as frame: the frame estimate can sit past
        # the sheet's paper edge, and a cut there renders the scan's white
        # background — an 18 px pure-white bar right across the wharf at the
        # 19th St seam, which no paper-tone check catches because it is not
        # unfilled canvas, it is sheet 08's scanner ground.
        ins_o = cov.scan_inset(year, cov.COVERAGE[year][owner]["file"],
                               "right" if axis == "v" else "bottom")
        ins_n = cov.scan_inset(year, cov.COVERAGE[year][nbr]["file"],
                               "left" if axis == "v" else "top")
        lo = max(geo[nbr]["frame_gp"][i0],
                 geo[nbr]["paper_g"][i0] + ins_n) + feather
        hi = min(geo[owner]["frame_gp"][i1],
                 geo[owner]["paper_g"][i1] - ins_o) - 4
        if lo > hi:
            mid = 0.5 * (lo + hi)
            log(f"seam {axis} {owner}|{nbr}: printed frames do not overlap "
                f"({lo - center:+.0f}..{hi - center:+.0f} rel line) — "
                f"cutting at the midpoint {mid - center:+.0f}, disclosed")
            return mid
        return float(min(max(cut, lo), hi))

    prop = {}
    nbr_frame_caps = set()
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
        # At a seam NEITHER unit may contribute from outside its printed
        # frame: the owner's far cap is its own frame edge (the junk caps
        # this replaces chased scanner bands but flagged rails and bay
        # water, displacing cuts by hundreds of px), and the neighbor's
        # near side is clamped to its frame in the clip loop so its margin
        # marginalia (sheet 7's Scale of Feet/No.7 at 19th in v2) and
        # frame rule stay out of the corridor.
        manual = cov.seam_cut(year, axis, idx, frozenset({owner, nbr}))
        if manual is not None:
            log(f"seam {axis}{idx} {owner}|{nbr}: manual cut {manual:+d}")
        # Seam policy. 1885 sheets share only a sliver of corridor, so the
        # cut is placed by the label-aware search. 1899 sheets overlap by
        # hundreds of px — each prints the whole street AND both facing
        # block frontages — so a cut anywhere inside that band destroys
        # something: it lands in one sheet's frontage strip (the 101-123
        # address row at 24th, the 1902-1928 kerb column at Avenue D), or in
        # the dead zone between the two sheets' copies of the street name,
        # discarding BOTH (21ST OR CENTRE, 24TH). Laying the owner over the
        # whole overlap, capped at its printed frame, keeps one complete
        # copy of everything — the same rule already proven at the wharf.
        own_top = (manual is None
                   and ed.get("seam_policy") == "owner-on-top")
        if axis == "v":
            center = X[idx]
            cut = (center + manual if manual is not None
                   else center + 4000 if own_top
                   else best_cut("v", center, owner, nbr, flip=flip))
            if flip:
                owner_end = max(min(cut, center - 40), center - 680)
                cap = geo[nbr]["frame_g"][0] + 6
                nbr_start = owner_end - feather
                if cap <= nbr_start + 350:
                    nbr_start = max(nbr_start, cap)
                log(f"seam v{idx} {owner}|{nbr}: FLIPPED cut at "
                    f"{owner_end - center:+.0f} rel to line")
                prop.setdefault((owner, "right"), []).append(owner_end)
                prop.setdefault((nbr, "left"), []).append(nbr_start)
                continue
            ins = cov.scan_inset(year, cov.COVERAGE[year][owner]["file"], "right")
            print_end = comp.pw_fwd([min(reg_own[2], nw - ins)],
                                    g_own["xkn"], g_own["xkg"])[0]
            owner_end = min(max(cut, center - 240), print_end - 4)
            owner_end = legal_cut("v", owner, nbr, owner_end, center)
            log(f"seam v{idx} {owner}|{nbr}: cut at {owner_end - center:+.0f}")
            prop.setdefault((owner, "right"), []).append(owner_end)
            prop.setdefault((nbr, "left"), []).append(owner_end - feather)
            nbr_frame_caps.add((nbr, "left"))
        else:
            center = Y[idx]
            cut = (center + manual if manual is not None
                   else center + 4000 if own_top
                   else best_cut("h", center, owner, nbr, flip=flip))
            if flip:
                owner_end = max(min(cut, center - 40), center - 680)
                cap = geo[nbr]["frame_g"][1] + 6
                if own_top and center - 680 <= cap <= center - 40:
                    # owner-on-top flip: end the owner at the neighbour's
                    # frame top, ABOVE the corridor band. A cut at line-40
                    # runs through the band where both sheets print the
                    # street label, ghosting it in the feather (22ND ST
                    # doubled at the wharf); at the frame top the label
                    # band belongs to the neighbour alone.
                    owner_end = cap + feather
                nbr_start = owner_end - feather
                if cap <= nbr_start + 350:
                    nbr_start = max(nbr_start, cap)
                log(f"seam h{idx} {owner}|{nbr}: FLIPPED cut at "
                    f"{owner_end - center:+.0f} rel to line")
                prop.setdefault((owner, "bottom"), []).append(owner_end)
                prop.setdefault((nbr, "top"), []).append(nbr_start)
                continue
            ins = cov.scan_inset(year, cov.COVERAGE[year][owner]["file"], "bottom")
            print_end = comp.pw_fwd([min(reg_own[3], nh - ins)],
                                    g_own["ykn"], g_own["ykg"])[0]
            owner_end = min(max(cut, center - 240), print_end - 4)
            owner_end = legal_cut("h", owner, nbr, owner_end, center)
            log(f"seam h{idx} {owner}|{nbr}: cut at {owner_end - center:+.0f}")
            prop.setdefault((owner, "bottom"), []).append(owner_end)
            prop.setdefault((nbr, "top"), []).append(owner_end - feather)
            nbr_frame_caps.add((nbr, "top"))

    for (key, side), vals in prop.items():
        if side in ("right", "bottom"):
            sides[key][side] = max(vals)
        else:
            sides[key][side] = min(vals)
    # Neighbor frame clamps are DEAD for normal seams (QC v4.2-1): frame
    # estimates proved unreliable in every round — even bounded to 350px
    # they blanked corridor halves (25th x B east, Ave D 22-23, Ave G
    # 20-23). With cuts never higher than center-240 and true frames
    # ~250-400 beyond the line, the neighbor's clip at cut-feather stays
    # inside its print anyway, so margin junk cannot enter. Flip seams
    # keep their bounded clamp (applied inline; the cut sits beyond the
    # line there).

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
        px0, py0, px1, py1 = g["paper_g"]
        # An exterior side has no neighbour, so it may run all the way to the
        # sheet's own PAPER edge — which is also the only bound that holds on
        # wharf sheets, whose single grid line defeats frame detection, and
        # the only one that keeps the scan's credit caption out of the map.
        edges = {
            "left":   (px0, [(a0k - 1, s) for s in range(s0k, s1k)]),
            "right":  (px1, [(a1k, s) for s in range(s0k, s1k)]),
            "top":    (py0, [(a, s0k - 1) for a in range(a0k, a1k)]),
            "bottom": (py1, [(a, s1k) for a in range(a0k, a1k)]),
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
        # A SEAM side may never reach outside this sheet's printed frame.
        # Without this the sheet extents run into the margin and paste its
        # furniture into the map: sheet 37's blank top margin and its giant
        # printed "37" landed across the Avenue G x 24th junction, and a
        # sliced "39" pointer filled the lost south frontage row at 24th
        # (seam QC, findings 3-4). legal_cut already guarantees the cut sits
        # inside BOTH sheets' printed extents, so capping here cannot open a
        # hole the neighbour does not fill.
        es = ext_sides.get(key, set())
        fr = frames_native[key]
        if "left" not in es:
            cx0 = max(cx0, fr[0])
        if "top" not in es:
            cy0 = max(cy0, fr[1])
        if "right" not in es:
            cx1 = min(cx1, fr[2])
        if "bottom" not in es:
            cy1 = min(cy1, fr[3])
        img = cv2.imread(sheet_path(year, unit["file"]), cv2.IMREAD_COLOR)
        # Static scan-edge insets on exterior-extended sides (QC v3.2-1):
        # dynamic junk detection failed in both directions — thin rules
        # slipped through while rail sidings / bay water got flagged and
        # the trim beheaded certified annotations. The measured, visually
        # verified per-side constants live in cov.SCAN_INSETS.
        if es:
            def inset(side):
                return cov.scan_inset(year, unit["file"], side)
            # insets measure from whichever boundary caps the side: the
            # scan edge for full sheets, the region border for panel
            # units — a panel divider carries the other panel's frame
            # rule (unit 3's retained top ran a 4660x44px black rule
            # straight from the divider zone, QC v4-C)
            pn = g["paper_n"]
            bx0, by0 = (creg[0], creg[1]) if creg else (pn[0], pn[1])
            bx1, by1 = (creg[2], creg[3]) if creg else (pn[2], pn[3])
            if "top" in es:
                cy0 = max(cy0, by0 + inset("top"))
            if "bottom" in es:
                cy1 = min(cy1, by1 - inset("bottom"))
            if "left" in es:
                cx0 = max(cx0, bx0 + inset("left"))
            if "right" in es:
                cx1 = min(cx1, bx1 - inset("right"))
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
        if config.PRESERVE_COLORS:
            s = 1.0   # unity gain cannot push a highlight anywhere it wasn't
        if s < 0.999:
            log(f"unit {key}: gain scaled x{s:.3f} to protect highlights")
        gains = gains * s
        comp.warp_sheet_piecewise(canvas, weight, img, g["xkn"], xkg_c,
                                  g["ykn"], ykg_c, clip, gains, feather,
                                  shear=tuple(sh),
                                  shear_pivot=(float(np.mean(g["xkn"])),
                                               float(np.mean(g["ykn"]))),
                                  border_bgr=tuple(target_tone))
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
    # per-edition street origin (1899 starts at 6th St)
    ed = config.EDITIONS[year]
    config.STREET_ORIGIN = ed.get("street_origin", config.STREET_ORIGIN)
    if "--original-colors" in sys.argv:
        config.PRESERVE_COLORS = True
        log("original-colour mode: no per-sheet white balance applied")
    # per-edition detect-scale comb pitches (native pitch scaled to the
    # DETECT_WIDTH working width). 1899: uniform slot pitch — see config.
    k = config.DETECT_WIDTH / ed["native_size"][0]
    config.PITCH_AV_DETECT = ed["pitch_av"] * k
    config.PITCH_ST_DETECT = ed["pitch_st"] * k
    registration = register_edition(year)
    blockers = {k: r["status"] for k, r in registration.items() if r["status"] != "ok"}
    if blockers:
        log(f"NOT compositing yet — unresolved units: {blockers}")
        return 1
    composite_edition(year, registration)
    return 0


if __name__ == "__main__":
    sys.exit(main())
