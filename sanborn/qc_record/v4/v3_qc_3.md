# v3 QC — Reviewer 3 (REGRESSION vs v2 + SUPREMACY vs "other")

Artifact under review: `build/1885/galveston_1885_composite.tif` (18188x27524, PAD 742)
Baselines: `compare/v2_composite.tif` (PAD 464), `compare/other_onepage.jpg`, `sources/1885/Galveston_1885_sheet_NN.jpg`
Evidence: `build/1885/v3_qc_evidence_3/` (89 files, 23 MB). Method: programmatic crops from
memmapped raw decodes; all offsets by `cv2.matchTemplate` TM_CCOEFF_NORMED on grayscale.
Nothing was fixed.

---

## 1. GEOMETRY REGRESSION — 12 windows, all units

Expectation from the brief: v3 content = v2 coords + 278 in both axes, tolerance ±2.

| window | unit | offx | offy | peak | verdict |
|---|---|---|---|---|---|
| U2_avB_st17.5 | 2 | **274** | **274** | 0.996 | **FAIL (-4,-4)** |
| U2_avC_st18.5 | 2 | **273** | **274** | 0.991 | **FAIL (-5,-4)** |
| U3_avE5_st19 | 3 | 278 | 278 | 1.0000 | pass |
| U4_avG5_st26.5 | 4 | 278 | 279 | 0.994 | pass |
| U5_avH5_st21.5 | 5 | 277 | 276 | 0.995 | pass |
| **TARGET_avE_st22** | 6 | **278** | **278** | 0.9999 | **pass (target OK)** |
| U7_avB_st20.5 | 7 | 278 | **281** | 1.0000 | **FAIL (+3 y)** |
| U9_avB_st23.5 | 9 | 278 | 280 | 0.992 | pass (at limit) |
| U10_avE5_st24.5 | 10 | 278 | 277 | 0.999 | pass |
| U11a_avG5_st24 | 11a | 278 | 278 | 1.0000 | pass |
| U13_avE5_st27 | 13 | 277 | 278 | 0.995 | pass |
| U14_avB_st26.5 | 14 | 278 | **283** | 0.9996 | **FAIL (+5 y)** |

Raw: `t1_offsets.json`. Crops `t1_<window>_v2.jpg` / `_v3.jpg`.

**These are real rigid per-unit translations, not seam noise.** Quadrant test (4x 200 px
sub-windows per window) returned the *same* offset in all four quadrants of every window,
and a 5-point-per-unit sweep over all 12 units (`t1c_perunit.json`) is internally consistent
to ±1 px:

```
unit 2  (-4.5,-4.0)   unit 3  ( 0, 0)*   unit 4  ( 0,+1.5)   unit 5  (-1,-2)
unit 6  ( 0, 0)*      unit 7  ( 0,+3.0)  unit 9  ( 0,+1.6)   unit 10 ( 0,-1)
unit 11a( 0, 0)*      unit 11b( 0, 0)*   unit 13 (-1.4, 0)   unit 14 ( 0,+4.7)
* = pixel-identical, MAD 0.00-0.11
```

**FINDING G-1 (WARNING, spec violation):** "geometry untouched" is false. 8 of 12 units moved;
3 exceed the ±2 tolerance. The largest *relative* change is at the unit2|unit7 seam, which I
localised to global y ≈ 6871 (sharp transition from (-4,-4) to (0,+3) within 100 px —
`t1_seam_u2u7_*.jpg`): v3 opens (4, 7) px of relative displacement across that seam vs v2.
Mitigation: the seam there falls on the physical page-edge band, and side-by-side crops at
three x-positions show **no visible jog** (`t1_seam_u2u7_0/1/2.jpg`). I grade this a warning,
not a visible defect — but the change is undisclosed and unexplained by any of the three
stated v3 changes.

## 2. PIXEL FIDELITY — 8 windows (asked for 6)

MAD after per-channel median matching, evaluated **at the matched offset** so the translation
of §1 does not contaminate the number (`t2_*_absdiff.jpg`):

