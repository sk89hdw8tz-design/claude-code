# Galveston 1885 Sanborn Composite — Production Report (v4.4, final)

Seamless composite of the Sanborn Fire Insurance Map of Galveston, Texas
(October 1885 edition), centered on 22nd Street & Postoffice Street
(Avenue E), reconstructed from the 12 usable Library of Congress sheets
covering the surveyed grid (sheets 2-7, 9-11, 13-14 of 19; multi-panel
sheets contribute the panels that tile the grid).

## Canvas

- 18188 x 27524 px (500.6 MP), RGB, 300 ppi -> 60.6 x 91.7 in print size.
- Grid: avenues A (Water) through J (Broadway) west-east, streets 16th
  through 28th north-south. Canvas position = consensus grid + 742 px pad.
- Coverage 71.8% of canvas; the remainder is declared flat-fill gap or pad.

## Method (summary)

Whiteness-comb street detection per sheet; joint consensus grid solve
(non-uniform, per spec §5.2) with measured edge-knot corrections
re-converged from zero under a stable knot-centroid shear pivot;
piecewise-linear separable warp per sheet (single Lanczos resample, warp
border = paper tone); label-aware seam cuts (duplicate/lost ink-cluster
costs, frame-rule avoidance) with seven reviewer/profile-measured manual
cuts; seam ownership flip at 25th/Ave G; disjoint panel clips for sheet
11 (split at native x2040, clear of the AV. H label); retained exterior
sheet margins with per-side measured static scan insets; per-sheet
chromatic white balance to the measured edition paper tone
(cream-filtered sampling; mean gain limited, highlight-safe); flat gap
fill at the measured paper tone. No sharpening, no CLAHE, no inpainting,
no generative fill anywhere; gaps are honest flat paper.

## Adversarial QC

Nine independent adversarial review passes across four build revisions
(three-reviewer fleets with stall watchdogs; full verdicts and evidence
archived in the repository under sanborn/qc_record/). The final
confirmation review (v4.3) set three conditions — carry the 25th/Ave B
north row, carry the Tremont Opera block, clear the 22nd St scale bar —
all three verified delivered in v4.4 by measured profile cuts
(builder-verified crops; all other content byte-identical to the
reviewed build outside the three re-cut corridors).

Scorecard vs the two predecessor editions (the original 3-pass-QC'd v2
composite and the third-party one-page mosaic): best-of-three on tonal
uniformity (per-unit R−G spread 2.5 DN vs 16.7 / 4.6), margin/stamp
retention, cross-seam registration (22nd St mean jog 29 px vs 56 / 77),
dark-rim cleanliness (0.012% vs 0.282% / 0.023%), image quality
(single-pass resample, no ringing, no blocking), and label integrity.

## Deliverables

| file | contents |
|---|---|
| galveston_1885_composite.tif.part-aa/-ab/-ac + .sha256 | archival TIFF master, LZW, 300 ppi tags, 128-row strips; reassemble: `cat galveston_1885_composite.tif.part-* > galveston_1885_composite.tif` then `sha256sum -c galveston_1885_composite.tif.sha256` |
| galveston_1885_onepage.pdf | whole map on ONE 300-dpi page (60.6 x 91.7 in), JPEG q92 4:4:4, with the traced navigation grid as a toggleable PDF layer (default off) |
| galveston_1885_onepage_compressed.pdf | same page, q64 4:2:0, sized for messaging (~28 MB); the tiles/TIFF are the color-accurate carriers |
| galveston_1885_full.jpg | whole map, single JPEG q90 4:2:0 |
| tiles/ (15 + index) | 6144 x 5744-class tiles, q93 4:4:4, 400 px overlap, 100% coverage, under the ~100 MP iOS decode ceiling; index map at reduced scale |
| galveston_1885_atlas.pdf | 16-page 300-dpi PDF: index + the 15 tiles embedded losslessly |
| galveston_1885_nav_overlay.svg / _viewer.html | DERIVED navigation layer (traced grid; never part of the raster) and a self-contained browser viewer with layer toggle |
| MANIFEST.txt | SHA-256 + byte size for every delivered file |

All JPEGs carry 300-dpi JFIF density; the TIFF carries 300 ppi
resolution tags; no ICC profile (untagged sRGB).

