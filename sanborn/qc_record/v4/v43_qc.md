# v4.3 QC — FINAL CONFIRMATION (round 5), the last gate before packaging

Artifact: `build/1885/galveston_1885_composite.tif` — 27524 x 18188 x 3, photometric 2,
LZW, 584,326,688 bytes, **mtime Sat Aug 8 07:36:09 2026**. Read with `tifffile`, dumped
to `build/1885/v43_raw.dat`; the dump is **md5-identical to the direct `tifffile` page
read on 6 sampled rows** (100 / 5000 / 13762 / 20000 / 27000 / 27523), so every number
below is the delivered TIFF (`q43_mk.py`, `000_artifact_identity.json`). Dimensions
unchanged. Geometry read fresh from `build/1885/registration.json` (mtime 07:34) and
`coverage_mask.png` (07:36).

Comparators: `compare/v2_composite.tif` (26968 x 17632, PAD 464), `compare/other_onepage.jpg`,
and — for change tracking — `build/1885/v42_raw.dat` (round 4's artifact).
**Every** cross-artifact comparison is locally re-aligned (`cv2.matchTemplate`
TM_CCOEFF_NORMED over a ring of anchor patches, so a blank site never drives its own fit).
No fixed offset is used anywhere. Measured offsets to v2 at the sites below run
x −187..−377, y −254..−397.

Evidence: `build/1885/v43_qc_evidence/`. Scripts: `q43_lib.py`, `q43_mk.py`,
`q43_p1_census.py`, `q43_p1b_diffmap.py`, `q43_p1c_tiles.py`, `q43_p2_voids.py`,
`q43_p3_labels.py`, `q43_p4_read.py`, `q43_p5_recover.py`, `q43_p5b_recover_inplace.py`,
`q43_p6_22nd.py`, `q43_p7_strips.py`, `q43_p8_findlabels.py`, `q43_p9_vstrips.py`,
`q43_p10_v2strips.py`, `q43_p11_dup.py`, `q43_p12_bandread.py`, `q43_p13_rim.py`,
`q43_p14_scalebars.py`, `q43_p15_spot.py`, `q43_p16_margins.py`, `q43_p17_flat.py`,
`q43_p18_jog.py`, `q43_p19_named.py`. **Nothing was modified.**

---

## 0. What actually changed between v4.2 and v4.3 — measured, not taken on trust

Exact full-resolution pixel diff against `v42_raw.dat` (`q43_p1_census.py`,
`q43_p1c_tiles.py`, `011_diffmap_v43_vs_v42.png`, `011_change_groups.json`):

```
changed pixels           6,953,778  of 500,606,512  (1.39 %)
change region 1   x     0- 6,656   y  5,120-15,872   2.76 Mpx  Ave D column + the 22nd St band
change region 2   x 11,776-12,288  y  8,704-19,968   1.99 Mpx  Ave G column
change region 3   x 11,776-12,032  y 25,344-26,624   0.01 Mpx  Ave G at 27th-28th
```

Resolved into seam geometry: the **h22 7|9 cut moved down ~190 px** (a 136 px band,
y 13,727-13,863, running x 150→6,100), the **Ave D column seam** was re-cut from
y 5,120 to 15,872 (x 6,104-6,456), and the **Ave G column seam** was re-cut from
y 8,704 to 19,968 (x 11,774-12,066 above 23rd, x 11,803-11,986 below).

**Two of round 4's five void sites were not touched at all.** Over the full 3600 x 3600
site windows:

```
site B  u9|u14  25th x Ave B   x 1644-5244, y 18477-22077   changed pixels: 0
site E  u14|u13 Ave D x 26th   x 4517-8117, y 20847-24447   changed pixels: 0
```

Site B is **byte-identical to v4.2**. That is the single most important fact in this
report: round-4 reviewer 1's FAIL **1-1** and reviewer 2's **R2-1(B)** were raised on
exactly this ground and **v4.3 does not address them**. Site E was already closed in
round 4, so its being untouched is fine.

The Tremont band (site D's headline loss) is likewise effectively untouched:
**9,334 changed pixels of 750,000** (1.2 %) in x 6300-7800, y 15650-16150.

---

## 1. CHECKLIST 1 — VOID CLOSURE

### 1(a) Hole census, round-3 C / round-4 reviewer-1 procedure reproduced exactly
3600 px window on each site, ink < 185, 161 px dilation, largest component
(`q43_p2_voids.py`, `100_voids_v43.json`, crops `100_*_quad.jpg`).

```
site                         v4.3 void  v4.2 void   on declared   ink on v4.2's void ground
                               (Mpx)      (Mpx)        gap        v4.3    v2     other
A u2|u3   Ave D x 18th          4.812      5.222       88 %      0.0000  0.0467  0.0449
B u9|u14  25th x Ave B          1.061      1.061        0 %      0.0000  0.0561  0.0509
C u11a|u4 25th x Ave G          0.993      1.226        3 %      0.0015  0.0529  0.0444
D u6|u10  23rd x Ave D          0.688      0.750        0 %      0.0245  0.0979  0.1149
E u14|u13 Ave D x 26th          0.299      0.299        0 %      0.0000  0.0461  0.1784
N1 Ave D 22-23 (new band r4)    0.312      0.866        0 %      0.0260  0.0622  0.1187
N2 Ave G 20-23 (new band r4)    1.595      2.107        0 %      0.0178  0.0509  0.0433
    five round-4 sites          7.853      8.558   (−8 %)
```

**The builder's "ink 4.8-9.5 % at all five" is true of the site *windows* and tells you
nothing about the voids.** Window ink: A 7.44 %, B 12.24 %, C 8.62 %, D 16.29 %,
E 11.28 % — against v2's 9.46 / 12.21 / 8.93 / 17.22 / 11.08 %. The blank *bands inside*
those windows still carry **0.00 ink** at A, B and E.

### 1(b) Content-recovery test — is the RIGHT content there?
v2 ground falling inside v4.2's void, tiled into 176 px inked templates, each searched
anywhere within ±750 px of v4.3 (`q43_p5_recover.py`, `320_recover_v43.json`).
Control (same template inside v2) = 1.00 throughout.

```
site   n     median peak in v4.3 (v4.2)   found      absent   declared-gap tiles
A    225          0.64  (0.64)            68 % (68 %)  16 %        162 / 225
B     58          0.62  (0.62)            72 % (72 %)   3 %          0 / 58
C     56          0.89  (0.89)            98 % (98 %)   0 %          1 / 56
D     45          0.59  (0.65)            64 % (67 %)  13 %          0 / 45
E     11          0.93  (0.93)           100 % (100%)   0 %          0 / 11
N1    34          0.61  (0.49)            56 % (44 %)  18 %          0 / 34
N2    89          0.72  (0.72)            88 % (90 %)   0 %          0 / 89
```

Only **N1 improves** on this metric. A, B, C, E are numerically identical to v4.2;
D is 3 points worse.

### 1(c) Site-by-site read at 100 % — the decisive evidence

**A — u2|u3, Ave D x 18th: unchanged in substance. WARNING (worse than v2, and than
"other" at moderate confidence).** `550_AvD_1819.jpg`, `660_aveD_seesheet_overlap.jpg`.
88 % of the 4.81 Mpx blank is the **disclosed D-G x 16-18 coverage gap**; 0.577 Mpx sits
on claimed ground (v4.2: 0.74). v4.3 recovers a thin sliver of covering paper at the top
of the strip and nothing else. The **block-326 lot row is still absent**: v2 draws
*Boarding / Vac. S.3 / Dw'g / 501 / "80'" / 303 310 312 314 318 320 322 326*; "other"
draws the same row (*1603 310 312 314 318 320 322 326*, alignment peak 0.63). v4.3 shows
bare paper carrying only "SHEET No.2" and "70'".

**B — u9|u14, 25th x Ave B: BYTE-IDENTICAL to v4.2. FAIL, unchanged.**
`300_B_void_full.jpg`, `302_B_void_bot.jpg`, **`310_B_east.jpg`**.
West half (read at 100 %): below "Compounding Rm 2ᵉ" the whole lower block face is blank
in v4.3 where **v2 and "other" both draw** the *1½" V.P. FROM TANK ON ROOF WITH SMALL
HOSE* note, the *1 Off.* building, the block wall, lots **501 502 503**, the **20'**
dimension and the **6" W. PIPE** dashed main with its caption. v4.3 puts a clipped
"…HEET" margin fragment over the blank.
East half: v4.3 lays unit 14's top margin ("NO. 9" + the GALVESTON cartouche + sheet
number 14) over the ground where **v2 and "other" both draw** the **"Scale of Feet."
caption AND its graduated ruler**, the **"SCALES"** box, **"Coal Off."**,
**"T. W. English Coal Yard"** (v4.3 keeps only the clipped "…ENGLISH / …AL YARD"),
**"Artificial Stone Wks"** (only "…al Wks"), lots **506 507 508** and the **70'/20'**
dimensions. **Worse than BOTH comparators at the same site. This is round-4 finding 1-1
verbatim, with zero pixels changed.**

**C — u11a|u4, 25th x Ave G: confirmed a non-loss.** `309_C_void.jpg`.
98 % of v2's ink on that ground is recoverable in v4.3 at median peak 0.89; the apparent
blank is v2's *second* print of "25TH ST. OR BATH AV." (v4.3 prints it once — correct)
plus a label-row displacement. 607 / 618 / 617 / 156 / *Dress Maker* / *Furn. Repair* /
*Vac. S.* all present. Not a defect.

**D — u6|u10, 23rd x Ave D: FAIL, effectively unchanged.**
**`303_D_tremont.jpg`**, **`550_D_tremont2.jpg`** (v4.3 / v4.2 / v2 / other at 100 %).
The 23rd St band at x 6,050-7,250, y ≈ 15,730-16,140 is bare paper in v4.3 exactly as in
v4.2 (1.2 % of pixels changed). Absent from v4.3, **carried by v2 AND by "other"**:
**"TREMONT OPERA HO."**, **"IRON COVERED CORNICE"**, block numbers
**601 602 156 158 160 162** and **166 168 172 174 176**, and the five-line fire note
(*ABOVE 1ST OPEN FROM 2ND TO ROOF. / 4 BABCOCK FIRE EXTINGUISHERS. 2" WATER / PIPE FROM
TANK UNDER ROOF TO STAGE / WITH 1¼" HOSE CONNECTED IN FLIES & / IN STAGE. 200' HOSE.*).
Only "80'" and a D.H. survive. **Round-4 finding 1-2, not fixed.**

**E — u14|u13, Ave D x 26th: closed.** `308_E_void.jpg`. Block 514/575, 58½, 58⅓,
BAKE/OVEN all match v2; 100 % tile recovery, median peak 0.93.

### 1(d) The two round-4 bands — synthetic fill eliminated, content partly restored

**N1, Avenue D 22nd-23rd — the 301 x 1954 px flat band is GONE.**
`305_N1_aveD_2223.jpg`, **`550_AVD_2223.jpg`**, `720_flatbands.json`.
Flat pixels in the corridor box **591,619 → 0**; exact fill colour (236,232,219) in the
band **96.9 % → 0.3 %**; ink **0.21 % → 3.85 %**. Restored: real covering paper, the
south block's tick row **101-131**, and sheet 6's west-margin **"SEE SHEET No. 9."**
cross-reference. **Still absent** (v2 and "other" both carry it): the north block's
south-face tick row **1303 / 110 112 114 116 122 124 126 128 132 134 136 138 140 142**,
the **70'** street width, and the facing **"SEE SHEET No. 6."** note.
→ the *new artifact class* of round 4 is closed; a content shortfall remains.

**N2, Avenue G 20th-23rd — the 258 x 6276 px flat band is GONE.**
`306_N2_aveG_2023.jpg`, **`540_AVG_E_2023_label.jpg`**, **`550_AVG_2122.jpg`**.
Flat pixels **1,611,780 → 0**; fill colour **100 % → 0.1 %**; ink **0.00 % → 2.36 %**.
**"AV. G OR WINNIE OR MENARD E." is now whole** — cap heights intact, side-by-side with
v4.2's beheaded version and with v2/other (`540_*`). **Still absent** (v2 and "other"
both carry it): the block's east-face lot/dimension column —
**152 158 100 1404 104 1405 1406**, **200 202 204 206 208 210**, **1407 1408** — and the
adjacent **80'/70'** widths.

### 1(e) Synthetic fill, canvas-wide
`q43_p17_flat.py`, `720_flatbands.json`. Exact fill-colour census over all 500.6 Mpx:

```
                       total flat fill    of which INSIDE the coverage mask
v4.3                     143.09 Mpx                  1.70 Mpx
v4.2                     146.05 Mpx                  4.67 Mpx
```

**Synthetic fill laid over ground the build claims to cover is down 64 %, −2.97 Mpx.**
Per-box: Ave D 22-23 591,619→0; Ave G 20-23 1,611,780→0; Ave D 20-22 192,375→0;
22nd A-D 84,088→0; 19th 74,060→0; 20th 22,635→0; 23rd 57,082→24,960.
**No box got worse.** Remaining large boxes (Ave G 16-20 3.30 Mpx, 25th A-D 0.83 Mpx,
Ave H 0.18 Mpx) are unchanged from v4.2 and are the disclosed gap / gutter classes.

---

## 2. CHECKLIST 2 — LABEL INVENTORY (full, cuts reshuffled)

Corridor strips read at 100 % (`500_*_v43strip.jpg`, `510_*`, `520_*`, `521_*`) plus a
**canvas-wide duplication census**: template cut from v4.3 at each label, searched over
the entire canvas at 1/2 scale with non-max suppression (`q43_p11_dup.py`,
`530_dupcensus.json`). A "hit" is a match ≥ 0.72; 0.55-0.65 matches are typeface noise
("ST." recurring) and were checked individually.

| label | strong hits in v4.3 | whole? | verdict |
|---|---|---|---|
| **19TH ST.** (A-D) | 1 (1.00) | yes | **pass** — plus its complete Scale of Feet caption + ruler |
| **20TH ST.** (D-G) | 1 (0.99) | yes | **pass** |
| **22ND ST.** (A-D) | 1 (0.98) | **yes** | **pass — round-4 FAIL 1-3 FIXED** (below) |
| **23RD OR TREMONT** (A-D) | 1 (1.00) | yes | **pass** |
| **23RD OR / TREMONT** (G-I) | 1 (0.98) | stepped | **disclosed** — 11a\|11b panel step, left arm of the "T" still clipped; legible |
| **25TH ST. OR BATH AV.** (A-D) | 1 (1.00) | yes | **pass** |
| **25TH ST. OR BATH AV.** (G-H) | 1 (0.96) | yes | **pass** (v2 prints this one twice) |
| **26TH ST.** — Ave E-F print | 1 (0.96) | yes | **pass** |
| **26TH ST.** — Ave G-H print | 1 (0.99) | yes | **pass** — the 0.719 secondary hit is the *27TH ST.* label at (12448, 24756), not a duplicate |
| **AV. D OR MARKET E.** | 3 prints, all at distinct corridor positions | yes | **pass** — with SEE SHEET No.2 / No.3 / No.7 / No.9 |
| **AV. D OR MARKET W.** | 3 prints, distinct positions | yes | **pass** — with SEE SHEET No.14 / No.9 |
| **AV. G OR WINNIE OR MENARD E.** (16-23) | 2 prints, distinct positions | **yes** | **pass — the 20-23 beheading is FIXED** |
| **AV. G OR WINNIE OR MENARD E.** (25-27) | **2 parallel prints, ~200 px apart** | yes | **warning, pre-existing** (below) |
| **AV. G OR WINNIE OR MENARD W.** | 2 prints, distinct positions | yes | **pass** |
| **AV. H OR WILLIAMS E.** | 2 prints, distinct positions | yes | **pass** — runs whole through the gutter |

**22ND ST. is repaired.** `400_22ND_quad.jpg`, `401_22ND_100.jpg`. Glyph-band ink in a
420 x 300 px box on the label:

```
v4.3 8,114 px    v4.2 2,254 px    v2 8,616 px    other 9,487 px
glyph row extent  v4.3 117-192    v4.2 117-138   (v4.2 kept 21 of 75 rows)
```

94 % of v2's ink, full cap height, the **10" W. PIPE** caption back, single instance.

**AV. G OR WINNIE OR MENARD E. is still printed twice between 25th and 27th.**
`640_aveGseam_2.jpg`, `510_AVG_22_28.jpg`. Two parallel prints at x ≈ 11,816 and
x ≈ 12,013, carrying "SEE SHEET No.11" and "SEE SHEET No.10" respectively — the facing
margins of sheets 10 and 11, both retained. Both are whole and legible. **Identical in
v4.2 and in round-3 v4, so the re-knotting did not cause it.** Pre-existing warning.

**The re-cutting itself introduced no new label damage.** The h22 seam (`630_h22seam_*.jpg`)
and the Ave G / Ave D seams (`640_*`, `650_*`) were walked end to end: no label is newly
doubled, and no *label* is newly sliced. One piece of retained map furniture is — §4.

---

## 3. CHECKLIST 3 — CENSUS

Full resolution, **every one of the 500,606,512 pixels**, no sampling
(`q43_p1_census.py`, `010_census_v43.json`; `q43_p13_rim.py`, `600_darkrim_calibrated.json`,
`602_darkruns.json`).

| statistic | **v4.3** | v4.2 | v2 | other |
|---|---|---|---|---|
| pure (0,0,0) px | **0** | 0 | 3,308 | 0 |
| px with gray == 0 | **0** | 0 | — | — |
| px with gray < 50 | **22** | 22 | 13,145 | 1 |
| px with any channel == 255 | **0** (R 0 / G 0 / B 0) | 0 | — | — |
| long thin dark runs (gray<90, ≥400 px long, ≤400 px thick) | **0** | 0 | **0** | **5** (largest 32 x 1820) |

**Both builder claims confirmed exactly: pure-black 0, channel-255 0.** The 22 remaining
sub-gray-50 pixels are the same single 170 x 90 px cluster at x 747-913 / y 6103-6194 that
round 4 back-mapped to genuine sheet-2 ink (source gmin 45-48) — unchanged.

**Dark rim, calibrated method.** Round 3's procedure verbatim (local-variance content mask
at 1/8, hole-filled, largest component, rim = content − erode(13), dark = gray < 75),
re-calibrated by the same 36-variant grid search against reviewer 3's published triple.
The search **independently re-selected the same variant** (var_thr 8.0, close 61, open 25)
and reproduced his numbers (v3.2 1,314 vs published 1,310; v2 **181** vs published 181):

