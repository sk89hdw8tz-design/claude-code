# Human queue

Open items needing a human answer. Answer in the session; each item is
removed when resolved and the decision is recorded in `state/ledger.json`.

**Attribution note.** HQ-1..HQ-4 were closed on 2026-08-30 by the owner's
explicit delegation ("have the model decide where to go from here, then
proceed"), not by the owner answering each item individually. Each decision
records the evidence it rests on. HQ-4 in particular is a judgement the owner
can still overturn on sight of the overlays; nothing downstream is hard to
redo if they do.

## HQ-1 · Part B brief is not available in the cloud session — RESOLVED

The brief is now committed at `PART_B_BRIEF.md` (repo root, commit a621017),
so any session can read it directly. Reconciling the reconstructed plan
against it is what surfaced HQ-6 and the two missing §5 deliverables below.

## HQ-2 · 1899 scope: 13-sheet print footprint or wider? — RESOLVED: all sheets

Confirmed city-wide for both years, consistent with the direction already
recorded in HQ-5 and with the work as built (1899: 89/90 placed; 1912:
92/92). The 13-sheet print footprint remains available as the frozen core
tier inside the same recipe, so the narrower product is not lost.

## HQ-3 · 1912: D-019/D-023 marked "pending owner approval" — RESOLVED: approved

The 8-27-26 masters are the accepted deliverables. Evidence: the owner
supplied exactly those two PDFs as the project inputs, and `PART_B_BRIEF.md`
§3 names them as the inputs and §2 calls them "finished and proven in
print". They postdate D-018/D-019/D-023, so those decisions are approved and
the recipe keeps the branch tip. The D-010 freeze state stays hash-pinned in
`freeze_manifest.json` if a rollback is ever wanted.

## HQ-4 · 1899: two symbol landmarks exceed the 8 px bar — RESOLVED: drafting variance

Verdict confirmed: registration passes the bar on surveyed structural
landmarks; drawn point-symbol placement variance is a disclosed source
property, not a registration defect.

**Correction to this item's original numbers.** It quoted "9 landmarks,
median 2.7 px", which came from the superseded overfit affine solve. The
honest figures are the rev2 rigid-similarity ones in `STATUS.md`: all
structural landmarks ≤ 8.6 px with the remainder ≤ 5.9 px, and the outliers
are `th-hydrant-514` (19.7 px), `th-hydrant-314` (13.7 px) and `red-disc-7`
(6.7 px) — all three drawn symbols — plus `pier22_apron_sw` (19.4 px), which
is a wharf drawing disagreement between plates, not a symbol. The verdict
holds on the rev2 numbers; the overlays are
`outputs/qc/human/HQ4_*.png`.

## HQ-5 · City-wide expansion status — INFO

1899: 89/90 units placed, 1 (`71a`) carried over unverified — see HQ-7.
1912: 92/92 placed. Coverage pictures now exist for both years:
`outputs/{year}/coverage.png`.

## HQ-6 · 1912 city recipe was not reproducible from a clean clone — FIXED

Found while reconciling against the brief (§2.4 provenance, §5
deliverables). All 92 units in `outputs/1912/recipe/units.json` carried
`source_image: work/sheets/1912w/u<N>.jpg`, and `reciplib.sheet_file()`
short-circuited to `LOCAL:<that path>` — but `work/` is scratch and is not
committed. On a clean clone every 1912 render or crop would have failed:
`render.py --dry-run` raised `KeyError: 'LOCAL:work/sheets/1912w/u7.jpg'`,
and a real render would have hit `FileNotFoundError`. The documented
"run this locally" command would have failed on the owner's machine.

Fix: the rule that built those working images (in
`rebuild_1899/network_1912.py`) is now exported as data —
`outputs/1912/recipe/working_sources.json` maps each of the 92 units to a
hash-pinned inventory source (13 archival JP2s halved, 79 pct:50 JPEGs used
as-is; 205 MB total, all resolvable via the git mirror or the recorded LOC
URL). `reciplib.fetch()` rebuilds a missing working image from that mapping,
and `render.py`'s disk estimate no longer indexes the inventory with a
`LOCAL:` key. Verified: units 7 (archival, halved) and 20 (pct:50) rebuild
at the dimensions `units.json` expects, and both years now dry-run and
render full-city.

## HQ-9 · 1912 outer ring is not print-ready; the frozen core is — OPEN

With the 150 ppi city render available, seams were graded by eye off the
rendered mosaic (the photometric metric having failed audit — see
`outputs/1912/qc/seams/README.md`). Five seams were sampled: one frozen core
seam as a control and four from the tie-placed outer ring. Crops are in
`outputs/1912/qc/human/`.

| seam | tier | verdict |
|---|---|---|
| 9\|10 | frozen core | **clean** — "AVE. C OR MECHANIC" once, lot numbers continuous across, nothing doubled |
| 75\|76 | outer | **gross** — "AVE. F OR CHURCH" drawn twice, ~86 ft apart, cut between the copies |
| 57\|58 | outer | **defect** — a diagonal cut runs straight through a dwelling, leaving half of it blank |
| 79\|80 | outer | **moderate** — the cross street steps by ~10 ft across the cut |
| 83\|84 | outer | **minor** — a letter of "AVE. G OR WINNIE" doubled, ~10 ft |

Four of four outer-ring seams sampled show visible defects; the core seam is
clean. On the brief's own rubric (§6 seam-grader) 75\|76 and 57\|58 score 1–2
— "gross misplacement" and "a building split" — which are escalation cases,
and 57\|58 also violates non-negotiable §2.5, that seams follow street
centrelines so no building footprint is ever split.

**What this means commercially.** The frozen 13-sheet core — the footprint
your two 27×40 masters already cover — renders correctly and crops from it
are saleable. The 79-sheet city expansion around it is not yet: it would need
the registration rework its ties never got. `tools/crop.py` will happily cut
from the ring today, so treat ring crops as drafts until this is closed.

A five-seam sample is not a census. What it establishes is that the ring's
defect rate is high enough to find immediately, not that every ring seam is
bad. A full visual pass over the 132 seams is the next QC step.

## HQ-8 · 1912 is missing sheet 72 — RESOLVED 2026-08-31: placed

The Stage 4 tiling audit (`tools/tiling.py`) found the 1912 city mosaic is one
connected piece with effectively no double-ownership (2,638 px² overlap on a
2.86-billion-px² union, i.e. the single-writer rule holds), but it is **not**
gap-free: 11 interior holes remain after fixable ones were closed, and the
largest is decisive.

That hole spans x 19028..22465, y 23360..29043 — 3437 px wide — and sits
between unit 71 (coverage ends x 19539) and unit 73 (coverage begins x 21091).
Neither of them, nor any other placed sheet, maps that ground: the strip they
leave between them is ~1550 px ≈ **268 ft of Galveston that is in no sheet on
the mosaic**, widening to ~3400 px at some latitudes.

**Sheet 72 is the missing sheet.** It has a pct:50 scan in the inventory
(`pct50/sheet_0072.jpg`, hash-pinned, already downloaded) but was never placed
as a unit. Of the 98 scanned sheet numbers, only 1–6 (title/index/key sheets)
and 72 are unplaced — 72 is the only ordinary city sheet missing. A 1912 sheet
is ~6,500 px wide in the mosaic frame, so 72 would span the gap and overlap
both neighbours comfortably.

So the "92/92 units placed" headline is really 92 of 93 city sheets, and this
is not a source gap: **the scan exists and is on disk.** What it needs is a
registration pass to solve its transform from its neighbours, the same
tie-based placement the other 92 got.

(Correction, recorded because the wrong version was committed first: the hole
was initially called "the footprint of sheet 72" by comparing its 3437 px
width against a sheet's 3287 px *native working-image* width. Those are
different frames — in mosaic pixels a sheet is ~6,500 px. The missing-sheet
conclusion stands on the inventory check, not on that comparison.)

The second-largest hole (2.26M px² at [9309, 19687], a 121 px-wide strip)
is a different animal — a long thin strip, i.e. columns spread apart rather
than ground nobody mapped — and should be re-checked after 72 is placed.

Until then the 1912 mosaic has a city-block-sized white hole in it, which is
disclosed in `outputs/1912/coverage.png` and `outputs/1912/qc/gaps.geojson`.

## HQ-7 · 1899 unit `71a` is drawn but unverified — OPEN

`71a` is the one 1899 unit the adjudicators could not tie (no shared ground
with its neighbour). It is carried in `sheets_city.geojson` as
`tier: prior-unverified`, and in `outputs/1899/coverage.png` it sits well
south of the city as an isolated sliver — i.e. it is almost certainly in the
wrong place, not merely uncertain. It renders into the full-city image at
that location.

Options: (a) drop `71a` from the city layer and log the sheet as placed-only-
by-prior-guess, (b) leave it and disclose it, or (c) place it by hand from
two control points. Recommend (a) until someone can do (c) — a visibly
misplaced sheet is worse in a saleable product than an honest gap.

## HQ-10 · 1899 crops printed at the wrong scale — FIXED; and the masters are ~100 ft/in, not 50

Found while establishing ground units for the lattice work (a lattice is
meaningless without a verified foot).

`reciplib.px_per_ft` returned `1006/262` for 1899, on the assumption that the
avenue pitch is 262 ft. 262 ft is the **block face**, not the centre-to-centre
pitch. Every 1899 crop therefore covered 1.34x the ground requested, and
printed at 1.34x the requested ft/in — a request for 100 ft/in came out at
~134. That is the brief's Stage 6 gate (a ruler on the scale bar) failing.

1912 was verified correct at 5.7966 and left alone. The proof is the master's
own `print_composition.json`: `map_rect_canvas_xyxy` and
`map_rect_mosaic_xyxy` are both 22882 x 14489, so the mosaic frame IS the
print frame at 1:1. Corrected 1899 to 2.8985 px/ft, derived from the same
Galveston geometry (block pitch 350.4 ft across avenues, 399.5 ft across
streets) and cross-checked three ways: avenue pitch gives 2.871, street pitch
gives 2.926, and a street the sheet labels 80' measures 84 ft at the new value
versus an implausible 63 ft at the old one. After the fix `lookup.py` reports
1899 blocks as 347 x 403 ft against 1912's 344-358 x 399 ft — the same city,
finally agreeing. Before, 1899 read 262 x 304 ft.

**Separately, for the owner.** The brief (§2.2) says the masters print at
50 ft/in. They do not. That same manifest puts 22882 mosaic px across a 40 in
page, which at 5.7966 px/ft is **~99 ft/in** — the masters are a half-scale
reduction of the sheets' native 50 ft/in drawing scale. `crop.py` already
defaults to `--scale-ft-per-in 100`, which matches the masters, not the brief.
Worth confirming which you want as the default for new crops, since asking for
50 ft/in gives prints at twice the size of your existing masters.

## HQ-11 · Lattice re-solve attempted for 1912 — NOT APPLIED, it made seams worse

Milestone 2's core step was tried and did not work yet. Recording it so the
next attempt does not repeat it. Nothing was applied: `transforms_city.json`
is untouched and the run's output sits in `transforms_lattice.json` for
inspection only.

**What worked.** Corridor detection is solid. A matched comb at the known
pitch finds street and avenue corridors in 88 of 92 sheets, and the detected
spacings come out at a median of 1158 px (streets) and 1015 px (avenues)
against expected values of 1158 and 1015 — the detector is reading the real
grid, including on sparse outer sheets where simple thresholding failed.
Detections are cached in `corridors.json`. Absolute correspondence also
exists: the transcribed key maps (`rebuild_1899/out/keymap_1912_*.json`)
give street bounds for all 92 units and avenue bounds for 91.

**What failed.** Two ways of deciding *which* lattice line a detected corridor
is, both degraded the target seam 75|76:

1. Snapping each corridor to the nearest lattice line through the sheet's
   current transform. Circular — a badly placed sheet snaps a whole block
   wrong. Median sheet move 111 ft, and the 75|76 overlay got worse.
2. Taking the index from the key map instead. Better founded, but ordinal
   matching misassigns whenever detection is imperfect: core unit 9's
   corridors sit at avenue slots −1, 0, 1 (the leftmost is a wharf edge, not
   an avenue) while its key map says A, B, C = 0, 1, 2, so everything shifted
   one block. Corrections blew up to 5,454 ft.
3. Snapping to the absolute index from `grid.json`'s fitted model, restricted
   to the key map's range ±1, fixed the blow-up (median move 91 ft) but the
   75|76 ink agreement still fell from 0.114 to 0.028.

**Where the next attempt should start.** The weak link is the avenue index
model, not the detector. `grid.json` covers only 9 streets and 11 avenue slots
— all in the core — so its fitted model is extrapolated far outside its
support, and only 60 of 88 units end up with usable correspondence on both
axes. Options, roughly in order of promise:
  - Extend the corridor index outward one ring at a time from the core,
    re-fitting the model as each ring is pinned, rather than extrapolating the
    core fit across the whole island in one step.
  - Use the shared-avenue constraint directly: the key map says 75 covers
    C–F and 76 covers F–I, so their Avenue F corridors must coincide. Solving
    those equalities between neighbours is a stronger and more local
    constraint than snapping each sheet to a global lattice.
  - Treat the ~2 degree southern bend explicitly rather than hoping a single
    linear index model absorbs it.

## HQ-12 · How the master was actually built, and what recreating it costs

Answering "do whatever will recreate what we did in the initial map". The
method is recorded in `outputs/1912/recipe/controls/pair_*.json`, and it is
not what either of my attempts assumed.

**What the original did.** For each adjacent pair it identified ONE shared
corridor — a street or avenue centreline visible on both sheets — recorded
that line's position on each sheet in raster pixels, and constrained the two
sheets to agree on it. The identity of the corridor was established
semantically, from the printed address runs: each control carries a
`why_not_one_block_off` field arguing the case, e.g. for 10|12, *"the 24th St
300/400-block transition happens across this avenue: printed runs '324' west
and '402' east on sheet 10; '323' west and '401' east on sheet 12."* Twenty
three such pairs produced the frozen core.

**Why that method, and not an easier one.** Adjacent 1912 sheets barely share
mapped ground. Measuring every pair: the shared-scan band along the seam has a
median width of 494 ft but 45 of 132 pairs are under 300 ft and 12 are under
100 ft. The two pairs that matter most here are the thinnest of all —
**75|76 shares 47 ft** and the clean core pair **9|10 shares 84 ft**. Below a
street's width there is no 2-D patch to correlate, which is why:
  - `tools/pairfit.py` (area cross-correlation over the shared band) cannot
    measure these pairs at all — it reports "no overlap" once no-data regions
    are excluded, and before that exclusion it peaked at the search boundary,
    returning the same wrong shift for a broken pair and a good one alike;
  - a 1-D corridor constraint works fine on 47 ft of shared ground, because it
    needs only the centreline to be readable on both sheets, not an area.

That the clean 9|10 also shares only 84 ft is the proof: thin overlap is not
what breaks a seam. Having no identified constraint across it is.

**What recreating it costs.** 132 adjacent pairs, 23 already done (the core).
So roughly **109 ring pairs** need the same treatment: for each, identify the
shared corridor on both sheets, justify its identity against the printed
address runs, record the line on each sheet, then re-solve the network from
those constraints with the core frozen. This is per-pair semantic work on the
images — it is exactly the `registration-engineer` role in the brief (§6), one
task per pair, emitting a control file in the existing schema.

The key maps shortcut part of it: they already name which streets and avenues
each sheet covers (all 92 units for streets, 91 for avenues), so the candidate
corridor for each pair is known before anyone looks at a scan. What the key
map cannot settle is which *detected* line is that corridor when detection
misses one — the failure that produced the one-block error in HQ-11 — and that
is precisely what reading the address runs resolves.

## HQ-13 · 1912 ring re-registered from 137 shared-corridor controls — APPLIED

The master's own method, run at scale. 18 Opus agents identified the shared
corridor for every ring pair: which street or avenue two sheets both draw, its
position in each sheet's native pixels, and the printed address runs proving
the identity is not one block off — the same `why_not_one_block_off` reasoning
as the original 23 core controls.

**Result: 146 controls written, 137 ACCEPTED, 9 correctly refused.** The nine
refusals are all cases where the two sheets are genuinely not adjacent (an
intervening sheet lies between them, each plate printing the other's number in
its margin) — my pair list was built from ownership cuts, which was the wrong
criterion; the agents caught it.

`tools/netsolve.py` solved a translation per sheet from those controls with
the 12 core sheets frozen. **Control residuals: median 0.0 ft, 90th percentile
5.1 ft, worst 33.6 ft.** 77 of 80 ring sheets are now constrained; 17, 81 and
91 have no usable control and were left where they were.

**What it fixed.** Seam 75|76 — the worst defect in the mosaic, "AVE. F OR
CHURCH" drawn twice ~86 ft apart — is now nearly coincident, ink agreement
0.116 → 0.207. Across the render the street grid runs continuously through
sheet boundaries instead of stepping at every seam. Total unclaimed gap area
fell from 12.1M to 10.0M px² and the largest hole from 8.58M to 5.69M px².
Three agents independently found pairs the old mosaic had a **full block**
wrong (40|41, 44|45, 50|51, 66|74).

**What it did not fix, and the honest caveats.**
- Sheets moved a median of 225 ft and up to 2,486 ft. Those are large, but they
  are what the address runs say, and the controls agree with each other.
- **Correction to an earlier version of this entry.** It blamed the mosaic's
  12% growth on some sheets carrying a wrong transform scale, citing sheet 41
  at 2.099 px/native against sheet 40's 2.007. That was wrong. Measuring every
  sheet's own corridor pitch against the known block pitch shows **every scale
  is correct to within 0.05%** — sheet 41's corridors really are spaced 1103
  native px against 40's 1154, and its scale is 4.6% larger to match. Nothing
  needs rescaling.
  The growth is instead the ring being *un-compressed*: sheet footprint
  overlap fell from 37.5% to 29.9% of sheet area, and the bounding box grew
  13% in x but only 0.7% in y. Since adjacent sheets actually share a median
  of only 494 ft of ground along a seam, a 37.5% areal overlap was far too
  much — the old ring was packed too tightly, and the avenue direction is
  where it shows.
- The mosaic still splits into 3 pieces, but only sheets 91 and 99 are
  detached now (2.5% of area between them), against 89-sheet fragmentation
  before the fix-up controls.
- Sheet 72 is still missing (HQ-8) and is the largest remaining hole,
  though it has shrunk from 8.58M to 4.22M px² as its neighbours moved right.
- Ownership was re-cut by Voronoi (`tools/recut.py`) since the old cuts no
  longer matched where sheets are. Those cuts do **not** follow street
  centrelines as §2.5 requires — that must be redone from the corridor index
  before ring crops are print-ready.
- **The key map for sheet 17 is wrong.** It describes an isolated SW-outlot
  plate covering 50th–52nd. The raster is a downtown wharf-district plate
  covering 7th–9th Streets, printing Sealy Hospital, University Hall and
  Seawall Blvd, with margins naming sheets 18 and 21. Anything else derived
  from that key-map row should be treated as suspect.

Previous state is recoverable: `transforms_city.json.pre_controls` and
`seams/ownership_city.json.pre_recut`.

## HQ-14 · 1912 seams re-cut on street centrelines — APPLIED

Closes the §2.5 breach recorded in HQ-9 and HQ-13. The Voronoi cut that
followed the control solve drew boundaries as bisectors between sheet centres,
which is what let a diagonal cut run through a dwelling at seam 57|58.

`tools/streetcut.py` uses the controls as the cut geometry. Each control names
the corridor two adjacent sheets share and gives its position on both, so the
seam between that pair IS that corridor's centreline. A sheet's region becomes
the intersection of the half-planes its controls put it on, clipped to the
ground it covers — convex, so one clean ring per sheet, every controlled
boundary on a street or avenue centreline, and buildings (which sit inside
blocks, between corridors) never split.

A single straight line per named street was deliberately not used: the
corridor index built from the controls shows a street's mosaic coordinate
varying by up to 1,122 ft along its length (the ~2° island bend), so each
pair's own reading is used instead. That index is saved as
`recipe/corridor_index.json`.

**Result.** 134 of 316 region boundaries are now cut on a named street or
avenue centreline; the remaining 182 are bisectors between sheets that have no
control (mostly diagonal or corner overlaps rather than true seams). Seam
57|58 is now a perfectly straight horizontal line — bounding box 1433 × 0 px —
running down the street, with the water mains and the printed 80' width
visible in the corridor and no footprint split.

| | tie-placed | Voronoi re-cut | street cut |
|---|---|---|---|
| overlap | 0.0001% | 0.0000% | **0** |
| disjoint pieces | 1 | 3 | **1** |
| interior gaps | 8 holes | 28 holes | **6 holes** |
| gap area | 0.42% | 0.31% | 0.70% |
| seams on street centrelines | no | no | **134** |

One bug found and fixed mid-way, worth recording: assigning half-plane sides
by comparing each sheet's centre to the cut line gives both sheets the same
side whenever the corridor lies at one sheet's far edge, which produced 1.35%
double-owned area. Sides must be assigned by which sheet lies lower on that
axis. After the fix, overlap is exactly zero.

Gap area is higher than the Voronoi cut because convex clipping trims a
sheet's outer margin where a third sheet's cut reaches it. `tools/fillgaps.py`
reabsorbed every hole that a neighbour actually covers (those holes are
bounded by cut lines, so filling them keeps boundaries on streets); the 6 that
remain are true source gaps where no sheet maps the ground, still dominated by
missing sheet 72 (HQ-8).


## HQ-15 · Sheet 72 placed — the mosaic's largest hole is closed

Registered as the 93rd unit and solved in from four agent-identified controls.

Its scan was fetched hash-verified from the git mirror (`pct50/sheet_0072.jpg`,
sha256 confirmed) at 3327×3898, identical to its neighbours. Its scale came
from its own corridor pitch — 1.9436 against neighbours' 1.9429 — with
rotation seeded from sheets 71 and 73 and translation left to the controls.

Its coverage was not in the key map, so it was inferred from the neighbours
(71 ends at Avenue O, 73 starts at P½) and then **confirmed against the plate
itself** by the agent: streets 33rd–36th, avenues O, O½, P, P½, with O and P½
printed 70' at the west and east edges and 33rd/36th printed 80'.

| pair | corridor | a_native | b_native |
|---|---|---|---|
| 71_72 | Ave O | 3187 | 120 |
| 72_73 | Ave P½ | 3126 | 155 |
| 65_72 | 33rd St | 3664 | 227 |
| 72_80 | 36th St | 3669 | 233 |

Both axes are pinned, and the two street controls cross-check: 65→72 and
72→80 give sheet pitches of 3437 and 3436 px. Address runs pin every corridor
(33rd St goes 1619→1701 across Ave O and 1919→2001 across Ave P½).

**Result.** 154 controls, residuals unchanged at median 0.0 ft / 90th 4.8 ft.
The hole at ~[20400, 27400] — 8.58M px² when first found, still 4.2M after the
ring solve — is gone. Remaining gaps: 7 holes totalling 23.2M px² (0.74%),
none of them a missing sheet; the largest is a long thin 334 px strip at
[18119, 5693], i.e. a seam spread rather than unmapped ground.

Two things this did not fix, and one it caused:
- Sheets 82, 89 and 99 now form a second disjoint piece (3.1% of area). The
  street cut had the city in one piece before sheet 72 was solved in; adding
  its constraints moved sheets 70 and 71 by 740 ft and the south-east group
  no longer touches the main body.
- The agent noted sheet 72 and sheet 80 disagree by ~6 px on 36th St west of
  Avenue P, where each runs blocks onto the platted centreline and draws only
  a 40' roadway. It measured east of Avenue P instead; recorded in the file.

## HQ-16 · 82/89/99 detachment fixed — the city is one piece

The three sheets were never mis-placed. All nine of their controls were
satisfied (residuals 0–4.3 ft), their scales matched their own corridor pitch,
and 99's 57% footprint overlap with 82 is exactly right — those two share two
avenues (S½ and T), so half a sheet of overlap is expected.

The fault was in the cut. `streetcut.py` took the cut's ORIENTATION from
whichever axis a pair's control happened to be on. Sheets 81 and 89 are
diagonal neighbours — 81 spans streets 36–39, 89 spans 39–42 — and share only
an avenue, so their one control is Ave R½. Cutting on that split them
left/right when they are stacked vertically, which stranded 2,335 px of 89's
west side claimed by neither region and left the group hanging off the mosaic
by a degenerate point contact.

Fix: the orientation now comes from how the two sheets are actually stacked
(the sign of their centre offset), and a control is used only when its axis
matches that orientation; otherwise the pair falls back to a bisector. Three
pairs moved from control to bisector as a result.

| | before | after |
|---|---|---|
| disjoint pieces | 2 | **1** |
| overlap | 0 | **0** |
| interior holes | 7 | 8 |
| gap area | 0.737% | **0.447%** |
| largest hole | 10.48M px² | **4.08M px²** |

Sheet 82 now shares a real edge with 81, and 89 with 88 — both in the main
body. The 10.48M px² strip that was the largest hole is gone; it was
over-clipped ground, not missing coverage. Remaining gaps are 8 holes
totalling 9.8 acres, none of them a missing sheet.

## HQ-17 · COG and tiles regenerated — and address lookup still stops at downtown

Rebuilt from the finished recipe (93 sheets, control-solved, street-cut):

| artifact | value |
|---|---|
| COG | `outputs/1912/mosaic/1912_fullcity_150ppi.tif`, 24317 × 45816 (1.114 gigapixels), 915 MB |
| | DEFLATE, 512 × 512 tiles, 7 internal overview levels; opens under `gdalinfo` and `vips` |
| DZI | `outputs/1912/tiles/`, 17 levels, 23,233 tiles, 201 MB |
| flat render | 1,018 MB intermediate (scratch) |

Peak memory 10 GB of 14 GB available. Neither artifact is committed — the COG
is over GitHub's 100 MB file cap — but both rebuild with
`python3 tools/publish.py --year 1912`.

`crop.py` was smoke-tested at the confirmed 100 ft/in and produced a clean
print-ready 16 × 20 at 300 dpi over the downtown core.

**But the smoke test also found the address layer is still core-only.** A crop
anywhere in the ring fails outright:

    python3 tools/crop.py --year 1912 --street 34 --avenue P ...
    KeyError: '18'

`recipe/grid.json` indexes **streets 18–26 and avenue slots 0–10** — the
frozen core, and nothing else. The city spans **streets 7–52 and avenue slots
0–27**. So `lookup.py` and `crop.py` can only serve downtown addresses, and
newly placed sheet 72 (avenue slot 18, streets 33–36) is unreachable by
address even though its pixels are now in the mosaic.

This is the brief's §1(a) — "look up any modern Galveston address and find its
lot" — still unmet outside downtown. The material to fix it now exists:
`recipe/corridor_index.json` holds 33 named corridors located in the mosaic
frame, derived from the 154 verified controls. Extending `grid.json` from it,
allowing for the ~2° island bend that makes a street's mosaic coordinate vary
along its length, is what would open address lookup to the whole city.

Note also that `crop.py` reports "unowned-sliver fallback (disclosed)" where a
crop crosses one of the remaining hairline gaps; the fallback is disclosed in
its output rather than silently filled.

---

## HQ-18 · The 1912 rows are sheared east-west, and the corridor detector never finds avenues

Two findings, both from extending the grid city-wide. The first blocks that
work; the second is a standing caveat on how every control was proposed.

### The shear

Sheets 57 and 63 cover the identical avenue band — L, M, M½, N — one street
row apart. Their y differs by the correct 1,225 ft. Their x differs by
**1,643 ft**, and the same "AVENUE M" renders at two positions across the row
boundary. It is not a drafting disagreement; it is missing constraint.

The control network only ever asked two questions. Sheets side by side share
an avenue, which pins a row internally in x. Sheets stacked share a street,
which pins a column in y. **Nothing ties one row to the next in x.** Counted
out: the 56 avenue controls leave **26 independent x-components** with the
frozen core treated as one rigid body. `tools/gridfit.py` measures the
consequence — streets fit a 399.5 ft pitch with a 28.8 ft residual, avenues a
334.6 ft pitch with a **329.2 ft** residual, and the observed avenue sequence
is non-monotonic (M½ west of L, O west of N).

The fix is to ask stacked pairs the other question: they abut along a street
but *cross* every avenue in their band. `tools/crossrow.py` selects those
pairs and picks a doubly-redundant spanning set, so every component join is
made twice and a bad call surfaces as a contradiction rather than a shear.

**Selecting those pairs from the sheets' footprints was wrong and circular** —
it tests overlap under the transforms being corrected, and it proposed pairs
four avenues apart. Observers rejected 15 of them outright. Selection now
reads the printed key maps, which do not depend on the placement.

### The detector finds alleys, not avenues

Every observer, independently, reported the same thing: of the candidate lines
`recipe/corridors.json` proposes, **none** was an avenue. They sit inside the
blocks, roughly 400 native px east of the roadway, on the mid-block alley or
the rear-lot line. The separator is quantitative and clean:

| | width between faces | printed |
|---|---|---|
| avenue (accepted) | 206–211 px = 69–71 ft | lettered name, hundred-block break |
| detector candidate | ~60 px = 20 ft | dashed, `6" W. PIPE`, no name, no break |

Every accepted cross-row coordinate is therefore a ruler-read roadway centre,
not a proposed candidate.

**What this means for the existing 154 controls.** They were proposed by the
same detector. A uniform bias cancels in the sheet-to-sheet offset, which is
all netsolve uses, so registration is not necessarily wrong. But a control
that took the alley on one sheet and the avenue on the other would be off by
about 400 px (~70 ft) and would not be visible in the residuals. That is worth
a pass over the accepted controls, checking each reported coordinate against
the 70 ft width test. **Not yet done.**

### Cross-validation actually observed

The accepted controls corroborate each other without being asked to. Where two
observers on different batches read the same corridor on the same sheet:
Ave D on sheet 28 → 1176.8 / 1176.6. Ave P on sheet 53 → 1162.0 / 1162.0.
Ave O on sheet 58 → 2121.1 / 2117.8. Ave N on sheet 86 → 1169.2 / 1167.1.
Ave I on sheet 84 → 2173.4 / 2173.1. Ave H on sheet 23 → 2163.1 / 2166.2.
That is 0–5 native px, under two feet on the ground.

Two accepted controls deliberately pair a ~1170 reading against a ~2173 one —
86|94 on Ave N, 90|98 on Ave T. That is a full avenue block apart in native
pixels, and it is the point: those plates' grids are offset by one block, so
matching by near-equal native x would have tied Ave N to Ave M½. Both are
argued from the hundred-block runs.

**Nothing here needs a decision.** It is recorded because the shear was
present in the published COG and tiles, and because the detector caveat
outlives this pass.

---

## HQ-19 · 1912 seams re-cut after the shear fix — APPLIED, with two defects left

`streetcut.py --apply` then `fillgaps.py --apply`, against the corrected
placement. Stage 4 gate: **93 regions, one connected piece, 0 px² overlap, 8
interior holes.** Seams: 136 from controls, 143 from bisectors.

The direct test passes. A crop across the 57|63 seam — the pair whose 1,643 ft
disagreement exposed the shear — now runs Avenue K, M and M½ straight through
30th St with no step.

### Loading all the controls needed a fix

`streetcut.load_cuts` keyed cuts by pair alone, and its filename regex was the
pre-`_x` one, so it saw 154 of the 204 controls. Once the cross-row files
parsed, a worse bug appeared: a stacked pair now carries **two** controls, the
street it abuts along and the avenue it crosses, and the second overwrote the
first. Since a stacked pair's avenue control is on the wrong axis to cut with,
the good street cut was then discarded and the seam fell back to a bisector.
Cuts are now keyed by pair **and** axis, and the caller asks for the axis the
seam's own geometry calls for.

### Negative result: snapping uncontrolled seams to the grid

143 seams have no control and fall back to a bisector between sheet centres,
which is an arbitrary line that can run through a building — what §2.5
forbids. With the city grid now solved, snapping those to the nearest corridor
centreline looked like a clear improvement. It is not: every setting made the
tiling worse.

| snap limit | seams on a centreline | disjoint pieces |
|---|---|---|
| off (bisectors) | 136 | **2** |
| 0.1 block | 248 | 3 |
| 0.2 block | 265 | 8 |
| 0.3 block | 275 | 8 |
| 0.5 block | 279 | 8 |

A seam that moves to reach a corridor trims its sheet away from a *different*
neighbour's seam, and the east-end sheets (17–32) come apart. Constraining the
snap to fall between the two sheet centres changed nothing — they already did.
The code is kept, defaulted off, behind `--snap-blocks`.

### Defect 1 — plate margins bleed in at centreline cuts

Visible at the 57|58 seam: the mosaic shows a grey vertical band carrying
sheet 57's **printed plate margin** — its border rule and the "57" plate
number. The cut itself is right, on Avenue N's centreline at x=21,536 against
the grid's 21,536. The problem is that each plate's drawn margin sits exactly
at the corridor where it will be cut, so a centreline cut necessarily includes
one sheet's margin instead of the neighbour's map content.

The fix is to trim each sheet's `extent` in `units.json` to the neat line, so
a footprint covers map area only. The extents are unchanged by this pass, so
the mechanism predates it. **Not done.**

### Defect 2 — 8 holes, and a correction

Two of the eight are large: 16.1M px² (11 acres) at [14699, 41989] and 11.8M
px² (8 acres) at [11207, 26881].

**I first reported these as over-trimming and I was wrong.** That reading came
from testing whether each hole's *centroid* fell inside a sheet footprint,
which it did. Measuring the polygons properly, the two holes are only **25%
and 37% covered by any sheet at all** — they are genuine source gaps, ground
that no 1912 plate maps. `fillgaps` was right to refuse them.

Of the six smaller holes, four are 82–100% covered but by a *union* of two or
three sheets, with no single sheet reaching the 98% bar `fillgaps` requires
before it will assign one. Splitting those between covering sheets, on the
same half-plane logic the cuts use, would close them without breaking the
single-writer rule. **Not done.**

---

## HQ-20 · 1912 seams re-cut from the plates themselves; the core's own cuts restored — APPLIED

Closes HQ-19's two defects, and corrects its diagnosis of the first.

**The "margin bleed" was unclaimed ground, not margin.** The white band through
30th St at 57|63 was measured against the ownership polygons: at x = 20,000
sheet 57 owned down to y = 17,516 and sheet 63 from y = 17,688, and nothing
owned the 172 px between. The band was an *inlet* — a channel of unclaimed
ground open to the exterior — which `tiling.py` never counted because it only
looked for interior rings. It arose because the first `streetcut.py`
intersected each sheet with whole half-planes, so a diagonal neighbour's cut
reached across the entire sheet and two such cuts did not meet. The ring
plates also turn out to have no continuous neatline to trim to: their border
is a set of brackets a few px inside the paper edge, and their plate numbers
and north arrows sit in the roadway — exactly as the accepted master shows
them at 9|10 (`qc/human/HQ9_09-10_core_control_clean.jpg`, plate number
"10" in Mechanic). Nothing in `units.json` was trimmed.

**What changed.** `streetcut.py` is rewritten on three points:
- a sheet is trimmed only inside its overlap with each neighbour —
  region(u) = base(u) − ∪ (base(u) ∩ base(v) ∩ v's side) — so a cut can only
  remove ground the neighbour keeps;
- the 12 frozen core sheets keep the 27×40 master's min-ink DP masks
  (`seams/masks.json`) as their base. The earlier city cut had silently
  replaced them with 5-vertex bisector boxes (IoU 0.92–0.96 against the
  master's regions); the master's cuts are the accepted product and are back;
- a seam with no control is cut on the corridor the two plates themselves
  show (HQ-22), not on a bisector.

`tiling.py` now reports inlets (closing the union by 700 px and reading what
the closed shape contains that the union does not). `fillgaps.py` splits a
gap between the sheets whose paper covers it when no single sheet does.

**Gate after the re-cut and re-solve:** 93 regions, one connected piece,
455 px² double ownership (0.0000%), **one** unclaimed hole — the 84|85 source
gap, 9.66M px² (1,154 px ≈ 200 ft wide, 0.245% of the union), where no 1912
plate maps the ground. The previous state had 8 holes and the uncounted
inlets. Of the 252 seams, 171 are true band seams and every one of them is
cut on a control — 133 observer-read, 38 lattice-read — and 81 are corner
contacts cut at the overlap midpoint.

A polygon-export bug found on the way is worth recording: a difference can
leave a notch attached to the ring at a single point, which GEOS represents
as a hole touching the exterior; exporting exteriors only brought the notch
back as double ownership (1.9M px² at 77|84). A 1 px opening before export
fixes it, and the audit's overlap figure is the check.

## HQ-21 · Width test over every accepted control — DONE (closes HQ-18's open item)

`tools/faces.py` reads every corridor on a plate from its own ink: block
faces are long rules, a street is two rules a roadway apart with little ink
between them, and consecutive streets are a block apart. A dynamic programme
over the rule spikes picks the chain, so the 25th St boulevard (359–364 px,
~125 ft) and the stained outlot plates read correctly. `tools/widthcheck.py`
compares every accepted control coordinate against that reading.

| | value |
|---|---|
| control coordinates checked | 483 (242 controls) |
| offset to the plate's corridor centre, median | **2.0 px** |
| 90th percentile | 19 px |
| flagged beyond 30 px | 21 |

**The trap HQ-18 predicted was real once.** 83|91 "Ave F" had been read at
native x ≈ 1,665 on *both* plates — the west lot line of blocks 459–461, the
mid-block alley, 500 px west of the lettered roadway. The equal offset
cancelled in the solve, so registration was unaffected, but the corridor
named Ave F in the grid and the seam cut both sat on the alley. Corrected to
the plates' roadway (83: 2,170; 91: 2,164) from the `AVE. F OR CHURCH`
lettering and the block faces either side of it.

Three observer reads were 45–54 px (15–19 ft) past the street's centre
(47|53 on 53, 78|86 on 86, 79|87 on 87 — all at a plate's top edge, between
the street label and the block face) and are corrected from the plate. Each
correction is recorded inside the control file with the observer's original
value. The remaining flags are on plates whose chain is itself flagged weak
(the composites 85/93/99, the rail yard 75, the wharf plates 13/15/17); there
the observers' reads stand.

## HQ-22 · Registration re-solved with 38 plate-read ties — APPLIED

With every corridor readable on every plate, the 38 seams that never had an
observer control got one from the plates (`tools/latticeties.py`): the
shared corridor's centre in each plate's native pixels, identity settled by
the current placement (the two readings must fall within 0.45 of a block of
each other; a block is 350–400 ft, and every one fell within 106 ft) and
the key maps' coverage lists. Only plates whose chain is not flagged weak
contribute, and only corridors whose faces were actually measured, not the
one extrapolated past the plate's edge (that extrapolation was 100 px off on
sheet 71).

What the plates said about the placement they had: median 20 ft apart,
90th percentile 45 ft, worst 106 ft (61|68 and 68|76 — sheet 68's y had never
been constrained). Three side-by-side pairs, **61|62, 69|70 and 76|77**, were
80 ft apart: each plate draws the full avenue (I, K, I) and they had been
placed with the two copies side by side, the same defect class as HQ-9's
75|76.

`netsolve.py` re-solved with the core frozen: observer controls median
3.7 ft, lattice ties median 4.1 ft / max 14.4 ft; sheets moved a median of
9 ft, at most 95 ft (68). The worst residuals (28–34 ft) are the pre-existing
15th/18th St cluster on sheets 30/31/35/36/37/41, where HQ-13 already noted
a scale mismatch that translation alone cannot close. `grid_city.json` was
refit: streets 397.9 ft pitch (21.6 ft residual), avenues 346.9 ft (28.5 ft).
`sheets_city.geojson` is now written from the live transforms (it had been
frozen at the city export and lacked sheet 72); coverage.png shows 93/93.

**The owner can overturn this.** The state before it is in git (commit
25d14c2) and `transforms_city.json.pre_controls`; the 38 tie files carry
`"observer": "lattice (tools/faces.py)"` and can be deleted and the solve
re-run.

## HQ-23 · Two sessions were working on this branch at once — NOTE

Commit 25d14c2 (session `018fqghgw6FGFRhXhgNu9MJF`, 22:14 UTC) added a
dashboard whose plan freezes the registration and lists a neatline trim as
the next task. This session (`019xkiTH5CzPb2j6nmj9Wg2t`) started at the same
time from the same tip and did the work above. The two are reconciled here:
the neatline trim is a misdiagnosis (HQ-20), and the registration moved on
sheet-level evidence (HQ-22), which is what that plan allowed. The dashboard
has been updated to the real state. If the other session pushes a
competing re-cut, rebase and re-run `streetcut → fillgaps → tiling`; the
gate numbers above are the check.

## HQ-24 · Seam census, round 1 — 144 band seams graded; the ring failed

Every band seam of the city mosaic was rendered at 100% and 50%
(`tools/seamcrops.py`, `outputs/1912/qc/seams/`) and graded by twelve
graders on the brief's §6 rubric, one grader per twelve seams
(`qc/seams/grades_round1.json`, per-grader reports in `grades_round1/`).

| score | 5 | 4 | 3 | 2 | 1 |
|---|---|---|---|---|---|
| seams | 0 | 1 | 15 | 66 | 62 |

Largest visible offset per seam: median 16 ft, 90th percentile 54 ft, worst
220 ft (94|95). Defect counts: step 112, duplicated label 73, misplacement
58, tone 33, gap 24, doubled lines 14, split building 2.

**What the graders actually saw** was consistent and diagnostic. The
offset at a seam *grows along it* — "40|41: 27 ft at the north end shrinking
to 2 ft at the south"; "57|63: 7 ft in the west, 22 ft in the east";
"70|78: 21 ft east at the left, 12 ft the other way at the right" — which is
not a translation error. It is the two plates being at different scales.
And a stacked pair's cross streets are shifted *along* the seam by a
constant amount (8|34: 66 ft; 38|42: 24 ft; 42|46: 55 ft) — the direction
that a street control does not pin.

The 1912 core (the master) is exempt: 9|10, 10|43 and the other core-core
seams are the master's own cuts and were not in the census. Every core-ring
seam was, and failed with the ring.

## HQ-25 · The ring plates' scales were wrong by up to 8%; fixed from the plates — APPLIED

HQ-13 recorded that "every scale is correct to within 0.05%". It is not.
The plates' own street chains give every block face-to-face, and the frozen
core — the accepted master — says what a block is in mosaic pixels: 314.6 ft
between street faces, 274.6 ft between avenue faces, each to ±0.7% over 70
core blocks. Measured against that, 49 of the 81 ring plates were more than
1% off and the worst — 79 (+8.1%), 37 (+7.3%), 30 (+5.8%), 41, 24 (+4.4%) —
were 40–60 ft wrong across a plate. `tools/platescale.py` sets each ring
plate's scale from its own blocks (rotation untouched, the plate rescaled
about its centre; 78 plates changed, three with no clean chain kept as
they were), and `netsolve` re-solved translations.

The scale fix alone dropped the control residuals from median 3.7 ft /
max 33.8 to **2.1 / 15.9** — the 15th/18th St cluster that HQ-22 could not
close was a scale problem — and the city grid fit from 21.6 ft (streets) and
28.5 ft (avenues) residual to **11.4 and 8.9 ft**, with pitches of 399.5 and
348.3 ft, which is Galveston's plat.

Then the direction along each seam was pinned. A stacked pair shares every
avenue in its band and a side-by-side pair every street; `latticeties.py
--cross` reads the corridor nearest the middle of the overlap on both plates,
pairing each corridor with its nearest counterpart under the current
placement (within 0.45 of a block). 77 cross-axis ties, none contradicting
the observers: after the re-solve, observer controls median 2.5 ft / max
25.1, cross ties 1.9 / 24.6, seam ties 3.0 / 11.4 (319 controls in all).
Sheets 48 and 74 — the two east-end outliers that only ever touched each
other — moved 144 ft; everything else a median of 6 ft.

Tiling gate after the re-cut: one piece, 386 px² overlap, the one 84|85
source hole. Seam census round 2 follows on the re-rendered crops.

**Owner's note.** This changes the placement of 78 ring sheets by up to
170 ft (sheet 20). The core did not move. The state before it is commit
3f7c092; `recipe/plates/plate_scales.json` records every plate's old and new
scale.

**Addendum — the cut itself.** With the plates placed to a few feet, the
round-2 crops showed the last defect the straight centreline cut makes on
its own: both plates print the street name at the centre of the roadway, and
a straight line through the middle of both left half of each — a ghosted
"27TH ST." at 12|14. The master's cuts never did that because they were
min-ink paths. `streetcut.py` now cuts every band seam the same way: inside
a ±320 px band about the control line, a dynamic programme finds the path
that crosses the least ink on *both* plates (Gaussian-blurred, with a weak
pull toward the centreline), so the seam runs between the label and the
block face and one plate's label survives whole. 144 seams cut on such a
path; the tiling gate is unchanged (one piece, 498 px² overlap, the 84|85
hole). `--straight` restores the old behaviour.

## HQ-26 · Seam census round 2, and the similarity solve — APPLIED

Round 2 graded the same 144 band seams after the plate rescale, the
cross-axis ties and the min-ink cuts (`qc/seams/grades_round2.json`):

| score | 5 | 4 | 3 | 2 | 1 |
|---|---|---|---|---|---|
| round 1 | 0 | 1 | 15 | 66 | 62 |
| round 2 | 10 | 14 | 33 | 70 | 17 |

Median visible offset 8 ft (was 16). Grader after grader described the
same residual: "at the middle the faces line up within 1–2 ft, toward the
north end the cross street is 13 ft out" (24|25, 23|24, 40|41, 73|81,
81|82…). An offset that tapers along a seam is a rotation between the two
plates, and a translation-only solve cannot touch it. Twelve of the
seventeen 1s are on plates whose lattice is flagged weak or that the
observers identified as composites (26, 32, 52–54, 85, 93–96, 99).

