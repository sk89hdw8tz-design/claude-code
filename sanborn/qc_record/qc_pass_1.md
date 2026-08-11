# QC Pass 1 — Geometry review, 1885 Galveston Sanborn composite
## REVISION 8 (independent, adversarial)

Artifact under review: `build/1885/galveston_1885_composite.tif`
(26968 rows x 17632 cols x 3, LZW, mtime 2026-08-07 19:31).

**Read source.** `composite_raw.dat` has been deleted as recommended in rev 7. This reviewer
decoded the delivered TIF once with `tifffile` (photometric = RGB, verified) and dumped it to
`build/1885/qc1r8/comp8.dat`; **every** measurement below comes from that buffer, i.e. from the
delivered file. That 1.4 GB scratch buffer was deleted after the review so as not to repeat rev
7's stale-`.dat` hazard; `qc1r8/lib8.py` regenerates it in ~30 s
(`tifffile.TiffFile(...).pages[0].asarray()` → memmap, shape 26968 x 17632 x 3, RGB). No rev-7 build exists on disk any more, so rev-7 numbers below are quoted from
the archived rev-7 report rather than re-derived; the estimators are byte-for-byte the same code
paths, and 14 control seams reproduce rev-7's values to within 1–3 px (table in Part A(2)), which
establishes that the comparison is sound.

All rev-8 evidence lives in `build/1885/qc1r8/`. The rev-7 report is archived unmodified as
`build/1885/qc_pass_1_rev7_superseded.md`.

---

## Grid — the brief's table is now CURRENT (rev-7's complaint is resolved)

The refreshed brief table matches `registration.json`'s `consensus_av` / `consensus_st` exactly,
and all twelve units' `knots.xkg` / `knots.ykg` key to those same values. Canvas position =
table + 464 px pad:

| | A | B | C | D | E | F | G | H | I | J |
|---|---|---|---|---|---|---|---|---|---|---|
| canvas x | 488 | 2307 | 4184 | 6117 | 7952 | 9799 | 11665 | 13480 | 15307 | 17022 |

| street | 16 | 17 | 18 | 19 | 20 | 21 | 22 | 23 | 24 | 25 | 26 | 27 | 28 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| canvas y | 493 | 2545 | 4699 | 6906 | 9056 | 11195 | 13351 | 15639 | 17836 | 19986 | 22372 | 24522 | 26585 |

Verified unit-by-unit: units 2/7/9/14 (A–D), 3/6/10/13 (D–G), 4/5/11a/11b (G–J) all reference
identical knot values. No stale-table hazard this revision. (Grid choice is in any case
irrelevant to a *step*, which is a difference of two offsets against the same nominal.)

## Estimators (three, deliberately redundant) and the measured noise floor

1. **Frontage-line pair** (`qc1r8/lib8.py:step_h/step_v`) — primary. Column (or row) ink-fraction
   over an 800 px band; a block frontage is a run with ink fraction ≥ 0.55. Report the frontage
   immediately either side of the nominal line; the step is the change in their midpoint across
   the seam. Text-robust and closest to what the eye sees.
2. **Whole-span profile cross-correlation** (`lib8.py:xcorr_h`) — smoothed ink-density profile of
   a 1000 px band above vs below the seam, best lag by normalised correlation, with the
   correlation *at zero lag* reported alongside so a weak/multimodal peak can be discounted.
3. **Matched corridor tracker** (`lib8.py:track_v/track_h`, `mf_h/mf_v`) — median over 17 × 80 px
   sub-bands per side; a third opinion that never sees the frontage detector's threshold.

**Noise floor, re-measured on this build.** Estimator 1 at 18 pure interiors (inside a single
sheet, where misregistration is impossible by construction) gives |step| =
0, 0.5, 0.5, 1, 1.5, 2, 2.5, 2.5, 13.5, 17.5, 20, 40.5, 41.5, 51.5, 53, 76.5, 81.5, 102.5
(median 15.5, p75 49, p90 78, max 102.5). Real Sanborn lot lines are not perfectly collinear
across a street, so **±80 px is the physical resolution limit of this artifact** and everything
is graded against it. The brief's "~40 px" is below that limit; it is reported against but not
used as the pass line.

---

# PART A — The rev-8 correction and the rev-7 regression checks

## (1) 20th D-G, units 3 | 6 — **PASS (the sign flip fixed it)**

Rev 7 applied unit 3's 138 px manual knot delta with the wrong sign. Rev 8 flipped it
(`manual_knot_deltas.json` unit 3 `v` = +138 on all four avenue knots, was −138): a **net
+276 px** change, moving unit 3's content **west**.

**Frontage-pair step (estimator 1), same code as rev 7:**

| crossing | rev 7 | rev 8 | change | verdict |
|---|---|---|---|---|
| Avenue E | dL −231, dR −254, **dCtr −242** | dL **+27**, dR **+23**, **dCtr +25** | **+267** | PASS |
| Avenue F | dL −289, dR −320, **dCtr −305** | dL **−11**, dR **−38**, **dCtr −24.5** | **+280.5** | PASS |

