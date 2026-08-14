#!/usr/bin/env python3
"""08 -- Page collars and region masks for every sheet.

WHAT A MASK IS FOR
    A scanned sheet carries more than its map: scanner borders, blank paper
    collars, title blocks, and -- on Sheet 1 -- a whole second mapped area from
    somewhere else. Left in, those paint over the neighbouring sheet's
    cartography when the mosaic is assembled. The mask says which pixels are
    map.

WHAT A MASK MUST NOT DO
    It must not trim real content. Buildings, lot lines, street labels,
    dimensions, construction notes, colour coding, waterfront detail and
    marginal geographic notes all stay, unless they are genuinely outside the
    mapped region being assembled. When in doubt the mask stays wide: a little
    extra paper at a seam is a cosmetic problem, a clipped block is lost data.
    Masks are therefore conservative by default and every proposal is inset by
    a fixed, visible amount rather than fitted tightly to content.

    Masks are also HARD-EDGED. Feathering across a join would blur the 1-2 px
    printed text these sheets are made of, so sheets meet along an exact
    polygon boundary instead.

Outputs
    masks/<sheet>_collar.geojson      one polygon per mapped region
    masks/previews/<sheet>.png        what the mask keeps, drawn on the sheet
    output/qc/masks.md
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
from sanborn.config import load_config, paths, setup_logging
from sanborn.render import read_image


def source_dir(cfg, p):
    sub = (cfg.get("paths") or {}).get("original_dir")
    return Path(cfg["_root"]) / sub if sub else p.original


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--profile", default="galveston1889")
    ap.add_argument("--propose", action="store_true",
                    help="write collar proposals for sheets that have no mask yet")
    ap.add_argument("--inset", type=float, default=8.0,
                    help="pixels pulled in from the detected map edge (conservative)")
    args = ap.parse_args()

    cfg = load_config(args.profile)
    p = paths().ensure()
    log = setup_logging("08_build_masks")
    src = source_dir(cfg, p)
    (p.masks / "previews").mkdir(parents=True, exist_ok=True)

    rows, problems = [], []
    for sheet in cfg.get("sheets", []):
        sid = str(sheet["id"])
        fname = sheet.get("file", "")
        if not fname:
            problems.append(f"sheet {sid}: no 'file' set in config")
            continue
        img_path = src / fname
        if not img_path.exists():
            problems.append(f"sheet {sid}: image missing ({img_path})")
            continue
        img = read_image(img_path)
        h, w = img.shape[:2]

        regions = sheet.get("regions", [])
        mask_rel = next((r.get("mask") for r in regions if r.get("mask")), "")
        mask_path = Path(cfg["_root"]) / mask_rel if mask_rel else \
            p.masks / f"sheet{sid}_collar.geojson"

        if not mask_path.exists():
            if not args.propose:
                problems.append(
                    f"sheet {sid}: no mask at {mask_path} (run with --propose, "
                    f"then check and edit the polygon)")
                continue
            panels = detect.split_by_gaps(img)
            feats = []
            for i, reg in enumerate(regions):
                box = panels[i] if i < len(panels) else \
                    (0.03 * w, 0.03 * h, 0.97 * w, 0.97 * h)
                ring = M.rect_ring(box[0] + args.inset, box[1] + args.inset,
                                   box[2] - args.inset, box[3] - args.inset)
                feats.append(M.polygon_feature(
                    sheet=sid, region=reg["id"], ring=ring,
                    keep=reg.get("keep", True),
                    role="map_region" if reg.get("keep", True) else "excluded_region",
                    source_image=fname, confidence="UNVERIFIED",
                    defined_by="08_build_masks.py --propose (DETECTOR GUESS)",
                    note="Collar proposal. Widen rather than trim if unsure; "
                         "check that no map content is cut."))
            M.write_mask(mask_path, feats, extra={
                "status": "UNVERIFIED - detector proposal, must be checked",
                "source_image": fname, "image_size": [w, h]})
            log.warning("sheet %s: wrote PROPOSAL %s -- inspect and edit",
                        sid, mask_path.name)

        doc = M.read_mask(mask_path)
        probs = M.validate(doc, image_size=(w, h))
        for pr in probs:
            problems.append(f"sheet {sid}: {pr}")
        allr = M.regions(doc, keep_only=False)
        declared = {r["id"] for r in regions}
        got = {rid for rid, _, _ in allr}
        if declared - got:
            problems.append(f"sheet {sid}: mask lacks region(s) {sorted(declared - got)}")

        page_area = float(w * h)
        keeps = []
        for rid, ring, props in allr:
            keep = bool(props.get("keep", True))
            frac = M.ring_area(ring) / page_area
            conf = str(props.get("confidence", ""))
            log.info("sheet %-3s %-22s keep=%-5s %5.1f%% of page  [%s]",
                     sid, rid, keep, 100 * frac, conf or "?")
            if conf.upper() == "UNVERIFIED":
                problems.append(f"sheet {sid}: region {rid} still UNVERIFIED")
            if keep and frac < 0.05:
                problems.append(
                    f"sheet {sid}: region {rid} keeps only {100*frac:.1f}% of the "
                    f"page -- suspiciously small, check it is not clipping content")
            keeps.append(keep)
            rows.append({"sheet": sid, "region": rid, "keep": keep,
                         "frac": frac, "confidence": conf,
                         "defined_by": props.get("defined_by", "")})

        vis = detect.preview(img, [{"polygon": r, "label": rid}
                                   for rid, r, _ in allr],
                             keep_flags=keeps, max_dim=1500)
        cv2.imwrite(str(p.masks / "previews" / f"sheet{sid}.png"),
                    cv2.cvtColor(vis, cv2.COLOR_RGB2BGR))

    for pr in problems:
        log.error("%s", pr)

    md = ["# Masks", "", f"Profile `{args.profile}`", "",
          "Hard-edged polygons in source-pixel coordinates. Conservative by "
          "design: a mask that keeps a little blank paper is preferable to one "
          "that clips cartography.", "",
          "| sheet | region | kept | % of page | confidence | defined by |",
          "|---|---|---|---|---|---|"]
    for r in rows:
        md.append(f"| {r['sheet']} | {r['region']} | {r['keep']} | "
                  f"{100*r['frac']:.1f}% | {r['confidence']} | {r['defined_by']} |")
    if problems:
        md += ["", "## Problems", ""] + [f"- {x}" for x in problems]
    (p.qc / "masks.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    if problems:
        log.error("%d mask problem(s) -- fix before warping", len(problems))
        return 2
    log.info("all %d region mask(s) valid", len(rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
