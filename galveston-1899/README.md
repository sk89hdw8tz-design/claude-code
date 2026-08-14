# Galveston 1899 Sanborn — selection and 27×40 print

Pulls a chosen subset of the Galveston 1899 Sanborn fire-insurance sheets from
the UT Austin PCL map library index, zips them, and assembles them into a
print-ready 27×40 inch sheet.

Requested selection: sheets **8, 7, 6, 5, 11, 13, 15, 12, 14, 16, 41, 39, 37**
(13 sheets) from the **second** Galveston 1899 group on the index page.

- The **Key** and **Index** are downloaded and go in the zip, but neither is
  printed as a tile. The Key was dropped from the print by request; the index
  map is the *alignment reference*, not a tile.
- The mosaic is aligned per the index map, via `layout-index.json`.

Both print versions are produced: a plate montage and a geographic mosaic.

## Status

Complete. All 13 sheets plus the Key, the Index and 4 skeleton variants were
supplied as two hand-saved zips and ingested; both prints render at 27×40 in at
300 dpi (8100×12000 px).

The download step itself was never run here: this environment's egress
allowlist does not include `maps.lib.utexas.edu`, and the gateway answers `403`
to the CONNECT, as it does for every general-web host. `fetch_maps.py` is
written and tested against a mock index but has not been exercised against the
live site — run it somewhere the host is reachable, or keep using `ingest.py`
with hand-saved files.

## Usage

Everything, in one command:

```bash
pip install Pillow
./run_all.sh out                    # download, then render
./run_all.sh out sheets.zip         # use sheets already downloaded by hand
```

### `ingest.py` — taking a hand-saved zip

Files saved by hand carry whatever names the browser gave them, and may include
both the plain and `(Skeleton)` version of a sheet. `ingest.py` works out what
each file is, copies it under the canonical name, verifies it decodes, and
reports what is present, missing, duplicated or unidentifiable:

```bash
python3 ingest.py --src incoming.zip --out maps
```

It reads the source only — nothing is renamed or deleted in place.

**Skeletons are kept but never printed.** They carry the same sheet numbers as
the plain sheets, so leaving them in would put sheets 11–14 on the print twice;
`run_all.sh` excludes them. They are worth keeping on disk, because the
outline-only versions are often the clearest thing to read block layout from
when checking the alignment against the index map.

Step by step:

```bash
# 1. See what is actually on the page. Downloads nothing.
python3 fetch_maps.py --list

# 2. Download the second group + zip it.
python3 fetch_maps.py --group 2 --out maps

# 3. Check the fit before committing to a 97 MP render.
python3 make_print.py --src maps --exclude key,index --probe --labels

# 4. Render. --exclude keeps the Key and the index map out of the print;
#    they stay in the zip.
python3 make_print.py --src maps --exclude key,index \
    --out galveston-1899-27x40.tif \
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
  pooling between rows. In **mosaic** mode this is what keeps the map to a
  single scale: stretching sheets to a cell of a different aspect scales the
  map by different factors across and down, so a city block prints the wrong
  shape. `--fit stretch` fills the canvas instead, and warns when doing so
  would distort a mosaic.
- Mosaic tiles take their pixel boundaries from the rounded cell edges, so
  neighbours share a boundary exactly and no white hairlines appear between
  sheets on grids that do not divide the canvas evenly.

### Part-sheets (shoreline sheets that are mostly water)

A sheet at the water's edge may carry map content over only part of its area,
and some are physically half-size scans. Stretching such a sheet to fill a
mosaic cell spreads its built-up part across ground it does not cover.

`--coverage` (also printed by `--probe`) measures the ink bounding box of every
sheet and flags any that carry much less than the rest, with the direction the
content leans:

```
  sheet-06.jpg   90.9% wide x  46.4% tall  area  42.2%  <-- only 51% of the typical sheet, leans s
