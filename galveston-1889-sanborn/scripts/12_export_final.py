#!/usr/bin/env python3
"""12 -- Final deliverables, checksums, and the optional georeferenced version.

TWO PRODUCTS, KEPT SEPARATE
    MASTER.tif is the historical reconstruction. Its geometry answers only to
    the 1889 sheets and the tie points between them. It carries no CRS, because
    claiming one would imply an accuracy against modern geography that the
    reconstruction does not assert.

    GEOREF.tif, when control allows, is the same pixels placed in the world by
    ONE global transform of the finished mosaic. Because it is one transform
    over the whole assembly rather than one per sheet, every internal
    relationship in the reconstruction survives it exactly: seams cannot open
    up, and modern street geometry cannot reach in and bend an 1889 block.
    If a per-sheet fit to modern data were used instead, it would improve
    agreement with today's map and damage agreement between the sheets --
    the opposite of this project's stated priority.

    A similarity is the default for that global step for the same reason: it
    can position, rotate and scale the reconstruction, but it cannot reshape it.

INTEGRITY
    SHA-256 for every original and every output, so the archival scans can be
    proven untouched and any deliverable can be traced to the run that made it.

Outputs
    output/Galveston_1889_SelectedSheets_preview.png
    output/Galveston_1889_SelectedSheets_GEOREF.tif   (only if control exists)
    output/DELIVERABLES.json
    output/CHECKSUMS.sha256
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import rasterio
from affine import Affine

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sanborn import geometry as G
from sanborn.config import (ProfileMismatch, load_config, paths, read_json,
                            require_profile, setup_logging,
                            sha256_file, utcnow, write_json)
from sanborn.render import MASTER_PROFILE, OutputGrid, downsample_preview
from sanborn.tiepoints import read_gcp_csv


def source_dir(cfg, p):
    sub = (cfg.get("paths") or {}).get("original_dir")
    return Path(cfg["_root"]) / sub if sub else p.original


def build_georef(cfg, p, grid, transforms, log):
    """Place the finished reconstruction in the world with ONE global transform."""
    gcfg = cfg.get("georeference", {})
    if not gcfg.get("enabled", False):
        log.info("georeferencing disabled for this profile -- skipping GEOREF")
        return None

    rows = [r for r in read_gcp_csv(p.gcps / "tiepoints.csv")
            if r.get("ref_lon") not in (None, "") and r.get("ref_lat") not in (None, "")]
    need = int(gcfg.get("min_control_points", 4))
    if len(rows) < need:
        log.warning("only %d control point(s) carry real-world coordinates "
                    "(need %d) -- GEOREF not produced.", len(rows), need)
        log.warning("Add ref_lon/ref_lat to control rows (e.g. from "
                    "data/reference/intersections.geojson) and re-run.")
        return None

    # Each control point: reconstruction-plane position -> lon/lat.
    src, dst = [], []
    for r in rows:
        rid = r["region"]
        if rid not in transforms:
            continue
        uv = G.apply(np.asarray(transforms[rid], float), [(r["src_x"], r["src_y"])])[0]
        src.append(uv)
        dst.append([float(r["ref_lon"]), float(r["ref_lat"])])
    if len(src) < need:
        log.warning("after matching regions, only %d usable point(s) -- skipping", len(src))
        return None

    src = np.asarray(src, float)
    dst = np.asarray(dst, float)
    kind = gcfg.get("transform_kind", "similarity")
    H = G.fit_single(kind, src, dst)
    resid = np.linalg.norm(G.apply(H, src) - dst, axis=1)
    log.info("global %s plane->world fit on %d point(s): median residual %.3e deg",
             kind, len(src), float(np.median(resid)))

    # A plane->world map that is a pure affine can be written straight into the
    # GeoTIFF transform; no pixels move, so the mosaic is not resampled again.
    if abs(H[2, 0]) > 1e-12 or abs(H[2, 1]) > 1e-12:
        log.warning("the fitted global transform is projective; writing it as a "
                    "GeoTIFF affine would misplace the image. Falling back to a "
                    "similarity so the reconstruction is not distorted.")
        H = G.fit_single("similarity", src, dst)

    # Compose: output pixel -> plane -> world.
    s = 1.0 / grid.pixels_per_unit
    P = np.array([[s, 0, grid.u0], [0, s, grid.v0], [0, 0, 1]], dtype=float)
    W = H @ P
    return Affine(W[0, 0], W[0, 1], W[0, 2], W[1, 0], W[1, 1], W[1, 2]), \
        {"kind": kind, "n_points": len(src),
         "median_residual_deg": float(np.median(resid)),
         "max_residual_deg": float(resid.max())}


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--profile", default="galveston1889")
    args = ap.parse_args()

    cfg = load_config(args.profile)
    p = paths().ensure()
    log = setup_logging("12_export_final")

    master = p.output / cfg["output"]["master_name"]
    if not master.exists():
        log.error("no master at %s -- run 10_build_mosaic.py", master)
        return 2

    with rasterio.open(master) as ds:
        comp = str(ds.profile.get("compress", "")).lower()
        log.info("master: %d x %d, %d bands, %s, compression=%s, tiled=%s",
                 ds.width, ds.height, ds.count, ds.dtypes[0], comp,
                 ds.profile.get("tiled"))
        if comp in ("jpeg", "webp", "lerc"):
            log.error("master uses LOSSY compression (%s) -- refusing to sign off. "
                      "The archival master must be lossless.", comp)
            return 3
        if ds.count < 4:
            log.warning("master has %d band(s); an alpha band is expected so that "
                        "genuine gaps stay transparent", ds.count)

    # ---- preview -----------------------------------------------------------
    prev = downsample_preview(master, p.output / cfg["output"]["preview_name"],
                              max_dim=int(cfg["output"].get("preview_max_dim", 6000)))
    log.info("preview: %s (%d x %d, %.3fx)", Path(prev["path"]).name,
             prev["size"][0], prev["size"][1], prev["scale"])

    # ---- optional georeferenced derivative ---------------------------------
    gdoc = read_json(p.working / "grid.json")
    try:
        require_profile(gdoc, args.profile, p.working / "grid.json", log)
    except ProfileMismatch:
        return 6
    grid = OutputGrid.from_dict(gdoc["grid"])
    tdoc = read_json(p.working / "transforms.json")
    georef_info = None
    built = build_georef(cfg, p, grid, tdoc["transforms"], log)
    if built:
        transform, georef_info = built
        out = p.output / cfg["output"]["georef_name"]
        with rasterio.open(master) as srcds:
            prof = dict(MASTER_PROFILE)
            prof.update(width=srcds.width, height=srcds.height, count=srcds.count,
                        dtype=srcds.dtypes[0], transform=transform,
                        crs=cfg["georeference"].get("crs", "EPSG:4326"),
                        photometric="RGB")
            with rasterio.open(out, "w", **prof) as dstds:
                for _, win in srcds.block_windows(1):
                    dstds.write(srcds.read(window=win), window=win)
                dstds.update_tags(
                    product="modern-georeferenced derivative",
                    derivation="ONE global transform of the finished historical "
                               "reconstruction; per-sheet geometry unchanged",
                    **{k: str(v) for k, v in georef_info.items()})
        log.info("wrote %s (%s)", out.name, georef_info)

    # ---- checksums ---------------------------------------------------------
    src = source_dir(cfg, p)
    originals = sorted(f for f in src.glob("*")
                       if f.is_file() and f.suffix.lower() in
                       (".jpg", ".jpeg", ".tif", ".tiff", ".png", ".jp2"))
    outputs = [f for f in sorted(p.output.glob("*")) if f.is_file()]

    lines, deliv = [], {"generated_utc": utcnow(), "profile": args.profile,
                        "originals": [], "outputs": []}
    for f in originals:
        h = sha256_file(f)
        lines.append(f"{h}  originals/{f.name}")
        deliv["originals"].append({"file": f.name, "sha256": h,
                                   "bytes": f.stat().st_size})
    for f in outputs:
        if f.name == "CHECKSUMS.sha256":
            continue
        h = sha256_file(f)
        lines.append(f"{h}  output/{f.name}")
        deliv["outputs"].append({"file": f.name, "sha256": h,
                                 "bytes": f.stat().st_size})
    (p.output / "CHECKSUMS.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")

    inv = src / "INVENTORY.json"
    if inv.exists():
        recorded = {i["file"]: i["sha256"] for i in read_json(inv).get("items", [])}
        changed = [d["file"] for d in deliv["originals"]
                   if d["file"] in recorded and recorded[d["file"]] != d["sha256"]]
        if changed:
            log.error("ORIGINALS HAVE CHANGED since inventory: %s", changed)
            return 4
        log.info("verified: all %d original scan(s) are byte-identical to the "
                 "inventory -- nothing in this pipeline modified them", len(recorded))

    deliv["georeference"] = georef_info
    deliv["qc"] = read_json(p.qc / "qc_summary.json") if (p.qc / "qc_summary.json").exists() else None
    deliv["privacy"] = ("Local processing only. No imagery was uploaded to any "
                        "hosted service, and no public URL was created.")
    write_json(p.output / "DELIVERABLES.json", deliv)

    log.info("=== deliverables ===")
    for d in deliv["outputs"]:
        log.info("   %-52s %8.1f MB", d["file"], d["bytes"] / 1e6)
    log.info("checksums: %s", p.output / "CHECKSUMS.sha256")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
