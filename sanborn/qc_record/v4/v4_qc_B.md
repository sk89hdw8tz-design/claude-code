# v4 QC — Reviewer B (MARGINS, TONE, HIGHLIGHTS, EDGES) — round 3, final gate

Artifact: `build/1885/galveston_1885_composite.tif` (18188 x 27524, PAD 742, built 01:40).
Raw dump `v4B_raw.dat` verified byte-identical to `v4_raw.dat` on 400 random rows and
md5-identical on 5 sampled rows — both are direct `tifffile` reads of the TIF under review.
Comparators: `compare/v2_composite.tif` (PAD 464), `compare/other_onepage.jpg`
(27160 x 17824), `sources/1885/Galveston_1885_sheet_NN.jpg`.
Geometry read fresh from `build/1885/registration.json`; every source↔canvas mapping in this
report goes through v4's own knots (`src2canvas` / `canvas2src`), never a fixed offset.
Evidence: `build/1885/v4_qc_evidence_B/` (191 files). Scripts: `qcB4_lib.py`,
`qcB4_p1..p8_*.py`, `qcB4r_p1_darkscan.py`, `qcB4r_p2_blobs.py`, `qcB4r_p3_other.py`,
`qcB4r_p4_u14.py`, `qcB4r_p5_annot.py`, `qcB4r_p6_sig.py`, `qcB4r_p7_rim.py`,
`qcB4r_p8_final.py`. Programmatic crops and statistics only. Nothing was modified.

---

## Headline: the round-2 bed sites are gone, but v4 **fabricates** new black at three margins

The three sites round 2 blocked on are genuinely clean. In their place v4 has three
**pure-(0,0,0)** bands — and, unlike every previous round, **they are not scanner bed at all.
They do not exist in the source scans.** Sampling the composite inside each band and mapping
each sample back through v4's own knots (`202_black_is_synthetic.json`):

| canvas px | v4 RGB | maps to source | source RGB there |
|---|---|---|---|
| (400, 27400) | **0,0,0** | sheet 14 (212.7, 7509.1) | 233,226,208 |
| (700, 27430) | **0,0,0** | sheet 14 (528.9, 7537.9) | 228,221,205 |
| (900, 27450) | **0,0,0** | sheet 14 (739.8, 7557.2) | 231,224,205 |
| (1200, 27455) | **0,0,0** | sheet 14 (1056.0, 7562.0) | 231,218,199 |
| (1500, 27458) | **0,0,0** | sheet 14 (1372.3, 7564.9) | 235,226,209 |
| (100, 85) | **0,0,0** | sheet 2 (236.7, 31.5) | 225,214,194 |
| (500, 90) | **0,0,0** | sheet 2 (599.4, 36.6) | 224,215,198 |
| (12012, 27000) | **1,1,1** | sheet 13 (6390, 4924) → 228,222,210; sheet 4 (326, 7222) → 235,227,208 |
| (12014, 27100) | **0,0,0** | sheet 13 (6392, 5024) → 219,216,211; sheet 4 (328, 7330) → 232,225,206 |

Control samples a few px outside the bands map correctly and carry the right colour
(canvas (600,27390) → src (423,7499): v4 223,229,233 = the light blue-grey **backing board**,
source 230,223,204 — reproduced, not blackened; canvas (1700,105) → v4 227,220,204 vs source
228,219,204).

The whole source windows contain **no dark pixel**: sheet 14 rows 7480-7620 × cols 20-1600
has **min gray 82**; sheet 2 rows 0-120 × cols 0-1800 has **min gray 71**; neither has a single
pixel below 50, let alone at 0 (`200_inset_headroom.json`, `201_SRC14_bottomleft_2x.png` shows
paper → torn edge → light backing board and nothing darker).

