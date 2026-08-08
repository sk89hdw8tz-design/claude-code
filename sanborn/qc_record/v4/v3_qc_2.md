# v3 QC — Reviewer 2: SEAMS & LABEL INTEGRITY

Artifact under review: `build/1885/galveston_1885_composite.tif` (18188 x 27524, PAD 742)
Reference: `compare/v2_composite.tif` (PAD 464; v3 = v2 + 278 in both axes)
Evidence: `build/1885/v3_qc_evidence_2/` (82 files)
Method: programmatic crops only; nothing was modified. Working memmaps `build/1885/v3_raw.dat`,
`build/1885/v2_raw.dat` (built by `qc2r_mk.py`); helpers `qc2r_lib.py`, `qc2r_seamlist.py`,
`qc2r_seam.py`, `qc2r_cont.py`, `qc2r_strips.py`, `qc2r_labels.py`, `qc2r_paper.py`.

NOTE on the seam registry supplied to me: I re-derived seam geometry from the imagery and the
unit-span table. All 11 vertical + 8 horizontal seams in the registry were located and walked.
Two registry notes did not survive contact with the imagery and are recorded below (§7).

---

## Headline

**v3's advertised glyph-aware seam-cut fix is not observable at the site it was specified for,
and v3 introduces a new solid-black scanner-edge rule across the 19th St corridor that covers
map content v2 rendered cleanly.**

---

## 1. STREET-NAME LABEL INTEGRITY

Every seam corridor was walked end to end at 0.42x (26 pair strips, `S_*_p*.png`, v3 beside v2),
then every display-weight label in each corridor was re-cropped at 100%. Label inventory was also
built programmatically (216 display-type blocks in v3, 220 in v2; `bigtext_v3.json`) and each v3
block matched to its v2 counterpart.

Labels verified COMPLETE at 100% — no mid-glyph slice, no missing half, no duplicate copy:

| Label | Corridor | Evidence |
|---|---|---|
| 19TH ST. | H1 19th A–D | `S_H1_19th_2-7_A-D_p0.png` |
| 20TH ST. | H2 20th D–G | `S_H2_20th_3-6_D-G_p0.png` |
| 22ND ST. | H3 22nd A–D | `S_H3_22nd_7-9_A-D_p0.png` |
| 23RD OR TREMONT | H4 23rd D–G | `S_H4_23rd_6-10_D-G_p0.png` |
| 25TH ST. OR BATH AV. | H6 25th A–D | `S_H6_25th_9-14_A-D_p0.png` |
| 26TH ST. | H8 26th D–G | `133_26th_full_v3.png` |
| AV. D OR MARKET | V6 AvD 25–26 | `130_AvD_label_v3.png` / `_v2.png` |
| AV. G OR WINNIE OR MENARD E. | V8 AvG 20–23, V9 AvG 23–25 | `070_AvG_label_v3.png`, `S_V8..p0.png`, `S_V9..p0.png` |
| AV. G OR WINNIE OR MENARD W. | V10 AvG 26–28 | `S_V10_AvG_13-4_26-28_p0.png` |

### 1a. The named v2 defect site is unchanged, not fixed — INFORMATIONAL

The brief says v2 sliced "25TH" numerals at 25th / Avenue G near v2 canvas (11600, 19994),
i.e. v3 (11878, 20272). At that exact site v3 and v2 are **pixel-identical**: over a 1600 x 1600 px
window centred there the maximum per-channel difference is 5/255. `060_v3_at_11878_20272.png` vs
`060_v2_at_11600_19994.png`, `070_AvG_label_v3.png` vs `070_AvG_label_v2.png`.

What is actually at that location is the tail ("AV." + "SEE") of the **AV. G OR WINNIE OR MENARD E.**
label, whose ink ends at canvas x≈11940 with the Avenue G cut at x=11943 — i.e. it clears the cut by
about 3 px, in v3 *and* in v2. I could not reproduce any sliced "25TH" numeral at this site in v2.
Either the coordinate in the brief is wrong, or the defect was never there. Either way **no glyph-aware
re-cut is detectable at the site the v3 change was written for.**

