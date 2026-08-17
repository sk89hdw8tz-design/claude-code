# Sheet 5 (wharf front) — deferred, region reserved

**Status: DEFERRED, not dropped. No substitute imagery exists or will be created.**

To be explicit about what "placeholder" means here: this is a *reserved region and a
deferral record*. It is not synthetic cartography, not an interpolation from the
neighbouring plates, and not borrowed 1899 wharf content. The brief forbids fabricating
map background, and nothing in this project will draw wharf geometry that the 1912
plate does not itself carry. Until sheet 5 is solved, the mosaic simply does not extend
across Avenue A, and the crop says so.

## Why sheet 5 is anomalous

Every other selected plate is a regular grid cell: 3 avenue-strips × 3 street-blocks,
orthogonal drafted grid, exactly one neighbour per edge. Sheet 5 is none of those.

| Property | Sheets 7–50 (12 plates) | Sheet 5 |
|---|---|---|
| Shape | 3×3 grid cell | long wharf strip |
| Street-row span | one row (3 blocks) | ~16th to 28th St — spans **three** rows |
| Neighbours on the landward edge | one | **four** (7, 9, 11, and 13 outside the set) |
| Drafted grid orientation concentration | 0.94–1.00 (median 0.994) | **0.454** |
| Dominant geometry | orthogonal street grid | piers drafted **diagonally** to the grid |

The 0.454 concentration is not a measurement failure — it is the correct answer for a
plate whose principal drafted features are angled piers and rail yard tracks rather
than an orthogonal street grid. That also means the grid-orientation prior used for the
other twelve plates does not apply to sheet 5.

## Why deferring is the right order of work

The remaining twelve form a **closed, regular 4×3 block** with 17 internal pairs, all
reciprocal, all agreeing with the key-map grid. That block can be solved as a single
coherent network on its own terms. Sheet 5 attaches to it along Avenue A at three
separate places (5–7, 5–9, 5–11) — so it is better constrained *against an already
solved block* than as one more unknown inside the solve, where its unusual geometry and
triple attachment could distort the whole network.

Deferral also isolates risk: if sheet 5 turns out to disagree with the block (a genuine
possibility — it is a different drafting problem, and the brief anticipates plates that
honestly disagree), that disagreement is then measurable against a fixed reference
rather than absorbed silently into a joint fit.

## What is reserved

- The mosaic plane reserves the region seaward of **Avenue A (Water)** across the 19th–25th
  Street frontage, covering **Piers 19–25**.
- The seam group **"Ave. A or Water"** (pairs 5–7, 5–9, 5–11) stays in the adjacency graph
  and the pooled-seam table, flagged `deferred`, so it cannot be quietly forgotten.
- Sheet 5's archival original remains in the verified inventory, checksummed and untouched.

## RESOLVED by independent review (2026-08-17): CONFIRMED MULTI-REGION — two panels

The Fable review track investigated independently (`fable_review/SHEET05_INDEPENDENT_FINDING.md`,
30 evidence crops, region polygons in `fable_review/sheet05_candidate_regions.geojson`) and the
controller verified the pivotal evidence directly against the archival scan. Findings adopted:

- Sheet 5 carries **two separately drafted panels of one continuous east-west wharf frontage**,
  divided by a drafted full-height triple rule at centreline x ≈ 3789 + 0.0099·y.
- **Panel A (page-left) = Piers 17–22** (16th–22nd St; landward refs 6, 33, 7, 9).
  **Panel B (page-right) = Piers 22–28** (22nd–28th St; refs 9, 11, 13, 4).
- **Pier 22 is drawn on BOTH panels** — verified at (1900, 7280) and (4560, 360). A single rigid
  transform would displace the same pier ~2,400 ft; **two transforms are required**. The
  duplicated Pier 22 / 22nd St ground is the cross-panel consistency check, and is the only
  duplicated cartography known anywhere in this edition.
- Corrections to the earlier stacked-strips hypothesis: the panels are **east/west**, the
  continuation runs bottom-of-A → top-of-B, and **sheet 9 adjoins BOTH panels** (the break at
  22nd St falls inside sheet 9's 21st–24th range). North is page-left (drafting rotated, page
  not rotated in the scan — lettering is upright). Pier 16 is not drawn despite the index's
  "16–28". The Piers 19–25 target footprint spans the break; Piers 17–18 and 26–28 lie outside
  it (polygon-flagged).
- Evidence gap: sheet 13 is not in the source set; the 5–13 attachment rests on sheet 5's own
  printed refs and the key map until sheet 13 is fetched.

Deferral and re-entry criteria below stand, amended: on re-entry, fit the TWO regions
independently against the frozen block, with the duplicated Pier 22 ground as the cross-panel
check, and controls per panel from the named features listed in the finding.

## Superseded working hypothesis (retained for the record): sheet 5 as *two* strips on one page

Raised by the project owner, and consistent with what has been observed: the plate may
carry **two separate wharf-front strips** rather than one continuous run — the left half
belonging north of / above the right half, laid out side by side purely to fit a portrait
page. Sanborn does exactly this with long waterfront frontages.

Supporting evidence already in hand:
- The landward edge references run **9 → 11 → 13** in sequence along its length; a single
  continuous strip meeting the block would not need to span that many rows on one page.
- The drafted grid concentration is 0.454, consistent with two differently-oriented runs
  of angled piers on one sheet rather than one coherent orthogonal frame.
- Piers 16–28 (the index's assignment for sheet 5) is a long frontage for one page at the
  edition's scale.

**If true, sheet 5 must not be treated as one rigid plate.** It would need to be cut into
its two constituent strips at the page break, each fitted as an independent piece with
its own transform. Fitting the page as a single rigid unit would be wrong regardless of
how low the residuals looked — the classic case of a plausible fit that is structurally
false. The page break must be located from the drafted content (where one strip's frontage
ends and the other begins), not guessed at the page midpoint.

Deferred by agreement until the twelve-sheet block is solved.

## Re-entry criteria

1. The twelve-sheet block is solved and its transforms frozen.
2. Controls along Avenue A are identified separately for each of 5–7, 5–9, 5–11, since a
   single strip meeting three plates may not be consistent with all three at once.
3. Sheet 5 is fitted **against the frozen block**, and any residual disagreement is
   reported rather than distributed into the block.
4. If the wharf cannot be reconciled honestly, the master is cropped at Avenue A and the
   omission is stated on the sheet — not papered over.