| | rim tiles | dark tiles | **dark-rim fraction** | dark-rim area |
|---|---|---|---|---|
| **v4.3** | 49,800 | **6** | **0.0120 %** | **0.0004 Mpx** |
| v3.2 | 49,644 | 1,314 | 2.6468 % | 0.0841 Mpx |
| **v2** | 64,194 | 181 | **0.2820 %** | 0.0116 Mpx |
| **other** | 68,178 | 16 | **0.0235 %** | 0.0010 Mpx |

Renormalised onto reviewer 3's own rim denominators (factor 0.821): **v4.3 ≈ 0.0146 %**.
Target ≤ 0.30 %. **v4.3 is 25x inside the bar, 24x better than v2 and 2x better than
"other"** — identical to v4.2, no regression. Visualisations `600_rimvis_*.png`.

---

## 4. CHECKLIST 4 — SCALE BARS

Caption census: template cut from v4.3's clean 19th-St instance, searched canvas-wide at
1/2 scale, then every hit read at 100 % (`q43_p14_scalebars.py`, `620_scalebars.json`,
`620_v43_cap*.jpg`, `621_*`, `622_numerals_zoom.jpg`).

```
                 captions found (peak)
v4.3   3    19th 1.00     22nd 0.685    26th 0.643
v4.2   2    19th 1.00                   26th 0.643
v2     8
other  8
```

