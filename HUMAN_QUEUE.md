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