The +267 / +280.5 change matches the +276 px knot flip to within 9 px on one crossing and 5 px on
the other — the correction landed with the intended sign *and* the intended magnitude.

Raw frontages (offset from nominal): at Avenue E, above the seam **−259 / +131**, below
**−232 / +154** (corridor 390 → 386 px). At Avenue F, above **−209 / +211**, below **−220 / +173**
(corridor 420 → 393 px). Corridor width is preserved on both sides.

**Corroboration, estimator 2 (cross-correlation).** The rev-7 signature was a −218 px lag with
the profiles *anti*-correlated at zero lag (r = −0.13 / −0.19). Rev 8:

| window | best lag | r at peak | r at lag 0 |
|---|---|---|---|
| full D-G span | **−34** | 0.466 | **+0.429** |
| Avenue E window | **−28** | 0.611 | **+0.449** |
| Avenue F window | **+30** | 0.424 | **+0.243** |
| control: INT 21st D-G (interior) | 0 | 0.419 | +0.419 |
| control: INT 22nd D-G (interior) | +4 | 0.418 | +0.413 |
| control: 23rd D-G (known-good seam) | −20 | 0.452 | +0.423 |

The zero-lag correlation is now strongly positive and within a few hundredths of the peak — the
same signature the two interior controls produce. The anti-correlation is gone.

**Corroboration, estimator 3 (corridor tracker):** Avenue E **+6.5**, Avenue F **−10.5**.

**Three independent estimators agree the residual is between −35 and +30 px** — inside ±80 px by
a factor of ~2.5, and inside the brief's own ~40 px nominal tolerance.

**Street-corridor width across the seam** (block frontage N to block frontage S), the metric that
would expose a bodily translation as a distortion:

| column | D-E | E-F | F-G |
|---|---|---|---|
| **20th (SEAM 3\|6)** | **448** | **433** | 271* |
| 19th (interior) | 460 | 459 | 456 |
| 21st (interior) | 430 | 431 | 441 |
| 22nd (interior) | 453 | 458 | 458 |

\* F-G: the detector locked on an inner lot line; the corridor is open and continuous there in
the crop. Seam corridor widths are indistinguishable from interiors.

**Visible at native resolution:** `qc1r8/a8_20th_avF.png` — the Avenue F corridor's west frontage
now lands at crop x ≈ 545 above the seam and x ≈ 530 below (rev 7: 690 vs 415), and the two `70'`
street-width callouts sit within ~10 px of the same x. `qc1r8/a8_20th_avE.png` shows the U.S. Post
Office block and the opposing 657–664 / 220–230 address runs meeting cleanly.
`qc1r8/a8_20th_DG_wide.png` shows the whole seam: block numbers 499/500, 439/440, 379/380 stack in
straight columns and both avenue corridors run through unbroken.

**PASS.**

## (2) No regressions from the unit-3 shift — **PASS**

Every rev-7 control re-measured with the identical estimator. Unit 3's delta is x-only and
confined to D-G × 18-20, so anything moving elsewhere would indicate a build-wide problem.

| control | rev 7 | rev 8 | Δ |
|---|---|---|---|
| 26th D-G @ AV F (10\|13) | +37 | **+37.0** | 0 |
| 23rd D-G @ AV E (6\|10) | −22 | **−22.5** | 0.5 |
| 23rd D-G @ AV F (6\|10) | +80 | **+79.0** | 1 |
| 22nd A-D @ AV C (7\|9) | −46 | **−46.0** | 0 |
| 25th A-D @ AV B (9\|14) | +84 | **+85.0** | 1 |
| 19th A-D @ AV C (2\|7) | +8 | **+9.0** | 1 |
| AV D @ 21st (7\|6) | −80 | **−79.0** | 1 |
| AV D @ 27th (14\|13) | −124 | **−123.5** | 0.5 |
| AV G @ 22nd (6\|5) | −6 | **−3.5** | 2.5 |
| AV G @ 27th (13\|4) | +8 | **+8.5** | 0.5 |
| AV H @ 24th (11a\|11b) | −146 | **−145.0** | 1 |
| INT 21st D-G @ AV E | +76 | **+76.5** | 0.5 |
| INT 22nd D-G @ AV F | −2 | **−1.5** | 0.5 |
| INT AV B @ 21st | +13.5 | **+13.5** | 0 |

**All fourteen reproduce to within 2.5 px.** Nothing outside unit 3 moved. Two crossings not in
rev 7's table: 22nd A-D @ AV B −65 (rev 7 reported −87 by a different estimator) and 25th A-D
@ AV C +25 — both unchanged in character.

**Sub-item detail on the specific rev-7 PASSes named in the assignment:**