**The widened owner window (+560) recovered one caption: 22nd A-D. Retention is 3 of 7.**

- **19th A-D — complete.** Caption + numerals 10/0/50/100 + full graduated bar (`610_probe_19th_scale.jpg`).
- **26th D-G — complete.** Caption + 20/10/0/50/100/150 + full graduated bar, with
  "SEE SHEET NO.13" and the F.H.S. 10.29.85 signature (`620_v43_cap2_*.jpg`).
- **22nd A-D — RECOVERED BUT SLICED.** `620_v43_cap1_1212_13764_pk0.69.jpg`,
  **`613_22nd_ruler_100.jpg`**, **`622_numerals_zoom.jpg`**, `612_22nd_scalebar_tall.jpg`.
  The caption "Scale of Feet." is whole, but the **numeral row is cut horizontally
  through the middle of the glyphs** at y ≈ 13,862 — the new h22 7|9 seam — leaving
  "50", "1oo" and "15o" as top-half fragments under the block face of lots 523/524;
  the graduated bar itself is below the cut and absent. **v2 and "other" both carry the
  numeral row whole and un-cut at this site** (`621_v2_22nd_scalebar.jpg`,
  `621_other_22nd_scalebar.jpg`). In v4.2 nothing at all was rendered here, so this is a
  **new artifact introduced by the re-cut**, and it is the checklist's own explicit
  FAIL trigger ("unless a bar is SLICED mid-glyph").
