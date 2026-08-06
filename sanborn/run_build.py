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

    # Per-unit fitted grid lines + frames (native and global)
    geo = {}
    for key, r in usable.items():
        unit = cov.COVERAGE[year][key]
        fit = r["fit"]
        avs, sts = cov.expected_lines(year, key)
        gv = [(a * ed["pitch_av"] - fit["tx"]) / fit["sx"] for a in avs]
        gh = [((s - config.STREET_ORIGIN) * ed["pitch_st"] - fit["ty"]) / fit["sy"] for s in sts]
        img = cv2.imread(sheet_path(year, unit["file"]), cv2.IMREAD_COLOR)
        img01 = img.astype(np.float32) / 255.0
        frame = comp.frame_bounds(img01, gv, gh, region=unit["region"])
        del img, img01
        geo[key] = {"fit": fit, "gv": gv, "gh": gh,
                    "frame_g": global_frame(fit, frame), "avs": avs, "sts": sts}

    # Global side bounds per unit: rim default (frame ∩ line±ext), then seams
    sides = {}
    for key, g in geo.items():
        fx0, fy0, fx1, fy1 = g["frame_g"]
        sides[key] = {
            "left":   max(fx0, min(g["avs"]) * ed["pitch_av"] - ext),
            "right":  min(fx1, max(g["avs"]) * ed["pitch_av"] + ext),
            "top":    max(fy0, (min(g["sts"]) - config.STREET_ORIGIN) * ed["pitch_st"] - ext),
            "bottom": min(fy1, (max(g["sts"]) - config.STREET_ORIGIN) * ed["pitch_st"] + ext),
        }
    for axis, idx, owner, nbr in cov.neighbors(year):
        if owner not in geo or nbr not in geo:
            continue
        if axis == "v":
            center = idx * ed["pitch_av"]
            bound = min(geo[owner]["frame_g"][2], center + shift)
            nbr_lo = geo[nbr]["frame_g"][0]
            if nbr_lo > bound + feather:
                log(f"seam v{idx} {owner}|{nbr}: print gap {nbr_lo-bound:.0f}px (frames do not tile)")
            sides[owner]["right"] = min(max(sides[owner]["right"], bound + feather),
                                        geo[owner]["frame_g"][2])
            sides[nbr]["left"] = max(min(sides[nbr]["left"], bound - feather),
                                     geo[nbr]["frame_g"][0])
        else:
            center = (idx - config.STREET_ORIGIN) * ed["pitch_st"]
            bound = min(geo[owner]["frame_g"][3], center + shift)
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
        fit = geo[key]["fit"]
        sd = sides[key]
        cx0 = (sd["left"] - fit["tx"]) / fit["sx"]
        cx1 = (sd["right"] - fit["tx"]) / fit["sx"]
        cy0 = (sd["top"] - fit["ty"]) / fit["sy"]
        cy1 = (sd["bottom"] - fit["ty"]) / fit["sy"]
        if unit["region"]:
            rx0, ry0, rx1, ry1 = unit["region"]
            cx0, cy0 = max(cx0, rx0), max(cy0, ry0)
            cx1, cy1 = min(cx1, rx1), min(cy1, ry1)
        clip = (cx0, cy0, cx1, cy1)
        gains = comp.channel_gains(tones[key], target_tone)
        affine = {"sx": fit["sx"], "tx": fit["tx"] - ox,
                  "sy": fit["sy"], "ty": fit["ty"] - oy}
        img = cv2.imread(sheet_path(year, unit["file"]), cv2.IMREAD_COLOR)
        comp.warp_sheet_into(canvas, weight, img, affine, clip, gains, feather)
        log(f"unit {key}: composited clip={[round(v) for v in clip]} gains={np.round(gains,3)}")
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