* **26th D-G (10\|13), rev 7 +26/+37** — Avenue F reproduces exactly at **+37** (raw frontages
  above −274/+120, below −240/+160; corridor 394 → 400 px). Avenue E is not resolvable by the
  frontage pair on either build (unit 13's west frontage there falls outside the search window;
  rev 7 reported only its dR = +26). Estimator 3 gives −118/−61 at Avenues E/F, which is the
  known one-sided-frontage effect rev 7 already documented at Avenue E; the frontage pair and the
  crop are the authority. `qc1r8/a8_26th_avF.png` shows the 605/606 and 629/630/1206 address runs
  and both `70'` callouts continuing across the seam. **PASS.**
* **Avenue H 23-24 (11a\|11b)** — see (3) below. **PASS with the 69 px gutter WARN, unchanged.**
* **23rd G-H (5\|11a), rev 7 +73** — the frontage pair is degenerate on this build too (unit 11a's
  retained panel-frame rule is detected in place of its block frontage: raw above
  −883/−248/+125/+803, below −883/−212/−196). Estimator 3 gives **−7.8**; the crop
  `qc1r8/a8_23rd_GH.png` shows an open, continuous corridor. Nothing suggests the +73 reading
  degraded. **PASS.**
* **19th / 22nd / 25th seams** — reproduce (table above); see also the new finding at 19th A-D in
  Item 4. **PASS on geometry.**
* **Coverage mask** — **changed**; see Item 5. A second uncovered component has appeared, caused
  by this fix. It is the one genuine cost of rev 8.

## (3) Avenue H 23-24, units 11a | 11b — **PASS, 69 px gutter carried as WARN (unchanged)**

* **Exactly one "AV. H OR WILLIAMS E." legend.** `qc1r8/a8_avH_label.png` (native, x 13100-13860,
  y 17100-17900) shows "AV. H OR WI…" set once, at one type size, glyphs complete and unclipped.
  `qc1r8/a8_avH_corridor.png` shows the full 23rd→24th corridor with a single legend.
* **No duplicated content strip.** Unit 11a's `1401`, `1402`, `1402½`, `1402⅓`, `BAKE HO.`,
  `OVEN`, `64½`, `62`, `60`, `170` each appear once; unit 11b's `1403` / `1404` / `59½` / `55` /
  `59` block appears once. The rev-6 duplication remains eliminated.
* **The 69 px paper gutter is still present and unchanged**: coverage-mask component **area
  236,931 px, bbox x 13427-13496, y 15930-19825** — bit-identical extent to rev 7. Tone
  (216, 202, 176) against paper (236, 230, 219). It lies wholly inside the street corridor
  (corridor frontages at −185 / +221; gutter −53 / +15) and destroys no block content; the legend
  glyphs begin at +16, immediately east of it, and are complete.
* At 69 px it still exceeds the disclosure's "thin (< 40 px) paper strips" wording. **WARN**, on
  the disclosure's numeric terms only.

## (4) Unit 3's other boundaries — **PASS (18th and Avenue D), WARN (Avenue G, see Item 5)**

Because the fix is a bodily 276 px x-translation of one unit, its *other* three edges are the
place a mis-sized correction would show. Direct test: measure the frontage x of each avenue
corridor in y-bands that lie wholly inside one unit, then compare unit 3's bands against unit 6's.

| avenue | frontage | unit 3 (18-19, 19-20) | unit 6 (20-21, 21-22, 22-23) | step |
|---|---|---|---|---|
| D | west (from units 2/7) | −181 | −181 | **0.0** |
| D | east (from unit 3 / unit 6) | +180 | +142 | **−38.0** |
| E | west | −255.5 | −225 | **+30.5** |
| E | east | +136 | +153 | **+17.0** |
| F | west | −200.5 | −220 | **−19.5** |
| F | east | +216 | +170 | **−46.0** |
| G | either | *no line detected* | −151 / +200 | see Item 5 |

Unit 3 now agrees with unit 6 to within **−46 … +31 px at every shared avenue**, measured
independently of the 20th-Street seam. This is the strongest single confirmation that the fix is
correct in magnitude and not merely correct at the two crossings that were used to derive it.

* **Avenue D seam vs units 2/7 — no regression.** Row-frontage step at 19th (units 2/7 west,
  unit 3 east): **+80.0** by estimator 1, **+72.5** by estimator 3 — at the top of the ±80 band,
  where it also sat before (the delta is x-only, so a *y*-step at a vertical seam cannot have been
  caused by it). Corridor widths 325 / 461 px, healthy. The Avenue D corridor tracked continuously
  from street 17 to street 22 (`qc1r8/m3.py` output) shows no discontinuity entering or leaving
  unit 3's band. Crop `qc1r8/a8_aveD_18_20.png`.
