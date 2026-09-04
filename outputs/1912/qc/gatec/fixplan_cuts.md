# Gate C fix plan — cut placement, furniture and ownership

Opus developer, Gate C. **Dry run only.** No tool was run with `--apply`; nothing under
`outputs/1912/recipe/` was written. Every simulated build was made from a scratch copy of the
recipe (`$S/recipe`, `Recipe.dir` repointed in memory, `units.json` patched in memory) exactly as
`qc/wave4/proposal_cuts.md` did, and rendered with `qcrender.render(..., d=1)` from a scratch
ownership document. `$S` =
`/tmp/claude-0/-home-user-claude-code/667180c2-8c6a-5c7c-8f63-764f5714e1d7/scratchpad/gc`.

Three code commits, all **default off** (`tools/streetcut.py`, `tools/fillgaps.py`) or QC-only
(`tools/seamcrops.py`); with no flags both pipeline tools reproduce the accepted build byte for
byte — checked against `recipe/seams/ownership_streetcut.json` and, after a simulated
`fillgaps --apply`, against `recipe/seams/ownership_city.json` (`regions` and `gap_fill` both
identical).

Baseline for every "before" below is the shipped Gate-C build: `streetcut --band-furniture-free
--min-band-span 2000` → `fillgaps` (HQ-54).

---

## 1. What the Gate C seams have in common

**(A) The candidate sort minimises the wrong quantity.** `dp_cut` scores a candidate by `visible`
— the ink the band still SHOWS after the cut — and takes the *least*. That is right only for
content **both** plates draw: the least-visible candidate is the one that hides one of two copies
of a street name, which is what the side rule was written for (57|58, 76|84). Where a feature is
drawn by **one** plate the same sort erases the only copy there is. Measured on the shipped build:

| seam | chosen candidate erases | best candidate erases | longest erasure run |
|---|---|---|---|
| 63\|71 | 129,481 grey-levels over a **468 px** run | 128,883 over 96 px | 63's 10" main, 81 ft |
| 64\|72 | 68,773 | **47,311** (+120, south of both mains) | the 8" main, east 850 px |
| 48\|99a | 184,295 | **9,135** (−97.8) | 20 ft |
| 5a\|6 | 900,131 over a **1,484 px** run | 471,211 over 748 px | plate 6's track yard |
| 5a\|9 | 199,356 | 103,208 | the "Slip" lettering cluster |

So each candidate now also reports the **unique ink it erases** (ink one plate draws that the
other does not draw within 44 px — 7.6 ft, wider than the largest same-feature registration split
measured) and the **longest continuous run** of the seam over which it does so, which separates a
deleted water main from a diffuse tone or margin difference.

**(B) A candidate can be read as infeasible because of the overlap lens's tips.** A path is
charged `BIG` for every cell it spends off the band; at the two tips the band tapers to nothing
and the DP, which may step only one cell across per cell along, cannot follow it in. Two or three
tip cells then condemn a candidate whose corridor is open along its whole length. That is exactly
why the south side at 64|72 — the side that keeps the main — scored `crossed 1.01e7` in
`proposal_cuts.md` §0 and never competed; with the tip cells counted separately it scores
**118,460, the lowest of the three**.

**(C) Several Gate C "cut" defects are not cuts at all.** 25|25b's duplicate `80'` is a panel
region boundary; 48|99a's white gash is a plate-48 extent that stops 93 px short of 99a's paper;
56|57's sliver is two `cut:true` furniture boxes overlapping; 63|70's patch is plate 70's own
title block; edge_18's tongue is created by `fillgaps`, not by `streetcut`. Each is stated as the
exact recipe edit below.

---

## 2. Production flag set for the next `streetcut --apply`

```bash
python3 tools/streetcut.py --year 1912 \
        --band-furniture-free --min-band-span 2000 \
        --erasure-guard --panel-centre --apply
