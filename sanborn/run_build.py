"""Phases B+C driver for one edition: detect -> gate -> identify -> fit ->
composite. Writes build/{year}/registration.json and the composite TIFF.

Usage: python3 run_build.py 1885|1877

Line-identity assignment uses coverage_prior ranges; any sheet whose detected
line count disagrees with the prior is written to registration.json with
status "needs-review" and skipped from compositing until resolved — the A2
step (visual label reading) settles those before re-running.
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


def sheet_path(year, num):
    ed = config.EDITIONS[year]
    d = os.path.join(config.SOURCES_DIR, year)
    candidates = [
        os.path.join(d, f"Galveston_{year}_sheet_{num:02d}.jpg"),  # uploaded set
        os.path.join(d, f"08539_{year}-{num:04d}.tif"),            # LoC master
        os.path.join(d, f"txu-sanborn-galveston-{year}-{num:02d}.jpg"),  # UT
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return candidates[0]


# On-grid panel regions (native px, x0,y0,x1,y1) for multi-panel sheets,
# verified visually against the scans. Content outside these regions is
# excluded and disclosed (off-scale upper panel of 3; east-of-Broadway
# panels of 4; off-grid panels of 11).
PANELS = {
    "1885": {
        3: (0, 2500, 6450, 7650),    # lower panel: Ave D-G x 18-20
        4: (0, 0, 2260, 7650),       # left panel: Ave G-H x 25-28
        11: (0, 0, 4400, 4950),      # upper-left panel: Ave G-I x 23-25
    },
}


def assign_identities(detected, year, sheet):
    """Map detected native-scale lines to avenue/street identities from the
    coverage prior. Requires an exact count match; anything else needs A2."""
    avs, sts = cov.expected_lines(year, sheet)
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
    """Per-axis fit, edge-bias aware.

    Edge grid lines sit on half-streets (sheets abut along street
    centerlines), so their center-of-mass refinement is pulled inward.
    Policy:
      - >=2 interior lines on an axis: fit scale+translation on interior
        lines only. Gate scale at +/-2% (1% warn).
      - fewer: lock scale to 1.0 (pitch is an edition constant, verified)
        and fit translation as the mean over ALL lines - the symmetric
        inward biases of the two edge lines cancel in the mean.
    Reports per-line residuals for QC.
    """
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
    """Off-scale check on refined line spacings (median vs edition pitch).
    Catches genuinely off-scale panels (e.g. 1885 sheet 3 upper, ~18% off)
    while tolerating the ~3% inward bias of edge lines."""
    ed = config.EDITIONS[year]
    devs = {}
    for key, pitch in (("v_lines_native", ed["pitch_av"]), ("h_lines_native", ed["pitch_st"])):
        lines = detected[key]
        if len(lines) < 3:
            continue  # only edge lines: spacing measures their bias, not scale
        sp = [b - a for a, b in zip(lines, lines[1:])]
        if len(lines) >= 4:
            sp = sp[1:-1]  # interior spacings only (unbiased)
        med = float(np.median(sp))
        devs[key] = round(med / pitch - 1, 4)
    bad = any(abs(d) > tolerance for d in devs.values())
    return bad, devs


def register_edition(year):
    ed = config.EDITIONS[year]
    results = {}
    for num in ed["working_set"]:
        path = sheet_path(year, num)
        if not os.path.exists(path):
            results[num] = {"status": "missing-source"}
            log(f"sheet {num}: source missing")
            continue
        region = PANELS.get(year, {}).get(num)
        det = reg.detect_sheet_grid(path, region=region)
        det["panel_region"] = region
        bad, devs = spacing_gate(det, year)
        if bad:
            results[num] = {"status": "off-scale", "spacing_dev": devs,
                            "note": "median spacing deviates >6% — excluded, disclosed"}
            log(f"sheet {num}: OFF-SCALE {devs} — excluded")
            continue
        controls, err = assign_identities(det, year, num)
        if err:
            results[num] = {"status": "needs-review", "detail": err, "detected": det}
            log(f"sheet {num}: NEEDS REVIEW — {err}")
            continue
        fit = fit_sheet(controls, year)
        flags = (fit["flag_x"], fit["flag_y"])
        status = "ok" if all(f in ("OK", "WARN") for f in flags) else "scale-fail"
        results[num] = {"status": status, "fit": fit, "detected": det, "controls": controls}
        log(f"sheet {num}: sx={fit['sx']:.4f} {fit['mode_x']} ({fit['flag_x']}) "
            f"resid={fit['resid_x']} | sy={fit['sy']:.4f} {fit['mode_y']} "
            f"({fit['flag_y']}) resid={fit['resid_y']}")
        if status == "scale-fail":
            log(f"sheet {num}: SCALE GATE FAIL — misidentified grid line, stop and re-derive")
    outdir = os.path.join(config.BUILD_DIR, year)
    os.makedirs(outdir, exist_ok=True)
    with open(os.path.join(outdir, "registration.json"), "w") as f:
        json.dump(results, f, indent=1, default=list)
    return results


def composite_edition(year, registration):
    import cv2

    ed = config.EDITIONS[year]
    a0, a1, s0, s1 = cov.composite_extent(year)
    pad = round(0.25 * ed["pitch_av"])
    width = round((a1 - a0) * ed["pitch_av"]) + 2 * pad
    height = round((s1 - s0) * ed["pitch_st"]) + 2 * pad
    # canvas origin: global (a0*P_AV - pad, (s0-16)*P_ST - pad)
    ox = a0 * ed["pitch_av"] - pad
    oy = (s0 - config.STREET_ORIGIN) * ed["pitch_st"] - pad
    log(f"{year} canvas {width} x {height} ({width*height/1e6:.0f} MP)")

    canvas, weight = comp.new_canvas(width, height, ed["paper_bgr"])

    native_w = ed["native_size"][0]
    shift = config.CLIP_SHIFT_3400 * native_w / config.DETECT_WIDTH
    feather = round(config.FEATHER_3400 * native_w / config.DETECT_WIDTH)
    ext = round(2.0 * shift)

    tones = {}
    usable = {n: r for n, r in registration.items() if r.get("status") == "ok"}
    for num, r in usable.items():
        img = cv2.imread(sheet_path(year, num), cv2.IMREAD_COLOR)
        tones[num] = comp.paper_tone(img)
        del img
    target_tone = np.mean([t for t in tones.values()], axis=0)
    log(f"edition mean paper tone (BGR): {np.round(target_tone,1)}")

    for num, r in usable.items():
        img = cv2.imread(sheet_path(year, num), cv2.IMREAD_COLOR)
        det, fit = r["detected"], r["fit"]
        # Grid lines for clipping come from the FITTED grid (unbiased), not
        # the detected lines: edge-line detections carry the half-street
        # inward bias, which would leave ~200 px paper gutters at seams.
        avs, sts = cov.expected_lines(year, num)
        gv = [(a * ed["pitch_av"] - fit["tx"]) / fit["sx"] for a in avs]
        gh = [((s - config.STREET_ORIGIN) * ed["pitch_st"] - fit["ty"]) / fit["sy"] for s in sts]
        img01 = img.astype(np.float32) / 255.0
        frame = comp.frame_bounds(img01, gv, gh, region=det.get("panel_region"))
        del img01
        clip = comp.clip_window(gv, gh, frame, shift, ext, cov.composite_edges(year, num))
        gains = comp.channel_gains(tones[num], target_tone)
        affine = {
            "sx": fit["sx"], "tx": fit["tx"] - ox,
            "sy": fit["sy"], "ty": fit["ty"] - oy,
        }
        comp.warp_sheet_into(canvas, weight, img, affine, clip, gains, feather)
        log(f"sheet {num}: composited (gains {np.round(gains,3)})")
        del img

    out = os.path.join(config.BUILD_DIR, year, f"galveston_{year}_composite.tif")
    comp.save_tiff(canvas, out)
    cov_pct = 100.0 * (weight > 0).mean()
    log(f"{year}: wrote {out} ({os.path.getsize(out)>>20} MB), coverage {cov_pct:.1f}%")
    cv2.imwrite(
        os.path.join(config.BUILD_DIR, year, "coverage_mask.png"),
        (weight > 0).astype(np.uint8) * 255,
    )
    return out


def main():
    year = sys.argv[1]
    registration = register_edition(year)
    blockers = {n: r["status"] for n, r in registration.items() if r["status"] != "ok"}
    if blockers:
        log(f"NOT compositing yet — unresolved sheets: {blockers}")
        return 1
    composite_edition(year, registration)
    return 0


if __name__ == "__main__":
    sys.exit(main())
