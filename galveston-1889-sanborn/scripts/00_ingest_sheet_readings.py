#!/usr/bin/env python3
"""00 -- Turn human/agent sheet readings into config, masks and grid positions.

The readings are what somebody actually read off the printed sheets: the sheet
number in the corner, the continuation notes at each edge, the street and avenue
names with roughly where they run, the block numbers, and the extent of the
drawn map area. This script converts that into the machine-readable artefacts
the pipeline consumes, and -- importantly -- CHECKS it rather than trusting it.

Checks performed
  * every continuation note that points at another of our sheets must be
    reciprocated by that sheet, in the opposite direction;
  * street and avenue names are normalised so that "22ND ST.", "22nd Street"
    and "22ND ST. 80'" all become the same identity, because a crossing is only
    a tie point if both sheets call it the same thing;
  * a sheet declaring more than one panel (Sheet 1) gets one mask polygon per
    panel, and only the panel that belongs with the group is kept.

Outputs
    config/grid_positions.yaml     approximate street/avenue positions per sheet
    config/sheet_readings.yaml     the readings themselves, for the record
    masks/sheet<N>_regions.geojson one polygon per mapped region
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sanborn import masks as M
from sanborn.config import load_config, paths, setup_logging, write_yaml

OPPOSITE = {"north": "south", "south": "north", "east": "west", "west": "east"}
EDGE_DIR = {"top": "north", "bottom": "south", "left": "west", "right": "east"}


def norm_street(printed):
    """'22ND ST. 80'' -> '22nd';  '23RD OR TREMONT' -> '23rd'."""
    m = re.search(r"(\d+)\s*(ST|ND|RD|TH)\b", str(printed).upper())
    if not m:
        m = re.search(r"(\d+)", str(printed))
        return m.group(1) if m else str(printed).strip()
    n = int(m.group(1))
    suf = {1: "st", 2: "nd", 3: "rd"}.get(n % 10 if n % 100 not in (11, 12, 13) else 0, "th")
    return f"{n}{suf}"