`tools/netsolve2.py` solves a similarity per ring sheet. Every control is a
line — the plate's street runs the length of the shared band — so sampling
it at both ends of the overlap makes rotation observable; with
M = [[a, −b], [b, a]] the constraint is linear in (a, b, tx, ty) of both
plates. The core is frozen and each plate is damped toward the scale and
rotation it has, so a plate with three controls cannot swing.

| line residual at the band ends | before | after |
|---|---|---|
| median | 4.7 ft | **1.1 ft** |
| 90th percentile | 12.6 ft | **4.0 ft** |
| worst | 51.3 ft | **12.9 ft** |

Scale changes: median 0.4%, largest 3.0% (sheet 54, three controls, one
clean lattice axis). Rotations: median 0.23°, largest 3.4° — sheet 26, which
had been carried at −4.3° when every other plate sits within ±1.7°.

`grid_city.json` refit: streets 400.5 ft pitch / 11.2 ft residual, avenues
347.3 ft / 15.6 ft. Tiling gate: one piece, 492 px² overlap, the 84|85
source hole (0.251%). Round 3 of the census follows on the re-rendered
crops; the state before this solve is commit 10dc96a.

## HQ-27 · Session 018 resumed as the only session: panels, wharf, and sheets 48/74 — APPLIED

The owner stopped session 019 (HQ-23) and asked this one to carry the task
from its head. Everything it did is kept (min-ink cuts, plate scales, the
similarity solve; the core did not move). Added on top, all on plate
evidence:

