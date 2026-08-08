# v3 QC — Reviewer 1 (TONE & MARGINS)

Artifact under review: `build/1885/galveston_1885_composite.tif` (18188 x 27524, PAD 742)
Comparators: `compare/v2_composite.tif` (PAD 464), `sources/1885/Galveston_1885_sheet_NN.jpg`
Evidence: `build/1885/v3_qc_evidence_1/` (all crops referenced below live there)
Method: programmatic crops + statistics only. Nothing was modified.
Disclosed non-defects were checked against the brief and are NOT counted as failures below.

---

## 1. CAST REMOVAL — **FAIL**

Per-unit interior paper tone (luma-selected paper mask `luma 195..246, max-min <= 45`,
interior inset 320 px from the unit's grid box) is in
`tone_table.md` / `tone_table_src_v2_v3.json`. Tone-map visualizations (chroma
exaggerated x4 about the per-pixel mean) are `01_tonemap_v3.png` and `01_tonemap_v2.png`;
raw downsamples `01_small_v3.png` / `01_small_v2.png`.

| unit | SRC B,G,R | v2 B,G,R | v3 B,G,R | v3 norm B/G/R | spread | G-excess |
|---|---|---|---|---|---|---|
| 2 | 215,229,236 | 215,229,234 | 215,229,234 | 0.9513/1.0133/1.0354 | 19 | +4.5 |
| 3 | 220,233,236 | 215,229,235 | 215,229,235 | 0.9499/1.0118/1.0383 | 20 | +4.0 |
| 4 | 219,233,236 | 216,230,235 | 216,230,235 | 0.9515/1.0132/1.0352 | 19 | +4.5 |
| 5 | 216,230,236 | 216,230,235 | 216,230,235 | 0.9515/1.0132/1.0352 | 19 | +4.5 |
| 6 | 209,224,232 | 213,227,233 | 213,227,233 | 0.9495/1.0119/1.0386 | 20 | +4.0 |
| 7 | 217,231,235 | 217,230,235 | 217,230,235 | 0.9545/1.0117/1.0337 | 18 | +4.0 |
| **9** | **199,222,232** | **209,233,231** | **209,234,229** | **0.9330/1.0446/1.0223** | **25** | **+15.0** |
| 10 | 219,232,235 | 215,229,234 | 215,229,234 | 0.9513/1.0133/1.0354 | 19 | +4.5 |
| 11a | 221,234,237 | 216,230,235 | 216,230,235 | 0.9515/1.0132/1.0352 | 19 | +4.5 |
| 11b | 222,235,238 | 216,230,235 | 216,230,235 | 0.9515/1.0132/1.0352 | 19 | +4.5 |
| 13 | 217,231,235 | 216,230,235 | 216,230,235 | 0.9515/1.0132/1.0352 | 19 | +4.5 |
| 14 | 219,232,236 | 216,229,235 | 216,229,235 | 0.9529/1.0103/1.0368 | 19 | +3.5 |

G-excess = `G - (B+R)/2`. Edition target (median of the 12 v3 units) = norm
0.9515/1.0132/1.0352, spread 19, G-excess +4.5.

**Finding 1A (BLOCKER). Sheet 9's cast was not removed — it was made worse.**
- Eleven of twelve units land on the edition target to within +/-0.005 normalized and
  G-excess +3.5..+5.0. Unit 9 sits at G-excess **+15.0** (v2: +13.0), i.e. v3 moved
  sheet 9 *further* from the target than v2, not closer. Spread 25 vs the 18-20 target.
- Unit 9 is the only unit whose v3 paper differs from v2 at all (all other units are
  bit-comparable in tone; see `patch_tone_v2.json` vs `patch_tone_v3.json`).
- Direction check against the source: source sheet 9 paper is **R > G by 10 DN**
  (199,222,232 — a *warm/yellow*, B-deficient scan, not a green one).
  v3 delivers **G > R by 5 DN** (209,234,229). The paper's warm/cool polarity is
  inverted relative to the source.
- Alignment-free gain measurement (per-channel percentile transfer over the whole unit
  interior, `hue_gain_report.json`): sheet 9 gains at p90 = **B x1.0586, G x1.0598,
  R x0.9916**; luminance-normalized **B 1.021 / G 1.022 / R 0.957**. R is pushed down
  6.4-6.9% relative to G/B. The needed correction was B-up / G-flat / R-slightly-down;
  what was applied is B-up / G-up-equally / R-down, which is a green push.
- Independent corroboration: a whole-canvas detector for "paper with R-B < 0" (physically
  impossible for aged paper) returns one dominant blob of 6.6 Mpx bounded by
  x 312-6256, y 13736-24688 — exactly unit 9 (`09_backing_map.png`,
  `intrusion_blobs.json`).

Evidence crops: `01_tonemap_v3.png` (unit 9 is the only green block on an otherwise
neutral map), `01_seam_st22_aveB_u7_u9.png` (warm cream above the 22nd St seam, mint
green below — the step is obvious at 1:2), `01_seam_st25_aveB_u9_u14.png`,
`02_feat_u9_yellow_SRC_vs_V3.png` and `02_feat_u9_pink_SRC_vs_V3.png` (source left,
v3 right: cream paper becomes mint), `06_edge_left.png`.

---

## 2. NO OVER-CORRECTION — **FAIL (sheet 9 only; sheets 6 and 3 pass)**

Source-vs-v3 crops of a pink (brick), yellow (frame) and blue (special) feature, located
by connected-component search in the source and mapped to the canvas through the unit's
knot map, are `02_feat_u{9,6,3,2,14,5}_{pink,yellow,blue}_SRC_vs_V3.png`
(source left | v3 right, 700 px at 100%).

| unit | pink hue src -> v3 | yellow hue | blue hue | norm gain B/G/R |
|---|---|---|---|---|
| 9 | 3 -> 5 (sat 40 -> 33) | 24 -> 26 | 95 -> 94 | 1.021 / 1.022 / **0.957** |
| 6 | 5 -> 4 | 23 -> 24 | 96 -> 97 | 1.010 / 1.000 / 0.991 |
| 3 | 5 -> 6 | 25 -> 24 | 96 -> 96 | 0.992 / 0.998 / 1.011 |
| 2 | 4 -> 3 | 24 -> 24 | 98 -> 98 | 1.003 / 1.003 / 0.994 |
| 14 | 3 -> 3 | 25 -> 23 | 98 -> 98 | 1.001 / 0.993 / 1.006 |
| 5 | 4 -> 4 | 24 -> 25 | 95 -> 95 | 1.001 / 1.001 / 0.997 |

- **Sheets 6 and 3 pass cleanly.** Normalized channel gains stay inside +/-1.1%, hue
  medians move <= 1-2 (OpenCV H units, i.e. <= 4 deg), saturation within 2-5%. Brick is
  pink, frame is yellow, specials are blue. `02_feat_u6_pink_SRC_vs_V3.png` is visually
  indistinguishable from its source.
- **Sheet 9 fails the "subtle uniform gain" bar.** The R channel is depressed 6.4-6.9%
  relative to B/G — that is a hue rotation, not a gain. Brick is still pink (hue 3 -> 5)
  but desaturated (S 40 -> 33) with hue IQR tripling (2 -> 6); the paper it sits on is
  visibly mint. Brick is NOT blue, so the specific "brick must be pink" test passes;
  the paper/whitepoint test does not.
- No washed channel anywhere: no unit shows a channel percentile curve collapsing.

---

## 3. HIGHLIGHTS — **FAIL (2 units clip more than source)**

Fraction of pixels with any channel = 255, same interior region in source / v2 / v3
(`tone_table_src_v2_v3.json`, columns `clip_*`):

| unit | src | v2 | v3 | v3 per-channel B/G/R |
|---|---|---|---|---|
| 9 | 0.0000% | 0.0613% | **0.0606%** | 0 / **0.0606%** / 0 |
| 7 | 0.0000% | 0.0002% | **0.0020%** | 0.0020% / 0.0015% / 0 |
| all others | 0.0000% | 0.0000% | 0.0000% | 0 / 0 / 0 |

- **Unit 9**: 0.061% of pixels clip, all in the **green channel only** — the signature of
  the green over-boost. Green p99 rises 237 -> 251 while red p99 falls 240 -> 239.
  The source clips nothing. The "highlight-safe ceiling" did not hold for sheet 9.
- **Unit 7**: 0.0020% (B and G) vs 0.0000% in source — a 10x increase over v2's
  0.0002%. Tiny in absolute terms, but it is a regression against both v2 and source.
- Ten of twelve units clip nothing, matching their sources exactly.

---

## 4. MARGIN RETENTION — **FAIL (scanner border entered the canvas; one margin
cut through its own text)**