* **18th D-G faces the disclosed D-G × 16-18 gap.** `qc1r8/a8_18th_DG.png`: unit 3's content
  begins at y ≈ 4526, 173 px *above* the 18th line, with a clean straight rim edge, no wedge and
  no white rule; flat disclosed paper above. The "18TH" legend appears once. **PASS** (rim edge
  facing a disclosed gap, uncorrected as per standing context).
* **23rd D-G (units 6\|10)** — reproduces rev 7 exactly (−22.5 / +79.0). `qc1r8/a8_23rd_DG_avF.png`
  shows the corridor open, both `70'` callouts and the 605/606/258 and 255/257/259 address runs
  continuing. **PASS.**

---

# PART B — Brief checklist, items 1-7

## Item 1 — Fitted scales within ±1 % → **PASS-WITH-WARNINGS**

Re-read from `registration.json` (unchanged from rev 7; the manual delta is a knot translation and
does not touch the fits):

| unit | sx | dev | sy | dev | grade |
|---|---|---|---|---|---|
| 2 | 0.98736 | −1.26 % | 1.00153 | +0.15 % | WARN (sx) |
| 3 | 1.00731 | +0.73 % | 1.00000 | 0.00 % | OK |
| 4 | 1.00000 | 0.00 % | 1.00701 | +0.70 % | OK |
| 5 | 1.00317 | +0.32 % | 1.00039 | +0.04 % | OK |
| 6 | 0.99987 | −0.01 % | 0.98957 | −1.04 % | WARN (sy) |
| 7 | 0.98446 | −1.55 % | 0.98789 | −1.21 % | WARN (both) |
| 9 | 0.98348 | **−1.65 %** | 0.98934 | −1.07 % | WARN (both) |
| 10 | 0.99933 | −0.07 % | 0.99068 | −0.93 % | OK |
| 11a | 1.00000 | 0.00 % | 1.00000 | 0.00 % | OK |
| 11b | 1.00000 | 0.00 % | 1.00000 | 0.00 % | OK |
| 13 | 0.99946 | −0.05 % | 1.00000 | 0.00 % | OK |
| 14 | 0.99607 | −0.39 % | 0.99983 | −0.02 % | OK |

Seven values in the 1-2 % WARN band, **none above 2 %**; worst is unit 9 sx at −1.65 %.
Content-side corroboration on this build: street-corridor widths measured across the canvas run
388-472 px in the A-D column and 430-460 px in the D-G column with no systematic drift between
units, and block-column pitch is reproduced (see Part A(1) table). The rev-6 unit-5 block-ratio
WARN (H-I × 21-22 at 1.068) was not re-derived and is carried forward unresolved.

**PASS-WITH-WARNINGS.**

## Item 2 — Seam crops; streets/blocks connect, offsets under ~40 px → **PASS-WITH-WARNINGS**

Graded against the measured ±80 px noise floor (the brief's ~40 px is below what the artifact can
physically resolve). All values are estimator 1 unless marked.

### Horizontal seams (shared streets)

| seam | units | crossing | rev 7 | rev 8 | verdict |
|---|---|---|---|---|---|
| 19th A-D | 2\|7 | AV C | +8 | **+9** | PASS |
| **20th D-G** | **3\|6** | **AV E** | **−242** | **+25** | **PASS (fixed)** |
| **20th D-G** | **3\|6** | **AV F** | **−305** | **−24.5** | **PASS (fixed)** |
| 22nd A-D | 7\|9 | AV B | −87 | −65 | PASS (edge of band) |
| 22nd A-D | 7\|9 | AV C | −46 | **−46** | PASS |
| 23rd D-G | 6\|10 | AV E | −22 | **−22.5** | PASS |
| 23rd D-G | 6\|10 | AV F | +80 | **+79** | PASS (edge of band) |
| 23rd G-H | 5\|11a | AV H | +73 | −7.8 (est. 3) | PASS |
| 25th A-D | 9\|14 | AV B | +84 | **+85** | PASS (edge of band) |
| 25th A-D | 9\|14 | AV C | +25 | +25 | PASS |
| 26th D-G | 10\|13 | AV F | +37 | **+37** | PASS |
| 26th D-G | 10\|13 | AV E | +26 (dR) | not resolvable | carried, see A(2) |
| 25th G-H | 11a\|4 | AV H | +169 (est. 3) | not resolvable | WARN, carried |

### Vertical seams (shared avenues)

| seam | units | crossing | rev 7 | rev 8 | verdict |
|---|---|---|---|---|---|
| AV D | 2/7\|3 | 19th | — | **+80** / +72.5 (est. 3) | PASS (edge of band) |
| AV D | 7\|6 | 21st | −80 | **−79** | PASS |
| AV D | 9\|10 | 24th | −93 | −92.8 (est. 3) | WARN |
| AV D | 14\|13 | 26th | −92 | +99.2 (est. 3) | WARN |
| AV D | 14\|13 | 27th | −124 | **−123.5** | WARN (known, disclosed) |
| AV G | 6\|5 | 21st | +152 (est. 3, split) | −59.5 | PASS |
| AV G | 6\|5 | 22nd | −6 | **−3.5** | PASS |
| AV G | 10\|11a | 24th | −14 (est. 3) | −111.5 (est. 3) | WARN, low confidence |
| AV G | 13\|4 | 27th | +8 | **+8.5** | PASS |
| AV H | 11a\|11b | 24th | −146 | **−145** | WARN (abuts disclosed H-I × 24-25 gap) |

