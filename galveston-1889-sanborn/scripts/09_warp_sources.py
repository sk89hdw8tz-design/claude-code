#!/usr/bin/env python3
"""09 -- Warp each region from its ORIGINAL scan onto the common grid.

ONE RESAMPLING, FROM THE ORIGINAL
    The solved transform is applied directly to the untouched source file. No
    intermediate rotate-crop-save-rewarp chain exists anywhere in this pipeline,
    so the master carries exactly one interpolation between archival scan and
    final pixel. Nothing is written as JPEG; the working rasters are lossless
    DEFLATE.

GRID
    The reconstruction plane's unit is the anchor sheet's own pixel, so at the
    default pixels_per_unit of 1.0 the master sits at the anchor scan's native
    scale and no sheet is upsampled to make room for another.

MASKS
    Each region's mask polygon is carried into the grid by transforming its
    vertices -- exact, because similarity, affine and projective all map lines
    to lines. The alpha edge is therefore hard and in exactly the right place,
    with no rasterise-then-resample softening.

Outputs
    working/warped/<region>.tif       RGBA, windowed to the region's extent
    working/grid.json                 the common output grid
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sanborn import masks as M
from sanborn.config import (ProfileMismatch, load_config, paths, read_json,
                            regions_from_config, require_profile, setup_logging,
                            write_json)
from sanborn.render import (OutputGrid, RegionSpec, build_output_grid, image_size,
                            read_image, warp_region)


def source_dir(cfg, p):
    sub = (cfg.get("paths") or {}).get("original_dir")
    return Path(cfg["_root"]) / sub if sub else p.original


def build_specs(cfg, p, transforms, log):
    src = source_dir(cfg, p)
    specs = []
    for sheet in cfg.get("sheets", []):
        for reg in sheet.get("regions", []):
            rid = reg["id"]
            if not reg.get("keep", True) or rid not in transforms:
                continue
            mask_rel = reg.get("mask")
            if not mask_rel:
                log.error("region %s has no mask declared in the profile", rid)
                return None
            mask_path = Path(cfg["_root"]) / mask_rel
            if not mask_path.exists():
                log.error("region %s: mask file not found: %s", rid, mask_path)
                log.error("Run 08_build_masks.py (with --propose for a starting "
                          "point), then check the polygon before warping.")
                return None
            doc = M.read_mask(mask_path)
            ring = None
            for r, rg, props in M.regions(doc, keep_only=False):
                if r == rid:
                    ring = rg
                    break
            if ring is None:
                log.error("mask for %s contains no polygon named %r", rid, rid)
                return None
            specs.append(RegionSpec(
                region_id=rid, sheet=str(sheet["id"]),
                source_path=str(src / sheet["file"]),
                transform=np.asarray(transforms[rid], dtype=float),
                ring=ring,
                priority=int(reg.get("priority", sheet.get("priority", 100))),
                meta={"note": reg.get("note", "")}))
    return specs


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--profile", default="galveston1889")
    args = ap.parse_args()

    cfg = load_config(args.profile)
    p = paths().ensure()
    log = setup_logging("09_warp_sources")

    tpath = p.working / "transforms.json"
    if not tpath.exists():
        log.error("no %s -- run 07_fit_and_evaluate_transforms.py first", tpath)
        return 2
    tdoc = read_json(tpath)
    try:
        require_profile(tdoc, args.profile, tpath, log)
    except ProfileMismatch:
        return 6
    transforms = {k: np.asarray(v, dtype=float) for k, v in tdoc["transforms"].items()}
    log.info("model=%s anchor=%s", tdoc["kind"], tdoc["anchor_region"])

    specs = build_specs(cfg, p, transforms, log)
    if specs is None:
        return 3
    if not specs:
        log.error("no kept regions to warp -- check that the profile declares "
                  "regions with keep: true and that 07 solved transforms for them")
        return 3

    out = cfg["output"]
    grid = build_output_grid(specs, padding=int(out.get("padding", 0)),
                             pixels_per_unit=float(out.get("pixels_per_unit", 1.0)))
    log.info("output grid: %d x %d px  (origin u0=%.1f v0=%.1f, %.3f px/unit)",
             grid.width, grid.height, grid.u0, grid.v0, grid.pixels_per_unit)
    gp = grid.width * grid.height / 1e6
    log.info("            %.1f megapixels, ~%.2f GB uncompressed RGBA", gp, gp * 4 / 1000)

    interp = out.get("interpolation", "lanczos")
    tile = int(out.get("tile", 1024))
    placed = []
    for spec in sorted(specs, key=lambda s: s.priority):
        w, h = image_size(spec.source_path)
        probs = []
        ring = np.asarray(spec.ring, dtype=float)
        if ring[:, 0].max() > w + 2 or ring[:, 1].max() > h + 2:
            probs.append(f"mask exceeds source {w}x{h}")
        if probs:
            log.error("region %s: %s", spec.region_id, "; ".join(probs))
            return 4
        log.info("warping %-16s from %-32s (%dx%d) ...", spec.region_id,
                 Path(spec.source_path).name, w, h)
        img = read_image(spec.source_path)
        info = warp_region(spec, grid, p.warped / f"{spec.region_id}.tif",
                           interp=interp, tile=tile, src_image=img)
        del img
        x0, y0, ww, hh = info["window"]
        log.info("   -> %s  window x%d y%d %dx%d", Path(info["path"]).name,
                 x0, y0, ww, hh)
        placed.append({**info, "priority": spec.priority})

    write_json(p.working / "grid.json",
               {"profile": args.profile,
                "grid": grid.to_dict(), "kind": tdoc["kind"],
                "anchor_region": tdoc["anchor_region"],
                "interpolation": interp,
                "regions": placed})
    log.info("warped %d region(s)", len(placed))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