(a) Original margin annotations are present where the sheet has them — **PASS**.
- unit 2 top: "16TH ST." header clean and complete (`09_u2_16thst_header_100pc.png`);
  "OCT. 1885 GALVESTON TEXAS" oval complete and undamaged (`08_u2_top_oval_100pc.png`).
- unit 5 top: "SEE SHEET No. 3", "20TH ST.", the oval stamp and the sheet number "5"
  all present (`04_m_u5_top_full.png`, `04_m_u5_topright_100pc.png`).
- unit 5 right: "AV. J OR BROADWAY" + sheet number, clean (`04_m_u5_right_full.png`,
  `09_u5_right_rim_100pc.png` — no dark rim, 0 dark pixels sampled every 500 rows).
- unit 14 bottom/left: "28TH ST.", "SEE SHEET No.17", "Scale of Feet" bar, and the
  "J. LLOYD 10/28/85" draftsman signature all intact (`04_m_u14_bottom_full.png`).
- unit 4 right/bottom: "AV. H OR WILLIAMS W.", "SEE SHEET No.16" intact, clean straight
  paper edge (`04_m_u4_right_full.png`, `04_m_u4_bottomright_100pc.png`).
- unit 11b right: "AV. I OR MCKINNEY E." and the map frame corner intact
  (`04_m_u11b_right_full.png`).
