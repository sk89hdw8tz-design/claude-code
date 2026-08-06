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
    if ed["source"] == "loc":
        return os.path.join(d, f"08539_{year}-{num:04d}.tif")
    return os.path.join(d, f"txu-sanborn-galveston-{year}-{num:02d}.jpg")


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


def register_edition(year):
    ed = config.EDITIONS[year]
    results = {}
    for num in ed["working_set"]:
        path = sheet_path(year, num)
        if not os.path.exists(path):
            results[num] = {"status": "missing-source"}
            log(f"sheet {num}: source missing")
            continue
        det = reg.detect_sheet_grid(path)
        bad, devs = reg.off_scale(det, year)
        if bad:
            results[num] = {
                "status": "off-scale",
                "pitch_dev_av_st": devs,
                "note": "measured pitch deviates >5% — excluded, disclosed",
            }
            log(f"sheet {num}: OFF-SCALE (dev av/st = {devs}) — excluded")
            continue
        controls, err = assign_identities(det, year, num)
        if err:
            results[num] = {"status": "needs-review", "detail": err, "detected": det}
            log(f"sheet {num}: NEEDS REVIEW — {err}")
            continue
        fit = reg.fit_affine(controls, year)
        flags = (fit["flag_x"], fit["flag_y"])
        status = "ok" if all(f.startswith("OK") or f.startswith("WARN") for f in flags) else "scale-fail"
        results[num] = {"status": status, "fit": fit, "detected": det, "controls": controls}
        log(
            f"sheet {num}: sx={fit['sx']:.4f} ({fit['flag_x']}), "
            f"sy={fit['sy']:.4f} ({fit['flag_y']})"
        )
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
        img01 = img.astype(np.float32) / 255.0
        frame = comp.frame_bounds(img01, det["v_lines_native"], det["h_lines_native"])
        del img01
        clip = comp.clip_window(
            det["v_lines_native"], det["h_lines_native"], frame, shift, ext,
            cov.composite_edges(year, num),
        )
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
