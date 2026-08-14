# Galveston 1889 Sanborn — private high-resolution selected-sheet mosaic

A private, local, reproducible pipeline that assembles selected sheets of the
1889 Galveston, Texas Sanborn Fire Insurance Map into one seamless
high-resolution reconstruction, without publishing anything anywhere.

Selected sheets: **1, 2, 7, 8, 9, 10, 27, 29** (plus the 1889 Key and Index as
reference). Sheet 1 carries a second, geographically detached mapped area that
is deliberately excluded.

---

## ⚠️ Status: pipeline complete and validated; the real sheets were never fetched

**The source images could not be downloaded in the environment where this was
built.** The organisation's network policy denies all outbound connections to
the University of Texas hosts (and to OpenStreetMap):

```
maps.lib.utexas.edu:443    CONNECT tunnel failed, response 403
www.lib.utexas.edu:443     CONNECT tunnel failed, response 403
legacy.lib.utexas.edu:443  CONNECT tunnel failed, response 403
geodata.lib.utexas.edu:443 CONNECT tunnel failed, response 403
www.openstreetmap.org:443  CONNECT tunnel failed, response 403
overpass-api.de:443        CONNECT tunnel failed, response 403
www.loc.gov:443            CONNECT tunnel failed, response 403
web.archive.org:443        CONNECT tunnel failed, response 403
```

These are proxy CONNECT refusals — no request ever reached UT. Only
`github.com` and `pypi.org` are reachable. There is no legitimate route around
this from here, and using an unofficial mirror or an upscaled copy was ruled
out by the brief.

**So there is no mosaic of the real Galveston sheets in `output/`, and there is
no invented topology in `config/`.** What exists instead is:

* the **complete pipeline**, which will do the real job on a machine with
  ordinary internet access — one command;
* **end-to-end validation on a synthetic fixture** whose true geometry is known
  exactly, so the accuracy claims below are measured, not asserted;
* a **real audit** of UT Libraries' own georeferencing tools (that repository
  *is* on GitHub, so it could be fetched and tested);
* **evidence-based** knowledge of how UT serves these images, gathered without
  ever reaching UT.

To produce the real mosaic:

```bash
pip install -r requirements.txt
./run_all.sh galveston1889        # or  .\run_all.ps1  on Windows
```

Step 01 will stop and tell you plainly if it still cannot reach UT. Steps 03,
04 and 08 will stop until a human has looked at the Key and filled in the
layout — by design, see *Verification gates*.

---

## What the brief asked for, and what happened

| Requirement | Status |
|---|---|
| Download Key, Index and sheets 1, 2, 7–10, 27, 29 from UT PCL | **Blocked** by network policy. Discovery-based fetcher written and ready. |
| Prefer highest official resolution; no unofficial upscales | Probe logic implemented (IIIF → archival extensions → linked JPG). Evidence gathered: **UT exposes no IIIF for these maps.** |
| Use the 1889 Key to verify topology | **Gated, not faked.** Pipeline refuses to build while topology is unverified. |
| Exclude Sheet 1's detached 43rd–45th St section by editable mask | **Implemented and demonstrated** end to end on the fixture. |
| Never alter the archival source | **Enforced and verified** — checksums re-verified at export. |
| Verified sheet-topology model | Schema + consistency checker implemented; entries left empty pending the Key. |
| Street alias table | Schema + normalisation implemented; **left empty rather than guessed**. |
| Progressive transform selection, no automatic rubber-sheeting | **Implemented, and this is where the most important finding is.** |
| Seamless lossless mosaic, hard seams, no blending or inpainting | **Implemented and measured.** |
| Independent QC with seam crops and residuals | **Implemented**; 76 seam panels generated on the fixture. |
| Reproducible, one command, private | **Yes.** No imagery leaves the machine; `.gitignore` blocks it from version control. |

---

## The most important finding

The pipeline was validated against a synthetic multi-sheet fixture whose true
geometry is known exactly, so absolute error is measurable — not just
sheet-to-sheet agreement. Comparing transform families:

| model | fit residual (median) | held-out residual (median) | **error vs ground truth** |
|---|---|---|---|
| **similarity** | 2.43 px | 3.08 px | **3.81 px** (max 23 px) |
| affine | **2.09 px** | **3.07 px** | **66.11 px** (max 412 px) |

**Affine won on every residual measure, including cross-validated held-out
error, and was seventeen times worse against the truth.**

The mechanism: the extra affine freedom is spent on a slow anisotropic squeeze
and shear (solved scale_x drifting to 0.88 against scale_y 0.98, shear reaching
9°). Adjacent sheets still agree *locally*, so tie-point residuals never rise
above 1–3 px, while the far corner of the mosaic walks 400 px out of position.

