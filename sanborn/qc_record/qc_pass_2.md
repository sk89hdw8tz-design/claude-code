# QC Pass 2 — Fidelity review (1885 Galveston Sanborn composite)

Independent adversarial reviewer, image-quality scope only (geometry already
passed in Pass 1 and was not re-litigated). Every judgement below is from
crops extracted from the real files with python3/cv2 and viewed directly.

- Composite under test: `build/1885/galveston_1885_composite.tif`
  — 17632 x 26968, uint8, LZW, photometric=RGB (1 row/strip).
- Sources: `sources/1885/Galveston_1885_sheet_NN.jpg`, 6450 x 7650 each.
- Working crops written to `/tmp/claude-0/-home-user-claude-code/2bd63ebc-a879-5d86-b98a-dc1ab929f20f/scratchpad/qc2/`.
- Canvas geometry used: `x = ave_index*1856 + 464`, `y = (street-16)*2170 + 464`.

**Channel-order sanity (prerequisite for item 5):** the TIFF is tagged
photometric=2 (RGB). Read as RGB it renders brick washes as pink
(R=226.8, G=179.2, B=179.2) and water/cistern washes as blue
(R=150.4, G=182.5, B=194.8). The source JPEGs decoded through
`cv2.imread` + `BGR2RGB` give the same hues. **No BGR/RGB swap.**

---

## 1. Legibility at 100% — **PASS**

Six 1:1 (one composite pixel = one screen pixel) crops, 1150x820, at
scattered locations including two at seams and one at the target
intersection. Every one of the smallest lettering classes named in the
brief was read without hesitation.

| # | Location (canvas x,y) | Sheet region | Sample of what was read |
|---|---|---|---|
| L1 | **Target: Ave E x 22nd** (7488, 13184) | unit 6 | `22ND`, `D. Hyd.`, block nos. `617. 618. 205 207`, addresses `129 131 133`, `130.132.134.136.138`, `Pianos & Organs`, `Tailor`, `Leather & Shoe Find'gs.`, `Jewelery`, **`D.G.`**, `B & S. Clo'g.`, `Off.`, `1R.CL.2º`, `W.Rm.`, `2½`, `C. Pipe` |
| L2 | **Seam: Ave D x 27th** (5532, 23934) — the disclosed ~124 px jog | units 13/14 | `AV. D`, `SEE SHEET` note, `B.&S. D.G. & Gro.`, `Restr't`, `Sal.`, `1210 1211`, `70 72`, `Cist.`, **`Dw'g`**, `Bl. Sm`, `602. 603.`, `D.H.`, `80'`, `157. 159.` |
| L3 | Ave G x 22nd (11660, 13544) | unit 5 | `TRINITY CHURCH (EPISCOPAL)`, `UNFINISHED BRICK TOWER`, `25' TO EAVES`, `WINDOWS`, `708 709` |
| L4 | Ave A x 17th (524, 2694) — densest micro-text on the map | unit 2 | `8" W. PIPE FROM CHANNEL`, `Seed W. Ho.`, `WORM SEED CONVEYOR`, `BABCOCK EXTING'R`, `HAND GRENADES. 6" WATER BBLS WITH…`, `ENG. 3" 250 H.P.`, `BALING PRESS.`, `SHAFT HOLE`, `NO OPGS`, `1638 1639`, `516. 515 514` |
| L5 | Ave H x 24th (12896, 17884) — coverage edge | unit 11a | `ST.`, `Gro.`, `161.`, `24.`, `22.` |
| L6 | Ave B x 25th (2380, 20054) — sheet 9/14 seam | units 9/14 | `25TH ST. OR BAT[H AV.]`, `NEW ORLEANS HO.`, `523 524`, `Sal.`, `BR.CIST.`, `1124`, `112.3`, `20'`, `FOUNDRY`, `EARTH FLOOR`, `2 BABCO[CK]`, `501–504` |

Additional dense blocks read in full while hunting landmarks (item 2)
confirm **`Vac. S.`** everywhere it occurs (blocks 620, 561, 621, 501, 622,
562), plus `Vac. Store.`, `Cotton Samples 2º & 3º`, `Off's of City
Government. 2º & 3º`, `Chinese Laundry`, `Telephone Exch. 3º`.