python3 tools/fillgaps.py --year 1912 --apply
```

* `--band-furniture-free --min-band-span 2000` — unchanged, already in production (HQ-54).
* `--erasure-guard` — **new.** Leaves the existing choice alone unless it erases materially more
  of the map than an alternative: 50 ft (290 px) more of a continuous feature, or 30 % more unique
  ink in total with at least 20,000 grey-levels of difference, and never for a candidate that is
  worse on the other measure. Alternatives include candidates that only looked infeasible because
  of (B). **Fires on 40 of 203 min-ink seams** (list in §5).
* `--panel-centre` — existing flag, previously left off (HQ-54). Needed for 20|20b; moves 3 panel
  seams (20|20b, 25|25b, 48|48b).

**Not recommended, measured and rejected:**

| flag | measured | verdict |
|---|---|---|
| `--dup-avoid 2.0` | threading cost on the chosen 54\|54b path 1,256 → 0, on 71\|78 2,041 → 61; **paths move ≤ a few px, 70 seams jag, no defect removed** — `54_54b_{before,after}.jpg` are visually identical | keep off; the term is real but nothing in this Gate C set is fixed by it |
| `--min-lost-ink` (scale-free form of the guard) | 91 of 203 seams move, including 76\|84, one of the two pairs the side rule was written for | diagnostic only |
| `--avoid-in-choice`, `--lost-ink W` | rank on the augmented cost `--line-avoid` never reached (that is why HQ-54 measured it moving 97 paths and flipping no candidate); blast radius similar to `--min-lost-ink` | diagnostic only |
| `--side-pinch-relief` alone | 60 seams move: it un-blocks side candidates and the *old* "take any feasible side" rule then takes them | do not ship alone; the guard uses the same measurement internally |
| `--pick-best`, `--panel-clamp`, `--blank-band` | unchanged from HQ-54 | off |

---

## 3. Recipe edits, exactly

### 3.1 `outputs/1912/recipe/units.json`

```jsonc
// unit "20" — removes the duplicated "AVENUE L." beside the inset's own copy.
// Evidence: plate 20's native columns 3232-3271 hold only the "L." of its vertical
// AVENUE L. and no border rule; the block-face address run 802-822 sits at native
// x 3197-3218 and is KEPT, as is the "70'" note; verified in the render.
"extent": [86, 91, 3271, 3804]   ->   [86, 91, 3232, 3804]

// unit "25b" — releases the strip carrying the redundant "80'" 12th St tick to plate 32,
// which maps the ground (32 spans mosaic x 21114-27558) and carries the surviving tick at
// mosaic 22465. Native 3170 = mosaic 22155, immediately west of 25b's own tick.
// Ink evidence (the profile proposal_cuts.md still owed): parent-scan columns 3170-3266,
// rows 83-1138 carry dark fraction 0.043-0.080 - the clipped SEA WALL BLVD / GULF OF
// MEXICO band, the "ST." + "80'" tick, and the adjoining numerals "0" and "32". All of it
// is either duplicated by plate 32 or edge furniture; no block face or building is released.
"region_native": [[2580,83],[3266,83],[3266,1138],[2580,1138]]
              -> [[2580,83],[3170,83],[3170,1138],[2580,1138]]
"extent": [2580, 83, 3266, 1138]   ->   [2580, 83, 3170, 1138]

// unit "48" — closes most of the 47k px2 white gash on the 48|99a seam. It is NOT a cut
// fault: over mosaic x 43400-44050 plate 48's footprint bottom is y 24935 and plate 99a's
// polygon does not begin until y 25028, and no third plate covers the 93 px between.
// Evidence: u48 native rows 3813-3843 hold map ink (two diagonal track lines running to
// the paper edge, dark fraction 0.013-0.015, the same as the rows above) and no printed
// neatline; the archival ruler strip starts at row 3855 (5th percentile over the sheet's
// width), so 3840 is inside the paper everywhere.
"extent": [90, 93, 3232, 3813]   ->   [90, 93, 3232, 3840]

