#!/usr/bin/env python
"""render_master.py — composite the 12-sheet candidate master.

For each sheet: exactly ONE warp from the archival JP2 (cv2.warpAffine with the
composed raw-pixel transform — including any canvas origin/scale — LANCZOS4,
white border) directly into the master canvas. Ownership is composited by a
nearest-neighbour warp of the rasterized sheet ownership polygon: hard
ownership, no blending, no exposure matching, no colour changes. Archival
scans are read-only; their sha256 is verified against the inventory first.

Canvas: cuts.json target_extent = bbox of the 12 solved footprints intersected
with the target extent, plus the reserved blank bay-side band for the sheet-5
panels (left empty in this build). Processing runs in horizontal strips
(<= --strip-height rows) over a disk-backed canvas so peak RAM stays modest.

Outputs: 60_master/candidate_master.tif (LZW, 8-bit RGB),
         60_master/candidate_preview.png (<= 4000 px wide),
         60_master/render_manifest.json (full one-resample provenance).

--preview renders at scale 0.5 and marks the manifest status
"preview-not-final" — the final render waits for the frozen transforms.
"""

import argparse
import json
import os
import sys
import time

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(PROJECT, "50_seams"))
import seamlib as sl  # noqa: E402

SCRATCH = os.environ.get(
    "G1912_SCRATCH",
    "/tmp/claude-0/-home-user-claude-code/3107d3d8-6779-530e-9ae5-ba7b48239c4e/scratchpad")


def rasterize_regions(regions, shape_hw):
    """Sheet ownership raster (uint8 0/255) from masks.json features."""
    m = np.zeros(shape_hw, dtype=np.uint8)
    for feat in regions:
        ext = np.rint(np.asarray(feat["polygon_sheet_px"]["exterior"])).astype(np.int32)
        cv2.fillPoly(m, [ext], 255)
        for hole in feat["polygon_sheet_px"]["interiors"]:
            cv2.fillPoly(m, [np.rint(np.asarray(hole)).astype(np.int32)], 0)
    return m


def transform_sha(T):
    return sl.sha256_text(sl.canonical_dumps(T, ndigits=9))