- The LoC "Map Division / Library of Congress" stamp near Avenue G x 20th is complete,
  not clipped (`08_locstamp_u3_cut_100pc.png`).

(b) No scanner border / torn-edge debris — **FAIL**.

**Finding 4A (BLOCKER). A hard black scanner border is inside the canvas at unit 2's
retained top and left margins.**
`07_u2_topleft_blackband_100pc.png` (100%), `04_m_u2_topleft_corner_100pc.png`,
`06_edge_top.png`, `06_edge_left.png`.
- Top: pure black (gray = 0) band beginning at y = 164, running x ~200 to ~2600
  (~2400 px), thickness tapering 48 px -> 3 px (wedge, from scan rotation).
- Left: same band, x start 199, running y ~300 to ~3100, thickness 60 px -> 4 px.
- Immediately inboard of the black band is a ~100 px strip of light-blue **scanner
  backing board**, then the torn paper edge, then map paper.
- Row/column profiles in `edge_profiles.json`: rows y 180-220 carry up to 9.3% dark
  pixels; columns x 200-240 up to 11.2%.

**Finding 4B. Scanner backing / scan-edge remnants at three more retained margins.**
- unit 9 left margin: ~85 px bluish-white backing strip plus a 12 px dark scan edge at
  x 152-164, y 13716-15020 (`06_intrusion_03_dark_152_13716.png`,
  `07_u9_leftmargin_backing_100pc.png`).
- unit 14 bottom-left: ~90 px backing strip on the left and ~50 px at the bottom, with a
  visible **debris speck** on the backing and the torn paper edge exposed
  (`04_m_u14_bottomleft_100pc.png`, 100%).
- unit 5 top margin: black scan-edge line, x 16280-17784 (~1500 px), y 8677-8695,
  4-17 px thick (`09_u5_top_rim_100pc.png`, `06_intrusion_02_dark_16280_8676.png`).
- Additional (interior, not a margin): a ~55 px grey/white scan-edge strip with a dark
  line at the Avenue G seam between units 13 and 4, x ~11880-11960, y 22752-23452
  (`07_aveG_darkline_100pc.png`). Same class as the disclosed 19th/23rd corridor bands
  but at an **undisclosed** location — reported, not counted as a blocker.
- Disclosed and confirmed as such (not counted): 19th St band x 576-6456 y 7544-7664;
  23rd St band x 13692-17732 y ~16160.

(c) Margins end in clean paper or a clean edge — **FAIL at unit 13**.

**Finding 4C (BLOCKER). Unit 13's bottom margin is trimmed straight through its own
annotation.** `08_u13_bottom_cuttext_100pc.png` (100%), `08_u13_bottom_cuttext2_100pc.png`,
`04_m_u13_bottom_full.png`, `06_edge_bottom.png`.
- A hard horizontal fill edge at y ~= 27063 slices the words "SHEET" and "No.17" of the
  "SEE SHEET No.17" cross-reference through the middle of the glyphs; the flat tan fill
  begins immediately below the cut. A second glyph top is clipped just under "28TH ST."
- This reads as broken, not intentional, and it sits directly against unit 14's margin
  which is retained ~450 px deeper — producing a visible staircase along the canvas
  bottom edge.
- All other margins end cleanly (units 4, 5-right, 11b, 14-bottom).

---

## 5. GAP HONESTY — **PASS with a warning**

`gap_stats.json`, `05_g_*.png`.
- Fill colour is exactly **BGR (176, 202, 216)** everywhere, including the padding ring.
- Fully-enclosed gaps are perfectly flat: Avenues D-G x 16th-18th and I-J x 25th-28th
  both give per-channel **std = 0.0000** with **1 unique colour** over the sampled
  interior. No content, no texture, no noise.