// unit "56", furniture_native[1] ("scale bar") — closes the 56|57 sliver, which is the
// intersection of two cut:true boxes' 6 px grows: 56's scale bar (grown east edge mosaic
// 15013.2) and unit 62's title (grown west edge 14996.8). Neither plate paints the 17 px
// between. Evidence: 56's own scale-bar ink ends at native x 3012 (dark 0.022 at 3010,
// 0.000 from 3015); the box was 9 px of blank margin too wide.
"box": [2374, 3669, 3021, 3778]   ->   [2374, 3669, 3012, 3778]
```

### 3.2 New control `outputs/1912/recipe/controls/pair_3_4_y.json`

The 3|4 pair is `how:"midpoint"`, `corridor:null`, and its min-ink path had run to the DP_HALF
band edge and stuck there as a straight line at mosaic y = 25305, slicing the coal-pocket track
group and the compress property line. Giving the pair the 33rd St corridor — the tie
`wharfplace.py` places sheet 3 from — moves the seam coordinate 1,304 px (225 ft) north to
24320.95 and **moves no other seam** (`cutdiff`: 1 of 203).

```json
{
 "pair": [3, 4],
 "axis": "street",
 "observer": "gate-C cut fix-plan",
 "method": "the tie tools/wharfplace.py places sheet 3 from, read as a seam corridor: 33rd St, the one street both wharf sheets draw",
 "corridor": "33rd St",
 "a_native": 235.0,
 "b_native": 3005.0,
 "status": "ACCEPTED"
}
```

(The sheet-3/sheet-4 shear itself is another agent's registration item; this is the cut only.)

---

## 4. Seam by seam

Crops are 1:1, `outputs/1912/qc/gatec/verify/<seam>_{before,after}.jpg`; "after" is the full
recommended configuration of §2 + §3 (`$S/city_final.json`).

| seam | cause | fix | verified |
|---|---|---|---|
| **64\|72** | the band cut ran north of both plates' copies of the 8" main; east of mosaic 25900 plate 72 draws nothing (0.00-0.02 dark) and plate 64 draws the main at y 24570-24578, so 260 ft of it was owned by the plate that does not draw it | `--erasure-guard` (off −120 → +120, erasure 68,773 → 47,311) | **yes** — after: `80' 8" W. PIPE` and its dash run continuous across the whole seam, plate 64's east label restored where the band was blank. Cost, stated plainly: the *west* label is now clipped to `8" W. P.` where before it was whole. Net content gained. |
| **63\|71** | the chosen side ran along plate 63's 10" main and erased it over a 468 px run (71 draws nothing there) | `--erasure-guard` (off −120 → +120, run 468 → 96 px) | **yes** — after: `10" W. PIPE` + `80'` and the dash run print in the middle-east of the band where before it was blank grey; nothing else in the 5,000 px window changed |
| **48\|99a** | not the cut: a 93 px strip of ground between plate 48's extent bottom and plate 99a's polygon that no plate's footprint covers | `units.json` unit 48 `extent[3]` 3813 → 3840 (+ the guard moves the cut off +97.8 → −97.8, erasure 184,295 → 9,135) | **partly** — the white gash narrows from ~90 px to ~15 px; the residue is a genuine source gap (both papers end) and is now under the tiling audit's reporting floor |
| **25\|25b** | ownership, not cut: 25b's panel region reached 96 px east of its own `80'` tick, over ground plate 32 maps and letters | `units.json` unit 25b `region_native`/`extent` east edge 3266 → 3170 | **yes** — before: two `80'` ticks; after: one `80'` and plate 32's complete `12TH ST.` |
| **20\|20b** | plate 20's east extent reached past its own vertical `AVENUE L.`, beside the inset's complete copy; no cut can separate copies 136 px apart in a 243 px band (the west-clamped path is infeasible, `crossed` 9.1e8 = 91 off-band cells, confirmed again here) | `--panel-centre` (cut moves 109 px west) + `units.json` unit 20 `extent[2]` 3271 → 3232 | **yes** — before: `AVENUE L.` twice side by side and a mangled adjoining numeral; after: one `AVENUE L.`, a clean `20`, address runs 806-822 / 805-823 and the `70'` note all intact |
| **56\|57** | two `cut:true` furniture boxes on adjoining plates (56's scale bar, 62's title) whose 6 px grows overlap by 17 px; each plate cuts the ground on the assumption the other supplies it | `units.json` unit 56 `furniture_native[1].box` east edge 3021 → 3012 | **yes** — the 14 px white sliver becomes a 1-2 px hairline (below the 2,500 px² audit floor). The same signature is worth testing at the other hairlines listed in `tiling_audit.json`. |
| **3\|4** | `how:"midpoint"`, path pegged at DP_HALF as a straight line at y 25305 through the pier-33/35 slip edge and the Fowler & McVitie coal-pocket track group | new control `pair_3_4_y.json` (33rd St) | **yes** — after: the track group, the slip edge and the property lines run unbroken through the whole 1,500 × 1,400 window and two structures previously buried under the far plate's paper are back; no other seam moves |
| **5a\|9** | the path threaded the "Slip" lettering cluster and left three clipped fragments | `--erasure-guard` (off 0 → +120, erasure 199,356 → 103,208) | **yes** — before: `ip` / `slip` / `Sli`, three truncated copies; after: two whole labels, no clipped glyph, cut clear of the cluster (crop x 680-920, y 1520-2260 of `seam_5a_9_100.jpg`) |
| **5a\|6** (edge_08) | plate 5a's blank torn top margin owns ground plate 6 draws | `--erasure-guard` (off 0 → −120) | **partly, and it needs a grader's eye.** The crop is much better: the 6" W. PIPE dash run and its label print continuously where an unbroken 100 ft blank strip was. But re-running the round-2 reviewer's own test ("5a ink < 0.003 and 6 ink > 0.02", 20 px sampling over mosaic −14000..−9000 × −15400..−14300) gives 914,000 px² before and **1,038,000 px² after**: the guard hands 5a *more* of the band, partly because the deckle **shadow** reads as ink in the erasure measure. The finding still needs the coverage edit — a local notch in unit 5a's `region_native` top edge where its paper is torn — which I did not derive; 5a's top rows are not blank across the sheet (dark 0.03-0.17 from row 80), so it cannot be done with a straight edge and needs its own ink pass. |
| **63\|70** | **not cut placement, not solved.** The patch printed in 33rd St is plate **70's own title block** — `GALVESTON TEXAS.` + the numeral `70` — kept by HQ-53's cycle rule as the smallest of the three-box cycle. On plate 70's own sheet that title is drawn **over** the roadway (its own 10" dashes and `80'` tick run under it), so keeping it necessarily buries the main and orphans one `80' 10" W. PIPE`. Keeping either alternative is worse, measured: neighbours' ink under 63[1] 17.5/11.2 over 248,100 px², under 70[0] 1.9/19.7 over 95,690 px², under 71[0] 11.2/22.6 over 112,932 px² — the cycle's choice is already the least damaging. Trimming the kept box to its ink does not help either: 70's title ink runs native x 3025-3246, *wider* than the box. | two options for the orchestrator: (a) accept and document as a three-plate furniture collision in 33rd St, the same class as master-kept furniture; (b) implement `furncover` coverage against `ownership_city.json` regions after `streetcut` — but note (b) alone will not remove this patch, because 70[0] still wins the keep test | **no** — before/after crops identical by design (the guard deliberately does not move 63\|70: its alternative is worse on the run measure, 216 → 520 px) |
| **71\|78** | diagnosed, **not fixed**. The seam coordinate (lattice, y 31453.3) sits ~130 px north of the roadway centre (block faces at y ≈ 31490 and 31680), so the `DP_SIDE = 120` side target lands *on* the `36TH ST.` lettering at y 31550-31610, and the north side is genuinely blocked (182 off-band cells, far past the tip-pinch allowance). `--dup-avoid` up to W=10 drops the threading cost 2,041 → 61 without moving the path. | proposed rule, not implemented: reference the side targets to the **overlap band's own centre** rather than to the control/lattice coordinate, so a side path lands inside a block face and not on the centre lettering | **no** — the orphan `H` beside `36TH` is unchanged |
| **54\|54b** (edge_48) | third `T.H.` manhole in the 24th St junction; a registration split of one symbol, 12 ft on the labels | `--dup-avoid` tested at W = 0, 2, 8: the chosen candidate and its path are unchanged (crops byte-comparable) | **no** — confirms `proposal_cuts.md`: this needs a junction term (forbid the path from crossing the cross-street box other than on one monotone segment), not a duplicate term |
| **24\|31** | the `70'` numeral is crossed by a **straight corner cut** (`kind:"corner"`, `cut:"straight"`, overlap only 12,170 px², span 174 px), so no DP candidate exists to move: `dp_cut` never runs | not fixable by any cut flag at this overlap size. Either promote it with a much smaller `--min-band-span` (a 174 px span is a corner contact by any measure — not recommended) or accept the clipped numeral, which plate 31 draws complete 90 px away | **no** — diagnosed only |
| **26\|38** | same class: `corner`/`straight`, overlap 131,505 px², span 286 px. The 12 × 26 px notch of canvas is smaller than `tiling_audit`'s 2,500 px² floor | `fillgaps` cannot see it either (`MIN_AREA` = 2,500 px²). Recommend lowering the tiling-audit reporting floor rather than a cut change; both plates draw blank roadway there, so either owner is authentic | **no** — diagnosed only |
| **edge_18 / 15\|4** | **not a `streetcut` fault.** Plate 15 loses the strip to plate 3 (the 3\|15 pair is a straight half-plane at the overlap midpoint x = −7844.6), plate 3 loses the same ground to plate 4 (3\|4 midpoint cut) — a three-way loss that leaves 913,775 px² unclaimed (bounds x −9147..−7844, y 23737..24584). `fillgaps` then hands the whole hole to plate 4 because 4's paper covers 100 % of it and 4's region touches it. | `--prefer-ink` is implemented and available, but **it does not move this hole**: measured ink per sample over the hole is plate 3 = 3.69, plate 4 = 1.36, plate 15 = 1.35, and plate 3's region does not touch it. Recommended instead: give 3\|15 a cut that does not hand 15's drawn ground to a plate that will not keep it (the pair is `corner`/`straight` on the overlap midpoint), or accept the new `pair_3_4_y` control first and re-measure — the 3\|4 coordinate moves 225 ft in this build and this hole is on that seam's ground | **no** — reported with measurements |
| **4\|13** (edge_14) | the `CONVEYER RAISED 40'` gallery doubles by 5-7 ft | the guard moves 4\|13 (off 0 → +120, erasure 195,027 → 48,755, run 432 → 52 px). It is a drawn-size difference between a wharf sheet and a city plate, under the 20 ft bar; no cut move puts the whole gallery on one plate cheaply | leave and record, as instructed |
| 64\|71, 17\|21, 4\|5b | registration residuals already adjudicated (HQ-50, `proposal_20b_25_17_21.md`, `proposal_4_wharf.md`) | out of scope here — no transform or control change proposed | n/a |