```

`--mosaic-scale uniform` (the default) then draws every sheet at one common
scale and anchors it in its cell, so a part-sheet occupies only the ground it
covers. `--mosaic-scale cell` restores the old fill-the-cell behaviour, which
is correct only when every sheet covers equal ground.

Pin a flagged sheet with a third element in its layout entry:

```json
{ "sheet-06": [0, 2, "s"] }
```

Anchors: `n s e w nw ne sw se c`.
- The grid is chosen automatically by maximising coverage for the measured
  sheet aspect; override with `--cols`/`--rows`. A partial final row is centred
  rather than left ragged.
- `--trim` removes the uniform white scan margin, refusing to cut more than 15%
  of either dimension so a genuinely pale sheet is never gutted.
- `--neatline` crops just inside a printed border rule where one exists. **These
  Galveston sheets have none** (see below), so it is a no-op here and `--inset`
  is used instead. A sheet with no detectable rule is left untouched and
  reported rather than mangled.
- `--exclude key,index` leaves matching files out of the print while they stay
  in the zip.
- `--probe` reports sizes, the chosen grid, cell size and the worst-case
  effective resolution, then exits. If it warns below 150 ppi, use fewer sheets
  per print or a bigger canvas.

`--layout` takes `{"sheet-08": [row, col], ...}`, row 0 = north, col 0 = west.
When a layout is given the grid is sized from the layout's **extent**, not the
image count, so a layout wider than the auto-grid cannot silently drop sheets.
Duplicate positions and malformed entries are rejected before rendering.

`layout-provisional.json` is a fallback inferred **only** from the order the
sheets were requested — it is a guess, not geography. `layout-index.json` is
the real thing, transcribed from the index map.

### `read_index.py` — aligning to the index map

The mosaic must follow the atlas, not the sheet numbering. The index map is the
authority, but its numbers are small on a full-page scan, so:

```bash
# blow the index map up into readable, overlapping tiles
python3 read_index.py tiles --src maps/00-index.jpg --out index-tiles

# transcribe positions into layout-index.json, then check it
python3 read_index.py validate --layout layout-index.json
```

`validate` prints the layout back as an ASCII map so it can be compared with the
index map at a glance, and flags duplicate cells, missing sheets, and holes
inside the footprint:

```
  (row 0 = north, col 0 = west)
      8   7   6   5
     11  13  15   .
```

`run_all.sh` uses `layout-index.json` when present and falls back to the
provisional layout with a loud warning when it is not.

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

A 24-agent adversarial review raised 20 candidate defects; 14 were refuted and
6 survived and were fixed, each with a regression test:

| Defect | Test that pins it |
| --- | --- |
| Mosaic stretched sheets to the cell aspect, distorting the map | a 500×500 px square renders 507×507 (was 507×577, 12% off) |
| Rounding tile size and origin separately left 1-px white seams | a 2×7 mosaic of solid grey has zero white rows/columns |
| `--neatline` needed numpy, undeclared against a "Pillow only" install | crops identically with numpy blocked from import |
| Cache keyed on label alone reused another group's file | refetching group 1 over group 2 reports "stale", refetches |
| README's step-by-step omitted `--exclude`, printing the Key | command corrected |
| Layout validator crashed on any non-`sheet-NN` key | validates a layout containing `00-index`/`keymap` |

Part-sheet handling is pinned by two tests that must both hold: a 2×7 mosaic of
identical sheets has no white row or column inside the block, and a set where
two sheets are half-height scans renders every reference square within 1.02×
of the others (it was 2.18× when each sheet was stretched to its cell).

### There is no neatline — what `--inset` is really doing

An independent calibration pass established that **these sheets carry no printed
border rule**. The map bleeds to the paper edge, the sheet's coverage boundary
is a *street*, and the neighbouring-sheet numbers are printed inside the map
area. That is why frame detection kept failing: there was nothing to find.

So `--inset` is not trimming a margin. Adjacent sheets **overlap** — each
repeats a strip of the neighbour — and the inset chooses how much of that
repeat to discard. Getting it wrong is not cosmetic:

| total L+R inset | result |
| --- | --- |
| 16.5% | Avenue D and Avenue G **deleted**; addresses jump 322 \| 402 |
| 8% | complete, but the avenue label prints twice (sheets still overlap) |
| **10% (5% a side)** | **correct: avenue appears once at full width** |
| 13% | avenue visibly pinched |

Verified by reading printed addresses and street names across the seam, not by
correlation — see the caution below.

### Measuring alignment on this map

The street grid is near-periodic at about 820 print px per block, and three
separate automated methods were defeated by it:

- cross-correlation with a search window under one block reported "aligned" at
  multiples of the block pitch, calling a 1663 px error 18 px;
- overlap detection by column profile returned answers one avenue pitch apart
  (~200-300 px and ~830-890 px) with weak correlation either way;
- avenue detection by colour density found different features on different
  sheets (pitch 512 vs 1022), making the ratios meaningless.

Block-number differences are also not proof: a **uniformly** displaced column
keeps a constant difference, so agreement across rows shows the error is
uniform, not that it is absent.

What does work: read the printed **street numbers and addresses** across a
seam. 16TH/17TH/18TH facing 18TH/19TH/20TH is a two-block error, unambiguously.
