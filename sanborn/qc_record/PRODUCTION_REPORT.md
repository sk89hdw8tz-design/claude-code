# Production Report — Galveston 1885 Sanborn Composite

Seamless composite of the October 1885 Sanborn Fire Insurance Map of
Galveston, Texas, centered on 22nd Street & Postoffice Street (Avenue E).
Built entirely from the user-supplied scans below; no network sources were
reachable from the build environment.

## Sources

- Origin: Library of Congress, Geography & Map Division (public domain),
  item sanborn08539_001 (https://www.loc.gov/item/sanborn08539_001/).
- Supplied as: quality-95 JPEG conversions (no chroma subsampling) of the
  ~142 MB uncompressed master TIFFs, made and uploaded by the user.
  All 19 sheets, each 6450 × 7650 px (~307 dpi of the original paper).
- Every sheet's printed number was verified against its filename before
  use; SHA-256 checksums in sources/1885/manifest_1885_uploaded.txt.

## Sheets used (12 compositing units from 10 sheets)

| Unit | Sheet | Coverage (avenues × streets) | Note |
|---|---|---|---|
| 2 | 2 | A–D × 16–19 | |
| 3 | 3 | D–G × 18–20 | lower panel only |
| 4 | 4 | G–H × 25–28 | left panel only |
| 5 | 5 | G–J × 20–23 | City Park, Ball High School |
| 6 | 6 | D–G × 20–23 | **contains 22nd & Postoffice** |
| 7 | 7 | A–D × 19–22 | |
| 9 | 9 | A–D × 22–25 | slight green scan cast (see Tonal) |
| 10 | 10 | D–G × 23–26 | |
| 11a | 11 | G–H × 23–25 | left leg of L-shaped panel |
| 11b | 11 | H–I × 23–24 | upper step of L-shaped panel |
| 13 | 13 | D–G × 26–28 | upper (West-addresses) panel |
| 14 | 14 | A–D × 25–28 | |

## Sheets/panels reviewed and excluded, with reasons

- Sheet 1 — index/key sheet; used only to cross-check coverage, never in art.
- Sheet 3 upper panel — off-scale (≈18% compressed street pitch); warping it
  to fit would distort its buildings.
- Sheet 4 middle/right panels — east of Broadway, outside the downtown grid.
- Sheet 8 — Avenue A wharf strip, outside the crop.
- Sheet 11 remaining panels — Ave J–M West / 26th–31st, off the grid.
- Sheet 12 — Ave M–N & Beach Hotel, outside the crop.
- Sheet 13 lower panel — wharf blocks (33rd–35th), outside the crop.
- Sheets 15–19 — west/south of the crop (28th–34th).

## Composite geometry

- Canvas: 17,632 × 26,968 px (475 MP), avenues A–J vertical (A left),
  streets 16th–28th horizontal (16th top) — the orientation of the printed
  sheets (bay/north at left).
- Registration: street-grid detection (whiteness comb at fixed edition
  pitch, center-of-mass refinement), per-unit axis-aligned affine solved
  JOINTLY with the global positions of every street/avenue line, so the
  grid keeps the map's real, slightly non-uniform street spacing and all
  units agree where shared streets lie. Grid-line deviations from a
  uniform grid: avenues −270…+101 px, streets −141…+136 px.
- Per-unit scales: 0.995–1.016 (all within ±2%; independent template
  matching measured content placement at 6–19 px RMS per sheet).
- Each shared boundary street is contributed by exactly one sheet; the cut
  runs through the whitest row of the corridor band (avoids slicing street
  labels), with a ~30 px crossfade.
- Resampling: exactly one Lanczos pass per sheet (native scale ≈1.0);
  delivered at native resolution — no output resize anywhere.

## Tonal treatment

Per-sheet per-channel gain only (no curves, no saturation change),
equalizing each sheet's interior paper tone to the edition mean; gains
clamped to 0.93–1.08. Sheet 9's scan has a green cast that exceeds the
clamp — it remains slightly green rather than force-matched. Foxing,
stains, show-through and age are retained everywhere.

## Genuine gaps (flat paper fill, no content)

Confirmed against all 19 sheets — these areas have no on-grid source in
the 1885 edition:
- Avenues G–J × 16th–20th (partially mapped only by sheet 3's excluded
  off-scale panel).
- Avenues D–G × 16th–18th.
- Avenues H–I × 24th–25th (sheet 11's L-panel step).
- Avenue I–J columns × 23rd–28th, except G–H × 25–28 (sheet 4).
- A 69 px paper gutter inside the Avenue H corridor at 23rd–24th (the two
  panels of sheet 11 physically abut there; no block content affected).
- A thin sliver on unit 3's east rim at Avenue G (faces the disclosed
  G–J × 16–20 gap, inside the roadway).
- Two thin scan-edge bands inside street corridors at 19th (sheet 2) and
  23rd (sheet 5) where the physical scans end.
- A residual ~124 px jog of 27th Street crossing the Avenue D seam
  (sheets 14|13); the corridor itself is continuous and healthy.
Covered area: 69.1% of the canvas; every uncovered region is one of the
above or the padding ring.

## Retained original artifacts (deliberately not removed)

"SEE SHEET Nº x" cross-references, oval "Oct. 1885 GALVESTON TEXAS" date
stamps, Library of Congress "Map Division" ink stamps, and in-frame
"Scale of Feet" bars — all printed/stamped within the map frame.

## Restoration operations performed

Geometric registration, seam clipping/feathering, per-channel tonal gains
as described. Nothing else. **No AI generation, no generative fill, no
synthetic inpainting, no content synthesis of any kind was used anywhere
in this composite.** Gap areas are flat paper tone.

## Resampling factors (honesty statement)

- TIFF master & full JPEG: native composite pixels, resampling factor 1.0
  from the warped composite (each source sheet warped once at ≈×1.0).
- Tiles: native pixels, factor 1.0 (crops only).
- Tile index map: reduced overview, factor ≈0.09 (navigation aid only).
- PDF atlas: embeds the tiles losslessly at 300 dpi page size.
- Maximum honest print size: ≈58.8 × 89.9 in at 300 ppi (the assembled
  size of the original sheets). Nothing exceeds native resolution.

## QC

- Pass 1 (geometry): PASS-WITH-WARNINGS at revision 8, after seven
  failed revisions of independent adversarial review. Each failure drove
  a structural fix: consensus non-uniform grid, piecewise warp, panel
  splits, measured knot corrections, disjoint panel clips. The final
  warnings are the disclosed items above plus seven per-axis scales in
  the 1–2% band. Full history in qc_pass_1*.md.
- Pass 2 (fidelity): PASS-WITH-WARNINGS (sheet 9 gain clip -> fixed by
  highlight-safe ceiling and rebuilt; no sharpening, aging retained,
  no invented content; 4 of 5 spec landmarks located and legible,
  H. Rosenberg Bank not located in the covered area).
- Pass 3 (delivery): first run FAILED on packaging (oversized monolith
  shipped beside its split; machine-unreadable checksum path; missing
  resolution tags; tile MP figure overstated) — all fixed and re-reviewed.

## Deliverables (17,632 x 26,968 px composite)

- galveston_1885_composite.tif.part-aa/-ab/-ac — LZW TIFF master
  (549 MB total, 300 ppi resolution tags, 128-row strips), split into
  three parts under 273 MB for transfer safety. Reassemble and verify:
  `cat galveston_1885_composite.tif.part-* > galveston_1885_composite.tif`
  then `sha256sum -c galveston_1885_composite.tif.sha256`.
- galveston_1885_full.jpg — full-resolution JPEG q90 one-file archive
  (4:2:0 chroma subsampling — the tiles and TIFF are the color-accurate
  carriers).
- tiles/ — 15 JPEG tiles (35.1 MP each, 400 px overlap, q93, 4:4:4
  no chroma subsampling) + annotated index map; 100.0% canvas coverage;
  sharp zooming under the ~100 MP iOS decode ceiling.
- galveston_1885_atlas.pdf — index page + the 15 tiles embedded
  losslessly at 300 dpi page size (16 pages).
- All JPEGs carry 300 dpi JFIF density; the TIFF carries 300 ppi
  resolution tags; no ICC profile is embedded (untagged sRGB).
- Sheet 9's tonal gain runs with a highlight-safe ceiling (x0.984) so no
  channel clips; its slight residual coolness vs neighbours (~3 DN at the
  25th St seam) is source-scan character, disclosed.
- Maximum honest print size: 58.8 x 89.9 in at 300 ppi.

MANIFEST (sha256  bytes  path):
e42cfb92ea1fe96edae4e0e4d4d8bcb64d21e345d64bc42ec9356d2f9b5fcde6          9896  PRODUCTION_REPORT.md
707c739136696feaab46db83641127e57fc45b1039fcfd5f167b3832482ad10f     107112574  galveston_1885_atlas.pdf
31556330b0ebc911e2bc1bdb77ded198ee23d612f39e86b58cc07e54fb819262     272629760  galveston_1885_composite.tif.part-aa
5be9f6be9654bae5af96ed3bf15ce1033ad7f18032b869adbe8a1bb56ba23be7     272629760  galveston_1885_composite.tif.part-ab
28c4641cd347fb260d84f46d6dd2b5f52573eca24012ebf9450c3d139ac20f3d       3700838  galveston_1885_composite.tif.part-ac
60ed0206d1d019a9854207d640f51534a99c45ca0ca3951bcf45a40730ae2745            95  galveston_1885_composite.tif.sha256
8c7393ea8a602bcd94156520acd4aace611ba17570874b08fcbde15a1d88ba0f      57830222  galveston_1885_full.jpg
ac6a59c6b8e9066aa626ddfe7dd645798797ad544260345b3ce5f6e441e4a207       1081705  tiles/galveston_1885_index.jpg
a41995eeecce130ea202815911f330f605908b1646bae83403829033bd6de7ef       8655816  tiles/galveston_1885_r1c1.jpg
d3d85c3f90e391b5f6d6568c67c519b85f95b1129784cd524d77379657e9f5f1       3046769  tiles/galveston_1885_r1c2.jpg
469e2dc6f92045ec1c423dfd11cb6830b155b90e9fea04a8e5158d0b29d9dab2        975371  tiles/galveston_1885_r1c3.jpg
6c737c7f2349c25976e88904e7829933b0111e0a6a14a7b36b4f727463256760       9076951  tiles/galveston_1885_r2c1.jpg
398966158df781530793a7f505caf92cdec84e68de611600b2bb9c02a94b326f       9320393  tiles/galveston_1885_r2c2.jpg
bec7fd50873ebb5b3da8c911ade6e7eab66c592dec53c975d2b3fbc22505ae57       3604557  tiles/galveston_1885_r2c3.jpg
00538f5d1dc9748379e7763c5f9426e731737f35314ce0c00754215958f50e70       9806525  tiles/galveston_1885_r3c1.jpg
fa08a7cd53497501fd9f722ecbaed4f96a7bcc442c1ad6439c4e7180bfa87303      10628537  tiles/galveston_1885_r3c2.jpg
ea994bd79c9292a4b620ed7c0cd699df461fb496d9f3e7307ad18559c9fadf77       7939733  tiles/galveston_1885_r3c3.jpg
20695b2f21c485c85cc7c30c9d7c5c80b0735b6fe1b1325c505d99b75003b88e       9469858  tiles/galveston_1885_r4c1.jpg
26bb0fdfb2165fede328616b64fd79a111065002436ffcd8f2e1c5ddd15cc9b2       9171436  tiles/galveston_1885_r4c2.jpg
4e62d66509d45907dd0494a6f507b0abe4a57394eefc39dc12c29355b690adce       4274770  tiles/galveston_1885_r4c3.jpg
63ca3725c698ef1d186633467e89bd6a8cb32a767af4e335dd5ba48f221060e3       7867785  tiles/galveston_1885_r5c1.jpg
c53f07080ea092c979eb8f731d4c2564cf942888b3167b9899679427f67eae6f       8691461  tiles/galveston_1885_r5c2.jpg
dc263bed8dd1ab85bda957e9cdf47bb0ea1b136fceae3352fad120c70442dd8c       3491870  tiles/galveston_1885_r5c3.jpg
