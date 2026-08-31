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

## HQ-8 · 1912 is missing sheet 72 — OPEN

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