### Other seam-quality checks

* **No black or transparent wedges** at any seam crop examined. Every crop is paper tone or
  printed content edge to edge.
* **No white seam lines.** No bright rule at any seam; the ~30 px crossfade is present by design.
* **Flat paper bands interrupting content.** A per-seam detector was run (`qc1r8/m8.py`) looking
  for (a) rows/columns whose median R−B drops to ≤ 6 — map paper is warm at R−B ≈ +19..+29,
  scanner background is neutral/cool — and (b) fully ink-free bands ≥ 60 px across the seam's
  whole width. Results, against interior controls:
  * **19th A-D (2\|7): a 48 px cool strip at y 7314-7361 with a 68 px ink-free band at 7276-7343,
    running x ≈ 700-6117 (the full A-D width).** This is the physical bottom edge of scanned
    sheet 02 — deckled paper edge, drop shadow, and scanner background — see Item 4. Row ink
    density shows unit 2's last block frontage at y ≈ 7000 and unit 7's first at y ≈ 7360, a
    360 px corridor against 460-470 px at interior streets: the band is **wholly inside the 19th
    Street corridor and destroys no block content**, but it narrows the corridor ~100 px.
  * **23rd H-I / G-H (5\|11b): a 65 px cool strip at y 15856-15920**, same signature (sheet 05's
    bottom edge). Below it lies unit 11a/11b content on the west and the disclosed H-I × 24-25 /
    I-J × 23-28 gaps on the east.
  * **25th A-D and INT 24th A-D also trip the cool test** — but there the *whole region* reads
    R−B = 7 and there is **no** ink-free band. That is unit 9's disclosed green/dark tonal cast,
    not a scan edge; the interior control (where a scan edge is impossible) proves the test's
    false-positive mode and it is discounted with cause.
  * Every other seam and every other interior is clean on both tests.

**PASS-WITH-WARNINGS** — no seam offset exceeds the noise floor by more than ~1.8x (worst:
AV D @ 27th, −124, disclosed and unchanged), the 20th D-G failure is cleared, and the two flat
bands found are scan edges confined to street corridors (graded under Item 4).

## Item 3 — No duplicated street or avenue labels at any seam → **PASS**

| location | legend | instances | evidence |
|---|---|---|---|
| Avenue H 23-24 | "AV. H OR WILLIAMS E." | **1** | `a8_avH_label.png`, `a8_avH_corridor.png` |
| 20th D-G | "20TH ST." | 1 | `a8_20th_DG_wide.png`, `a8_20th_avE.png` |
| 18th D-G | "18TH" | 1 | `a8_18th_DG.png` |
| 22nd A-D / D-E | "22ND" | 1 | `a8_target_E22.png` |
| 23rd D-G | "TREMONT" (= 23rd St) | 1 | `a8_23rd_DG_avF.png` |
| 26th D-G | "…ST." (26th) | 1 | `a8_26th_avF.png` |
| Avenue E | "AV. E OR…" | 1 | `a8_target_E22.png` |
| Avenue F | "AV. F OR C…" | 1 | `a8_26th_avF.png` |
| Avenue D | "OR MARKET E. NO 6" | 1 | `a8_20th_DG_wide.png` |

No duplicated address run, block number or building label was found in any crop, at any seam,
beyond the intended ~30 px crossfade. The rev-6 Avenue H duplication stays eliminated.

**PASS.**

## Item 4 — No title cartouche, scale bar, or sheet-margin material inside the artwork → **PASS-WITH-WARNINGS (new finding)**

The enumerated failure modes are **absent**: no title cartouche, no decorative masthead, no sheet
number in a margin block, no marginal note beyond a border anywhere examined. Everything
previously flagged resolves to the disclosed retained-in-frame list:

| feature | location | verdict |
|---|---|---|
| "Scale of Feet" graduated bars | 20th D-G, 23rd G-H, 26th D-G, Avenue H 23-24 | disclosed in-frame original |
| "SEE SHEET Nº 7 / Nº 11 / Nº 20" cross-references | 19th A-D, 23rd G-J, Avenue H | disclosed in-frame original |
| "A.V.D.G. Oct. 27" oval date stamp | 23rd, east of Avenue I | disclosed in-frame original |
| Library of Congress "Map Division" ink stamp | Avenue D between 18th and 19th | disclosed in-frame original |
| Printed panel-frame rules | sheet 02 bottom at 19th; sheet 05 bottom at 23rd; 11a/11b edges | retained in-frame panel border, per instruction |

