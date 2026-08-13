# Galveston 1899 Sanborn — selection and 27×40 print

Pulls a chosen subset of the Galveston 1899 Sanborn fire-insurance sheets from
the UT Austin PCL map library index, zips them, and assembles them into a
print-ready 27×40 inch sheet.

Requested selection: sheets **8, 7, 6, 5, 11, 13, 15, 12, 14, 16, 41, 39, 37**
(13 sheets) plus the **Key**, taken from the **second** Galveston 1899 group on
the index page — 14 items.

Both print versions are produced: a plate montage and a geographic mosaic.

## Status

The download step has **not been run**. This environment's egress proxy
allowlist does not include `maps.lib.utexas.edu`; the gateway answers `403` to
the CONNECT, as it does for every general-web host (`lib.utexas.edu`,
`loc.gov`, `archive.org`, even `example.com`). Only package registries and
GitHub are reachable. Nothing here routes around that — the scripts are ready
to run wherever the host is reachable.

To unblock in a web session, add the host to the environment's network policy
(see https://code.claude.com/docs/en/claude-code-on-the-web) — the environment
generally has to be restarted before a policy change takes effect. Or just run
these scripts locally; they need only Python 3 and Pillow.

## Usage

Everything, in one command:

```bash
pip install Pillow
./run_all.sh out
```

That lists the groups, downloads group 2 with the Key, zips it, then renders
both the montage and the mosaic with JPEG proofs.

Step by step:

```bash
# 1. See what is actually on the page. Downloads nothing.
python3 fetch_maps.py --list

# 2. Download the second group + zip it.
python3 fetch_maps.py --group 2 --out maps

# 3. Check the fit before committing to a 97 MP render.
python3 make_print.py --src maps --probe --labels

# 4. Render.
python3 make_print.py --src maps --out galveston-1899-27x40.tif \
    --trim --labels --proof proof.jpg --pdf galveston-1899-27x40.pdf
```

### `fetch_maps.py`

Resolves URLs from the index page at run time rather than hard-coding them: it
parses every link, keeps the Galveston 1899 ones, and splits them into groups
by URL directory in page order, so `--group 2` is the second set as read
top-to-bottom. `--list` prints the groups without downloading so the choice can
be confirmed first.

Selection is exact — a requested sheet that is missing from the chosen group is
reported as an error rather than silently substituted, and the standard variant
is preferred over `(Skeleton)` unless `--skeleton` is passed. Downloads retry
with exponential backoff, are verified as decodable images, and are recorded in
`manifest.json` with SHA-256, byte size and pixel dimensions.

**On the "legend":** the 1899 listing has a *Key* but no item literally named
*Legend*; confirmed that "the key and legend" means the Key sheet alone, so
`--front` defaults to `key`. Widen it with `--front key,title,index` if the
symbol explanation turns out to sit on the title page.

### `make_print.py`

Builds a fixed **physical** size (default 27×40 in at 300 dpi = 8100×12000 px,
97.2 MP) with the DPI written into the file, so it prints at true size instead
of being "a big JPEG". Pillow's default 89.5 MP decompression-bomb guard is
below that, so the script raises the ceiling deliberately.

- `--mode grid` (default) keeps each sheet whole in its own cell — a plate-style
  montage, nothing cropped.
- `--mode mosaic` butts sheets edge-to-edge to approximate a continuous map.
  Use with `--trim` and a `--layout` file so sheets land in their true
  geographic positions.
- `--fit block` (default) sizes cells to the sheets' median aspect and centres
  the whole block, so leftover space becomes even outer margin instead of
  pooling between rows. `--fit stretch` fills the canvas and letterboxes inside
  each cell.
- The grid is chosen automatically by maximising coverage for the measured
  sheet aspect; override with `--cols`/`--rows`. A partial final row is centred
  rather than left ragged.
- `--trim` removes the uniform white scan margin, refusing to cut more than 15%
  of either dimension so a genuinely pale sheet is never gutted.
- `--probe` reports sizes, the chosen grid, cell size and the worst-case
  effective resolution, then exits. If it warns below 150 ppi, use fewer sheets
  per print or a bigger canvas.

`--layout` takes `{"sheet-08": [row, col], ...}`. `layout-provisional.json` is
a starting point inferred **only** from the order the sheets were requested
(8,7,6,5 / 11,13,15 / 12,14,16 / 41,39,37), which looks like geographic
adjacency. It must be checked against the Key sheet before the mosaic is
trusted. Sheets absent from the layout — the Key itself — are reported and
left out of the mosaic rather than silently dropped.

## Verification

Both scripts were exercised end-to-end against generated stand-in scans at
realistic dimensions (~2200–2500 px wide, portrait, with a scan margin) and a
mock index page carrying two Galveston 1899 groups:

- group discovery correctly split the two sets and ignored other years
- the 13 requested sheets were selected in order, standard variants not skeletons
- manifest + zip written, all files verified decodable
- 97.2 MP render completed in ~10 s, output confirmed 8100×12000 at 300 dpi
- border trim, labels, TIFF/JPEG-proof/PDF outputs, and mosaic-with-layout all
  confirmed working

The stand-ins are portrait (aspect ≈ 0.79), for which the auto-grid picks 4×4.
Real sheets may differ; the grid is chosen from measurement at run time, so
check `--probe` output against the real scans before rendering.
