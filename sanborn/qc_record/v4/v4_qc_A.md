# v4 QC round 3 (final gate) — Reviewer A: SEAMS, LABELS, CORRIDORS

Artifact: `build/1885/galveston_1885_composite.tif` (18188 x 27524, PAD 742)
References: `compare/v2_composite.tif` (PAD 464), `compare/other_onepage.jpg`, `build/1885/v3_raw.dat` (v3.2)
Evidence: `build/1885/v4_qc_evidence_A/` — crops, JSON and a `LOG_*.txt` for every run.
Helpers (new this round): `qcA4_lib.py`, `qcA4_mk.py`, `qcA4_black.py`, `qcA4_19{th,b,c,d}.py`,
`qcA4_holes.py`, `qcA4_fill.py`, `qcA4_flatdiff.py`, `qcA4_labels.py`, `qcA4_jog.py`, `qcA4_jog2.py`,
`qcA4_dupcensus.py`, `qcA4_newflat.py`, `qcA4_h6.py`, `qcA4_h6b.py`, `qcA4_25g.py`, `qcA4_bands.py`,
`qcA4_blackloc.py`, `qcA4_tremont.py`, `qcA4_sweep.py`, `qcA4_other.py`, `qcA4_oth2.py`.
Nothing was modified.

## Method notes

1. **Every v2 comparison is locally re-aligned** (`qcA4_lib.locoff`, 420–520 px template, ±260–380
   search), score quoted. v4-vs-v2 residuals run **-287 to +133 px** and vary within a unit; a fixed
   +278 offset invents content loss. Round-2 reviewer 2's warning holds for v4 too.
2. **All findings below were re-read from the delivered TIF**, not only from the memmap
   (`LOG_tifverify.txt`: `tifffile` direct read of the H6 band reproduces it byte-identically).
3. The 19-corridor tile sweep (`LOG_sweep.txt`) is reported but **not used as a headline number**:
   a single rigid offset per 600-px tile cannot absorb local shear, so it reports "41 % lost" for
   H1/19th while v4 actually carries **more** ink there than v2 (196,976 vs 191,146). Every claim
   below rests on either a synthetic-fill measurement (unambiguous) or a 100 % visual pair.

---

## 1. 19th corridor (A–D) — **PASS, and it is the best fix in this build**

Round 2's FAIL item 1 is fully cleared. `110/111_19TH_label_100_*.png`, `112_19th_pipe_band_v4.png`,
`120_bakeho_v4.png`, `LOG_19th.txt`.

| measure | v3.2 (round 2) | v2 | **v4** |
|---|---|---|---|
| "19TH ST." label window, v2 ink unmatched in build | 24,278 px (**86 %**) | — | **2,351 px (8.4 %)** |
| ink in that window | 6,872 | 28,048 | **28,274** |
| round-2 hole band y 7130–7245: flat fraction / ink | fill, 0 ink | — | **0.028 / 36,626 px** |
| H1_19th solid black, h / v runs | 167 / 122 | 4,490 / 620 | **191 / 310** |
| H1_19th backing/flat-bright rows (>30 %) | 0 | 0 | **0** |

- **"19TH ST." is complete at 100 %** — every glyph whole, indistinguishable from v2.
- **The 8" W. PIPE dashed main runs the full corridor.** Segment-wise (`LOG_19th.txt`, 6 segments,
  locally aligned): v4 ink ≥ v2 ink in 5 of 6; the ink-free column gaps in v4 coincide with v2's
  (e.g. v4 (440,222)/(717,319)/(1039,401) vs v2 (295,234)/(576,289)/(867,393)) — they are the
  printed dash gaps, not holes.
- **No solid black bar.** The 1,160-px rule is still gone.
- **No backing band.** Zero flat-bright rows; the only flat region inside H1 is a 161 x 860 px
  sliver on the Avenue D gutter line, not a band across the street.
- **Sheet 7's Bake Ho./OVENS./Bakery. block tops are intact**, with the top wall, "Sleep'g Rms",
  "No opgs", the 272/274/276 dimensions and the sheet's "Scale of Feet" ruler.

Solid-black run counts, all 19 corridors, are in `010_blackruns_v4.json`. **No new black rules
exist anywhere.** Every component ≥ 600 px was located and inspected (`LOG_blackloc.txt`,
`380_black_*.png`): they are printed block walls (V1 @ 6295,5033 — the heavy wall above
"4. FRAME DW'GS.") and the retained **OCT. 1885 / GALVESTON / TEXAS cartouches** at Avenue D/22nd
and 25th/Ave A–D. Nothing scanner-edge shaped.