**Neatline trim (revisits HQ-20).** `tools/neatline.py` found a rule on
every plate — the outermost chain of dark columns that runs most of a
side, judged against the plate's own paper level — 40–60 px inside the
paper edge on three sides and often too faint to chain on the fourth
(fallback: paper edge + 50). Every unit's `extent` is now inside it
(`extent_scan` keeps the old value); the adjoining numerals and brackets
sit inside the rule, in the roadway, and are handled by ownership as the
master does. Tiling gate unchanged by the trim.

**Composite plates split (26, 48, 85, 93, 99).** Each detached inset is
its own unit (`26b`, `48b`, `85b`, `93b`, `99a`) whose transform is the
parent's plus a native shift measured on the plate: the shared avenue's
block face and the shared street's face with the printed roadway width
(`units.json` notes carry the numbers). The parent's footprint excludes the
inset's frame. For 99 all three observer controls were read on the right
strip, so it keeps the unit's transform and the left strip (34th–36th,
S½–T) is the derived panel — it lands between 74 and 82 where 74 and 99
print each other's numbers. The ground under 85's inset (cemetery,
40th–42nd K–L) is the one remaining hole: a source gap, 17.8M px².

**Wharf plate 5 in the city.** Panels `5a`/`5b` from the archival scan
unreduced (100 ft/in), on the master's frozen joint transforms, verified
against sheets 7/9 (every street lines up). The core plates draw the whole
wharf yard at 50 ft/in, so each seam with 5a/5b sits 200 native px inside
the core plate's neatline and the min-ink path finds the pier-shed ends;
5a|5b is cut on 22nd St (the panel break the master's controls record).

**Sheets 48 and 74 were one street row north of their row.** 74's outlot
quarters S.E. 136 / N.E. 161 sit directly above 81/82's N.W. 136 and
N.W./S.W. 161 and beside 99's S.E. 161; 73, 81, 82 and 99 print '74' on the
edge facing that ground; plate 48 prints 30TH ST at its top, 33RD ST at
its bottom, '66' on its west edge and '74' on its south. Two lattice ties
(66|74_y, 48|60_y) had taken their street identity from the placement and
held both plates a row north (the 36M px² "hole" beside 73 was 74's
place). Those are REJECTED in their files; three plate-read street ties
(48|66 31st, 73|74 35th, 74|82 36th) added; `tools/localsolve.py` moved
only 48 and 74 (~1,190 ft each; residuals ≤ 15 ft; nothing else touched).
The same audit over every accepted tie (face index vs key-map coverage)
flags nothing else of that class.

Gate after all of it: 100 regions, one piece, ~400 px² overlap, one
source hole. Seam census round 3 follows on this state.

## HQ-28 · Correction round: registration reviews A–D, furniture, one-label seams — APPLIED

Four reviewers (subagents, `outputs/1912/qc/seams/regreview_{A,B,C,D}.json`)
re-examined the 40 seams the round-3 census graded as stepped, reading the
plates' own block faces, address runs and printed widths. Their verdicts
were applied only where the evidence was on the plate:

**Mis-read controls, not bad placement logic.** The steps came from control
values: `pair_53_54_y` (lattice) had taken a 275-px non-street on plate 54
for Rosenberg Av (real faces 1195/1556.5, 48 ft off) and bent 53/54's
scales; five Ave L/N/Q ties (24|25, 30|31, 36|37, 37|38, 53|54) had been
read as the centre of a half-drawn roadway strip (12–20 ft); `pair_71_79`
used plate 71's neat line as its south block face (124 px); `pair_92_93`
assumed a 70-ft Broadway on the 105-ft (302-px) convention; `pair_62_71`
and `pair_84_94` tied plates that share no ground. 28 controls were
re-read, added (cross-axis ties on 52|53 26th, 25|32 12th, 31|32 13th/14th,
32|38 15th + Ave N½, 35|36 16th, 24|25 12th, 13|15 Ave A) or rejected; each
file records the previous values and the reason.

**Local re-solves, no city solve.** `tools/localsolve.py --similarity`
(rotation + scale from the controls as lines, everything else fixed) on
52/53/54, 56/57, 84/92/93, 15 (wharf 4 re-placed from it), 25/31/37/32/38,
24, 35/36, 48/74, 70–73 and 62. Plate 54's 1.974 scale (artefact of the
phantom tie) was reset to the ring median before its solve. Band residuals
of all 340 accepted controls (`tools/bandresid.py`, sampled where the
plates meet): median 1.7 ft; the >6 ft remainder are the wharf frontage
seam positions (not feature ties), 40|41 and 71|79 (10–13 ft, plate 71's
scale is damped short of the ~2 % its neighbours imply).

