# Galveston Sanborn wharf/downtown mosaics — production report

**Branch:** `claude/galveston-setup-part-a-mk5z1l` · **Governing spec:** cloud
addendum (recipe-first; renders are reproductions), reconciled 2026-08-30
against the original brief, now committed at `PART_B_BRIEF.md`. That
reconciliation closed HQ-1..4, added the missing `coverage.png` deliverable,
and found and fixed HQ-6 — the 1912 city recipe could not render from a
clean clone. Remaining open item: HQ-7 (`71a`).

## What the product is

`outputs/{year}/recipe/` — everything needed to rebuild either mosaic
byte-deterministically on any machine:

| piece | 1912 | 1899 |
|---|---|---|
| `inventory.json` (URL + sha256 + git mirror per source file) | ✅ 129 files | ✅ 102 files |
| `transforms.json` (per-sheet solve into the mosaic frame) | ✅ frozen prior solve | ✅ full-affine rebuild, gated |
| `seams/` (cuts + per-sheet ownership polygons) | ✅ frozen (D-018/19/23) | ✅ 19 min-ink cuts + ownership |
| `controls/` (verified correspondences) | ✅ 23 pairs | ✅ landmarks_v2 (3-source) |
| `grid.json` + `intersections/blocks/sheets.geojson` | ✅ | ✅ |
| QC scores | ✅ prior run1 + reviews | ✅ gate + guard metrics + proof panels |
| provenance | ✅ `provenance.json` | ✅ `provenance.json` |

## Tools

- **`tools/crop.py`** — address + print size → print-ready TIFF/PDF. Lazy:
  resolves the address in `grid.json`, intersects the crop with the
  ownership polygons, fetches only the needed sheets (sha256-cached under
  `work/sheets/`; git data branch first, recorded source URL second),
  warps through the frozen transforms, composites by ownership. Verified on
  1912: single-sheet crop (22nd × Postoffice) and a four-sheet corner
  (21st × Ave C) both clean.
- **`tools/render.py`** — whole-mosaic or rect render from the recipe;
  prints disk needs first; `--dry-run` stops there; `--downsample N` for
  QC previews; `--dzi` writes a DeepZoom tile pyramid of the render via
  libvips. Web-viewer tiles were NOT generated in the cloud: a
  150-ppi-equivalent set for both years (~250 MB) would push the repository
  toward its size budget, so run
  `python3 tools/render.py --year YYYY --all --downsample 2 --dzi --out t.tif`
  locally instead (addendum §A.4 path). Full 1912 at 1/1 is 24,849×21,582 px (~536 MP, ~1.6 GB
  uncompressed canvas + ~111 MB sources) — run that locally, not in the
  cloud VM (addendum §E). A 1/8 preview renders correctly in-cloud.
- **`tools/reciplib.py`** — the shared recipe loader (hash-verified lazy
  fetch, transform/ownership access, address lookup). For 1912 it rebuilds a
  missing pct:50 working image from `recipe/working_sources.json` rather than
  assuming the scratch dir survived (HQ-6).