This matters well beyond this project: **residual quality — even honest
held-out residual quality — cannot detect accumulated drift in a tie-point
network.** Choosing a transform by residuals alone will pick the wrong one.

Three defences are therefore built in, and each is a hard gate:

1. **Rank check.** Sheets that abut along a line yield only collinear tie
   points, and per-sheet affine is then *rank deficient*: there is an exact
   shear of the plane that fixes every seam line pointwise while deforming
   everything between. Measured on a 2×2 network — affine nullity **4**,
   similarity nullity **0**. Residuals stay near zero the whole time.
2. **Physical plausibility.** A solved sheet cannot be rotated 90°, mirrored,
   scaled by half, or sheared 9°, because no scanner does that. This gate is
   what actually rejected affine on the fixture, and it rejected a projective
   solution whose fitting residuals (0.83 px) were the best of any model while
   its sheets were rotated 97° and mirrored.
3. **Similarity by default.** Affine and projective are excluded from
   `config/project.yaml` unless real-world control points spread across the
   group are available to pin the drift.

---

## Architecture

Two products, kept deliberately separate:

* **Historical reconstruction** (`MASTER.tif`) — geometry answers only to the
  1889 sheets and the tie points between them. Carries no CRS, because claiming
  one would assert an accuracy against modern geography that it does not have.
* **Modern georeferenced derivative** (`GEOREF.tif`, optional) — the same
  pixels placed in the world by **one global transform of the finished
  mosaic**, never per sheet. Because it is a single transform over the whole
  assembly, every internal relationship survives it exactly: seams cannot open
  and modern street geometry cannot bend an 1889 block. This is the concrete
  answer to "don't let modern georeferencing distort the historical map".

### How the sheets are joined

All sheets are solved **at once** (a block adjustment), not one at a time. A
feature identified on two sheets contributes one equation forcing those sheets
to agree; every equation is solved together. One region is held at identity to
fix the gauge — a tie-point network alone determines the solution only up to a
global transform — which also makes the reconstruction plane that sheet's own
pixel grid, so **every residual in this project reads directly as original scan
pixels**.

Robustness is IRLS with a Huber loss, so one mis-clicked point cannot drag the
network. An optional conformal penalty pulls affine solutions toward
similarity. Model choice runs the three gates above, then requires a richer
model to beat the simpler one on *held-out* error by a margin.

Panorama stitching is **not** used, as instructed. Adjoining Sanborn sheets
share a boundary, not substantial duplicate imagery, and blind feature matching
on a city grid locks onto the wrong one of fifty near-identical blocks.
Correlation is used only *predictively* — warping a patch through the current
transform estimate before matching — and only to refine points a human already
identified, or to propose extras where sheets genuinely overlap.

### Image handling

**One resampling.** The solved transform is applied directly from the untouched
original to the final grid. No rotate–crop–save–rewarp chain exists anywhere,
so the master carries exactly one interpolation between archival scan and final
pixel. Mask polygons are carried through the transform *analytically* (all
models map lines to lines), so mask edges are exact and hard.

**Hard seams, no blending.** Where sheets overlap, one wins the pixel outright
by fixed priority. Feathering would smear the 1–2 px printed text that carries
most of a Sanborn sheet's information.

**No colour correction.** Sheets scanned on different days differ in tone;
that difference is archival information. QC reports tone offset separately from
structural misalignment so the two are never confused.

**Gaps stay transparent.** Nothing is inpainted, extrapolated or generated.

---

## Verification gates (why the pipeline refuses to run)

The brief's decision rule puts cartographic correctness above automation, so
several steps stop and demand a human rather than guess:

* `config/profiles/galveston1889.yaml` carries `verified: false`. Step 04
  refuses to emit a topology until a human has read the Key and set it true.
* Masks marked `confidence: UNVERIFIED` block steps 03 and 08.
* Topology is checked for symmetry, contradictory directions, unknown region
  ids, connectivity to the anchor, and any reference to an excluded region.

**Automatic page segmentation is not trusted for the Sheet 1 split.** Measured
on the fixture, the detector merged the two genuinely separate panels on Sheet 1
*and* invented a split on Sheet 9 that does not exist. It therefore only
proposes; the committed polygon is human-authored. This is the one place the
brief explicitly preferred determinism over automation, and the measurement
supports that.

---

## Audit of UT's `histmap-autogeoref-tools`

