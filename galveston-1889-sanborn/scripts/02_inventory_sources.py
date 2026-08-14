#!/usr/bin/env python3
"""02 -- Inventory the original scans: dimensions, checksums, provenance.

The originals in data/original/ are the one immutable thing in this project.
Everything downstream reads them and nothing ever writes back, so this script
records exactly what they were: SHA-256, byte size, pixel dimensions, format,
and any DPI the file declares. Re-running it later verifies nothing drifted.

Outputs
    data/original/INVENTORY.json
    output/qc/source_inventory.md
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sanborn.config import (load_config, paths, read_json, setup_logging,
                            sha256_file, utcnow, write_json)


def describe(path, log):
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = None
    info = {"file": path.name, "bytes": path.stat().st_size,
            "sha256": sha256_file(path)}
    try:
        with Image.open(path) as im:
            info.update(width=im.width, height=im.height, format=im.format,
                        mode=im.mode)
            dpi = im.info.get("dpi")
            if dpi:
                info["dpi"] = [float(dpi[0]), float(dpi[1])]
            info["megapixels"] = round(im.width * im.height / 1e6, 2)
    except Exception as exc:
        info["error"] = f"{type(exc).__name__}: {exc}"
        log.error("  cannot read %s: %s", path.name, exc)
    return info


def source_dir(cfg, p):
    sub = (cfg.get("paths") or {}).get("original_dir")
    return Path(cfg["_root"]) / sub if sub else p.original


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--profile", default="galveston1889")
    ap.add_argument("--verify", action="store_true",
                    help="compare against a previous inventory and fail on any change")
    args = ap.parse_args()

    cfg = load_config(args.profile)
    p = paths().ensure()
    log = setup_logging("02_inventory_sources")
    src = source_dir(cfg, p)

    files = sorted(f for f in src.glob("*")
                   if f.is_file() and f.suffix.lower() in
                   (".jpg", ".jpeg", ".tif", ".tiff", ".png", ".jp2"))
    if not files:
        log.error("no source images in %s", src)
        log.error("Run 01_fetch_sources.py first (or make_synthetic_fixture.py "
                  "for the synthetic profile).")
        return 2

    log.info("inventorying %d file(s) in %s", len(files), src)
    items = [describe(f, log) for f in files]
    for it in items:
        log.info("  %-34s %6.1f MP  %s", it["file"],
                 it.get("megapixels", 0), it["sha256"][:16])

    manifest_path = src / "MANIFEST.json"
    provenance = read_json(manifest_path) if manifest_path.exists() else {}

    inv = {"generated_utc": utcnow(), "profile": args.profile,
           "source_dir": str(src), "count": len(items), "items": items,
           "acquisition_manifest": provenance}

    out = src / "INVENTORY.json"
    if args.verify and out.exists():
        old = {i["file"]: i["sha256"] for i in read_json(out).get("items", [])}
        changed = [i["file"] for i in items
                   if i["file"] in old and old[i["file"]] != i["sha256"]]
        gone = [f for f in old if f not in {i["file"] for i in items}]
        if changed or gone:
            log.error("ORIGINALS CHANGED since the last inventory: modified=%s missing=%s",
                      changed, gone)
            return 3
        log.info("verify: all %d previously inventoried originals are unchanged", len(old))

    write_json(out, inv)

    md = ["# Source inventory", "",
          f"Generated {inv['generated_utc']} (profile `{args.profile}`)", "",
          f"Source directory: `{src}`", "",
          "| file | pixels | MP | format | bytes | SHA-256 |",
          "|---|---|---|---|---|---|"]
    for i in items:
        md.append("| {} | {} x {} | {} | {} | {:,} | `{}` |".format(
            i["file"], i.get("width", "?"), i.get("height", "?"),
            i.get("megapixels", "?"), i.get("format", "?"), i["bytes"],
            i["sha256"]))
    if provenance.get("items"):
        md += ["", "## Provenance", "",
               f"Collection: {provenance.get('collection_url','(not recorded)')}",
               f"Retrieved: {provenance.get('retrieved_utc','(not recorded)')}", "",
               "| item | chosen URL | status | resolution note |", "|---|---|---|---|"]
        for k, v in provenance["items"].items():
            md.append(f"| {k} | {v.get('chosen_url','')} | {v.get('status','')} "
                      f"| {v.get('resolution_note','')} |")
    (p.qc / "source_inventory.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    log.info("wrote %s and %s", out, p.qc / "source_inventory.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
