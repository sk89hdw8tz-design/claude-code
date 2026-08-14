#!/usr/bin/env python3
"""03 -- Sheet 1: separate the region that belongs from the detached section.

THE PROBLEM
    Sheet 1 carries two geographically separate mapped areas on one physical
    page. The 1889 Key shows one of them belongs with sheets 2, 7-10, 27 and
    29; the other is a long narrow strip around 43rd/44th/45th Street by the
    western waterfront -- Texas Standard Oil, cattle yards, railroad ground --
    which is nowhere near the selected group. If it is left in, the mosaic
    silently contains a slab of city from somewhere else.

THE POLICY
    The archival scan is never modified. Exclusion is a MASK: an editable
    polygon in source-pixel coordinates, stored as GeoJSON, plus a raster
    alpha preview. Re-running with a corrected polygon changes the result;
    nothing is baked into an image.

    The polygon is defined BY A HUMAN, in config, after looking at the sheet
    and the Key. This script will propose candidates and draw pictures, but it
    will not decide. That is deliberate: automatic page segmentation was
    measured on the synthetic fixture and proved unreliable in both directions
    -- it merged two genuinely separate panels on one sheet and invented a
    split on another. For a single mask that determines whether the mosaic is
    right or wrong, deterministic beats clever.

    OCR of a sheet number is never used to decide this. It answers "which
    sheet", not "which part of this sheet belongs here", which is the question.

Usage
    --propose   write a starting-point mask from the detector, for editing
    (default)   validate the committed mask and render the preview

Outputs
    masks/<sheet1 mask>.geojson              editable polygons (source pixels)
    masks/sheet1_alpha_preview.png           raster alpha mask
    output/sheet1_masked_preview.png         retained vs excluded, annotated
    output/qc/sheet1_region_proposals.png    what the detector suggested
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sanborn import detect
from sanborn import masks as M
from sanborn.config import all_regions, load_config, paths, setup_logging
from sanborn.render import read_image


def source_dir(cfg, p):
    sub = (cfg.get("paths") or {}).get("original_dir")
    return Path(cfg["_root"]) / sub if sub else p.original


def find_sheet1(cfg):
    for sheet in cfg.get("sheets", []):
        if str(sheet.get("id")) == "1":
            return sheet
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--profile", default="galveston1889")
    ap.add_argument("--propose", action="store_true",
                    help="write a detector-derived starting mask for hand editing")
    args = ap.parse_args()

    cfg = load_config(args.profile)
    p = paths().ensure()
    log = setup_logging("03_build_sheet1_mask")

    sheet = find_sheet1(cfg)
    if sheet is None:
        log.error("no sheet with id '1' in profile %r", args.profile)
        return 2
    if not sheet.get("file"):
        log.error("sheet 1 has no 'file' in config -- run 01/02 first, or set it by hand")
        return 2

    img_path = source_dir(cfg, p) / sheet["file"]
    if not img_path.exists():
        log.error("sheet 1 image not found: %s", img_path)
        return 2
    img = read_image(img_path)
    h, w = img.shape[:2]
    log.info("sheet 1: %s (%dx%d)", img_path.name, w, h)

    # ---- advisory detection ------------------------------------------------
    proposals = detect.propose_regions(img)
    panels = detect.split_by_gaps(img)
    log.info("detector: %d blob proposal(s), %d projection-profile panel(s)",
             len(proposals), len(panels))
    for i, b in enumerate(panels):
        log.info("   panel %d: x %.0f-%.0f  y %.0f-%.0f", i, b[0], b[2], b[1], b[3])

    vis_items = [{"polygon": np.array(M.rect_ring(*b), dtype=float),
                  "label": f"panel {i}"} for i, b in enumerate(panels)]
    vis = detect.preview(img, vis_items, keep_flags=[True] * len(vis_items))
    cv2.imwrite(str(p.qc / "sheet1_region_proposals.png"),
                cv2.cvtColor(vis, cv2.COLOR_RGB2BGR))
    log.info("wrote %s", p.qc / "sheet1_region_proposals.png")

    if len(panels) != 2:
        log.warning("detector did NOT cleanly find two regions on sheet 1. "
                    "This is expected to be unreliable -- define the polygons "
                    "by hand from the image and the Key.")

    mask_rel = ""
    for reg in sheet.get("regions", []):
        mask_rel = reg.get("mask") or mask_rel
    mask_path = Path(cfg["_root"]) / mask_rel if mask_rel else \
        p.masks / "sheet1_regions.geojson"

    # ---- propose mode ------------------------------------------------------
    if args.propose:
        if mask_path.exists():
            log.error("%s already exists -- refusing to overwrite a mask that may "
                      "contain hand corrections. Delete it first if you really "
                      "want a fresh proposal.", mask_path)
            return 3
        cfg_regions = [r for r in all_regions(cfg) if r["sheet"] == "1"]
        feats = []
        for i, reg in enumerate(cfg_regions):
            box = panels[i] if i < len(panels) else (0.05 * w, 0.05 * h, 0.95 * w, 0.95 * h)
            feats.append(M.polygon_feature(
                sheet="1", region=reg["id"], ring=M.rect_ring(*box),
                keep=reg.get("keep", True),
                role="map_region" if reg.get("keep", True) else "excluded_region",
                source_image=img_path.name,
                confidence="UNVERIFIED",
                defined_by="03_build_sheet1_mask.py --propose (DETECTOR GUESS)",
                note="STARTING POINT ONLY. Check against the 1889 Key and edit."))
        M.write_mask(mask_path, feats, extra={
            "status": "UNVERIFIED - detector proposal, must be checked by a human",
            "source_image": img_path.name, "image_size": [w, h]})
        log.warning("wrote PROPOSAL %s -- edit it, then set confidence to 'high' "
                    "and defined_by to your own note.", mask_path)
        return 0

    # ---- validate a committed mask ----------------------------------------
    if not mask_path.exists():
        log.error("no Sheet 1 mask at %s", mask_path)
        log.error("Run with --propose for a starting point, then edit it by hand.")
        return 4

    doc = M.read_mask(mask_path)
    problems = M.validate(doc, image_size=(w, h))
    for prob in problems:
        log.error("mask problem: %s", prob)
    if problems:
        return 5

    allr = M.regions(doc, keep_only=False)
    kept = [(rid, ring, pr) for rid, ring, pr in allr if pr.get("keep", True)]
    dropped = [(rid, ring, pr) for rid, ring, pr in allr if not pr.get("keep", True)]
    log.info("mask defines %d region(s): %d retained, %d excluded",
             len(allr), len(kept), len(dropped))
    for rid, ring, pr in allr:
        x0, y0, x1, y1 = M.ring_bounds(ring)
        log.info("   %-24s keep=%-5s area=%.1f Mpx  bbox x %.0f-%.0f y %.0f-%.0f  [%s]",
                 rid, pr.get("keep", True), M.ring_area(ring) / 1e6, x0, x1, y0, y1,
                 pr.get("confidence", "?"))

    unver = [rid for rid, _, pr in allr
             if str(pr.get("confidence", "")).upper() == "UNVERIFIED"]
    if unver:
        log.error("regions still marked UNVERIFIED: %s", unver)
        log.error("Compare each against the 1889 Key, correct the polygon, and "
                  "set its confidence before continuing.")
        return 6
    if not dropped:
        log.warning("no region on sheet 1 is marked keep:false. If the detached "
                    "43rd-45th Street section is present on this page, it is NOT "
                    "being excluded.")

    # ---- alpha preview + annotated preview --------------------------------
    alpha = M.rasterize([r for _, r, pr in allr if pr.get("keep", True)], (h, w))
    scale = min(1.0, 2000 / max(h, w))
    cv2.imwrite(str(p.masks / "sheet1_alpha_preview.png"),
                cv2.resize(alpha, (int(w * scale), int(h * scale)),
                           interpolation=cv2.INTER_NEAREST))

    items = [{"polygon": ring, "label": rid} for rid, ring, _ in allr]
    keeps = [pr.get("keep", True) for _, _, pr in allr]
    vis = detect.preview(img, items, keep_flags=keeps, max_dim=2000)
    banner = np.full((46, vis.shape[1], 3), 24, dtype=np.uint8)
    cv2.putText(banner, "SHEET 1 -- green = retained in mosaic, red = detached "
                        "section EXCLUDED (archival scan unmodified)",
                (10, 31), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (240, 240, 240), 1, cv2.LINE_AA)
    out = np.vstack([banner, vis])
    cv2.imwrite(str(p.output / "sheet1_masked_preview.png"),
                cv2.cvtColor(out, cv2.COLOR_RGB2BGR))
    log.info("wrote %s", p.output / "sheet1_masked_preview.png")
    log.info("wrote %s", p.masks / "sheet1_alpha_preview.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