Verdict: the smallest lettering class is comfortably legible at 100% at
every location tested, including directly on seams.

## 2. Landmarks present and legible — **PASS (4 of 5 confirmed; 1 not located)**

Located by walking the street grid, one block at a time (19 blocks read).

| Landmark | Found at | Legibility evidence |
|---|---|---|
| **Harmony Hall** | Block **441**, Ave E–F x 21st–22nd (Post Office / Church) | `HARMONY HALL` + `1882`, `Billiard Room`, `Dining Room`, `Sitting Rms.`, `Gallery Vestibule`, `GAS FOOTLIGHTS`, `2 BABCOCK FIRE EXTING. ON STAGE ALSO W. TANK`, `D.Hyd. 601. 602. 603. 604. 605.` |
| **Ball High School** | Block **321**, Ave G–H x 21st–22nd (Winnie/Menard–Williams) | `BALL HIGH SCHOOL`, `HEATED BY HOT AIR FURNACES`, `LIGHTS-GAS & ELECTRIC`, `AUDITORIUM`, `DOME, GLASS COVERED`, `SPIRAL IR. STAIRS`, `TIN CLAD 3º`, `SMALL STAGE 2º` |
| **Cotton Exchange** | Block **621**, Ave B–C x 21st–22nd (Strand–Mechanic) | Header `COTTON EXCHANGE.` + `1877`, and inside `Cotton Exchange 2ND`, `Offices 1st`, `HUGHES & STOWE Ths. Off 2-4`, `FULL OF WINDOWS WITH IR. SHUTT'S` |
| **The News Bld'g** | Block **621**, same block, Mechanic side | `THE NEWS BLDG.` + `1883.`, `PRESS RM 1st`, `Off's 1st`, `JOB COMPOS'G ROOM. 2º`, `EDITORIAL RM. 2º`, `COMPOSING ROOM 3ᴿᴰ`, `VAULT 1st`, `PUBLIC HALL 2º` |
| **H. Rosenberg Bank** | **Not located** | See note |

Note on H. Rosenberg Bank: 19 blocks were read across the whole Strand /
sheet-7 region and neighbours — A19, A20, A21, A22, B19, B20, B21, B22,
C19, C20, C21, C22, D19, D20, D21, F21, F22, G21, H20, H21, H22, I20, I21,
I22. The 1885 sheets label the banks in this district as **`1st NATIONAL
BANK. Off's 2º`** (block 621, Strand at 22nd), **`ISLAND CITY SAVINGS
BANK. 1874`** (block 561), **`Nat. Bank of Texas.`** (block 682) and a
generic **`Bankers.`** at 230–234 Strand (block 680), with banker surnames
`J. BERLOCHER. H. RUNGE. T.W. HOUSE.` printed as the Strand-side owner
strip. No `Rosenberg` label was found. This is reported as *not located*,
not as a defect: every square inch of the region is intact, matches the
source scans 1:1, and shows no erasure, blur patch or fill (see items 4
and 7). No OCR was available in this environment to search exhaustively,
so absence of the label on the 1885 edition cannot be distinguished from
my failing to spot it. **Not scored as a FAIL.**

## 3. No sharpening halos — **PASS**

Measured directly on edge profiles (row-averaged across a long vertical
street rule, so the profile is noise-free), composite vs. its own source:

```
COMP  line min 94.6   far-field 228.4   max within +-30 px 228.9   overshoot = +0.54 DN
SRC   line min 99.1   far-field 228.5   max within +-30 px 229.0   overshoot = +0.49 DN
```

Composite profile approaching the rule (left to right):
`227.0 226.5 225.7 224.9 224.0 222.3 218.9 210.3 180.8 136.3 104.9 94.8 94.6 …`
— strictly monotone into the edge, no bright rim, no undershoot lobe.
The composite's overshoot (+0.54 DN) is statistically indistinguishable
from the untouched source's (+0.49 DN); both are just paper-grain noise.

Visual confirmation at 200% (nearest-neighbour) at three sites — Ave E x
22nd (the bold `22ND` street cap and dashed rules), the Ave D x 27th seam,
and the News Bldg block. No halo, no ringing, no edge doubling anywhere.
Paper grain is intact right up to every stroke, which is itself proof no
unsharp mask was run (USM would have raised grain contrast in the
paper field).