---

## 5. Blast radius and the re-grade set

`cutdiff --min-move 30` from the shipped build to the recommended configuration:

* **44 of 203 shared seams move more than 30 px**; one pair (25b|31) is newly cut on a min-ink
  path because of the 25b region edit.
* The erasure guard accounts for 40 of them:
  `4|13 5a|5b 5a|6 5a|9 5b|9 6|21 14|55 16|67 17|21 31|32 47|54b 48|74 48|99a 53|59 59|65 62|70
  63|71 64|72 65|73 66|73 68|76 70|77 70|78 71|72 73|80 74|82 74|99a 76|77 76|83 78|86 80|88
  81|89 82|89 82|90 83|84 85|86 92|93 93|93b 94|95 96|97`
* `--panel-centre` accounts for 20|20b, 25|25b, 48|48b; the new control for 3|4; the units edits
  for 25b|31, 25b|32 and the 48/56 boundaries.
* Every guard firing is recorded on its seam row in the ownership document as
  `"erasure_guard": {"from_off", "to_off", "lost_before", "lost_after", "run_before_px",
  "run_after_px"}`, so the re-grade set is machine-readable from the build itself.

Geometry after the recommended run (`streetcut` stage): **106 regions, 1 piece, overlap 8 px²,
union 4,513,103,224 px²** (baseline: 1 piece, overlap 8 px², union 4,513,636,374 px²); after the
simulated `fillgaps`, 144 gaps assigned and **8** true source gaps (baseline 141 / 9).

