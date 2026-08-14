#!/usr/bin/env python3
"""10 -- Combine the warped regions into the single master reconstruction.

SEAMS, NOT BLENDS
    Where two sheets genuinely overlap, one of them wins the pixel outright,
    decided by a fixed priority. Nothing is averaged and nothing is feathered.
    Blending would soften the 1-2 px printed text and hatching that carry most
    of a Sanborn sheet's information, and averaging two slightly misaligned
    copies of a street produces a doubled line that looks like a drafting error
    the 1889 surveyors never made.

COLOUR
    No exposure matching, no histogram alignment, no colour correction. Sheets
    scanned on different days do differ slightly in tone, and that difference is
    part of the archival record. The master's colours are the scans' colours.

GAPS
    Anywhere no sheet supplies data stays transparent. Nothing is inpainted,
    extrapolated or generated. A hole in the mosaic is a true statement about
    the source material.

Outputs
    output/Galveston_1889_SelectedSheets_MASTER.tif   (lossless, tiled, BigTIFF)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import rasterio

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sanborn.config import (ProfileMismatch, load_config, paths, read_json,
                            require_profile, setup_logging,
                            sha256_file, utcnow, write_json)
from sanborn.render import OutputGrid, mosaic


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--profile", default="galveston1889")
    ap.add_argument("--out", default="", help="override the master filename")
    args = ap.parse_args()

    cfg = load_config(args.profile)
    p = paths().ensure()
    log = setup_logging("10_build_mosaic")

    gpath = p.working / "grid.json"
    if not gpath.exists():
        log.error("no %s -- run 09_warp_sources.py first", gpath)
        return 2
    gdoc = read_json(gpath)
    try:
        require_profile(gdoc, args.profile, gpath, log)
    except ProfileMismatch:
        return 6
    grid = OutputGrid.from_dict(gdoc["grid"])
    warped = gdoc["regions"]
    missing = [w["region_id"] for w in warped if not Path(w["path"]).exists()]
    if missing:
        log.error("warped rasters missing for: %s -- re-run 09", missing)
        return 3

    priority = {w["region_id"]: w.get("priority", 100) for w in warped}
    log.info("mosaicking %d region(s) onto %d x %d grid",
             len(warped), grid.width, grid.height)
    log.info("seam priority (lower wins where sheets overlap): %s",
             ", ".join(f"{k}={v}" for k, v in sorted(priority.items(), key=lambda x: x[1])))

    name = args.out or cfg["output"]["master_name"]
    out_path = p.output / name
    res = mosaic(warped, out_path, grid, priority=priority,
                 tile=int(cfg["output"].get("tile", 1024)))

    with rasterio.open(out_path) as ds:
        # Coverage from the alpha band, sampled at reduced scale -- enough to
        # report honestly without reading a multi-gigabyte band.
        step = max(1, int(max(ds.width, ds.height) / 4000))
        a = ds.read(4, out_shape=(max(1, ds.height // step), max(1, ds.width // step)))
        covered = float((a > 0).mean())
        log.info("master: %d x %d, %d band(s), dtype=%s, compression=%s",
                 ds.width, ds.height, ds.count, ds.dtypes[0],
                 ds.profile.get("compress"))
        log.info("coverage: %.1f%% of the grid carries map data; the remaining "
                 "%.1f%% is transparent (no source material -- nothing invented)",
                 100 * covered, 100 * (1 - covered))

    size = out_path.stat().st_size
    log.info("wrote %s (%.1f MB)", out_path, size / 1e6)
    write_json(p.output / "master_manifest.json", {
        "generated_utc": utcnow(), "profile": args.profile,
        "file": out_path.name, "bytes": size, "sha256": sha256_file(out_path),
        "grid": grid.to_dict(), "transform_model": gdoc.get("kind"),
        "anchor_region": gdoc.get("anchor_region"),
        "interpolation": gdoc.get("interpolation"),
        "region_order": res["order"], "coverage_fraction": covered,
        "product": "historical reconstruction (reconstruction plane, not georeferenced)",
        "notes": ["lossless DEFLATE, tiled, BigTIFF",
                  "one resampling from the original scans",
                  "no colour correction, no blending, no inpainting"],
    })
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