## 4. Aging retained — **PASS**

Foxing/stain retention was measured, not just eyeballed: brown specks were
segmented as (local-median − pixel) with the blue drop exceeding the red
drop, on precisely aligned composite/source pairs.

| Pair | Composite | Source | Retention |
|---|---|---|---|
| Sheet 5 / Trinity Church block, full 1150x820 crop | 497 speck blobs, 10 741 px | 504 blobs, 11 739 px | **98.6 % of blobs**, 91.5 % of px |
| Sheet 2 / block 616, 1300x1500 crop | 1376 blobs, 40 961 px | 1180 blobs, 37 608 px | **>100 %** (nothing removed) |
| Sheet 14 / Galveston Bay + Marx & Kempner, excl. gap fill | 281 blobs, 7148 px | 294 blobs, 8925 px | **95.6 % of blobs** |

The residual pixel-area deficit is fully explained by the ~3 % Lanczos
downscale (0.967² = 0.934 of the source pixel area per speck), not by
cleanup.

Low-frequency brown mottle (25 px Gaussian, R−B) correlates
**0.977** (sheet 2) and **0.907** (sheet 14) between composite and source,
with matching amplitude (σ 8.51 vs 8.42, and 17.1 vs 16.0) — the stain
field is carried through at full strength.

A saturation-boosted side-by-side montage of the Trinity Church left
margin (`qc2/F_fox_montage.png`) shows the individual foxing specks
matching one-for-one. The output does **not** look cleaned up.

Other aging/provenance content confirmed retained in-frame: `SEE SHEET`
notes (Ave D x 27th, Ave B x 19th), `Scale of Feet.` bars (blocks 681,
382), panel frame rules, the Library of Congress **`Map Division`**
handstamp (bleeding into block 561 at Ave C–D x 21st–22nd), and the
adjoining sheet's `TEXAS` title arc showing in the 22nd-St corridor —
all original, none removed, none retouched.

## 5. Color fidelity — **PASS-WITH-WARNING**

Hue classes are correct and per-channel gains are subtle. Measured on
intersection masks (a region counts only where composite *and* aligned
source both classify the same) so residual misalignment cannot bias the
numbers.

| Feature | Composite RGB | Hue | Source RGB | gain (R,G,B) |
|---|---|---|---|---|
| **Pink (brick)** — Marx & Kempner / sheet 14 | 225.8, 179.2, 179.2 | 0° S=52 | 226.9, 182.2, 182.2 | 0.995, 0.984, 0.984 |
| **Pink (brick)** — Trinity Church / sheet 5 | 204.2, 169.7, 165.5 | 6° S=49 | 203.6, 168.2, 164.1 | 1.003, 1.009, 1.008 |
| **Yellow (frame)** — block 616 / sheet 2 | 229.9, 218.1, 169.3 | 50° S=67 | 230.5, 217.7, 168.1 | 0.997, 1.002, 1.007 |
| **Blue (water/special)** — Galveston Bay / sheet 14 | 150.4, 182.5, 194.8 | 196° S=58 | 150.6, 184.7, 197.2 | 0.999, 0.988, 0.988 |
| **Blue (cistern)** — block 616 / sheet 2 | 144.6, 179.6, 190.3 | 194° S=62 | 144.4, 178.4, 188.6 | 1.002, 1.006, 1.009 |
| **Paper** — three sheets | ~235, 230, 217 | 40–46° S≈20 | ~236, 231, 217 | 0.995 – 1.004 |

Brick is pink (R ≫ G ≈ B), frame is yellow (R ≈ G > B), water is blue
(B > G > R). All gains are within ±1.6 %, far inside the disclosed
0.93–1.08 clamp. No hue rotation, nothing washed out.

