# v4 QC — Reviewer C (REGRESSION vs v2 + SUPREMACY vs "other" + FINAL SCORECARD), round 3

Artifact: `build/1885/galveston_1885_composite.tif` (18188 x 27524, PAD 742)
Baselines: `compare/v2_composite.tif` (PAD 464), `compare/other_onepage.jpg`
Evidence: `build/1885/v4_qc_evidence_C/` — scripts `qcC_{lib,g1..g12,h1..h6,s2,s4..s8}.py`
Round-2 predecessor: `build/1885/v32_qc_3.md`. Nothing was fixed.

Method note honoured throughout: v4's geometry was re-converged, so **every** comparison is
locally re-aligned (`cv2.matchTemplate` TM_CCOEFF_NORMED per site); no fixed +278 offset is used
anywhere. Offsets vs v2 in fact run **+192..+449 in x and +157..+333 in y** (`g1_offsets.json`),
and the global fit gives v4 = **2.15 % wider in x, 0.49 % taller in y** than v2
(`g1_globalfit.json`) — so the warning is well founded.

---

## 1. GEOMETRY QUALITY

### (a) within-unit uniformity — **PASS on substance, misses the stated 3 % on 3 of 11 units**

Probes are content-matched window pairs inside each unit's knot bbox (350 px inset, 6x6 grid,
256 px windows, peak >= 0.70; n = 17..46 per unit; `g3_probes.json`, `g4_uniformity.json`).

```
unit   n   Laplacian var v4 -> v2      delta      local-scale CV %  x (v4/v2)   y (v4/v2)
 2    30      104.4 / 96.6            +2.26 %        3.99 / 2.76        3.31 / 1.42
 3    41      123.2 / 98.4           +11.29 %        2.84 / 3.63        0.93 / 3.21
 4    18       72.8 / 58.4           +18.04 %        0.08 / 0.29        0.23 / 1.68
 5    39       98.1 / 103.1           -0.20 %        5.61 / 4.26        2.11 / 3.60
 6    41      159.2 / 160.5           +1.65 %        2.57 / 3.10        1.81 / 2.93
 7    39      163.5 / 170.6           -1.11 %        1.42 / 0.28        0.96 / 1.43
 9    41      165.3 / 180.8           -7.81 %        3.33 / 1.51        4.04 / 4.02
10    36      116.0 / 111.9           +3.19 %        0.45 / 3.69        1.65 / 1.85
11a   46      164.1 / 158.5           +3.31 %          -  / -           8.42 / 5.97
13    17      126.7 / 127.1           +0.57 %        0.47 / 4.06        1.35 / 0.36
14    27      122.6 / 112.8           +1.77 %        1.83 / 2.08        2.44 / 4.76
11b    5        (too few probes to fit)
```

Six units are inside +-3 %, two are just outside (10, 11a at +3.2/+3.3 %), and three miss:
**u3 +11.3 %, u4 +18.0 %, u9 -7.8 %**. Two of the three are in the *sharper* direction, and u9's
is the known deliberate white-balance change moving the luma weights, not blur. To settle it I ran
three alignment-free, contrast-invariant checks against the **source sheets resampled to canvas
scale** as a third reference (`g5_sharpness.json`):

```
                     v4        v2       source
R = var(Lap)/var(Sobel), mean over units   0.0491    0.0451    0.0381
10-90 % edge rise width, mean (px)          9.88      9.77      9.67
overshoot outside source range, median     0.0010    0.0012      -
```

R differs v4-vs-v2 by <= 4 % at 9 of 12 units (u3 +8.1 %, u13 -8.0 %, u11b +34.7 % on 5 probes).
Rise widths are identical to a quarter pixel and both match the source. Overshoot is ~0.1 % in
both — no ringing. Local-scale CV (adjacent-probe spacing v4 vs source, the direct stretch test)
averages **x 2.06 % / y 2.45 % in v4 against x 2.53 % / y 2.77 % in v2** — v4 is marginally the
more uniform of the two, with u5 (x 5.61 %) and u11a (y 8.42 %) its two loosest units.

**No stretch artifacts, no resample softening, no ringing.** The 3 % Laplacian clause fails on its
own terms at u3/u4/u9 but not on substance.

### (b) seam continuity at the endpoints — **meets the stated bar; statistically a TIE**