- **Absent entirely:** 20th D-G (replaced by the OCT.1885 cartouche), 23rd D-G, 23rd G-I,
  25th A-D (the site-B blank), Ave A-B x 28th.

---

## 5. CHECKLIST 5 — SPOT REGRESSION SWEEP

`q43_p15_spot.py`, `q43_p16_margins.py`, `q43_p18_jog.py`, `q43_p19_named.py`,
`700_spot.json`, `710_perimeter.json`, `730_jogs.json`.

**Target — Avenue E x 22nd** (`700_target_AveE_22nd.jpg`): **byte-identical to v4.2.**
Blockiness 0.982 (1.00 = none; v2 1.022, other 0.983); Laplacian variance 155.8
(v2 160.2, other 133.5); ink 0.1687 (v2 0.1725, other 0.1783). No blocking, no regression.

**26th and 27th at Avenue D** (`731_jog_*.jpg`): **byte-identical to v4.2 — every metric
reproduces v4.2 to the digit.** Profile-correlation jog: **26th +73 px** (v2 +143),
**27th +82 px** (v2 +61) — both **≤ 110**. The corridor-centre metric reads −122 / −68
(v2 −95 / −138), but its own non-seam control at the same site reads −285 px, i.e. the
measurement sits below the metric's noise floor here. Round 4's recorded metric conflict
persists unchanged; nothing regressed.