- **`tools/lookup.py`** — modern address → block, sheet, pixel bounds, and an
  optional preview PNG (`--preview`). Parses a free-form address ("2314 Strand
  St, Galveston, TX"): on an avenue the hundred-block is the lower cross
  street, so no geocoder is needed for a block-level answer. It reports the
  frontage point plus both flanking blocks, because the house number alone
  does not say which side of the avenue the lot is on, and it says so rather
  than guessing a lot. Addresses given on a numbered street are marked LOW
  confidence (the hundred-block→avenue mapping has shifted since 1912).
  lat/lng is reported as unavailable: the mosaic frame has no EPSG:3857 solve.
  Smoke-tested on Strand/Postoffice/Mechanic/Market/Sealy in the 2000–2500
  blocks — all resolve to the expected downtown sheets (11, 13–16, 37).
- **`tools/coverage.py`** — writes `outputs/{year}/coverage.png`: every unit
  drawn in the mosaic frame, coloured by how its transform was obtained
  (frozen master core vs. fitted vs. tie-placed), with the headline count
  separating verified placements from anything carried over unverified.

- **`tools/publish.py`** — render a year full-city, then write the §5 web
  deliverables: a tiled/overviewed COG (deflate, predictor 2, 512 px blocks)
  and a `vips dzsave` DeepZoom pyramid. `--downsample 2` is the ~150
  ppi-equivalent the brief caps web tiles at.
- **`tools/tiling.py`** — the Stage 4 gate as exact polygon geometry: is the
  city one connected piece, is any ground unclaimed (holes, and since HQ-20
  inlets — channels open to the exterior), does any pixel have two owners.
  **`tools/fillgaps.py`** closes gaps a neighbour's scan can supply, splitting
  a gap between sheets when no single one covers it (ownership only, never
  pixels).
- **`tools/faces.py`** — reads every street and avenue on a plate from its
  own ink: block faces are long rules, a street is two rules a roadway apart
  with little ink between, consecutive streets are a block apart; a dynamic
  programme over the rule spikes picks the chain. Validated against the
  observers' 483 control coordinates at 2 px median. Cached in
  `recipe/plates/lattice.json`; plates whose chain is doubtful are flagged
  `weak` and never used for placement.
- **`tools/widthcheck.py`** — HQ-18's test: every accepted control coordinate
  against the plate's own corridor centre (`recipe/qc/control_widthcheck.json`).
- **`tools/latticeties.py`** — a control for every seam that had none, from
  the plates' readings; identity from the current placement (within 0.45 of
  a block) and the key maps. **`tools/streetcut.py`** cuts each seam on its
  control's corridor, trimming a sheet only inside its overlap with the
  neighbour, with the master's DP masks as the core's base.
- **`tools/seamcrops.py`** — every band seam as a 100% and 50% crop with the
  cut marked, plus `qc/seams/index.json`; the graders work from these.
- **`tools/sheetsgeo.py`** — rewrites `recipe/sheets_city.geojson` from the
  live transforms (footprint, tier, scale, rotation per unit).

Both years were rendered full-city at 1/8 in-cloud on 2026-08-30 as an
end-to-end check of the recipes: 1899 → 3795×5945, 1912 → 2547×5687. The
1899 render shows a continuous street grid through the core with visible
white wedges between some outer sheets (real registration spread, not
missing sheets) and `71a` isolated to the south (HQ-7).

**1912 published at 150 ppi (2026-08-30), in-cloud.** 20370×45493 (927 MP):
`outputs/1912/mosaic/1912_fullcity_150ppi.tif` (828 MB COG, opens under both
`gdalinfo` and `vips`) and a 19-level DeepZoom pyramid (141 MB, 19,576
tiles). Neither is committed: the COG exceeds GitHub's 100 MB per-file limit,
and the tile set will be superseded once HQ-8 (sheet 72) and HQ-9 (ring
seams) are closed. Both regenerate with one command now that the renderer
handles gigapixel output — `python3 tools/publish.py --year 1912`.

Full 300 ppi is **not** reachable in a 15 GB container: the renderer holds
the whole canvas plus a full-canvas warp per sheet, so 1912 at 1/1 (3.7 GP)
needs ~22 GB. Print-resolution output comes from `crop.py` per address, which
is what the product actually needs; a full-city 300 ppi TIFF would require
either a larger machine or a strip-wise renderer.

Determinism note: renders are deterministic for a given recipe + tool
version (fixed interpolation, integer-labeled ownership, no
machine-dependent state). They are NOT pixel-identical to the uploaded
8-27-26 masters, which were produced by the prior pipeline with flat-field
and water treatment; parity with those masters is tracked in HUMAN_QUEUE.

## 1912 — finishing pass (2026-09-01)

Three things were wrong with the city mosaic after the row-shear fix, and
each is now closed with a measurement rather than a judgement
(`HUMAN_QUEUE.md` HQ-20..22):