Round-2's metric (strongest ink row each side, differenced) reproduced at its reference gate
(B=400, close=31, dth=22, gA=.55, gB=.40), 28 endpoints measurable in both, each locally aligned
(`g6c_seam_final.json`):

```
|jog| px      v4        v2        bar to beat
mean        28.61     33.14        32.71   PASS
median      28.00     26.50            -
p90         58.30     68.60        64.46   PASS
max         70.00     70.00            -
```

**v4 meets both stated numbers.** But a 9-gate sweep (`g8_seam_sweep.json`, n = 15..46) flips the
sign depending on the gate — v4 better at 4 settings, worse at 5 — and the non-seam control floor
of that metric (`g9_control_floor.json`) is **12-23 px median, p90 60-67** at every gate, i.e. as
large as the signal, because the two sides can lock onto different lot lines.

So I rebuilt the measurement: jog = the shift maximising the normalised cross-correlation of the
**whole ink profile** of the two 400 px strips flanking the seam, so every lot line votes
(`qcC_g10.py`, `g11_seam_xcorr_sweep.json`). Its control floor is **6.5 px (v4) / 5.5 px (v2)**
median — reproducing round 2's 6.6 / 7.9, so this version has real signal:

```
accept Q    n     v4 mean / med / p90      v2 mean / med / p90     ctrl med v4/v2
 >=0.30    28     32.1 / 32.0 / 60.3       29.1 / 27.5 / 53.6        11.0 / 9.0
 >=0.35    25     31.7 / 32.0 / 59.6       28.8 / 26.0 / 54.2         9.0 / 7.0
 >=0.40    20     28.7 / 28.5 / 59.1       25.5 / 22.5 / 52.1         7.0 / 6.5
```

On the robust metric v4 is **3 px worse in mean and 5-6 px worse in p90**. Paired bootstrap over
endpoints (`g12_seam_significance.json`): peak-pick mean delta **-4.5 px, 95 % CI [-14.9, +6.2]**;
x-corr mean delta **+3.0 px, CI [-8.0, +13.8]**. **Neither difference is significant.** The five
sites where the robust metric says v4 is worst were inspected (`g12_xcorr_worst*_sbs.jpg`): four
are featureless street corridors where the metric has nothing to lock onto and no reader would see
a jog. The fifth is not a jog at all — see §1(d).

**Verdict (b): passes the stated bar, TIE on the evidence.**

### (c) line straightness, 6 long lines across multiple sheets — **v4 better on 4 of 6**

Robust fit at the widest sampling (`g7b_straightness_robust.json`, WIN=150):

```
line                       n    v4 rms / max      v2 rms / max
19th St, Ave A-G          16     8.69 / 18.22      9.02 / 17.74
20th St, Ave A-J          28    18.49 / 40.93     20.26 / 48.73
23rd St, Ave A-J          39    11.93 / 25.44     12.33 / 32.74
26th St, Ave A-H           8    23.83 / 35.55     23.50 / 29.80
Avenue D, 17th-28th        9    12.81 / 24.77     29.64 / 51.26
Avenue G, 19th-28th       38    29.79 / 70.92     28.77 / 86.88
                     mean rms   17.59             20.60
                worst max dev   70.9 (Ave G)      86.9 (Ave G)
```

**Max deviation across all six lines: v4 70.9 px vs v2 86.9 px.** v4 wins outright on 20th, 23rd,
Ave D (by 2.3x) and on 19th's rms; loses marginally on 26th (max +5.7 px) and Ave G's rms
(+1.0 px). Overlays: `g7_L1..L6_*_overlay.jpg`.

### (d) NEW: v4 opens blank strips at its internal seams — **the finding of this review**

The one x-corr outlier that was not a corridor artefact turned out to be a **hole**. Measuring the
ink-free run straddling every seam, perpendicular to it, at all 61 usable endpoints
(`h4_seam_gaps.json`, identical procedure both images, locally aligned):

```
void run (px)    v4      v2
mean           167.1   103.1
median         120.0    29.0
p90            372.0   269.0
max           1091.0   419.0
endpoints >300  14 / 61   5 / 61
```

Five of these are genuine assembly holes. Exact blank masks (not bounding boxes) with the ink that
the other two artefacts carry **on exactly that ground** (`h6_holes.json`, `h6_*_triple.jpg`):