**New finding — physical scan edges are visible at two seams.** Immediately *below* the retained
frame rules named above, i.e. genuinely **outside** the printed map frame, the composite shows:

1. **19th A-D (units 2 \| 7)**: ~110 px of blank off-frame sheet margin (tone 230,222,206 vs paper
   236,232,220), then a 48 px neutral/cool scanner-background strip (225,231,236 — note B > R,
   the inverse of map paper) terminated by the deckled paper edge and its drop shadow, at
   **y 7276-7361, x ≈ 700-6117** (the full A-D width, ~5,400 px).
   Evidence: `qc1r8/c8_edge_19th_native.png` (native, unmistakable torn edge + shadow),
   `qc1r8/c8_edge_19th_AD.png` (full seam width).
2. **23rd G-J (units 5 \| 11a/11b)**: the same signature at **y 15856-15920, x ≈ 13416-17192**.
   Evidence: `qc1r8/c8_edge_23rd_HJ.png`, `qc1r8/c8_edge_23rd_native.png`.

Mitigation, measured not assumed: both bands lie **wholly inside their street corridors** — at
19th A-D unit 2's last block frontage is at y ≈ 7000 and unit 7's first at y ≈ 7360, versus 460-470
px corridors at interior streets, so **no block, building, address or annotation is lost**. The
canvas-wide sweep (`qc1r8/m7.py`, 8x-subsampled cool-tone connected components) finds no third
instance.

This is **pre-existing, not a rev-8 regression** — the affected seams are in the A-D and G-J
columns, untouched by unit 3's x-only delta — and it was missed by rev 7. It is graded as a WARN
rather than a FAIL because the failure modes the item names are absent and no content is
displaced; but it is literally off-frame material inside the artwork, so it is named here in full.

**PASS-WITH-WARNINGS.**

## Item 5 — Coverage mask, numeric → **PASS-WITH-WARNINGS (one new region, caused by the fix)**

Recomputed from `coverage_mask.png` (26968 x 17632, binary 0/255):

* covered = **71.027 %**
* **uncovered = 28.973 %** (137,766,515 px)   [rev 7: 28.674 % — **+0.30 pp**]
* mapped-by-some-unit area = 327,441,436 px (68.86 % of canvas)
* **uncovered inside the mapped area = 823,755 px = 0.2516 % of mapped** [rev 7: 236,931 px]

Connected components of `(~covered) AND (mapped by some unit)`:

| # | area | bbox | identification |
|---|---|---|---|
| 1 | **586,824 px** | x 11533-11767, y 4699-9106 (234 x 4407) | **NEW — unit 3's east rim at Avenue G, streets 18-20** |
| 2 | 236,931 px | x 13427-13496, y 15930-19825 (69 x 3895) | the known Avenue H gutter (Item 3), extent bit-identical to rev 7 |

**Components between 300 and 3,000 px: 0. Components under 300 px: 0.** There is no scattered
hole anywhere inside a mapped block.

Per-cell coverage below 99.5 %:

| cell | unit | rev 8 | rev 7 |
|---|---|---|---|
| F-G x 18-19 | 3 | **92.93 %** | ~100 % |
| F-G x 19-20 | 3 | **92.93 %** | ~100 % |
| G-H x 23-24 | 11a | 97.47 % | 97.47 % |
| G-H x 24-25 | 11a | 97.30 % | 97.30 % |
| H-I x 23-24 | 11b | 99.24 % | 99.24 % |

**Component 1 is the price of the rev-8 fix and must be disclosed.** Translating unit 3's content
276 px west moved its rendered east limit from beyond Avenue G to x ≈ 11533, leaving a strip
uncovered. Assessment from pixels:

* The strip is **132 px wide inside unit 3's D-G box** (x 11533→11665); the remaining 102 px
  (x 11665→11767) lies in the already-disclosed G-J × 16-20 gap and merges with it seamlessly
  (identical tone 216,202,176 — `qc1r8/d8_aveG_u3_gap.png` shows no visible boundary between the
  two).
* It falls **inside the Avenue G roadway**: unit 6's Avenue G frontages sit at −151 / +200 from
  nominal (x 11514 / 11865), so 11533-11665 is street, not block. Unit 3's block content reaches
  x ≈ 11533, i.e. ~19 px past the block frontage line. **No building, address, block number or
  annotation is lost.**
* What *is* clipped: the eastern tips of two block-division rules (`1515.`, `131.`) are cut
  mid-stroke at the rim, and the block's east corner returns are absent —
  `qc1r8/d8_aveG_u3_native.png` shows this at native scale. Cosmetic.
* The far side of this rim is the disclosed **G-J × streets 16-20 gap**, so under the standing
  context ("rim edges facing water/gaps uncorrected") this is an uncorrected rim edge facing a
  disclosed gap, not a hole in mapped territory.