**WARNING 1 — green-channel highlight clipping in the sheet-9 region.**
Over the sheet-9 footprint (Ave A–D x 22nd–25th) the composite has
**1.62 % of pixels at G = 255**, while R and B never exceed 249/246 there.
The **source** sheet 9 has *zero* clipped pixels in any channel
(max R/G/B = 247/245/233). So the per-channel gain applied to sheet 9
(paper 233.4,224.3,213.1 → 235.0,232.0,220.0; gain ≈ 1.007 / 1.034 / 1.033)
pushed the green channel into hard clip across ~1.6 % of that unit —
an irreversible loss of highlight separation that did not exist in the
master. It is confined to blank paper (verified visually at canvas
(4034, 17684): genuine map content, reads as a slightly cool white with
no visible artifact), so it is cosmetically invisible but archivally
real. Not a FAIL at this magnitude.

**WARNING 2 — the sheet-9 correction moved it *away* from its neighbours.**
The brief discloses sheet 9's green cast as accepted. Note for the record
that the applied gain did not reduce it: source sheet 9 paper
(233.4, 224.3, 213.1) is barely different from source sheet 7
(234.4, 226.8, 213.7), but *after* correction the composite's sheet-9
paper (235.0, 232.0, 220.0) sits 3.0 G / 4.8 B above composite sheet 7
(235.1, 229.0, 215.2) and sheet 14 (235.1, 230.0, 217.2). Measured
across the 25th-St seam at Ave B this is a step of
ΔR 3.0 / ΔG 1.2 / ΔB 3.4 DN — about 1.3 % luminance, and it is visible
as a faint tonal band in crop L6. The equivalent step at Ave E x 26th is
smaller (~2 DN). Cosmetic, not disqualifying.

**Clipping across the whole canvas:** R max 249 (0 % at 255), B max 249
(0 % at 255), G 0.12 % at 255 — all of the G clipping localises to the
sheet-9 cells (C24, B23, B22, A22, D23, C23, B24, D24…). No black
crushing anywhere (R/G/B min 50/52/37, 0 % at 0).

## 6. Warp softness — **PASS**

Identical lettering compared between native source pixels and the
composite location, at 300 % nearest-neighbour
(`qc2/W_letters_300.png`): the words `AUDITORIUM`, `DOME.`,
`GLASS CUV'D`, `IR. FRAMED`, `OFFS 1ST`, `SMALL STAGE 2º` inside Ball
High School (block 321, sheet 5).

- Composite:source resampling ratio at this unit is 0.967 (single pass).
- Every letterform is intact and separately resolvable. Stroke joins,
  the thin hairlines of the italic caps, and the dashed partition rules
  all survive.
- No aliasing: no staircasing on the dome circle or the diagonal stage
  hatching, no moiré on the ruled window ticks.
- No double-resampling mush: edge transitions are 3–4 px 10-90 in the
  composite vs 5–6 px in the (larger-scale) source, i.e. the edge width
  scales with the resample ratio exactly as a single clean pass should.
- Objective: on the same pair, |∂x| gradient p95 = 197 (composite) vs
  173 (source at its own native scale) and p99 = 298 vs 276 — the
  composite is marginally *crisper per pixel*, which is the expected
  signature of one Lanczos downscale, and it is accompanied by
  **zero overshoot** (item 3), which rules out sharpening as the cause.

Softening is mild and single-pass. PASS.

## 7. No invented content — **PASS**

**(a) Gap areas are flat, not synthesized.** The uncovered canvas is a
single exact constant, RGB **(216, 202, 176)**, occupying 29.0 % of the
canvas as one connected component.

- Full-resolution 1500x1500 sample from the largest gap:
  **per-channel σ = 0.0000, exactly 1 unique colour.**
- Over 1.70 M sampled gap pixels canvas-wide: σ = (0.022, 0.022, 0.021),
  range 214–218 / 200–204 / 174–178 — that spread is only the ±2
  tolerance band I used, i.e. anti-aliased boundary pixels.

There is no grain, no texture, no gradient, no fabricated linework in any
gap. Nothing was inpainted or generatively filled.

**(b) No cloned or repeated texture along seams.** Tiled
normalized-cross-correlation clone search: 96x96 tiles at 48 px stride
along 240 px-wide bands centred on all 8 interior avenue seams (B–I) and
7 street seams (19th, 20th, 22nd, 23rd, 25th, 26th, 27th). Tiles
touching the fill colour were excluded; tile pairs closer than 200 px
were excluded; and tiles were required to carry real cartographic content
(6–50 % ink coverage, ≥8 connected ink components) so that the trivially
self-similar "one straight rule on blank paper" tiles could not
manufacture false hits.