```
site                          hole area   v4 ink   v2 ink   other ink   anchors (v2 / other)
A  u2|u3   Ave D x 18th        4.76 Mpx    0.000    0.043    (n/a)       0.54 / unreliable
B  u9|u14  25th x Ave B        2.36 Mpx    0.000    0.076    0.079       0.73 / 0.71
C  u11a|u4 25th x Ave G        1.19 Mpx    0.000    0.050    0.044       0.86 / 0.60
D  u6|u10  23rd x Ave D        0.71 Mpx    0.000    0.061    0.098       0.71 / 0.68
E  u14|u13 Ave D x 26th        0.94 Mpx    0.000    0.037    0.078       0.59 / 0.52
                        total  9.96 Mpx  (~2.0 % of the canvas)
```

Typical map ink density is 8.6 %, so v2 and other are carrying **normal, fully drawn map** on
ground where v4 has literally nothing. At site B the lost content is nameable: the whole bottom
lot row **501-507**, the **"Scale of Feet" bar and its numbers**, and part of **"T. W. English Coal
Yard" / "Artificial Stone Wks"** — all present in v2 *and* in other (`h1_25th_aveB5_triple.jpg`).
The gap edge also **slices the cap-height off "25TH ST. OR BATH AV."**. Confirmed by reading the
delivered TIFF directly with `tifffile`, not through the memmap (`h7_tif_holeB_direct.jpg`).

The whole-map previews show it plainly at phone size: v4's sheet joins read as pale seams where
v2's and other's are continuous (`s6_whole_sbs.jpg`).

**In fairness, this is a redistribution, not a net loss of material.** Total ink is v4 43.12 Mpx
vs v2 41.39 Mpx; normalising for v4's 2.65 % larger area scale, v4 = 42.01 Mpx = **+1.5 % vs v2**
(`s7_content.json`). v4 gains at the outer margins (headers, ovals, SEE SHEET notes, stamps) what
it loses at the internal seams. That makes the trade a design consequence of "seam extents
frame-capped / static-inset-capped, junk caps removed" — but the loss lands in the **map body**,
which the gains do not compensate for.

---

## 2. SUPREMACY SCORECARD vs "other" (and vs v2)

### (a) tonal uniformity — **v4 WINS both** (`s2_tone_stats.json`, `s2_chroma_*.jpg`)

```
statistic                          v4        v2       other
per-unit R-G sd                   0.78      4.39      1.40
per-unit R-G range          +3.1..+5.6  -10.2..+6.5  +2.4..+6.9
per-unit R-G ptp                  2.48     16.72      4.53
per-unit L sd                     1.30      3.07      2.80
256 px tile frac |R-G| > 8       0.166     0.469     0.190
whole-map tile chroma sd          6.36      6.89      6.23
```

v4 is best on five of six columns; other is 0.13 better on whole-map tile sd — a tie in practice.
Unit 9 is +3.5 R-G, in family with every other unit. **Round-1 T-1 stays closed. WIN.**

### (b) margins / stamps present — **v4 WINS both** (`s8_b*.jpg`)

- unit 5 top: v4 keeps **"SHEET No. 3"**, **"20TH ST."**, the **OCT. 1885 / GALVESTON / TEXAS**
  oval and the sheet number **5**. v2 clips all of it under tan fill. other has 20TH ST + oval + 5
  but **loses the SEE SHEET No. 3 line**. **beats both.**
- unit 13 bottom: v4 shows **"28TH ST."** and **"SEE SHEET No.16"** whole and unsliced; v2 clips
  them under tan fill. **beats v2.**
- top strip (16th / Hulme Bros / oval): all three comparable. **tie.**
- "AV. H OR WILLIAMS E." whole with no gutter through it in v4 (`s9_aveH_williams_rot_sbs.jpg`);
  the Ave H corridor's widest ink-free run is **136 px (v4) vs 128 px (v2)** — no new gutter.

### (c) 25th / Ave G label — **FIXED. v4 ties other, beats v2. Round-2 G32-2 is CLOSED.**

`s4c_25thG_triple.jpg`, `s3_25thG_zoom_sbs.jpg`, `s5c_25thG_band_*.jpg`.

- The street label template matches **exactly once** in a 4600 x 2800 px v4 window. v3.2 printed
  it twice; v2 prints it twice.
- **Zero pixels below gray 60** anywhere in a 3400 x 2600 px window over the corridor — the
  822 x 35 px solid black scanner wedge that v3.2 dragged in is **gone**.