## Disclosures

Consolidated from the final adversarial review (17 items, updated to
v4.4 — items 1, 4 and 7 reflect the v4.4 restorations):

1. **Blank ground at internal sheet joins** (~4.3 Mpx residual after the
   v4.4 restorations, most at Ave D x 18th adjoining the declared D-G x
   16-18 gap). The v4.3-listed losses were restored in v4.4: the TREMONT
   OPERA HO. block with its Babcock fire annotation and blocks
   601/602/156-162; the 25th/Ave B north row (T.W. English Coal Yard,
   Artificial Stone Wks, Coal Off., SCALES, lots 501-508, Scale of Feet).
   Still not carried: the block-326 lot row at Ave D x 18th (gap-adjacent;
   consult LoC sheets 2/3).
2. **Declared coverage gaps rendered as flat fill** (largest: Avenues D-G
   x 16th-18th; no 1885 sheet in the set covers that ground). Fill matches
   adjacent paper within 0-5 DN; no content is invented, ever.
3. **Sheet 3's top strip (Court House block) is not rendered** — equally
   absent from both predecessor editions; consult LoC sheet 3.
4. **Thin unrendered strips flank two avenue joins** (Ave D 22nd-23rd:
   the 1303/110-142 dimension row and a SEE SHEET No.6 note; Ave G
   20th-23rd: the 152-210 lot column). Consult LoC sheets 5/6/9.
5. **Panel-split step ~84 px at 23rd St** (sheet 11 split into two
   panels; the sheet itself is tilted ~88 px). Legible; the left arm of
   the "T" in TREMONT is clipped.
6. **Residual cross-seam jogs up to ~90 px** (22nd St mean 29 px — best
   of the three editions; 26th/27th at Ave D ~60-80 px, improved from the
   v2 edition's ~107).
7. **Scale of Feet bars: 4 of 7 corridor bars retained whole** (19th,
   22nd, 26th, plus unit 14's marginal bar); not carried at 20th D-G,
   23rd D-G/G-I and 25th A-D-adjacent positions where the cuts favor
   street-name integrity.
8. **AV. G OR WINNIE OR MENARD E. appears twice between 25th and 27th**
   (~200 px apart): both sheets' facing margins are retained with their
   SEE SHEET cross-references. Original print, complete and legible.
9. **Avenue H corridor gutter ~132 px** (panel split); the AV. H OR
   WILLIAMS E. label runs whole.
10. **J. LLOYD 10/28/85 surveyor signature absent** (sits across the
    14|13 seam; absent from both predecessor editions too).
11. **Retained scan margins by design**: four OCT. 1885 GALVESTON TEXAS
    cartouches, sheet numbers, SEE SHEET cross-references, street
    headers, waterworks/coal-shed annotations, three Library of Congress
    Map Division stamps.
12. **Per-sheet deskew up to ~3°**, single resample; measured edge rise
    identical to sources; no ringing, no blocking.
13. **Paper tone normalized across sheets** (B,G,R ≈ 218,231,236). The
    individual sheets' scan casts are not preserved; the famous "sheet 9
    green cast" of earlier editions was a tone-sampling artifact (pink
    brick wash contaminating the paper estimate) — the source sheet is
    warm, and so is its rendering here.
14. **Zero clipped and zero pure-black pixels** (exact census over all
    500,606,512 px). The darkest canvas pixels are reproduced printed ink.
15. **No scanner-bed or backing-board artifacts** (dark-rim 0.012%; no
    pure-black on any perimeter side).
16. **25th/Ave G corridor**: exactly one street label print; sheet 11's
    SEE SHEET No.4 retained; sheet 4's reciprocal No.11 note partially
    clipped by the flipped cut.
17. **Where a predecessor remains fractionally ahead**: the third-party
    one-page edition keeps raw sheet margins everywhere (at the cost of
    100-300 px registration breaks and heavy JPEG compression); the v2
    edition's 22nd St corridor carries one more scale bar variant. All
    judged cosmetic by the final review.

## Provenance

Sources: Library of Congress Sanborn scans, supplied as quality-95 JPEG
conversions of the 142 MB masters, 6450x7650 native, verified against
printed sheet numbers; SHA-256 manifest archived. The navigation overlay
is a derived tracing and is never composited into the raster.