## 2. 25th / Avenue G — **PASS on both stated criteria; one new fill band**

`200/203/207_25thG_*.png`, `350/351_25thG_band_*.png`, `353/354_AvG_vertnote_*_rot.png`, `LOG_25g.txt`.

- **Exactly ONE "25TH ST. OR BATH AV." print.** Confirmed visually at 100 % and by the display-type
  census (the two blocks the detector finds at (12400,20288) 528x88 and (12980,20272) 508x84 are
  the two word-groups of the *same* line, contiguous in x with a 52-px gap — not two prints).
- **The black rule is gone.** Repeating round 2's window count: **0 px** solid black
  (h and v) in the 3000 x 500 window at x 11439–14439, y 19900–20400, **down from 14,530 px**.
  v2's same box carries 4 raw sub-70 px. Better than v2.
- **SEE SHEET cross-references — stated plainly:**
  - Sheet 4's reciprocal note (**"SEE SHEET No. 11."**, expected) — **present but mutilated**: its
    top is clipped by the new fill band, leaving only glyph bottoms (`355_SEESHEET_horiz_v4_100.png`).
    Effectively illegible.
  - Sheet 11's **"SEE … No.4."** running up Avenue G — **SURVIVES**, and matches v2 glyph for glyph
    (`353` vs `354`, aligned +6,-32 at r 0.78). This is a **restoration** — round 2 recorded it lost
    in v3.2. Reported, not failed, per the brief.
- **NEW defect:** a synthetic flat band, **x 12157–13699 (1,543 px) x y 20014–20124 (111 rows)**,
  flat fraction 1.00, uniform BGR 219/232/236, **zero ink**. It covers **20,293 px** of v2 content
  (align r 0.46). Much of what it removes is v2's own duplicated label print, but it also blanks a
  row of building cells and beheads the SEE SHEET note.

## 3. Doubled labels — **de-duplication PASSES; the disclosed TREMONT step is 2.2x worse than described**

`230_H2_20th_DG_v4.png`, `232_H8_26th_DG_v4.png`, `234_H5_23rd_GI_v4.png`,
`390_TREMONT_v4_100.png`, `LOG_tremont.txt`, `LOG_tremont2.txt`.

- **20TH ST. (D–G): single.** One clean, complete print. No pair anywhere near it in the census.
- **26TH ST. (D–G): single.** Complete; the sheet's "Scale of Feet" ruler survives beside it.
- **23rd G–I: sheet 5's duplicate copy is gone.** The phrase now reads once, as "23RD OR" on the
  11a panel and "TREMONT" on the 11b panel.
- **But the disclosed step is 227 px, not "~100 px".** Ink-row extents, locally measured:
  "23RD OR" y 15808–15884, "TREMONT" y 16035–16096 → **step +227 px (tops) / +212 px (bottoms)**.
  The panel edge is a hard tone discontinuity at x ≈ 13594–13655 (mean-gray step 16.7) and it
  **clips the left arm of the "T" in TREMONT**.
  - **At 100 % it does not read as one street name.** It reads as two unrelated labels on two
    different rows, separated by a visible panel join — the eye has to be told they belong together.
  - **v2 carries the phrase as a single unbroken 1,476 x 92 px line** — no step at all.
  - **"other" could not be registered at this site** (best match 0.20 across ±1100 px and 5 scales),
    so no comparison is claimed there.
  Per the brief this is "note if worse than described" — it is, by 2.2x. Not counted toward the FAIL.

## 4. Full label inventory

`bigtext_v4.json`, `401_dupcensus.json`, `LOG_dupcensus.txt`.

Display-type blocks: **v4 215, v2 220** (v3.2 was 236).

Near-duplicate census, round-2 filter (same orientation, centre distance ≤ 800, w and h within 45 %,
min 150 x 50 px). The filter is validated by **reproducing round 2's v2 count exactly**:

| | v2 | v3.2 (round 2) | **v4** |
|---|---|---|---|
| near-duplicate pairs | 13 | 18 | **19** |

The count did not improve, but **the composition did**: not one v4 pair falls at 20th D–G, 26th D–G
or 25th G–H. The 23rd pair is the stepped halves of §3, not a duplicate. The rest are legitimately
adjacent original print (sheet 14's three-line cartouche at 25th/Ave A–B, a column of repeated
wharf-shed labels at Ave B–C between 27th and 28th, block-number rows).