**Source disagreements left as drawn.** 19|20/20|23/20|24 (plate 20 draws
Broadway 158 ft, 23/24/56 draw 105 ft, all labelled 150'); 46|52 (Ave N½
not drawn south of 24th on 52); 52|57 (Base Ball Park block 15 ft deeper on
57); 79|80 (plate 80 runs S.W. 60 onto the 38th St centreline); Ave Q½
70'/35' at 54|60.

**Furniture.** `furniture_native` boxes (93 plate titles, edge numerals,
now the wharf plates' titles/scale bars and plate 76's scale bar) are cut
from a unit's footprint — panels inherit their parent's — so the tiling
hands that ground to a neighbour; where nobody maps it the renderer's
fallback keeps the plate's own paper rather than a hole. Compass roses and
adjoining-sheet numerals stay, as on the master.

**One label per shared street.** The min-ink seam weaved round each plate's
street name on its cheaper side and showed both (57|58, 76|84). It now
keeps to one side of the lettering strip (a side path may not come nearer
the centreline than 40 px, or half the band), the side chosen by the ink
left visible in the band; the centreline path is used only where the band
is too narrow (<80 px) for a side path. Verified on 57|58 (one AVENUE N)
and 76|84 (one 39TH ST).

**Gate after pipeline 7.** 106 regions, one piece, 0.43 % unclaimed (4
holes: cemetery under 85's inset 18.1M px²; 9th St/Ave L corner where
plate 20's inset frame is cut diagonally and 24/25's neat lines stop short,
54k px²; bay water at the 6/5a corner 184k px²; 47k px² at [43809,24982]),
10 inlets, 8 hairlines under the renderer fallback.

**Census round 4** on the 30 re-cut seams: see `grades_round4/` and the
final report.

## HQ-29 · 1912 completion: census round 5, periphery and interior review — APPLIED

The city was reviewed three ways on the finished recipe and the findings
were worked to exhaustion.

**Seam census, round 5** (`outputs/1912/qc/seams/GRADER_BRIEF_R5.md`, 42
graders over all 249 seams): 203 score 5, 38 score 4, 5 score 3, 3 score 2,
none score 1. Every 4 but one is paper tone, which policy does not correct.
Each seam scoring 3 or less was re-examined by a second reviewer who
categorised it (cut placement / registration / source disagreement /
coverage gap / furniture) rather than trusting the grade.

**Periphery** (63 windows along the outer boundary, with a confirmation
pass on every serious finding): 18 confirmed. They were all one of three
things — furniture on blank paper or water, which the accepted master keeps;
the neatline trim ending the map at the city's edge; or the wharf/Strand
source gap below.

