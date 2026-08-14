#!/usr/bin/env python3
"""08b -- Cut each sheet's mask at the street centrelines it shares with a neighbour.

WHY
    A Sanborn sheet is printed with a blank paper collar around the drawn map.
    If the mask keeps that collar, the collar of one sheet lands on top of its
    neighbour's cartography in the mosaic, and the result is a grid of white
    bands separating sheets that should butt together. That is exactly the
    "blank collars covering neighbouring maps" failure the brief warns about,
    and it is what the first real mosaic looked like.

    The fix uses geometry the sheets already agree on. Both sheets of a seam
    draw the street they share, so cutting BOTH masks exactly at that street's
    centreline makes them meet edge to edge with no overlap and no gap -- each
    sheet contributing its own half of the roadway.

    On a side with no neighbour in the selected group, the mask instead runs out
    to the mapped-area bound, so nothing real is trimmed.

MUST BE RE-RUN AFTER THE GRID CHANGES
    The cut positions come from the same centreline refinement that produces the
    control points. If the two are computed from different runs they disagree by
    tens of pixels and the seams reopen, so this is run alongside 06b.

Outputs
    masks/sheet<N>_regions.geojson   (cut polygons; excluded regions preserved)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sanborn import gridlines as GL
from sanborn import masks as M
from sanborn.config import load_config, paths, setup_logging
from sanborn.render import read_image

OPP = {"north": "south", "south": "north", "east": "west", "west": "east"}


def street_order(name):
    return int("".join(c for c in str(name) if c.isdigit()) or 0)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--profile", default="galveston1889")
    ap.add_argument("--pad", type=float, default=45.0,
                    help="inset applied when clipping the band search to the mask")
    args = ap.parse_args()

    cfg = load_config(args.profile)
    p = paths().ensure()
    log = setup_logging("08b_cut_masks_at_seams")
    root = Path(cfg["_root"])
    pos = (yaml.safe_load((p.config / "grid_positions.yaml").read_text(encoding="utf-8"))
           or {}).get("sheets", {})
    if not pos:
        log.error("no config/grid_positions.yaml")
        return 2

    neighbours = {}
    for t in cfg.get("topology", []):
        neighbours.setdefault(t["region"], set()).add(t["direction"])
        neighbours.setdefault(t["neighbour"], set()).add(OPP[t["direction"]])

    src_dir = root / ((cfg.get("paths") or {}).get("original_dir") or "data/original")
    for sid, spec in sorted(pos.items(), key=lambda kv: int(kv[0])):
        rid = spec["region"]
        img = read_image(src_dir / spec["file"])
        H, W = img.shape[:2]
        mask_path = p.masks / f"sheet{sid}_regions.geojson"
        doc = M.read_mask(mask_path)
        regs = {r[0]: r for r in M.regions(doc, keep_only=False)}
        if rid not in regs:
            log.error("sheet %s: mask has no region %s", sid, rid)
            continue
        bx0, by0, bx1, by1 = M.ring_bounds(regs[rid][1])

        R = GL.refine_grid(
            img,
            {k: float(v) for k, v in (spec.get("streets") or {}).items()},
            {k: float(v) for k, v in (spec.get("avenues") or {}).items()},
            street_bounds=(by0 + args.pad, by1 - args.pad),
            avenue_bounds=(bx0 + args.pad, bx1 - args.pad))
        st = sorted(R["streets"].items(), key=lambda kv: street_order(kv[0]))
        av = sorted(R["avenues"].items(), key=lambda kv: kv[0])
        if not st or not av:
            log.warning("sheet %s: no grid recovered; mask left unchanged", sid)
            continue

        side = neighbours.get(rid, set())
        top = st[0][1] if "north" in side else None
        bottom = st[-1][1] if "south" in side else None
        left = av[0][1] if "west" in side else None
        right = av[-1][1] if "east" in side else None

        def yline(l, x):
            return l["offset"] + l["slope"] * x

        def xline(l, y):
            return l["offset"] + l["slope"] * y

        corners = []
        for xs, ys in ((0, 0), (1, 0), (1, 1), (0, 1)):
            x = (xline(right, 0) if right is not None else bx1) if xs else \
                (xline(left, 0) if left is not None else bx0)
            y = (yline(bottom, x) if bottom is not None else by1) if ys else \
                (yline(top, x) if top is not None else by0)
            if left is not None and not xs:
                x = xline(left, y)
            if right is not None and xs:
                x = xline(right, y)
            corners.append((float(np.clip(x, 0, W)), float(np.clip(y, 0, H))))
        ring = corners + [corners[0]]

        feats = []
        for name, (_, ring0, props) in regs.items():
            if name == rid:
                feats.append(M.polygon_feature(
                    sheet=sid, region=rid, ring=ring, keep=True, role="map_region",
                    source_image=spec["file"], confidence="high",
                    defined_by="cut at the street/avenue centrelines shared with each neighbour",
                    note="Butt joint on shared centrelines; edges with no neighbour "
                         "run out to the mapped-area bound so nothing is trimmed."))
            else:
                feats.append(M.polygon_feature(
                    sheet=sid, region=name, ring=ring0,
                    keep=props.get("keep", True), role=props.get("role", ""),
                    source_image=spec["file"], confidence=props.get("confidence", ""),
                    defined_by=props.get("defined_by", ""), note=props.get("note", "")))
        M.write_mask(mask_path, feats, extra={"source_image": spec["file"],
                                              "sheet": sid, "image_size": [W, H]})
        log.info("sheet %-3s %-10s cut N=%-5s S=%-5s W=%-5s E=%-5s",
                 sid, rid, top is not None, bottom is not None,
                 left is not None, right is not None)
    log.info("masks re-cut; re-run 09 and 10")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