**These 45 seams must be re-graded before the build ships.** The guard trades one kind of damage
for another in at least one case (64|72's west label is clipped where it was whole), and 5a|6 is
better in the crop but worse on the reviewer's own area test, so a grader — not this measurement —
must sign each one off.

---

## 6. Code commits

| commit | file | what |
|---|---|---|
| `ec0b192` | `tools/seamcrops.py` | **the QC bug the 3\|4 adjudicator found.** The red tick was drawn at `s["coord"]`; a min-ink path wanders up to `DP_HALF` = 320 px (55 ft) from it, so on 3\|4 the tick pointed 320 px away from the straight cut at y = 25305 and two graders read the crop without ever seeing the cut. The tick now follows the **actual ownership boundary** at each end of the crop (sampled from the buffered intersection of the two regions, which lies on the cut wherever it runs); where that differs from the coordinate by more than 8 px the coordinate is kept beside it as a thin blue tick. Verified on 3\|4 (rendered to a scratch tree, the shipped crops untouched): the red tick lands at mosaic y = 25,303, the straight cut the adjudicator measured, and the thin blue tick at 25,625, the seam's coordinate 320 px away. No map pixel changes. |
| `acc8a23` | `tools/streetcut.py` | `--erasure-guard`, plus the measurements it needs (unique ink erased, longest erasure run, off-band cell count) and three further default-off terms: `--dup-avoid` / `--dup-avoid-k` (threading between two plates' copies of one feature), `--avoid-in-choice` and `--lost-ink` / `--min-lost-ink` (rank candidates on the augmented cost `--line-avoid` never reached), `--side-pinch-relief`. Every candidate's `threaded`, `lost_unique`, `lost_run_px` and `off_band_cells` are written to `--cand-dump`. Defaults reproduce `recipe/seams/ownership_streetcut.json` byte for byte. |
| `2a05e35` | `tools/fillgaps.py` | `--prefer-ink`: rank the plates that can supply a gap by what they actually **draw** in it (measured against each plate's own paper tone), not by how much paper covers it, and never hand a gap larger than `INK_SPLIT_AREA` to one plate whole. The measured ink is recorded on each gap's row. Default off; without the flag the tool reproduces `recipe/seams/ownership_city.json` exactly. |

## 7. Files

* Verification crops: `outputs/1912/qc/gatec/verify/*_{before,after}.jpg` (12 pairs, 1:1, ≤ 1500 px).
* Scratch builds (not committed): `$S/own_final.json`, `$S/city_final.json`, `$S/cuts_final.json`,
  `$S/cand_g.json` (candidate table with the new columns), `$S/moved_final.json` (the changed-seam
  set), `$S/recipe/controls/pair_3_4_y.json`, `$S/edits2.json` (the `units.json` patch as applied
  in memory).