**11a|11b panel step**: +67 px at 23.5 (xcorr peak 0.40) and −92 px at 24.0 (peak 0.34),
**identical to v4.2** and consistent with the disclosed ~84 px. `registration.json`
still carries the measured content offset (−112.7, −29.9, peak 0.71).

**Unit 14 cartouche** (`745_u14_cartouche_100.jpg`): **"OCT. 1885 / GALVESTON / TEXAS"
whole**, full oval rule top and bottom, with sheet number **14** and "NO. 14." — intact.

**Unit 13 bottom SEE SHEET row** (`746_u13_bottom.jpg`): **"28TH ST.", "SEE SHEET No.17",
"SEE SHEET No.16"** all whole and unsliced, divider rule intact, with AV. E / AV. F /
AV. G headers. Unit 14's bottom row likewise intact.

**Margins, all four edges, low res + line-by-line walk** (`711_edge_*.jpg`):

| side | v4.3 lines | v4.3 sub-gray-70 | **v4.3 pure-black** | v2 sub-70 | other sub-70 |
|---|---|---|---|---|---|
| top | 6,122 | **0 (0.0 %)** | **0** | 429 (7.3 %) | 325 (5.5 %) |
| bottom | 13,689 | 83 (0.6 %) | **0** | 4 (0.0 %) | 24 (0.3 %) |
| left | 27,233 | 35 (0.1 %) | **0** | 894 (3.4 %) | 619 (2.3 %) |
| right | 6,794 | **0 (0.0 %)** | **0** | 291 (4.1 %) | 23 (0.3 %) |

**No pure-black pixel on any perimeter**; cleanest of the three on three sides. No black
bands, no backing board, no debris. Whole-canvas overview `800_overview_v43.jpg`: the
composite reads as one continuous document, the two round-4 fill bands are visibly gone,
and the only remaining pale strips are the disclosed gaps and the joins listed above.

---

## 6. Findings ledger

