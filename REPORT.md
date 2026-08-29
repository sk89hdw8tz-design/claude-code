# Galveston Sanborn wharf/downtown mosaics — production report

**Branch:** `claude/galveston-setup-part-a-mk5z1l` · **Governing spec:** cloud
addendum (recipe-first; renders are reproductions). Part B's text was not
available in the cloud session; stage structure was reconstructed from the
addendum plus the prior-work branches, with open questions in
`HUMAN_QUEUE.md`.

## What the product is

`outputs/{year}/recipe/` — everything needed to rebuild either mosaic
byte-deterministically on any machine:

| piece | 1912 | 1899 |
|---|---|---|
| `inventory.json` (URL + sha256 + git mirror per source file) | ✅ 129 files | ✅ 102 files |
| `transforms.json` (per-sheet solve into the mosaic frame) | ✅ frozen prior solve | 🔄 rebuild in progress |
| `seams/` (cuts + per-sheet ownership polygons) | ✅ frozen (D-018/19/23) | 🔄 generator ready |
| `controls/` (verified correspondences) | ✅ 23 pairs | 🔄 3-source landmark consolidation |
| `grid.json` + `intersections/blocks/sheets.geojson` | ✅ | ✅ (grid is frame-exact; sheets pending solve) |
| QC scores | ✅ prior run1 + reviews | 🔄 |
| provenance | ✅ `provenance.json` | 🔄 |

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
  QC previews. Full 1912 at 1/1 is 24,849×21,582 px (~536 MP, ~1.6 GB
  uncompressed canvas + ~111 MB sources) — run that locally, not in the
  cloud VM (addendum §E). A 1/8 preview renders correctly in-cloud.
- **`tools/reciplib.py`** — the shared recipe loader (hash-verified lazy
  fetch, transform/ownership access, address lookup).

Determinism note: renders are deterministic for a given recipe + tool
version (fixed interpolation, integer-labeled ownership, no
machine-dependent state). They are NOT pixel-identical to the uploaded
8-27-26 masters, which were produced by the prior pipeline with flat-field
and water treatment; parity with those masters is tracked in HUMAN_QUEUE.

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

## 1899 — registration rebuild (in progress)

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
| Step at ground-truth landmarks | up to 85 px | ≤8, none >12 | structural (corners): **max 7.7 px** ✓; drawn symbols: 2 of 4 at 14–16 px — overlay evidence shows surrounding ink aligned and only the symbol offset (drafting variance, HQ-4) |
| Lateral row step across 24th St | 48–85 px | ≤8 | held-out 13\|15 landmark: **1.2 px** ✓ |
| Vertical steps at Avenue G | −42…+64 px | ≤8 | 12\|41 2.7 · 14\|39 0.6 · 16\|37 2.9 px ✓ |
| Wharf seams (22nd/19th) | ±6 / −3…+4 px | ≤8 | 07\|06 1.6 · 08\|07 7.7 px ✓ |
| Source coverage | 98.98% | ≥98.98% | **99.68%** within the source footprint (extent outside every sheet is unrendered by design — the prior build tinted the bay; see qc/guard_metrics.json) |
| Pure-white px | 20 | ≤50 | not comparable: prior number measured after flat-field + bay tint; raw-scan renders carry the scans' own whites (disclosed) |
| Row tone max jump | 18.48 | (guard) | **12.95** ✓ |
| Duplicated street name / hydrant | several | zero | single-writer ownership guarantees one copy per pixel; seam panels show no duplication; full-res sweep pending off-cloud render |
| Generated map content | none | none | **none** — gaps stay paper-white and are counted in tool output |

Gate protocol: 9 HELD-OUT consolidated landmarks (never fed to the solver),
median **2.7 px**. Six pairs run on landmark-only constraints because dense
content matching disagreed or was too weak (flagged in
`qc/r1_measurements.json` → `dense_flags`) — the honest fallback the seed
prompt prescribes. Pairs without a held-out landmark (08\|11, 11\|13,
13\|14, 41\|39, and the four schematic Avenue A pairs) are covered by seam
panels in `qc/proof/` rather than an independent numeric gate — disclosed
limitation.

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
