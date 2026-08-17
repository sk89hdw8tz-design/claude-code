# QA report — Galveston 1912 candidate master (run1)

Master: `60_master/final/candidate_master.tif`
sha256: `3c35c429cca0d4b8c823604cdcac8eaaad55fdc83da296275207b1557c1d4cb9`
Canvas 26206 x 14489 px, scale 1.0 (native).

## Stale-artifact guard

- stage1 seam_matrix: accepted (`3c35c429cca0d4b8...`)
- stage2 seam_panels: accepted (`3c35c429cca0d4b8...`)
- stage2 panel_verdicts: accepted (`3c35c429cca0d4b8...`)
- stage3 junction_panels: accepted (`3c35c429cca0d4b8...`)
- stage3 junction_verdicts: accepted (`3c35c429cca0d4b8...`)
- stage5 edge_audit: accepted (`3c35c429cca0d4b8...`)
- stage6 census: accepted (`3c35c429cca0d4b8...`)
- stage6 census_verdicts: accepted (`3c35c429cca0d4b8...`)
- stage7 ownership_audit: accepted (`3c35c429cca0d4b8...`)

## Frozen-input verification

19 hash checks against FREEZE_MANIFEST + inventory: **ALL PASS**
Note: the render manifest's status string is the tool's hardcoded 'candidate-awaiting-frozen-transforms' label; the hash evidence above shows the render consumed exactly the frozen cuts/masks/transforms.

## Stages 1-2 — seams (17)

| seam | street | along rms/worst px | across rms/worst px | tiling | drift px | verdict |
|---|---|---|---|---|---|---|
| 7-9 | 21st_or_center_st | 4.8 / 7.1 | 34.5 / 44.4 | PASS | 5.47 | **PASS** |
| 8-10 | 21st_or_center_st | 3.0 / 4.0 | 10.3 / 10.5 | PASS | 2.66 | **REVIEW** — cosmetic: mid-intersection ornament (fountain/lamp) drawn by s10 loses its top at the cut, s8 half blank (canvas ~17800-18000, 4835); geometry aligned, no cartography lost|
| 39-43 | 21st_or_center_st | 3.2 / 4.4 | 20.1 / 23.9 | PASS | 2.65 | **REVIEW** — cosmetic: s43 compass/ornament and arrow tops amputated at cut + s39's own version leaves stray tip fragments (canvas ~21730-22760, 4850); geometry aligned|
| 40-44 | 21st_or_center_st | 3.4 / 5.6 | 5.2 / 6.7 | PASS | 5.44 | **PASS** |
| 9-11 | 24th_st | 0.8 / 0.9 | 7.6 / 7.6 | PASS | 4.98 | **PASS** |
| 10-12 | 24th_st | 7.5 / 11.2 | 7.8 / 8.6 | PASS | 2.43 | **REVIEW** — cosmetic: s12 large '24TH ST.' label top-amputated at cut, only glyph bottoms show (canvas ~16590-17100, 11690-11740); geometry aligned; candidate for a future manual deviation|
| 43-49 | 24th_st | 4.0 / 5.9 | 20.4 / 24.8 | PASS | 2.42 | **PASS** |
| 44-50 | 24th_st | 2.8 / 4.2 | 23.9 / 26.7 | PASS | 4.99 | **PASS** |
| 7-8 | ave_c_or_mechanic | 6.2 / 12.8 | 17.1 / 22.7 | PASS | 2.55 | **PASS** |
| 9-10 | ave_c_or_mechanic | 20.6 / 34.8 | 28.5 / 37.7 | PASS | 0.83 | **PASS** |
| 11-12 | ave_c_or_mechanic | 9.3 / 16.5 | 62.1 / 87.6 | PASS | 2.56 | **PASS** |
| 8-39 | ave_f_or_church | 4.5 / 7.7 | 15.0 / 22.5 | PASS | 1.73 | **PASS** |
| 10-43 | ave_f_or_church | 11.0 / 20.1 | 27.0 / 36.0 | PASS | 0.56 | **PASS** |
| 12-49 | ave_f_or_church | 4.7 / 8.0 | 108.7 / 110.8 | PASS | 1.74 | **PASS** |
| 39-40 | ave_i_or_sealy | 5.0 / 7.5 | 8.4 / 14.0 | PASS | 0.93 | **REVIEW** — cosmetic: two plates' 'AVE. I' labels misaligned ~35px = ghost-doubled text at cut; margin cross-refs compose to a '4|9' chimera (s39 '40' + s40 '39'); geometry aligned|
| 43-44 | ave_i_or_sealy | 4.0 / 6.9 | 3.7 / 4.4 | PASS | 0.3 | **PASS** |
| 49-50 | ave_i_or_sealy | 3.6 / 6.2 | 10.3 / 12.1 | PASS | 0.94 | **PASS** |

Panel self-test: **PASS** (clamped-int-rect, A-owned byte-exact, B-owned byte-exact, recomposed==master, float-rect refused, shapes==rect).
Byte-exact master-vs-warp verification: **17/17 seams byte-exact** on all unambiguously-owned pixels (the master is provably the product of the frozen transforms + masks + archival sources along every seam corridor).

## Stage 3 — junctions + corners

