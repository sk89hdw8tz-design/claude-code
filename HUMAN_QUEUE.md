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
