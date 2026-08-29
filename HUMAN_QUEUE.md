# Human queue

Open items needing a human answer. Answer in the session; each item is
removed when resolved and the decision is recorded in `state/ledger.json`.

## HQ-1 · Part B brief is not available in the cloud session — OPEN

The session runs from the cloud addendum alone; the Part B text lives in
another chat that cloud sessions cannot read. The stage structure now in
`state/ledger.json` was reconstructed from the addendum's references and the
prior-work branches. **If Part B's stages/gates/thresholds differ, paste the
brief (or the relevant section) into the session** and the plan will be
reconciled. Until then, thresholds are taken from the prior accepted 1912 run
(its QA plan and acceptance reports).

## HQ-2 · 1899 scope: 13-sheet print footprint or wider? — OPEN

The addendum speaks of "the whole city" for `render.py --all`, but every
prior deliverable (both 27×40 masters) covers the wharf/downtown footprint
only, and the repo holds all 94 numbered 1899 sheets. Stage 2 will register
the **13 print-footprint sheets** first. Confirm whether the recipe should
eventually extend to all 94 sheets (registration effort scales roughly
linearly per seam), or the print footprint is the product.

## HQ-3 · 1912: D-019/D-023 marked "pending owner approval" — OPEN

The 1912 source branch tip includes cut/mask revisions from decisions
D-018/D-019/D-023 (street-label repairs). D-019 and D-023 are logged as
*pending owner approval*, but the uploaded 27×40 master (8-27-26) postdates
them and presumably renders them. The consolidated recipe takes the branch
tip. **Confirm the 8-27-26 masters are the accepted deliverables** (making
D-019/D-023 approved); if not, the recipe rolls back to the D-010 freeze
state, which is fully hash-pinned in `freeze_manifest.json`.

## HQ-4 · 1899: two symbol landmarks exceed the 8 px bar — adjudicated as drafting variance, confirm — OPEN

Held-out gate: 9 landmarks, median 2.7 px; all structural landmarks
(block/pier corners) pass at ≤7.7 px. Two drawn point-symbols are over:
`th-hydrant-514` (14|16, 16.3 px) and `red-disc-7` (11|12, 14.3 px). In the
overlays (`outputs/qc/human/HQ4_*.png`, panels: sheet A | sheet B |
red/blue blend) the surrounding structural ink — alley dashes, block
corners — aligns within a few px while only the symbol is offset, i.e. the
two draftsmen placed the symbol differently, the same failure class as the
alarm boxes and dash rows the relocation agents condemned. Proposed
verdict: registration passes THE BAR on surveyed structural landmarks;
symbol placement variance (≤16 px) is a disclosed source property.
Confirm, or direct otherwise.

## HQ-5 · City-wide expansion status — INFO (no answer needed yet)

Scope extended per your direction: all sheets, both years. 1899: 87 sheets /
90 units placed (frozen gated downtown core + ring solve; 26 sparse southern
units under blind tie-point adjudication; draft preview
`outputs/qc/preview_1899_city_draft.png`). 6 sheets excluded with cause
(rotated wharf-pier sheets 01/02/03/09/10, Texas City inset 94). 1912: all
233 source files fetched and hash-verified (archival for the accepted core,
IIIF pct:50 working copies elsewhere; full-res URLs recorded); key-map span
transcription in progress; registration will freeze the accepted 13-sheet
core and ring outward, same as 1899.
