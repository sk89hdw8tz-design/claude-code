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

## HQ-8 · 1912 is missing sheet 72 — OPEN

The Stage 4 tiling audit (`tools/tiling.py`) found the 1912 city mosaic is one
connected piece with effectively no double-ownership (2,638 px² overlap on a
2.86-billion-px² union, i.e. the single-writer rule holds), but it is **not**
gap-free: 11 interior holes remain after fixable ones were closed, and the
largest is decisive.

That hole spans x 19028..23360, y 22465..29043 — 3437 × 5684 px, sitting
exactly between unit 71 (centre x 16350) and unit 73 (centre x 24402), at the
same latitude. A 1912 sheet is ~3287 px wide. **It is the footprint of sheet
72**, which has a pct:50 scan in the inventory (`pct50/sheet_0072.jpg`,
hash-pinned) but was never placed as a unit. Of the 98 scanned sheet numbers,
only 1–6 (title/index/key) and 72 are unplaced — 72 is the only ordinary city
sheet missing.

So the "92/92 units placed" headline is really 92 of 93 city sheets, and the
gap is not a source gap: **the scan exists and is already downloaded.** What
it needs is a registration pass to solve its transform from its neighbours,
the same tie-based placement the other 92 got. Recommend doing that before
1912 is called done; the second-largest hole (2.26M px² at [9309, 19687], a
121 px-wide strip) should be re-checked afterwards, as it may be spread
between columns rather than missing ground.

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