| id | severity | site | summary |
|---|---|---|---|
| **3-1** | **FAIL** | u9\|u14, 25th x Ave B (window x 1644-5244, y 18477-22077) | **0 pixels changed since v4.2 — round-4 FAIL 1-1 / R2-1(B) is untouched.** 1.06 Mpx blank, 100 % on claimed ground. Absent from v4.3 and carried by **v2 AND "other"**: the **"Scale of Feet." caption + graduated ruler**, **"SCALES"**, **"Coal Off."**, **"T. W. English Coal Yard"**, **"Artificial Stone Wks"**, lots **506/507/508** and **501/502/503**, the **70'/20'** dimensions, the **1½" V.P. FROM TANK** note and the **6" W. PIPE** main. Worse than BOTH. |
| **3-2** | **FAIL** | u6\|u10, 23rd x Ave D (x 6050-7250, y 15730-16140) | **1.2 % of pixels changed since v4.2 — round-4 FAIL 1-2 is untouched.** **"TREMONT OPERA HO."**, **"IRON COVERED CORNICE"**, the five-line Babcock fire annotation and blocks **601/602/156/158/160/162** and **166-176** absent; **v2 and "other" both complete**. Worse than BOTH. |
| **3-3** | **FAIL / NEW** | 22nd A-D scale bar (x ≈ 1350-2100, cut at y 13,862) | The re-cut **h22 7\|9 (+190)** seam runs **through the middle of the scale-bar numeral glyphs** — "50", "100", "150" survive as top halves; the graduated bar is gone. **v2 and "other" both carry the row whole.** New artifact class relative to round 4, whose sweep found "no cut newly slices" any retained item. |
| 3-4 | WARNING | Ave D 22nd-23rd | Flat band **eliminated** (591,619 → 0 flat px) and paper + the 101-131 tick row + "SEE SHEET No.9" restored, but the facing **"SEE SHEET No. 6."**, the **70'** width and the **1303 / 110-142** dimension row are still absent; v2 and other carry them. |
| 3-5 | WARNING | Ave G 20th-23rd | Flat band **eliminated** (1,611,780 → 0 flat px) and **"AV. G OR WINNIE OR MENARD E." restored whole**, but the east-face lot column **152/158/100/1404/104/1405-1408** and **200-210** is still absent; v2 and other carry it. |
| 3-6 | WARNING | Ave D x 18th, u2\|u3 | 4.81 Mpx blank, **88 % the disclosed D-G x 16-18 gap**; 0.577 Mpx on claimed ground (v4.2 0.74). The **block-326 lot row** (*Vac. S.3 / Dw'g / 501 / 303 310 312 314 318 320 322 326 / 80'*) remains absent; v2 draws it and "other" appears to as well (alignment peak 0.63). |
| 3-7 | WARNING | scale bars | **3 of 7 retained** (19th and 26th complete, 22nd sliced — see 3-3). Absent: 20th D-G, 23rd D-G, 23rd G-I, 25th A-D, Ave A-B x 28th. v2 and "other" have all of them. |
| 3-8 | WARNING | Ave G, 25th-27th | **"AV. G OR WINNIE OR MENARD E." printed twice**, parallel prints ~200 px apart at x ≈ 11,816 / 12,013 (the retained facing margins of sheets 10 and 11). v2 and "other" print it once. Pre-existing — identical in v4.2 and round-3 v4. |
| 3-9 | WARNING | 25th at Ave G | The round-3/4 fill band persists (~0.83 Mpx flat in the 25th A-D corridor box, unchanged), still beheading the horizontal "SEE … SHEET No. 11." note. |
| 3-10 | note | 26th at Ave D | Two valid metrics still disagree (profile +73 px vs corridor-centre −122 px, the latter below its own −285 px control floor). Byte-identical to v4.2; no regression. |
| 3-11 | note | 23rd G-I panel split | Step ~67-92 px measured, matching the disclosed ~84 px; the panel edge still clips the left arm of the "T" in TREMONT. Legible. |

## 7. Genuinely fixed in v4.3 — verified, not taken on trust

- **"22ND ST." (Ave A-D) is whole and single** — glyph-band ink 2,254 → 8,114 px against
  v2's 8,616 (94 %), full cap height restored, the 10" W. PIPE caption back. Round-4
  FAIL 1-3 **closed**.
- **Both round-4 synthetic bands are gone.** Ave D 22-23: 591,619 → **0** flat px.
  Ave G 20-23: 1,611,780 → **0** flat px. Canvas-wide, synthetic fill sitting on ground
  the build claims to cover falls **4.67 → 1.70 Mpx (−64 %)**. The *new artifact class*
  of round 4 is eliminated.
- **"AV. G OR WINNIE OR MENARD E." is no longer beheaded** at 20th-23rd — cap heights
  intact against v2 and "other".
- **Void area at the five round-4 sites 8.56 → 7.85 Mpx (−8 %)**, with no site worse.
- **Every census target held:** pure black 0, channel-255 0, long thin dark runs 0
  (v2 0, other 5), dark rim 0.0120 % (v2 0.282 %, other 0.0235 %), zero pure-black
  perimeter pixels on all four sides, cleanest perimeter of the three on three sides.
- **No regression anywhere it was swept:** unit-14 cartouche, unit-13 bottom SEE SHEET
  row, Ave E x 22nd sharpness/blockiness, the 26th/27th Ave D jogs, the 11a|11b panel
  step, all thirteen corridor labels single and (bar the disclosed panel step) whole,
  and no flat-band box got worse.

---

## 8. Consolidated disclosure list for the production report

Round 4 reviewer 2's twelve items, updated to v4.3 and merged with this round's findings.
Items **1, 4, 7, 8, 13, 14** changed; **15-17** are new.