More generally: I found **no seam anywhere whose cut position moved measurably between v2 and v3**
(see §2). If cuts had been re-chosen, corridor diff profiles would show a strip of wholesale content
replacement; the largest local diff fraction found in any corridor is 0.32, and every cut boundary
lands at the same canvas coordinate in both builds.

### 1b. AV. H OR WILLIAMS is sliced mid-glyph — PRE-EXISTING, NOT FIXED

`120_AvH_label_v3.png` (rotated to read horizontally) — the disclosed 69 px Avenue H gutter runs
straight through the label. Roughly the top 57% of every glyph height is replaced by flat tan paper;
the label survives only because its lower half is still readable.

- v2 is pixel-identical here (`120_AvH_label_v2.png`), so this is **not a v3 regression**.
- But the source scan has the label **completely intact on continuous paper**: `121_src_sheet11_AvH_label.png`
  (sheet 11 native x 1950–2350, y 1300–2650) shows "AV. H OR WILLIAM[S]" with no paper gap at all.
  The 69 px "gutter" is manufactured by the 11a/11b panel clipping, not by the original sheet.
- This is the single worst mid-glyph slice of a street-name label in the whole composite, it is the
  one the "glyph-aware p97 localized-ink penalty" should have caught, and it was not touched.

### 1c. Duplicated "25TH ST. OR BATH AV." at 25th x G–H — PRE-EXISTING, genuine content

`03_v3_25th_labels_tall.png`, `S_H7_25th_11a-4_G-H_p0.png`. Two complete copies of the label,
offset ~+110 px in y and ~-70 px in x. Verified NOT a rendering ghost:

- sheet 11 carries the label near its bottom edge (`02_src_sheet11_25th.png`), sheet 4 carries it
  near its top edge (`02_src_sheet04_25th.png`) — both are original print, and the 25th cut passes
  between them, so both survive;
- ink strength is full in both copies (min gray 68 / 71; mean ink 104 / 110) and matches the two
  sources (sheet 11 = 102, sheet 4 = 112). Neither is a 50% grey ghost.

v2 is identical here. Reported for completeness against the checklist wording; not a v3 regression,
but it is a real duplicate that a cut placed ~110 px differently would have removed.

---

## 2. NO NEW DUPLICATES / GHOSTS — PASS

- Per-corridor v3-vs-v2 difference profiles (±760 px band, 40 px bins) over all 19 seams: **no strip
  anywhere shows the >0.5 difference fraction that a moved cut would produce**. Peak was 0.32 (V1);
  the differences that do exist are whole-sheet, caused by v3's per-sheet re-registration
  (phase-correlation vs v2, beyond the +278 offset: sheet 2 = −4.2/−3.8 px, sheet 7 = 0/+3.2,
  sheet 14 = 0/+4.8, sheet 9 = 0/+1.6, sheets 3/5/6/10/11/13/4 ≈ 0) and by the new white balance.
- Whole-canvas large-difference map `007_bigdiff_v3_v2.png`: all changes are either whole sheets or
  the new exterior margins. No thin band hugging any interior cut.
- Near-duplicate display-text pair census (same orientation, ≤400 px apart, size within 35%):
  **17 pairs in v3, 17 pairs in v2** — no new pair. Manually cleared the one v3-only split
  (`020_H6_25th_dupcheck_v3.png`: "T.W. ENGLISH" / "COAL YARD." — two different lines of text, not a duplicate).
- No 50% grey ghost text found at any seam (ink-strength check in §1c is representative).

---

## 3. AVENUE H CORRIDOR (23rd–24th) — PASS

Over the full 23rd→24th span, ±500 px either side of Avenue H, v3 and v2 differ by >25/255 in only
**10 of 1000 columns**; overall differing fraction 0.0049. Measured on a 1300-row sample the two are
literally pixel-identical (max per-channel diff = 1).

- Gutter width: **canvas x 13706–13774 = 68 px** in v3, matching the disclosed 69 px, and identical
  to v2 (`030_AvH_gutter_v3_100.png` vs `030_AvH_gutter_v2_100.png`, column profile in the run log).