**Round-2 pass list, re-verified:**

| label | round 2 | **v4** | evidence |
|---|---|---|---|
| 22ND ST. (H3 A–D) | complete, single | **DESTROYED — see §6** | `430/431/432_22ND_wide_*.png` |
| AV. G OR WINNIE OR MENARD E. | pass | **pass** — complete, single, whole | `254b_AvG_E_v4_rot.png` |
| AV. G OR WINNIE OR MENARD W. | pass | **pass** — complete, single, whole | `441_AvG_W_v4_rot.png` |
| AV. D OR MARKET E. NO.6. | pass | **pass** — complete, with its SEE SHEET NO.6. | `252_AvD_MARKET_v4_rot.png` |
| AV. H OR WILLIAMS E. | pass (best fix) | **pass** — still whole on continuous paper | `253_AvH_WILLIAMS_v4_rot.png` |
| 26TH ST. (nr Ave G) | complete, single | **pass** | `442_26TH_nrAvG_v4.png` |
| 25TH ST. OR BATH AV. (H6 A–D) | complete, single | **MUTILATED — see §6** | `413/414_H6_25TH_label_*.png` |

## 5. 27th St jog at Avenue D — **FAIL (over the disclosed 130 px limit, and worse than v3.2)**

Round-1/2's exact method (median-blurred ink row profile, cross-correlated left vs right of the
Avenue D cut, windows 250–1400 px). `qcA4_jog.py`, `LOG_jog.txt`, `500_jog27D_{v4,v2}.png`.

| half-height | **v4** | v3.2 (round 2) | v3 | v2 |
|---|---|---|---|---|
| 300 | **+184 px** (r 0.67) | +161 | — | +107 (r 0.81) |
| 400 | **+179 px** (r 0.56) | +164 | +112 | +107 (r 0.46) |
| 500 | **+177 px** (r 0.48) | +165 | — | +135 (r 0.42) |

The method is validated by **reproducing round 1's v2 value of +107 at two of three half-heights**.
Independent check (`qcA4_jog2.py`, roadway-edge peak tracking, no correlation): v4 right-minus-left
edge deltas **-85 / -213 px**, v2 **-108 / -136 px**.

**v4 is +177 to +184 px — 36 to 41 % over the 130 px limit, and worse than v3.2's +164.** The jog is
plainly visible at 100 %: the 601/602/603/604 block row and its D.H. east of Avenue D sit ~180 px
above their west-side counterparts, and 27th's north kerb line does not continue across the avenue.

## 6. Whole-corridor content sweep — **FAIL: three new holes and one destroyed street label**

Alignment-free synthetic-fill map (`qcA4_fill.py`/`qcA4_flatdiff.py`, 9x9 local max-min ≤ 1: real
paper is never flat), plus per-corridor flat-component geometry (`qcA4_bands.py`, `LOG_bands.txt`,
`LOG_bandwidth.txt`) and 100 % visual pairs.

**Flat-fill inventory of all 19 corridors.** Two *horizontal* bands exist; the rest are vertical
gutters (median horizontal run = true width):

| region | geometry | class |
|---|---|---|
| **H6 25th, Ave A–D** | **5,881 px wide x 364–446 rows, y 20114–20477** | **NEW — full-corridor blank band** |
| 25th / Ave G | 1,543 x 111 rows, y 20014–20124 | NEW — §2 |
| V11 Avenue H | **53 px** | disclosed gutter, in spec |
| V6/H8 Avenue D 25th–27th | 182–273 px | NEW — see (b) |
| V1/H1 Avenue D 18th–19th | 161 px | round-2's known "v4 keeps more" case; 0 v2 ink lost when aligned |
| V5/V3 Avenue D | 26 / 41 px | benign slivers |

### (a) H6, 25th St across Avenue A–D — the headline defect

`340/341_H6_25th_AD_*_strip.png`, `344/345_H6_band_*_100_w*.png`, `346_H6_band_FROM_TIF_100.png`,
`600_other_H6_25th_AveA-D.png`, `LOG_h6.txt`, `LOG_h6b.txt`, `LOG_tifverify.txt`.

- **Every one of the 5,881 columns from Avenue A to Avenue D has ≥ 364 flat rows** (median 364,
  max 446). Flat fraction 1.00, uniform BGR 219/232/236 — synthetic gap fill, not paper.
  2,189,434 flat px inside the corridor box. Flat-bright rows >30 %: **v4 364, v2 0**.