1. **Blank ground at internal sheet joins (7.85 Mpx across five joins, ~1.6 % of the
   canvas; 3.6 Mpx of it inside the sheet footprints).** Ave D x 18th (u2|u3) 4.81 Mpx
   near (6317, 4830); 25th x Ave B (u9|u14) 1.06 Mpx near (3444, 20277); 25th x Ave G
   (u11a|u4) 0.99 Mpx near (11964, 20277); 23rd x Ave D (u6|u10) 0.69 Mpx near
   (7284, 15918); Ave D x 26th (u14|u13) 0.30 Mpx near (6317, 22647). **Named detail
   not carried into the composite:** the **"TREMONT OPERA HO."** block with its
   "IRON COVERED CORNICE" and four-Babcock fire annotation and blocks 601/602/156-162
   (23rd/Ave D); the **"Scale of Feet" bar, "T. W. English Coal Yard", "Artificial Stone
   Wks", "Coal Off.", "SCALES" and lots 501-508** (25th/Ave B); the **block-326 lot row
   303-326** (Ave D/18th). *Users needing these blocks should consult LoC sheets 6/10,
   9/14 and 2/3 directly.*
2. **Declared coverage gaps, rendered as flat fill (236,232,219).** 143.1 Mpx of the
   canvas is flat fill; 141.4 Mpx of it lies outside any sheet footprint. Largest single
   gap: **Avenues D-G x streets 16-18** (canvas x 6317-11964, y 485-4831) — no 1885 sheet
   in the available set covers this ground. Smaller declared gaps east of unit 4, right of
   units 11a/11b, and along the G-H x 18-20 edge. Fill matches adjacent retained paper to
   within 0-5 DN (median 2 DN); no visible step at 100 %.
3. **Sheet 3's top strip (source rows 0-2268, ~1.06 Mpx of ink) is not rendered** —
   the Court House block with its "Offices / Kitchen / Female Prisoners' Rooms"
   annotations, the Avenue G/H/I/J labels on that row and a "20TH ST." repeat. **Equally
   absent from the v2 composite and from the third-party one-page edition**, and not
   duplicated on any other 1885 sheet. Consult LoC sheet 3.
4. **Partial content loss along two avenue corridors that were previously blank fill.**
   The synthetic bands over **Avenue D between 22nd and 23rd** and **Avenue G between
   20th and 23rd** have been replaced with the original covering paper, but the block
   faces immediately adjoining the join are still not carried: the **1303 / 110-142**
   dimension row and the "SEE SHEET No. 6." note at Ave D 22-23, and the
   **152/158/100/1404/104/1405-1408 and 200-210** lot column at Ave G 20-23. Consult
   LoC sheets 6 and 9 (Ave D) and sheets 5 and 6 (Ave G).
5. **Panel-split step of ~84 px at 23rd St** where sheet 11 is split into panels 11a/11b.
   The sheet itself is tilted ~88 px, so this is the floor without shear modelling.
   Legible; lot lines step but do not break; the left arm of the "T" in TREMONT is clipped.
6. **Residual cross-seam jogs of up to ~90 px.** 5-53 px across 22nd St (mean 29 px, the
   best of the three editions at all five crossings), rising to ~83-90 px at the joins in
   item 1, where the measurement is degraded by the blank ground itself. All ≤ 110 px.
7. **"Scale of Feet" graduated bars: 3 of 7 retained.** Complete at **19th St (Ave A-D)**
   and **26th St (Ave D-G)**. At **22nd St (Ave A-D)** the caption is retained but the
   numeral row is cut mid-glyph by the sheet-7/sheet-9 join and the graduated bar is not
   carried — use the 19th or 26th St bar, or the unit-14 marginal bar, for measurement.
   Not carried at all at 20th D-G (replaced by the OCT. 1885 cartouche), 23rd D-G,
   23rd G-I, 25th A-D and Ave A-B x 28th.
8. **"AV. G OR WINNIE OR MENARD E." appears twice between 25th and 27th St**, ~200 px
   apart, because the facing margins of sheets 10 and 11 are both retained (they carry
   "SEE SHEET No.11" and "SEE SHEET No.10" respectively). Both prints are complete and
   legible. The same avenue label is also printed once per adjoining sheet elsewhere along
   Avenues D, G and H — that repetition is original to the atlas.
9. **Avenue H corridor gutter.** The widest ink-free column run through the Ave H corridor
   is ~132 px (v2: 128 px). "AV. H OR WILLIAMS E." runs whole with no gutter through it.
10. **"J. LLOYD 10/28/85" surveyor's signature (sheet 14, bottom right) is absent.** It
    sits across the unit 14 / unit 13 ownership seam. **Also absent from the v2 composite
    and from the third-party edition.** Consult LoC sheet 14.