**Interior at 1:1** (33 sampled windows, 1 px = 0.1725 ft, adversarial
check of every non-cosmetic finding): 21 clean; 16 findings confirmed, of
which two were real and are fixed below. The rest were refuted — including
a "block face drawn twice" that is plate 74 drawing the west face of 34th
St and panel 99a the east face, 70 ft apart, and an "elevator drawn twice"
where plate 13's paper does not reach the ground plate 4 draws.

**Four defects found and fixed.**

1. *The wharf 3|4 step* (18.5 ft). Each wharf plate followed only the block
   plates behind it, so where those rows disagree the wharf plates parted at
   their shared street. The wharf solve now fits a scale as well as a
   translation — sheet 3's residuals grew monotonically along the plate,
   +6.5 ft at 33rd to −11.9 at 39th, which is a half-percent scale error —
   and sheet 3 carries an equation on 33rd St against sheet 4. Sheet 3's fit
   to plates 67/75 improves from 16.9 ft max to 7.7, sheet 6 to 6.1, sheet 4
   to 3.2, and the step falls to 7.7 ft, shared instead of concentrated.

2. *Legends printing in streets.* Every plate's "Scale of Feet" bar is now
   boxed (`tools/scalebar.py`), each box fitted to the legend's own ink and
   validated (the darkest row inside every box is 0.71–0.94 ink).

3. *The furniture holes were being refilled.* Two bugs, both silent. The
   ownership export dropped every interior ring, so a box surrounded by its
   own plate's ground came back; and `streetcut` took the 27×40 master's
   masks as the base for the core plates and used them unchanged, so
   `footprint()` — the neatline trim AND the furniture boxes — never applied
   to the core at all. Rings are now written and honoured by the renderers,
   tiling and the gap audit; the core keeps the master's cut lines but is
   clipped to this recipe's footprint.

4. *A box is cut only when a neighbour maps all of it.* Cutting every box
   left patches of neighbour paper beside half a legend. `tools/furncover.py`
   measures coverage: 158 boxes are removable in full, 40 stay on their
   plate's own paper, as the accepted master keeps its scale bars and roses.

**The one large source gap.** Sheet 3 ends at "AVE. A OR WATER"; sheets
67/75 begin at "AVE. B OR STRAND" / "AVE. C"; and both plates print the
adjoining-sheet numeral "0" on that edge — the series' mark for no
adjoining sheet. About 660 ft of wharf ground from 34th to 39th St is
simply not in the 1912 atlas. The two frontage pairs that claimed a seam
there are rejected: their values lay 920 and 1440 px beyond sheet 3's own
neatline.

**Gate.** 106 regions, one piece, 1,026 px² double ownership (0.00002%),
0.455% unclaimed (10 holes, 5 inlets, 9 hairlines under the renderer's
disclosed fallback). 333 accepted controls, band-residual median 1.6 ft.

## HQ-30 · Review record persisted — APPLIED

The round-5 census, periphery review and interior review (HQ-29) existed
only in Workflow subagent journals, never under `qc/`. New
`tools/journalq.py` reads each journal (last result per agentId) and merges
scores/findings with their adjudication or confirmation passes into durable
per-seam / per-window JSON.

`outputs/1912/qc/seams/census_round5.json`: 249 seams, 203×5 / 38×4 / 5×3 /
3×2 / 0×1 — reproduces HQ-29 exactly. `outputs/1912/qc/periphery/review_round2.json`:
63 windows, 30 confirms, 18 confirmed. `outputs/1912/qc/interior/review_round1.json`:
33 windows, 21 clean, 23 checks, 16 confirmed. `outputs/1912/qc/interior/win_*.jpg`
and `windows.json` were copied to `qc/interior/round1/` before this ran, per
plan rule 9.

## HQ-31 · P2-2 `pair_26_42` (Ave O 1/2, plates 26|42) — NO CHANGE, values sound, net tension

Identity re-confirmed on the native scans to the existing standard: both plates
letter "AVENUE O 1/2" in the shared roadway and each prints the other's sheet
numeral there ("42" on 26, "26" on 42); the frontages interlock 42-evens
1902–1928 against 26-odds 1901–1927; the cross-street run changes 1723|1801
exactly at the corridor; Ave P is 1,004 px east on sheet 26, so a one-block
error is excluded.

Values re-measured by column-ink profile over three block rows: plate 26 draws
only the east face (267.6) and plate 42 only the west face (3075.2) — both
"faces" at the sheet edges in `lattice.json` are paper-edge shoulders, so the
half-width reconstruction the control used is the only method available. A
re-read using the measured faces and h = 105.8 px (from plate 47, which draws
both faces of this avenue) shifts the tie by 2.8 ft — inside the ±3 ft spread
of the printed 70' roadway across these plates — and makes the band residual
**worse** (−10.3 / +1.6 against −7.2 / +4.7). The recorded value sits 1.3 ft
from zero at band centre. Left ACCEPTED unchanged.

The residual is relative rotation: plate 26 is skewed −0.904° against 42's
−0.101°, and 0.7 × 1214 ft of band × the tilt difference predicts an
0.15→0.85 swing of +11.91 ft against +11.91 ft observed. Plate 26 is the skew
outlier in its neighbourhood (47 −0.236, 41 −0.219, 46 −0.062, 45 +0.056) and
all four of its controls show the same sign flip. `localsolve --units 26` sits
in a balanced deadlock (26_42 +4.1 against 26_47_x −4.1 in x; 26_47 +4.0
against 26_42_y −4.0 in y), so no translation helps, and `--similarity` would
mean re-solving a corner plate held by four controls. Same outcome as 52|53 and
40|41.

## HQ-32 · P2-2 `pair_30_36` (15th St, plates 30|36) — NO CHANGE, values sound, net tension

Both plates print "15TH ST." in the corridor, plate 30 prints the adjoining
numeral "36" south of it and plate 36 prints "30" north of it; the frontage
runs are 902–924 / 1002–1024 (even, plate 30 north) against 901–925 / 1001–1023
(odd, plate 36 south), and the flanking avenue labels change 1425–1428 to
1501–1504 across this line only. The same 8" W. PIPE, T.H. hydrant, 20' alley
and 150' block dimension are drawn on both sheets.

Values verified, not re-read: block faces by row-ink profile give plate 30
3546.0 / 3787.1 and plate 36 102.4 / 343.0 — both 241 px, identical drafted
width, so no source disagreement. The corridor centre sampled in ten x-windows
means 3664.7 and 218.5, so the stored 3664.0 / 219.0 are correct to within one
native px (0.35 ft). The 1.4 ft difference between the 0.15 and 0.85 band
samples is opposite-phase scan bow (±5 px per sheet), irreducible under a
similarity transform.

Cause: plates 31 and 36 agree on the 15th St centreline to 0.4–1.2 ft while
plate 30 sits 5.8–7.2 ft north of both, pinned there by pair_24_30,
pair_29_30_y, pair_25_30 and pair_24_30_x. `localsolve --units 30` moves it
only (−1, +2) ft; `--similarity` buys 3 ft only by changing plate 30's scale
+0.18% and rotation +0.12° while driving pair_30_31 to 5.8 ft; `--units 36`
makes this control worse (−7.5 ft) because pair_31_36 ties the same corridor
from plate 31.

**For a later wave:** the 30-vs-(24/29/25) y tension is the real defect, and
pair_29_30_y and pair_36_37_y are bare "lattice (tools/faces.py)" ties with
corridor "?" and no identity argument — candidates for a named re-read.

## HQ-33 · P2-2 `pair_54_60` (27th St, plates 54|60) — NO CHANGE, values sound, net tension

Plate 54 prints "27TH" with the adjoining numeral 60 and 80' in the roadway,
north-side runs 2102–2124 / 2202–2214 on the 2600 avenue block; plate 60 prints
"27TH" with the adjoining numeral 54, a compass rose and 80', south-side runs
2101–2123 / 2201–2211 on the 2700 block — odds facing evens across one corridor.

Face reads hold: 54's north face at native y 3614–3615 (columns x = 300/900/1500),
60's south face at 347–353, roadway 240–243 px = 80 ft, so a_native 3735 and
b_native 226 are correct (54's south face is trimmed at extent y = 3812, centre
= face + 121.5). The 53/54/60 tie loop closes in value to 1.25 native px (0.41 ft).

The −4.7 / −6.9 ft residual is the per-plate scale spread (53 2.0413, 54 2.0216,
60 1.9994 px per native px) plus a 0.169° rotation difference: over the 822 ft
between 25th and 27th St that leaves 54 5.8 ft too far south of 53 and 5.8 ft
too far north of 60 at once. The mosaic renders 27th St 85.6 ft wide at the east
end against the 80 ft both plates print. Moving 60 zeroes this control but newly
breaks pair_59_60 (+5.8) and pair_60_66 (−4.1); moving 54 splits the tension into
two −7.9 ft residuals; `--similarity` on 54 reaches 3.5 ft only by changing that
plate's scale +0.49% off three controls with no plate evidence. Registration
frozen.

## HQ-34 · P2-2 `pair_30_31` (Ave L, plates 30|31) — APPLIED (control value only; no plate moved)

Corridor identity unchanged and re-confirmed: both plates letter AVENUE L,
plate 30's even Ave-L column 1302–1320 faces plate 31's odd 1301–1317, the
cross-street runs change 1100→1200 exactly across the corridor, and each plate
prints the other's adjoining numeral in the roadway.

The **value** was wrong. Review B read the gutter as 80 ft (half-widths 123 /
120 px), but the printed 80' in those crops sits in the numbered-street
corridor (240–245 px = 80 ft on both plates' y lattice), while Avenue L
measures 213 px — plate 30 Ave K 213.0, plate 31 Ave M 212.1, Ave M-1/2 212.0,
Ave N 217.5, and plate 57, which draws Avenue L complete, 216.5. The correct
half-width is 106.8 px, the figure pair_56_57, pair_29_30, pair_25_31_x and
pair_31_32 already use. `a_native` 3230.0 → 3214.0 (west face 3107.2 + 106.8),
`b_native` 126.0 → 141.2 (east face 248.0 − 106.8); previous values and the
reason are recorded in the control file.

This does not cure the residual, which now reads −7.4 / −4.1 ft: plate 31's
Ave-L face drifts −8.5 px over 2,265 px of y against plate 30's +2 px (~0.2°
relative skew), and `localsolve` already leaves both plates at their optimum
(31 moves (−0.2, −0.4) ft, 30 (−0.6, +2.3) ft). The remaining ~5 ft is held by
pair_31_32_y (−9.6 ft) and pair_31_36 (+6.4 ft). No `localsolve --apply` was run.

**For a later wave:** pair_24_25 (h = 121/121) and pair_36_37 (h = 123/117)
carry the same 80 ft assumption on the same Avenue L column; measured centres
would be 3210.0 / 111.5 and 3200.2 / 150.7, and pair_20_25_x independently
places Ave L on plate 25 at 111.8.

## HQ-35 · P2-2 `pair_31_32` (Ave N, plates 31|32) — NO CHANGE, values sound, net tension

Both plates letter AVENUE N inside the same roadway (31 at native x~3150, 32 at
x~240); 31's face carries the even runs 1206–1216 and 1304–1314, 32's the odd
1205–1215 and 1303–1313. `lattice.json` plus the independently lettered AVENUE M
(pair_31_37_x) on 31 and AVENUE N 1/2 (pair_32_38_x) on 32 fix the chain
indices, and the one-block alternatives are a full 344 ft away with the wrong
parity.

Sub-pixel face fits in 11 y-windows put the mid-plate corridor centres at 3152
(31) and 251.4 (32) against the recorded 3149 / 251 — 1.0 ft and 0.1 ft.

The 7.2 ft swing (−0.9 → +6.3) is the 0.459° relative rotation of the two
transforms over the 7,417 px band (7.18 ft predicted), which no scalar can
flatten. Measured through the transforms, the drawn corridors agree +6.6 ft at
the north end to −2.6 ft at the south and cross at ~0.75 of the band;
`bandresid`'s straight-native-line model exaggerates because the drawn corridor
is skewed 0.79° differently on the two scans. `--units 31` moves it (0,0) ft;
`--units 32` moves it (−5,−6) ft and worsens pair_32_38 to −8.4 ft.

**Tool finding for a later wave:** `tools/localsolve.py:controls()` matches
`pair_<a>_<b>(_[xy])?.json`, so three ACCEPTED controls with a `_y2` suffix —
`pair_31_32_y2` (14th St), `pair_24_25_y2`, `pair_35_36_y2` — are silently
dropped by `localsolve`, `bandresid` and `streetcut.load_cuts`. On 31|32 that
leaves y constrained by 13th St alone. Not fixed here: repairing the regex
changes the city solve for three pairs.

## HQ-36 · P2-2 `pair_38_42` (18th St, plates 38|42) — APPLIED (small value re-read; no plate moved)

Both plates print "18TH ST." and each prints the other's adjoining numeral (42
on sheet 38, 38 on sheet 42); the faces pair even/odd of one hundred-block (38:
1602–1612 / 1702–1712; 42: 1601–1611 / 1701–1711) and the cross-avenue
addresses change 17xx → 18xx across the line. Both draw the roadway 241 px (80',
printed).

Centres re-read from the drawn faces at 18 x-samples: `a_native` 3682 → 3678.0
(38 measures 3678.5 west to 3675.0 east), `b_native` 210 → 210.8 (42 measures
209.0 west to 216.5 east). Previous values and the reason are recorded in the
control file. The 6.2 ft band figure was mostly net tension: the transforms
differ by 0.297° in rotation and the corridor as drawn is not parallel between
plates, which a single-y control cannot encode — the measured centrelines
disagree by only 2.0–3.4 ft in the mosaic. Freeing 38 (+3, −1 ft) or 42
(+0, −1 ft), or solving either with `--similarity`, leaves 5–7 ft on this pair
because pair_38_41 and pair_32_38_x pull the other way. After the re-read the
pair drops off the >6 ft list (+0.7 / +4.6 ft predicted).