- Re-read straight from the delivered TIF: 364 fully-flat rows, y 20114–20477. Not a memmap artifact.
- **What it erases** (all present and clean in v2 at 100 %): block faces 501/502/503/504/505/72/1301,
  "D.G. W.HO.", "Coal Off.", "SCALES", "T. W. ENGLISH COAL Y'D", "Artificial Stone Wks", the
  70'/20'/80' dimensions, D.H. hydrants — **and the complete "Scale of Feet" caption *and* ruler**.
- **It beheads the street label.** "25TH ST. OR BATH AV." loses its top: **"25TH" is destroyed**,
  "ST." and "BATH" survive only as clipped lower halves. Round 2 certified this corridor CLEAN
  ("one complete 25TH ST. OR BATH AV., no bar, no band").
- **Worse than BOTH references at the same site.** v2 is complete. The user's **"other" mosaic is
  also complete** at this site (match r 0.39, side-by-side in `600_other_H6_25th_AveA-D.png`): it
  carries every building, the dimensions and the full label with no band.
- **New artifact class:** round 2 established that v3.2 had **zero** backing/flat bands in all 19
  corridors. v4 reintroduces them, at 16x the width of anything v2 ever had here.

### (b) Avenue D, 25th–26th — "AV. D OR MARKET W." and "SEE SHEET NO.10" deleted

`460_V6_AvD_worsttile.png`, `472/473_AvD_W_label_*_rot.png`, `LOG_avdw.txt`.

A **273-px-wide flat vertical strip** replaces the label column. v2 carries, in bold,
"AV. D OR MARKET W." plus the italic "SEE SHEET" and "SEE SHEET NO.10" notes; v4 has blank fill.
Template control (search the v2 template inside v2) = **1.00**; best score anywhere in v4's entire
Avenue D column (x 5300–7400, y 15000–27000) = **0.38**; "SEE SHEET NO.10" = **0.46**. The label is
not merely displaced — it is not in the composite at this site.

### (c) 23rd, Ave D–G — the Tremont Opera House annotation deleted

`460_H4_23rd_worsttile.png`, `470/471/474_TremontOpera_*.png`, `LOG_tremontopera.txt`.

v2 carries, in the 23rd corridor: "IRON COVERED CORNICE", block numbers 601/602/156/158/160,
**"TREMONT OPERA H[OUSE]"** and its five-line fire annotation ("ABOVE 1ST OPEN FROM 2ND TO ROOF. /
4 BABCOCK FIRE EXTINGUISHERS. 2" … / PIPE FROM TANK UNDER ROOF TO S… / WITH 1¼" HOSE CONNECTED IN
FLIES. / IN STAGE. 200' HOSE."). In v4 the whole area is blank roadway paper — only the "80'"
dimension remains. Template of the words "TREMONT OPERA H": control inside v2 = **1.00**; best match
anywhere in v4's west half (x 400–12000, y 13000–19000) = **0.47**. Absent.

### (d) 22ND ST. at Avenue A–D — the round-2 19th failure, relocated

`430_22ND_wide_v4.png` vs `431_22ND_wide_v2.png` vs `432_22ND_wide_v32.png`,
`440_other_22ND.png`, `LOG_22nd.txt`, `LOG_22nd_v32.txt`.

The top ~60 % of every glyph of "22ND ST." is replaced by the covering sheet's **blank roadway
paper** (0 flat px in the window — it is real paper, exactly the v3.2/19th mechanism, not fill).
The **10" W. PIPE dashed main and its caption go with it**.

| glyph-band ink (x 2600–5400, y 13580–13800) | ink px |
|---|---|
| v3.2 | 34,887 |
| v2 | 24,747 |
| **v4** | **11,708** |
| v2 ink with no v4 counterpart (aligned +76,+21 r 0.56) | **19,764 (80 %)** |

**Worse than v2, worse than v3.2, and worse than "other"** — the "other" mosaic (match r 0.54,
`440_other_22ND.png`) carries "22ND ST." complete with the pipe main. Round 2 listed 22ND ST. as
"complete, single". This is a straight regression on a previously-passing label.

### (e) Scale bars

- Round 2's **two known dropped rulers have NOT returned**: H2 20th (`372_H2_20th_wide_v4.png` —
  blank where v2 has the ruler; **the "Scale of Feet" caption is now gone too**, where round 2
  recorded the caption surviving) and H4 23rd (`372_H4_23rd_wide_v4.png` — replaced by the
  OCT. 1885 GALVESTON TEXAS cartouche).