- Avenue G-H x 18th-20th (the specific area named in the checklist) and H-I x 24th-25th
  show std 10-14 **only because the nominal grid rectangle overlaps units 3/5/11's
  retained margins**; the gap proper is flat. Verified visually in `05_g_GH_18_20.png`
  and `05_g_HI_24_25.png` — the non-flat pixels are unit 3's "AV. G OR WINNIE OR
  MENARD E. / THIS SHEET ABOVE. BLOCK No.319." margin band, i.e. real retained content.
- **WARNING — the fill does not match the paper it now abuts.** With v3 retaining
  exterior margins, the flat fill sits directly against original paper far more often
  than in v2. Retained-margin paper measures (216,230,235) at unit 2's top,
  (216,230,235) at unit 3's bottom, (201,215,220) at unit 5's right. The fill is
  (176,202,216): **dB 40, dG 28, dR 19** darker, and much warmer (R-B 40 vs 19-20).
  The boundary is a visible hard tonal step at every margin edge
  (`04_m_u4_right_full.png`, `08_u13_bottom_cuttext_100pc.png`). It is at least
  consistent — the same colour as the padding ring — so it reads as an intentional
  backing board rather than as damage. Recommend lightening/cooling the fill toward
  ~(205,222,230) so gap edges stop reading as a cut.

---

## 6. CANVAS EDGES — **FAIL (same causes as item 4)**

Outer 800 px border swept on all four sides at 1/6 (`06_edge_top.png`,
`06_edge_bottom.png`, `06_edge_left.png`, `06_edge_right.png`, stats in
`v3_edge_stats.json`), plus a whole-canvas dark-blob catalogue at 1/4
(`intrusion_blobs.json`, `06_intrusion_map.png`, `00_v3_darkmap.png`) and 100% corner
crops (`08_canvas_corner_{TL,TR,BL,BR}.png`).

- **Top edge / top-left corner: dark band present** — min gray 0, 0.93% of the strip
  below gray 80. This is Finding 4A. Visible at overview zoom.
- **Left edge: dark band present** — min gray 0, 0.71% below gray 80 (Findings 4A/4B).
- **Right edge: clean.** min 81 in the sampled strip, no bands, unit 5's margin ends in
  clean paper; the "5" sheet number and "AV. J OR BROADWAY" are complete.
- **Bottom edge: no dark band** (min gray 71) **but the unit 13 half-cut text of
  Finding 4C sits in it**, and the three bottom margins (14, 13, 4) are retained to
  three different depths, giving a ragged staircase.
- No clipped stamps found anywhere on the border sweep: every oval date stamp, LoC
  stamp, sheet number and scale bar encountered is whole.
- Canvas corners TR / BR / BL are pure fill; TL carries the black band.

---

VERDICT: FAIL

- **Sheet 9's cast is worse in v3 than in v2, not fixed.** G-excess of unit 9's paper
  went +13.0 (v2) -> +15.0 (v3) against an edition target of +4.5; the applied gain
  depresses R by 6.4-6.9% relative to G/B, inverting the paper's warm/cool polarity
  versus a source that is R > G by 10 DN. Unit 9 is the only unit whose tone changed
  at all, and it changed in the wrong direction.
- **The green over-boost also breaks the highlight guarantee**: unit 9 clips the green
  channel on 0.061% of pixels (G p99 237 -> 251) where the source clips nothing; unit 7
  clips 0.0020% vs 0.0000% in source. Two units clip more than their sources.
- **Margin retention imported the scanner bed.** A pure-black scanner border (48-60 px
  tapering to 3 px, ~2400 px along the top and ~2800 px down the left) plus a ~100 px
  blue-white backing strip now sit inside the canvas at unit 2's top-left; backing
  strips, a debris speck and a 4-17 px black scan-edge line also appear at units 9-left,
  14-bottom-left and 5-top.
- **Unit 13's bottom margin is trimmed through the middle of its own "SEE SHEET No.17"
  glyphs**, with flat fill starting immediately below the cut — the one place where the
  retained margin looks broken rather than deliberate.
- **What passes:** sheets 6, 3, 2, 5, 14 hold their source hue to within 1-2 hue units
  and +/-1.1% normalized gain (brick pink, frame yellow, specials blue, no washed
  channels); every named margin annotation — 16TH ST., both GALVESTON ovals, SEE SHEET
  Nos. 3/16/17, AV. J / AV. H / AV. I labels, scale bar, LoC stamp, J. Lloyd signature —
  is present and unclipped; enclosed gaps are exactly flat (std 0.0000, 1 colour) with
  no content, though the fill tone is 40 DN bluer-deficient than the paper it abuts and
  should be nudged toward it.