| window | gain v3/v2 R/G/B | MAD @ +278 | MAD @ matched | P99 abs | Lap.var v2 → v3 |
|---|---|---|---|---|---|
| U2_avB_st17.5 | 1.000/1.000/1.000 | 13.29 | **1.16** | 13 | 122.7 → 123.0 |
| U3_avE5_st19 | 1.000/1.000/1.000 | 0.02 | **0.02** | 1 | 85.9 → 85.9 |
| U5_avH5_st21.5 | 1.000/1.000/1.000 | 7.16 | **1.49** | 13 | 121.0 → 121.1 |
| TARGET_avE_st22 | 1.000/1.000/1.000 | 0.11 | **0.11** | 1 | 92.4 → 92.4 |
| U9_avB_st23.5 | 0.991/1.000/1.000 | 6.61 | **2.43** | 21 | 182.3 → 181.1 |
| U14_avB_st26.5 | 1.000/1.000/1.000 | 17.14 | **0.49** | 4 | 225.1 → 225.2 |
| U7_avB_st20.5 | 1.000/1.000/1.000 | 8.62 | **0.24** | 2 | 118.3 → 118.4 |
| U13_avE5_st27 | 1.000/1.000/1.000 | 3.51 | **0.94** | 13 | 84.0 → 82.8 |

**PASS.** Residual MAD 0.02–2.43 (the non-zero part tracks the sub-pixel remainder of each
unit's translation, e.g. unit 2's ≈ −4.5). Laplacian variance is identical to <1.5 %
everywhere — **same warp, same single-pass resample, no softening**. The MAD @ +278 column is
the geometry finding of §1 restated in pixels.

## 3. SUPREMACY vs "other"

### (a) sheet-9 paper tone — **v3 LOSES. Regression vs v2.**

Per-unit bright-paper chroma (mean of top-20 % luminance pixels, 4 samples/unit, 700 px
windows) — `t3a_chroma_v3.jpg`, `_v2.jpg`, `_other.jpg`:

```
              L range        R-G range          R-G sd   frac |R-G| > 8  (256px tiles)
v3     229.5 - 241.5   -12.7 .. +6.6  (ptp 19.3)  5.04         0.391
v2     229.5 - 242.5   -10.8 .. +6.6  (ptp 17.3)  4.50         0.395
other  228.2 - 235.2    +2.5 .. +6.7  (ptp  4.2)  1.31         0.073
```

Unit 9 (A-D / 22-25) sits at **R-G = −12.7** while every other unit is +2.8 … +6.6. v2 was
−10.8, so **v3 made it 1.9 units worse**, not better. The chroma heatmaps show it as a hard-
edged solid-blue rectangle in both v3 and v2 and as *nothing at all* in other.

**FINDING T-1 (FAIL):** the cast is fabricated by the pipeline, not inherited from the scan.
All 19 source sheets measure R-G +2.2 … +6.4; **sheet 09 measures +3.8**. I matched a v3
unit-9 patch back into the source (multi-scale, peak 0.725, `t3a_source_vs_v3_sheet9.jpg`):

```
SOURCE sheet09 matched patch : R-G = +3.6   G-B = +11.9   L = 231.6
v3, identical area           : R-G = −12.3  G-B = +12.9   L = 239.9
```

A ~16-unit hue swing — far past the brief's "no sheet may drift in HUE from its source beyond
a subtle uniform-gain look". It is not confined to paper: under a fixed colour classifier the
yellow (frame-construction) fills of sheet 9 come out **G > R** in v3 (229,237,198) where the
source is R > G (230,222,184), and the pink (brick) pixel population collapses from 1.89 M to
0.12 M because the hue has moved out of band. Change #1 (chromatic WB) did not fire usefully
on this sheet; the only measurable effect was R −2.0 / B −0.7 with G unchanged, which
*deepens* the cast.

Visible proof: `t3a_sheet9_boundary_zoom.jpg` (Ave D at 23rd–24th). v3 shows a hard cool/warm
tonal step down the Avenue D line (left half R-G −10.6, right half +4.6); other is uniform
(+5.4 / +3.4). Same at 22nd St (`t3a_sheet9_st22_zoom.jpg`, `t3f_22nd_aveB5_sbs.jpg`).

### (b) top-left 16TH ST. header + oval stamp — **v3 WINS vs v2, TIES other.**

`t3b_topstrip_v3.jpg` / `_v2.jpg` / `_other.jpg`. v3 retains **"16TH ST."** in full and the
complete **"OCT. 1885 / GALVESTON / TEXAS"** oval. v2 clips the header entirely and keeps only
the bottom arc of the oval ("TEXAS"). other also has both. Content-wise this criterion is
recovered.

### (c) 25th / Ave G street label — **v3 LOSES. Unchanged from v2.**

`t3c_label_final_sbs.jpg`, `t3c_label_v3_only.jpg`, `t3c_25th_aveG_sbs.jpg`.