**Mechanism.** Each band lies between the sheet's real (diagonal, torn) paper edge and v4's
new straight static inset, and follows the paper edge exactly. The static SCAN_INSET is cut
**outside the detected paper polygon**, and the uncovered wedge is left at buffer-zero instead
of being painted with the paper fill. The same unclamped boundary produces the mirror-image
defect on the bright side — see FIX 2. **This is a new artifact class: synthesised black, not
retained bed.**

---

## FIX 3(a) — ROUND-2's THREE BED SITES — **all three GONE (credit where due)**

Full-resolution, every pixel, over generous boxes (`r2_sites.json`, `90_darkblobs_*.json`):

| round-2 site | v3.2 (same box) | **v4** | evidence |
|---|---|---|---|
| **unit 5 TOP wedge** (round-2's worst: 2810 px long, to 28 px thick) | gmin 0, 39,593 px < 50, **36,164 px == 0** | **gmin 65, 0 px < 50, 0 px == 0** | `40_u5_top_wedge_v4_q.png`, `75_u5_top_band_q.png` |
| **unit 5 RIGHT full-height band + backing** (7,154 px tall) | gmin 0, 24,124 px < 50, **21,008 px == 0** | **gmin 57, 0 px < 50, 0 px == 0** | `40_u5_right_band_v4_q.png` |
| **unit 3 RIGHT band + grey-blue backing** | reviewer-3 site x 12212-12218 | **min gray 214** at y 6000 in an x 11950-12300 probe; **0 px < 70** | `40_u3_right_band_v4_q.png`, `195_vline_x12100_100pc.png` |

Also gone, un-asked-for: v3.2's 25th/Ave G street wedge (828 × 52, 13,398 px == 0) and its
x 12200 sliver (6,524 px == 0) — neither appears in v4's blob census.
Unit 5's top margin now carries **SEE SHEET NO. 3, 20TH ST., the OCT.1885 GALVESTON TEXAS oval
and the sheet number "5" all whole, with no wedge** (`75_u5_top_band_q.png`).

## FIX 3(a′) — FINDING B-1 (BLOCKER). Three NEW pure-black bands

Full-resolution census of the entire canvas (4×4 max-pool → connected components → full-res
re-measure, `qcB4r_p1_darkscan.py`, `90_darkblobs_v4.json`, `100_blob_profiles.json`):

**v4: 90,343 px below gray 50; 83,809 px at exactly gray 0, in exactly three blobs — and the
three blobs account for 83,809 of the 83,809.** No printed ink anywhere on the canvas reaches 0,
so gray == 0 is a perfect discriminator.

| # | site | box | px == 0 | shape |
|---|---|---|---|---|
| 1 | **unit 14 BOTTOM-LEFT** | x 248-1760, y 27368-27468 | **59,304** | 81 rows carry zeros; peak 1,472 zeros on row 27459 = the trim row; RGB max over all 59,304 px = (1,0,1) |
| 2 | **unit 2 TOP-LEFT** | x 0-1720, y 72-116 | **21,918** | 27 rows; peak 1,645 zeros on row 81 = the trim row; RGB max (0,1,1) |
| 3 | Ave G corridor (u13\|u4) | x 11992-12024, y 26816-27276 | **2,587** | 13 columns; peak 410 zeros in column 12015; RGB max (0,0,0) |

Comparators, measured the same way:

| | pure-black px, whole canvas | px < gray 50 |
|---|---|---|
| **v4** | **83,809** | 90,343 |
| v3.2 | 72,650 (4 blobs) | 81,817 |
| v2 | **3,308** (one blob, 2,321 px, the same Ave G corridor class) | 13,145 |
| **other** | **0** in 484,099,840 px | **1** |

Sites 1 and 2 are **worse than BOTH v2 and other**: v2 has zero pure-black pixels anywhere on
its canvas except its own Ave G blob, and other has zero, full stop. Round 2 certified both of
these exact sites clean in v3.2 ("unit 2 top black band — **gone**, gmin 64, 0 px below gray 50";
"unit 14 bottom-left backing + debris speck — **gone**"). Site 3 is the same class and roughly
the same size as v2's own (2,587 vs 2,321) and is not counted against v4.

Visible at 1/6 and at 1/14: `192_edge_top_1_6.png`, `192_edge_bottom_1_6.png`,
`191_v4_overview_darkmarked.png`. At 100 %: `100_A_u2_top_v4_100pc.png`,
`100_B_u14_bot_v4_100pc.png`, `133_ctrl_scalebar_hit_100pc.png` (paper → torn edge →
**~50-70 px white/blue backing board** → hard black), `193_aveG_sliver_100pc.png`.

**The backing-board strip is also back.** Round 2 recorded every backing strip eliminated
(unit 2 ~100 px, unit 9). v4 re-exposes one at unit 14's bottom, immediately inboard of the
black (`133_ctrl_scalebar_hit_100pc.png`, `61_u14_scalebar_100pc.png`).

## FIX 3(b) — UNIT 14 OVER-TRIM CASUALTIES — **5 of 6 restored, 1 still missing**

`trim_loss_v4.json`: unit 14 left now trims at canvas x 259 = **source x 64.0** (v3.2: 487.5)
and bottom at canvas y 27459 = **source y 7565.8** (v3.2: 7103.2). **Discarded ink beyond the
trim is now 0 on both sides**, against v3.2's 55,330 + 62,048 = 117,378 px.

| round-2 casualty | v4 | evidence |
|---|---|---|
| **"28TH ST."** | **RESTORED whole** — rotation-tolerant template match NCC **0.898** | `60_u14_bottom_band_q.png`, `132_ctrl_28TH_hit_100pc.png` |
| **"SEE SHEET No.17"** | **RESTORED whole** — all three words, terminal period, read at 100 % | `60_u14_bottom_band_q.png`, `122_u14_seesheet_100pc.png` |
| **"Scale of Feet" bar** | **RESTORED whole, not sliced** — full graduated bar, both halves, tick risers under 50/40/30/20/10/0/50/100/150, and **paper below it** | `136_u14_bottomleft_wide_q.png`, `61_u14_scalebar_100pc.png`, `135_u14_scalebar_region_100pc.png` |
| **waterworks annotation** ("100' TO FR.SHED … WATERWORKS PUMPING HO. 35'X45'") | **RESTORED**, ink ratio src→canvas **0.94** | `120_u14_waterworks_L_SBS_100pc.png`, `66_u14_left_waterworks_100pc.png` |
| **"130' TO 1 STY FR. COAL SHED"** | **RESTORED**, ink ratio **0.97** | `120_u14_coalshed_130_SBS_100pc.png`, `66_u14_left_coalshed_100pc.png` |
| **"J. LLOYD 10/28/85" signature** | **STILL ABSENT** | below |

### FINDING B-2 (WARNING). The J. LLOYD signature is still not there — for a new reason

Rotation-tolerant hunt (±4°, 0.5° steps) with the signature cut from source sheet 14 at
(6232,7312)-(6362,7438) — located by scanning the sheet's bottom-right corner for ink
(`130_SRC14_corner_3x.png` reads "J.LLOYD / 10/28/85" plainly):

| | best NCC | controls |
|---|---|---|
| v4 | **0.302** | same method, same scene scale: "28TH ST." in v4 = **0.898**; signature matched against its own sheet = **1.000** |
| v3.2 | 0.319 | |
| v2 | 0.285 | |
| other | 0.312 | |

Absent from all four. The **cause has changed**: it is no longer trimmed away. The signature
maps to canvas ≈ (6331, 27313), which now falls **east of the unit-14 / unit-13 ownership seam
at x ≈ 6211**, so unit 13's frame rule and its "SEE" occupy the pixels
(`121_u14_sig_wide_q.png`, `121_u14_sig_zoom_100pc.png`). Not counted as a FAIL — v2 and other
lack it too — but the checklist item is **not** satisfied.

### FINDING B-3 (SERIOUS). New half-trimmed annotation: unit 14's GALVESTON cartouche is beheaded

`186_u14_oval_100pc.png`, `184_u14_top_wide_q.png`, `188_u14_oval_v4_q.png` vs
`188_u14_oval_v32_q.png`.

- Flat gap fill (exactly 236,232,219) occupies **canvas y 20110-20481** — a 372-row run,
  identical at x = 4200, 5000, 5568 and 6100, i.e. a dead-straight horizontal cut.
- The oval's ink spans **source y 201-659** → canvas **y 20138-20508**.
- Result: **"OCT. 1885" and the top half of "GALVESTON" are replaced by flat fill**; only the
  lower arc and "TEXAS" survive.
- **v3.2 has this same cartouche complete** (`188_u14_oval_v32_q.png` reads "OCT. 1885 /
  GALVESTON / TEXAS" in full). Round 2 listed it under PRESENT & WHOLE.

So v4's static insets went *tighter* than the paper on unit 14's left and bottom (letting black
in) and *looser* than the annotation on unit 14's top (cutting the cartouche out).

## FIX 3(c) — ROUND-2 KEEPERS — **all held**

| keeper | v4 | evidence |
|---|---|---|
| **16TH ST.** | whole, NCC 0.797 | `70_u2_top_band_q.png` |
| **OCT.1885 GALVESTON TEXAS ovals** | unit 2 **0.908**, unit 5 **0.745**, unit 10 **0.859** — all whole; **unit 14 beheaded (B-3)** | `70_u2_top_band_q.png`, `75_u5_top_band_q.png`, `181_u*_galv_oval_q.png` |
| sheet number "2" | whole, NCC 0.970 | `70_u2_top_band_q.png` |
| **AV. A OR WATER** + SEE SHEET **No.15** | whole, NCC 0.764. Unit 2's left trim = source x **149.6**; the leftmost margin ink on sheet 2 is at source x **166** → 16 px clearance, nothing shaved | `196_u2_leftmargin_strip_q.png`, `180_keepers.json` |
| **LoC "Map Division / Library of Congress" stamps** | both complete — unit 5 right, unit 14 | `73_locstamp_u5right_q.png`, `74_locstamp_u14_q.png` |
| **unit 13 bottom SEE SHEET No.17 / No.16 row** | "…SEE SHEET No.17. 28TH ST. SEE SHEET No.16." — **every glyph whole**, periods and descenders intact | `72_u13_bottom_row_q.png` |
| unit 2 top block-boundary rules | complete, including the tick risers v3.2 truncated | `70_u2_top_band_q.png` |

---

## 2. DARK-RIM FRACTION — **FAIL (1.2-1.4 %, bar was ~0.3 %)**

Reviewer 3's `s2e.py` is not in the tree, so it was rebuilt from its description (local-variance
content mask at 1/8, hole-filled, rim = content minus erode(13), dark = gray < 75) and
**calibrated by grid search over 36 parameter variants against its published triple**
(`qcB4r_p7_rim.py`, `140_darkrim_calibrated.json`). Best variant: var_thr 8.0, close 61,
open 25, erode 13, dark 75.

Reproduction quality — the **dark counts and absolute areas reproduce almost exactly**; the rim
*denominator* does not (mask-smoothing differences make my rim 22-34 % larger on v3.2/other):

| | reviewer 3 dark / area | **this reproduction** |
|---|---|---|
| v3.2 | 1,310 / 0.0838 Mpx | **1,314 / 0.0841 Mpx** |
| v2 | 181 / 0.0116 Mpx | **181 / 0.0116 Mpx** |
| other | 0 / 0.0000 Mpx | **16 / 0.0010 Mpx** |

Read on one consistent mask across all four artifacts:

| | rim tiles | dark tiles | **dark-rim fraction** | dark-rim area |
|---|---|---|---|---|
| **v4** | 47,004 | **552** | **1.17 %** | **0.0353 Mpx** |
| v3.2 | 49,644 | 1,314 | 2.65 % | 0.0841 Mpx |
| v2 | 64,194 | 181 | **0.28 %** | 0.0116 Mpx |
| other | 68,178 | 16 | **0.02 %** | 0.0010 Mpx |

Renormalised onto reviewer 3's own rim denominators (× 3.226/2.647, the factor that maps this
mask's v3.2 reading onto the published 3.23 %): **v4 ≈ 1.43 %**.

**v4 is 1.2-1.4 %.** That is a real halving of v3.2, but it is **~4× the ~0.3 % bar, ~4-5× v2
and ~50× other**. Visualisations: `141_rimvis_v4.png`, `141_rimvis_v2.png`,
`141_rimvis_other.png`; the marked tiles are `142_v4_rim_dark_points.json`.

## 3. TONE PERSISTENCE — **PASS**

Strict near-neutral paper mask (luma 200-248, max-min ≤ 26), 6 %-inset unit interiors,
source vs v3.2 vs v4 (`tone_clip_v4.json`):

| unit | SRC B,G,R | v3.2 B,G,R | **v4 B,G,R** | v4 R-B | v4 G-exc | v4 norm B/G/R |
|---|---|---|---|---|---|---|
| 2 | 216,230,236 | 217,231,236 | **217,231,236** | 19 | +4.5 | 0.9518/1.0132/1.0351 |
| 3 | 222,234,237 | 218,231,236 | **218,231,236** | 18 | +4.0 | 0.9547/1.0117/1.0336 |
| 4 | 220,233,237 | 218,231,237 | **217,231,237** | 20 | +4.0 | 0.9504/1.0117/1.0380 |
| 5 | 217,231,236 | 219,232,236 | **219,232,236** | 17 | +4.5 | 0.9563/1.0131/1.0306 |
| 6 | 212,227,233 | 219,232,236 | **219,232,236** | 17 | +4.5 | 0.9563/1.0131/1.0306 |
| 7 | 222,234,238 | 219,232,236 | **219,232,236** | 17 | +4.5 | 0.9563/1.0131/1.0306 |
| **9** | **220,231,236** | **219,231,237** | **219,231,237** | **18** | **+3.0** | **0.9563/1.0087/1.0349** |
| 10 | 221,233,236 | 219,231,236 | **219,231,236** | 17 | +3.5 | 0.9577/1.0102/1.0321 |
| 11a | 222,234,237 | 219,232,236 | **219,231,236** | 17 | +3.5 | 0.9577/1.0102/1.0321 |
| 11b | 223,235,238 | 218,232,236 | **218,232,236** | 18 | +5.0 | 0.9534/1.0146/1.0321 |
| 13 | 218,232,236 | 219,232,237 | **219,232,237** | 18 | +4.0 | 0.9549/1.0116/1.0334 |
| 14 | 220,233,237 | 219,231,237 | **219,231,237** | 18 | +3.0 | 0.9563/1.0087/1.0349 |

- **v4 equals v3.2 to ≤ 1 DN on every unit and every channel.** The re-converged geometry did
  not disturb the gains, exactly as the brief predicted it should not.
- **Unit 9 still sits on the edition target**: R-B 18 inside a 17-20 band, G-excess +3.0 inside
  a +3.0..+5.0 band, normalized B 0.9563 = the edition median, **R > G by 6 DN** like every
  neighbour and like its own scan.
- **Unit 9 still matches its source hue on the loose mask**: SRC (198,222,232) → v4
  **(198,222,232) — bit-identical**, gain 1.00 confirmed. No polarity inversion, no mint block.

## 4. HIGHLIGHT CLIPPING — **regression, 175 px (round 2 was exactly 0)**

Exact full-resolution census, no sampling (`qcB4r_p8_final.py`, `150_clip255_v4.json`):

- **175 of 500,606,512 pixels have any channel == 255** (per-channel R 121 / G 86 / B 0).
  Round 2 verified **exactly 0**. That is 0.35 parts per **billion**.
- **All twelve unit interiors are still 0.000 ppm, 0 px, per channel.**
- All 175 sit on the retained scan margins, in three clusters:

| n | box | what it is |
|---|---|---|
| 88 | x 277-1777, y 27378-27459 | unit 14's bottom backing board — inside FINDING B-1's band |
| 86 | x 348-349, y 13706-13859 | unit 9's left trim column |
| 1 | (12012, 26881) | Ave G sliver |

The unit-9 cluster is a **1-2 px ringing overshoot at the paint boundary**: across four adjacent
columns the composite reads 236,232,219 (fill) → **42,43,44** → **255,255,254** → 217,222,222,
while the source across the same span is a smooth 227-228 everywhere
(`202_black_is_synthetic.json`). Same unclamped edge kernel as FINDING B-1 — undershoot crushes
to 0, overshoot clips to 255. Not visible; reported because the baseline was a verified zero and
because it corroborates the root cause.

## 5. GAP FILL vs MARGIN PAPER — **PASS (worst 5 DN, was 7)**

Strict paper band inboard vs fill band outboard, **10 borders** (`160_gapfill_v4.json`,
`160_gapedge_*_q.png`). Fill is a single value **(219,232,236) BGR** — `fill_unique_colours = 1`
at all six true flat-fill bands.

| border | paper B,G,R | fill B,G,R | delta B/G/R | worst |
|---|---|---|---|---|
| u11a right — **gap** | 220,233,237 | 219,232,236 | -1/-1/-1 | **1** |
| u11b right — **gap** | 218,232,236 | 219,232,236 | +1/0/0 | **1** |
| u3 top — **D-G / 16-18 gap** | 217,230,235 | 219,232,236 | +2/+2/+1 | **2** |
| u4 right — **gap east of unit 4** | 217,231,236 | 219,232,236 | +2/+1/0 | **2** |
| u13 bottom (exterior) | 221,232,237 | 219,232,236 | -2/0/-1 | **2** |
| u2 left (exterior) | 213,227,233 | 211,227,234 | -2/0/+1 | **2** |
| u5 right (exterior) | 216,232,237 | 219,232,236 | +3/0/-1 | 3 |
| u3 right — **G-H / 18-20 gap** | 215,230,236 | 219,232,236 | +4/+2/0 | 4 |
| u2 top (exterior) | 214,229,235 | 219,232,236 | +5/+3/+1 | 5 |
| u14 bottom (exterior) | 214,228,236 | 219,232,236 | +5/+4/0 | 5 |

**Six borders at ≤ 2 DN, worst 5 DN** against round 2's worst of 7. The two 5-DN sites are the
edge-vignetted paper at unit 2's top and unit 14's bottom — the fill is closer to those units'
bulk paper than to their outermost 300 px. No perceptible step at 100 %.

## 6. CANVAS BORDER SWEEP — **FAIL (finding B-1 only)**

Line-by-line walk in from the background on all four sides, background colour taken per
artifact (v4/other 236,232,219-class; v2 216,202,176), outer 70 px of content inspected
(`170_perimeter.json`):

| side | v4 lines | v4 < gray 70 | **v4 lines carrying pure black** | v4 worst gmin | v2 | other |
|---|---|---|---|---|---|---|
| top | 2,982 | 1,209 (40.5 %) | **284** — one run, x 6-1704 | **0** | 0 lines, gmin 51 | 0 lines, gmin 59 |
| bottom | 2,982 | 406 (13.6 %) | **250** — x 264-1746, x 12006-12012 | **0** | 0, gmin 66 | 0, gmin 67 |
| left | 4,563 | 24 (0.5 %) | **17** — y 84-102, y 27384-27456 | **0** | 0, gmin 57 | 0, gmin 60 |
| right | 4,563 | 213 (4.7 %) | **0** | 52 | 0, gmin 54 | 0, gmin 67 |

- **v4 is the only one of the three with any pure-black pixel on its perimeter.** v2 and other
  have none on any side.
- The right edge — v3.2's worst — is now **completely clean** (0 black lines, gmin 52).
- The elevated "< gray 70" counts on v4's top edge are overwhelmingly the **printed double frame
  rule and compass rose** of unit 3, not bed: probing canvas y 4900-5100 gives min gray 55-58 at
  x 7000/9000, and the long vertical suspect at x ≈ 12100 is a tone step, not dark — min gray
  **214** at y 6000 with **0 px below 70** in a 350 px band (`195_vline_x12100_100pc.png`).
- Whole-canvas 1/14 overview with gray < 70 marked (`191_v4_overview_darkmarked.png`,
  `190_v4_overview_1_14.png`): the **only** visible border artifacts are the unit-2 top band and
  the unit-14 bottom band. No other dark bands, no other backing strips.
- Half-trimmed annotations found anywhere on the sweep: **one** — unit 14's GALVESTON cartouche
  (FINDING B-3). Every other margin label, oval, stamp, scale bar and sheet number checked in
  this report is whole.

---

## Findings ledger

| id | severity | site | summary |
|---|---|---|---|
| **B-1** | **FAIL** | unit 2 top, unit 14 bottom (+ Ave G) | **83,809 pure-(0,0,0) px** in 3 bands, **fabricated by the pipeline** — the mapped source pixels are light paper/backing (min gray 82 / 71, zero px below 50 in either window). v2 has 3,308 canvas-wide (one Ave G blob); other has **0 in 484 Mpx**. Worse than **both** comparators at two sites round 2 certified clean, **and** a new artifact class. Backing-board strip re-exposed at unit 14 bottom. |
| **B-2** | WARNING | unit 14 bottom-right | "J. LLOYD 10/28/85" **still absent** (NCC 0.302 vs controls 0.898 / 1.000). No longer a trim loss — the site now belongs to unit 13 across the seam at x ≈ 6211. Absent from v2 and other too, so not worse than both; checklist item unmet. |
| **B-3** | SERIOUS | unit 14 top | **OCT.1885 GALVESTON TEXAS cartouche beheaded** — flat fill occupies canvas y 20110-20481 (straight cut, identical at 4 sampled columns) while the oval spans y 20138-20508. v3.2 has it complete. New half-trimmed annotation. |
| **B-4** | WARNING | whole canvas | Dark-rim **1.17 % on a mask calibrated to reviewer 3 (≈ 1.43 % on his normalisation)** vs the ~0.3 % bar, v2's 0.28 % and other's 0.02 %. Halved from v3.2's 3.23 %, not finished. |
| **B-5** | note | u14 bottom, u9 left, Ave G | **175 px** with a channel at 255 (round 2: exactly 0). All on retained margins, all at trim boundaries; unit 9's cluster is a demonstrable 1-2 px ring (42 → 255 → 217 where the source is a flat 227-228). Same unclamped boundary as B-1. Unit interiors remain 0.000 ppm. |

**Closed since round 2:** unit 5 top wedge (36,164 → **0** px at gray 0), unit 5 right full-height
band + backing (21,008 → **0**), unit 3 right band + grey-blue backing (**min gray 214**), the
25th/Ave G street wedge and the x 12200 sliver; the right edge is now the cleanest side.
Unit 14's "28TH ST.", "SEE SHEET No.17", the full "Scale of Feet" bar, the waterworks
annotation and "130' TO 1 STY FR. COAL SHED" are all **restored whole**, with **0 discarded ink**
beyond both trims (v3.2 discarded 117,378 px).

**No regression found in:** per-unit paper tone (v4 = v3.2 within 1 DN on all 12 units; unit 9
on target and bit-identical to source on the loose mask), unit-interior clipping (0 px, 12/12),
gap-fill match (worst 5 DN over 10 borders, one fill colour), unit 13's bottom SEE SHEET row,
16TH ST., three of four GALVESTON ovals, AV. A OR WATER, SEE SHEET No.15, SEE SHEET No.3,
20TH ST., both LoC stamps, or the right and interior edges.

**Actionable, single root cause for B-1 + B-5:** the new static SCAN_INSETS are applied without
being intersected with each sheet's detected paper polygon. Where the straight inset over-runs
the sheet's diagonal torn edge — unit 14 bottom by up to ~100 px, unit 2 top by ~44 px, the
Ave G corridor by ~13 px — the uncovered wedge is left at buffer-zero instead of the paper fill,
and the same unclamped boundary rings to 255 on the bright side. Clamping the inset to the paper
polygon (or filling the residue with 236,232,219) removes 83,809 black px and 175 clipped px at
once, without giving back any of unit 14's restored annotations.

---

VERDICT: FAIL

- **FIX 3 finally lands on the sites round 2 blocked on, and unit 14 is genuinely restored.**
  The unit-5 top wedge (36,164 px at gray 0), the unit-5 right full-height band and the unit-3
  right band + backing are all at **0 pure-black px**, and unit 14's bottom and left now discard
  **0 ink** where v3.2 destroyed 117,378 — "28TH ST.", "SEE SHEET No.17", the complete "Scale of
  Feet" bar with both halves and all tick risers, the waterworks annotation (ink ratio 0.94) and
  "130' TO 1 STY FR. COAL SHED" (0.97) are all back and whole.
- **But v4 fabricates black where none exists.** 83,809 pixels at exactly (0,0,0) in three bands;
  sampled inside each band and mapped back through v4's own knots, **every one lands on light
  paper or backing board in the source** (233,226,208 / 228,221,205 / 231,224,205 …), and the
  source windows contain **no pixel below gray 50 at all** (min gray 82 on sheet 14, 71 on
  sheet 2). The two large bands sit at **unit 2's top** (21,918 px) and **unit 14's bottom**
  (59,304 px) — the exact sites round 2 certified clean — where **v2 has zero pure-black pixels
  canvas-wide and other has zero in 484 Mpx**. Worse than both comparators at the same site,
  and a new artifact class. A ~50-70 px backing-board strip is re-exposed with it.
- **A new half-trimmed annotation appeared.** Unit 14's OCT.1885 GALVESTON TEXAS cartouche is
  beheaded by a dead-straight fill boundary at canvas y 20481 while the oval runs to y 20508;
  v3.2 has the same cartouche complete. The J. LLOYD 10/28/85 signature is still missing
  (NCC 0.302 against controls of 0.898 and 1.000), now because unit 13 owns those pixels rather
  than because they were trimmed.
- **Tone and gap fill are clean and should be shipped as-is.** v4's per-unit paper matches v3.2
  within 1 DN on all twelve units; unit 9 holds the edition target (R-B 18, G-excess +3.0,
  normalized B 0.9563, R > G) and is **bit-identical to its source** on the loose mask despite
  the geometry re-solve. Gap fill is one colour across ten borders, worst delta **5 DN** (was 7),
  six borders at ≤ 2. Unit interiors clip **0 px** in 12/12 units.
- **Margins are still lost to other, and now to v2 as well.** Dark-rim **1.17 %** on a mask
  calibrated against reviewer 3's published counts (**≈1.43 %** on his normalisation) against a
  ~0.3 % bar, v2's 0.28 % and other's 0.02 %; v4 is the only one of the three with any pure-black
  pixel on its perimeter (284 top lines, 250 bottom, 17 left; v2 and other: zero on all four
  sides). One clamp — intersect the static insets with each sheet's detected paper polygon —
  clears 83,809 black px and the 175 clipped px together, and costs none of the restored
  annotations.