1. **The seams.** The white band at 57|63 was unclaimed ground, not plate
   margin: the first street cut intersected whole half-planes, so diagonal
   neighbours' cuts reached across entire sheets and left channels nobody
   owned, which the hole audit could not see. It had also replaced the 27×40
   master's own min-ink cuts on the 12 core sheets with bisector boxes.
   `streetcut.py` now trims only inside each pair's overlap and keeps the
   master's masks. Gate: one piece, 455 px² double ownership, one hole
   (the 84|85 source gap, 0.245%).
2. **The controls.** Every one of the 242 accepted controls was checked
   against the plate's own lattice reading. One pair (83|91) had read the
   mid-block alley as Avenue F on both plates — exactly the trap HQ-18
   predicted — and three observer reads were 15–19 ft past the street's
   centre; all four are corrected in place with the observer's value kept.
3. **The uncontrolled seams.** 38 seams had never had a constraint; the
   plates' lattices supplied one for each, and the network was re-solved
   with the core frozen. Sheets moved a median of 9 ft (max 95 ft, sheet
   68, whose y had never been pinned). Three side-by-side pairs (61|62,
   69|70, 76|77) had been drawing the same avenue twice, 80 ft apart.

The 144 band seams were then rendered at 100% and 50% and graded on the
brief's §6 rubric by twelve graders (`outputs/1912/qc/seams/grades/`); the
tally and the correction round are in HQ-24.

Still outside the product: the wharf sheet 5 (two panels with their own
joint transforms) is not in the city ownership, and the mosaic frame has no
EPSG:3857 solve (the geocoders and OSM are unreachable from this VM), so
`lookup.py` reports mosaic coordinates rather than lat/lng.

## 1912 — consolidated from the accepted prior build

Source: LOC `sanborn08539_004` (public domain), 13 target sheets + sheet 13
as context. The prior session network solved per-sheet similarity
transforms (gauge: sheet 10), cut seams, passed two independent reviews
(`80_review/ACCEPTANCE.md`), and rendered the 27×40 master. This work was
verified against `FREEZE_MANIFEST.json` hash-by-hash and carried into the
recipe verbatim; post-freeze decisions D-018/D-019/D-023 (street-label
repairs; ownership-only cut moves) are included per the branch tip, with
D-019/D-023 marked "pending owner approval" upstream — see HQ-3.

The corridor grid (`grid.json`) was derived from the 23 verified control
files: frontage-midline measurements (σ≈3 px) mapped through the frozen
transforms; boundary corridors (Aves C/F/I, 21st/24th) recovered from the
segment endpoints that bracket them (bracket widths 410–455 px ≈ 70–80 ft
corridors — sane). Spreads: ≤40 px per corridor across sheets.