Every other uncovered pixel lies in a disclosed gap (G-J × 16-20, D-G × 16-18, H-I × 24-25,
I-J × 23-28, G-J × 23-28 except G-H × 25-28, padding ring).

**PASS-WITH-WARNINGS.** No scattered holes; one new 132 x 4,357 px rim strip inside a street
corridor, at 0.176 % of the mapped area.

## Item 6 — Target intersection Avenue E x 22nd present and labelled → **PASS**

Predicted canvas position **x = 7952, y = 13351** (brief table + 464). `qc1r8/a8_target_E22.png`
(native x 7202-8702, y 12601-14101 at 0.62x) puts the two corridors crossing at the crop centre —
the prediction is exact this revision, the rev-7 grid discrepancy having been resolved.

Both legends present, single-instance and fully legible: **"AV. E OR…"** set vertically and
**"22ND"** set horizontally, plus the corridor annotations `10" W. Pipe` and two `D. Hyd.`
hydrants. Readable content on all four corners: LAMP CO. / B & S. / D.G. / Dress Making / Off's
above / D.G. Cloy. / 168-176 (NW); Vac. S. ×3 / Cigars / Laundry / 151⅓ / 161½ / 202-206 (NE);
165-175 / Cobbler / Vac. / D.G. / STOVE / B & S. Cloy. / Fac. Building / 128-138 (SW);
Pianos & Organs / Tailor / Leather & Shoe Findgs. / Jewelery / Sew'g Mach's / Books & Patterns /
617-618 / 205-207 (SE).

**PASS.**

## Item 7 — Spot-check line identity → **PASS**

Seven checks (brief asks for three), each at the canvas position predicted by the refreshed table,
each read off native pixels:

| grid line | canvas coord | legend found in the composite | match |
|---|---|---|---|
| 18th Street | y = 4699 | "18TH" | yes |
| 20th Street | y = 9056 | "20TH ST." | yes |
| 22nd Street | y = 13351 | "22ND" | yes |
| 23rd Street | y = 15639 | "TREMONT" (23rd = Tremont St) | yes |
| 26th Street | y = 22372 | "…ST." (26th corridor, with 605/606, 629/630) | yes |
| Avenue D | x = 6117 | "OR MARKET E. NO 6" (D = Market St) | yes |
| Avenue E | x = 7952 | "AV. E OR…" (= Postoffice) | yes |
| Avenue F | x = 9799 | "AV. F OR C…" | yes |
| Avenue H | x = 13480 | "AV. H OR WI[LLIAMS]…" | yes (single instance) |

No line is mislabelled or off by one; the Galveston street/avenue alias pairs (D = Market,
E = Postoffice, H = Williams, 23rd = Tremont) all land on the correct grid line.

**PASS.**

---

# PART C — Non-geometry observations (reported, not graded here)

* **Sheet 9 tonal cast** — present as disclosed and now quantified: across A-D × 22-25 the median
  R−B is **+7** against +19..+29 everywhere else, i.e. the cast is a loss of the paper's warmth,
  not just a darkening. Fidelity item, not geometry. It is also the sole false-positive source for
  the scan-edge detector in Item 2.
* **Tonal seams** — a visible brightness/warmth step runs along the 26th D-G seam
  (`a8_26th_avF.png`) and along Avenue D near 25th. Geometry unaffected; cosmetic.
* **Housekeeping done** — `composite_raw.dat` has been deleted as rev 7 recommended, and the
  brief's canvas table now matches `registration.json`. Both rev-7 housekeeping items are closed.
* **`registration.json` is stale in one respect**: `seam_content_offsets` still holds only the
  single stale entry `["11a","4",42.3,49.0,0.63]`. Cosmetic; no consumer identified.
* **Rim edges facing water/gaps** remain uncorrected as disclosed. RIM corridors were excluded
  from all seam-vs-interior comparisons.

---

# VERDICT

## **PASS-WITH-WARNINGS**

The rev-7 FAIL is cleared decisively. The sign flip on unit 3's manual knot delta moved the 20th
D-G seam from −242 / −305 px to **+25 / −24.5 px**, a change of +267 / +280.5 against the +276 px
the flip should produce; three independent estimators put the residual between −35 and +30 px,
the zero-lag cross-correlation has gone from *anti*-correlated (−0.13 / −0.19) to strongly positive
(+0.43 / +0.45), and the seam's corridor widths are now indistinguishable from single-sheet
interiors. Independently, unit 3's frontages agree with unit 6's to within −46…+31 px at all three
shared avenues, so the correction is right in magnitude and not merely tuned to two crossings.
Fourteen control seams reproduce rev-7's values to within 2.5 px: nothing else moved.

**There are no FAILs this revision.** Three warnings are carried, one of them new and caused by
the fix:

### Warnings, in order of importance