- The **"SEE ... No. 4"** cross-reference is present (rotated, running along Ave G).
- other: one label + a horizontal "SEE SHEET No. 4" — marginally the better *placement*, same
  information. **TIE with other, WIN vs v2.**

### (d) dark rim / scanner bands — **v4 LOSES to v2, roughly ties other**

Round 2's dark-rim fraction cannot be reproduced: v4's canvas background is paper-toned, so the
content mask degenerates (rim -> 0). Substitute measure — long thin dark runs anywhere
(gray < 90, >= 400 px long, <= 400 px thick), `s5_cde.json`, crops `s6d_*`:

```
          runs   largest                              total
v4          4    4660 x 44 px at (6296, 5036)         ~226 kpx
v2          0    -                                      0
other       5    32 x 1820 px at (13428, 24736)       ~164 kpx
```

v4's largest is a **solid black rule spanning 4660 px across unit 3's retained top margin**, right
above "4. FRAME DW'GS" / "18TH ST." — the same artefact round 2 measured at 30 x ~1500 px in v3.2,
now **3x longer**. Three shorter bands remain (1620 x 28 top-left edge, 1460 x 80 bottom-left,
616 x 44). other's five are its own internal seam lines (32-40 px wide, 1144-1820 px long).
**v2 is clean here; v4 is not. LOSE to v2.**

### (e) cross-seam registration at 22nd St — **v4 WINS both, at all five crossings**

Measured *intrinsically inside each image* with the same profile x-corr, so it is not hostage to
which artefact is treated as truth (`s5_cde.json`, `s5e_22nd_*_triple.jpg`):

```
crossing        v4 jog    v2 jog   other jog
22nd x Ave A.5    +17       +75       +90
22nd x Ave B.5    -53       -59       -78
22nd x Ave C.5     -5       -14       -64
22nd x Ave B      -25       -41       -73
22nd x Ave C      -48       -54       -80
mean |jog|       29.6      48.6      77.0
```

other's breaks are 64-90 px, in the 100-300 px band round 1 reported. **v4 is the best of the
three at every one of the five crossings. WIN.**

### (f) image quality at 3 matched sites — **v4 ties v2, beats other** (`s4f_*_triple.jpg`)

```
site                    blockiness (1.00 = none)     10-90 % rise (px)      Laplacian var
                        v4     v2    other           v4   v2  other       v4    v2  other
Ave E x 22nd (u6)      1.019  0.999  0.947            5    5     8        113   113   96
Ave G.5 x 24th (u11a)  0.981  1.021  0.947            8    9    10        139   139   99
Ave B x 17.5 (u2)      1.010  0.990  1.030           11   11    11        151   154  134
```

No JPEG blocking in any of the three. v4 equals v2 on every measure and is sharper than other at
two of three sites. **TIE v2 / WIN other.**

### Scorecard summary

| criterion | vs v2 | vs other | net |
|---|---|---|---|
| (a) tonal uniformity | **WIN** | **WIN** | **WIN** |
| (b) margins / stamps | **WIN** | **WIN** | **WIN** |
| (c) 25th / Ave G label | **WIN** | TIE | **recovered** |
| (d) dark rim / scanner bands | **LOSE** | ~tie | **LOSE** |
| (e) cross-seam registration, 22nd St | **WIN** | **WIN** | **WIN** |
| (f) image quality | TIE | **WIN** | **WIN** |
| (+) map-body completeness at seams | **LOSE** | **LOSE** | **LOSE** |

---

## 3. Reconfirmations — all held

- **No ghosting at 27th / Ave D.** Duplicate-patch self-match count in a 3200 px window at
  threshold 0.80 = **1** (the patch itself). Tracked jog **60 px (v4) vs 61 px (v2)**, inside the
  disclosed 130 px bound. v4's "AV. D OR MARKET W." runs whole and the corridor is continuous;
  v2 has a visible vertical seam through the same block (`s6_27th_aveD_sbs.jpg`).
- **Avenue D corridor numerals, 21st-22nd** (`s6_aveD_21_22_v4.jpg`) — all present and legible:
  115 117 119 121 125 127 / 186 184 182 180 / 1401-1408 / 515 516 517 518 / 152 156 158 160 162
  164 / 153 155 157 161 163 165 169 171 173 175 177 179 183 185 / 608 609 173 175; and
  "INTERNAL REVENUE OFF.", "ISLAND CITY SAVINGS BANK 1874", "Sew'g Mach's", "PICTURES & ARTISTS
  SUPPLIES", "ART SCHOOL", "Auction D.G. B&S", "Music 1st Pianos 2nd", "WASHINGTON ARTILLERY
  HALL 3rd". LoC "Map Division" stamp retained (disclosed).