- **A third ruler is now dropped:** the "Scale of Feet" caption + ruler at 25th / Avenue A–D,
  destroyed by the band in (a). Round 2 knew of two; v4 has three.

## 7. Target intersection Avenue E x 22nd — **PASS, unchanged**

`420_target_AvE22_v4_v2.png`, `LOG_passlist.txt`. Locally aligned (-20,-14) at r 0.66 over a
2200 x 1600 window: v4 ink **368,385** vs v2 **377,048**; the residual is symmetric (95,075 v2-only
vs 92,018 v4-only) — registration residual across a sheared window, not loss. **0 px solid black,
0 px flat fill.** "22ND", "AV. E OR", the 10" W. Pipe main, both D. Hyd. markers, "Texas Lamp &
Oil Co.", "Pianos & Organs", block faces and colours are all present and continuous in both.

---

## What would clear the FAIL

1. Close the 9|14 gap at 25th / Avenue A–D. A 5,881 x 364–446 px synthetic band across a whole
   corridor is the single worst artifact in any build reviewed so far; it must become zero flat rows,
   as v3.2 achieved in all 19 corridors.
2. Re-cut 22nd (A–D) so "22ND ST." and the 10" W. PIPE main survive — the same fix that worked at
   19th, applied one corridor south.
3. Restore the Tremont Opera House annotation block at 23rd (D–G) and "AV. D OR MARKET W." +
   "SEE SHEET NO.10" at Avenue D, 25th–26th.
4. Bring the 27th-at-Avenue-D jog under 130 px (it has now grown in two consecutive builds:
   +112 → +164 → +180).
5. Keep §1, §2 and §4's pass list exactly as they are — the 19th corridor, the 25th/Ave G black rule,
   the de-duplication of 20th/23rd/26th and the restored "SEE … No.4." are genuine wins over both v2
   and v3.2. Optionally reduce the 227-px TREMONT step, which is 2.2x its disclosed size.

---

VERDICT: FAIL

- **A 5,881 x 364–446 px synthetic blank band now crosses the entire 25th St corridor from Avenue A
  to Avenue D** (y 20114–20477; all 5,881 columns flat, BGR 219/232/236; verified by direct TIF
  read). It erases blocks 501–510/72/1301, "D.G. W.HO.", "T. W. ENGLISH COAL Y'D", "Artificial Stone
  Wks", a full "Scale of Feet" caption+ruler, and it beheads "25TH ST. OR BATH AV." so that "25TH"
  is gone. **v2 and the user's "other" mosaic are both complete at this exact site**, and v3.2 had
  zero flat bands in all 19 corridors — this is worse than both references and a new artifact class.
- **"22ND ST." (Ave A–D) is destroyed the same way "19TH ST." was in v3.2** — top ~60 % of every
  glyph plus the 10" W. PIPE main replaced by the covering sheet's blank roadway. Glyph-band ink
  11,708 px vs v3.2's 34,887 and v2's 24,747; 80 % of v2's ink has no counterpart. **"other" carries
  it complete.** Round 2 had passed this label. The fix moved the defect one corridor south.
- **Two further deletions:** the "TREMONT OPERA H[OUSE]" name with its five-line Babcock fire
  annotation, "IRON COVERED CORNICE" and blocks 601/602/156/158/160 at 23rd (D–G) are absent from
  v4 (template control 1.00, best in v4 0.47); and "AV. D OR MARKET W." with "SEE SHEET NO.10" at
  Avenue D 25th–26th is replaced by a 273-px flat strip (control 1.00, best in v4 0.38). A third
  "Scale of Feet" ruler is dropped, on top of round 2's known two.
- **The 27th-at-Avenue-D jog grew again: +177 to +184 px** (v3 +112, v3.2 +164, v2 +107 — reproduced,
  validating the method). That is 36–41 % over the brief's own explicit 130 px fail threshold.
- **Round 2's other FAIL items are genuinely cleared, and cleanly.** 19th: "19TH ST." complete at
  100 %, the 8" W. PIPE main continuous, 0 backing rows, 191/310 px solid black, Bake Ho./OVENS.
  block tops intact. 25th/Ave G: **0 px solid black in the round-2 window, down from 14,530**,
  exactly ONE "25TH ST. OR BATH AV.", and sheet 11's "SEE … No.4." restored. 20th, 26th and 23rd
  G–I are single again (the 23rd step is 227 px, 2.2x its disclosed ~100 px, but legible and
  disclosed-class). Avenue H OR WILLIAMS E. still whole; Avenue E x 22nd unchanged.