def mask_sha(regions):
    return sl.sha256_text(sl.canonical_dumps(
        [{k: f[k] for k in ("region_id", "polygon_sheet_px")} for f in regions]))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--preview", action="store_true",
                    help="half-resolution pipeline-proof render (scale 0.5)")
    ap.add_argument("--scale", type=float, default=None,
                    help="explicit canvas scale (default 1.0, or 0.5 with --preview)")
    ap.add_argument("--strip-height", type=int, default=2000)
    ap.add_argument("--transforms", default=sl.TRANSFORMS_JSON)
    ap.add_argument("--cuts", default=sl.CUTS_JSON)
    ap.add_argument("--masks", default=sl.MASKS_JSON)
    ap.add_argument("--outdir", default=os.path.join(PROJECT, "60_master"))
    ap.add_argument("--preview-max-width", type=int, default=4000)
    args = ap.parse_args(argv)

    scale = args.scale if args.scale is not None else (0.5 if args.preview else 1.0)
    status = "preview-not-final" if scale != 1.0 else "candidate-awaiting-frozen-transforms"

    t_start = time.time()
    raw, tdoc = sl.load_transforms(args.transforms)
    with open(args.cuts) as f:
        cuts = json.load(f)
    with open(args.masks) as f:
        masks = json.load(f)
    inv_items, _ = sl.load_inventory()

    # consistency: masks must have been built from these transforms
    t_sha = sl.sha256_file(args.transforms)
    if masks["inputs"]["transforms_json"]["sha256"] != t_sha:
        raise SystemExit("masks.json was built from different transforms.json — "
                         "re-run build_cuts.py + build_masks.py first")

    x0m, y0m, x1m, y1m = cuts["target_extent"]["canvas_rect_mosaic"]
    W = int(np.ceil((x1m - x0m) * scale))
    H = int(np.ceil((y1m - y0m) * scale))
    band = cuts["target_extent"]["reserved_bay_band"]["mosaic_rect"]
    band_canvas = [0, 0, int(np.ceil((band[2] - x0m) * scale)), H]
    strip_h = max(64, min(args.strip_height, 2000))
    print("canvas %d x %d px (scale %s of mosaic rect %d..%d x %d..%d), "
          "strips of %d rows, reserved bay band 0..%d px" %
          (W, H, scale, x0m, x1m, y0m, y1m, strip_h, band_canvas[2]))

    regions_by_sheet = {}
    for feat in masks["regions"]:
        regions_by_sheet.setdefault(int(feat["sheet"]), []).append(feat)

    os.makedirs(SCRATCH, exist_ok=True)
    canvas_path = os.path.join(SCRATCH, "render_canvas_%dx%d.dat" % (W, H))
    canvas = np.memmap(canvas_path, dtype=np.uint8, mode="w+", shape=(H, W, 3))
    for y0 in range(0, H, strip_h):
        canvas[y0:min(y0 + strip_h, H)] = 255  # white ground

    manifest_sheets = []
    for sheet in sorted(regions_by_sheet):
        t_sheet = time.time()
        T = raw[sheet]
        item = inv_items[sheet]
        src = item["path"]
        got_sha = sl.sha256_file(src)
        if got_sha != item["sha256"]:
            raise SystemExit("sha256 mismatch for sheet %d source %s — refusing to "
                             "render from an unverified archival file" % (sheet, src))
        img = cv2.imread(src, cv2.IMREAD_COLOR)  # BGR, read-only use
        if img is None or img.shape[:2] != (item["height"], item["width"]):
            raise SystemExit("decode failure or size mismatch for sheet %d" % sheet)
        regions = sorted(regions_by_sheet[sheet], key=lambda f: f["region_id"])
        own_raster = rasterize_regions(regions, img.shape[:2])

        # sheet -> canvas matrix (single composed transform; ONE resample)
        M = sl.warp_matrix(T, origin=(x0m, y0m), scale=scale)

        # canvas-space footprint of the page quad limits the strips touched
        quad = np.asarray([[0, 0], [item["width"], 0],
                           [item["width"], item["height"]], [0, item["height"]]], float)
        qc = (M[:, :2] @ quad.T).T + M[:, 2]
        bx0 = max(0, int(np.floor(qc[:, 0].min())))
        bx1 = min(W, int(np.ceil(qc[:, 0].max())) + 1)
        by0 = max(0, int(np.floor(qc[:, 1].min())))
        by1 = min(H, int(np.ceil(qc[:, 1].max())) + 1)
        strips = 0
        if bx1 > bx0:
            for y0 in range(by0 - by0 % strip_h, by1, strip_h):
                sy0, sy1 = max(y0, 0), min(y0 + strip_h, H)
                if sy1 <= max(by0, 0):
                    continue
                w, h = bx1 - bx0, sy1 - sy0
                Ms = M.copy()
                Ms[0, 2] -= bx0
                Ms[1, 2] -= sy0
                warped = cv2.warpAffine(img, Ms, (w, h), flags=cv2.INTER_LANCZOS4,
                                        borderMode=cv2.BORDER_CONSTANT,
                                        borderValue=(255, 255, 255))
                ownw = cv2.warpAffine(own_raster, Ms, (w, h), flags=cv2.INTER_NEAREST,
                                      borderMode=cv2.BORDER_CONSTANT, borderValue=0)
                own = ownw > 0
                if own.any():
                    roi = canvas[sy0:sy1, bx0:bx1]
                    roi[own] = warped[..., ::-1][own]  # BGR -> RGB, hard ownership
                strips += 1
        del img, own_raster
        manifest_sheets.append({
            "sheet": sheet,
            "source_file": os.path.basename(src),
            "source_sha256": got_sha,
            "source_sha256_verified_against_inventory": True,
            "transform_raw": T,
            "transform_sha256": transform_sha(T),
            "mask_region_ids": [f["region_id"] for f in regions],
            "mask_sha256": mask_sha(regions),
            "warp": {"interpolation": "INTER_LANCZOS4", "border": "white",
                     "mask_interpolation": "INTER_NEAREST",
                     "resamples_from_archival": 1,
                     "compositing": "hard ownership, no blending, no exposure or "
                                    "colour changes"},
            "canvas_bbox": [bx0, by0, bx1, by1],
            "strips_written": strips,
            "seconds": round(time.time() - t_sheet, 2),
        })
        print("  sheet %2d warped: bbox x %d..%d y %d..%d, %d strip(s), %.1fs" %
              (sheet, bx0, bx1, by0, by1, strips, time.time() - t_sheet))

    # reserved band must be empty (white): verify, do not fix
    bx = band_canvas[2]
    band_ok = True
    if bx > 0:
        for y0 in range(0, H, strip_h):
            seg = canvas[y0:min(y0 + strip_h, H), :bx]
            if seg.min() != 255:
                band_ok = False
                break
    print("reserved bay band empty: %s" % band_ok)

    canvas.flush()
    import tifffile
    tif_path = os.path.join(args.outdir, "candidate_master.tif")
    est_bytes = H * W * 3
    t_tif = time.time()
    tifffile.imwrite(tif_path, canvas, photometric="rgb", compression="lzw",
                     rowsperstrip=1024, bigtiff=est_bytes > 3_500_000_000)
    print("wrote %s (%.1f MB, %.1fs)" % (tif_path,
                                         os.path.getsize(tif_path) / 1e6,
                                         time.time() - t_tif))

    pw = min(args.preview_max_width, W)
    ph = max(1, int(round(H * pw / W)))
    preview = cv2.resize(np.asarray(canvas), (pw, ph), interpolation=cv2.INTER_AREA)
    png_path = os.path.join(args.outdir, "candidate_preview.png")
    cv2.imwrite(png_path, preview[..., ::-1])
    print("wrote %s (%d x %d)" % (png_path, pw, ph))

    manifest = {
        "generated_by": "60_master/tools/render_master.py",
        "status": status,
        "note": "half-resolution pipeline proof; NOT the final master — final render "
                "waits for the frozen transforms" if scale != 1.0 else
                "full-resolution candidate; final only after transform freeze",
        "canvas": {
            "mosaic_rect": [x0m, y0m, x1m, y1m],
            "scale": scale,
            "size_px": [W, H],
            "strip_height": strip_h,
            "mosaic_convention": tdoc["convention"],
            "reserved_bay_band_canvas_px": band_canvas,
            "reserved_bay_band_verified_empty": band_ok,
        },
        "inputs": {
            "transforms_json": {"sha256": t_sha},
            "cuts_json": {"sha256": sl.sha256_file(args.cuts)},
            "masks_json": {"sha256": sl.sha256_file(args.masks)},
        },
        "sheets": manifest_sheets,
        "outputs": {
            "candidate_master_tif": {"path": os.path.relpath(tif_path, PROJECT),
                                     "compression": "lzw", "dtype": "uint8 RGB",
                                     "bytes": os.path.getsize(tif_path)},
            "candidate_preview_png": {"path": os.path.relpath(png_path, PROJECT),
                                      "size_px": [pw, ph]},
        },
        "total_seconds": round(time.time() - t_start, 1),
    }
    man_path = os.path.join(args.outdir, "render_manifest.json")
    sl.write_canonical_json(man_path, manifest, ndigits=9)
    print("wrote %s  (total %.1fs)" % (man_path, time.time() - t_start))

    del canvas
    try:
        os.remove(canvas_path)
    except OSError:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