- No black divider rule entered the corridor: solid-black (≥14 px contiguous) pixel count in this
  corridor is **0 in v3** (v2 had 172).
- No content loss on 11b's side: block faces, "1403", "Dwg.", "59½", "1½ / TUB CIST." all intact and
  identical to v2.

Note: the brief states v3 moved 11b's left clip from native x 2100 to 2164 (+64 px). **That change
produced no net effect in the composite** — the gutter did not move or widen, and the corridor is
byte-for-byte what v2 shipped.

---

## 4. CORRIDOR CONTINUITY — PASS

Measured at all 38 seam endpoints (each vertical seam at both of its street intersections, each
horizontal seam at both of its avenue intersections) by cross-correlating the cross-street edge-line
profiles taken 250–900 px either side of the cut.

- v3 is within **±5 px of v2 at every endpoint**; the few flagged "worse" (V1 @18/19 −21 vs −18,
  V7 @28 +39 vs +35, V10 @26 −36 vs −33, H1 @AvA −17 vs −12) are all at correlation r ≤ 0.48 and
  are inside measurement noise.
- Two endpoints improved materially: V6 @26th (v3 −11 vs v2 +40) and H6 @AvA (v3 +6 vs v2 −37).
- **Target intersection Avenue E x 22nd** (v3 canvas 8229, 13628): over a 1600 x 1600 px window the
  maximum per-channel difference vs v2 is **5/255**, mean 0.29, zero pixels differing by >8.
  Unchanged, as required. `040_target_E22_v3.png` / `040_target_E22_v2.png`.

---

## 5. KNOWN 27th ST JOG AT AVENUE D — PASS

Row-profile cross-correlation of 27th St's channel edges, left vs right of Avenue D:

| window | v3 | v2 |
|---|---|---|
| 250–1400 px | +112 px (r 0.41) | +107 px (r 0.41) |
| 250–900 px | +115 px (r 0.44) | +110 px (r 0.44) |

Jog grew by ~5 px (≈4%), still comfortably under the disclosed ~124 px. `050_jog27_AvD_v3.png`,
`050_jog27_AvD_v2.png`. **Did not grow materially.**

---

## 6. PRINT-EXTENT CAPS — FAIL

**A new solid-black scanner-edge rule has been pasted across the 19th St corridor, over unit 7's map
content.** This is precisely the failure mode this check exists to catch.

Evidence: `900_FINDING_blackrule_19th_v3_vs_v2.png` (annotated pair), `114_blackbar_19th_pair.png`,
`111_19th_band_v3_100.png` vs `111_19th_band_v2_100.png`, `112_lost_worst_v3.png` vs `112_lost_worst_v2.png`.

Measurements (solid black = gray < 70 with a ≥14 px contiguous run, i.e. excludes map linework):

| corridor | v3 | v2 | ratio |
|---|---|---|---|
| H1_19th_2-7_A-D, horizontal runs | **27,868 px** | 5,087 px | 5.5x |
| H1_19th_2-7_A-D, vertical runs | **10,491 px** | 261 px | 40x |
| V2_AvD_7-3_19-20 (same artifact, its east end) | 19,464 / 10,289 px | 5,617 / 91 px | 3.5x / 113x |
| every other corridor (17 of 19) | — | — | equal or better (V9, V11, H5 improved) |

Geometry of the new bar: canvas **y 7622–7648, x 5292–6452** — 1,160 px long, thickening from 14 px
at its west end to 30 px at Avenue D. Columns carrying a ≥14 px solid-black run in the A–D half of
the 19th corridor: **1,059 in v3 vs 25 in v2 (42x)**. Confined to x < 6470 (the units 2/7 side);
right of the Avenue D cut v3 and v2 are identical (19 columns each).

Collateral, same corridor: the disclosed scan-edge band widened from **49 to 69 rows** of scanner
backing-white (rows >30% coverage: v2 7302–7350, v3 7576–7644), and total black in the corridor
window went 9,151 → 33,224 px.