- C_NE: **PASS** — content trims cleanly at canvas edges; 4|9 chimera documented under seam 39-40
- C_NW: **PASS** — reserved band pure white; s7 content begins with its physically-trimmed paper edge visible as faint 2-3px line (stage-5 REVIEW note); printed '5' cross-ref points into the band correctly
- C_SE: **PASS** — clean trims both edges; no backdrop
- C_SW: **PASS** — band white; s11 trim edge line (same west-edge note); margin legend note preserved
- J_21st_x_aveC: **PASS** — all four quadrants intact (Cotton Exchange etc.); single unowned core pixel is the 4-corner rounding coincidence, master white there (core unowned 1, nonwhite-in-unowned 0)
- J_21st_x_aveF: **PASS** — Cathedral and Interurban Station blocks intact; sub-glyph stray marks only (core unowned 0, nonwhite-in-unowned 0)
- J_21st_x_sealy: **PASS** — coverage full, no holes; cosmetic: s40 F.A. circle halved at Ave I cut (~25960,4700); floating Scale-of-Feet caption in 39/43 zone; per-plate 70-ft label pairs by design (core unowned 0, nonwhite-in-unowned 0)
- J_24th_x_aveC: **PASS** — cosmetic: s12 street-name glyph double-amputated at junction corner leaves an isolated wedge (~13890,11800); quadrants intact (core unowned 0, nonwhite-in-unowned 0)
- J_24th_x_aveF: **PASS** — cosmetic: bold amputated street-name fragment ('T/C' tops) floats at junction (~19890-20110,11770-11850); quadrants intact (core unowned 0, nonwhite-in-unowned 0)
- J_24th_x_sealy: **PASS** — Rosenberg Library block intact; corridors cross cleanly; only by-design label pairs (core unowned 0, nonwhite-in-unowned 0)

## Stage 4 — sheet-5 note

See `sheet5_note.md`: reserved band (canvas x 0..7460, full height) verified pixel-exactly blank (0 non-white, min 255); no sheet-5 source warped; cross-panel QA deferred to the wharf phase, not waived.

## Stage 5 — paper edge / scanner surround

- check1 paint containment: **PASS** (0 stray non-white px outside ownership)
- check2 ownership inside paper: **PASS** (all sheets 0 px2 outside page quad +2px)
- check3 page-edge proximity: **REVIEW** — 49/363 samples dark: the physically-trimmed paper edge of bay-side sheets 7/9/11 is faintly visible (1-3 px line, grey ~96-110) along the west content boundary at canvas x~7480-7540, adjacent to the blank reserved band. Not scanner surround (checks 1-2 prove no backdrop). Options: accept as the genuine plate limit, or add a ~10-15 px ownership inset in a future revision.
- check4 canvas border: **PASS-with-note** — 40 segments >30% dark are the target-extent trim slicing through drawn blocks (visually confirmed content, not backdrop).

## Stage 6 — hidden-content census

Self-test: **PASS** (hidden 200-px square detected, 44816 px2).
Method: page-isolated Otsu-within-page ink (render agent's calibration, NOT the rejected literal ink<185); ownership subtracted with 2-native-px cut-line tolerance; 548 components > 400 px2 listed; **every one of the 108 components > 2000 px2 visually inspected** against the original scans.

| verdict | n |
|---|---|
| FURNITURE-BY-DESIGN | 95 |
| OWNED-BY-NEIGHBOUR-CORRECTLY | 13 |
| **HIDDEN-CONTENT-FAIL** | **0** |

Notable (details in census_verdicts.json): the sheet-7 scale bar removal is the documented 21st St manual deviation working as designed; sheet-39's scale bar is hidden while its caption survives (floating caption, REVIEW note under seams 39-43/40-44); two sheet-9 components are paper punctures (archival defects, not cartography); compass roses/ornaments and street-name letters split at cuts are the cosmetic REVIEW items of stage 2.

## Stage 7 — source ownership

- raster exactly-one test (1/8 scale, 3275 x 1811): overlap>=2: **0 px**; interior holes: **0 px**; 412 edge-inset samples all within 51.2 px of ownership at the bay-side trim edge (master verified white there). Verdict: **PASS**.
- per-sheet transform/mask sha vs render manifest: **PASS**
- cuts follow pooled definitions: **PASS** (max mask-cut drift 5.47 px, within the 3-dp canonical rounding budget; both sides share the same rounded cut so tiling is exact)

## Open REVIEW items (all cosmetic, none geometric)

1. Split/amputated mid-street furniture at cuts: seam 8-10 ornament (~17900,4835); seam 10-12 '24TH ST.' label (~16800,11715); seam 39-43 ornament+arrow (~22200,4850); seam 39-40 ghost-doubled 'AVE. I' + '4|9' cross-ref chimera; junction glyph wedges (~13890,11800 and ~20000,11800); s39 floating 'Scale of Feet.' caption (~24890,4805). Options: accept as honest source-ownership, or record targeted manual deviations (the 21st St scale-bar deviation is the working precedent).
2. Faint trimmed paper-edge line along the west content boundary (sheets 7/9/11, canvas x~7480-7540) next to the reserved band.

No HIDDEN-CONTENT-FAIL, no misregistration beyond the plates' own drafting scatter, no scanner surround, no ownership overlap or interior hole, full provenance chain verified.