## HQ-37 · P2-2 `pair_38_41` (18th St, plates 38|41) — APPLIED (value re-read only; no plate moved)

Plates 38 and 41 share only the 18th St × Ave N corner (120 × 244 native px).
Both print "18TH ST." in that roadway, 38 with the adjoining numeral "42" below
it and 41 with "37" above it; the 18th St hundreds break 1400|1500 falls on the
shared Ave N (41 prints 1401–1423 west of it, 38 prints 1502–1524 east of it);
a single F.A. disc is drawn at the corner on each plate. One chain off is 396 ft
away.

The recorded tie was misread, not misidentified: `a_native` 3659 sat 19.7 native
px north of plate 38's measured corridor centre (faces 3557.0 / 3800.3 → 3678.7)
and `b_native` 233 sat 23.9 px south of plate 41's (faces 88.0 / 330.1 → 209.1)
— 14.9 ft of compounded tie error, while the sibling controls on the same
corridor read it correctly. Values re-read to 3678.7 / 209.1 with the previous
values, observer and reason recorded in the file; the clause calling the
1702–1728 run "the 17th–18th block" is corrected (it is the 1700 block of 18th
St, Ave O to Ave O 1/2).

**No registration change.** Corrected, the corner shows a constant +8.8 ft (y)
and +18.3 ft (x) offset on both faces of both corridors — translation only — and
both plates draw the street 82.6 / 83.2 ft and the avenue 73.7 / 72.5 ft, so it
is not a source disagreement. `localsolve` puts 38 and 41 already at their
optimum, and forcing 38 to satisfy the corrected tie breaks pair_32_38,
pair_37_38_y and pair_38_42_x by the same amount. The control now reads
+8.7 / +8.9 ft, which is the honest measured disagreement; `streetcut` takes the
mean of the two positions, so the 38|41 cut line moves 4.5 mosaic px (0.8 ft),
below the 50 px diff threshold, and 37/42 own nearly all pixels at that corner.

## HQ-38 · P2-3 the 17|18|19 seawall steps — `pair_17_18_y` REJECTED; no plate moved, no re-solve

Two independent Opus reviewers worked edge_00 (18|19) and edge_01 (17|18) and
**converged on the same finding, the same corridor and the same face pair.**

First, the scale: the periphery windows are 6,000 mosaic px rendered to 1,500 at
5.7966 px/ft, so 1 window px = 0.69 ft, not the 1.4 ft `PERIPHERY_BRIEF.md`
states. The reported 20–28 ft steps are really 11.6 ft (17|18) and 12.3 ft
(18|19) on the SEAWALL double line, over blank beach paper 2,200–3,400 native px
north of the nearest shared corridor.

**18|19: no change.** The corridor is Ave F (606–628 even against 605–627 odd,
with the 513–523 → 601–611 hundred-block break on Seawall Blvd). The two plates
put the seawall 2,233.8 and 2,234.6 native px from 8th St's north face — 0.03%
apart — so they agree on the ground; the mosaic step is the 1.13% scale gap
absorbing a real 0.76% drafting-scale difference between the sheets, and
`--similarity` leaves the scales within 0.07% of optimum.

**17|18: the tie is invalid and is removed from the solve.** `pair_17_18_y` is a
`observer: "lattice (tools/faces.py)"` cross-axis tie with `corridor: "?"` whose
plate-17 face pair [2351, 2685] joins two pieces of different ground: y = 2350.5
exists only for x < ~700 and is the north face of 52ND ST inside plate 17's
**detached "Union Slaughtering Co. — Located 3 Miles W of P.O." inset** (printed
52ND ST, 80', address run 1002–1016), while y = 2685 is the 8TH ST south face of
the downtown map — plate 17 is a composite sheet split near native x~1280. The
implied 334 px roadway is no Galveston roadway (80' street = 242 px, 70' avenue
= 212 px, 20' alley = 61 px) and plate 17's other two chains are 244 and 245 px.
Both reviewers named the replacement corridor as 8TH ST and read the same face
pair to within 1.5 px — plate 17 north 2437.2–2438.9 / south 2679.7–2681.0 (runs
214–224 even, 213–223 odd, blocks 607/608), plate 18 north 2446.8–2447.7 / south
2687.5–2688.4 (runs 302–312 / 301–311, blocks 547/548) — with the 200|300 break
on Ave C (Mechanic), exactly as the accepted `pair_17_18` x-tie argues.
Status set to REJECTED with the full reason in the control file.

**No replacement value was written and no `localsolve --apply` was run.** The two
reviewers disagree on the value itself by 5.6 ft at the point `localsolve`
evaluates: plate 17 draws 8th St 70 ft wide west of Strand ("70'" printed) and
80 ft east of it ("80'" printed), so its north line jogs 12.5 ft at Strand and
reviewer 1 declines to choose (2581.1 at the extent centre, 2558.5 in the shared
band) while reviewer 2 fits the continuous south face and derives 2564.0 /
2563.7. Under the Gate A standard a contested value may not be written, and a
`--similarity` re-solve of three plates — which changes their scale and rotation
— may not be bought with it. The candidates are recorded in the file for a
future named re-read.

Both reviewers agree this would not close the seawall steps in any case: the
best case leaves 6–10 ft at 17|18 and 7–9 ft at 18|19. `bandresid` after: 332
accepted controls, median 1.6 ft, 11 over 6 ft, none newly over.

**Also flagged, not changed:** `pair_18_22` carries round-number values (3700 /
198) where the 9th St centres measure 3715.1 / 223.5 — a ~3.5 ft error in the
same direction — and `pair_19_20` is another lattice tie with corridor "?"
carrying the largest local residual.

## HQ-39 · P1-3 inset-frame notch, family 20b/24/25 — APPLIED (coverage only)

The 51,239 px² hole at mosaic [15426, −31174] (9th St / Ave L) was the meeting
of four trimmed margins.

**Plate 20 right: relaxed 3239 → 3271.** `tools/neatline.py` lists this side as
FALLBACK (3239 = paper edge − 50); a 16-segment chain test finds no rule anywhere
in 3239..3283, and by 25 px connected components at ink < paper−45 the map ink
runs to x = 3271 in the parent band and 3264 in the inset band — the vertical
"AVENUE" name in the Ave L roadway, two wharf/rail lines, the 810/812/820 runs
and the 70' width calls — with 3272..3283 blank and the minimum paper-edge column
at 3282. Unit 20's `exclude_native` right edge moved 3244 → 3287 so the parent
cannot claim inset ground the extent now reaches.

**Panel 20b: diagonal re-cut and right edge followed.** The region's single
diagonal ran up to 41 px inside the inset's printed frame band, whose inner edge
traces per row to x = 0.7679y + 1339.1; it is replaced by a 4-segment polyline on
that inner edge with a 5 px guard, clipped so no pixel is ever given up (176 dark
clearance samples against the old line's 181, none in the notch band). The inset
carries no frame on its top or right, so the panel follows the parent to 3271.

**Plates 24 and 25: no change.** Plate 24's right margin never exceeds 0.0016 ink
in 3239..3282 and is exactly 0.000 from 3261; plate 25's left margin is exactly
blank from 38..70 and its top margin holds the title, the adjoining numerals "20"
and "0" and "GULF OF MEXICO" — furniture, which relaxing would import. Their share
of the notch is their `cut:false` title boxes, not an extent question.

Effect: notch 51,239 → 22,714 px² (−56%) with zero pixels lost by any unit. The
residual is bounded by the inset frame band, by plate 20's paper edge (the ground
continues past the 3,327 px scan) and by the two title boxes — an honest source
limit.

## HQ-40 · P1-3 inset-frame notch, family 25b/54b/32/47 — APPLIED (coverage only)

Strips between `extent` and `extent_scan` were sampled on the native scans of
plates 25, 32, 54, 48 and 74 with `neatline`'s own paper-relative ink threshold.
Four fallback sides (no rule was ever measured on any of them) carry continuous
map ink and were relaxed:

- **32 top 92 → 50** — rows 46..92 over x 620..1180 hold the seawall double line
  at ink 0.009–0.015, no value above 0.013; paper edge min 41 / median 42 / max 46.
- **25 right 3239 → 3266** — plate-wide ink 0.006–0.015 to 3266, 0.000 from 3267;
  the inset rows carry SEAWALL BLVD, block NE 48, 12TH ST. and the Gulf wash to 3277.
- **54 top 95 → 52** — ink 0.028–0.035 continuously in rows 48..95, identical to
  rows 96–152, including the Casino Pavilion's north apex and the 2205/2206
  frontage the old boundary clipped (the edge_49 "north end missing" finding).
- **54 right 3233 → 3258** — ink 0.064 at 3233 tapering to 0.000 from 3264 (pier
  structure, water wash, dashed pipe, the adjoining numeral 32).

The 25 and 54 inset `exclude_native` polygons and the 25b / 54b `region_native`
polygons were moved out to match. **Added at Gate A, beyond the worker's
proposal:** unit 32's inset `exclude_native` top was moved 87 → 45 with the
extent, so relaxing the top could not hand plate 32 thirty-seven rows of the
deliberately unplaced plate-32 inset at the parent's own position.

Effect: footprint union +1.46 M px², one piece, all footprints valid, no unit
loses a pixel; `bandresid` unchanged (no transform or control touched).

**Not filled — source gaps.** Back-projection shows the bulk of both wedges is on
neither sheet's paper (25/25b reach native x 3278–3705 against a 3288 paper edge;
54 reaches y −1776 against paper from y 43): roughly 196 × 249 ft and 340 × 800 ft
of ground the atlas does not carry. Disclosed, not filled.

**The 47k px² hole at [43809, 24982] stays open, cause identified.** Plate 48's
bottom strip and plate 74's right strip measure ink exactly 0.000 at every row and
column facing it — blank margin, so the ink test fails and neither extent may
move. The hole is unit 99's "plate number and title" box: `reciplib.footprint_native`
cuts a parent's furniture out of each **panel** in the panel's frame, while
`furncover.py` scores the box in the **owner's** frame, and for 99/99a those frames
are 6,500 px apart (cov 1.000 stored against 0.821 real). The worker proposed
patching `furncover.py` to score each box in every frame it is cut from and take
the minimum. **Declined at Gate A:** that changes the cut decision for every
panel-parent box in the city, which is outside this gate's apply order and would
need its own evidence pass. Logged for a later wave; until then the 46,827 px²
hole stands, disclosed, over blank paper carrying only "GALVESTON TEXAS. / 99 /
AUG 17 1912".

## HQ-41 · P2-1 adjoining-sheet numerals and compass roses as furniture — APPLIED (28 boxes)

New `tools/edgeglyph.py` proposed 29 candidates; three Opus adjudicators named
every one on 1:1 native crops against the two already-confirmed references
(u10 "8", u40 "44"). **Zero rejects** — all are genuine plate furniture: 27
adjoining-sheet numerals (u8 34, u11 5, u13 14, u17 21, u23 22, u25 20, u27 21,
u28 22 and 34, u29 28 and 23, u30 24, u31 25, u34 28, u35 29, u38 42, u43 44,
u44 40, u45 44 and 41, u46 42, u48 48, u81 74, u83 84, u86 95, u93 0, u95 94)
and one compass rose (u96). None is a lot number, width numeral, label or
building: this series' lot/address numerals measure ~30 px italic and width
numerals carry a prime, while every glyph here is 70–210 native px in a rule
break, a roadway or a blank margin.

Identity is argued from the ground, not the template: each box centre mapped
through `transforms_city.json` and probed outward names the sheet that actually
adjoins that edge, and the same probe reproduces the two confirmed boxes. u48 and
u93 have no sheet across their edge — plate 48 prints "48" at its top edge and
again at the internal step where its own coverage resumes, and plate 25's top
margin prints "20", then "0", then "0", which is this atlas's convention of "0"
where no sheet adjoins.

The detector's own output was not usable and was overridden in every case: with
no 1/3/6/7/9 templates it mis-read most names (u81's 7 as a 2, "24" for 34,
"4" for 84), and its boxes swallow the neatline rule vertically while clipping
digits horizontally. Every box was re-measured as the glyph's ink bbox (long
rules removed; T.H. hydrant discs, alley ticks, street-label letters and one
brown edge stain excluded) and padded.

Two conflicts resolved at Gate A: candidates 18 and 19 are the **same** u45 "44",
and the tighter of the two boxes was written (the wider one would have taken in
the AVENUE L label stroke) — one box, not two. And the **existing** confirmed u31
box [1632, 40, 1717, 177] clips its own numeral (the "2" measures x 1597–1630,
wholly outside it), so it was replaced by the union box [1567, 40, 1717, 178]
rather than joined by a second entry; nothing previously kept is lost.

One `furncover.py --apply` then ran once for the whole gate: 182 boxes cut, 45
kept. Of the new ones, 24 come back `cut:true` (a neighbour supplies the ground
in full) and 4 `cut:false` (u23 0.899, u29 0.72, u45 0.944, u48 0.0) — correct,
the master keeps those, as `Do not do` rule 4 requires.

**Recorded caveat:** u93's box lies mostly west of that plate's extent x0 = 90 and
the sheet is trimmed ~15 px west of the glyph, so any leading digit was lost in
trimming; the box covers only ink the plate carries.

**Tool bug, reported not fixed:** `tools/edgeglyph.py` serialises numpy int64 box
values, so `json.dump` raises and leaves a truncated 68-byte candidates file —
all three adjudicators had to recover the list from the detector's stdout and
crops. A one-line `int()` cast fixes it; the candidate order is deterministic and
reproduces exactly.

## HQ-42 · P3-2 plate 89's scale bar; plates 3 / 5a / 5b titles — APPLIED