- **Four legibility spot-reads** — all sharp, no blur, no double-edging
  (`s6_L1..L4_*_v4.jpg`). L2 read out in full: "Turner Hall 1=2", "Bar / Hall / Hat Rm.",
  "TEN PIN ALLEY", "BALCONY", "GAS FOOT LIGHTS", "STAGE & SCENERY", "Carp'tr Shop",
  "JEWISH SYNAGOGE", "ARTILLERY HALL", 1203 1204 1205, 151-167, 157 1/4, 157 1/2, 159 1/4.
- **Target Avenue E x 22nd** (`s6_target_aveE_22nd_triple.jpg`): content identical across all
  three; Laplacian variance **158.0 (v4) vs 158.6 (v2)**; local offset to v2 (-293, -282) at
  peak 0.685. No defect.
- Disclosed items are no worse than described: 27th jog 60 px (bound 130), Ave H corridor 136 px
  vs v2's 128 px, "AV. H OR WILLIAMS E." whole.

---

## 4. WHOLE-MAP judgement — `s6_whole_sbs.jpg`, `s6_preview_{v4,v2,other}.jpg`

Flipping between the three at phone size: v4 has the **warmest and most even sheet** (v2's
mint-green block over sheet 9 is gone and does not come back), the **most complete silhouette**
— retained headers, ovals, scale bars, SEE SHEET notes and stamps on the outer faces — and the
**straightest streets**. Against that, v4 is the only one of the three whose **internal sheet
joins are visible as pale strips**; v2 and other read as continuous fabric there.

**Is v4 the best map of the three overall? Not yet — it is the best on six of seven axes and the
worst on the one that matters most, map-body completeness.** Everywhere a reader is reading the
map, v4 is at least as good as both predecessors; but at five internal joins the map simply is
not there, and two of those are large.

Sites where a predecessor is still locally better:

| site | who is better | severity |
|---|---|---|
| u2\|u3, Ave D x 18th — 4.76 Mpx blank in the map body | **v2** | **significant** |
| u9\|u14, 25th x Ave B — 2.36 Mpx blank; lots 501-507, "Scale of Feet" and part of the Coal Yard lost; "25TH ST. OR BATH AV." sliced | **v2 and other** | **significant** |
| u11a\|u4, 25th x Ave G — 1.19 Mpx blank | **v2 and other** | **significant** |
| u14\|u13, Ave D x 26th — 0.94 Mpx blank | **v2 and other** | noticeable |
| u6\|u10, 23rd x Ave D — 0.71 Mpx blank | **v2 and other** | noticeable |
| unit-3 top margin: 4660 x 44 px solid black rule (3x longer than v3.2's) | **v2** (has no dark runs at all) | noticeable |
| three shorter dark bands: 1620 x 28 (top-left edge), 1460 x 80 (bottom-left), 616 x 44 | **v2** | cosmetic |
| seams u6\|u5 Ave G x 21st, u10\|u13 26th x Ave D / D.5, u3\|u6 20th x Ave D — jog 33-48 px worse | v2, marginally | cosmetic (at the metric's noise floor; invisible in the crops) |
| whole-map tile chroma sd 6.36 vs 6.23 | other, marginally | cosmetic |
| "SEE SHEET No. 4" placement at 25th/Ave G (horizontal in other, rotated along Ave G in v4) | other, marginally | cosmetic |

Nothing else. On tone, edge content retention, silhouette, cross-street registration, corridor
numerals, ghosting, straightness and legibility, v4 is the better artefact of the three.

---

## Findings ledger

| id | severity | site | summary |
|---|---|---|---|
| C4-1 | **FAIL** | five internal seams | v4 leaves **9.96 Mpx of blank map body** at u2\|u3 (4.76), u9\|u14 (2.36), u11a\|u4 (1.19), u14\|u13 (0.94) and u6\|u10 (0.71 Mpx). Zero ink in v4 where v2 carries 3.7-7.6 % and other carries 4.4-9.8 % — normal drawn map. At 25th x Ave B the named losses are lots 501-507, the "Scale of Feet" bar and part of "T. W. English Coal Yard"/"Artificial Stone Wks", and the gap edge slices "25TH ST. OR BATH AV.". Verified in the delivered TIFF. Seam-wide: ink-void run mean 167 px (v4) vs 103 px (v2), max 1091 vs 419, 14 endpoints >300 px vs 5. **Worse than BOTH predecessors at the same sites** (B, C, D, E confirmed against both; A against v2, other's anchor there was unreliable). |
| C4-2 | WARNING | unit 3 top margin, three edges | Four long thin dark runs survive, the largest a **4660 x 44 px solid black rule** across unit 3's retained top margin — 3x longer than the band round 2 measured in v3.2. v2 has none. Criterion (d) lost to v2, ~tied with other. |
| C4-3 | WARNING | u3, u4, u9 | Per-unit Laplacian variance on content-matched windows moves +11.3 %, +18.0 % and -7.8 % — outside the 3 % clause. Alignment-free checks (R index, 10-90 % rise, overshoot, all referenced to the source sheets) show **no softening, no ringing, no stretch**; u3/u4 move in the sharper direction and u9's is the deliberate white-balance change. Metric violation, not a defect. |
| C4-4 | note | all units | Offsets vs v2 run +192..+449 x, +157..+333 y; global fit 2.15 % wider in x, 0.49 % taller in y. Consistent with the brief's "re-converged from zero" disclosure, but worth recording since it invalidates every earlier round's coordinate frame. |
| C4-5 | note | seams generally | Round-2's seam metric has a 12-23 px control floor and flips sign with its gate. A cross-correlation replacement with a 6.5 px floor puts v4 3 px behind v2 in mean; neither metric's difference is significant (bootstrap CIs straddle zero). Seam continuity is a TIE, and v4 does meet the stated 32.7 / 64.5 bar. |

**Closed since round 2:** G32-2 — the 25th/Ave G label is now printed **once**, the 822 x 35 px
black wedge is gone (zero sub-60 pixels in the whole corridor window), and the SEE SHEET No. 4
cross-reference is retained. Criterion (c) is recovered.

**No regression found in:** tone (v4 beats both on five of six statistics), retained
margins/headers/stamps (beats both at unit 5 top, beats v2 at unit 13 bottom), sharpness and
blockiness (equals v2, beats other), cross-22nd-St registration (best of three at all five
crossings), line straightness (best on four of six lines, worst-case max deviation 70.9 px vs
v2's 86.9), 27th/Ave D ghosting, Avenue D corridor numerals, four legibility spot-reads, or the
Avenue E x 22nd target.

VERDICT: FAIL

- **v4 drops 9.96 Mpx of drawn map at five internal seams — content that BOTH v2 and other
  carry.** At 25th x Ave B a whole lot row (501-507), the "Scale of Feet" bar and part of the
  Coal Yard block are simply absent, and the gap edge slices the top off "25TH ST. OR BATH AV.".
  Verified against the delivered TIFF. This is the protocol's FAIL condition — worse than both
  predecessors at the same site — and it is a new artifact class relative to round 2.
- **It is a redistribution, not a shortfall of material:** total ink is +1.5 % vs v2 after scale
  normalisation, because v4 gains at the outer margins what it loses at the joins. The gains are
  in the margins; the losses are in the map body.
- **Five of the seven scorecard axes are won outright.** Tone (per-unit R-G sd 0.78 vs other's
  1.40 and v2's 4.39; tile fraction 0.166 vs 0.190 / 0.469), margins and stamps, cross-street
  registration at 22nd (mean jog 29.6 vs v2 48.6 vs other 77.0), image quality (equals v2, beats
  other), and line straightness (worst max deviation 70.9 px vs v2's 86.9).
- **Round 2's FAIL is properly closed.** One "25TH ST. OR BATH AV." print, no black wedge
  anywhere in the corridor, SEE SHEET No. 4 retained. Criterion (d) is still lost — four dark
  runs survive, the worst a 4660 x 44 px black rule over unit 3's header, against v2's zero.
- **Geometry itself is sound.** No stretch artifacts, no softening, no ringing against the source
  sheets; seam residuals tie v2 on two independent metrics and meet the stated 32.7 / 64.5 bar.
  Fix the seam holes and v4 is unambiguously the best of the three.