| # | Item | Warning | Evidence |
|---|---|---|---|
| W1 | Item 5 | **NEW, caused by the fix.** Unit 3's 276 px westward translation uncovered its east rim: a 132 x 4,357 px strip inside the D-G box at Avenue G, streets 18-20 (component area 586,824 px incl. the part already in the disclosed gap; uncovered-inside-mapped rose 236,931 → 823,755 px). It lies inside the Avenue G roadway, faces the disclosed G-J × 16-20 gap, and clips only the eastern tips of two block-division rules — no building, address or block content lost. | `qc1r8/d8_aveG_u3_gap.png`, `qc1r8/d8_aveG_u3_native.png`, `qc1r8/m9.py` |
| W2 | Item 4 / Item 2 | **Pre-existing, missed by rev 7.** Physical scan edges — off-frame sheet margin, deckled paper edge, drop shadow and cool scanner background — are visible at two seams: 19th A-D (y 7276-7361, full A-D width) and 23rd G-J (y 15856-15920). Both sit wholly inside street corridors; no content lost. | `qc1r8/c8_edge_19th_native.png`, `qc1r8/c8_edge_19th_AD.png`, `qc1r8/c8_edge_23rd_HJ.png` |
| W3 | Item 3 / Item 5 | Unchanged from rev 7: the 69 px Avenue H 23-24 paper gutter exceeds the disclosure's "< 40 px" wording. Inside the street corridor, no content lost, single unclipped legend. | `qc1r8/a8_avH_label.png`, `qc1r8/a8_avH_corridor.png` |
| W4 | Item 2 | Unchanged from rev 7 and never corrected: Avenue D at 27th (14\|13) at **−123.5 px**, ~1.5x the noise floor. Corridors healthy (463 / 436 px), no duplication. Also AV D @ 24th/26th and AV G @ 24th at 90-115 px by estimator 3 only, low confidence. | `qc1r8/a8_aveD_27th.png` |
| W5 | Item 1 | Seven fitted scale values in the 1-2 % band (worst unit 9 sx −1.65 %); none above 2 %. Unit 5's rev-6 block-ratio WARN (H-I × 21-22, 1.068) carried forward unresolved. | `registration.json` |

### Per-item summary

| item | verdict |
|---|---|
| (1) 20th D-G (3\|6) re-measure | **PASS** — +25 / −24.5 px (was −242 / −305); 3 estimators agree within ±35 |
| (2) no regressions from the unit-3 shift | **PASS** — 14 controls reproduce rev 7 to ≤2.5 px |
| (2a) 26th D-G (10\|13) | **PASS** — +37 at AV F, identical to rev 7 |
| (2b) Avenue H 23-24 (11a\|11b) | **PASS** — one label, no duplication; 69 px gutter **WARN**, unchanged |
| (2c) 23rd G-H (5\|11a) | **PASS** — corridor open, est. 3 −7.8; rev-7 +73 not contradicted |
| (2d) 19th / 22nd / 25th seams | **PASS** on geometry (scan-edge finding at 19th → Item 4) |
| (2e) coverage mask | **PASS-WITH-WARNINGS** — one new rim component (W1) |
| (3) unit 3's other boundaries (18th, AV D, AV G, 23rd D-G) | **PASS** — ≤46 px vs unit 6 at every shared avenue |
| Checklist 1 — fitted scales | **PASS-WITH-WARNINGS** (7 in 1-2 %; none > 2 %) |
| Checklist 2 — seam crops, offsets | **PASS-WITH-WARNINGS** (worst −123.5 px, disclosed; no wedges, no white lines) |
| Checklist 3 — no duplicated labels | **PASS** |
| Checklist 4 — no margin material | **PASS-WITH-WARNINGS** (scan edges at two seams, W2) |
| Checklist 5 — coverage mask | **PASS-WITH-WARNINGS** (28.973 % uncovered; 0.2516 % of mapped, in 2 components, both inside street corridors) |
| Checklist 6 — target Avenue E x 22nd | **PASS** |
| Checklist 7 — line identity | **PASS** |

### Recommended for a rev 9 (none blocking)

1. **W1** — reclaim unit 3's east rim: extend its rendered extent 132 px east at Avenue G (or
   accept it, since it faces a disclosed gap and is inside the roadway). If accepted, add it to
   the disclosed-gap list so the next reviewer does not re-raise it.
2. **W2** — trim the two scan edges: mask sheet 02's and sheet 05's data below their printed frame
   rules so the lower unit's content wins the blend there. Low risk, both bands are in corridors.
3. **W4** — Avenue D at 27th (−123.5 px) has now gone three revisions without a correction.
4. **W3** — the Avenue H gutter, or a reworded disclosure that admits a 69 px in-corridor gutter.
5. Housekeeping: `registration.json`'s `seam_content_offsets` is stale.

The rev-7 report is archived as `qc_pass_1_rev7_superseded.md` (byte-identical to the superseded
`qc_pass_1.md`).