Cloned and examined directly (GitHub was reachable). **Recommendation: do not
reuse it here.** It is a bulk-throughput discovery pipeline built for ~14,000
Texas sheets at "good enough for a web map" accuracy, which is 2–3 orders of
magnitude away from an eight-sheet precision mosaic. Verified independently:

| Finding | Evidence |
|---|---|
| The committed script **does not compile** | `python -m py_compile georeferencing-automator.py` → `IndentationError: unexpected indent, line 775` (stray editor scratch: `h = 4, w =1`) |
| RMSE is **not** RMSE | L662 `totalsquarederrorft += abs(disterrorft)*2` — multiplies by 2 instead of squaring, so the quality gate admits far larger error than it reports |
| Tesseract config string is malformed | L170 builds `'--psm 11-c preserve_interword_spaces=1'` (missing space); `-c` is destroyed and the option becomes a positional argument |
| Output is **lossy** | L735 writes the GeoTIFF with `COMPRESS=JPEG, JPEG_QUALITY=90` — incompatible with this project's lossless requirement |
| Detector resolution ceiling | SSD MobileNet V2 FPNLite **320×320**, one forward pass over a whole sheet: one model pixel ≈ 16–28 scan pixels, so intersection centroids cannot reach this project's sub-10-px target |
| Model not obtainable | The trained model lives at a Texas Data Repository DOI, also blocked here; no GitHub mirror |

Two ideas were worth keeping and are reflected in this pipeline: cropping a
strip **along the street axis and rotating it** so vertically-set street names
become horizontal for OCR; and grading outputs into accuracy categories rather
than pass/fail. The GCP-matching, OCR-cleaning and warping code was rejected.

---

## What is known about the UT source URLs (without reaching UT)

Gathered from third-party pages retrievable via GitHub, so the fetcher targets
something real rather than a guess:

* Sheets are served as **flat JPEGs**, no viewer wrapper and no `/iiif/`
  segment:
  `https://maps.lib.utexas.edu/maps/sanborn/{letter-range}/txu-sanborn-{city}-{year}-{sheet}.jpg`
  (verified example: `.../d-f/txu-sanborn-dallas-1892-01.jpg`).
* Per-initial index pages exist at `/maps/sanborn/{letter}.html`, confirming
  `g.html` is the right entry point for Galveston.
* **The sheet token is not a clean padded integer.** Real values from one city
  include `01`, `45`, `1k`, `85`, `167`, `401k`, `499f` — padding is even
  inconsistent between years. **A fetcher that generates filenames by counting
  will 404 and will miss the Key.** This is why `01_fetch_sources.py` *parses
  the index page* instead.
* The letter-range directory holding Galveston is **unknown** — only `d-f` could
  be evidenced. It is deliberately not guessed; it is read from `g.html`.
* **UT exposes no IIIF for these maps.** Across all 2,676 records in UT
  Libraries' own OpenGeoMetadata Aardvark repository there are zero IIIF image
  or manifest references; the only service keys used are `schema.org/downloadUrl`,
  the COG spec, `schema.org/url`, ISO 19139 and PMTiles. The resolution probe
  still checks at run time rather than trusting this.

---

## Measured results (synthetic fixture)

Full pipeline, twelve steps, **80 seconds** end to end on eight sheets.

```
transform model selected     similarity  (affine and projective both rejected by gates)
tie observations             62 across 15 sheet pairs
fit residuals                median 2.43 px   p90 4.45   max 14.62
held-out residuals           median 3.08 px   rms 4.60   max 18.42
ABSOLUTE error vs truth      median 3.81 px   p90 13.80  max 22.93
master                       7443 x 4650, RGBA, lossless DEFLATE, tiled, BigTIFF
coverage                     93.1% (remainder transparent — nothing invented)
seam panels                  76
originals                    verified byte-identical after the run
```

Both the ≤ 5 px median target and the "nothing unexplained above 10–15 px"
target are met. Absolute error grows with distance from the anchor region
(anchor 0 px → far corner 14 px median), which is the expected behaviour of a
tie-point network with no absolute control: **choose an anchor near the middle
of the group**, and add real-world control if the outer sheets matter.

Caveat, stated plainly: these numbers characterise the *pipeline*, on
synthetic input with clean geometry and simulated 1.5 px picking noise. Real
1889 sheets carry paper distortion, drafting inconsistency and genuine
sheet-to-sheet survey disagreement, and will do worse. The QC step is built to
distinguish those two causes — it classifies each seam as `SYSTEMATIC`
(suspect the processing) or `SCATTERED` (consistent with 1889 disagreement).

---

## Project layout