def norm_avenue(printed, letter=""):
    """'AV. B OR STRAND E.' -> 'B'. The letter is the stable identity."""
    if letter and re.fullmatch(r"[A-Z]", str(letter).strip().upper()):
        return str(letter).strip().upper()
    m = re.search(r"AV(?:E|ENUE)?\.?\s*([A-Z])\b", str(printed).upper())
    return m.group(1) if m else str(printed).strip().upper()


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--profile", default="galveston1889")
    ap.add_argument("--readings", required=True,
                    help="JSON array of per-sheet readings")
    ap.add_argument("--keep-panel", default="",
                    help="for a multi-panel sheet: SHEET:PANEL_INDEX to retain, "
                         "e.g. 1:1 keeps the second panel of sheet 1")
    args = ap.parse_args()

    cfg = load_config(args.profile)
    p = paths().ensure()
    log = setup_logging("00_ingest_sheet_readings")
    root = Path(cfg["_root"])

    readings = json.loads(Path(args.readings).read_text(encoding="utf-8"))
    readings = [r for r in readings if isinstance(r, dict) and r.get("sheet")]
    by_sheet = {str(r["sheet"]): r for r in readings}
    log.info("ingesting %d sheet reading(s): %s", len(by_sheet), sorted(by_sheet))

    keep_panel = {}
    for spec in filter(None, args.keep_panel.split(",")):
        s, i = spec.split(":")
        keep_panel[s.strip()] = int(i)

    # ---- reciprocity of continuation notes --------------------------------
    claims = defaultdict(dict)
    for sid, r in by_sheet.items():
        for c in r.get("continuations", []):
            d = EDGE_DIR.get(c.get("edge", ""))
            tgt = str(c.get("sheet_referenced", "")).strip()
            if d and tgt:
                claims[sid][d] = tgt
    problems, adjacency = [], []
    for sid, dirs in sorted(claims.items()):
        for d, tgt in sorted(dirs.items()):
            if tgt not in by_sheet:
                continue                      # points outside our eight sheets
            back = claims.get(tgt, {}).get(OPPOSITE[d])
            if back != sid:
                problems.append(
                    f"sheet {sid} says {d} -> {tgt}, but sheet {tgt} does not say "
                    f"{OPPOSITE[d]} -> {sid} (it says {back!r})")
            adjacency.append({"a": sid, "b": tgt, "direction": d,
                              "reciprocated": back == sid})
    for x in problems:
        log.warning("RECIPROCITY: %s", x)
    log.info("%d adjacency claim(s) between our sheets, %d reciprocated",
             len(adjacency), sum(1 for a in adjacency if a["reciprocated"]))

    # ---- grid positions ----------------------------------------------------
    grid = {"note": "Approximate centreline positions read from the printed "
                    "labels. Identity comes from here; precision comes from "
                    "06b_grid_control_points.py.",
            "sheets": {}}
    sheets_cfg = {str(s["id"]): s for s in cfg.get("sheets", [])}
    for sid, r in sorted(by_sheet.items(), key=lambda kv: int(kv[0])):
        panels = r.get("panels") or []
        idx = keep_panel.get(sid, 0)
        panel = panels[idx] if len(panels) > idx else None
        region_id = (sheets_cfg.get(sid, {}).get("regions") or [{}])[0].get("id", f"S{sid}")
        if sid in keep_panel:
            regs = sheets_cfg.get(sid, {}).get("regions") or []
            kept = [x for x in regs if x.get("keep", True)]
            if kept:
                region_id = kept[0]["id"]

        streets, avenues = {}, {}
        for s in r.get("streets", []):
            y = float(s.get("approx_y_px", -1))
            if y < 0:
                continue
            if panel and not (panel["y0"] - 40 <= y <= panel["y1"] + 40):
                continue
            if panel and "x0" in panel:
                pass  # streets span the panel; y-test above is the discriminator
            streets[norm_street(s.get("printed", s.get("number", "")))] = round(y, 1)
        for a in r.get("avenues", []):
            x = float(a.get("approx_x_px", -1))
            if x < 0:
                continue
            if panel and not (panel["x0"] - 40 <= x <= panel["x1"] + 40):
                continue
            avenues[norm_avenue(a.get("printed", ""), a.get("letter", ""))] = round(x, 1)

        grid["sheets"][sid] = {
            "file": sheets_cfg.get(sid, {}).get("file", ""),
            "region": region_id,
            "streets": streets,
            "avenues": avenues,
        }
        log.info("sheet %-3s region %-14s streets=%s avenues=%s", sid, region_id,
                 sorted(streets), sorted(avenues))

    write_yaml(p.config / "grid_positions.yaml", grid, header=(
        "Approximate street/avenue centreline positions, per sheet.\n"
        "Generated by 00_ingest_sheet_readings.py from readings of the printed\n"
        "sheets. These supply IDENTITY; 06b measures the precise positions."))

    # ---- masks -------------------------------------------------------------
    for sid, r in sorted(by_sheet.items(), key=lambda kv: int(kv[0])):
        fname = sheets_cfg.get(sid, {}).get("file", "")
        panels = r.get("panels") or []
        area = r.get("mapped_area") or {}
        feats = []
        regs = sheets_cfg.get(sid, {}).get("regions") or []
        if len(panels) > 1 and len(regs) >= len(panels):
            keep_idx = keep_panel.get(sid, 0)
            for i, pan in enumerate(panels):
                reg = regs[i]
                feats.append(M.polygon_feature(
                    sheet=sid, region=reg["id"],
                    ring=M.rect_ring(pan["x0"], pan["y0"], pan["x1"], pan["y1"]),
                    keep=(i == keep_idx),
                    role="map_region" if i == keep_idx else "excluded_region",
                    source_image=fname, confidence="high",
                    defined_by="read from the sheet and checked against the 1889 Key",
                    note=pan.get("what_it_shows", "")[:400]))
        else:
            reg = regs[0] if regs else {"id": f"S{sid}"}
            if not area:
                log.warning("sheet %s: no mapped_area; skipping mask", sid)
                continue
            feats.append(M.polygon_feature(
                sheet=sid, region=reg["id"],
                ring=M.rect_ring(area["x0"], area["y0"], area["x1"], area["y1"]),
                keep=True, role="map_region", source_image=fname,
                confidence="high",
                defined_by="drawn map area read from the sheet",
                note=str(area.get("how_determined", ""))[:400]))
        out = p.masks / f"sheet{sid}_regions.geojson"
        M.write_mask(out, feats, extra={"source_image": fname,
                                        "sheet": sid,
                                        "status": "read from the printed sheet"})
        log.info("wrote %s (%d region(s))", out.name, len(feats))

    write_yaml(p.config / "sheet_readings.yaml",
               {"readings": readings, "adjacency_claims": adjacency,
                "reciprocity_problems": problems},
               header="Verbatim sheet readings, kept for the record.")
    log.info("done. Review config/grid_positions.yaml before running 06b.")
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