11. **Retained scan margins, intentionally.** Four **"OCT. 1885 / GALVESTON / TEXAS"**
    cartouches (units 2, 5, 10, 14), sheet numbers 2/5/14, the **"Scale of Feet"**
    graduated bars, **"SEE SHEET No. 3 / 15 / 16 / 17"** cross-references, street headers
    (16TH, 20TH, 28TH ST., "AV. A OR WATER", "AV. J OR E. BROADWAY", "AV. G OR WINNIE OR
    MENARD E."), unit 14's waterworks and coal-shed annotations, the F.H.S. 10.29.85
    surveyor's mark, and three **Library of Congress "Map Division"** ownership stamps
    (units 3, 5, 14). These are original artifacts of the scanned sheets.
12. **Slight per-sheet deskew.** Individual sheets are rotated by up to ~3° relative to the
    raw scans (unit 14 −3.0°, unit 2 +1.0°) to square the street grid. Text and rules are
    resampled once; measured 10-90 % edge rise is 5-11 px, identical to the source sheets,
    with no ringing and no JPEG blocking (blockiness index 0.94-1.03; 1.00 = none).
13. **Paper tone is normalised across sheets** to a common warm tone (B,G,R ≈ 218,231,236;
    R−B 17-19; R > G by ~5 DN) so the twelve sheets read as one document. Per-unit R−G
    spread 2.5 DN (v2: 16.7; third-party edition: 4.6). The source sheets' individual
    casts, including sheet 6's cooler paper, are therefore **not** preserved. Users needing
    colorimetric fidelity to an individual sheet should use the LoC scan.
14. **No clipping and no crushed blacks.** Canvas-wide, **0 pixels have any channel at 255**
    and **0 pixels are pure black** (exact census over all 500,606,512 pixels). The 22
    darkest pixels on the canvas (gray 46-49, at x 747-913 / y 6103-6194) are faithfully
    reproduced printed ink from sheet 2.
15. **Scanner-bed and backing-board artifacts: none.** No pure-black pixel appears anywhere
    on the perimeter (all four sides, all three editions checked); the dark-rim fraction is
    **0.012 %** (v2 0.282 %, third-party edition 0.023 %); long thin dark runs: 0
    (third-party edition: 5). The six rim tiles that read dark are the printed "18TH"
    street label.
16. **A blank band crosses 25th St between Avenues A and C** (~0.83 Mpx), carrying unit
    14's top margin — the "NO. 9" note and the GALVESTON cartouche — over ground that the
    original sheet 9 draws. It also beheads the horizontal "SEE … SHEET No. 11." note at
    25th/Ave G. See item 1 for the named detail affected.
17. **Cosmetic points where a predecessor is fractionally ahead:** Ave H gutter 132 px vs
    v2's 128 px; whole-map tile chroma sd 6.36 vs the third-party edition's 6.23;
    "SEE SHEET No. 4" at 25th/Ave G rotated along the avenue rather than horizontal;
    blockiness at Ave E x 22nd 0.982 vs v2's 1.022 (both ≈ 1.00 = no blocking).

---

VERDICT: FAIL

- **Two of the three content FAILs v4.3 was built to close were never touched.** Site B
  (u9|u14, 25th x Ave B) is **byte-identical to v4.2 over the entire 3600 x 3600 site
  window — 0 changed pixels**; the "Scale of Feet" caption+ruler, "T. W. English Coal
  Yard", "Artificial Stone Wks", "Coal Off."/"SCALES", lots 501-503 and 506-508, the
  1½" V.P. note and the 6" W. PIPE main are still absent while **v2 and "other" both draw
  them**. Site D's Tremont band changed by **9,334 of 750,000 pixels (1.2 %)**;
  "TREMONT OPERA HO.", "IRON COVERED CORNICE", the five-line Babcock annotation and
  blocks 601/602/156-162 remain absent, and **v2 and "other" are both complete**. Round-4
  findings 1-1 and 1-2 stand verbatim.
- **The re-cut h22 7|9 (+190) seam slices the 22nd St scale bar mid-glyph.** Its numeral
  row ("50 / 100 / 150") is cut horizontally through the middle of the glyphs at
  y = 13,862 and the graduated bar is gone, where **v2 and "other" both carry the row
  whole**. This is a new artifact class relative to round 4 — whose seam sweep explicitly
  found that no cut sliced any retained item — and it is the checklist's own stated FAIL
  trigger. Scale-bar retention is 3 of 7, up from 2, but one of the three is mutilated.
- **What v4.3 did fix, it fixed cleanly and I verified all of it.** "22ND ST." is whole
  and single (label-band ink 2,254 → 8,114 px against v2's 8,616, full cap height, the
  10" W. PIPE caption back). Both round-4 synthetic bands are gone — Ave D 22-23
  591,619 → **0** flat px, Ave G 20-23 1,611,780 → **0** flat px — and canvas-wide,
  synthetic fill over claimed ground drops **4.67 → 1.70 Mpx (−64 %)**.
  "AV. G OR WINNIE OR MENARD E." is no longer beheaded. Void area at the five sites is
  down 8 % with no site worse.
- **Everything else regression-swept clean across all six changed cuts.** Pure-black 0 and
  channel-255 0 over all 500,606,512 pixels; long thin dark runs 0 (v2 0, other 5);
  dark rim 0.0120 % (v2 0.282 %, other 0.0235 %); zero pure-black perimeter pixels on all
  four sides and the cleanest perimeter of the three on three of them; unit-14 cartouche
  and unit-13's SEE SHEET row whole; Ave E x 22nd, the 26th/27th Ave D jogs and the
  11a|11b panel step byte-identical to v4.2; all thirteen corridor labels single and
  whole; no flat-band box got worse; no label newly doubled or sliced.
- **What would make this a PASS-WITH-WARNINGS:** carry the 25th/Ave B block (sheet 9's
  bottom-right quadrant, including its Scale of Feet bar) and the 23rd/Ave D Tremont
  Opera block (sheet 6 or 10) into the composite, and move the h22 7|9 cut clear of the
  22nd St scale-bar numerals — roughly 60 px further down, or back to v4.2's line with
  the owner window kept wide. Nothing else in this report blocks packaging; the
  disclosure list in §8 is complete and ready for the production report as written.