**Plate 89.** The "Scale of Feet." legend is inside the trimmed extent (34 px
above the neatline) and prints across Avenue R1/2 in the shipped build, between
the even run 2302–2324 and the odd run 2301–2323. `tools/scalebar.py` missed it
because the plate's true template peak is 0.451, under THRESH = 0.52, and is
outranked by a spurious 0.500 on the scan's bottom paper/cutting-mat edge. **The
threshold was not lowered** — at 0.50 it would write that wrong box here and a
second wrong box on 5a/5b. The box was hand-fitted to the ink (298,3650)–(917,3731)
+ 8 px = 635 × 97, against plate 14's 646 × 98; darkest row 0.769, clean 3 px ring,
local template peak 8 px away. `furncover` returns coverage 1.000, so the legend is
now supplied by authentic neighbour paper.

**Plate 3.** The title block ("GALVESTON, TEXAS." over "3", ink (67,73)–(212,208))
was recorded as kind `edge numeral/glyph` with a box that cut "TEXAS." off
mid-word. Re-kinded to `plate number and title` and refitted to [56, 63, 222, 220];
coverage 0.541, `cut:false`, footprint unchanged. Plate 3's real adjoining numerals
("4", "15", "2") are in the map body and remain undetected, so the edge
numeral/glyph unit count drops 6 → 5.

**Plate 5a.** The title (ink (268,190)–(500,440)) already had an `exclude_native`
rectangle but no furniture record; the box was added equal to that rectangle — the
convention on 93 of the 95 plates with a title box — so nothing moves (coverage
0.743, `cut:false`).

**Plate 5b: none needed, recorded.** Sheet 5 carries one title impression and it
lies at x 268–500, west of 5b's region boundary at x~3803; 5b's own corners carry
no title.

## HQ-43 · P1-2 blank-band ownership rule — APPLIED to tools only, NO CHANGE to the recipe

`tools/streetcut.py:dp_cut` now measures each plate's ink inside the band against
that plate's own paper tone (new `band_ink()`) and, when one plate's band ink is
below `BLANK_RATIO = 0.20` of the other's, builds a fourth DP candidate pinned at
the blank plate's own band edge (grid rebuilt at `DP_HALF_BLANK = 4000`) and
force-selects it, writing `blank_band {winner, ink_ratio}` on the exported seam
row. New `--dump-cuts`, and new `tools/cutdiff.py` to diff two dumps into the
changed-seam set. The raw `255 − g` measure the plan specified can never fire:
grey Sanborn paper puts every pair's raw ratio above 0.80.

**The rule ships default OFF** (`--blank-band` enables it), because its premise did
not survive the plates. At 94|95 both sheets print "AVENUE N1/2" and the 70' width
in the shared corridor (ratio 0.555) and at 13|14 both draw the 6" W. PIPE run down
Ave C (0.926); the blank paper on 94 east of its rule is matched by blank paper on
95, each carrying only the other's adjoining numeral. City-wide the rule fires on
1 of 172 min-ink seams, 5b|11 (0.129), and that firing is a false positive: plate 11
draws the Wharf Co. terminal yard there (blocks 744–746, Ave A or Water St, the
"WOOD FIRE WALL BUILT OF 2"x12" DRESSER TIMBER" note on its own scan), and it would
move 16.5 M px² from 11 to 5b and open 764k px² of unclaimed ground — a Gate B
failure. With the rule off the tool reproduces the previous
`ownership_streetcut.json` byte for byte and `cutdiff` reports 0 moved seams.

## HQ-44 · GATE A summary

Applied, in the plan's order: four control files, then `units.json` extents and
regions, then furniture boxes, then one `furncover.py --apply`. **No
`localsolve --apply` was run and no plate moved anywhere in this gate.**

| | before | after |
|---|---|---|
| accepted controls | 333 | 332 (`pair_17_18_y` rejected) |
| band residual, median of max-abs | 1.6 ft | 1.6 ft |
| controls over 6 ft | 12 | 11, none newly over |
| footprint union | 4,543.0 M px² | 4,544.5 M px² |
| furniture boxes | 199 | 227 (182 cut, 45 kept) |

Changes applied: `pair_30_31`, `pair_38_42`, `pair_38_41` re-read (values only,
previous values recorded); `pair_17_18_y` rejected; plate 20/25/32/54 extents and
the 20b/25b/54b regions relaxed on measured ink profiles; 28 furniture boxes added
and 2 corrected. Declined at Gate A: the seawall re-value and its `--similarity`
re-solve (reviewers agree on the corridor and faces but differ 5.6 ft on the value);
the `furncover.py` panel-frame patch (city-wide effect, needs its own evidence
pass); the `edgeglyph.py` and `localsolve.py` regex fixes (tool changes, logged in
HQ-35 and HQ-41). No change and no plate move for `pair_26_42`, `pair_30_36`,
`pair_54_60`, `pair_31_32`, the 18|19 seawall seam, plates 24/25 in the 20b notch,
plates 48/74 at the 47k hole, and plate 5b.

## HQ-45 · Wave 2 re-cut after Wave 1 — APPLIED (Gate B passes)

`streetcut.py --apply` → `fillgaps.py --apply` → `tiling.py` re-run on the
Gate A recipe (four control files, the 20/25/32/54 extents and 20b/25b/54b
regions, 28 new furniture boxes). No tool behaviour changed in this wave: the
blank-band rule stayed off, as HQ-43 concluded, and its dump on this build again
fires on 0 of 172 min-ink seams.

**Gate B**

| | before | after | gate |
|---|---|---|---|
| regions | 106 | 106 | — |
| disjoint pieces | 1 | **1** | == 1 |
| overlap | 1,025.8 px² | **1,031.2 px²** | ≤ 1,100 px² |
| union | 4,541.2 M px² | 4,542.7 M px² | — |
| unclaimed | 20,671,614 px² (0.4552%) | **20,649,212 px² (0.4546%)** | ≤ 0.455% |
| gaps reported | 24 | 25 | — |

No new hole over 50,000 px². The one gap that is new is a 5,569 px² cut-line
hairline at [11159.7, 53312.1]; every hole above 50k is one already on the
disclosed list (the cemetery under 85's inset 18.07 M, the bay water at 6/5a
308k / the five ~290k bay-edge slivers, the 128k at [-13226.6,-14580.3], the
48/74/99a notch 46.8k), and the 9th St/Ave L inset notch **shrank from 51,239
px² to 22,714 px²** — the P1-3 coverage relaxations doing what they were
accepted for. Nothing closed and no hole grew.

**Changed-seam set** (cut line moved > 50 px anywhere; `tools/cutdiff.py`,
172 cuts in both runs, no seam changed kind):

`17_21` (max 252 px / 43.5 ft, median 128) · `88_96` (180 px / 31.1 ft) ·
`54_54b` (125.5 px / 21.7 ft) · `20_20b` (108 px / 18.6 ft) ·
`25b_32` (89.3 px / 15.4 ft) · `20b_25` (84.4 px / 14.6 ft) ·
`25_25b` (83 px / 14.3 ft) · `38_42` (52 px / 9.0 ft)

Seven of the eight are the inset-frame families whose extents and regions moved
(20/25/32/54 and the 20b/25b/54b panels, plus plate 17, whose relaxed side stops
three slivers from detaching); `38_42` is the re-read 18th St centre control.
The remaining 164 shared cuts moved ≤ 50 px. This is the set Wave 3 re-crops
(`seamcrops.py --only`) and Wave 4 re-grades against round 5.

## HQ-46 · Wave 3 render — APPLIED

All Wave 3 deliverables rebuilt from the Gate-B recipe (no recipe file
touched this wave; `outputs/1912/recipe/*.json` stayed frozen). Sequence:
`rm -f work/city/*.tif` → `publish.py --year 1912` → `printmaster.py --year
1912` → `printmaster.py --year 1912 --tiles 2x2 --skip-render` →
`seamcrops.py --only 17_21 88_96 54_54b 20_20b 25b_32 20b_25 25_25b 38_42
14_49 15_67 20_23 63_70 63_71 64_71 64_72 --kinds band,corner` →
`perirender.py --year 1912` → `interiorwins.py --cols 12 --rows 16 --size
1500` (round 1 was already archived to `qc/interior/round1/` before this
wave; `interiorwins.py` overwrote `win_*.jpg`/`windows.json` in place with
the denser 12x16 = 136-window grid per P2-4).

**New tool code**: `tools/printmaster.py --tiles COLSxROWS` (P2-5). Reuses
`work/city/1912_wall_4.tif` pixel-for-pixel (renders it only if missing);
crops with pyvips into a COLSxROWS panel grid, each panel a 300 px (1 in)
overlap into its neighbours plus a 150 px blank bleed margin carrying four
corner registration marks (crosshair + ring) and a panel label — both drawn
entirely inside the bleed, never over map pixels or the overlap band. Ships
TIFF (deflate, predictor horizontal, tiled, BigTIFF) and PDF (jpegsave +
`img2pdf --pagesize`) per panel plus `print/tiles/manifest.json` (source,
mosaic/overlap/bleed px, and per panel: core rect, crop rect, overlap width
on each side, file paths). Caught and fixed a real bug while building this:
pyvips 3.2.0's `draw_line`/`draw_circle` return a *new* image rather than
mutating in place, so every draw call needed its return value reassigned —
the first cut silently produced blank bleed margins (verified by pixel
sampling before it shipped). `.gitignore` gained
`outputs/*/print/tiles/*.tif` and `outputs/*/print/tiles/*_tile_*.tif`,
matching the existing wallmaster/sheet TIFF-not-tracked convention; the four
panel PDFs and `manifest.json` are tracked.

**Verification**

- `gdalinfo -norat -noct` opens the COG; `vipsheader` opens every shipped
  TIFF (wall master, sheet, all 4 tile panels).
- `pyvips.Image.new_from_file(pdf, dpi=20)` confirms PDF page size against
  `--pagesize`: sheet 29.55x38.75in (target 29.6x38.7), all four tile PDFs
  31.55-31.60 x 40.75in (target from the tif dims, exact to the pagesize
  arg's 2-decimal rounding).
- Tile overlap checked pixel-for-pixel, not by eye: for each shared boundary
  the 600 px band that both neighbouring panels carry (300 px into each side
  of the core line) was cropped from both panels' TIFFs at the matching
  mosaic coordinates and compared as numpy arrays. All four boundaries
  (c0r0|c1r0, c0r1|c1r1, c0r0|c0r1, c1r0|c1r1) came back byte-identical
  (max abs diff 0), each band 70-95% non-white (real map content, not
  blank bleed bleeding into the compare).
- Registration marks and label sampled directly: corner mark centred at
  (75,75) px in c0r0, well inside the 150 px bleed and outside the 600 px
  compared overlap band; label sits in the bottom bleed strip only.

**Output list** (pixel sizes; full paths under `outputs/1912/` unless noted)

| file | pixels | on disk |
|---|---|---|
| `mosaic/1912_fullcity_150ppi.tif` (COG) | 35491 x 46497 | 1.2 GB |
| `tiles/1912.dzi` + `tiles/1912_files/` (DeepZoom) | — | 279 MB |
| `preview/1912_fullcity_preview.jpg` | 7098 x 9299 | 12 MB |
| `print/1912_wallmaster_59x77in_300ppi.tif` (gitignored, regenerates) | 17745 x 23248 | 259 MB |
| `print/1912_sheet_30x39in_300ppi.tif` (gitignored, regenerates) | 8872 x 11624 | 79 MB |
| `print/1912_sheet_30x39in_300ppi.pdf` | 29.6 x 38.7 in page (300 ppi) | 23 MB |
| `print/tiles/1912_tile_2x2_c0r0_32x41in_300ppi.tif` (gitignored) | 9472 x 12224 | 95 MB |
| `print/tiles/1912_tile_2x2_c1r0_32x41in_300ppi.tif` (gitignored) | 9473 x 12224 | 42 MB |
| `print/tiles/1912_tile_2x2_c0r1_32x41in_300ppi.tif` (gitignored) | 9472 x 12224 | 78 MB |
| `print/tiles/1912_tile_2x2_c1r1_32x41in_300ppi.tif` (gitignored) | 9473 x 12224 | 74 MB |
| `print/tiles/1912_tile_2x2_c0r0_32x41in_300ppi.pdf` | 31.55 x 40.75 in page | 24 MB |
| `print/tiles/1912_tile_2x2_c1r0_32x41in_300ppi.pdf` | 31.60 x 40.75 in page | 13 MB |
| `print/tiles/1912_tile_2x2_c0r1_32x41in_300ppi.pdf` | 31.55 x 40.75 in page | 21 MB |
| `print/tiles/1912_tile_2x2_c1r1_32x41in_300ppi.pdf` | 31.60 x 40.75 in page | 20 MB |
| `print/tiles/manifest.json` | 4 panels | 4 KB |
| `qc/seams/seam_*.jpg` (15 pairs, band+corner, gitignored except index) | 1500x1500-class crops | 778 files |
| `qc/seams/index.json` | — | tracked |
| `qc/periphery/edge_*.jpg` (63 windows, gitignored) | 1500x1500 | 63 files |
| `qc/interior/win_*.jpg` (12x16 = 136 windows, overwrote round-1 set) | 1500x1500 | 136 files |
| `qc/interior/windows.json` | — | tracked |
| `qc/interior/round1/` (33-window round-1 archive, untouched, pre-existing) | 1500x1500 | 34 files |

No `--apply` was run on any recipe tool this wave. `outputs/1912/recipe/*.json`
byte-identical to before. Nothing under `inputs/` touched.

## HQ-47 · Gate A' 1a · wharf sheet 4 (and dependent sheet 3) re-placed — APPLIED

`outputs/1912/qc/wave4/proposal_4_wharf.md`. Plate 4's "ELEVATOR (IRON CLAD)
(For Report See Sheet 13)" is plate 13's Elevator "B" (same block 748, same
annexes, addresses 2802-2828 / 2801-2827); it stood 347.9 ft west of plate 13's
copy at 29th St because `tools/wharfplace.py` pinned sheet 4's Ave A to plate
15's x-chain 0 ([29,235]), which is the scan/neatline border, not a corridor.
Plate 15's Ave A is chain 1 ([1044,1254], 210 px = 72 ft, "AVE. A OR WATER"
lettered, 3100-block addresses).