**FINDING L-1 (FAIL):** v3 prints **"25TH ST. OR BATH" twice**, stacked, the lower copy
offset down-right and rendered in a slightly different tone — a seam duplication that also
**destroys the original "SEE SHEET N° 4" note** that belongs on that line. other renders it
correctly: one "25TH ST. OR BATH", then "SEE SHEET N° 4". v3 is pixel-equivalent to v2 here;
the glyph-aware seam cut (change #2) did not resolve this site. A faint vertical seam-blend
band is also visible through the 5301/5303 lots in the same crop.

Change #2 does hold at other seam-crossing labels I sampled — `t3g_seamlabel_19th_aveB.jpg`,
`_25th_aveB.jpg`, `_23rd_aveE.jpg`, `_26th_aveE.jpg`, `_20th_aveE.jpg` all show single, intact
labels. 25th/Ave G is the specific site the goal named, and it is the one still broken.

### (d) margins / "clean presentation" — **split: v3 wins on content, LOSES on cleanliness.**

Site 1, unit 5 top (`t3d_u5top_v3/_v2/_other.jpg`): v3 retains **"SEE SHEET No. 3"**,
**"20TH ST."** and the oval stamp with a clean cut. v2 clips all three. other keeps the header
and stamp but **loses the "SEE SHEET No. 3" line**. → v3 best.

Site 2, unit 14 bottom (`t3d_u14bot_v3/_v2/_other.jpg`): v3 retains the scale bar
("…le of Feet / 50 100 150") and **"28TH ST. / SEE SHEET NO. 17"** in full. v2 truncates
mid-block. other **slices "28TH ST." in half horizontally** and loses the SEE SHEET line.
→ v3 best.

**FINDING M-1 (WARNING):** margin retention also drags in raw scanner edges. Dark-rim metric
(pixels < 75 within ~50 px of the content boundary, `t3d_darkrim_*.jpg`):

```
v3     2.78 %      v2  0.18 %      other  0.09 %      (v3 ≈ 15x v2, 30x other)
```

Largest offenders (v3 canvas coords):
- **x 6480–11056, y 4768–4840** — a solid black band ~72 px thick and **4576 px long** across
  the entire top margin of unit 3, directly above the "18TH ST." header
  (`t3d_darkband_u3top_v3.jpg`). Visible as a hairline at whole-map zoom.
- **x 184–2352, y 152–3008** — black wedge plus a white/blue platen sliver along the whole
  top-left corner (`t3d_v3_topleft_corner.jpg`).
- **x 15848–15896, y 16256–17096** — black band + torn page edge at unit 11b's right margin
  (`t3d_darkband_11bright_v3.jpg`). This one faces a disclosed gap, but it is a
  40 x 840 px black bar, not a "rim sliver".

other has clean cream margins throughout. On the literal wording of criterion (d) — "clean
margins presentation" — other still wins even though v3 preserves more real content.

### Reconfirmations (places v3/v2 already won) — **all still won**

- **Alignment across 22nd St at three avenues.** Visual: v3's lot lines run straight through
  the street, label "22ND ST." single and intact (`t3f_22nd_aveA5/B5/C5_sbs.jpg`).
  Numeric: matching v3 templates 800 px above vs 800 px below the seam into other gives
  relative displacements of **(+15, −196)**, **(−18, −174)**, **(−50, −152)** px at Ave A/B/C —
  i.e. other carries a 150-200 px registration break at 22nd St. (25th @ Ave B: −297 px.)
  v3 wins decisively.
- **No ghosting at 27th / Ave D** (`t3f_27th_aveD_sbs.jpg`): v3 == v2, only the disclosed
  ~124 px jog; no duplicated content. other has no coverage on the east half of that crop.
- **Corridor address numerals, Avenue D 21st-22nd** (`t3f_aveD_21_22_v3.jpg`): all present —
  115 117 119 121 125 127 / 186 184 182 180 / 1401 1403 1405 1406 1408 / 561 / 501 /
  185 183 179 177 175 173 171 169 167 165 163 161 159. Legible; the "Map Division" LoC stamp
  is retained (disclosed).

## 4. LEGIBILITY SPOT-CHECK — 4 scattered sites, all sharp

- `t4_L1_u2_avA5_st17.jpg` — "Hull House"; "1ST 10 STAND TAYLOR PRESSES 6 / 30 RAMS. 160
  BOXES, 10 STEAM HEATERS, CAKE MILL & GRINDER"; "2º 10 CARVERS LINTERS & CONDENSERS, 5
  HULLER 3 SET ROLLS, 1 GIN FILE."; "2 SIFTERS 1 CHAMPION RE-GINNING MACH. 1 STURTEVANT FAN
  Nº 7 (1750 REV.)"; "CIST. 70,000 GALL'S"; "KNOWLES F.P. Nº C"; "D.H.&CO. 2½" HOSE ATT."
- `t4_L2_u5_avI_st21p5.jpg` — "Turner Hall  1 = 2"; "Bar / Hall / Hat Rm."; "TEN PIN ALLEY";
  "BALCONY"; "GAS FOOT LIGHTS"; "STAGE & SCENERY"; numerals 159 161 163 / 1204 1205.
- `t4_L3_u13_avE5_st27.jpg` — "613. 614. 615. 616. 617."; "CARRIAGE HO."; "Sal."; "Dwg";
  "1052"; "HEN HO."; "1102 / 1101".
- `t4_L4_u11a_avG5_st24.jpg` — "5309½"; "60½"; "Servants Rm."; "SHED"; "55½"; "51½"; "51¾";
  "Board'g"; "TANK."; "20'"; "164. 166."

No blur, no double-edging, no JPEG mush. Consistent with §2's unchanged Laplacian variance.

## 5. WHOLE-MAP LOOK (~2100 px previews)

`t5_whole_sbs.jpg`, `t5_preview_v3.jpg`, `_v2.jpg`, `_other.jpg`.

Flipping between them at phone size, in order of what the eye lands on:
1. **v3 and v2 both show a mint-green rectangle** occupying the whole left-centre of the map
   (sheet 9). It is the single most conspicuous feature of either image and reads immediately
   as "one page is a different colour". other is uniformly warm cream end to end.
2. v3's black hairline across the top of unit 3 and the black corner wedge are visible at this
   zoom as thin dark strokes in the margin; v2 and other have none.
3. v3 has the most complete and squarest silhouette — retained headers/stamps on the outer
   faces, tidy edges; v2's outline is visibly stair-stepped and chewed; other's is loose, with
   thin white gaps between adjacent sheets on the right side and mid-map.

**Where other still looks better:** overall tone (decisive, criterion a) and margin/edge
cleanliness (criterion d). Everywhere else — content retention at edges, silhouette,
cross-street registration — v3 is the better artifact.

---

## Findings ledger

| id | severity | site | summary |
|---|---|---|---|
| T-1 | **FAIL** | unit 9 / sheet 09, A-D × 22-25 | Green-cyan cast unremoved and 1.9 units worse than v2; ~16-unit hue drift from source (+3.6 → −12.3); corrupts yellow/pink construction fills. Criterion (a) lost to other. |
| L-1 | **FAIL** | 25th St × Ave G | Street label duplicated ("25TH ST. OR BATH" twice), original "SEE SHEET N° 4" destroyed. Identical to v2. Criterion (c) lost to other. |
| G-1 | WARNING | units 2, 7, 14 (also 4, 5, 9, 10, 13) | Undisclosed rigid per-unit translations up to 5 px; 3 units outside the ±2 spec; max relative seam change (4, 7) px at unit2\|unit7 (y≈6871). Not visible; not explained by the three stated changes. |
| M-1 | WARNING | unit 3 top, top-left corner, unit 11b right | Margin retention pulls in raw scanner black edges; dark-rim fraction 2.78 % vs 0.18 % (v2) / 0.09 % (other). One band is 4576 × 72 px of solid black. Criterion (d) lost to other. |

No regression found in: pixel fidelity / sharpness (§2), the Avenue E × 22nd target window
(exactly +278/+278, MAD 0.11), seam-label integrity at 19th/20th/23rd/25th-Ave-B/26th,
27th × Ave D ghosting, Ave D corridor numerals, cross-22nd-St alignment, or legibility.

VERDICT: FAIL

- **Two of the four supremacy goals are simply not met.** Sheet 9's green cast (a) and the
  25th/Ave G label (c) are byte-for-byte as broken as in v2 — change #1 and change #2 did not
  fire at the sites they were written for.
- **(a) is an outright regression vs v2**, not merely a miss: unit 9 moved from R-G −10.8 to
  −12.7 while all 19 source sheets sit at +2.2…+6.4, so v3 now displays a ~16-unit hue drift
  from its own scan — a direct violation of the brief's stated acceptance bound for change #1.
- **(b) and the two extra margin sites are genuine, substantial wins** — v3 recovers "16TH ST.",
  "20TH ST.", "SEE SHEET No. 3", "28TH ST. / SEE SHEET NO. 17", the scale bar and three oval
  stamps that v2 threw away, and beats other at both extra sites.
- **Margin retention is not yet clean:** it also imports 15x more scanner-black rim than v2,
  including a 4576-px black band over unit 3's header, so criterion (d) is still lost to other.
- **Everything v2 earned is intact:** identical warp and sharpness (residual MAD ≤ 2.4,
  Laplacian variance unchanged), no new ghosting, corridor numerals present, and v3 beats other
  on cross-22nd-St registration by 150-200 px. The geometry did shift by up to 5 px per unit,
  which contradicts "geometry untouched" but produces no visible defect.
