#!/usr/bin/env python3
"""Render a year full-city and publish the §5 web deliverables.

    python3 tools/publish.py --year 1899 [--downsample 2]

Writes, for the chosen year:
  work/city/{year}_{ppi}ppi.tif        the flat render (scratch, gitignored)
  outputs/{year}/mosaic/{year}_fullcity_{ppi}ppi.tif   COG, deflate/predictor 2
  outputs/{year}/tiles/{year}.dzi + _files/            DeepZoom pyramid

The masters print at ~300 ppi, so --downsample 2 is the ~150 ppi-equivalent
the brief caps web tiles at. The COG carries no CRS: the mosaic frame has no
EPSG:3857 solve yet, so it is a plain tiled/overviewed GeoTIFF, not a
georeferenced one — see REPORT.md.
"""
import argparse
import os
import subprocess
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run(cmd, **kw):
    print("+", " ".join(cmd), flush=True)
    t = time.time()
    r = subprocess.run(cmd, cwd=REPO, **kw)
    if r.returncode != 0:
        sys.exit(f"failed ({r.returncode}): {' '.join(cmd)}")
    print(f"  [{time.time() - t:.0f}s]", flush=True)


def mb(p):
    if os.path.isdir(p):
        n = sum(os.path.getsize(os.path.join(d, f))
                for d, _, fs in os.walk(p) for f in fs)
    else:
        n = os.path.getsize(p)
    return n / 1e6


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", required=True, choices=["1899", "1912"])
    ap.add_argument("--downsample", type=int, default=2)
    ap.add_argument("--skip-render", action="store_true",
                    help="reuse an existing flat render")
    a = ap.parse_args()

    ppi = int(round(300 / a.downsample))
    work = os.path.join(REPO, "work", "city")
    os.makedirs(work, exist_ok=True)
    flat = os.path.join(work, f"{a.year}_{ppi}ppi.tif")

    mosaic_dir = os.path.join(REPO, "outputs", a.year, "mosaic")
    tiles_dir = os.path.join(REPO, "outputs", a.year, "tiles")
    os.makedirs(mosaic_dir, exist_ok=True)
    os.makedirs(tiles_dir, exist_ok=True)
    cog = os.path.join(mosaic_dir, f"{a.year}_fullcity_{ppi}ppi.tif")
    dzi_base = os.path.join(tiles_dir, a.year)

    if not (a.skip_render and os.path.exists(flat)):
        run([sys.executable, "tools/render.py", "--year", a.year, "--all",
             "--ppi", str(ppi),
             "--downsample", str(a.downsample), "--out", flat])
    print(f"flat render: {mb(flat):.0f} MB", flush=True)

    # COG: tiled + internal overviews, lossless deflate with the horizontal
    # predictor the brief asks for
    run(["gdal_translate", "-of", "COG", "-co", "COMPRESS=DEFLATE",
         "-co", "PREDICTOR=2", "-co", "BLOCKSIZE=512",
         "-co", "OVERVIEWS=IGNORE_EXISTING", "-co", "NUM_THREADS=ALL_CPUS",
         flat, cog])
    print(f"COG: {mb(cog):.0f} MB", flush=True)

    run(["vips", "dzsave", flat, dzi_base, "--suffix", ".jpg[Q=85]"])
    print(f"DZI: {mb(dzi_base + '_files'):.0f} MB", flush=True)

    print("\n== verification ==", flush=True)
    run(["gdalinfo", "-norat", "-noct", cog], stdout=subprocess.DEVNULL)
    print("gdalinfo: opens", flush=True)
    run(["vipsheader", cog], stdout=subprocess.DEVNULL)
    print("vips: opens", flush=True)
    print(f"\n{a.year}: {cog}\n{a.year}: {dzi_base}.dzi", flush=True)


if __name__ == "__main__":
    sys.exit(main())