Content actually lost: **18,110 px that carried map ink or block colour in v2 are covered by
scanner black / backing white in v3**, spread over x 1000–6650, y 7380–7894. Worst concentration at
canvas (5795, 7633) — the black rule sits on the top block-face line of the "Bake Ho. / OVENS. /
Bakery." block and shaves ~25 px off the top of unit 7's first block row (`112_lost_*`).

Why it matters beyond the pixel count: in v2 this transition was a soft grey shadow that read as
scan noise. In v3 it is a hard, straight, opaque black rule running 1,160 px across the map — it
reads exactly like a printed frame rule cutting through the city, which is the specific defect the
user objects to in the "other" mosaic.

Related (borders on Reviewer 3's scope, flagged here because it is new and it is black): v3's newly
retained top margin for unit 3 at canvas y≈4800, x≈8880–10720 also carries a solid black scanner bar
inside the map's visual field (`113_sheet3_topmargin_v3.png`). It faces a genuine coverage gap, so it
is not a seam violation, but it is new in v3 and it is not "frame + paper".

---

## 7. Registry corrections (imagery beats the pair list)

- The registry lists a horizontal seam at 25th as "(10,4 area)". Units 10 (D–G/23–26) and 4 (G–H/25–28)
  only touch at a corner; the actual 25th seam over avenues G–H is **11a | 4**, and that is what I walked.
- The vertical Avenue G seam listed as "(13,4) 26-28" is confirmed, but note that the Avenue G cut
  between units 10 and 11a sits at canvas x = 11943 (exactly the consensus Avenue G line), not at the
  offsets my first tone-step search returned; the tone-step method is unusable here because v3's white
  balance left several sheet pairs nearly tone-matched. Cut positions in this report were established
  from the v3/v2 difference boundary, which is unambiguous.

---

## What would clear the FAIL

1. Cap the 19th St cut at unit 7's mapped print extent so the scanner black bar at y 7622–7648,
   x 5292–6452 is excluded (and restore the ~25 px of unit 7 block-face rows it covers).
2. While there: the disclosed backing-white band in the same corridor should not have widened
   49 → 69 rows.
3. Optional but valuable, and the actual point of the v3 glyph-aware change: the "AV. H OR WILLIAMS"
   label at 23rd–24th is sliced by the 69 px Avenue H gutter even though sheet 11 carries it intact on
   continuous paper. Closing that gutter (or pulling one panel's clip across it) would recover the
   one genuinely broken street-name label in the composite.

---

VERDICT: FAIL

- **NEW REGRESSION (the reason for FAIL):** a solid black scanner-edge rule, 1,160 px long and up to
  30 px thick (canvas y 7622–7648, x 5292–6452), is pasted across the 19th St corridor over unit 7's
  map content; solid-black in that corridor rose 5.5x–40x vs v2 and 18,110 px of former map ink/colour
  are now covered. This is exactly the print-extent-cap failure mode item 6 was written to catch.
- **The headline fix is not observable.** At the specified site (v3 canvas 11878, 20272) v3 is
  pixel-identical to v2 (max diff 5/255), and no seam cut anywhere in the composite moved measurably
  between v2 and v3 — so "glyph-aware seam cuts" changed nothing that I can detect.
- **Label integrity is otherwise good but one label is still broken:** all nine street/avenue-name
  labels in the seam corridors are complete and un-ghosted, except "AV. H OR WILLIAMS", whose top ~57%
  is removed by the Avenue H gutter — pre-existing, and recoverable (sheet 11 has it intact on
  continuous paper).
- **No new duplicates or ghosts.** 17 near-duplicate display-text pairs in v3 vs 17 in v2; the doubled
  "25TH ST. OR BATH AV." at 25th x G–H is full-strength original print from sheets 11 and 4 and is
  identical to v2.
- **Continuity, Avenue H, and the 27th jog all pass.** All 38 seam endpoints within ±5 px of v2 (two
  improved); target Avenue E x 22nd pixel-identical (max diff 5/255); Avenue H gutter 68 px and the
  corridor byte-identical to v2 with zero solid black; 27th jog +112 px vs v2's +107 px, still under
  the disclosed ~124 px.