```
vert Ave B  472 tiles  maxNCC 0.824      horiz 19 St   58 tiles  maxNCC 0.683
vert Ave C  446 tiles  maxNCC 0.958      horiz 20 St  227 tiles  maxNCC 0.688
vert Ave D  435 tiles  maxNCC 0.750      horiz 22 St  256 tiles  maxNCC 0.739
vert Ave E  203 tiles  maxNCC 0.826      horiz 23 St  229 tiles  maxNCC 0.845
vert Ave F  154 tiles  maxNCC 0.886      horiz 25 St  195 tiles  maxNCC 0.681
vert Ave G  117 tiles  maxNCC 0.779      horiz 26 St  160 tiles  maxNCC 0.684
vert Ave H   89 tiles  maxNCC 0.790      horiz 27 St  114 tiles  maxNCC 0.628
vert Ave I   63 tiles  maxNCC 0.812      CONTROL blk E22 295 tiles maxNCC 0.865
```

Only 3 pairs anywhere exceeded 0.90, all on Ave C. The single highest
(0.958, canvas offsets 288 px apart) was pulled and inspected at 4x:
two different stretches of the same block-outline rule over pink wash,
**RMSE 7.85 DN**, with visibly different paper grain — not a clone. Every
seam band scores at or below the non-seam control block (0.865), i.e.
seam neighbourhoods are no more self-similar than ordinary map interior.

**(c) Content provenance spot-checks.** Five composite regions across four
different source sheets (5, 2, 14, and the sheet-5 Trinity block) were
template-matched back into their source JPEGs and found at consistent,
scale-coherent positions with matching foxing, matching paper grain and
matching linework. Nothing in the composite was found that does not exist
in a source scan.

Disclosed features re-confirmed as original-scan artifacts and not
inventions: the 69 px paper gutter in the Ave H corridor at 23rd–24th,
the scan-edge shading bands in the corridors at 19th and 23rd (visible in
the 200 % Ave D x 27th crop as a soft one-sided falloff, with no ringing),
and the rim slivers facing the disclosed gaps.

---

## Summary

| # | Item | Result |
|---|---|---|
| 1 | Legibility at 100 % | **PASS** |
| 2 | Landmarks present and legible | **PASS** (4/5 confirmed; H. Rosenberg Bank not located — reported, not failed) |
| 3 | No sharpening halos | **PASS** (overshoot +0.54 DN vs +0.49 DN in the untouched source) |
| 4 | Aging retained | **PASS** (95.6–100 % of foxing blobs retained; mottle correlation 0.91–0.98) |
| 5 | Color fidelity | **PASS-WITH-WARNING** (hues correct, gains ≤1.6 %; but G clipped at 255 over 1.62 % of the sheet-9 region where the source had none, and the sheet-9 tonal step vs neighbours is ~3 DN) |
| 6 | Warp softness | **PASS** (single-pass, no mush, no aliasing) |
| 7 | No invented content | **PASS** (gap fill σ = 0.0000, 1 unique colour; max content-tile NCC on any seam 0.958, at/below the non-seam control) |

# VERDICT: PASS-WITH-WARNINGS

The composite is faithful. Nothing was sharpened, cleaned, smoothed or
synthesized; the smallest lettering is readable everywhere including on
seams; the paper's age is carried through intact; colour is untouched to
within ~1.5 %. The two warnings are both confined to the already-disclosed
sheet 9: its per-channel gain drove the green channel to hard clip across
1.62 % of that unit (the master scan had zero clipped pixels), and it
left sheet 9 ~3 DN cooler than its neighbours, producing a faint but real
tonal step at the 25th-Street seam. Neither is visible at normal viewing
and neither justifies a FAIL, but the green clip is an irreversible
archival loss and should be recorded in the provenance notes — or fixed by
re-running sheet 9's gain with a highlight-safe ceiling.

Not verified by this pass, and left as an open question rather than a
finding: whether the 1885 edition labels an **H. Rosenberg** bank anywhere
in the covered area.