```
config/           project.yaml, profiles/, street_aliases.yaml, sheet_topology.yaml
sanborn/          geometry.py (block adjustment), render.py (warp/mosaic),
                  masks.py, tiepoints.py, detect.py, qc.py, synthetic.py, config.py
scripts/          01..12 pipeline steps + make_synthetic_fixture.py
data/original/    archival scans — NEVER written to
masks/            editable region/collar polygons (GeoJSON, source-pixel coords)
gcps/             control points (CSV + GeoJSON) and residuals
working/          transforms, output grid, per-region warped rasters
output/           MASTER.tif, preview, sheet1_masked_preview.png, qc/
tests/            synthetic fixture + validate_against_truth.py
logs/             timestamped run logs
```

### Pipeline steps

| # | script | needs imagery? |
|---|---|---|
| 01 | `01_fetch_sources.py` — discover and download from UT, probe for higher resolution | network |
| 02 | `02_inventory_sources.py` — dimensions, SHA-256, provenance | yes |
| 03 | `03_build_sheet1_mask.py` — the detached-section exclusion | yes |
| 04 | `04_build_topology.py` — validate the Key-derived adjacency | no |
| 05 | `05_generate_reference_intersections.py` — OSM (optional, GEOREF only) | network |
| 06 | `06_detect_or_define_gcps.py` — assemble/refine control points | yes |
| 07 | `07_fit_and_evaluate_transforms.py` — block adjustment + model gates | no |
| 08 | `08_build_masks.py` — page collars (**swapped with 09**: masks precede warping) | yes |
| 09 | `09_warp_sources.py` — one resampling, original → final grid | yes |
| 10 | `10_build_mosaic.py` — hard-seam merge | yes |
| 11 | `11_quality_control.py` — residuals, seam panels, step metrics | yes |
| 12 | `12_export_final.py` — preview, GEOREF, checksums | yes |

---

## Editing masks, GCPs and topology

* **Masks** — `masks/*.geojson`, coordinates are **source-image pixels, y down**
  (stated in every file's `pixel_crs` field; they are *not* lon/lat). Edit in
  QGIS or a text editor. Re-run from step 08. Nothing is baked into an image,
  so a corrected polygon changes the result on the next run.
* **Control points** — `gcps/tiepoints_manual.csv`. Two rows sharing a
  `point_id` on different sheets *is* the statement "this is the same feature",
  and is what ties those sheets together. Re-run from step 06. Every row records
  its method, confidence and who selected it.
* **Topology** — edit the profile, not the generated `sheet_topology.yaml`, so
  the consistency checks are applied. Re-run step 04.

Prefer street-centreline intersections, block corners and wharf geometry.
Avoid individual buildings: they burn down and get redrawn between editions.

---

## Privacy

Local computation only. Nothing is uploaded to OldInsuranceMaps.net, Allmaps,
ArcGIS Online, GitHub or any hosted map service; no third-party image API is
called; no public URL is created. The only outbound traffic is downloading the
scans from UT (step 01) and, optionally, an OpenStreetMap street-network query
for the georeferenced derivative (step 05) — which sends no imagery.

`.gitignore` enforces this: all imagery is excluded from version control while
code, configuration, mask polygons, control points and text QC reports are
tracked, so the work is reproducible without redistributing UT's scans.

---

## Known uncertainties

1. **The real sheets have not been processed.** Every accuracy number here is
   from the synthetic fixture. Real scans will be harder.
2. **Topology and street aliases are empty**, not filled with plausible guesses.
   They require the Key.
3. **The letter-range directory and exact sheet tokens for Galveston 1889 are
   unknown** and are discovered at run time rather than guessed.
4. **No verified figure exists for the resolution of UT's Galveston 1889
   JPEGs.** Step 01 records what it actually retrieves.
5. **Automatic region segmentation is unreliable** (measured: one miss, one
   false positive on eight sheets). Sheet 1's split is human-authored.
6. **Error accumulates away from the anchor** in a tie-point-only network. With
   the real sheets, add real-world control if the outer sheets matter.
7. The georeferenced derivative has not been exercised on real coordinates —
   the fixture has none. Its code path is implemented but untested against real
   control.

## Source and licence notes

Source imagery: University of Texas Perry-Castañeda Library Map Collection,
Sanborn Fire Insurance Maps — `https://maps.lib.utexas.edu/maps/sanborn/g.html`.
Retrieval dates and per-file SHA-256 are recorded in
`data/original/MANIFEST.json` and `INVENTORY.json` when step 01 runs.

Optional reference data: OpenStreetMap, © OpenStreetMap contributors, ODbL 1.0.

UT's `histmap-autogeoref-tools` was audited but no code from it is reused.