**Change** — `tools/wharfplace.py`: `WHARF["4"]["ave_a_chain"] = {"13": None,
"15": 1}` with the evidence in a comment; then `--sheet 4 --apply`, `--sheet 3
--apply` (3 reads 4's transform).

Also fixed a real bug in the same tool: the `--apply` path reused the loop
variable `k` for the "carry `extent_scan` / `extent_fallback_sides` /
`furniture_native` forward" loop, clobbering the solved scale, so `--apply`
crashed with `could not convert string to float: 'furniture_native'` before
writing anything. Renamed to `key`. (No wharf sheet had been re-applied since
furniture boxes were added, which is why it had never fired.)

| | before | after |
|---|---|---|
| sheet 4 t | [-21273.5, 12286.0] | **[-19260.5, 12285.0]** (+347 ft east) |
| sheet 4 scale | 3.9724 | 3.9766 |
| sheet 4 solve | 10 eqns, residual median 1.1 / max 3.2 ft | median **1.0** / max **3.3** ft |
| sheet 3 t | [-21608.5, 23324.0] | **[-19577.8, 23328.0]** (+350.4 ft east) |
| sheet 3 solve | median 1.6 / max 7.8 ft | median **1.5** / max **6.4** ft |

`units.json` is byte-identical after both applies (extents, `extent_scan`,
`extent_fallback_sides` and every furniture box preserved); only
`transforms_city.json` `m`/`t`/`scale` for units 3 and 4 changed, plus the four
frontage controls the tool rewrites.

**Frontage controls.** `pair_4_13.a_native` 3147.4 -> 2637.8 and
`pair_4_15.a_native` 3137.2 -> 2627.6 (b_native 200 unchanged), both just west
of the elevator body, so plates 13/15 keep the elevator and the yard.
`wharfplace.py` also rewrote `pair_3_67` / `pair_3_75` from REJECTED back to
ACCEPTED; **their rejection has been restored by hand** (the wharf-Strand strip
is a disclosed source gap; both plates print the adjoining numeral "0") with the
new `a_native` (3668.4 / 4188.2, still beyond sheet 3's neatline at 3287) and
the re-measurement below recorded in the file. No control's `solve` flag was
touched; the five `solve:false` panel pairs are unchanged.

**Wharf-Strand source gap, re-measured after the move** (footprints,
furniture-free): nearest-point 3|67 587.8 -> **238.3 ft**, 3|75 961.0 ->
**611.5 ft**; mean gap along shared latitudes 3|67 695 -> **345 ft**, 3|75
1063 -> **714 ft**. The strip narrowed by ~350 ft everywhere and did not close;
it stays disclosed.

**Verification.** `outputs/1912/qc/wave4/verify/elevator_4_vs_13.jpg` — the same
mosaic rect (-8700,13800)-(-7800,15100) at 1:1, left as rendered from plate 13
("ELEVATOR \"B\", CAPCY 600,000 BUSHELS (IRON CLAD)"), right sampled through
sheet 4's new transform ("ELEVATOR (IRON CLAD) (For Report See Sheet 13)"). The
two bodies now occupy the same rect to ~20 px (3.5 ft) with corners 4-12 ft
apart (the two sheets are drawn at 50 and 100 ft/in). Before the move the plate-4
copy was a whole 348 ft west, off this crop entirely.

**Gate**: `bandresid --year 1912` 332 controls, median max-abs **1.6 ft**,
**11** over 6 ft - identical to the baseline, nothing newly over 6 ft
(`pair_4_13` +11.9/+5.9, was +11.9/+6.0; it is a frontage seam-position pair,
not a feature tie).


## HQ-48 · Gate A' 1b · `pair_91_92` (Ave G / Winnie) re-read + unit 91 similarity — APPLIED

`outputs/1912/qc/wave4/proposal_91_92.md` (from interior window win_58): the 30"
supply main down Ave G and its caption print twice, ~10.5 ft apart at the south
end, one copy per plate, and plate 91's copy lies west of the 91|92 overlap band,
so no cut can suppress it. Cause: the control's centreline was built as
curb + half-width using **80'**, but that "80'" is lettered in the E-W cross
street beside the 6" W. PIPE; both plates letter **70** inside the Ave G roadway.

**Control** `controls/pair_91_92.json`: `a_native` 3177.8 -> **3162.7**,
`b_native` 121.4 -> **136.5**, previous values kept as `a_native_previous` /
`b_native_previous` and the width proof, the width-free hydrant/main tie and the
70' half-width (105.2 px) recorded in a new `re_read` field. Corridor identity
and `why_not_one_block_off` unchanged (600/700 address break at 44th St).

**Solve** `localsolve.py --year 1912 --units 91 --similarity --apply` (91
disagreed with both x-neighbours equally and oppositely; 92 is well tied by
`pair_84_92_x` / `pair_92_93`). 10 line samples, residual median **0.6** / max
**1.3 ft**; unit 91 scale 2.0119 -> 2.0130 (+0.05%), rotation +0.256 -> +0.178
deg, centre moves (+4, +1) ft. No fallback needed.

| control | before | after |
|---|---|---|
| `pair_91_92` | +6.2 / +6.2 ft (against the corrected value) | **-1.3 / -1.0** |
| `pair_83_91_x` | +6.2 | **-1.1 / -1.2** |
| `pair_83_91` | | +0.2 / +0.9 |
| `pair_84_91` | | -0.2 / -0.3 |
| `pair_91_92_y` | | +0.2 / +0.2 |

**Gate**: 332 controls, median max-abs **1.6 ft**, **11** over 6 ft, none newly
over 6 ft (the over-6 list is unchanged from baseline). The doubled main is
verified after the re-cut (HQ-51).

## HQ-49 · Gate A' 1c · `pair_17_18_y` settled and ACCEPTED; units 17+18 re-solved — APPLIED

`outputs/1912/qc/wave4/proposal_17_18.md`, which settles the value the two P2-3
reviewers could not agree on (HQ-38 rejected the control rather than write a
contested value). The disagreement was 5.6 ft = plate 17's own 70'/80' half-width
difference (17.05 px); it disappears by taking the **south block face** instead
of the centre, which is continuous on both plates (17: 2685.36 -> 2679.87 with no
break at Strand, the widening taken off the north side; 18: 2685.60 -> 2688.00).

**Control** `controls/pair_17_18_y.json`: `status` REJECTED -> **ACCEPTED**,
`corridor` "?" -> **"8th St - SOUTH block face"**, `a_native` 2518.0 ->
**2685.4**, `b_native` 2566.0 -> **2685.6**, `roadway_px` dropped (a face, not a
corridor pair). Previous values kept as `a_native_previous` /
`b_native_previous`; the P2-3 rejection text is kept verbatim as
`previously_rejected` and the reviewers' candidate values as
`prior_reviewers_note`; the re-read, its width-free check (8th St south face ->
seawall centreline along the Ave C meridian, 576.8 ft on 17 vs 575.4 on 18,
0.24% apart) and the identity argument are in `re_read`.

**Solve** `localsolve.py --year 1912 --units 17 18 --similarity --apply`:
18 line samples, residual median **1.5** / max **3.4 ft**. Unit 17 scale
1.9850 -> 1.9894 (+0.22%), rotation +0.425 -> +0.329 deg, centre (-2, -4) ft;
unit 18 scale 2.0152 -> 2.0143 (-0.04%), rotation +0.507 -> +0.332 deg, centre
(-1, +4) ft. (Translation-only was tested by the proposal and is not the fix.)

| control | after |
|---|---|
| `pair_17_18_y` | +3.4 / +3.4 ft (was 13.1 in the band model) |
| `pair_17_18` | +0.0 / +0.1 |
| `pair_17_21` | **-1.6 / -0.8** (was +0.3 / +2.4) |
| `pair_17_21_x` | -0.1 / -0.1 |
| `pair_17_22` | -2.2 / -2.2 |
| `pair_18_19` | -2.0 / +0.8 |
| `pair_18_19_y` | +1.5 / +1.4 |
| `pair_18_22` | +1.5 / +2.4 |

Predicted remaining steps at the Ave C meridian: 8th St south face 0.34 ft,
north -0.13, 7th St 3.98, seawall 3.18 - the residual is the two sheets'
drafting-scale difference and cannot be absorbed without breaking 17|21, 17|22,
18|19, 18|22. Side effect confirmed by `proposal_20b_25_17_21.md`: seam 17|21's
along-seam gradient falls from 10.6 ft (0.98%) to 7.3 ft (0.68%) and its worst
step from 6.0 to 4.4 ft.

**Gate**: 333 accepted controls (the re-accepted one is new to the count),
median max-abs **1.6 ft**, **11** over 6 ft, none newly over 6 ft.

## HQ-50 · Gate A' 1d · `pair_63_70_x` re-read, new `pair_64_71_x`, units 63+64+71+72 re-solved — APPLIED

`outputs/1912/qc/wave4/proposal_64_71.md`. Two findings, both invisible to every
gate before this: `pair_63_70_x` asserted a value ~14 native px (4.7 ft) off yet
reported a band residual of -0.1 ft, and seams 64|71 / 64|72 carried **no control
at all** while stepping a constant 13 ft.

**`controls/pair_63_70_x.json`** (re-read): `a_native` 1178.5 -> **1178.0**,
`b_native` 2186.5 -> **2172.3**, `corridor` "?" -> **"Ave M"**, `roadway_px`
[207,207] -> [208.0, 209.5], previous values kept as `*_previous`, the band
measurement and the plate-70 grid corroboration in `re_read`, and a
`why_not_one_block_off` (four corridors on a ~1000 px pitch on both plates; the
correction is 14 px). `lattice.json`'s faces for plate 70's third x chain,
[2083, 2290], are simply not where plate 70 draws Ave M (2067.5 / 2277.0).

**`controls/pair_64_71_x.json`** (new): Ave N, `a_native` **178.3** (64) /
`b_native` **1177.6** (71), faces 73.0/283.6 and 1071.5/1283.6, both roadways
70 ft and both plates lettering `70'`, `disagreement_before_ft` 13.0. The
`why_not_one_block_off` carries the printed evidence (33rd St 1500-block runs,
the 3200/3300 avenue frontage change at 33rd St, the shared **T.H. hydrant** as a
width-free tie, Ave N 1/2 one corridor east taking the 1500/1600 change) and the
three independent offsets (faces 999.3, centreline main 1002.3, hydrant 999.1)
plus the NCC of the whole overlap band at four positions (1000/988/990/999 -
constant, a translation). The `method` field records the convention caveat: this
is the **band** reading that `bandresid` and `--similarity` sample, not the
mid-height reading (a 171.0 / b 1188.7), which differs by ~18 px because the two
plates' drawn tilts differ by more than their transforms' rotations.

With the two files in place and no transform change, `bandresid` reproduced the
proposal exactly: `pair_64_71_x` **+13.0 / +13.0**, `pair_63_70_x` **+4.6 / +4.7**.

**Solve.** The proposal's `--units 64 71 72 --similarity` was run first and
**failed the gate by 0.03 ft**: it pushed `pair_71_72` to **6.03 ft**, newly over
6. It also left `pair_63_70_x` at 4.66 ft, i.e. above the 4 ft the proposal set as
the trigger to "check 63 too". Freeing 63 as well does both jobs, so the applied
solve is **`localsolve.py --year 1912 --units 63 64 71 72 --similarity --apply`**:
46 line samples, residual median **1.1** / max **5.7 ft**.

| unit | scale | rotation | centre |
|---|---|---|---|
| 63 | 2.0150 -> 2.0142 (-0.04%) | +0.291 -> +0.416 deg | (-2, +0) ft |
| 64 | 2.0149 -> 2.0224 (+0.37%) | +0.381 -> +0.540 deg | (-3, +2) ft |
| 71 | 2.0114 -> 2.0083 (-0.15%) | +0.328 -> +0.395 deg | (+2, +0) ft |
| 72 | 2.0251 -> 2.0249 (-0.01%) | +0.281 -> +0.271 deg | (+0, +0) ft |

| control | before | after |
|---|---|---|
| `pair_64_71_x` | +13.0 / +13.0 | **+3.9 / +3.8** |
| `pair_63_70_x` | +4.6 / +4.7 | **+1.0 / +1.0** |
| `pair_71_72` | +4.4 / +3.7 | +5.6 / +3.7 (under 6) |
| `pair_63_64` | -1.1 / +0.3 | +0.9 / +2.8 |
| `pair_63_70` | +0.9 / +0.4 | -0.0 / +0.6 |
| `pair_63_71` | -0.9 / -1.6 | -0.9 / -0.8 |
| `pair_70_71` | +3.3 / +3.2 | +0.4 / +1.2 |
| `pair_58_64_x` | -0.3 / -0.2 | -0.3 / -0.2 |

Alternatives measured before choosing: `64 71 72` (fails, above), `64 71 72 79`
(passes, but leaves `pair_63_70_x` at 4.66), `64 71 72 65` (same), `70 71 72 64`
(two controls newly over 6 ft). The remaining ~3.9 ft on `pair_64_71_x` is the
drawing tilt the proposal documents in its §5(a) - plate 63's N-S lines tilt
-0.0018 px/px against plate 70's +0.0044 - and is **not** chased.

Not applied, as the proposal advises: `pair_70_71` (method fault recorded, the
half-width error cancels in the difference - "fixing" one side would introduce
~50 px) and the optional 2 ft `pair_63_64.a_native` re-read.

**Gate**: 334 accepted controls, median max-abs **1.6 ft**, **11** over 6 ft -
the same eleven as the baseline, none newly over 6 ft.