The wharf band (sheet 5's two panels) has its own joint transforms
(`transforms_sheet5.json`); crop.py currently serves the inland grid A–K ×
16th–28th and leaves the pier band to `render.py` regions — noted as a
limitation.

## 1899 — registration rebuild

Source: UT Austin PCL scans (public domain), 12 sheets: wharf 06/07/08,
downtown 11–16, 37/39/41. The prior build's registration was never
committed (only its reports); `SEED_1899` documents its defects and sets
THE BAR (≤8 px at ground-truth landmarks, none >12). Method per the SEED
prompt, fresh code under `rebuild_1899/` (legacy pipeline firewalled):

1. Anchor placements from seed constants + pair-context lines.
2. Dense seam matching: edge-NCC patches, two-pass with landmark-informed
   bias, mutual A↔B consistency; the ~245 px corridor frontage aliasing the
   seed warns about was observed and defeated by the landmark seeds.
3. Landmarks measured three ways: original locator, edge-template matcher,
   and four *blind* relocation agents working from descriptions alone.
   Consolidation (three-source voting) splits the kept set per pair into a
   FIT half (solver constraints) and a GATE half (held out for
   `landmark_check`) so the gate is never fit to.
   Group B established that the `dash-*` centreline features are per-sheet
   drafting conventions, not shared physical points — excluded.
4. Full-affine per-sheet bundle adjustment (relative rotations up to ~1°
   and ±1% scale are real; axis-aligned and similarity models leave
   20–90 px signatures), Huber IRLS + hard rejection.
5. Gate: held-out landmarks through both transforms (the seed's
   anti-circular check, extended to full affine — disclosed deviation:
   the seed tool's axis-separable knots cannot represent rotation; it is
   also run on a knots approximation as a cross-check).
6. Seam cuts: min-ink DP paths inside the both-printed band
   (`rebuild_1899/cuts_1899.py`), then ownership polygons.

### Result vs THE BAR

| Metric | Prior build | Required | This rebuild |
|---|---|---|---|
| Step at ground-truth landmarks | up to 85 px | ≤8, none >12 | held-out median **6.7 px**; structural corners 1.9–8.6 px; over the bar: two drawn symbols at 14–20 px (drafting variance, HQ-4) and one pier-22 corner at 19.4 px where the two sheets' own wharf-overlap drawings disagree (source-level, asterisk class) |
| Lateral row step across 24th St | 48–85 px | ≤8 | held-out 13\|15 structural evidence within seam panels; its hydrant symbol 13.7 px (symbol class) |
| Vertical steps at Avenue G | −42…+64 px | ≤8 | 12\|41 1.9 · 14\|39 8.6 · 16\|37 3.5 px |
| Wharf seams (22nd/19th) | ±6 / −3…+4 px | ≤8 | 08\|07 5.9 px ✓; 07\|06 held-out pier corner 19.4 px (wharf-overlap drawing disagreement — the fit ties on the same pier sit at ~2.6 px) |
| Source coverage | 98.98% | ≥98.98% | **99.68%** within the source footprint (extent outside every sheet is unrendered by design — the prior build tinted the bay; see qc/guard_metrics.json) |
| Pure-white px | 20 | ≤50 | not comparable: prior number measured after flat-field + bay tint; raw-scan renders carry the scans' own whites (disclosed) |
| Row tone max jump | 18.48 | (guard) | **12.95** ✓ |
| Duplicated street name / hydrant | several | zero in the frozen core; **present in the outer ring** | single-writer ownership guarantees one copy per *pixel*, but it cannot prevent two misregistered sheets from each drawing their own copy of a label on their own side of the cut. The 2026-08-30 render sweep found exactly that at seam 75\|76 (~86 ft apart) and 83\|84 — see HQ-9. The core seams remain clean. |
| Generated map content | none | none | **none** — gaps stay paper-white and are counted in tool output |

**Model revision (rev2).** The first solve used a full 6-dof affine and
passed the gate at median 2.7 px — falsely: with constraints concentrated
in seam bands, the affine sheared sheet interiors by up to 13° while
satisfying the few gate points (visible immediately in the whole-canvas
render). The model is now a rigid similarity per sheet (rotation ≤0.7°,
scale spread 0.978–1.000 — physically plausible paper/scan variation), the
whole-canvas render is square, and the gate numbers below are the honest
rigid ones.

Gate protocol: 9 HELD-OUT consolidated landmarks (never fed to the solver),
median **6.7 px**. Six pairs run on landmark-only constraints because dense
content matching disagreed or was too weak (flagged in
`qc/r1_measurements.json` → `dense_flags`) — the honest fallback the seed
prompt prescribes. Pairs without a held-out landmark (08\|11, 11\|13,
13\|14, 41\|39, and the four schematic Avenue A pairs) are covered by seam
panels in `qc/proof/` rather than an independent numeric gate — disclosed
limitation.

## City-wide expansion (both years, all sheets)

Scope was extended from the 27x40 wharf/downtown footprint to the whole
island for both editions. Method: the gated downtown solve is **frozen**,
and every other sheet is placed outward from it — never the reverse, so a
weak lock in a vacant outlot stays local instead of bending the core.

| | 1899 | 1912 |
|---|---|---|
| Units placed | **89 / 90** | **92 / 92** |
| Source sheets | 87 (+3 panels; 6 excluded with cause) | 92 |
| core (gated downtown) | 12 | 12 |
| fit (content matching) | 34 | 33 |
| tie-fit / tie-translation | 12 / 28 | 4 / 34 |
| tie-single | 3 | 9 |
| prior-unverified | 1 | 0 |

Placement chain: dense edge-NCC content matching where sheets have enough
shared ink; 1D corridor-profile alignment where 2D matching aliases on
repeating lot ticks; and blind human-style tie measurement by agents where
neither works — each tie anchored to a *named* landmark (block numbers,
water-pipe junctions, named buildings, rail crossings) and cross-checked by
counting lot lines, which is what defeats the one-block (~1010 px) ambiguity
that wrecked earlier automated attempts. Ties are combined by
largest-agreeing-cluster, so a single mismeasured tie is outvoted rather
than fatal; a lone tie places a unit only when it is high-confidence and
anchored on a reliably-placed neighbour (recorded as `tie-single`).

**The one unplaced unit** is 1899 panel 71a. Two independent adjudicators
established the same physical fact: across 150-ft Broadway, sheet 28 draws
only its west ~210 px and panel 71 only its east ~150 px, leaving a ~90 px
strip of ground that **neither sheet maps**. There is nothing to tie. It
keeps its grid-prior placement and is tiered `prior-unverified`.

### Source-level disagreements found (not registration error)

- Drawn symbols (hydrants, fire-alarm boxes) sit 9-90 px apart between
  sheets that otherwise agree to a few px — the same class as HQ-4
  downtown. Ties were taken on pipes and block corners instead.
- 1899 sheet 67 is drawn ~9% larger than sheet 40; sheets 32/38 in 1912
  differ ~0.8% in scale: those seams cannot close by translation alone.
- 1899 panel 26b maps a block north of 39th St as "Cemetery, No Exposure";
  sheet 29 maps the same ground as dwellings 1102-1124.
- 1899 sheet 49 calls the 9th-St track "Galveston & Western R.R."; sheets
  47/48 call it "Galveston, La Porte & Houston (Bay Shore Line)".
- Several 1912 sheets (48, 85, 93, 99) carry **inset panels with their own
  origins**; ties to them were deliberately avoided, and they need panel
  splitting (as 1899's 26b/71a/71b already have) before final ownership.

### City ownership and indexes

`seams/ownership_city.json` gives every unit a polygon: downtown keeps the
frozen min-ink DP cuts (authoritative), and the outer city uses each unit's
Voronoi cell clipped to its printed extent — a uniform, explainable rule for
sheets whose overlaps are often only a corridor wide. 1899's address index
now spans the whole island (streets 6-46, Avenues A-M plus the outlot
half-avenues M1/2-T1/2): **1148 intersections, 1080 blocks, 90 footprints**.
`crop.py` resolves city-wide addresses (verified at 35th x Avenue O in the
southern outlots, and at the downtown crossings). The 1912 corridor grid is
still downtown-only; its key-map spans are transcribed (4 quadrants) but not
yet converted into a city-wide grid, so 1912 address lookup outside downtown
is the main piece of remaining work.

## Environment & acquisition

Cloud VM egress is proxy-restricted (no loc.gov / maps.lib.utexas.edu /
texashistory.unt.edu). All sources were previously fetched by GitHub
Actions CI (full egress; plain HTTP with browser headers, **no bot-defense
circumvention**) onto data branches, and every byte used here was verified
against the recorded sha256 before use. The toolchain installs are in
`state/ledger.json`.

## Non-negotiables honored

No generated map content anywhere; gaps stay paper-white and are counted
and disclosed by crop.py/render.py. No per-sheet white balance in the new
tools. Scan-to-scan tone differences remain visible at joins in recipe
renders (the prior 1912 master's flat-field belongs to its own render
manifest, preserved in the recipe).
